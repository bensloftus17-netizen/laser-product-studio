import base64
import io
import json
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from ai_workbench_hero import SIZE, MARKER, generate_workbench_hero


class WorkbenchHeroTests(unittest.TestCase):
    def test_reviewed_scene_is_bounded_and_returned_only_on_positive_match(self):
        image = io.BytesIO()
        Image.new("RGB", (960, 540), "#56667a").save(image, "JPEG")
        jpeg = image.getvalue()
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [json.dumps({"candidates": [
            {"content": {"parts": [{"inlineData": {
                "data": base64.b64encode(jpeg).decode("ascii")}}]}}]
        }).encode()]
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fixture", "STUDIO_AI_WORKBENCH": "true"}), \
             patch("ai_workbench_hero.requests.post", return_value=response) as post, \
             patch("ai_concepts._gemini_json", side_effect=[{"matches": True}, {"matches": False}]):
            hero = generate_workbench_hero({"title": "3pc ratchet set"}, jpeg, jpeg)
            self.assertTrue(hero.startswith(MARKER))
            with Image.open(io.BytesIO(hero[len(MARKER):])) as result:
                self.assertEqual(result.size, SIZE)
            self.assertEqual(post.call_args.kwargs["json"]["generationConfig"]["responseModalities"],
                             ["IMAGE"])
            self.assertIsNone(generate_workbench_hero({"title": "3pc ratchet set"}, jpeg, jpeg))

    def test_disabled_feature_makes_no_provider_calls(self):
        with patch.dict("os.environ", {"STUDIO_AI_WORKBENCH": "false"}), \
             patch("ai_workbench_hero.requests.post") as post:
            self.assertIsNone(generate_workbench_hero({}, b"", b""))
        post.assert_not_called()
