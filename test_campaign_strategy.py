"""Real product-specific marketing strategy, constrained AI selections and tests."""
import io
import json
import os
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image
import app as studio
from campaign_strategy import explain_strategy, strategy_options
from marketing_intelligence import detect_category
from ai_concepts import propose
from campaign_hub import build_campaign


def demo_product(part, title, facts, price=None):
    return {
        "part": part, "title": title,
        "description": "Manufacturer product details for the relevant workshop tool.",
        "features": list(facts), "specs": {},
        "price": price, "source": "https://www.toolconnection.co.uk/products/" + part,
    }


class IntelligentMarketingStrategyTests(unittest.TestCase):
    def setUp(self):
        self.bearing = demo_product(
            "9395", "Front Wheel Bearing Kit for Mercedes-Benz Sprinter and VW Crafter",
            ["For the removal and installation of front wheel bearings on specified "
             "Mercedes-Benz Sprinter and VW Crafter vehicles.",
             "Kit includes extraction and insertion clamshells."], None)
        self.socket = demo_product(
            "9364", "3 Piece Ratchet Set",
            ["Set includes three ratchets with verified drive sizes.",
             "Comfortable handle design with 72-tooth ratchet mechanism."], "£99 ex VAT")
        self.press = demo_product(
            "9372", "Hydraulic Workshop Press",
            ["Workshop press for controlled pressing applications.",
             "Supplied with a hydraulic ram and workshop frame."], None)

    def test_different_tool_types_get_different_audiences_and_channels(self):
        strategies = [explain_strategy(p) for p in
                      (self.bearing, self.socket, self.press)]
        self.assertEqual([x["category"] for x in strategies],
                         ["bearing_suspension", "socket_ratchet", "workshop_press"])
        self.assertEqual(len(set(x["target_audience"] for x in strategies)), 3)
        self.assertEqual(
            [x["primary_focus"] for x in strategies],
            ["application", "benefit", "benefit"])
        self.assertEqual(strategies[0]["recommended_channels"][0]["id"], "email")
        self.assertEqual(strategies[1]["recommended_channels"][0]["id"], "social")
        self.assertEqual(strategies[2]["recommended_channels"][1]["id"], "website")
        self.assertTrue(all(x["review_required"] for x in strategies))
        self.assertTrue(all(x["method"] == "category-rules-fallback" for x in strategies))

    def test_model_can_select_only_validated_audience_focus_channels_and_fact(self):
        options = strategy_options(self.bearing)
        self.assertEqual(options["category"], "bearing_suspension")
        self.assertEqual(options["category_evidence"], "product title")
        proposed = {
            "audience_id": "vehicle_specialists",
            "primary_focus": "benefit",
            "channels": ["website", "social"],
            "proof_index": 1,
            "extra_claim": "Guaranteed 70% faster than competition",
            "audience_reason": "Proven to purchase 10000 kits",
        }
        result = explain_strategy(self.bearing, proposed)
        self.assertEqual(result["method"], "gemini-validated-choice")
        self.assertEqual(result["audience_id"], "vehicle_specialists")
        self.assertEqual(result["primary_focus"], "benefit")
        self.assertEqual([x["id"] for x in result["recommended_channels"]],
                         ["website", "social"])
        self.assertEqual(result["proof_point"], self.bearing["features"][1])
        self.assertNotIn("70%", json.dumps(result))
        self.assertNotIn("10000", json.dumps(result))

    def test_invalid_or_forged_model_choices_cannot_enter_strategy(self):
        proposals = [
            {"audience_id": "Fake lead 123", "primary_focus": "free giveaway",
             "channels": ["instagram_spam", "guaranteed_orders"], "proof_index": 987},
            {"audience_id": [], "primary_focus": ["price"],
             "channels": [{"id":"social"}, "social"], "proof_index": False},
            {"audience_id": "commercial_workshops", "primary_focus": "application",
             "channels": ["email", "email"], "proof_index": 0},
        ]
        for bad in proposals:
            with self.subTest(bad=bad):
                result = explain_strategy(self.bearing, bad)
                self.assertEqual(result["method"], "category-rules-fallback")
                self.assertEqual(result["target_audience"], "Commercial-vehicle repair workshops")
                self.assertIn(result["proof_point"], self.bearing["features"])
                self.assertNotIn("guaranteed_orders", json.dumps(result))

    def test_missing_price_is_never_made_price_led_by_model(self):
        proposal = {"audience_id": "commercial_workshops", "primary_focus": "price",
                    "channels": ["email", "social"], "proof_index": 0}
        strategy = explain_strategy(self.bearing, proposal)
        self.assertEqual(strategy["method"], "gemini-validated-choice")
        self.assertEqual(strategy["primary_focus"], "benefit")

    def test_gemini_existing_concept_call_carries_bounded_strategy_no_second_call(self):
        product = self.bearing
        raw = {"concepts": [
            {"headline": "Front wheel bearing kit", "name": "Retail",
             "subline": "For approved workshop applications", "feature_ids": [0]},
            {"headline": "Extraction and insertion kit", "name": "Premium",
             "subline": "Includes clamshells", "feature_ids": [1]},
            {"headline": "Mercedes and VW bearing service", "name": "Trade",
             "subline": "For confirmed applications", "feature_ids": [0]},
        ], "marketing_strategy": {
            "audience_id": "vehicle_specialists",
            "primary_focus": "application",
            "channels": ["email", "linkedin"],
            "proof_index": 0,
        }}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "mock-token"}), \
             patch("ai_concepts._gemini_json", return_value=raw) as model:
            concepts = propose(product)
        self.assertEqual(model.call_count, 1)
        payload = model.call_args.args[0]
        context = json.loads(payload["contents"][0]["parts"][0]["text"])
        self.assertIn("strategy_options", context)
        self.assertEqual(context["strategy_options"]["category"], "bearing_suspension")
        self.assertEqual(concepts[0]["ai_strategy_choice"]["audience_id"], "vehicle_specialists")
        self.assertEqual([c["family"] for c in concepts], ["retail", "premium", "trade"])

    def test_pack_stores_and_uses_model_strategy_for_actual_graphics(self):
        photo = Image.new("RGB", (160, 120), "white")
        from PIL import ImageDraw
        pencil=ImageDraw.Draw(photo)
        pencil.rounded_rectangle((29,28,135,91),radius=9,fill="#384F61")
        pencil.ellipse((39,35,65,62),fill="#A5B8C6")
        buf = io.BytesIO()
        photo.save(buf, "PNG")
        fake = Image.new("RGB", (1200, 1500), "#102B4C")
        d=__import__("PIL.ImageDraw",fromlist=["Draw"]).Draw(fake)
        d.rectangle((50,180,1120,950),fill="#1386C0")
        d.rectangle((100,1060,1040,1400),fill="#F5C241")
        out = io.BytesIO()
        fake.save(out, "PNG")
        images = out.getvalue()
        concepts = [
            {"focus":"price","headline":"Price-led", "selling_point":"Price on request"},
            {"focus":"benefit","headline":"Benefit-led", "selling_point":self.bearing["features"][1]},
            {"focus":"application","headline":"Application-led", "selling_point":self.bearing["features"][0]},
        ]
        concepts[0]["ai_strategy_choice"] = {
            "audience_id":"vehicle_specialists", "primary_focus":"benefit",
            "channels":["website","social"],"proof_index":1,
        }
        with patch("campaign_hub._concepts",return_value=(concepts, "gemini-assisted", [])), \
             patch("campaign_hub.render_promo",return_value=images), \
             patch("campaign_hub._native_graphic",return_value=images) as native, \
             patch("campaign_hub.find_scene",return_value=(None,{})):
            pack = build_campaign(self.bearing,buf.getvalue())
        strategy = pack["manifest"]["marketing_strategy"]
        self.assertEqual(strategy["method"], "gemini-validated-choice")
        self.assertEqual(strategy["proof_point"], self.bearing["features"][1])
        # V57 makes the six graphics inherit three distinct poster
        # narratives instead of pasting one global strategy proof six times.
        parents=pack["manifest"]["creative_plan"]["format_parent_roles"]
        self.assertEqual(set(parents.values()),{
            "technical_application","price_promo","product_selected"})
        roles={a["role"]:a for a in pack["manifest"]["angles"]}
        self.assertEqual(len(native.call_args_list),6)
        for call in native.call_args_list:
            kind=call.args[3]
            expected=roles[parents[kind]]["selling_point"]
            self.assertEqual(call.args[4],expected)
        with ZipFile(io.BytesIO(pack["archive"])) as z:
            note=z.read("05_Product_Info/Marketing_Strategy.txt").decode("utf-8")
            self.assertIn("vehicle specialists", strategy["target_audience"].lower())
            self.assertIn("website",note.lower())
            self.assertIn("not a validated prospect",note.lower())
            self.assertEqual(json.loads(z.read("Campaign_Manifest.json"))["marketing_strategy"],
                             strategy)

    def test_dashboard_visible_strategy_is_not_fake_prospect_data(self):
        page=studio.V7_HOME_PAGE
        self.assertEqual(page.count('id="marketingStrategyPanel"'),1)
        for name in ("strategyAudience","strategyChannels","strategyProof",
                     "strategyReason","strategyMethod","strategyFocus"):
            self.assertEqual(page.count('id="'+name+'"'),1)
        self.assertIn("strategy=m.marketing_strategy",page)
        self.assertIn("marketing-strategy-panel",page)
        self.assertIn("Audience and channel recommendations are marketing hypotheses",page)


if __name__ == "__main__":
    unittest.main()
