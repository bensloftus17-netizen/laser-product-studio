"""Laser 6200 is an engine timing kit, not a general hand tool.

Keep manufacturer facts distinct from sales suggestions and accessories.
"""
import unittest

from marketing_intelligence import (detect_category, strategy_for,
                                    rank_verified_features)
from campaign_strategy import explain_strategy, strategy_options
from promo_selling_points import choose_feature, focus_concept


class EngineTimingCategoryTests(unittest.TestCase):
    def setUp(self):
        self.product={
            "part": "6200",
            "title": "Engine Timing Kit - for PSA, Vauxhall/Opel 1.0, 1.2",
            "description": "Designed to hold the camshafts and crankshaft in their timed position during belt replacement on Citroën, DS, Peugeot and Vauxhall/Opel EB0 and EB2 1.0L and 1.2L 3 cylinder engines.",
            "features": [
                "Designed to hold the camshafts and crankshaft in their timed position during belt replacement.",
                "Applications include: Citroën, DS, Peugeot and Vauxhall/Opel models.",
                "Designed for the Citroën, DS, Peugeot and Vauxhall/Opel EB0 and EB2 1.0 & 1.2L 3 cylinder engines.",
                "To refit the water pump belt use stretchy belt installation tool, Laser Part No. 7595. for Timing Belt Checking Gauge, see Part No. 8207.",
                "Packed in EVA foam in a metal tin. Made in Sheffield.",
            ],
            "price": "£238.01 plus VAT",
            "specs": {"Application": "EB0 and EB2 engines"},
            "source": "https://www.toolconnection.co.uk/products/cars-vans/engine-timing-tools/peugeot/6200-engine-timing-kit-for-psa-vauxhall-opel-1-0-1-2",
        }

    def test_6200_classifies_as_engine_timing_not_hand_tools(self):
        category,evidence=detect_category(self.product)
        self.assertEqual(category,"engine_timing")
        self.assertEqual(evidence,"product title")
        direction=strategy_for(self.product)
        self.assertEqual(direction["category_label"],"Engine timing & locking tools")
        self.assertEqual(direction["technical_preference"],"dense")

    def test_related_tools_are_not_featured_as_primary_sales_claim(self):
        source_feature=self.product["features"][3]
        ranked=rank_verified_features(self.product)
        self.assertTrue(ranked)
        self.assertNotIn(source_feature,ranked)
        for focus in ("price","benefit","application"):
            chosen=choose_feature(self.product,focus)
            self.assertIn(chosen,self.product["features"])
            self.assertNotIn("7595",chosen)
            self.assertNotIn("8207",chosen)
        trade=focus_concept(self.product,{"family":"trade","headline":"Engine Timing Kit"},2)
        self.assertNotIn("7595",trade["selling_point"])
        self.assertIn(trade["selling_point"],self.product["features"])

    def test_marketing_strategy_targets_engine_workshops_and_real_application(self):
        result=explain_strategy(self.product)
        self.assertEqual(result["category"],"engine_timing")
        self.assertEqual(result["primary_focus"],"application")
        self.assertEqual(result["target_audience"],"Engine repair and timing-belt workshops")
        self.assertEqual([c["id"] for c in result["recommended_channels"]],
                         ["email","website"])
        self.assertIn(result["proof_point"],self.product["features"][:3])
        self.assertNotIn("7595",result["proof_point"])
        self.assertNotIn("8207",result["proof_point"])

    def test_gemini_cannot_choose_accessory_cross_reference_for_engine_kit(self):
        choices=strategy_options(self.product)
        self.assertEqual(choices["category"],"engine_timing")
        self.assertTrue(all("7595" not in p["verified_manufacturer_fact"]
                            for p in choices["proof_options"]))
        valid={
            "audience_id":"marque_specialists","primary_focus":"application",
            "channels":["email","linkedin"],"proof_index":1,
        }
        result=explain_strategy(self.product,valid)
        self.assertEqual(result["method"],"gemini-validated-choice")
        self.assertIn(result["proof_point"],self.product["features"][:3])
        self.assertNotIn("7595",result["proof_point"])
        self.assertEqual(result["audience_id"],"marque_specialists")

    def test_other_engine_timing_titles_and_unrelated_tools(self):
        cases=[
            ("Engine Timing Master Kit for Peugeot", "engine_timing"),
            ("Cambelt Tool Kit for Vauxhall", "engine_timing"),
            ("Camshaft Locking Tool Set for PSA", "engine_timing"),
            ("Crankshaft Holding Tool for PSA", "engine_timing"),
            ("Timing Belt Checking Gauge for PSA", "engine_timing"),
            ("Timing Chain Locking Kit for Citroën", "engine_timing"),
            ("Front Wheel Bearing Kit for Mercedes-Benz Sprinter", "bearing_suspension"),
            ("72 Tooth Ratchet and Socket Set", "socket_ratchet"),
            ("Hydraulic Workshop Press 20 Tonne", "workshop_press"),
            ("Digital Multimeter and Voltage Tester", "diagnostic_electrical"),
        ]
        for title,expected in cases:
            with self.subTest(title=title):
                actual,_=detect_category({"title":title,"description":""})
                self.assertEqual(actual,expected)


if __name__=="__main__":
    unittest.main()
