"""V62: prevent short Dutch technical features from leaking into any copy.

The 7845 Dutch source sentence and verified manufacturer English listing
cover exactly a 16 mm square section and 25-degree angled head.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import app
from english_numeric_specs import translate_known_numeric_labels
from promo_copy import compose_promotional_copy
from copy_rewriter import rewrite_copy
from campaign_director import plan_campaign


DUTCH="Vierkante doorsnede van 16 mm, gebogen kop van 25°."
ENGLISH="16 mm square section; 25° angled head."
REAL_OFFICIAL="https://www.toolconnection.co.uk/products/general-hand-tools/striking-tools/pry-bars/heavy-duty/7845-pry-bar-900mm"
PRODUCT={
    "part":"7845",
    "title":"Pry Bar 900mm",
    "features":[
        DUTCH,
        "Met een sterke metalen kop voor werkzaamheden.",  # Not verified in English.
    ],
    "description":"900mm pry bar. "+DUTCH,
    "specs":{"Length":"900mm","Material":"EN9 steel"},
    "source":REAL_OFFICIAL,
    "price":None,
}


class DutchLanguageGateV62Tests(unittest.TestCase):
    def test_7845_is_pinned_to_official_english_manufacturer_page(self):
        self.assertEqual(app.OFFICIAL_UK_PRODUCTS["7845"],REAL_OFFICIAL)

    def test_verified_dutch_geometry_translates_preserving_every_number(self):
        self.assertTrue(app.is_non_english(DUTCH))
        self.assertEqual(translate_known_numeric_labels(DUTCH),ENGLISH)
        self.assertEqual(translate_known_numeric_labels(
            "vierkante doorsnede van 16 mm; gebogen kop van 25°"),
            ENGLISH)
        self.assertFalse(app.is_non_english(ENGLISH))
        self.assertNotIn("Vierkante",ENGLISH)
        self.assertNotIn("gebogen",ENGLISH)

    def test_unknown_dutch_marketing_claim_is_rejected_not_creatively_translated(self):
        for dutch in (
            "Vierkante doorsnede van 16 mm, gebogen kop van 25° gegarandeerd.",
            "Met een sterke metalen kop voor werkzaamheden.",
            "Geharde en vervaardigd werkplaats onderdelen.",
            "Geschikt voor alle voertuigen; gebogen kop.",
            "De doorsnede van het staal maakt dit de beste pry bar.",
        ):
            with self.subTest(dutch=dutch):
                self.assertEqual(translate_known_numeric_labels(dutch),dutch)
                self.assertTrue(app.is_non_english(dutch))
                self.assertEqual(app.english_only_features([dutch]),[])

    def test_short_dutch_markers_not_reliant_on_language_guesser(self):
        for dutch in ("Vierkante doorsnede van 16 mm.",
                      "Gebogen kop van 25°.",
                      "Een handgreep voor werkplaatsgebruik.",
                      "Vervaardigd uit geharde materialen."):
            self.assertTrue(app.is_non_english(dutch),dutch)
        for english in ("Suitable for Volkswagen vans.",
                        "16 mm square section; 25° angled head.",
                        "Metal-capped handle for use with a mallet.",
                        "Use this pry bar in the workshop."):
            self.assertFalse(app.is_non_english(english),english)

    def test_source_audit_kept_but_all_marketing_features_are_english(self):
        cleaned=app.normalise_product_language(PRODUCT)
        self.assertIn(DUTCH,cleaned["source_raw_features"])
        self.assertEqual(cleaned["features"],[ENGLISH])
        self.assertIn(ENGLISH,cleaned["description"])
        self.assertNotIn("Vierkante",cleaned["description"])
        self.assertNotIn("gebogen",str(cleaned["features"]))
        self.assertEqual(app.normalise_product_language(cleaned)["features"],
                         [ENGLISH])

    def test_all_three_initial_copy_angles_are_english_and_fact_checked(self):
        for family in ("trade","retail","premium"):
            draft=compose_promotional_copy(PRODUCT,{"family":family,"features":[]})
            for channel in ("social_caption","linkedin_post","email_body"):
                text=draft[channel]
                self.assertIn(ENGLISH,text,(family,channel))
                self.assertNotIn("Vierkante",text,(family,channel))
                self.assertNotIn("gebogen",text,(family,channel))
                self.assertIn("Price on request",text)
            self.assertEqual(draft["source_claims"],[ENGLISH])

    def test_copy_editor_never_repeats_dutch_or_invents_prices(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":""}):
            for mode in ("shorter","hook","evidence","enquiry","english"):
                for channel in ("linkedin_post","email_body","social_caption"):
                    with self.subTest(mode=mode,channel=channel):
                        result=rewrite_copy(
                            PRODUCT,mode=mode,channel=channel,angle=0,
                            audience="workshop",current_text=DUTCH)
                        text=result["text"]
                        self.assertIn(ENGLISH,text)
                        self.assertIn("Price on request",text)
                        self.assertNotIn("Vierkante",text)
                        self.assertNotIn("gebogen",text)
                        self.assertNotIn("£",text)
                        self.assertTrue(result["review_required"])

    def test_campaign_concepts_have_no_untranslated_dutch(self):
        product=app.normalise_product_language(PRODUCT)
        concepts,plan=plan_campaign(product)
        self.assertEqual(len(concepts),3)
        for concept in concepts:
            text=str({k:concept.get(k) for k in (
                "headline","selling_point","features")})
            self.assertNotIn("Vierkante",text)
            self.assertNotIn("gebogen",text)
        self.assertEqual(len(product["features"]),1)

    def test_unrelated_french_and_german_numeric_translation_still_works(self):
        self.assertEqual(translate_known_numeric_labels(
            "Longueur: 120 mm, profondeur interne: 93 mm."),
            "Length: 120 mm. Internal depth: 93 mm.")
        self.assertEqual(translate_known_numeric_labels(
            "Abmessungen: 172 x 69 x 235 mm. Gewicht: 820 g."),
            "Dimensions: 172 x 69 x 235 mm. Weight: 820 g.")


if __name__=="__main__":
    unittest.main()
