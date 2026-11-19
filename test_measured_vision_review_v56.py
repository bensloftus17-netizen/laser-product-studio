"""V56: objective rendered-pixel evidence must arbitrate fallible AI criticism."""
from __future__ import annotations
import io
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

from creative_qa import reconcile_with_measured_geometry
from poster_quality import capture
from campaign_hub import build_campaign
from format_creative import FORMATS,FORMAT_ORDER
from test_ai_creative_director_v45 import (
    PRODUCT,PRICE,SMART,TECH,image_bytes,fake_photo)
from creative_director import validate_brief


POSTERS=("poster_technical","poster_price","poster_smart")


def critique(price=None,smart=None):
    return {
        "reviewed":True,"method":"test-independent-vision",
        "issues":{"poster_technical":[],"poster_price":list(price or []),
                  "poster_smart":list(smart or [])},
        "warning":None,
    }


def measured(*,text=True,fraction=.13):
    return {"passed":True,"text_bounds_verified":text,
            "product_bounds_verified":True,
            "product_visible_fraction":fraction}


def social_png(kind):
    w,h=FORMATS[kind][:2]
    image=Image.new("RGB",(w,h),"#082840")
    d=ImageDraw.Draw(image)
    d.rectangle((0,h//4,w,3*h//4),fill="#1675AF")
    d.rectangle((w//3,h//3,w*2//3,2*h//3),fill="#F8BD31")
    out=io.BytesIO();image.save(out,"PNG")
    return out.getvalue()


class MeasuredCriticGateTests(unittest.TestCase):
    def test_independent_ai_can_be_wrong_about_actual_glyph_and_hero_bounds(self):
        result=reconcile_with_measured_geometry(
            critique(price=["cutoff_text"],smart=["tiny_product"]),
            {"poster_price":measured(),"poster_smart":measured()})
        self.assertEqual(result["issues"]["poster_price"],[])
        self.assertEqual(result["issues"]["poster_smart"],[])
        self.assertEqual(result["geometry_disagreements"],{
            "poster_price":["cutoff_text"],
            "poster_smart":["tiny_product"],
        })
        self.assertIn("measurable",result["warning"])

    def test_never_clear_real_photo_contrast_diversity_or_unmeasured_text(self):
        result=reconcile_with_measured_geometry(
            critique(price=["cutoff_text","white_halo","poor_contrast",
                            "duplicate_layout"],
                     smart=["tiny_product","blurry_product"]),
            {"poster_price":measured(text=False),
             "poster_smart":measured(fraction=.051)})
        self.assertEqual(result["issues"]["poster_price"],[
            "cutoff_text","white_halo","poor_contrast","duplicate_layout"])
        self.assertEqual(result["issues"]["poster_smart"],[
            "tiny_product","blurry_product"])
        self.assertEqual(result["geometry_disagreements"],{})

    def test_only_explicitly_passing_source_measurements_can_resolve_fault(self):
        for report in (
            {},{"passed":False,"text_bounds_verified":True},
            {"passed":True,"text_bounds_verified":False},
            {"passed":True,"text_bounds_verified":True,
             "product_bounds_verified":False,"product_visible_fraction":.2},
        ):
            with self.subTest(report=report):
                result=reconcile_with_measured_geometry(
                    critique(smart=["tiny_product"]),{"poster_smart":report})
                self.assertEqual(result["issues"]["poster_smart"],["tiny_product"])

    def test_full_pack_can_pass_when_vision_misreads_real_measured_artwork(self):
        photo=image_bytes()
        events=[]
        analyses=[]
        original=[{"creative_canvas":PRICE},
                  {"creative_canvas":SMART},
                  {"creative_canvas":TECH}]
        source={"source":"No external photograph used","category":"hand_tools"}
        def inspected(render,role,source_photo,**kwargs):
            chosen=kwargs.get("variants",(1,))[0]
            result,geometry=render(chosen)
            # This test executes real Pillow typography, recording actual
            # glyph-safe zone boundaries and the real product image position.
            if geometry.get("text_bounds_verified"):
                self.assertFalse(geometry["truncated"])
                self.assertFalse(geometry["overlaps"])
            analyses.append((role,geometry))
            return result,{
                "passed":True,"score":96,"variation":chosen,
                "text_bounds_verified":geometry.get("text_bounds_verified",False),
                "product_bounds_verified":geometry.get("product_bounds_verified",False),
                "product_visible_fraction":geometry.get("product_visible_fraction"),
            }
        review=critique(price=["cutoff_text"],smart=["tiny_product"])
        with patch("campaign_hub._concepts",
                   return_value=(original,"gemini-assisted",[])), \
             patch("campaign_hub.find_scene",return_value=(None,source)), \
             patch("campaign_hub.require_good_asset",
                   return_value={"passed":True}), \
             patch("campaign_hub.choose_best",side_effect=inspected), \
             patch("campaign_hub.generate_format",
                   side_effect=lambda kind,*a,**kw:(
                       social_png(kind),{
                           "passed":True,"score":96,
                           "render_engine":"ai-original-format-canvas",
                           "native_dimensions":list(FORMATS[kind][:2]),
                       })), \
             patch("campaign_hub.check_distinctness",
                   return_value={"passed":True,"issues":[],"pairs":[]}), \
             patch("campaign_hub.review_finished_artworks",
                   return_value=review) as reviewer, \
             patch("flexible_canvas.product_photo",side_effect=fake_photo):
            pack=build_campaign(
                PRODUCT,photo,use_gemini=True,
                progress=lambda *args:events.append(args))
        self.assertEqual(reviewer.call_count,1)
        self.assertTrue(all(g["text_bounds_verified"] for _,g in analyses))
        self.assertTrue(all(g["product_bounds_verified"] for _,g in analyses))
        self.assertEqual(len([e for e in events if e[0]=="ready" and
                             e[1] in (*POSTERS,*FORMAT_ORDER)]),9)
        manifest=pack["manifest"]
        self.assertEqual(manifest["creative_critic"]["geometry_disagreements"],{
            "poster_price":["cutoff_text"],"poster_smart":["tiny_product"]})
        self.assertEqual(len([k for k in manifest["images"]
                              if k["id"] in (*POSTERS,*FORMAT_ORDER)]),9)
        self.assertTrue(pack["archive"].startswith(b"PK"))

if __name__=="__main__":
    unittest.main()
