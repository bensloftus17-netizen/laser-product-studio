"""Opt-in downloads: generating a campaign must not navigate away on iPhone."""
import time
import unittest

import app as studio


class OptionalCampaignDownloadsTests(unittest.TestCase):
    def test_generation_shows_results_without_programmatically_opening_zip(self):
        page = studio.V7_HOME_PAGE
        start = page.index("$('campaignBtn').addEventListener('click',async()=>{")
        end = page.index("$('distributorBrand').addEventListener('change'", start)
        handler = page[start:end]
        self.assertIn("showCampaign(data)", handler)
        self.assertNotIn("anchor.click()", handler)
        self.assertNotIn("window.location", handler)
        self.assertNotIn("document.createElement('a')", handler)
        self.assertIn("Nothing has downloaded", handler)
        self.assertIn('id="campaignDownload"', page)
        self.assertIn('nothing downloads automatically', page.lower())
        self.assertIn("Download complete ZIP", page)

    def test_gallery_individual_image_download_links(self):
        page = studio.V7_HOME_PAGE
        self.assertIn("campaign-save-image", page)
        self.assertIn("Download PNG", page)
        self.assertIn("campaignAssetUrl(asset.id)+'?download=1", page)

    def test_png_is_inline_for_preview_and_attachment_only_when_requested(self):
        token = "testmobileoptionaldownloadtoken001"
        image = b"fake-png-blob"
        pack = {
            "manifest": {"part": "7411"},
            "images": {"social_square": image},
            "archive": b"test-zip",
        }
        with studio.CAMPAIGN_PACK_LOCK:
            studio.CAMPAIGN_PACKS[token] = {
                "bundle": pack,
                "expires": time.time() + 90,
            }
        try:
            client = studio.app.test_client()
            preview = client.get("/api/campaign/assets/" + token + "/social_square")
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.mimetype, "image/png")
            self.assertIn("inline", preview.headers.get("Content-Disposition", ""))
            self.assertNotIn("attachment", preview.headers.get("Content-Disposition", ""))
            download = client.get("/api/campaign/assets/" + token + "/social_square?download=1")
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download.data, image)
            self.assertIn("attachment", download.headers["Content-Disposition"])
            self.assertIn("LASER_7411_social_square.png", download.headers["Content-Disposition"])
            self.assertIn("no-store", download.headers["Cache-Control"])
            zip_download = client.get("/api/campaign/download/" + token)
            self.assertEqual(zip_download.status_code, 200)
            self.assertIn("attachment", zip_download.headers["Content-Disposition"])
            self.assertEqual(zip_download.mimetype, "application/zip")
        finally:
            with studio.CAMPAIGN_PACK_LOCK:
                studio.CAMPAIGN_PACKS.pop(token, None)


if __name__ == "__main__":
    unittest.main()
