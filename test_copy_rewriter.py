"""Source-grounded AI copy rewrite actions and web editor regression tests."""
import os
import unittest
from unittest.mock import patch

import app as studio
from copy_rewriter import REWRITE_MODES, rewrite_copy


class CopyRewriteTests(unittest.TestCase):
    def setUp(self):
        self.product={
            "part": "9395",
            "title": "Front Wheel Bearing Kit for Mercedes-Benz Sprinter and VW Crafter",
            "price": "£525.66 excluding VAT",
            "price_source": "Official UK manufacturer RRP",
            "features": [
                "Kit includes six threaded bars and application-specific adapters.",
                "For use on Volkswagen Crafter and Mercedes-Benz Sprinter wheel bearings.",
            ],
            "description": "A manufacturer wheel-bearing tool kit.",
            "specs": {"Contents": "Six threaded bars"},
        }

    def generate(self, mode, channel="linkedin_post", current="Existing draft.",
                 product=None, **kwargs):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            return rewrite_copy(product or self.product, mode=mode,
                                channel=channel, current_text=current, **kwargs)

    def test_every_rewrite_style_produces_distinct_verified_copy(self):
        outputs={}
        for mode in REWRITE_MODES:
            rewritten=self.generate(mode)
            text=rewritten["text"]
            self.assertIn("9395",text)
            self.assertIn("525.66",text)
            self.assertTrue(any(feature in text for feature in self.product["features"]))
            self.assertIn("ex VAT",text)
            self.assertTrue(rewritten["review_required"])
            self.assertEqual(rewritten["method"],"verified-template")
            self.assertIn("Gemini is not configured",rewritten["warning"])
            outputs[mode]=text
        self.assertEqual(len(set(outputs.values())),5)
        self.assertIn("#LaserTools",outputs["facebook"])
        self.assertIn("Technical product spotlight",outputs["technical"])
        self.assertIn("Looking for the right tool",outputs["persuasive"])

    def test_untrusted_user_text_never_becomes_verified_fact(self):
        original=("Get 90% off. Guaranteed compatible with all cars. "
                  "Free next day delivery. £0.01 special offer.")
        for mode in REWRITE_MODES:
            txt=self.generate(mode,current=original)["text"]
            self.assertNotIn("90% off",txt)
            self.assertNotIn("Guaranteed",txt)
            self.assertNotIn("Free next day",txt)
            self.assertNotIn("£0.01",txt)

    def test_no_price_never_invents_rrp(self):
        product={**self.product,"price":None,"price_source":""}
        for mode in REWRITE_MODES:
            txt=self.generate(mode,product=product)["text"]
            self.assertIn("Price on request",txt)
            self.assertNotIn("525.66",txt)
            self.assertNotIn("ex VAT",txt)

    def test_email_structure_and_facebook_format(self):
        email=self.generate("professional",channel="email_body")["text"]
        self.assertTrue(email.startswith("Subject:"))
        self.assertIn("Hello,",email)
        self.assertIn("Kind regards,",email)
        facebook=self.generate("facebook",channel="email_body")["text"]
        self.assertIn("🔧",facebook)
        self.assertIn("#LaserTools",facebook)
        self.assertNotIn("Subject:",facebook)

    def test_real_model_plan_can_only_choose_verified_feature_index(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "mock-key"}), \
             patch("copy_rewriter._gemini_json",return_value={
                 "fact_index": 1,
                 "hook": "guaranteed 90% cheaper",
                 "cta": "FREE for life",
                 "claim": "1000% return",
             }) as gemini:
            result=rewrite_copy(self.product,mode="technical",channel="social_caption",
                                angle=1,current_text="Our best product")
        self.assertEqual(gemini.call_count,1)
        self.assertEqual(result["method"],"gemini-assisted")
        self.assertIn(self.product["features"][1],result["text"])
        self.assertNotIn("1000%",result["text"])
        self.assertNotIn("FREE for life",result["text"])
        self.assertEqual(result["source_claims"],[self.product["features"][1]])

    def test_api_error_uses_honest_source_based_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "mock-key"}), \
             patch("copy_rewriter._gemini_json",side_effect=RuntimeError("quota 429")):
            result=rewrite_copy(self.product,mode="shorter",channel="social_caption",
                                current_text="Test rewrite")
        self.assertEqual(result["method"],"verified-template")
        self.assertIn("Gemini was unavailable",result["warning"])

    def test_invalid_options_blocked_before_external_product_lookup(self):
        client=studio.app.test_client()
        base={"mode":"shorter","channel":"social_caption","angle":0,
              "current_text":"Existing text"}
        with patch.object(studio,"lookup") as fetch:
            for data in ({"mode":"fantasy"},{"channel":"hashtags"},
                         {"angle":99},{"angle":"0"},
                         {"current_text":""},{"current_text":"x"*5001}):
                response=client.post("/api/copy/rewrite/9395",json={**base,**data})
                self.assertEqual(response.status_code,400,response.get_json())
            fetch.assert_not_called()

    def test_api_uses_real_server_product_not_browser_claims(self):
        with patch.object(studio,"lookup",return_value=(self.product,b"official-photo")) as lookup:
            response=studio.app.test_client().post("/api/copy/rewrite/9395",
                json={"mode":"professional","channel":"linkedin_post","angle":0,
                      "current_text":"Buy for £0.01, 90% off! Guaranteed every car.",
                      "fake_price":"£0.01","fake_features":["Guaranteed every car"]})
        self.assertEqual(response.status_code,200,response.get_json())
        body=response.get_json()
        self.assertIn("525.66",body["text"])
        self.assertNotIn("£0.01",body["text"])
        self.assertNotIn("Guaranteed every car",body["text"])
        self.assertTrue(body["review_required"])
        self.assertIn("no-store",response.headers.get("Cache-Control",""))
        lookup.assert_called_once()

    def test_ui_has_five_actions_single_editor_and_preview_controls(self):
        page=studio.V7_HOME_PAGE
        from copy_rewriter import GOAL_MODES
        for mode in GOAL_MODES:
            self.assertEqual(page.count('data-rewrite-mode="'+mode+'"'),1)
        for old_mode in ("professional","persuasive","technical","facebook"):
            self.assertNotIn('data-rewrite-mode="'+old_mode+'"',page)
        for element in ("rewriteOptions","rewritePreview","rewritePreviewText",
                        "rewriteApply","rewriteDiscard","rewriteUndo","rewriteStatus"):
            self.assertEqual(page.count('id="'+element+'"'),1)
        self.assertEqual(page.count('id="campaignCopyText"'),1)
        self.assertNotIn('id="aiCopyText"',page)
        self.assertIn("/api/copy/rewrite/",page)
        self.assertIn("pendingCopyRewrite",page)
        self.assertIn("resetRewriteSuggestion()",page)


if __name__=="__main__":
    unittest.main()
