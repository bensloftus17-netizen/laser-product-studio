"""AI promotional copy: one Gemini call, factual channel drafts and copy UI."""
import io
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

import app as studio
from promo_copy import compose_promotional_copy,normalise_copy_direction


class PromotionalCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        im=Image.new("RGB",(380,250),"white")
        ImageDraw.Draw(im).rounded_rectangle((55,35,330,220),radius=17,
                                             fill="#183F67")
        buffer=io.BytesIO();im.save(buffer,format="PNG")
        cls.photo=buffer.getvalue()
        cls.product={
            "part":"8899","title":"Ball Joint Separator for Land Rover / Jaguar",
            "price":"£144.16 excluding VAT",
            "price_source":"Official UK manufacturer",
            "features":[
                "Heavy-duty scissor-type mechanism provides controlled separation.",
                "Applications include Land Rover and Jaguar suspension ball joints."
            ],
            "description":"Tool for servicing ball joints.",
            "specs":{}
        }
        cls.concepts=[
            {"part":"8899","title":cls.product["title"],
             "family":family,"id":i,"variant":0,"name":"Campaign",
             "headline":"Ball Joint Separator for JLR",
             "subline":"Suspension tools","angle":"Workshop application",
             "features":[cls.product["features"][0]],
             "copy_direction":{"tone":tone,"hook":"feature","cta":"details"}}
            for i,(family,tone) in enumerate((
                ("retail","direct"),("premium","practical"),("trade","professional")))
        ]

    def test_four_channels_and_hashtags_use_exact_verified_facts(self):
        for concept in self.concepts:
            copy=compose_promotional_copy(self.product,concept)
            for item in ("social_caption","linkedin_post","email_subject",
                         "email_body","hashtags"):
                self.assertTrue(copy[item],(concept["family"],item))
            self.assertIn("8899",copy["social_caption"])
            self.assertIn("144.16",copy["linkedin_post"])
            self.assertIn("ex VAT",copy["email_body"])
            self.assertEqual(copy["hashtags"][0],"#LaserTools")
            self.assertIn("#LandRover",copy["hashtags"])
            self.assertEqual(copy["review_required"],True)
            self.assertNotIn("Save £",str(copy))

    def test_poster_families_create_distinct_social_and_linkedin_drafts(self):
        copies=[compose_promotional_copy(self.product,c) for c in self.concepts]
        self.assertEqual(len({c["social_caption"] for c in copies}),3)
        self.assertEqual(len({c["linkedin_post"] for c in copies}),3)
        self.assertEqual([c["focus"] for c in copies],
                         ["price","benefit","application"])

    def test_missing_price_never_invents_amount_or_vat(self):
        copy=compose_promotional_copy({**self.product,"price":None},
                                      self.concepts[0])
        self.assertIn("Price on request",copy["social_caption"])
        self.assertNotIn("144.16",str(copy))
        self.assertNotIn("ex VAT",str(copy))
        self.assertNotIn("inc VAT",str(copy))

    def test_reviewed_staff_price_clearly_marked_draft(self):
        copy=compose_promotional_copy({
            **self.product,"price":"£79.99 including VAT",
            "price_source":"Staff entry, independently reviewed"},self.concepts[0])
        self.assertIn("Draft Uk Rrp: £79.99 (inc VAT)",copy["social_caption"])
        self.assertNotIn("144.16",str(copy))

    def test_malicious_or_invented_model_claims_are_not_repeated(self):
        fake={**self.concepts[2],
              "features":["Guaranteed compatible with every BMW ever made"],
              "headline":"Massive 90% off this tool",
              "copy_direction":{"tone":"exaggerated","hook":"fake_claim",
                                "cta":"buy_now_at_unknown_url"}}
        copy=compose_promotional_copy(self.product,fake)
        all_text=str(copy)
        self.assertNotIn("90% off",all_text)
        self.assertNotIn("Guaranteed compatible",all_text)
        self.assertNotIn("BMW",all_text)
        self.assertNotIn("buy_now_at_unknown_url",all_text)
        self.assertEqual(normalise_copy_direction(fake["copy_direction"]),
                         {"tone":"professional","hook":"product","cta":"details"})

    def test_no_unverified_vehicle_hashtags(self):
        p={"title":"Workshop Ratchet Set 3pc","part":"9364",
           "features":["Three different drive sizes"],"price":None}
        c=compose_promotional_copy(p,{"family":"trade","features":[]})
        self.assertIn("#HandTools",c["hashtags"])
        self.assertNotIn("#Ford",c["hashtags"])
        self.assertNotIn("#LandRover",c["hashtags"])

    def test_generation_route_attaches_copy_without_extra_model_call(self):
        originals=[dict(c) for c in self.concepts]
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"propose_ai_concepts",return_value=originals) as gemini, \
             patch.object(studio,"find_scene",return_value=(None,{"category":"suspension",
                  "source":"No external photograph used","description":"none"})), \
             patch.object(studio,"render_ai_promo",return_value=b"fake-png"):
            response=studio.app.test_client().post("/api/ai/concepts/8899",
                                                    json={"distributor_brand":"none"})
        self.assertEqual(response.status_code,200,response.get_json())
        concepts=response.get_json()["concepts"]
        self.assertEqual(len(concepts),3)
        self.assertEqual(gemini.call_count,1)
        self.assertEqual(len({c["marketing_copy"]["focus"] for c in concepts}),3)
        self.assertTrue(all(len(c["marketing_copy"]["hashtags"])>=3 for c in concepts))

    def test_editor_refreshes_copy_from_verified_record_not_forged_data(self):
        c=self.concepts[0].copy()
        c["marketing_copy"]={"social_caption":"Save £9999! Free tools."}
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"render_ai_promo",return_value=b"fake-png"):
            response=studio.app.test_client().post("/api/ai/edit/8899",json={
                "index":0,"concept":c,"distributor_brand":"none",
                "edits":{"headline":"Ball Joint Separator","palette":0,
                         "background":"clean","price_position":"standard",
                         "accent":"#F6D343","background_colour":"#056DB9"}})
        self.assertEqual(response.status_code,200,response.get_json())
        copy=response.get_json()["concept"]["marketing_copy"]
        self.assertNotIn("Save £9999",str(copy))
        self.assertIn("8899",copy["email_subject"])
        self.assertIn("ex VAT",copy["email_body"])

    def test_browser_copy_tabs_buttons_and_javascript_syntax(self):
        html=studio.V7_HOME_PAGE
        for control in ("aiMarketingCopy","aiCopyDesignTabs","aiCopyChannels",
                        "aiCopyText","aiCopyCurrent","aiCopyAll","aiCopyStatus"):
            self.assertIn('id="'+control+'"',html)
        self.assertIn("function renderAiMarketingCopy()",html)
        self.assertIn("navigator.clipboard.writeText",html)
        self.assertIn("data-ai-copy",html)
        if shutil.which("node"):
            script=re.search(r"<script>(.*?)</script>",html,re.S).group(1)
            checked=subprocess.run(["node","--check"],input=script,
                                   capture_output=True,text=True,timeout=10)
            self.assertEqual(checked.returncode,0,checked.stderr)


if __name__=="__main__":
    unittest.main()
