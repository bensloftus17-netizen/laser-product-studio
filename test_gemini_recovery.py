"""Ensure temporary Gemini outage does not dead-end users or fake AI."""
import unittest
from unittest.mock import patch

import app as studio


class GeminiRecoveryTests(unittest.TestCase):
    def test_helpful_recovery_controls_exist_in_one_gallery(self):
        html=studio.V7_HOME_PAGE
        self.assertIn("data-ai-retry", html)
        self.assertIn("data-ai-fallback", html)
        self.assertIn("Retry AI posters", html)
        self.assertIn("Generate full campaign instead", html)
        self.assertIn("temporarily unavailable", html)
        self.assertIn("'verified manufacturer facts", html)
        self.assertIn("if(retry){$('generateAI').click();return;}", html)
        self.assertIn("if(fallback){$('campaignBtn').click();return;}", html)
        self.assertIn("const temporary=/HTTP 50[0234]", html)
        self.assertIn("const copyBtn=event.target.closest('button[data-ai-copy]')", html)

    def test_ai_outage_stays_an_error_without_forged_model_posters(self):
        product={"part":"9395","title":"Front wheel bearing kit","features":[]}
        with patch.object(studio,"lookup",return_value=(product,b"real-photo")), \
             patch.object(studio,"propose_ai_concepts",side_effect=RuntimeError(
                 "Google Gemini is temporarily unavailable (HTTP 503). Try again shortly.")):
            result=studio.app.test_client().post("/api/ai/concepts/9395",json={})
        self.assertEqual(result.status_code,503)
        self.assertIn("HTTP 503",result.get_json()["error"])
        self.assertNotIn("concepts",result.get_json())

    def test_existing_complete_campaign_fallback_remains_available(self):
        page=studio.V7_HOME_PAGE
        self.assertIn("verified-template-fallback",page)
        self.assertIn("Generate Campaign",page)
        self.assertIn("const response=await fetch('/api/campaign/'",page)


if __name__=="__main__":
    unittest.main()
