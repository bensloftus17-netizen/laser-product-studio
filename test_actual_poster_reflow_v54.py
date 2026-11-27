"""V54: text-reflow repairs must alter pixels and keep independent art usable."""
import base64
import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from flexible_canvas import _text, render_creative_canvas
from poster_quality import capture
from test_ai_creative_director_v45 import (
    PRODUCT, SMART, image_bytes, fake_photo)
from test_visual_review_recovery_v53 import VisualReviewRecoveryV53Tests


def verdict(smart_codes=()):
    return {
        "method":"test-visual-critic","reviewed":True,
        "issues":{
            "poster_technical":[],
            "poster_price":[],
            "poster_smart":list(smart_codes),
        },
        "warning":None,
    }


class ActualPosterTextRepairTests(unittest.TestCase):
    def test_product_selected_recovery_measures_9315_copy_before_painting(self):
        from campaign_role_posters import smart_poster
        title="Brake Fluid Pressure Bleeder with Adaptor Kit"
        proof="A portable workshop pressure bleeder with a selection of reservoir adaptors."
        product={**PRODUCT,"part":"9315","title":title}
        concept={"headline":title,"selling_point":proof,
                 "name":"Workshop brake servicing and fluid replacement"}
        with patch("campaign_role_posters.product_photo",side_effect=fake_photo):
            with capture() as tracked:
                png=smart_poster(product,image_bytes(),concept)
        self.assertTrue(png.startswith(b"\x89PNG"))
        painted={item["role"]:" ".join(item["lines"]) for item in tracked.texts}
        self.assertEqual(painted["headline"],title)
        self.assertEqual(painted["proof"],proof.rstrip("."))
        self.assertFalse(any(item["truncated"] for item in tracked.texts))
        from creative_qa import reconcile_with_measured_geometry
        reconciled=reconcile_with_measured_geometry(
            verdict(["cutoff_text","white_halo"]),
            {"poster_smart":{"passed":True,"text_bounds_verified":True}})
        self.assertEqual(reconciled["issues"]["poster_smart"],["white_halo"])

    def test_9395_fallback_uses_readable_copy_when_the_ai_wording_is_oversized(self):
        from campaign_role_posters import smart_poster
        title="Front Wheel Bearing Kit for Mercedes-Benz Sprinter and Volkswagen Crafter"
        product={**PRODUCT,"part":"9395","title":title}
        concept={"headline":"Oversized generated headline "*80,
                 "name":"Oversized campaign theme "*80,
                 "selling_point":"For Mercedes-Benz Sprinter and Volkswagen Crafter."}
        with patch("campaign_role_posters.product_photo",side_effect=fake_photo):
            with capture() as tracked:
                png=smart_poster(product,image_bytes(),concept)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertTrue(any(t["role"]=="headline" and
                            " ".join(t["lines"])==title for t in tracked.texts))
        self.assertTrue(any(t["text"]=="PRODUCT HIGHLIGHT" for t in tracked.texts))
        self.assertFalse(any(t["truncated"] for t in tracked.texts))

    def test_text_safety_reflows_actual_painted_headline_and_proof(self):
        product=dict(PRODUCT)
        product["title"]="Ratchet Set 4pc"
        concept={
            "campaign_role":"product_selected",
            "creative_canvas":SMART,
            "headline":"Ratchet Set 4pc",
            "selling_point":"Set of four ratchets.",
        }
        pictures=[]
        captures=[]
        with patch("flexible_canvas.product_photo",side_effect=fake_photo):
            for level in (0,1,2):
                with capture() as tracked:
                    picture=render_creative_canvas(
                        product,image_bytes(),concept,variant=1,
                        text_safety=level)
                pictures.append(picture)
                captures.append(tracked)
        boxes=[]
        sizes=[]
        for tracked in captures:
            text=[x for x in tracked.texts if x["role"]=="headline"]
            proof=[x for x in tracked.texts if x["role"]=="proof"]
            self.assertEqual(len(text),1)
            self.assertEqual(len(proof),1)
            self.assertEqual(" ".join(text[0]["lines"]),"Ratchet Set 4pc")
            self.assertEqual(" ".join(proof[0]["lines"]),"Set of four ratchets.")
            self.assertFalse(text[0]["truncated"])
            boxes.append(text[0]["box"])
            sizes.append(text[0]["font_size"])
        self.assertEqual(len(set(boxes)),3)
        self.assertLessEqual(sizes[1],sizes[0])
        self.assertLessEqual(sizes[2],sizes[1])
        self.assertEqual(len(set(pictures)),3)

    def test_visual_critic_gets_readable_preview_not_micro_thumbnail(self):
        from creative_qa import _small_jpeg
        original=image_bytes(1200,1500)
        preview=Image.open(io.BytesIO(base64.b64decode(_small_jpeg(original))))
        self.assertEqual(preview.size,(760,950))

    def test_glyph_extents_are_measured_before_any_drawing(self):
        canvas=Image.new("RGB",(300,130),"#113B53")
        draw=ImageDraw.Draw(canvas)
        with self.assertRaisesRegex(ValueError,"does not fit"):
            _text(draw,"UnbreakablyLongOfficialManufacturerDescription",
                  (15,30,36,52),base=30,minsize=20,maxlines=1)
        self.assertEqual(canvas.getpixel((15,30)),(17,59,83))

    def test_persistently_cutoff_smart_poster_gets_separate_approved_layout(self):
        harness=VisualReviewRecoveryV53Tests()
        harness.setUp()
        pack,calls=harness.run_campaign([
            verdict(["cutoff_text"]),verdict(["cutoff_text"]),
            verdict(["cutoff_text"]),verdict([]),
        ])
        self.assertEqual(calls,4)
        review=pack["manifest"]["artwork_quality"]
        self.assertEqual(review["poster_smart"]["render_engine"],
                         "verified-safe-layout")
        self.assertEqual(pack["manifest"]["creative_plan"]["render_engine"],
                         "mixed-ai-and-verified-safe-layout")
        self.assertIn("poster_smart",
                      pack["manifest"]["creative_plan"]["verified_safe_recoveries"])
        angles=pack["manifest"]["angles"]
        self.assertEqual(angles[2]["layout"],"Verified-safe recovery")
        self.assertIn("independently approved safe-layout recovery",
                      __import__("app").V7_HOME_PAGE)
        self.assertTrue(pack["archive"].startswith(b"PK"))
        self.assertEqual(
            sum(e[0]=="ready" and e[1]=="poster_smart" for e in harness.events),1)

    def test_approved_native_artwork_released_even_when_smart_poster_fails(self):
        harness=VisualReviewRecoveryV53Tests()
        harness.setUp()
        with self.assertRaisesRegex(ValueError,"poster_smart: cutoff_text"):
            harness.run_campaign([
                verdict(["cutoff_text"]),verdict(["cutoff_text"]),
                verdict(["cutoff_text"]),verdict(["cutoff_text"]),
            ])
        from format_creative import FORMAT_ORDER
        native_ready=[e[1] for e in harness.events
                      if e[0]=="ready" and e[1] in FORMAT_ORDER]
        self.assertEqual(set(native_ready),set(FORMAT_ORDER))
        self.assertFalse(any(
            e[0]=="ready" and e[1] in
            ("poster_technical","poster_price","poster_smart")
            for e in harness.events))
        native_last=max(i for i,e in enumerate(harness.events)
                        if e[0]=="ready" and e[1] in FORMAT_ORDER)
        poster_review=next(i for i,e in enumerate(harness.events)
                           if e[0]=="reviewing_posters")
        self.assertLess(native_last,poster_review)


if __name__=="__main__":
    unittest.main()
