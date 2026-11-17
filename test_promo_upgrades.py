"""All five poster upgrades: safe QA, AI art, real scenes, proof points, RRP.

Checks actual finished PNGs and captures what the renderer drew, without OCR
or assuming unverified prices or fitment. Does not require paid APIs.
"""
import io
import unittest
from PIL import Image,ImageDraw
from ai_promo_renderer import render_promo,verified_price
from promo_art_direction import normalise_art_direction,PRICE_STYLES
from promo_scene_library import classify_product,scene_reference
from promo_selling_points import focus_concept,FOCUS_BY_FAMILY


def product_photo():
    im=Image.new("RGB",(630,425),"white")
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((98,68,528,351),radius=16,fill="#1C3C53")
    d.rectangle((200,175,398,263),fill="white")
    out=io.BytesIO();im.save(out,format="PNG")
    return out.getvalue()


class FiveImprovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.photo=product_photo()
        cls.product={
            "part":"8899",
            "title":"Ball Joint Separator for Land Rover / Jaguar",
            "description":"Scissor-type separator for servicing Land Rover suspension.",
            "price":"£144.16 excluding VAT",
            "price_source":"Official UK manufacturer",
            "features":[
                "Heavy-duty scissor-type mechanism provides controlled separation.",
                "Applications include Land Rover and Jaguar suspension ball joints.",
                "Steel construction with upper and lower jaws for workshop servicing.",
            ]}

    def test_three_factual_sales_angles_use_different_source_evidence(self):
        points=[focus_concept(self.product,{
            "family":family,
            "features":[self.product["features"][0]],
            "headline":"Ball Joint Separator for JLR"},i)
                for i,family in enumerate(("retail","premium","trade"))]
        self.assertEqual([p["focus"] for p in points],
                         ["price","benefit","application"])
        self.assertEqual(len({p["angle"] for p in points}),3)
        self.assertIn("£144.16",points[0]["selling_point"])
        self.assertEqual(points[1]["features"],
                         [self.product["features"][0]])
        self.assertEqual(points[2]["features"],
                         [self.product["features"][1]])
        self.assertTrue(all(
            p["features"][0] in self.product["features"] for p in points))

    def test_unverified_application_never_invents_vehicle(self):
        missing={"title":"General Hand Tool","part":"1020","features":[],
                 "price":None}
        concept=focus_concept(missing,{"family":"trade"},2)
        self.assertNotIn("Land Rover",concept["selling_point"])
        self.assertIn("requires manufacturer confirmation",concept["angle"])
        self.assertFalse(concept["features"])

    def test_verified_price_including_vat_and_missing_price(self):
        self.assertEqual(verified_price(self.product)["vat"],"EX VAT")
        self.assertEqual(verified_price({**self.product,
                "price":"£122.99 including VAT"})["vat"],"INC VAT")
        missing=verified_price({**self.product,"price":None})
        self.assertIsNone(missing["amount"])
        self.assertEqual(missing["vat"],"")

    def test_new_rrp_shapes_render_verbatim_price_and_vat(self):
        for family,style in [
            ("retail","sticker"),("premium","corner"),("trade","panel"),
            ("retail","corner"),("premium","sticker"),("trade","sticker")
        ]:
            with self.subTest(family=family,shape=style):
                report={}
                concept={"family":family,"variant":0,
                         "headline":"Ball Joint Separator for JLR",
                         "subline":"Suspension workshop service",
                         "features":self.product["features"][:1]}
                png=render_promo(concept,self.photo,self.product,editor={
                    "price_style":style,"_quality_report":report})
                self.assertTrue(report.get("passed"),report)
                self.assertTrue(report.get("price_checked"))
                with Image.open(io.BytesIO(png)) as output:
                    self.assertEqual(output.size,(1200,1500))

    def test_new_shapes_do_not_invent_vat_when_price_on_request(self):
        for style in ("sticker","corner","panel"):
            with self.subTest(style=style):
                report={}
                concept={"family":"premium","variant":0,
                         "headline":"Ball Joint Separator for JLR",
                         "features":self.product["features"][:1]}
                png=render_promo(concept,self.photo,
                     {**self.product,"price":None},
                     editor={"price_style":style,"_quality_report":report})
                self.assertTrue(report.get("passed"),report)
                self.assertTrue(png.startswith(b"\x89PNG"))

    def test_art_direction_only_supports_verified_safe_palette_and_shapes(self):
        for style in ("sticker","corner","panel"):
            result=normalise_art_direction({
                "price_style":style,"layout_variant":2,
                "product_scale":112,"graphic_motif":"diagonal-bars"},family="retail")
            self.assertEqual(result["price_style"],style)
            self.assertIn(result["accent"],("#F6D343","#F9A842",
                                            "#13B5EC","#D9E75B",
                                            "#40C1E8","#F1E9D8","#E8F4F4",
                                            "#FFCB5B","#FFFFFF"))
        self.assertEqual(len(PRICE_STYLES),7)

    def test_battery_hub_diagnostics_have_specific_real_photo_categories(self):
        self.assertEqual(classify_product({"title":"12V Battery Charger"}),"battery")
        self.assertEqual(classify_product({"title":"Wheel Bearing Kit"}),"wheel_hub")
        self.assertEqual(classify_product({"title":"OBD Diagnostic Scanner"}),"diagnostic")
        for category in ("battery","wheel_hub","diagnostic"):
            pages=[scene_reference(category,i,"trade")["page_url"]
                   for i in range(3)]
            self.assertTrue(all("pexels.com/photo/" in p for p in pages))
            self.assertGreaterEqual(len(set(pages)),3)


if __name__=="__main__":
    unittest.main()
