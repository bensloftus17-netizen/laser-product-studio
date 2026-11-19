"""V55: full campaign survives AI Story text-zone failures without fake quality success."""
import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from PIL import Image, ImageDraw

from format_creative import (FORMATS,FORMAT_ORDER,generate_format,
                             quality_check_safe_native)
from campaign_hub import build_campaign,FOLDERS
from test_ai_formats_v46 import STORY,FOUR,HEADLINES,cutout_stub
from test_ai_creative_director_v45 import TECH,PRICE,SMART,PRODUCT,image_bytes
from flexible_canvas import _role_art_direction
from creative_director import validate_brief


def coloured_native(kind):
    w,h=FORMATS[kind][:2]
    im=Image.new("RGB",(w,h),"#092c4b")
    d=ImageDraw.Draw(im)
    d.rectangle((0,h//3,w,h*2//3),fill="#0c8ac6")
    d.ellipse((w//3,h//3,w*2//3,h*2//3),fill="#f4ba35")
    out=io.BytesIO()
    im.save(out,format="PNG")
    return out.getvalue()


class ReliableDemoCampaignTests(unittest.TestCase):
    def test_long_exact_official_story_copy_recovers_on_new_type_variants(self):
        long_title="Ratchet Set 4pc - "+("Professional Workshop Applications " * 9)
        long_fact=("Use this professional ratchet set for workshop work "
                   "under the manufacturer's listed conditions. " * 9)
        source=[long_fact,"Set of four ratchets."]
        product=dict(PRODUCT,title=long_title,features=source)
        with patch("format_creative.inspected_product",side_effect=cutout_stub):
            png,qa=generate_format(
                "social_story",STORY,product,image_bytes(),
                headlines={
                    "technical_application":long_title,
                    "price_promo":"Ratchet Set 4pc",
                    "product_selected":long_title,
                },facts=source,source_report={"passed":True})
        self.assertTrue(qa["passed"])
        self.assertTrue(qa["verified_copy_reflow"])
        self.assertIn(qa["variation"],(2,3))
        self.assertEqual(qa["candidates_checked"],4)
        self.assertEqual(Image.open(io.BytesIO(png)).size,(1080,1920))

    def test_fallback_quality_rejects_non_native_white_and_bad_source(self):
        png=coloured_native("social_story")
        self.assertTrue(quality_check_safe_native(
            png,"social_story",{"passed":True})["passed"])
        self.assertFalse(quality_check_safe_native(
            png,"social_story",{"passed":False})["passed"])
        blank=io.BytesIO()
        Image.new("RGB",FORMATS["social_story"][:2],"white").save(blank,"PNG")
        self.assertFalse(quality_check_safe_native(
            blank.getvalue(),"social_story",{"passed":True})["passed"])

    def _build(self,fail_backup=False):
        concepts=[
            {"creative_canvas":PRICE,"ai_format_canvases":FOUR},
            {"creative_canvas":SMART},{"creative_canvas":TECH},
        ]
        poster=image_bytes(1200,1500)
        events=[]
        def render_format(kind,*args,**kwargs):
            if kind=="social_story":
                raise ValueError("AI social_story artwork rejected by quality "
                                 "controls: Verified copy does not fit AI-designed text zone")
            return coloured_native(kind),{
                "passed":True,"score":95,"render_engine":"ai-original-format-canvas",
                "native_dimensions":list(FORMATS[kind][:2]),
            }
        def render_safe(product,photo,distributor,kind,fact,**kwargs):
            self.assertEqual(kind,"social_story")
            return coloured_native(kind)
        with patch("campaign_hub._concepts",return_value=(
                concepts,"gemini-assisted",[])), \
             patch("campaign_hub.find_scene",return_value=(
                None,{"source":"No external photograph used","category":"hand_tools"})), \
             patch("campaign_hub.require_good_asset",return_value={"passed":True}), \
             patch("campaign_hub.choose_best",return_value=(
                poster,{"passed":True,"score":90,"variation":1})), \
             patch("campaign_hub.render_creative_canvas",return_value=poster), \
             patch("campaign_hub.generate_format",side_effect=render_format), \
             patch("campaign_hub._native_graphic",side_effect=render_safe), \
             patch("campaign_hub.check_distinctness",return_value={
                "passed":True,"issues":[],"pairs":[]}), \
             patch("campaign_hub.review_finished_artworks",return_value={
                "method":"test","reviewed":True,"issues":{},"warning":None}), \
             patch("campaign_hub.quality_check_safe_native",
                   side_effect=(
                    lambda blob,kind,source: {"passed":False,"issues":["source rejected"]}
                    if fail_backup else quality_check_safe_native(blob,kind,source))):
            try:
                pack=build_campaign(
                    PRODUCT,image_bytes(),use_gemini=True,
                    progress=lambda *args:events.append(args))
                return pack,events
            except ValueError:
                if not fail_backup:raise
                return None,events

    def test_story_failure_falls_back_to_full_valid_nine_format_zip(self):
        pack,events=self._build()
        self.assertIsNotNone(pack)
        self.assertEqual(
            len([e for e in events if e[0]=="ready" and e[1] in FOLDERS]),9)
        self.assertEqual(pack["manifest"]["format_artwork_quality"]
                         ["social_story"]["render_engine"],"verified-native-recovery")
        with ZipFile(io.BytesIO(pack["archive"])) as z:
            for id,path in FOLDERS.items():
                self.assertIn(path,z.namelist())
        self.assertTrue(any("social_story used a verified" in w for w
                            in pack["manifest"]["warnings"]))

    def test_rejected_story_backup_does_not_hide_separately_approved_posters(self):
        pack,events=self._build(fail_backup=True)
        self.assertIsNone(pack)
        self.assertEqual(
            len([e for e in events if e[0]=="ready" and e[1] in
                 ("poster_technical","poster_price","poster_smart")]),3)
        self.assertTrue(any(
            e[0]=="failed" and e[1]=="social_story" for e in events))

    def test_five_ai_chosen_composition_modes_change_actual_pixels(self):
        import copy
        from creative_director import COMPOSITION_MODES
        blank=Image.new("RGBA",(1200,1500),"#0A2948")
        results=[]
        for mode in COMPOSITION_MODES:
            proposed=copy.deepcopy(TECH)
            proposed["composition_mode"]=mode
            brief=validate_brief(proposed,"technical_application")
            self.assertEqual(brief["composition_mode"],mode)
            results.append(_role_art_direction(
                blank,brief,"technical_application").tobytes())
        self.assertEqual(len(set(results)),len(COMPOSITION_MODES))

    def test_ai_freeform_roles_have_distinct_real_rendered_visual_languages(self):
        blank=Image.new("RGBA",(1200,1500),"#0A2948")
        scenes=[]
        for role,original in (
            ("technical_application",TECH),
            ("price_promo",PRICE),
            ("product_selected",SMART),
        ):
            brief=validate_brief(original,role)
            self.assertIsNotNone(brief)
            image=_role_art_direction(blank,brief,role)
            scenes.append(image.tobytes())
        self.assertEqual(len(set(scenes)),3)


if __name__=="__main__":
    unittest.main()
