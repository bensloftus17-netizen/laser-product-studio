"""V60 regressions: genuine creative freedom, not renamed navy templates.

Model-selected palettes and layouts must change real pixels for all formats.
No AI-drawn tools, fake prices, unsafe source text or hidden QA bypass.
"""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

from creative_expression import (
    PALETTES,normalise_expression,express_background,format_palette,
    DEFAULT_FORMAT_PALETTE,
)
from creative_director import validate_brief
from flexible_canvas import render_creative_canvas
from format_creative import (
    validate_format_canvas,render_format_canvas,quality_check_format,
    FORMATS,FORMAT_ORDER,
)
from campaign_hub import build_campaign,FOLDERS
from poster_quality import capture
from test_ai_creative_director_v45 import (
    TECH,PRICE,SMART,PRODUCT,image_bytes,fake_photo,
)
from test_ai_formats_v46 import SQUARE,STORY,EMAIL,cutout_stub


class CreativeFreedomV60Tests(unittest.TestCase):
    def test_seven_colour_choices_really_change_background_pixels(self):
        blank=Image.new("RGBA",(1200,1500),"#092D4C")
        rendered=[]
        for palette in PALETTES:
            result=express_background(
                blank,palette,"split_canvas",
                zones={"headline":(82,285,580,485)},
                hero_treatment="spotlight")
            self.assertEqual(result.size,(1200,1500))
            rendered.append(result.resize((75,95)).tobytes())
        self.assertGreaterEqual(len(PALETTES),7)
        self.assertEqual(len(set(rendered)),len(PALETTES))
        self.assertNotEqual(rendered[0],rendered[1])

    def test_six_visual_architectures_change_real_pixels(self):
        blank=Image.new("RGBA",(1080,1080),"#092B49")
        choices=("photo_editorial","bold_geometry","clean_minimal",
                 "cinematic","split_canvas","technical_infographic")
        results=[express_background(
            blank,"signal_yellow",treatment).resize((45,45)).tobytes()
            for treatment in choices]
        self.assertEqual(len(set(results)),len(choices))

    def test_invalid_model_expression_never_leaks_untrusted_commands(self):
        incoming={
            "creative_palette":"https://bad.example/my-cover.png",
            "visual_treatment":"__import__('os').system('rm -rf /')",
            "text_treatment":"javascript:alert(1)",
            "hero_treatment":"invent_a_new_product",
            "tool_url":"https://evil.example/fake-tool.png",
            "claims":"unverified 90 percent discount",
        }
        validated=validate_brief({**TECH,**incoming},"technical_application")
        for field in ("creative_palette","visual_treatment",
                      "text_treatment","hero_treatment"):
            self.assertIn(field,validated)
            self.assertNotEqual(validated[field],incoming[field])
        self.assertNotIn("claims",validated)
        self.assertNotIn("tool_url",validated)
        self.assertEqual(len(normalise_expression({},kind="social_story")),4)

    def test_poster_colours_and_text_frames_change_actual_art_not_tool(self):
        real_photo=image_bytes()
        styles=(
            ("studio_silver","clean_minimal","underline"),
            ("signal_yellow","bold_geometry","banner"),
            ("electric_violet","cinematic","panel"),
        )
        pixels=[]
        with patch("flexible_canvas.product_photo",side_effect=fake_photo) as use_photo:
            for palette,layout,typography in styles:
                original={**TECH,"creative_palette":palette,
                          "visual_treatment":layout,
                          "text_treatment":typography,
                          "hero_treatment":"graphic_frame"}
                concept={
                    "campaign_role":"technical_application",
                    "creative_canvas":original,
                    "headline":"Ratchet Set 4pc",
                    "selling_point":"Set of four ratchets.",
                }
                with capture() as tracked:
                    image=render_creative_canvas(
                        PRODUCT,real_photo,concept,variant=1)
                self.assertTrue(tracked.products)
                self.assertTrue(any(t["role"]=="headline" for t in tracked.texts))
                self.assertFalse(any(t["truncated"] for t in tracked.texts))
                pixels.append(Image.open(io.BytesIO(image))
                              .resize((65,80)).tobytes())
        self.assertEqual(len(set(pixels)),len(styles))
        self.assertEqual(use_photo.call_count,len(styles))
        self.assertTrue(all(x.args[1]==real_photo
                            for x in use_photo.call_args_list))

    def test_native_story_square_and_email_have_independent_styles_and_qa(self):
        photo=image_bytes()
        examples=(
            ("social_square",SQUARE,"signal_yellow","bold_geometry"),
            ("social_story",STORY,"cold_cyan","cinematic"),
            ("email_header",EMAIL,"studio_silver","split_canvas"),
        )
        images=[]
        with patch("format_creative.inspected_product",side_effect=cutout_stub):
            for kind,raw,palette,layout in examples:
                brief={**raw,"creative_palette":palette,
                       "visual_treatment":layout,"text_treatment":"underline"}
                parsed=validate_format_canvas(kind,brief,len(PRODUCT["features"]))
                self.assertEqual(parsed["creative_palette"],palette)
                with capture() as tracked:
                    output=render_format_canvas(
                        kind,brief,PRODUCT,photo,variant=0,
                        headlines={"technical_application":"Ratchet Set 4pc",
                                   "price_promo":"Ratchet Set 4pc",
                                   "product_selected":"Ratchet Set 4pc"},
                        facts=PRODUCT["features"])
                report=quality_check_format(output,kind,tracked,{"passed":True})
                self.assertTrue(report["passed"],(kind,report))
                self.assertEqual(Image.open(io.BytesIO(output)).size,
                                 FORMATS[kind][:2])
                images.append(output)
        self.assertEqual(len(images),3)

    def test_repeated_palette_choices_are_rebalanced_in_the_six_formats(self):
        chosen=[]
        for kind in FORMAT_ORDER:
            palette=format_palette(kind,"laser_blue",chosen)
            chosen.append(palette)
        self.assertGreaterEqual(len(set(chosen)),4)
        self.assertTrue(all(chosen.count(x)<=2 for x in chosen))
        self.assertEqual(set(DEFAULT_FORMAT_PALETTE),set(FORMAT_ORDER))

    def test_complete_pack_preserves_six_different_palette_choices(self):
        models=[
            {"creative_canvas":{**PRICE,"creative_palette":"signal_yellow"},
             "creative_direction":{"creative_family":"commercial_burst",
                                   "creative_palette":"signal_yellow"}},
            {"creative_canvas":{**SMART,"creative_palette":"electric_violet"},
             "creative_direction":{"creative_family":"premium_spotlight",
                                   "creative_palette":"electric_violet"}},
            {"creative_canvas":{**TECH,"creative_palette":"studio_silver"},
             "creative_direction":{"creative_family":"engineering_grid",
                                   "creative_palette":"studio_silver"}},
        ]
        fake=image_bytes(1200,1500)
        palette_kwargs=[]
        def native(product,photo,dist,kind,fact,*args,**kw):
            palette_kwargs.append((kind,kw.get("creative_palette"),photo))
            w,h=FORMATS[kind][:2]
            buf=io.BytesIO()
            Image.new("RGB",(w,h),"#0A5480").save(buf,"PNG")
            return buf.getvalue()
        with patch("campaign_hub._concepts",return_value=(
                models,"gemini-assisted",[])), \\
             patch("campaign_hub.find_scene",return_value=(
                None,{"source":"No external photograph used",
                      "category":"hand_tools"})), \\
             patch("campaign_hub.require_good_asset",
                   return_value={"passed":True}), \\
             patch("campaign_hub.choose_best",
                   return_value=(fake,{"passed":True,"score":95,
                                       "variation":1})), \\
             patch("campaign_hub._native_graphic",side_effect=native), \\
             patch("campaign_hub.check_distinctness",return_value={
                "passed":True,"issues":[],"pairs":[]}), \\
             patch("campaign_hub.review_finished_artworks",return_value={
                "method":"test","reviewed":True,
                "issues":{},"warning":None}):
            pack=build_campaign(PRODUCT,image_bytes(),use_gemini=True)
        self.assertEqual(len(palette_kwargs),6)
        self.assertEqual(len({p for _,p,_ in palette_kwargs}),6)
        self.assertTrue(all(photo==image_bytes() for _,_,photo in palette_kwargs))
        styles=pack["manifest"]["creative_plan"]["format_palettes"]
        self.assertEqual(len(styles),6)
        self.assertEqual(len(set(styles.values())),6)
        self.assertEqual(
            [a["creative_palette"] for a in pack["manifest"]["angles"]],
            ["studio_silver","signal_yellow","electric_violet"])
        self.assertTrue(all(
            pack["manifest"]["format_artwork_quality"][kind]["creative_palette"]==
            styles[kind] for kind in FORMAT_ORDER))
        with ZipFile(io.BytesIO(pack["archive"])) as z:
            self.assertTrue(all(path in z.namelist() for path in FOLDERS.values()))


if __name__=="__main__":
    unittest.main()
