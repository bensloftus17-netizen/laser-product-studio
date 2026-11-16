"""Tests for genuinely distinct, free-tier Gemini-directed poster compositions."""
import io
import json
import os
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

from ai_creative_engine import W,H,STYLE_GROUPS,RENDERERS,render_concept
from ai_concepts import propose
from ai_promo_renderer import FAMILIES


class CreativeCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        im=Image.new("RGB",(550,380),"white")
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((110,165,455,230),radius=20,fill="#1F313D")
        d.ellipse((110,130,210,265),fill="#1F313D")
        d.ellipse((130,150,190,245),fill="#CFDCE6")
        d.text((30,35),"LASER",fill="#152D47")
        buff=io.BytesIO()
        im.save(buff,"PNG")
        cls.photo=buff.getvalue()
        cls.record={"part":"9364","title":"Three-piece ratchet set",
                    "headline":"Precision from every angle",
                    "subline":"Three ratchets with verified drive sizes",
                    "angle":"A real workshop tool assortment",
                    "features":["Ratchet with 72 teeth","Three drive sizes"]}

    def test_nine_distinct_dramatic_art_directions(self):
        rendered=[]
        for family in STYLE_GROUPS:
            for style in family:
                with self.subTest(style=style):
                    b=render_concept({**self.record,"visual_style":style},self.photo)
                    self.assertTrue(b.startswith(b"\x89PNG\r\n\x1a\n"))
                    self.assertGreater(len(b),15000)
                    with Image.open(io.BytesIO(b)) as im:
                        self.assertEqual(im.size,(W,H))
                        self.assertEqual(im.mode,"RGB")
                        rendered.append((style,b,im.getpixel((10,10)),im.getpixel((800,200))))
        self.assertEqual(len(rendered),9)
        self.assertEqual(len({b for _,b,_,_ in rendered}),9)
        # The groups genuinely contrast in background and spatial hierarchy.
        self.assertNotEqual(rendered[0][2],rendered[4][2])
        self.assertNotEqual(rendered[4][3],rendered[7][3])

    def test_text_stays_within_bounded_region(self):
        from ai_creative_engine import _txt
        canvas=Image.new("RGB",(600,300),"white")
        d=ImageDraw.Draw(canvas)
        _txt(d,"INCOMPREHENSIBLY LONG MARKETING COPY "*25,
             (55,44,535,236),(64,55,46,38,30,23,17),
             "#0A2C4D","bold",5)
        pixels=canvas.load()
        for y in range(300):
            for x in range(600):
                if x<55 or x>=535 or y<44 or y>=236:
                    self.assertEqual(pixels[x,y],(255,255,255))

    def test_model_picks_styles_from_different_families(self):
        results={"concepts":[
            {"name":"Campaign","headline":"The right tools","subline":"Ratchets for workshops",
             "visual_style":"retail","angle":"Retail campaign","feature_ids":[0]},
            {"name":"Editorial","headline":"A genuine set","subline":"Complete workshop assortment",
             "visual_style":"minimal","angle":"Editorial campaign","feature_ids":[1]},
            {"name":"Technical","headline":"Three ratchets","subline":"Three sizes",
             "visual_style":"blueprint","angle":"Technical campaign","feature_ids":[0,1]},
        ]}
        class FakeResponse:
            def raise_for_status(self): return None
            def json(self):
                return {"candidates":[{"content":{"parts":[{"text":json.dumps(results)}]}}]}
        manufacturer={**self.record,"description":"Ratchet set","specs":{},
                      "marketing_direction":{"category_label":"Socket and ratchet sets"}}
        with patch.dict(os.environ,{"GEMINI_API_KEY":"not-a-real-key"}),patch("ai_concepts.requests.post",return_value=FakeResponse()) as post:
            concepts=propose(manufacturer,creative_brief="bold launch campaign")
        self.assertEqual([c["family"] for c in concepts],list(FAMILIES))
        self.assertTrue(all(0<=c["variant"]<=2 for c in concepts))
        self.assertEqual(concepts[0]["features"][:1],["Ratchet with 72 teeth"])
        self.assertTrue(all(v in manufacturer["features"] for v in concepts[0]["features"]))
        # The user now never needs a creative prompt: the AI is given official product data.
        self.assertNotIn("bold launch campaign",post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"])

    def test_gemini_bare_array_output_is_accepted(self):
        """The live Google model sometimes returns a JSON array, not a wrapper."""
        result=[
            {"name":"Campaign","headline":"Three ratchets","subline":"Professional tool set",
             "visual_style":"cinematic","angle":"Hero promotion","feature_ids":[0]},
            {"name":"Editorial","headline":"Designed for the job","subline":"Chrome vanadium ratchets",
             "visual_style":"editorial","angle":"Workshop story","feature_ids":[1]},
            {"name":"Details","headline":"Drive sizes","subline":"Verified specifications",
             "visual_style":"data","angle":"Specification story","feature_ids":[0,1]},
        ]
        class FakeResponse:
            def raise_for_status(self):return None
            def json(self):
                return {"candidates":[{"content":{"parts":[{"text":json.dumps(result)}]}}]}
        with patch.dict(os.environ,{"GEMINI_API_KEY":"not-a-real-key"}),patch("ai_concepts.requests.post",return_value=FakeResponse()):
            concepts=propose({**self.record,"description":"Three ratchets","specs":{}})
        self.assertEqual(len(concepts),3)
        self.assertEqual([c["family"] for c in concepts],list(FAMILIES))

    def test_invalid_model_styles_are_safely_constrained(self):
        import ai_creative_engine
        self.assertEqual(len(STYLE_GROUPS),3)
        self.assertEqual(len(set.union(*map(set,STYLE_GROUPS))),len(RENDERERS))


if __name__=="__main__":
    unittest.main()
