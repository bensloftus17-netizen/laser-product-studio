"""V71: the reference workshop poster must actually use the supplied image."""
import io
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
from poster_quality import capture, record_product
from reference_poster_templates import render_promo_reference
from workshop_reference_locked import reference_scene, SOURCE_PATH
from test_reference_templates_v67 import ReferenceTemplateTests


class LockedWorkshopReferenceV71Tests(unittest.TestCase):
    def setUp(self):
        self.product={
            "part":"9395", "title":"Front Wheel Bearing Kit", "price":"£175.00 ex VAT",
            "features":[
                "Press front wheel bearings using a standard workshop press.",
                "Applications include Mercedes-Benz Sprinter and VW Crafter.",
                "Kit includes extraction and insertion clamshells.",
            ],
        }
        self.concept={"features":list(self.product["features"]),
                      "selling_point":self.product["features"][0]}
        photo=Image.new("RGBA",(470,280),(0,0,0,0))
        d=ImageDraw.Draw(photo)
        d.ellipse((38,29,440,252),fill=(82,101,120,255))
        stream=io.BytesIO()
        photo.save(stream,"PNG")
        self.photo=stream.getvalue()

    def photo_placer(self,canvas, blob, bounds, scale=1, **placement):
        part=Image.open(io.BytesIO(blob)).convert("RGBA")
        part.thumbnail((bounds[2]-bounds[0]-75,bounds[3]-bounds[1]-80),
                       Image.Resampling.LANCZOS)
        x=(bounds[0]+bounds[2]-part.width)//2
        y=(bounds[1]+bounds[3]-part.height)//2
        canvas.alpha_composite(part,(x,y))
        record_product((x,y,x+part.width,y+part.height),.15,True)

    def render(self, scene=None):
        with patch("reference_poster_templates.product_photo",
                   side_effect=self.photo_placer) as placed:
            with capture() as record:
                result=render_promo_reference(
                    self.product,self.photo,self.concept,scene=scene)
            self.assertEqual(placed.call_args.args[1],self.photo)
        image=Image.open(io.BytesIO(result))
        image.load()
        return image,record,result

    def test_generated_scene_replaces_packshot_and_keeps_template_price(self):
        from ai_workbench_hero import MARKER, SIZE
        stream=io.BytesIO()
        Image.new("RGB",SIZE,"#806040").save(stream,"JPEG")
        with patch("reference_poster_templates.product_photo",
                   side_effect=AssertionError("Packshot must not overlay AI scene")):
            with capture() as record:
                output=render_promo_reference(
                    self.product,self.photo,self.concept,scene=MARKER+stream.getvalue())
        with Image.open(io.BytesIO(output)) as result:
            self.assertTrue(all(abs(a-b)<=3 for a,b in
                                zip(result.getpixel((600,800)),(128,96,64))))
        self.assertIn("£175.00",[item["text"] for item in record.texts])
        self.assertTrue(any("AI VISUALISATION" in item["text"] for item in record.texts))

    def test_workbench_preserves_separate_pieces_across_photo_shapes(self):
        from campaign_role_posters import product_photo

        for width, height in ((460, 180), (180, 460)):
            with self.subTest(size=(width, height)):
                kit=Image.new("RGBA",(width,height))
                draw=ImageDraw.Draw(kit)
                draw.rectangle((0,0,30,30),fill="#ff0000")
                draw.rectangle((width-31,height-31,width-1,height-1),fill="#00ff00")
                canvas=Image.new("RGBA",(1200,1500),"#444444")
                with patch("campaign_role_posters.inspected_product",return_value={
                    "rgba":kit,"isolated":True,"needs_manual_cutout":False,
                }):
                    result=product_photo(canvas,b"fixture",(58,630,1142,1012),workbench=True)
                x0,y0,x1,y1=result["position"]
                self.assertGreaterEqual(y0,630)
                self.assertEqual(y1,996)
                self.assertLessEqual(abs((x1-x0)/(y1-y0)-width/height),.025)
                pixels=canvas.crop((x0,y0,x1,y1)).getcolors(maxcolors=100000)
                colors={pixel for _,pixel in pixels}
                self.assertIn((255,0,0,255),colors)
                self.assertIn((0,255,0,255),colors)

    def test_reference_is_bundled_and_is_real_photographic_scene(self):
        self.assertTrue(SOURCE_PATH.exists())
        picture=reference_scene()
        self.assertEqual(picture.size,(1200,810))
        # Workbench is demonstrably photographic, not an abstract blue card.
        self.assertNotEqual(picture.getpixel((100,600)),
                            picture.getpixel((900,600)))

    def test_locked_workshop_is_not_a_generic_blue_artboard(self):
        image,record,_=self.render()
        self.assertEqual(image.size,(1200,1500))
        self.assertEqual(image.getpixel((11,20)),(2,16,31))
        # The pale steel workbench appears below the dark workshop backdrop.
        self.assertGreater(sum(image.getpixel((12,865))),
                           sum(image.getpixel((12,390))))
        self.assertTrue(record.products)
        self.assertIn("headline",[t["role"] for t in record.texts])
        self.assertIn("price",[a["role"] for a in record.areas])
        self.assertFalse(any(t["truncated"] for t in record.texts))

    def test_reference_grid_is_filled_with_source_verified_facts(self):
        _,record,_=self.render()
        displayed=[t["text"] for t in record.texts]
        self.assertIn("KIT CONTENTS",displayed)
        self.assertIn("KEY FEATURES",displayed)
        self.assertIn("£175.00",displayed)
        self.assertTrue(any("clamshells" in value for value in displayed))
        for fact in displayed:
            if "Press front wheel bearings" in fact:
                self.assertIn(fact,self.product["features"])

    def test_no_false_kit_claim_when_source_has_none(self):
        self.product["features"]=self.product["features"][:2]
        self.concept["features"]=self.product["features"]
        _,record,_=self.render()
        displayed=[t["text"] for t in record.texts]
        self.assertNotIn("KIT CONTENTS",displayed)
        self.assertIn("PRODUCT DETAILS",displayed)

    def test_workshop_look_is_immutable_against_unverified_scene_bytes(self):
        # User-approved reference is fixed; the model cannot swap it with an
        # arbitrary AI scene when one is provided.
        _,_,a=self.render()
        _,_,b=self.render(scene=b"not-a-licensed-workshop-photograph")
        self.assertEqual(a,b)

    def test_template_remains_distinct_from_technical_sheet(self):
        from reference_poster_templates import render_technical_reference
        with patch("reference_poster_templates.product_photo",
                   side_effect=self.photo_placer):
            technical=render_technical_reference(
                self.product,self.photo,self.concept)
        _,_,price=self.render()
        self.assertNotEqual(technical,price)


if __name__=="__main__":
    unittest.main()
