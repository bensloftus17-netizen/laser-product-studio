"""V69 regression: one workshop price poster, distinct native asset formats.

No internet or Gemini required. These tests enforce routing, separation and
independent visual-family selection without weakening source/quality gates.
"""
from __future__ import annotations
import unittest

from creative_families import (
    FAMILIES, FORMAT_VISUAL_FAMILIES, FORMAT_VISUAL_TREATMENTS,
    choose_native_visuals, validate_poster_reference_roles,
)

EXPECTED={
    "poster_technical":"laser-technical-reference",
    "poster_price":"laser-workshop-promo-reference",
    "poster_smart":"ai-freeform-canvas",
}


class PosterRoleAndFormatSeparationV69Tests(unittest.TestCase):
    def test_exactly_one_workshop_poster(self):
        self.assertTrue(validate_poster_reference_roles(
            dict(EXPECTED),"workshop_showcase"))

    def test_reference_cannot_replace_technical_or_selected(self):
        for broken in (
            {**EXPECTED,"poster_technical":"laser-workshop-promo-reference"},
            {**EXPECTED,"poster_smart":"laser-workshop-promo-reference"},
            {**EXPECTED,"poster_price":"ai-freeform-canvas"},
            {**EXPECTED,"poster_smart":"laser-technical-reference"},
        ):
            with self.subTest(broken=broken),self.assertRaises(ValueError):
                validate_poster_reference_roles(broken,"workshop_showcase")

    def test_unselected_workshop_template_is_not_used(self):
        switched={**EXPECTED,"poster_price":"ai-freeform-canvas"}
        self.assertTrue(validate_poster_reference_roles(switched,"ai_original"))
        with self.assertRaises(ValueError):
            validate_poster_reference_roles(EXPECTED,"ai_original")

    def test_all_six_native_formats_are_distinct_with_no_model(self):
        self.assertEqual(len(FORMAT_VISUAL_FAMILIES),6)
        self.assertEqual(set(FORMAT_VISUAL_FAMILIES),
                         set(FORMAT_VISUAL_TREATMENTS))
        used_families=[]
        used_treatments=[]
        for kind in FORMAT_VISUAL_FAMILIES:
            family,treatment=choose_native_visuals(
                kind,None,None,used_families,used_treatments)
            self.assertNotIn(family,used_families)
            self.assertNotIn(treatment,used_treatments)
            used_families.append(family)
            used_treatments.append(treatment)
        self.assertEqual(len(set(used_families)),6)
        self.assertEqual(len(set(used_treatments)),6)

    def test_repeated_ai_compositions_are_diversified(self):
        used_families=[]
        used_treatments=[]
        for kind in FORMAT_VISUAL_FAMILIES:
            family,treatment=choose_native_visuals(
                kind,"premium_spotlight","cinematic",
                used_families,used_treatments)
            used_families.append(family)
            used_treatments.append(treatment)
        self.assertEqual(len(set(used_families)),6)
        self.assertEqual(len(set(used_treatments)),6)

    def test_valid_original_ai_choice_is_preserved_when_unique(self):
        self.assertEqual(
            choose_native_visuals(
                "social_square","editorial_split","cinematic",(),()),
            ("editorial_split","cinematic"))

    def test_unsupported_format_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_native_visuals("poster_price","premium_spotlight")

    def test_families_are_known_and_templates_not_reused(self):
        self.assertEqual(set(FORMAT_VISUAL_FAMILIES.values()),set(FAMILIES))
        self.assertNotIn("workshop_showcase",FORMAT_VISUAL_FAMILIES.values())
        self.assertNotIn("technical_reference",FORMAT_VISUAL_FAMILIES.values())


if __name__=="__main__":
    unittest.main()
