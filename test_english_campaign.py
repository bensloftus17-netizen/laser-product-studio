"""Keep product 9476 and other supplier documents English-only in every output.

Known German *numeric labels* can be translated without changing values.
Unrecognised foreign factual claims must be omitted rather than invented.
"""
import io
import json
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

import app
from campaign_director import plan_campaign
from campaign_hub import build_campaign
from english_numeric_specs import (RAW_GERMAN_TECH, translate_known_numeric_labels,
                                   normalise_numeric_spec_row)
from promo_copy import compose_promotional_copy
from copy_rewriter import rewrite_copy


GERMAN_9476="Abmessungen: 172 x 69 x 235 mm. Gewicht: 820 g."
ENGLISH_9476="Dimensions: 172 x 69 x 235 mm. Weight: 820 g."
GERMAN_9469="Auswechselbare Schlüsselköpfe: 13, 14, 15, 16, 17, 19, 21, 24, 27 und 30 mm."
ENGLISH_9469="Interchangeable spanner heads: 13, 14, 15, 16, 17, 19, 21, 24, 27 and 30 mm."
OFFICIAL_PRODUCT = {
    "part":"9476",
    "title":"9476 Multi-Function Work Lamp with Built-In 3 Speed Fan",
    "source":"https://www.toolconnection.co.uk/products/workshop/inspection-lighting/"
             "workshop-lamps/9476-multi-function-work-lamp-with-fan",
    "price":None,
    "description":"Rechargeable work lamp with built-in three-speed fan. "+GERMAN_9476,
    "features":[
        GERMAN_9476,
        "Includes a built-in three-speed fan for workshop use.",
        "Lieferumfang mit Ladegerät und Beleuchtung für Werkstatt.",
    ],
    "specs":{
        "Abmessungen":"172 x 69 x 235 mm",
        "Gewicht":"820 g",
        "Battery":"Manufacturer-confirmed rechargeable type",
        "Ladezeit":"3 h",
        "Unbekannte Angaben":"Mit Zubehör",
    },
}


def picture():
    image=Image.new("RGB",(500,440),"#FDFDFD")
    from PIL import ImageDraw
    pencil=ImageDraw.Draw(image)
    pencil.rounded_rectangle((110,70,410,390),radius=26,fill="#112D4C")
    pencil.rectangle((135,90,370,330),fill="#2279BE")
    output=io.BytesIO()
    image.save(output,"PNG")
    return output.getvalue()


