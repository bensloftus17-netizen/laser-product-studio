"""V46: independently AI-designed social square, mobile Story and banners."""
import io
import unittest
from copy import deepcopy
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image,ImageDraw

from format_creative import (
    FORMATS,FORMAT_ORDER,format_instruction,validate_format_canvas,
    render_format_canvas,generate_format,quality_check_format,
)
from poster_quality import capture
from campaign_hub import build_campaign,FOLDERS
from campaign_director import plan_campaign
from test_ai_creative_director_v45 import TECH,PRICE,SMART,PRODUCT,image_bytes

SQUARE={
    "zones":{"headline":[65,165,490,135],
             "product":[540,325,375,380],
             "proof":[65,735,435,125],
             "price":[560,760,335,115]},
    "background":"industrial","mood":"bold","motif":"circles",
    "headline_role":"price_promo","scene_role":"technical_application",
    "proof_feature_index":0,"headline_style":"massive",
    "photo_focus":"left","accent":"#FFC83A",
}
STORY={
    "zones":{"headline":[70,175,640,115],
             "product":[80,322,810,326],
             "proof":[80,690,810,115]},
    "background":"workshop-photo","mood":"energetic",
    "headline_role":"technical_application","scene_role":"technical_application",
    "proof_feature_index":1,"headline_style":"editorial",
    "photo_focus":"right","accent":"#13B5EC",
}
WEB={
    "zones":{"headline":[55,270,480,230],
             "product":[600,240,325,555],
             "proof":[60,615,460,125]},
    "background":"studio-gradient","mood":"editorial",
    "headline_role":"product_selected","scene_role":"product_selected",
    "proof_feature_index":0,"headline_style":"compact",
    "accent":"#71D6EE",
}
EMAIL={
    "zones":{"headline":[55,270,470,245],
             "product":[600,270,330,475],
             "proof":[55,620,470,140]},
    "background":"studio-gradient","mood":"understated",
    "headline_role":"price_promo","scene_role":"price_promo",
    "proof_feature_index":1,"headline_style":"compact",
    "accent":"#13B5EC",
}
LINKEDIN={
    "zones":{"headline":[55,240,465,205],
             "product":[605,235,315,500],
             "proof":[60,590,455,160]},
    "background":"workshop-photo","mood":"editorial",
    "headline_role":"technical_application","scene_role":"technical_application",
    "proof_feature_index":2,"headline_style":"editorial",
    "accent":"#40C1E8",
}
LANDSCAPE={
    "zones":{"headline":[60,245,470,200],
             "product":[590,230,330,520],
             "proof":[65,600,445,145]},
    "background":"industrial","mood":"energetic",
    "headline_role":"product_selected","scene_role":"product_selected",
    "proof_feature_index":1,"headline_style":"massive",
    "accent":"#D9E75B",
}
FOUR=dict(zip(FORMAT_ORDER,(SQUARE,STORY,WEB,EMAIL,LINKEDIN,LANDSCAPE)))
FEATURES=PRODUCT["features"]
HEADLINES={
    "technical_application":"Ratchet Set 4pc",
    "price_promo":"Ratchet Set 4pc",
    "product_selected":"Ratchet Set 4pc",
}


def cutout_stub(blob):
    src=Image.new("RGBA",(530,420),(0,0,0,0))
    d=ImageDraw.Draw(src,"RGBA")
    d.rounded_rectangle((60,58,474,357),radius=30,
                        fill=(15,64,102,255),outline=(31,177,230,255),width=12)
    d.ellipse((160,117,342,295),fill=(228,167,49,255))
    return {"rgba":src,"isolated":True,"needs_manual_cutout":False}


