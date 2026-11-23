"""V70: secondary Gemini visual-review outages must not erase safe draft artwork."""
import unittest
from creative_qa import pending_review_after_outage


def reports():
    return {
        role:{
            "passed":True,
            "text_bounds_verified":True,
            "product_bounds_verified":True,
            "product_visible_fraction":.22,
        } for role in ("poster_technical","poster_price","poster_smart")
    }


def differences():
    return {"passed":True, "issues":[], "pairs":[
        {"left":"poster_technical","right":"poster_price",
         "difference":.24,"perceptual_hash_distance":24},
        {"left":"poster_technical","right":"poster_smart",
         "difference":.22,"perceptual_hash_distance":18},
        {"left":"poster_price","right":"poster_smart",
         "difference":.19,"perceptual_hash_distance":15}
    ]}


class VisualReviewOutageV70Tests(unittest.TestCase):
    def test_available_only_as_manual_review_draft(self):
        report=pending_review_after_outage(
            reports(), differences(),
            {"poster_price":["clutter"],"poster_smart":["cutoff_text"]},
            {"poster_price","poster_smart"},"Gemini HTTP 429")
        self.assertIsNotNone(report)
        self.assertFalse(report["reviewed"])
        self.assertTrue(report["manual_review_required"])
        self.assertEqual(report["review_status"],"pending_human_visual_review")
        self.assertIn("DO NOT PUBLISH",report["warning"])
        self.assertEqual(report["issues"]["poster_price"],["clutter"])
        self.assertIn("Gemini HTTP 429",report["warning"])

    def test_no_delivery_for_white_halo_or_blurry_product(self):
        for code in ("white_halo","white_box","blurry_product"):
            self.assertIsNone(pending_review_after_outage(
                reports(),differences(),{"poster_smart":[code]},
                {"poster_smart"}))

    def test_no_delivery_with_incomplete_poster_repair(self):
        self.assertIsNone(pending_review_after_outage(
            reports(),differences(),
            {"poster_price":["clutter"],"poster_smart":["poor_contrast"]},
            {"poster_price"}))

    def test_no_delivery_if_any_objective_qa_fails(self):
        for override in (
            {"passed":False},
            {"text_bounds_verified":False},
            {"product_bounds_verified":False},
        ):
            quality=reports()
            quality["poster_smart"].update(override)
            self.assertIsNone(pending_review_after_outage(
                quality,differences(),{"poster_smart":["cutoff_text"]},
                {"poster_smart"}))

    def test_no_delivery_for_real_visual_duplicates(self):
        d=differences()
        d["passed"]=False
        self.assertIsNone(pending_review_after_outage(
            reports(),d,{"poster_price":["duplicate_layout"]},
            {"poster_price"}))

    def test_duplicate_concern_requires_strong_pixel_evidence(self):
        d=differences()
        d["pairs"][0]["difference"]=.04
        d["pairs"][0]["perceptual_hash_distance"]=3
        self.assertIsNone(pending_review_after_outage(
            reports(),d,{"poster_price":["duplicate_layout"]},
            {"poster_price"}))

    def test_duplicate_concern_preserved_as_pending_not_approved(self):
        result=pending_review_after_outage(
            reports(),differences(),{"poster_price":["duplicate_layout"]},
            {"poster_price"})
        self.assertIsNotNone(result)
        self.assertFalse(result["reviewed"])
        self.assertEqual(result["issues"]["poster_price"],["duplicate_layout"])

    def test_tiny_product_must_be_repaired_measurably(self):
        data=reports()
        data["poster_smart"]["product_visible_fraction"]=.03
        self.assertIsNone(pending_review_after_outage(
            data,differences(),{"poster_smart":["tiny_product"]},
            {"poster_smart"}))

    def test_no_fallback_without_any_prior_visual_issue(self):
        self.assertIsNone(pending_review_after_outage(
            reports(),differences(),{},{"poster_price"}))


if __name__=="__main__":
    unittest.main()
