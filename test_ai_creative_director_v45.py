"""V45: AI owns the composition; product pixels/facts and quality remain locked."""
import io
import json
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image,ImageDraw

from creative_director import validate_brief, distinct_briefs, creative_instruction
from campaign_distinctness import check_distinctness
from flexible_canvas import render_creative_canvas
from asset_quality import inspect_asset
from creative_qa import review_finished_artworks
from campaign_director import plan_campaign
from campaign_hub import build_campaign
from poster_quality import capture,record_product


TECH = {
    "zones":{"headline":[330,170,590,130],"product":[60,355,470,420],
             "proof":[595,580,300,150]},
    "background":"industrial","mood":"technical","motif":"industrial-grid",
    "headline_style":"editorial","photo_focus":"right","accent":"#13B5EC",
}
PRICE = {
    "zones":{"headline":[60,155,495,145],"product":[575,280,345,400],
             "proof":[60,480,420,125],"price":[60,715,420,145]},
    "background":"workshop-photo","mood":"energetic","motif":"speed-lines",
    "headline_style":"massive","photo_focus":"centre","accent":"#FFC83A",
}
SMART = {
    "zones":{"headline":[70,190,390,175],"product":[485,395,430,430],
             "proof":[70,590,350,190]},
    "background":"studio-gradient","mood":"understated","motif":"circles",
    "headline_style":"compact","photo_focus":"left","accent":"#71D6EE",
}
PRODUCT = {
    "part":"9365","title":"Ratchet Set 4pc",
    "description":"Professional ratchet set.",
    "features":["Set of four ratchets.","Supplied with a carry case.",
                "Four drive options for workshop use."],
    "specs":{},"price":None,
    "source":"https://www.toolconnection.co.uk/products/general-hand-tools/socketry/"
             "general-ratchets/mixed-sets/9365-stainless-steel-ratchet-set",
}


