"""Photographic campaign scene selection — real asset + verified product rules."""
import io
import re
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw

from promo_scene_library import (SCENE_PHOTOS, SCENE_LABELS, classify_product,
                                 scene_reference, find_scene)
from ai_promo_renderer import render_promo


class ProductAwareCampaignTests(unittest.TestCase):
    def test_category_is_from_actual_product_title(self):
        cases = [
            ("12V Automatic Battery Charger and Maintainer","battery"),
            ("Portable Jump Starter with Battery Leads","battery"),
            ("Professional OBD Diagnostic Scan Tool","diagnostic"),
            ("Brake & Clutch Pressure Bleeder Kit","brakes"),
            ("MacPherson Suspension Hub Spreader Kit","wheel_hub"),
            ("50 Tonne Hydraulic Workshop Press","press"),
            ("MIG Welder Torch Kit","welding"),
            ("Crankshaft Pulley Puller Ford EcoBlue","engine"),
            ("Glow Plug Damaged Removal Set","engine"),
            ("3pc Ratchet with Comfort Handle Set","hand_tools"),
            ("General Tool Storage Unit","workshop"),
        ]
        for name,expected in cases:
            with self.subTest(product=name):
                self.assertEqual(classify_product({"title":name}),expected)

    def test_battery_advert_has_real_jumper_leads_photo_source(self):
        product={"title":"12V Battery Charger 10A","part":"CHG123"}
        for variation in (0,1,2):
            item=scene_reference(classify_product(product),variation)
            self.assertIn(item["photo_id"],(32282232,32282233,6473244))
            self.assertIn("battery",item["description"].lower())
            self.assertEqual(item["source"],"Pexels free commercial-use photo")
            self.assertEqual(item["license_url"],"https://www.pexels.com/license/")
            self.assertTrue(item["image_url"].startswith("https://images.pexels.com/photos/"))
        with patch("promo_scene_library._fetch_licensed_photo",return_value=b"real_photo") as f:
            picture,metadata=find_scene(product)
        self.assertEqual(picture,b"real_photo")
        self.assertEqual(metadata["category"],"battery")
        f.assert_called_once()

    def test_official_in_situ_photo_is_preferred_for_trade(self):
        p={"part":"5205","title":"Damaged Glow Plug Removal Set",
           "application_photo_source":"https://www.lasertools.co.uk/official/photo.jpg"}
        img=b"official_verified_photo"
        with patch("promo_scene_library._fetch_licensed_photo",return_value=b"licensed_photo") as f:
            chosen,meta=find_scene(p,variation=2,official_photo=img,prefer_official=True)
            self.assertEqual(chosen,img)
            self.assertEqual(meta["source"],"Official manufacturer application photo")
            f.assert_not_called()
            chosen,meta=find_scene(p,variation=1,official_photo=img)
            self.assertEqual(chosen,b"licensed_photo")
            self.assertEqual(meta["category"],"engine")

    def test_manual_scene_category_is_restricted(self):
        p={"title":"Battery Charger"}
        with patch("promo_scene_library._fetch_licensed_photo",return_value=b"real") as fetch:
            image,meta=find_scene(p,category_override="engine")
            self.assertEqual(meta["category"],"engine")
            image,meta=find_scene(p,category_override="not-a-real-category")
            self.assertEqual(meta["category"],"battery")

    def test_missing_photo_does_not_generate_fake_usage_picture(self):
        with patch("promo_scene_library._fetch_licensed_photo",return_value=None):
            photo,meta=find_scene({"title":"Brake Disc Caliper Service"})
        self.assertIsNone(photo)
        self.assertEqual(meta["source"],"No external photograph used")

    def test_three_full_bleed_campaigns_are_all_real_tool_photographs(self):
        kit=Image.new("RGB",(580,470),"white")
        d=ImageDraw.Draw(kit)
        d.rounded_rectangle((110,55,487,414),radius=42,fill="#0878BA")
        d.rectangle((185,180,400,300),fill="#283443")
        out=io.BytesIO();kit.save(out,format="PNG")
        photo=out.getvalue()
        actual_scene=Image.new("RGB",(1300,900),"#365260")
        d=ImageDraw.Draw(actual_scene)
        d.rectangle((80,80,1000,700),fill="#8A9B9F")
        d.line((100,320,1250,610),fill="#132C43",width=120)
        buf=io.BytesIO();actual_scene.save(buf,format="JPEG")
        background=buf.getvalue()
        product={"part":"5205","title":"Damaged Glow Plug Removal Set",
                 "features":["M8 and M10 threads","Precision adaptors supplied"],
                 "price":None,"price_source":None}
        outputs=[]
        for i,family in enumerate(("retail","premium","trade")):
            concept={"family":family,"variant":i,"headline":"Damaged Glow Plug Removal Set",
                     "features":product["features"],"subline":"Removal kit"}
            data=render_promo(concept,photo,product,
                              editor={"background":"context","_scene_bytes":background})
            with Image.open(io.BytesIO(data)) as picture:
                self.assertEqual(picture.size,(1200,1500))
                self.assertEqual(picture.mode,"RGB")
                outputs.append(data)
        self.assertEqual(len(set(outputs)),3)


if __name__=="__main__":
    unittest.main()