class OriginalFormatCampaignTests(unittest.TestCase):
    def test_all_four_have_genuinely_separate_design_and_native_sizes(self):
        self.assertEqual(len(FORMATS),6)
        self.assertIn("NEVER copy/scale",format_instruction())
        shapes=[]
        for kind,raw in FOUR.items():
            with self.subTest(kind=kind):
                safe=validate_format_canvas(kind,raw,len(FEATURES))
                self.assertIsNotNone(safe)
                self.assertEqual(safe["zones"],raw["zones"])
                self.assertEqual(safe["source"],"AI-format-specific-canvas")
                shapes.append(tuple(safe["zones"]["product"]))
        self.assertEqual(len(set(shapes)),4)
        self.assertEqual(FORMATS["social_story"][:2],(1080,1920))
        self.assertEqual(FORMATS["website_banner"][:2],(1600,600))
        self.assertEqual(FORMATS["email_header"][:2],(1200,420))
        self.assertEqual(FORMATS["linkedin_graphic"][:2],(1200,627))
        self.assertEqual(FORMATS["landscape_ad"][:2],(1600,900))

    def test_rejects_overlap_bad_mobile_safe_area_and_untrusted_inputs(self):
        for kind,safe in FOUR.items():
            invalid=deepcopy(safe)
            invalid["zones"]["product"]=invalid["zones"]["headline"][:]
            self.assertIsNone(validate_format_canvas(kind,invalid,3))
        story=deepcopy(STORY)
        story["zones"]["headline"][1]=89
        self.assertIsNone(validate_format_canvas("social_story",story,3))
        bad=deepcopy(SQUARE)
        bad["zones"]["price"]=[60,150,200,100]
        self.assertIsNone(validate_format_canvas("social_square",bad,3))
        extra={**EMAIL,"text":"Amazing guaranteed offer",
               "tool_image_url":"https://invented.example/wrench.png"}
        accepted=validate_format_canvas("email_header",extra,3)
        self.assertNotIn("text",accepted)
        self.assertNotIn("tool_image_url",accepted)
        invalid_price=deepcopy(EMAIL)
        invalid_price["proof_feature_index"]=999
        self.assertIsNone(validate_format_canvas("bogus_format",EMAIL,3))
        self.assertIsNone(validate_format_canvas("email_header",{"zones":{}},3))
        self.assertIsNone(validate_format_canvas("email_header",None,3))
        self.assertIsNone(validate_format_canvas("email_header",[],3))
        self.assertIsNone(validate_format_canvas("email_header",
            {**EMAIL,"zones":{**EMAIL["zones"],"headline":[True,100,500,200]}},3))

    def test_actual_native_pngs_use_original_cutout_without_reinventing_tool(self):
        for kind,brief in FOUR.items():
            with self.subTest(kind=kind),\
                 patch("format_creative.inspected_product",side_effect=cutout_stub):
                with capture() as trace:
                    generated=render_format_canvas(
                        kind,brief,PRODUCT,image_bytes(),scenes=(None,None,None),
                        headlines=HEADLINES,facts=FEATURES,variant=0)
                with Image.open(io.BytesIO(generated)) as result:
                    self.assertEqual(result.size,FORMATS[kind][:2])
                    self.assertEqual(result.mode,"RGB")
                self.assertTrue(any(t["role"]=="headline" for t in trace.texts))
                self.assertTrue(trace.products)
                self.assertTrue(all(not t["truncated"] for t in trace.texts))
                report=quality_check_format(generated,kind,trace,{"passed":True})
                self.assertTrue(report["passed"],report)

    def test_qa_fails_damaged_photo_low_quality_and_missing_headline(self):
        for kind in FOUR:
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    generate_format(kind,FOUR[kind],PRODUCT,image_bytes(),
                        source_report={"passed":False},scenes=(None,None,None),
                        headlines=HEADLINES,facts=FEATURES)
        with patch("format_creative.inspected_product",side_effect=cutout_stub):
            with capture() as traced:
                image=render_format_canvas("social_square",SQUARE,PRODUCT,
                    image_bytes(),headlines=HEADLINES,facts=FEATURES)
        traced.texts.clear()
        out=quality_check_format(image,"social_square",traced,{"passed":True})
        self.assertFalse(out["passed"])
        self.assertIn("Missing headline",out["issues"])

    def test_generation_chooses_passing_candidate_and_reports_real_dimensions(self):
        with patch("format_creative.inspected_product",side_effect=cutout_stub):
            payload,report=generate_format(
                "website_banner",WEB,PRODUCT,image_bytes(),
                source_report={"passed":True},headlines=HEADLINES,facts=FEATURES)
        self.assertTrue(report["passed"])
        self.assertEqual(report["native_dimensions"],[1600,600])
        self.assertEqual(report["candidates_checked"],2)
        self.assertEqual(report["render_engine"],"ai-original-format-canvas")
        self.assertEqual(Image.open(io.BytesIO(payload)).size,(1600,600))

    def test_end_to_end_ai_uses_all_original_formats_and_correct_zip_paths(self):
        raw_concepts=[
            {"creative_canvas":PRICE,"ai_format_canvases":FOUR},
            {"creative_canvas":SMART},
            {"creative_canvas":TECH},
        ]
        fake=io.BytesIO()
        Image.new("RGB",(1200,1500),"#194A67").save(fake,format="PNG")
        poster=fake.getvalue()
        expected={}
        for kind,config in FOUR.items():
            image=Image.new("RGB",FORMATS[kind][:2],"#134968")
            buf=io.BytesIO();image.save(buf,"PNG")
            expected[kind]=buf.getvalue()
        poster_report={"passed":True,"score":92,"variation":1,
                       "warnings":[],"candidates_checked":1}
        source={"source":"No external photograph used","category":"hand_tools"}
        with patch("campaign_hub._concepts",return_value=(
                raw_concepts,"gemini-assisted",[])),\
             patch("campaign_hub.find_scene",return_value=(None,source)),\
             patch("campaign_hub.require_good_asset",return_value={"passed":True}),\
             patch("campaign_hub.choose_best",return_value=(poster,poster_report)),\
             patch("campaign_hub.review_finished_artworks",return_value={
                 "method":"test","reviewed":True,"issues":{},"warning":None}),\
             patch("campaign_hub.check_distinctness",return_value={
                 "passed":True,"issues":[],"pairs":[]}),\
             patch("campaign_hub.generate_format",side_effect=lambda kind,*args,**kwargs:
                 (expected[kind],{
                     "passed":True,"render_engine":"ai-original-format-canvas",
                     "native_dimensions":list(FORMATS[kind][:2])})) as render,\
             patch("campaign_hub._native_graphic") as legacy:
            pack=build_campaign(PRODUCT,image_bytes(),use_gemini=True)
        self.assertEqual(render.call_count,4)
        self.assertEqual(legacy.call_count,0)
        self.assertEqual(set(pack["manifest"]["ai_format_canvases"]),set(FOUR))
        self.assertEqual(set(pack["manifest"]["format_artwork_quality"]),set(FOUR))
        self.assertTrue(all(
            x["render_engine"]=="ai-original-format-canvas"
            for x in pack["manifest"]["format_artwork_quality"].values()))
        with ZipFile(io.BytesIO(pack["archive"])) as z:
            for kind in FORMAT_ORDER:
                self.assertEqual(z.read(FOLDERS[kind]),expected[kind])

    def test_missing_format_brief_falls_back_with_honest_warning(self):
        concepts=[
            {"creative_canvas":PRICE,"ai_format_canvases":{"social_square":SQUARE}},
            {"creative_canvas":SMART},{"creative_canvas":TECH}
        ]
        fake=io.BytesIO()
        Image.new("RGB",(1200,1500),"#194A67").save(fake,format="PNG")
        png=fake.getvalue()
        source={"source":"No external photograph used","category":"hand_tools"}
        with patch("campaign_hub._concepts",return_value=(
                concepts,"gemini-assisted",[])),\
             patch("campaign_hub.require_good_asset",return_value={"passed":True}),\
             patch("campaign_hub.find_scene",return_value=(None,source)),\
             patch("campaign_hub.choose_best",return_value=(png,{
                 "passed":True,"score":91,"variation":1,"warnings":[]})),\
             patch("campaign_hub.review_finished_artworks",return_value={
                 "method":"test","reviewed":True,"issues":{},"warning":None}),\
             patch("campaign_hub.check_distinctness",return_value={
                 "passed":True,"issues":[],"pairs":[]}),\
             patch("campaign_hub.generate_format",return_value=(png,{
                 "passed":True,"render_engine":"ai-original-format-canvas"})),\
             patch("campaign_hub._native_graphic",return_value=png) as old:
            pack=build_campaign(PRODUCT,image_bytes(),use_gemini=True)
        self.assertEqual(old.call_count,5)
        self.assertEqual(
            pack["manifest"]["format_artwork_quality"]["social_square"]["render_engine"],
            "ai-original-format-canvas")
        self.assertEqual(
            pack["manifest"]["format_artwork_quality"]["email_header"]["render_engine"],
            "verified-legacy-layout")
        self.assertTrue(any("No safe AI original layout" in w
                            for w in pack["manifest"]["warnings"]))


if __name__=="__main__":
    unittest.main()
