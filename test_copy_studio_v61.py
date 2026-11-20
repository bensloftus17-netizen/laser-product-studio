"""V61: French numerical specs stay factual, copy goals are actually different.

Never fabricate prices, fitment, new specifications or AI-authored product
facts when producing British English marketing copy.
"""
from __future__ import annotations

import os
import re
import unittest
from unittest.mock import patch

import app
from english_numeric_specs import translate_known_numeric_labels,normalise_numeric_spec_row
from promo_copy import compose_promotional_copy
from copy_rewriter import (
    GOAL_MODES,SUPPORTED_MODES,AUDIENCES,FOCUSES,rewrite_copy,
)


RAW_7823="Longueur : 120 mm, profondeur interne : 93 mm."
ENGLISH_7823="Length: 120 mm. Internal depth: 93 mm."
PRODUCT={
    "part":"7823",
    "title":"Extra Deep Socket Set 3/8in 5pc",
    "features":[
        RAW_7823,
        # These only appear in the untrusted supplier fragment; every
        # campaign angle must use the single safely converted source fact.
        "Profondeur interne avec un nouveau système garanti.",
    ],
    "description":"Extra deep socket set. "+RAW_7823,
    "specs":{
        "Longueur":"120 mm",
        "Profondeur interne":"93 mm",
        "Workshop":"Verified manufacturer specification",
    },
    "price":None,
}


