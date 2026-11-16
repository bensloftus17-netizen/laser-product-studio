"""Zero-cost AI promo system regression tests: 3 sales posters with prices.

No external API calls are made. Manufacturer photos and Gemini are mocked.
"""
import io
import json
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

from ai_promo_renderer import (FAMILIES,RENDERERS,verified_price,
                               render_promo,RETAIL_PALETTES,
                               PREMIUM_PALETTES,TRADE_PALETTES)

class OneClickPromos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        im=Image.new("RGB",(650,360),"white")
        d=ImageDraw.Draw(im)
        d.line((70,300,550,90),fill="#202A35",width=55)
        d.ellipse((430,60,570,192),fill="#202A35")
        b=io.BytesIO();im.save(b,format="PNG")
        cls.photo=b.getvalue()
        cls.product={"part":"9364","title":"Ratchet Set with Comfort Handle 3pc - 50th Anniversary",
                     "price":"£101.48 excluding VAT",
                     "price_source":"Official UK manufacturer RRP",
                     "description":"Three genuine ratchets of different drive sizes.",
                     "specs":{"Pieces":"3"},
                     "features":["Three chrome vanadium ratchets with a comfortable handle",
                                 "1/4 inch ratchet with 72 tooth ratchet mechanism",
                                 "3/8 inch ratchet with 72 tooth ratchet mechanism"]}
        cls.concepts=[
            {"family":"retail","headline":"Three Ratchets. One Kit.","subline":"Three genuine ratchets.",
             "part":"9364","name":"Retail Promo","variant":0,
             "features":cls.product["features"]},
            {"family":"premium","headline":"A Ratchet for the Job","subline":"Discover the three-piece set.",
             "part":"9364","name":"Premium Promo","variant":0,
             "features":cls.product["features"]},
            {"family":"trade","headline":"Tools for the Workshop","subline":"Verified drive sizes and contents.",
             "part":"9364","name":"Trade Promo","variant":0,
             "features":cls.product["features"]},
        ]

    def test_three_real_sales_promo_families_are_distinct(self):
        self.assertEqual(FAMILIES,("retail","premium","trade"))
        self.assertEqual(set(RENDERERS),set(FAMILIES))
        outputs=[]
        for concept in self.concepts:
            data=render_promo(concept,self.photo,self.product)
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            with Image.open(io.BytesIO(data)) as img:
                self.assertEqual(img.size,(1200,1500))
                self.assertEqual(img.mode,"RGB")
                outputs.append((data,img.getpixel((10,10)),img.getpixel((65,740))))
        self.assertEqual(len({a for a,_,_ in outputs}),3)
        self.assertEqual(len({b for _,b,_ in outputs}),3)

    def test_colour_variants_generate_nine_distinct_graphics(self):
        posters=[]
        for concept in self.concepts:
            for variant in (0,1,2):
                posters.append(render_promo({**concept,"variant":variant},self.photo,self.product))
        self.assertEqual(len(set(posters)),9)
        self.assertEqual(len(RETAIL_PALETTES),3)
        self.assertEqual(len(PREMIUM_PALETTES),3)
        self.assertEqual(len(TRADE_PALETTES),3)

    def test_price_is_exact_and_vat_is_not_invented(self):
        self.assertEqual(verified_price(self.product)["amount"],"£101.48")
        self.assertEqual(verified_price(self.product)["vat"],"EX VAT")
        self.assertEqual(verified_price({**self.product,"price":"£121.78 including VAT"})["vat"],"INC VAT")
        missing=verified_price({**self.product,"price":None})
        self.assertIsNone(missing["amount"])
        self.assertEqual(missing["label"],"PRICE ON REQUEST")
        draft=verified_price({**self.product,"price_source":"Staff entry, independently reviewed"})
        self.assertEqual(draft["label"],"DRAFT UK RRP")
        for c in self.concepts:
            self.assertGreater(len(render_promo(c,self.photo,{**self.product,"price":None})),10000)

    def test_mocked_endpoint_generates_three_price_led_posters(self):
        import app as app_module
        self.assertNotIn('id="creativeBrief"',app_module.V7_HOME_PAGE)
        self.assertNotIn('creative_brief:',app_module.V7_HOME_PAGE)
        model=[{**c} for c in self.concepts]
        with patch.object(app_module,"lookup",return_value=(self.product,self.photo)), \
             patch.object(app_module,"propose_ai_concepts",return_value=model):
            response=app_module.app.test_client().post("/api/ai/concepts/9364",
                             json={"distributor_brand":"none"})
            self.assertEqual(response.status_code,200,response.get_json())
            body=response.get_json()
            self.assertEqual([v["family"] for v in body["concepts"]],list(FAMILIES))
            for v in body["concepts"]:
                self.assertTrue(v["preview"].startswith("data:image/png;base64,"))
        with patch.object(app_module,"lookup",return_value=(self.product,self.photo)), \
             patch.object(app_module,"propose_ai_concepts",return_value=model), \
             patch.object(app_module,"render_ai_promo",return_value=b"test") as render:
            r=app_module.app.test_client().post("/api/ai/concepts/9364",
                json={"distributor_brand":"none","staff_rrp_ex":"54.25",
                      "staff_rrp_reviewed":True,"staff_rrp_basis":"inc"})
            self.assertEqual(r.status_code,200,r.get_json())
            self.assertEqual(render.call_args_list[0].args[2]["price"],"£54.25 including VAT")
            blocked=app_module.app.test_client().post("/api/ai/concepts/9364",
                json={"distributor_brand":"none","staff_rrp_ex":"54.25",
                      "staff_rrp_reviewed":False,"staff_rrp_basis":"inc"})
            self.assertEqual(blocked.status_code,404)

if __name__=="__main__":
    unittest.main()
