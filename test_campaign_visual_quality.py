"""Visual campaign QA: real manufacturer silhouettes, no white cards, best art."""
import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from ai_photo_effects import manufacturer_cutout
from campaign_art_quality import (inspected_product, choose_best,
                                  visual_review, campaign_consistency)
from campaign_director import plan_campaign
from campaign_role_posters import technical_poster, smart_poster
from campaign_hub import _native_graphic
from poster_quality import capture


def photo_bytes(image):
    buf=io.BytesIO()
    image.save(buf,format="PNG")
    return buf.getvalue()


def synthetic_ratchets():
    """Flat white manufacturer-photo surrogate with four dark metal tools."""
    im=Image.new("RGB",(840,660),"white")
    d=ImageDraw.Draw(im)
    for index in range(4):
        x0=145+index*12
        y=140+index*110
        x1=710-index*35
        d.line([(x0,y),(x1,y+25)],fill=(42+index*12,55+index*9,63+index*8),width=22)
        d.ellipse((x0-44,y-40,x0+39,y+42),
                  fill="#637381",outline="#203448",width=8)
        d.ellipse((x0-16,y-13,x0+16,y+14),fill="#DCE5E9",outline="#1B3748",width=5)
        d.ellipse((x1-14,y+13,x1+12,y+37),fill="#415765")
    return photo_bytes(im)


def workshop_photo():
    im=Image.new("RGB",(640,450),"#30546A")
    d=ImageDraw.Draw(im)
    for x in range(20,630,76):
        d.rectangle((x,35,x+38,240),fill="#71909A")
        d.rectangle((x+6,280,x+45,360),fill="#B49463")
    return photo_bytes(im)


def product_record():
    return {
        "part":"9365",
        "title":"Stainless Steel High-Quality Ratchet Set 4pc - 50th Anniversary",
        "features":[
            "1/4 inch ratchet with 60 tooth ratchet mechanism.",
            "Set includes four ratchets with different drive sizes.",
            "As part of Laser Tools 50th Anniversary, these ratchets are offered with a 50-year warranty.",
        ],
        "description":"Stainless steel ratchet set for workshops.",
        "specs":{},"price":"£178.00 ex VAT",
        "source":"https://www.toolconnection.co.uk/products/general-hand-tools/socketry/"
                 "general-ratchets/mixed-sets/9365-stainless-steel-high-quality-ratchet-set",
    }


class VisualCampaignQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.photo=synthetic_ratchets()
        cls.scene=workshop_photo()
        cls.product=product_record()

    def test_genuine_cutout_has_transparency_with_original_dark_tool_pixels(self):
        cut,success=manufacturer_cutout(self.photo)
        self.assertTrue(success)
        self.assertEqual(cut.mode,"RGBA")
        alpha=cut.getchannel("A")
        self.assertGreater(alpha.getextrema()[1],220)
        self.assertGreater(alpha.histogram()[0],0) # white paper becomes transparent
        self.assertFalse(inspected_product(self.photo)["needs_manual_cutout"])
        self.assertGreater(inspected_product(self.photo)["foreground_coverage"],.012)

    def test_technical_and_product_selected_posters_do_not_have_white_photo_cards(self):
        concepts,_=plan_campaign(self.product)
        with capture() as technical_capture:
            tech=technical_poster(self.product,self.photo,concepts[0],self.scene)
        with capture() as smart_capture:
            smart=smart_poster(self.product,self.photo,concepts[2],self.scene)
        self.assertNotEqual(tech,smart)
        for role,image,data in (
            ("technical_application",tech,technical_capture),
            ("product_selected",smart,smart_capture),
        ):
            with self.subTest(role=role):
                report=visual_review(image,role,source_info=inspected_product(self.photo))
                self.assertTrue(report["passed"],report)
                self.assertLess(report["white_fraction"],.18)
                self.assertLessEqual(len([t for t in data.texts if t["truncated"]]),0)
                with Image.open(io.BytesIO(image)) as pic:
                    self.assertEqual(pic.size,(1200,1500))
                    # Large old white card occupied much of this region.
                    points=((95,760),(85,890),(115,1050))
                    self.assertTrue(all(
                        not all(c>240 for c in pic.getpixel(pt)[:3])
                        for pt in points))

    def test_story_and_social_hero_use_cutout_instead_of_white_photo_rectangle(self):
        image=_native_graphic(
            self.product,self.photo,None,"social_story",
            self.product["features"][0],self.scene)
        with Image.open(io.BytesIO(image)) as art:
            self.assertEqual(art.size,(1080,1920))
            # White product card previously occupied x=62..1018 y=558..1360.
            for pt in ((85,585),(95,1000),(984,1340)):
                self.assertFalse(all(v>=243 for v in art.getpixel(pt)[:3]))

    def test_rejects_white_flyers_bad_contrast_and_text_clipping(self):
        white=photo_bytes(Image.new("RGB",(1200,1500),"white"))
        self.assertFalse(visual_review(white,"technical_application")["passed"])
        navy=photo_bytes(Image.new("RGB",(1200,1500),"#11253A"))
        self.assertFalse(visual_review(navy,"price_promo")["passed"])
        good=Image.new("RGB",(1200,1500),"#0B2948")
        d=ImageDraw.Draw(good)
        d.rectangle((100,210,1120,780),fill="#1782C4")
        d.rectangle((145,850,980,1390),fill="#F6BF35")
        image=photo_bytes(good)
        self.assertTrue(visual_review(image,"price_promo")["passed"])
        self.assertFalse(visual_review(image,"price_promo",
                                      text_status={"truncated":True})["passed"])
        accepted,report=choose_best(
            lambda v: ((white if v==0 else navy if v==1 else image),{}),
            "price_promo",self.photo)
        self.assertEqual(accepted,image)
        self.assertEqual(report["variation"],2)
        self.assertEqual(report["rejected_candidates"],2)
        with self.assertRaisesRegex(ValueError,"quality checks"):
            choose_best(lambda v:(white,{}),"technical_application",self.photo)

    def test_price_poster_has_short_product_headline_not_repeated_paragraph(self):
        concepts,plan=plan_campaign(self.product)
        self.assertLess(len(concepts[1]["headline"]),49)
        self.assertIn("Ratchet",concepts[1]["headline"])
        self.assertEqual(concepts[1]["features"],[])
        self.assertEqual(concepts[1]["focus"],"price")
        self.assertEqual(len(campaign_consistency(concepts)),0)
        self.assertNotEqual(concepts[0]["selling_point"],concepts[2]["selling_point"])

    def test_bad_product_roles_and_duplicate_proof_are_detected(self):
        concepts,_=plan_campaign(self.product)
        invalid=[dict(x) for x in concepts]
        invalid[2]["campaign_role"]="price_promo"
        self.assertTrue(campaign_consistency(invalid))
        invalid=[dict(x) for x in concepts]
        for item in invalid:
            item["selling_point"]="The exact same manufacturer feature"
        self.assertIn("All three posters repeat the same selling point",
                      campaign_consistency(invalid))


if __name__=="__main__":
    unittest.main()
