"""V68: a model's duplicate_layout opinion needs evidence on fixed reference art.

The objective poster-distinctness check always remains in force. Only a locked,
already-approved reference composition with strong pairwise pixel evidence can
dispute the subjective critic. Weak/unknown evidence cannot unlock artwork.
"""
import io
import unittest

from PIL import Image, ImageDraw
from creative_qa import reconcile_with_measured_geometry
from campaign_distinctness import check_distinctness


REFERENCE_QUALITY={
    "poster_technical":{"passed":True,"render_engine":"laser-technical-reference",
                        "text_bounds_verified":True},
    "poster_price":{"passed":True,"render_engine":"laser-workshop-promo-reference",
                    "text_bounds_verified":True},
    "poster_smart":{"passed":True,"render_engine":"ai-freeform-canvas"},
}


def _visual(role="poster_price",*codes):
    return {"reviewed":True,"method":"gemini-visual-critic",
            "issues":{key:(list(codes) if key==role else [])
                      for key in REFERENCE_QUALITY},"warning":None}


def _strong_distinctness():
    return {"passed":True,"issues":[],"pairs":[
        {"left":"poster_technical","right":"poster_price",
         "difference":.238,"perceptual_hash_distance":25},
        {"left":"poster_technical","right":"poster_smart",
         "difference":.190,"perceptual_hash_distance":15},
        {"left":"poster_price","right":"poster_smart",
         "difference":.151,"perceptual_hash_distance":13},
    ]}


class ReferenceDuplicateCriticV68Tests(unittest.TestCase):
    def test_reference_price_duplicate_disputed_with_strong_actual_pixels(self):
        r=reconcile_with_measured_geometry(
            _visual("poster_price","duplicate_layout"),
            REFERENCE_QUALITY,_strong_distinctness())
        self.assertEqual(r["issues"]["poster_price"],[])
        self.assertIn("duplicate_layout",r["geometry_disagreements"]["poster_price"])
        self.assertIn("human review",r["warning"])

    def test_reference_technical_duplicate_disputed_with_strong_actual_pixels(self):
        r=reconcile_with_measured_geometry(
            _visual("poster_technical","duplicate_layout"),
            REFERENCE_QUALITY,_strong_distinctness())
        self.assertEqual(r["issues"]["poster_technical"],[])

    def test_unknown_or_weak_pairwise_evidence_never_unlocks(self):
        for evidence in [None,{"passed":False,"pairs":[]},
                         {"passed":True,"pairs":[]},
                         {"passed":True,"pairs":[
                             {"left":"poster_technical","right":"poster_price",
                              "difference":.031,"perceptual_hash_distance":1},
                             {"left":"poster_price","right":"poster_smart",
                              "difference":.042,"perceptual_hash_distance":4},
                         ]}]:
            r=reconcile_with_measured_geometry(
                _visual("poster_price","duplicate_layout"),
                REFERENCE_QUALITY,evidence)
            self.assertEqual(r["issues"]["poster_price"],["duplicate_layout"])

    def test_generic_ai_duplicate_still_blocks(self):
        r=reconcile_with_measured_geometry(
            _visual("poster_smart","duplicate_layout"),
            REFERENCE_QUALITY,_strong_distinctness())
        self.assertEqual(r["issues"]["poster_smart"],["duplicate_layout"])

    def test_wrong_engine_or_failed_reference_qa_still_blocks(self):
        for override in ({"passed":False},{"render_engine":"ai-freeform-canvas"}):
            quality={k:dict(v) for k,v in REFERENCE_QUALITY.items()}
            quality["poster_price"].update(override)
            r=reconcile_with_measured_geometry(
                _visual("poster_price","duplicate_layout"),
                quality,_strong_distinctness())
            self.assertEqual(r["issues"]["poster_price"],["duplicate_layout"])

    def test_unrelated_visual_issues_are_not_disputed(self):
        r=reconcile_with_measured_geometry(
            _visual("poster_price","duplicate_layout","white_halo",
                    "unreadable_copy","clutter"),
            REFERENCE_QUALITY,_strong_distinctness())
        self.assertEqual(
            r["issues"]["poster_price"],
            ["white_halo","unreadable_copy","clutter"])

    def test_actual_identical_posters_still_fail_independent_gate(self):
        raw=io.BytesIO()
        Image.new("RGB",(1200,1500),"#072C4A").save(raw,"PNG")
        imgs={key:raw.getvalue() for key in REFERENCE_QUALITY}
        concepts=[{"creative_direction":{"creative_family":name}}
                  for name in ("engineering_grid","commercial_burst",
                               "premium_spotlight")]
        actual=check_distinctness(imgs,concepts)
        self.assertFalse(actual["passed"])
        opinion=_visual("poster_price","duplicate_layout")
        r=reconcile_with_measured_geometry(opinion,REFERENCE_QUALITY,actual)
        self.assertEqual(r["issues"]["poster_price"],["duplicate_layout"])


if __name__=="__main__":
    unittest.main()