class EnglishOnlyProductPipelineTests(unittest.TestCase):
    def test_german_short_specs_are_detected_before_statistical_detection(self):
        snippets=[
            "Abmessungen: 172 x 69 x 235 mm.",
            "Gewicht: 820 g.",
            "Abmessungen: 172 x 69 x 235 mm. Gewicht: 820 g.",
            "Ladezeit: 3 h.",
            "Technische Daten: 10W",
            "Lieferumfang mit Ladekabel",
        ]
        for item in snippets:
            with self.subTest(item=item):
                self.assertTrue(app.is_non_english(item))
        for english in ("Dimensions: 172 x 69 x 235 mm.",
                        "Weight: 820 g.",
                        "Rechargeable work lamp with three-speed fan."):
            with self.subTest(english=english):
                self.assertFalse(app.is_non_english(english))

    def test_only_exact_known_numeric_labels_are_translated(self):
        self.assertEqual(translate_known_numeric_labels(GERMAN_9476),ENGLISH_9476)
        self.assertEqual(translate_known_numeric_labels("Gewicht: 820 g."),
                         "Weight: 820 g.")
        self.assertEqual(translate_known_numeric_labels("Ladezeit: 3 h."),
                         "Charging time: 3 h.")
        self.assertEqual(normalise_numeric_spec_row("Abmessungen","172 x 69 x 235 mm"),
                         ("Dimensions","172 x 69 x 235 mm"))
        self.assertEqual(normalise_numeric_spec_row("Gewicht","820 g"),
                         ("Weight","820 g"))
        # Unsupported foreign claims remain untranslated and are subsequently
        # rejected, rather than passed to AI to fabricate English wording.
        untranslated="Lieferumfang enthält drei Ladegeräte."
        self.assertEqual(translate_known_numeric_labels(untranslated),untranslated)
        self.assertTrue(app.is_non_english(untranslated))

    def test_9469_spanner_sizes_remain_verified_and_english_everywhere(self):
        self.assertTrue(app.is_non_english(GERMAN_9469))
        self.assertEqual(translate_known_numeric_labels(GERMAN_9469), ENGLISH_9469)
        self.assertFalse(app.is_non_english(ENGLISH_9469))
        product = {
            "part": "9469",
            "title": "9469 Open Spanner Torque Wrench Set 20 - 210Nm - 12pc",
            "price": None,
            "features": [GERMAN_9469, "Wechselbare Maulschlüssel für Werkstatt."],
            "description": "Open spanner torque wrench set. " + GERMAN_9469,
            "specs": {
                "Auswechselbare Schlüsselköpfe":
                    "13, 14, 15, 16, 17, 19, 21, 24, 27 und 30 mm",
            },
        }
        cleaned = app.normalise_product_language(product)
        self.assertEqual(cleaned["features"], [ENGLISH_9469])
        self.assertIn(ENGLISH_9469, cleaned["description"])
        self.assertEqual(cleaned["specs"]["Interchangeable spanner heads"],
                         "13, 14, 15, 16, 17, 19, 21, 24, 27 and 30 mm")
        self.assertNotIn("Maulschlüssel", " ".join(cleaned["features"]))
        # Old cached/unsanitised input must not leak into any copy channel.
        for record in (cleaned, product):
            for family in ("retail", "premium", "trade"):
                copy = compose_promotional_copy(record, {"family": family, "features": []})
                for channel in ("social_caption", "linkedin_post", "email_body", "email_subject"):
                    self.assertNotIn("Schlüssel", copy[channel], (family, channel))
                    self.assertNotIn("Wechselbare", copy[channel], (family, channel))
                    self.assertIn(ENGLISH_9469, copy[channel], (family, channel))
            rewritten = rewrite_copy(
                record, mode="professional", channel="linkedin_post",
                current_text="Product spotlight: Laser Tools 9469", angle=0)
            self.assertNotIn("Schlüssel", rewritten["text"])
            self.assertIn(ENGLISH_9469, rewritten["text"])

    def test_unverified_german_claims_are_rejected_not_guessed(self):
        for text in (
            "Wechselbare Maulschlüssel für Werkstatt.",
            "Schlüsselköpfe für viele Anwendungen",
            "Drehmomentschlüssel mit verstellbaren Aufsätzen",
        ):
            with self.subTest(text=text):
                self.assertTrue(app.is_non_english(text))
                self.assertEqual(translate_known_numeric_labels(text), text)
                self.assertEqual(app.english_only_features([text]), [])

    def test_normalisation_preserves_numbers_not_german_copy(self):
        cleaned=app.normalise_product_language(OFFICIAL_PRODUCT)
        self.assertIn(ENGLISH_9476,cleaned["features"])
        self.assertEqual(cleaned["specs"]["Dimensions"],"172 x 69 x 235 mm")
        self.assertEqual(cleaned["specs"]["Weight"],"820 g")
        self.assertEqual(cleaned["specs"]["Charging time"],"3 h")
        self.assertNotIn("Abmessungen",cleaned["specs"])
        self.assertNotIn("Gewicht",cleaned["specs"])
        self.assertNotIn("Unbekannte Angaben",cleaned["specs"])
        self.assertFalse(any(app.is_non_english(f) for f in cleaned["features"]))
        self.assertNotIn("Lieferumfang",json.dumps({
            "features":cleaned["features"],"description":cleaned["description"],
            "specs":cleaned["specs"]
        },ensure_ascii=False))
        # Original audit remains internal, never used in campaign artwork.
        self.assertIn(GERMAN_9476,cleaned["source_raw_features"])
        twice=app.normalise_product_language(cleaned)
        self.assertEqual(cleaned["features"],twice["features"])

    def test_director_and_all_marketing_copy_use_only_english_record(self):
        cleaned=app.normalise_product_language(OFFICIAL_PRODUCT)
        concepts,plan=plan_campaign(cleaned)
        for c in concepts:
            values=[c["headline"],c["selling_point"],*(c["features"] or [])]
            self.assertFalse(any(app.is_non_english(v) for v in values))
            copy=compose_promotional_copy(cleaned,c)
            for field in ("social_caption","linkedin_post","email_body","email_subject"):
                self.assertNotIn("Abmessungen",copy[field])
                self.assertNotIn("Gewicht",copy[field])
                self.assertNotIn("Lieferumfang",copy[field])

    def test_campaign_rechecks_unsanitised_record_and_zip_cannot_leak_german(self):
        payload=picture()
        placeholder=Image.new("RGB",(1200,1500),"#09294B")
        out=io.BytesIO()
        placeholder.save(out,"PNG")
        png=out.getvalue()

        def best(*args,**kwargs):
            return png,{"passed":True,"candidates_checked":3,"score":89,"warnings":[]}

        # Direct unsanitised record simulates stale cached inputs bypassing
        # app.lookup; build_campaign must still deliver only English outputs.
        with patch("campaign_hub.choose_best",side_effect=best), \
             patch("campaign_hub.find_scene",return_value=(None,{})):
            pack=build_campaign(dict(OFFICIAL_PRODUCT),payload,use_gemini=False)

        manifest=pack["manifest"]
        self.assertEqual(len(manifest["angles"]),3)
        for key in ("angles","copy","social_suggestions","marketing_strategy"):
            output=json.dumps(manifest[key],ensure_ascii=False)
            self.assertNotIn("Abmessungen",output)
            self.assertNotIn("Gewicht",output)
            self.assertNotIn("Lieferumfang",output)
        self.assertIn("Dimensions: 172 x 69 x 235 mm",json.dumps(
            app.normalise_product_language(OFFICIAL_PRODUCT)["features"]))
        with ZipFile(io.BytesIO(pack["archive"])) as z:
            for name in z.namelist():
                if name.endswith((".json",".txt")) and "Campaign_Manifest" not in name:
                    text=z.read(name).decode("utf-8")
                    self.assertNotIn("Abmessungen",text,name)
                    self.assertNotIn("Gewicht",text,name)
                    self.assertNotIn("Lieferumfang",text,name)
            record=json.loads(z.read("05_Product_Info/Source_Record.json"))
            self.assertNotIn("source_raw_features",record)
            self.assertEqual(record["specs"]["Weight"],"820 g")


if __name__=="__main__":
    unittest.main()
