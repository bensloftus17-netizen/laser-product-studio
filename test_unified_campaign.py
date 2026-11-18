"""End-to-end regression tests for one product-aware campaign generator."""
import io
import json
import os
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image, ImageDraw

import app as studio
from campaign_director import ROLES, plan_campaign, third_angle_options
from campaign_hub import build_campaign


def product(part,title,features,source=None,price=None):
    return {
        "part":part, "title":title, "features":features, "specs":{},
        "description":"Manufacturer product information and applications.",
        "price":price, "source":source or "",
    }


def make_png(color, size=(400,320)):
    image=Image.new("RGB",size,color)
    draw=ImageDraw.Draw(image)
    draw.rectangle((45,50,295,275),fill="white",outline="#1A6189",width=7)
    return make_image_png(image)


def make_image_png(image):
    buf=io.BytesIO()
    image.save(buf,"PNG")
    return buf.getvalue()


class UnifiedIntelligentCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.photo=make_png("#DAE4E9")
        cls.workshop=make_png("#D7AD6C")
        branded=Image.new("RGB",(1200,1500),"#0A294B")
        drawing=ImageDraw.Draw(branded)
        drawing.rectangle((64,185,1110,980),fill="#176CA5")
        drawing.polygon([(40,1120),(1080,960),(1140,1400),(100,1440)],fill="#F5C239")
        cls.rrp=make_png("#F5CC3A",size=(1200,1500)) if False else make_image_png(branded)
        cls.scene={"category":"engine","description":"Genuine contextual workshop",
                   "source":"Pexels free commercial-use photo",
                   "page_url":"https://www.pexels.com/photo/8985517/",
                   "license_url":"https://www.pexels.com/license/"}
        cls.timing=product(
            "6200", "Engine Timing Kit - for PSA, Vauxhall/Opel 1.0, 1.2",[
                "Designed to hold camshafts and crankshaft in the timed position.",
                "For specified PSA, Vauxhall and Opel 1.0L and 1.2L engines.",
                "Includes engine locking components supplied in a tin.",
                "To fit a belt see Laser Part No. 8207.",
            ],
            "https://www.toolconnection.co.uk/products/cars-vans/engine-timing-tools/peugeot/"
            "6200-engine-timing-kit-for-psa-vauxhall-opel-1-0-1-2",
            "£101.49 excluding VAT")
        cls.socket=product(
            "9364","Ratchet Set with Comfort Handle 3pc",[
                "Three chrome-vanadium ratchets with comfortable handles.",
                "Ratchets supplied with 1/4, 3/8 and 1/2 inch drives.",
                "Supplied in storage tray.",
            ],"https://www.toolconnection.co.uk/products/general-hand-tools/socketry/"
              "general-ratchets/mixed-sets/9364-ratchet-set-with-comfort-handle-3pc",
            "£99.99 excluding VAT")
        cls.press=product(
            "9372","Air Hydraulic Workshop Press 50 Tonne",[
                "50 tonne pressing capacity.",
                "Air-operated hydraulic workshop press.",
                "Workshop press with reinforced frame.",
            ],"https://www.toolconnection.co.uk/products/workshop/equipment/"
              "hydraulic-press/9372-hydraulic-workshop-press")
        cls.bearing=product(
            "9395","Front Wheel Bearing Kit for Mercedes Sprinter and VW Crafter",[
                "Designed for front wheel bearing removal and installation.",
                "Compatible with specified Sprinter and Crafter models.",
                "Includes extraction and insertion clamshells.",
            ])

    def test_three_required_roles_and_distinct_design_families(self):
        for p in (self.timing,self.socket,self.press,self.bearing):
            with self.subTest(part=p["part"]):
                concepts,plan=plan_campaign(p)
                self.assertEqual(tuple(c["campaign_role"] for c in concepts),ROLES)
                self.assertEqual(tuple(c["family"] for c in concepts),
                                 ("trade","retail","premium"))
                self.assertEqual([c["focus"] for c in concepts[:2]],
                                 ["application","price"])
                self.assertNotEqual(concepts[0]["name"],concepts[1]["name"])
                self.assertNotEqual(concepts[2]["name"],concepts[0]["name"])
                self.assertEqual(len(set(c["family"] for c in concepts)),3)
                self.assertEqual(len({c["visual_plan"]["price_style"] for c in concepts}),3)
                for c in concepts:
                    self.assertTrue(c["headline"])
                    self.assertTrue(all(f in p["features"] for f in c["features"]))
                self.assertIn("manufacturer imagery",plan["reason"].lower())

    def test_bespoke_third_angles_for_real_tool_families(self):
        desired=[
            (self.timing,"kit_contents","engine"),
            (self.socket,"kit_contents","hand_tools"),
            (self.press,"capacity_specs","press"),
            (self.bearing,"workshop_solution","wheel_hub"),
        ]
        for p,third,scene in desired:
            with self.subTest(part=p["part"]):
                concepts,plan=plan_campaign(p)
                self.assertEqual(plan["third_angle"],third)
                self.assertEqual(concepts[2]["visual_plan"]["scene_category"],scene)
                self.assertNotEqual(concepts[0]["selling_point"],
                                    concepts[2]["selling_point"])
        a,_=plan_campaign(self.socket)
        b,_=plan_campaign({**self.socket,"part":"9365"})
        self.assertNotEqual([x["visual_plan"]["scene_index"] for x in a],
                            [x["visual_plan"]["scene_index"] for x in b])

    def test_gemini_choice_is_validated_and_cannot_inject_claims(self):
        p=self.timing
        first={"ai_strategy_choice":{"third_angle":"workshop_solution",
              "new_application":"Guaranteed 100 percent faster",
              "fake_feature":"Works on every PSA car"}}
        planned,metadata=plan_campaign(p,[first])
        self.assertEqual(metadata["selection_method"],"gemini-validated-category-choice")
        self.assertEqual(metadata["third_angle"],"workshop_solution")
        self.assertNotIn("Guaranteed",json.dumps(planned))
        self.assertNotIn("Works on every",json.dumps(planned))
        invalid={"ai_strategy_choice":{"third_angle":"guaranteed-superior"}}
        planned,metadata=plan_campaign(p,[invalid])
        self.assertEqual(metadata["third_angle"],"kit_contents")
        self.assertEqual(metadata["selection_method"],"category-evidence-fallback")
        self.assertNotIn("8207",json.dumps(planned))

    def test_complete_pack_contains_three_unique_posters_and_social_suggestions(self):
        calls=[]
        def price_renderer(concept,photo,product,distributor,editor=None):
            calls.append((concept,editor))
            return self.rrp
        with patch("campaign_hub.find_scene",return_value=(self.workshop,self.scene)) as stock, \
             patch("campaign_hub.render_promo",side_effect=price_renderer):
            pack=build_campaign(self.timing,self.photo,use_gemini=False)
        self.assertEqual(stock.call_count,3)
        manifest=pack["manifest"]
        self.assertEqual(tuple(x["role"] for x in manifest["angles"]),ROLES)
        self.assertEqual([item["id"] for item in manifest["images"][:3]],
                         ["poster_technical","poster_price","poster_smart"])
        self.assertEqual(len(manifest["images"]),8) # 3 posters, 4 channels, 1 QR
        self.assertEqual(len(manifest["social_suggestions"]["instagram_story"]),3)
        self.assertTrue(manifest["scene_photography"])
        self.assertEqual(manifest["generation_method"],"verified-template-fallback")
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0]["campaign_role"],"price_promo")
        self.assertEqual(calls[0][1]["background"],"context")
        self.assertEqual(calls[0][1]["_scene_bytes"],self.workshop)
        self.assertNotEqual(pack["images"]["poster_technical"],pack["images"]["poster_smart"])
        self.assertNotEqual(pack["images"]["poster_smart"],pack["images"]["poster_price"])
        with ZipFile(io.BytesIO(pack["archive"])) as archive:
            names=set(archive.namelist())
            for name in ("01_Posters/01_Application_Technical.png",
                         "01_Posters/02_Price_Promotion.png",
                         "01_Posters/03_Product_Selected.png",
                         "04_Copy/Instagram_Story_Suggestions.txt"):
                self.assertIn(name,names)
            for key in ("poster_technical","poster_price","poster_smart",
                        "social_square","social_story","website_banner","email_header"):
                with Image.open(io.BytesIO(pack["images"][key])) as image:
                    self.assertEqual(image.mode,"RGB")
            story=archive.read("04_Copy/Instagram_Story_Suggestions.txt").decode()
            self.assertIn("Story frame 1",story)
            self.assertIn("camshafts",story.lower())
            self.assertIn("review",story.lower())

    def test_no_verified_price_is_not_made_up(self):
        with patch("campaign_hub.find_scene",return_value=(None,self.scene)), \
             patch("campaign_hub.render_promo",return_value=self.rrp):
            pack=build_campaign({**self.press,"price":None},self.photo,
                                use_gemini=False)
        self.assertIn("ON REQUEST",pack["manifest"]["price"])
        self.assertEqual(pack["manifest"]["angles"][1]["role"],"price_promo")
        self.assertFalse(any("£" in str(v) for v in pack["manifest"]["angles"]))

    def test_one_visible_campaign_button_not_two_generators(self):
        page=studio.V7_HOME_PAGE
        self.assertEqual(page.count('id="campaignBtn"'),1)
        self.assertIn('✦ Build Campaign',page)
        self.assertIn('id="productStudio" hidden',page)
        self.assertIn('id="aiExplore" hidden',page)
        self.assertIn('id="campaignSocialIdeas"',page)
        self.assertIn('id="storySuggestions"',page)
        self.assertIn('poster_technical',page)
        self.assertIn('poster_smart',page)
        self.assertNotIn('Use AI Generator</button>',page)
        self.assertNotIn('Find product &amp; preview standard posters',page)
        self.assertIn("m.social_suggestions",page)


if __name__=="__main__":
    unittest.main()
