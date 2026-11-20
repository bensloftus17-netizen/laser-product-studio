"""V64 user-reference promotional poster template integration and fidelity.

The reference informs fixed brand composition; AI still chooses bounded
palette, scene and hero style while original manufacturer facts, photo and RRP
remain unchanged. The template affects only poster 02, not the other eight.
"""
from __future__ import annotations

import io
import copy
import unittest
from unittest.mock import patch

from PIL import Image

from poster_quality import capture
from campaign_art_quality import visual_review
from test_ai_creative_director_v45 import PRODUCT,image_bytes,fake_photo
from workshop_promo_template import (
    render_workshop_showcase,validate_promo_template,_verified,
    TEMPLATE_OPTIONS,
)
import app
import campaign_hub


def product(**kwargs):
    p=copy.deepcopy(PRODUCT)
    p.update({
        "part":"4554",
        "title":"Metric Tap and Die Set 110pc",
        "features":[
            "110-piece metric tap and die set.",
            "Includes metric taps and dies.",
            "Supplied in a blue storage case.",
        ],
        "specs":{"Piece count":"110"},
    })
    p.update(kwargs)
    return p


def concept(palette="laser_blue"):
    return {
        "campaign_role":"price_promo",
        "headline":"Metric Tap and Die Set 110pc",
        "selling_point":"Includes metric taps and dies.",
        "creative_direction":{
            "creative_palette":palette,
            "visual_treatment":"photo_editorial",
            "hero_emphasis":"dominant",
            "creative_family":"commercial_burst",
        },
    }


class WorkshopPromoTemplateV64Tests(unittest.TestCase):
    def test_template_is_selected_by_default_but_can_be_disabled(self):
        self.assertEqual(validate_promo_template(None),"workshop_showcase")
        self.assertEqual(set(TEMPLATE_OPTIONS),{"workshop_showcase","ai_original"})
        self.assertEqual(validate_promo_template("ai_original"),"ai_original")
        for invalid in ("clone","javascript:alert(1)",22,{},False):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_promo_template(invalid)

    def test_kit_contents_is_source_only_and_never_made_up(self):
        p=product()
        facts=_verified(p,concept())
        self.assertIn("Includes metric taps and dies.",facts)
        self.assertNotIn("Includes Allen keys.",facts)
        facts2=_verified(product(features=["110-piece metric tap and die set."]),{
            **concept(),"selling_point":"Includes 100 pieces of titanium."})
        self.assertNotIn("Includes 100 pieces of titanium.",facts2)

    def test_reference_layout_renders_readable_price_and_real_photo(self):
        p=product(price="£114.70 ex VAT")
        original=image_bytes()
        with patch("workshop_promo_template.product_photo",
                   side_effect=fake_photo) as placed:
            with capture() as tracked:
                poster=render_workshop_showcase(p,original,concept(),variant=1)
        self.assertEqual(Image.open(io.BytesIO(poster)).size,(1200,1500))
        self.assertEqual(placed.call_count,1)
        self.assertEqual(placed.call_args.args[1],original)
        self.assertTrue(tracked.products)
        self.assertTrue(any(t["role"]=="headline" for t in tracked.texts))
        self.assertTrue(any(t["role"]=="price" and "£114.70" in t["text"]
                            for t in tracked.texts))
        self.assertTrue(any(t["role"]=="price_caption" and "EX VAT" in t["text"]
                            for t in tracked.texts))
        self.assertTrue(any(t["role"]=="kit_details" and
                            "Includes metric taps" in t["text"]
                            for t in tracked.texts))
        self.assertTrue(any(a["role"]=="price" for a in tracked.areas))
        self.assertTrue(all(not t["truncated"] for t in tracked.texts))
        self.assertTrue(visual_review(poster,"price_promo",text_status={
            "product_visible_fraction":.13,"text_bounds_verified":True,
            "product_bounds_verified":True})["passed"])

    def test_template_does_not_invent_price_or_contents(self):
        p=product(price=None,features=["110-piece metric tap and die set."])
        with patch("workshop_promo_template.product_photo",side_effect=fake_photo):
            with capture() as tracked:
                render_workshop_showcase(p,image_bytes(),concept(),variant=0)
        visible=" ".join(t["text"] for t in tracked.texts)
        self.assertIn("PRICE ON REQUEST",visible)
        self.assertNotIn("£",visible)
        self.assertNotIn("UK RRP",visible)
        self.assertNotIn("Includes metric taps and dies.",visible)
        self.assertIn("PRODUCT DETAILS",visible)
        self.assertNotIn("KIT CONTENTS",visible)

    def test_three_safe_model_driven_variants_are_visibly_different(self):
        raw=image_bytes()
        results=[]
        with patch("workshop_promo_template.product_photo",side_effect=fake_photo):
            for var in range(3):
                picture=render_workshop_showcase(product(),raw,
                    concept(("laser_blue","signal_yellow","electric_violet")[var]),
                    variant=var)
                results.append(Image.open(io.BytesIO(picture))
                               .resize((48,60)).tobytes())
        self.assertEqual(len(set(results)),3)

    def test_workshop_template_applies_only_to_price_poster(self):
        with patch("campaign_hub._concepts",return_value=([],"verified-templates",[])), \
             patch("campaign_hub.require_good_asset",
                   return_value={"passed":True}), \
             patch("campaign_hub.find_scene",return_value=(
                 None,{"source":"No external photograph used",
                       "category":"hand_tools"})), \
             patch("campaign_hub.choose_best",
                   return_value=(image_bytes(1200,1500),{
                       "passed":True,"score":90,"variation":0})), \
             patch("campaign_hub.review_finished_artworks",
                   return_value={"reviewed":True,"method":"test",
                                 "issues":{},"warning":None}), \
             patch("campaign_hub.check_distinctness",
                   return_value={"passed":True,"issues":[],"pairs":[]}), \
             patch("campaign_hub._native_graphic",
                   return_value=image_bytes(1080,1080)):
            pack=campaign_hub.build_campaign(
                product(),image_bytes(),use_gemini=False,
                promo_template="workshop_showcase")
        manifest=pack["manifest"]
        self.assertEqual(manifest["promo_template"],"workshop_showcase")
        self.assertEqual(manifest["creative_plan"]["promo_template"],"workshop_showcase")
        self.assertIn("Workshop Showcase",manifest["angles"][1]["layout"])
        self.assertNotIn("Workshop Showcase",manifest["angles"][0]["layout"])
        self.assertNotIn("Workshop Showcase",manifest["angles"][2]["layout"])

    def test_website_has_real_selector_and_payload_reaches_backend(self):
        page=app.V7_HOME_PAGE
        self.assertIn('id="promoTemplate"',page)
        self.assertIn('value="workshop_showcase" selected',page)
        self.assertIn('value="ai_original"',page)
        self.assertIn("promo_template:$('promoTemplate').value",page)
        self.assertIn("Template: Workshop Showcase",page)
        self.assertIn("V65 memory stable",page)

    def test_bad_api_template_rejected_before_retrieving_product(self):
        with patch.object(app,"lookup") as lookup:
            with self.assertRaises(ValueError):
                app._assemble_campaign_bundle(
                    "4554",{"promo_template":"unapproved-external-image"})
            lookup.assert_not_called()


if __name__=="__main__":
    unittest.main()