class EnglishCopyStudioV61Tests(unittest.TestCase):
    def test_exact_screenshot_translates_only_verifiable_measurements(self):
        self.assertTrue(app.is_non_english(RAW_7823))
        self.assertEqual(translate_known_numeric_labels(RAW_7823),ENGLISH_7823)
        self.assertEqual(translate_known_numeric_labels("Longueur: 120 mm."),
                         "Length: 120 mm.")
        self.assertEqual(normalise_numeric_spec_row("Profondeur interne","93 mm"),
                         ("Internal depth","93 mm"))
        self.assertFalse(app.is_non_english(ENGLISH_7823))
        self.assertEqual(translate_known_numeric_labels(
            "Longueur: 120 mm, profondeur interne: fabriqué pour tous."),
            "Longueur: 120 mm, profondeur interne: fabriqué pour tous.")
        self.assertTrue(app.is_non_english(
            "Longueur: 120 mm, profondeur interne: fabriqué pour tous."))

    def test_filter_preserves_raw_source_for_audit_but_only_english_exits(self):
        product=app.normalise_product_language(PRODUCT)
        self.assertIn(RAW_7823,product["source_raw_features"])
        self.assertIn(ENGLISH_7823,product["features"])
        self.assertIn(ENGLISH_7823,product["description"])
        self.assertEqual(product["specs"]["Length"],"120 mm")
        self.assertEqual(product["specs"]["Internal depth"],"93 mm")
        self.assertFalse(any(app.is_non_english(t) for t in product["features"]))
        self.assertNotIn("Profondeur interne",str(product["specs"]))
        self.assertNotIn("garanti",str(product["features"]))

    def test_initial_7823_copy_is_english_for_all_three_angles(self):
        for family in ("trade","retail","premium"):
            copy=compose_promotional_copy(PRODUCT,{
                "family":family,"features":[RAW_7823]})
            for channel in ("social_caption","linkedin_post",
                            "email_body","email_subject"):
                text=copy[channel]
                self.assertNotIn("Longueur",text)
                self.assertNotIn("profondeur interne",text)
                self.assertNotIn("garanti",text)
                if channel!="email_subject":
                    self.assertIn("Length: 120 mm",text)
            self.assertIn("Price on request",copy["linkedin_post"])

    def test_four_distinct_goals_are_channel_aware_and_fact_checked(self):
        outputs={}
        with patch.dict(os.environ,{"GEMINI_API_KEY":""}):
            for mode in ("shorter","hook","evidence","enquiry"):
                item=rewrite_copy(
                    PRODUCT,mode=mode,channel="linkedin_post",
                    angle=0,audience="workshop",
                    current_text="99% off, in French: "+RAW_7823)
                text=item["text"]
                self.assertIn("7823",text)
                self.assertIn("Length: 120 mm",text)
                self.assertIn("Price on request",text)
                self.assertNotIn("Longueur",text)
                self.assertNotIn("99% off",text)
                self.assertIn("#LaserTools",text)
                outputs[mode]=text
        self.assertEqual(len(set(outputs.values())),4)
        self.assertIn("Manufacturer specification",outputs["evidence"])
        self.assertIn("For workshop technicians",outputs["enquiry"])
        self.assertTrue(outputs["hook"].startswith("Length: 120 mm"))

    def test_check_english_uses_official_record_not_dirty_draft(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":""}):
            response=rewrite_copy(
                PRODUCT,mode="english",channel="email_body",
                angle=2,audience="trade",
                current_text=RAW_7823+" Save 50%. Guaranteed for every vehicle.")
        self.assertTrue(response["text"].startswith("Subject:"))
        self.assertIn("Length: 120 mm",response["text"])
        self.assertNotIn("Longueur",response["text"])
        self.assertNotIn("Guaranteed",response["text"])
        self.assertNotIn("50%",response["text"])
        self.assertTrue(response["review_required"])
        self.assertEqual(response["method"],"verified-source")

    def test_selected_channel_cannot_be_overridden_by_writing_goal(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":""}):
            email=rewrite_copy(PRODUCT,mode="hook",channel="email_body",
                               current_text="French copy",angle=1)["text"]
            social=rewrite_copy(PRODUCT,mode="hook",channel="social_caption",
                                current_text="French copy",angle=1)["text"]
            shop=rewrite_copy(PRODUCT,mode="hook",channel="website_listing",
                              current_text="French copy",angle=1)["text"]
        self.assertIn("Subject:",email)
        self.assertIn("Kind regards,",email)
        self.assertNotIn("Subject:",social)
        self.assertNotIn("Subject:",shop)
        self.assertNotIn("#LaserTools",email)

    def test_rewrite_api_rejects_bad_audience_and_unsupported_goal(self):
        client=app.app.test_client()
        with patch.object(app,"lookup") as lookup:
            for extra in ({"audience":"everyone"},
                          {"mode":"unlimited discounts"},
                          {"channel":"invalid"}):
                result=client.post("/api/copy/rewrite/7823",json={
                    "mode":"english","channel":"linkedin_post",
                    "angle":0,"audience":"trade",
                    "current_text":"Old text",**extra})
                self.assertEqual(result.status_code,400,result.get_json())
            lookup.assert_not_called()

    def test_api_works_against_official_product_even_for_french_cached_draft(self):
        with patch.object(app,"lookup",return_value=(PRODUCT,b"")):
            response=app.app.test_client().post(
                "/api/copy/rewrite/7823",json={
                    "mode":"english","channel":"linkedin_post",
                    "angle":0,"audience":"trade",
                    "current_text":RAW_7823})
        self.assertEqual(response.status_code,200,response.get_json())
        text=response.get_json()["text"]
        self.assertIn("Length: 120 mm",text)
        self.assertNotIn("Longueur",text)
        self.assertIn("7823",text)

    def test_interface_removes_redundant_actions_and_groups_channels(self):
        page=app.V7_HOME_PAGE
        for mode in GOAL_MODES:
            self.assertEqual(page.count('data-rewrite-mode="'+mode+'"'),1)
        for old in ("professional","persuasive","technical","facebook"):
            self.assertNotIn('data-rewrite-mode="'+old+'"',page)
        for key in ("campaignCopyAngles","campaignCopyChannels","copyAudience",
                    "campaignCopyText","rewritePreview","rewriteApply",
                    "rewriteUndo","rewriteOptions"):
            self.assertEqual(page.count('id="'+key+'"'),1)
        self.assertIn("Other formats",page)
        self.assertIn("Writing for",page)
        self.assertIn("V64 workshop poster",page)
        self.assertIn("audience:$('copyAudience').value",page)
        self.assertEqual(FOCUSES,("application","price","benefit"))
        self.assertEqual(len(AUDIENCES),3)
        self.assertEqual(len(SUPPORTED_MODES),9)


if __name__=="__main__":
    unittest.main()
