"""V44 creative intelligence, relevant real photography, QA and one-poster editor."""
import io
import json
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from PIL import Image,ImageDraw

import app as studio
from campaign_director import plan_campaign
from campaign_art_quality import photo_relevance,visual_review
from campaign_hub import build_campaign
from poster_live_edit import verified_title_excerpt,edit_campaign_poster
from product_evidence_ranker import choose_verified_fact,rank_product_facts
from promo_scene_library import SCENE_CANDIDATES,classify_product,scene_reference


def png(image):
    out=io.BytesIO()
    image.save(out,"PNG")
    return out.getvalue()


def realish_photo():
    im=Image.new("RGB",(550,430),"white")
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((100,75,400,365),radius=30,fill="#162B40")
    d.ellipse((170,115,330,290),fill="#0D71B5",outline="#A7CEDF",width=8)
    d.ellipse((215,160,285,235),fill="#0D2942",outline="#19A1DA",width=9)
    return png(im)


def dummy_poster(colour="#083057"):
    im=Image.new("RGB",(1200,1500),colour)
    d=ImageDraw.Draw(im)
    d.rectangle((60,190,1140,1060),fill="#168CC9")
    d.polygon([(70,1150),(1130,1080),(1130,1450),(65,1480)],fill="#F7C23C")
    return png(im)


class CampaignCreativeUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.lamp={
            "part":"9476","title":"9476 Multi-Function Work Lamp with Built-In 3 Speed Fan",
            "description":"Verified manufacturer workshop light and fan.",
            "features":[
                "Dimensions: 172 x 69 x 235 mm. Weight: 820 g.",
                "Built-in 3 speed fan with integrated workshop lamp.",
                "Rechargeable work lamp, three lighting modes.",
                "Full details are available on the Laser Tools website.",
            ],
            "specs":{},"price":None,
            "source":"https://www.toolconnection.co.uk/products/workshop/"
                     "inspection-lighting/workshop-lamps/"
                     "9476-multi-function-work-lamp-with-built-in-fan",
        }
        self.ratchet={
            "part":"9365",
            "title":"Stainless Steel High-Quality Ratchet Set 4pc - 50th Anniversary",
            "description":"Stainless-steel ratchets",
            "features":[
                "Set of four stainless-steel ratchets.",
                "1/4 inch drive ratchet with 60 tooth mechanism.",
                "The ratchet set is supplied with a case.",
            ],"specs":{},"price":"£178.00 ex VAT",
            "source":"https://www.toolconnection.co.uk/products/general-hand-tools/"
                     "socketry/general-ratchets/mixed-sets/"
                     "9365-stainless-steel-high-quality-ratchet-set",
        }
        self.photo=realish_photo()

    def test_worklamp_function_beats_weight_or_dimensions(self):
        ranked=rank_product_facts(self.lamp,"technical_application")
        self.assertGreater(ranked[0][0],ranked[-1][0])
        fact=choose_verified_fact(self.lamp,"technical_application")
        self.assertIn("fan",fact.lower())
        smart=choose_verified_fact(self.lamp,"product_selected","performance_specs",
                                    excluded=(fact,))
        self.assertIn("lamp",smart.lower())
        self.assertNotIn("Dimensions:",fact)
        self.assertEqual(classify_product(self.lamp),"lighting")
        concepts,plan=plan_campaign(self.lamp)
        self.assertEqual(concepts[0]["selling_point"],fact)
        self.assertEqual(plan["product_type"],"lighting_inspection")
        self.assertTrue(all(c["selling_point"] in self.lamp["features"]
                            for c in concepts if c["selling_point"]))

    def test_ai_real_art_direction_is_applied_to_correct_role_and_constrained(self):
        models=[
            {"art_direction":{"layout_variant":2,"photo_focus":"left",
                              "graphic_motif":"circles","product_scale":112,
                              "accent":"#13B5EC"}},
            {"art_direction":{"layout_variant":1,"photo_focus":"right",
                              "background_mood":"dramatic","product_scale":118}},
            {"art_direction":{"layout_variant":0,"photo_focus":"centre",
                              "background_mood":"bright","accent":"#FFCB5B"}},
        ]
        concepts,plan=plan_campaign(self.ratchet,models)
        self.assertEqual(concepts[0]["visual_plan"]["art_direction"]["background_mood"],"bright")
        self.assertEqual(concepts[1]["visual_plan"]["preferred_variant"],2)
        self.assertEqual(concepts[1]["visual_plan"]["art_direction"]["photo_focus"],"left")
        self.assertEqual(concepts[2]["visual_plan"]["art_direction"]["product_scale"],118)
        self.assertEqual(concepts[1]["visual_plan"]["creative_source"],"gemini-bounded-art-direction")
        bad=[{"art_direction":{"layout_variant":999,"photo_focus":"arbitrary",
                               "product_scale":100000,"accent":"#00F000"}},
             {},{}]
        plans,_=plan_campaign(self.ratchet,bad)
        art=plans[1]["visual_plan"]["art_direction"]
        self.assertIn(art["layout_variant"],(0,1,2))
        self.assertIn(art["photo_focus"],("left","centre","right"))
        self.assertLessEqual(art["product_scale"],125)
        self.assertNotEqual(plans[1]["visual_plan"]["accent"],"#00F000")

    def test_lighting_real_photo_pool_is_automotive_not_lab(self):
        self.assertIn("lighting",SCENE_CANDIDATES)
        self.assertEqual(len(SCENE_CANDIDATES["lighting"]),3)
        for idx in range(3):
            ref=scene_reference("lighting",idx,family="trade")
            self.assertEqual(ref["category"],"lighting")
            self.assertTrue(any(word in ref["description"].lower()
                                for word in ("mechanic","vehicle","garage","automotive","technician")))
            self.assertEqual(ref["source"],"Pexels free commercial-use photo")
            self.assertTrue(photo_relevance(self.lamp,"lighting",ref)["supported"])
        bad={"category":"diagnostic","source":"Pexels free commercial-use photo"}
        self.assertFalse(photo_relevance(self.lamp,"lighting",bad)["supported"])
        official={"category":"lighting","source":"Official manufacturer application photo"}
        self.assertEqual(photo_relevance(self.lamp,"lighting",official)["score"],100)

    def test_qa_rejects_tiny_product_or_missing_headline(self):
        pic=dummy_poster()
        self.assertFalse(visual_review(pic,"product_selected",text_status={
            "product_visible_fraction":.005})["passed"])
        self.assertFalse(visual_review(pic,"product_selected",text_status={
            "missing_headline":True})["passed"])
        self.assertTrue(visual_review(pic,"product_selected",text_status={
            "product_visible_fraction":.14,"missing_headline":False})["passed"])

    def make_pack(self):
        source={"category":"hand_tools","source":"Pexels free commercial-use photo",
                "description":"Mechanic using ratchet in workshop","page_url":"https://www.pexels.com/photo/3855334/",
                "license_url":"https://www.pexels.com/license/"}
        mock_report={"passed":True,"score":89,"variation":1,"candidates_checked":3,
                     "rejected_candidates":0,"warnings":[]}
        with patch("campaign_hub.choose_best",return_value=(dummy_poster(),mock_report)), \
             patch("campaign_hub.find_scene",return_value=(dummy_poster(),source)), \
             patch("campaign_hub.render_promo",return_value=dummy_poster()):
            return build_campaign(self.ratchet,self.photo,use_gemini=False)

    def test_single_poster_editor_keeps_original_product_and_zip_consistent(self):
        pack=self.make_pack()
        base=pack["images"]["poster_smart"]
        with ZipFile(io.BytesIO(pack["archive"])) as original:
            before=original.read("01_Posters/01_Application_Technical.png")
        revised=dummy_poster("#245778")
        with patch("poster_live_edit.choose_best",return_value=(
            revised,{"passed":True,"variation":2,"candidates_checked":1,"score":94,"warnings":[]})):
            result=edit_campaign_poster(pack,"poster_technical",{
                "headline":"Ratchet Set 4pc","feature_index":1,"layout_variant":2})
        self.assertEqual(result["revision"],1)
        self.assertEqual(pack["images"]["poster_technical"],revised)
        self.assertEqual(pack["images"]["poster_smart"],base)
        self.assertEqual(pack["manifest"]["angles"][0]["headline"],"Ratchet Set 4pc")
        self.assertEqual(pack["manifest"]["angles"][0]["selling_point"],self.ratchet["features"][1])
        self.assertEqual(pack["manifest"]["artwork_quality"]["poster_technical"]["variation"],2)
        with ZipFile(io.BytesIO(pack["archive"])) as edited:
            self.assertNotEqual(before,edited.read("01_Posters/01_Application_Technical.png"))
            self.assertEqual(edited.read("01_Posters/01_Application_Technical.png"),revised)
            self.assertEqual(edited.read("01_Posters/03_Product_Selected.png"),base)
            meta=json.loads(edited.read("Campaign_Manifest.json"))
            self.assertEqual(meta["poster_revision"],1)
            self.assertIn(b"%PDF",edited.read("05_Product_Info/Campaign_Summary.pdf")[:16])

    def test_editor_rejects_invented_headline_and_unverified_features(self):
        self.assertEqual(verified_title_excerpt(self.ratchet["title"],"Ratchet Set 4pc"),
                         "Ratchet Set 4pc")
        for bad in ("GUARANTEED 50% FASTER","Works on any vehicle","","£50 discount"):
            with self.assertRaises(ValueError):
                verified_title_excerpt(self.ratchet["title"],bad)
        pack=self.make_pack()
        original=pack["archive"]
        for bad in (
            {"headline":"Guaranteed savings","feature_index":0,"layout_variant":1},
            {"headline":"Ratchet Set 4pc","feature_index":999,"layout_variant":1},
            {"headline":"Ratchet Set 4pc","feature_index":True,"layout_variant":1},
            {"headline":"Ratchet Set 4pc","feature_index":1,"layout_variant":9},
        ):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                edit_campaign_poster(pack,"poster_technical",bad)
        self.assertEqual(pack["archive"],original)
        self.assertNotIn("editor_context",pack["manifest"])

    def test_api_editor_and_ui_controls_are_real_not_placeholder(self):
        pack=self.make_pack()
        token="V"*28
        studio.CAMPAIGN_PACKS[token]={"expires":time.time()+120,"bundle":pack}
        try:
            with patch("poster_live_edit.choose_best",return_value=(
                dummy_poster("#356C91"),
                {"passed":True,"variation":0,"score":94,"candidates_checked":1,"warnings":[]})):
                reply=studio.app.test_client().post(
                    "/api/campaign/edit/"+token+"/poster_smart",
                    json={"headline":"Ratchet Set 4pc","feature_index":0,"layout_variant":0})
            self.assertEqual(reply.status_code,200,reply.data[:300])
            self.assertEqual(reply.get_json()["asset_id"],"poster_smart")
            denied=studio.app.test_client().post(
                "/api/campaign/edit/"+token+"/social_square",
                json={"headline":"Ratchet Set 4pc","feature_index":0,"layout_variant":0})
            self.assertEqual(denied.status_code,400)
            self.assertEqual(studio.app.test_client().post(
                "/api/campaign/edit/"+"M"*28+"/poster_price",
                json={"headline":"Ratchet Set 4pc","feature_index":0,"layout_variant":0}
            ).status_code,404)
        finally:
            studio.CAMPAIGN_PACKS.pop(token,None)
        page=studio.V7_HOME_PAGE
        for marker in ('id="campaignPosterEditor"','id="posterEditSave"',
                       'data-edit-poster','static/campaign_poster_edit.js'):
            self.assertIn(marker,page)
        self.assertNotIn("editor_context",json.dumps(pack["manifest"]))