def image_bytes(w=950,h=800):
    im=Image.new("RGB",(w,h),"white")
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((w//5,h//4,w*4//5,h*3//4),
                        radius=36,fill="#09283F",outline="#1387BE",width=22)
    d.ellipse((w//3,h//3,w*2//3,h*2//3),
              fill="#F2B42D",outline="#1475A3",width=26)
    out=io.BytesIO();im.save(out,"PNG");return out.getvalue()


def fake_photo(canvas,raw,bounds,scale=1):
    # Simulates compositing a genuine opaque manufacturer shape for deterministic
    # renderer geometry checks without depending on auto-segmentation heuristics.
    x0,y0,x1,y1=bounds
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((x0+15,y0+15,x1-15,y1-15),
                        radius=32,fill="#3577A4")
    record_product((x0+15,y0+15,x1-15,y1-15),.13,True)
    return {"isolated":True,"needs_manual_cutout":False}


class CreativeDirectorV45Tests(unittest.TestCase):
    def test_model_controls_real_coordinates_not_template_ids(self):
        for role,brief in (
            ("technical_application",TECH),
            ("price_promo",PRICE),
            ("product_selected",SMART),
        ):
            result=validate_brief(brief,role)
            self.assertIsNotNone(result)
            self.assertEqual(result["zones"],brief["zones"])
            self.assertEqual(result["source"],"ai-freeform-canvas")
        self.assertTrue(distinct_briefs([
            validate_brief(TECH,"technical_application"),
            validate_brief(PRICE,"price_promo"),
            validate_brief(SMART,"product_selected")]))
        self.assertIn("NOT template IDs",creative_instruction())

    def test_rejects_missing_price_overlap_and_tiny_product(self):
        broken={**PRICE,"zones":{**PRICE["zones"],"product":[80,165,200,200]}}
        self.assertIsNone(validate_brief(broken,"price_promo"))
        collided={**PRICE,"zones":{**PRICE["zones"],"product":[150,170,400,350]}}
        self.assertIsNone(validate_brief(collided,"price_promo"))
        no_price={**PRICE,"zones":{k:v for k,v in PRICE["zones"].items()
                                  if k!="price"}}
        self.assertIsNone(validate_brief(no_price,"price_promo"))
        bad_content={**PRICE,"headline":"guaranteed free unlimited repairs",
                     "photo_url":"https://fake.example.com/fake-tool.png"}
        safe=validate_brief(bad_content,"price_promo")
        self.assertNotIn("headline",safe)
        self.assertNotIn("photo_url",safe)

    def test_director_routes_original_ai_artboards_by_campaign_role(self):
        models=[
            {"creative_canvas":PRICE},  # retail -> price promotion
            {"creative_canvas":SMART},  # premium -> smart product selected
            {"creative_canvas":TECH},   # trade -> technical
        ]
        concepts,plan=plan_campaign(PRODUCT,models)
        self.assertEqual([c["creative_canvas"]["zones"] for c in concepts],
                         [TECH["zones"],PRICE["zones"],SMART["zones"]])
        self.assertTrue(all(c["visual_plan"]["creative_source"]=="gemini-freeform-canvas"
                            for c in concepts))

    def test_renderer_never_uses_untrusted_model_claims_or_urls(self):
        concept={"campaign_role":"price_promo","creative_canvas":PRICE,
                 "headline":"Ratchet Set 4pc","selling_point":"Set of four ratchets.",
                 "part":"9365"}
        raw=image_bytes()
        with patch("flexible_canvas.product_photo",side_effect=fake_photo) as placed:
            with capture() as tracked:
                png=render_creative_canvas(PRODUCT,raw,concept,variant=1)
        self.assertEqual(Image.open(io.BytesIO(png)).size,(1200,1500))
        self.assertEqual(placed.call_args.args[1],raw)
        self.assertTrue(any(t["role"]=="headline" for t in tracked.texts))
        self.assertTrue(any(t["role"]=="price" for t in tracked.texts))
        self.assertTrue(any(a["role"]=="price" for a in tracked.areas))
        self.assertFalse(any(t["truncated"] for t in tracked.texts))

    def test_rejects_low_resolution_and_duplicate_pixels(self):
        bad=inspect_asset(image_bytes(240,220))
        self.assertFalse(bad["passed"])
        self.assertTrue(any("too small" in issue for issue in bad["issues"]))
        solid=Image.new("RGB",(1200,1500),"#072B49")
        canvas=io.BytesIO();solid.save(canvas,"PNG")
        sample=canvas.getvalue()
        image_map={"poster_technical":sample,"poster_price":sample,"poster_smart":sample}
        concepts=[{"creative_canvas":validate_brief(item,role)} for item,role in
                  zip((TECH,PRICE,SMART),("technical_application","price_promo","product_selected"))]
        result=check_distinctness(image_map,concepts)
        self.assertFalse(result["passed"])
        self.assertTrue(any("duplicate" in issue for issue in result["issues"]))

    def test_real_manufacturer_photo_freeform_artwork(self):
        """When the genuine 8899 photo is reachable, actually render all three."""
        import requests
        from campaign_art_quality import visual_review
        try:
            response=requests.get(
                "https://www.lasertools.co.uk/items/xlarge/8899.jpg",
                timeout=(3,12))
            response.raise_for_status()
        except requests.RequestException as exc:
            self.skipTest("Official photo unavailable: "+str(exc)[:90])
        photo=response.content
        evaluation=inspect_asset(photo)
        self.assertTrue(evaluation["passed"],evaluation)
        product={
            "part":"8899","title":"Ball Joint Separator for JLR",
            "features":["Heavy-duty scissor-type ball joint separator."],
            "price":"£144.16 excluding VAT","specs":{},
        }
        for role,brief in (
            ("technical_application",TECH),
            ("price_promo",PRICE),
            ("product_selected",SMART),
        ):
            with self.subTest(role=role):
                concept={"campaign_role":role,
                         "creative_canvas":brief,
                         "headline":"Ball Joint Separator",
                         "selling_point":product["features"][0]}
                with capture() as traced:
                    result=render_creative_canvas(product,photo,concept,variant=1)
                status={
                    "truncated":any(x["truncated"] for x in traced.texts),
                    "missing_headline":not any(
                        x["role"]=="headline" for x in traced.texts),
                    "product_visible_fraction":max(
                        (x["visible_fraction"] for x in traced.products),
                        default=0),
                }
                report=visual_review(result,role,text_status=status)
                self.assertTrue(report["passed"],report)

    def test_no_ai_critic_without_key_but_deterministic_qa_remains(self):
        with patch.dict("os.environ",{"GEMINI_API_KEY":""}):
            result=review_finished_artworks({})
        self.assertFalse(result["reviewed"])
        self.assertEqual(result["issues"],{})

    def test_build_campaign_uses_freeform_path_and_preserves_bundle(self):
        concepts,_=plan_campaign(PRODUCT,[
            {"creative_canvas":PRICE},
            {"creative_canvas":SMART},
            {"creative_canvas":TECH},
        ])
        raw=image_bytes()
        mock_scene={"source":"No external photograph used","category":"hand_tools"}
        placeholder=io.BytesIO()
        Image.new("RGB",(1200,1500),"#183B59").save(placeholder,"PNG")
        payload=placeholder.getvalue()
        records=[]
        def select(render,role,blob,**kwargs):
            records.append(role)
            # A controlled model canvas must reach the new renderer, not the
            # legacy technical/smart/retail functions.
            output,geometry=render(1)
            return output,{"passed":True,"score":93,"variation":1,
                           "warnings":[],"candidates_checked":1}
        with patch("campaign_hub._concepts",return_value=(
                [{"creative_canvas":PRICE},{"creative_canvas":SMART},
                 {"creative_canvas":TECH}],"gemini-assisted",[])), \
             patch("campaign_hub.require_good_asset",return_value={"passed":True}), \
             patch("campaign_hub.find_scene",return_value=(None,mock_scene)), \
             patch("campaign_hub.choose_best",side_effect=select), \
             patch("campaign_hub.render_creative_canvas",return_value=payload) as draw, \
             patch("campaign_hub.review_finished_artworks",return_value={
                 "method":"test-critic","reviewed":True,"issues":{},"warning":None}), \
             patch("campaign_hub.check_distinctness",return_value={
                 "passed":True,"issues":[],"pairs":[]}):
            pack=build_campaign(PRODUCT,raw,use_gemini=True)
        self.assertEqual(records,
            ["technical_application","price_promo","product_selected"])
        self.assertEqual(draw.call_count,3)
        self.assertEqual(pack["manifest"]["creative_plan"]["render_engine"],
                         "ai-authored-freeform-layout")
        self.assertTrue(pack["manifest"]["creative_critic"]["reviewed"])
        self.assertEqual(pack["manifest"]["product_photo_quality"],{"passed":True})
        with ZipFile(io.BytesIO(pack["archive"])) as zip_file:
            self.assertIn("Campaign_Manifest.json",zip_file.namelist())
            self.assertEqual(zip_file.read("01_Posters/02_Price_Promotion.png"),payload)


if __name__=="__main__":
    unittest.main()
