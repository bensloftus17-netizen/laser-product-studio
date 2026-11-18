"""One-click campaign integration tests: no external product or Gemini requests."""
import io
import json
import os
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image, ImageDraw

import app as studio
from campaign_hub import build_campaign, _source_qr


class CampaignHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        photo = Image.new("RGB", (550, 350), "white")
        d = ImageDraw.Draw(photo)
        d.rounded_rectangle((100, 80, 450, 270), radius=30, fill="#194c76")
        data = io.BytesIO()
        photo.save(data, format="PNG")
        cls.photo = data.getvalue()
        cls.product = {
            "part": "9364",
            "title": "Ratchet Set with Comfort Handle 3pc",
            "source": "https://www.toolconnection.co.uk/products/hand-tools/9364-ratchet-set",
            "price": "£101.48 excluding VAT",
            "price_source": "Official UK manufacturer RRP",
            "price_status": "Official UK RRP — check before publishing",
            "description": "Three-piece ratchet set for workshop use.",
            "features": [
                "Three chrome vanadium ratchets with a comfortable handle",
                "1/4 inch ratchet with 72 tooth ratchet mechanism",
                "3/8 inch ratchet with 72 tooth ratchet mechanism",
            ],
            "specs": {"Pieces": "3"},
        }

    @staticmethod
    def sample_poster(*args, **kwargs):
        picture = Image.new("RGB", (1200, 1500), "#0B2948")
        return _png(picture)

    def build(self, product=None, **kwargs):
        with patch("campaign_hub.render_promo", side_effect=self.sample_poster):
            return build_campaign(product or self.product, self.photo,
                                  use_gemini=False, **kwargs)

    def test_complete_zip_includes_all_distinct_channel_assets(self):
        pack = self.build()
        manifest = pack["manifest"]
        self.assertEqual(manifest["generation_method"], "verified-template-fallback")
        self.assertTrue(manifest["review_required"])
        self.assertEqual(len(manifest["angles"]), 3)
        self.assertEqual([x["focus"] for x in manifest["angles"]],
                         ["price", "benefit", "application"])
        expected = {
            "01_Posters/Price-led.png", "01_Posters/Benefit-led.png",
            "01_Posters/Application-led.png",
            "02_Social/Facebook_Instagram_Square.png",
            "02_Social/Instagram_Facebook_Story.png",
            "03_Web_Email/Website_Banner.png",
            "03_Web_Email/Email_Header.png",
            "04_Copy/All_Channels.txt", "04_Copy/All_Channels.json",
            "05_Product_Info/Official_Product_QR.png",
            "05_Product_Info/Campaign_Summary.pdf",
            "05_Product_Info/Marketing_Strategy.txt",
            "05_Product_Info/Source_Record.json",
            "05_Product_Info/READ_FIRST.txt", "Campaign_Manifest.json",
        }
        with ZipFile(io.BytesIO(pack["archive"])) as zip_file:
            self.assertEqual(set(zip_file.namelist()), expected)
            self.assertTrue(zip_file.read("05_Product_Info/Campaign_Summary.pdf").startswith(b"%PDF"))
            self.assertIn(b"SOCIAL MEDIA", zip_file.read("04_Copy/All_Channels.txt"))
            self.assertIn(b"review", zip_file.read("05_Product_Info/READ_FIRST.txt").lower())
            for key, size in [
                ("02_Social/Facebook_Instagram_Square.png", (1080, 1080)),
                ("02_Social/Instagram_Facebook_Story.png", (1080, 1920)),
                ("03_Web_Email/Website_Banner.png", (1600, 600)),
                ("03_Web_Email/Email_Header.png", (1200, 420)),
            ]:
                with Image.open(io.BytesIO(zip_file.read(key))) as image:
                    self.assertEqual(image.size, size)

    def test_only_verified_prices_and_qr_domains(self):
        no_price = {**self.product, "price": None,
                    "source": "https://example.com/anything"}
        pack = self.build(no_price)
        self.assertIn("PRICE ON REQUEST", pack["manifest"]["price"])
        self.assertNotIn("source_qr", pack["images"])
        self.assertIsNone(_source_qr(no_price))
        for copy in pack["manifest"]["copy"]:
            self.assertNotIn("£101.48", json.dumps(copy))
            self.assertIn("Price on request", copy["social_caption"])
        self.assertIn("#LaserTools", pack["manifest"]["copy"][0]["hashtags"])

    def test_missing_manufacturer_photo_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "genuine manufacturer"):
            build_campaign(self.product, None, use_gemini=False)

    def test_one_click_api_and_tokenised_downloads(self):
        with patch.object(studio, "lookup", return_value=(self.product, self.photo)), \
             patch("campaign_hub.render_promo", side_effect=self.sample_poster):
            res = studio.app.test_client().post("/api/campaign/9364",
                json={"distributor_brand": "none"})
        self.assertEqual(res.status_code, 200, res.get_json())
        body = res.get_json()
        token = body["token"]
        self.assertEqual(body["manifest"]["part"], "9364")
        self.assertEqual(len(body["manifest"]["images"]), 8)
        self.assertIn("private", res.headers["Cache-Control"])
        download = studio.app.test_client().get("/api/campaign/download/" + token)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.mimetype, "application/zip")
        preview = studio.app.test_client().get(
            "/api/campaign/assets/" + token + "/social_square"
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.mimetype, "image/png")
        self.assertEqual(studio.app.test_client().get(
            "/api/campaign/assets/" + token + "/not-real").status_code, 404)
        self.assertEqual(studio.app.test_client().get(
            "/api/campaign/download/wrong-token").status_code, 404)

    def test_unreviewed_price_and_unknown_distributor_not_accepted(self):
        with patch.object(studio, "lookup", return_value=(self.product, self.photo)):
            client = studio.app.test_client()
            no_review = client.post("/api/campaign/9364",
                json={"staff_rrp_ex": "55.95", "staff_rrp_reviewed": False})
            self.assertEqual(no_review.status_code, 400)
            unknown = client.post("/api/campaign/9364",
                json={"distributor_brand": "not-a-customer"})
            self.assertEqual(unknown.status_code, 400)

    def test_campaign_ui_selects_and_previews_copy_before_copying(self):
        page = studio.V7_HOME_PAGE
        # The previous card buttons copied immediately without showing wording.
        self.assertNotIn('id="campaignCopies"', page)
        self.assertEqual(page.count('id="campaignCopyText"'), 1)
        self.assertEqual(page.count('id="unifiedCopyStudio"'), 1)
        self.assertNotIn('id="aiCopyText"', page)
        self.assertNotIn('id="aiMarketingCopy"', page)
        self.assertIn("origin:'ai'", page)
        self.assertIn("origin:'campaign'", page)
        self.assertIn('id="campaignCopyAngles"', page)
        self.assertIn('id="campaignCopyChannels"', page)
        self.assertIn('data-campaign-channel="linkedin_post"', page)
        self.assertIn('data-campaign-channel="social_caption"', page)
        self.assertIn('data-campaign-channel="email_body"', page)
        self.assertIn('data-campaign-channel="hashtags"', page)
        self.assertIn('id="campaignCopyCurrent"', page)
        self.assertIn('id="campaignCopyAll"', page)
        self.assertIn('id="campaignCopyReset"', page)
        self.assertIn("renderCampaignCopyStudio()", page)

    def test_one_click_without_gemini_uses_honest_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), \
             patch("campaign_hub.render_promo", side_effect=self.sample_poster):
            result = build_campaign(self.product, self.photo)
        self.assertEqual(result["manifest"]["generation_method"],
                         "verified-template-fallback")
        self.assertTrue(result["manifest"]["warnings"])
        for concept in result["manifest"]["angles"]:
            self.assertTrue(concept["selling_point"])


def _png(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    unittest.main()
