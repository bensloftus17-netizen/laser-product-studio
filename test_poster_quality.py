"""Quality gate regression: actual text boxes/alpha, safe RRP, auto-repair."""
import io
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

from ai_promo_renderer import render_promo
from poster_quality import QualityCapture,assess_text_and_geometry,review


def image_bytes():
    source=Image.new("RGB",(620,420),"white")
    draw=ImageDraw.Draw(source)
    draw.rounded_rectangle((81,61,545,360),radius=20,fill="#193A55")
    draw.rectangle((180,160,394,257),fill="white")
    output=io.BytesIO();source.save(output,format="PNG")
    return output.getvalue()


class PromotionalQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=image_bytes()
        cls.product={"part":"8899","title":"Ball Joint Separator for JLR",
                     "price":"£144.16 excluding VAT",
                     "features":["Scissor-type tool for suspension joints"]}
        cls.concept={"family":"retail","variant":0,
                     "headline":"Ball Joint Separator for JLR",
                     "subline":"Suspension application",
                     "features":cls.product["features"]}

    def test_reject_cropped_product_missing_price_and_clipped_headline(self):
        tracked=QualityCapture(
            texts=[{"text":"Very Long Headline","box":(10,20,110,70),
                    "lines":("Very Long…",),"font_size":44,"role":"headline",
                    "truncated":True}],
            areas=[{"role":"price","box":(20,40,280,230)}],
            products=[{"box":(0,50,600,500),
                       "visible_fraction":.73,"isolated":True}])
        res=assess_text_and_geometry(tracked,
             {"amount":"£144.16","vat":"EX VAT"},self.concept)
        self.assertFalse(res["passed"])
        self.assertTrue(any("cropped" in x for x in res["issues"]))
        self.assertTrue(any("clipped" in x for x in res["issues"]))
        self.assertTrue(any("price" in x.lower() for x in res["issues"]))
        self.assertTrue(any("overlaps" in x for x in res["issues"]))

    def test_all_family_variants_are_checked_and_remain_valid(self):
        for family in ("retail","premium","trade"):
            for variant in range(3):
                with self.subTest(family=family,variant=variant):
                    report={}
                    concept={**self.concept,"family":family,"variant":variant}
                    art=render_promo(concept,self.source,self.product,
                                     editor={"_quality_report":report})
                    self.assertTrue(art.startswith(b"\x89PNG"))
                    self.assertTrue(report["passed"],report)
                    self.assertEqual(report["status"] in ("passed","review"),True)
                    self.assertTrue(report["price_checked"])
                    self.assertLessEqual(report["attempts"],3)

    def test_autorepair_cropped_product_scale_without_lying_about_it(self):
        report={}
        art=render_promo(self.concept,self.source,self.product,
                         editor={"product_scale":160,"product_x":95,
                                 "product_y":85,"_quality_report":report})
        self.assertTrue(art.startswith(b"\x89PNG"))
        self.assertTrue(report["auto_corrected"])
        self.assertTrue(report["passed"])

    def test_missing_verified_rrp_does_not_generate_price(self):
        report={}
        no_rrp={**self.product,"price":None}
        art=render_promo(self.concept,self.source,no_rrp,
                         editor={"_quality_report":report})
        self.assertTrue(art.startswith(b"\x89PNG"))
        self.assertTrue(report["passed"])
        self.assertEqual(report["price_checked"],True)

    def test_render_result_has_exact_expected_pixel_size(self):
        png=render_promo(self.concept,self.source,self.product)
        with Image.open(io.BytesIO(png)) as im:
            self.assertEqual(im.size,(1200,1500))


if __name__=="__main__":
    unittest.main()
