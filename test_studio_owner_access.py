import hashlib
import unittest
from unittest.mock import patch

from app import app


class StudioOwnerAccessTests(unittest.TestCase):
    def test_owner_gate_covers_home_assets_and_api(self):
        digest = hashlib.sha256(b"example-test-password").hexdigest()
        with patch.dict("os.environ", {"RENDER": "true", "STUDIO_OWNER_PASSWORD_SHA256": digest}):
            client = app.test_client()
            for path in ("/", "/static/styles.css", "/api/competitors/9395",
                         "/api/campaign/download/example"):
                response = client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertIn("Basic", response.headers["WWW-Authenticate"])
                self.assertIn("no-store", response.headers["Cache-Control"])
            self.assertEqual(client.get("/", auth=("other", "example-test-password")).status_code, 401)
            self.assertEqual(client.get("/", auth=("ben", "wrong")).status_code, 401)
            self.assertEqual(client.get("/", auth=("ben", "example-test-password")).status_code, 200)
            self.assertEqual(client.post("/api/campaign/start/9395",
                             auth=("ben", "example-test-password"),
                             headers={"Origin": "https://another.example"}).status_code, 403)

    def test_render_fails_closed_when_secret_is_missing(self):
        with patch.dict("os.environ", {"RENDER": "true"}, clear=True):
            client = app.test_client()
            self.assertEqual(client.get("/").status_code, 503)
            self.assertEqual(client.get("/api/health").get_json(), {"ok": True})
