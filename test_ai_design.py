"""Regression checks for the optional Gemini-backed creative poster renderer."""
import io
import unittest

from PIL import Image, ImageDraw

from ai_design import W, H, render_concept, _text


class CreativePosterTests(unittest.TestCase):
    def setUp(self):
        im=Image.new("RGB",(800,470),"white")
        d=ImageDraw.Draw(im)
        d.ellipse((180,45,580,425),fill="#203447")
        d.rectangle((310,120,500,290),fill="#E1E9ED")
        out=io.BytesIO()
        im.save(out,"PNG")
        self.photo=out.getvalue()
        self.base={
            "part":"9395",
            "title":"Front Wheel Bearing Kit for Mercedes-Benz Sprinter and VW Crafter",
            "headline":"A better view of the job at hand",
            "subline":"Designed for the applications listed by the manufacturer",
            "angle":"Workshop application and features",
            "features":["Clamshells for wheel bearing removal and installation",
                        "Application: Mercedes-Benz Sprinter and VW Crafter"],
        }

    def test_three_distinct_compositions_are_valid_downloadable_pngs(self):
        outputs={}
        for kind in ("spotlight","split","technical"):
            data=render_concept({**self.base,"layout":kind},self.photo)
            with Image.open(io.BytesIO(data)) as img:
                self.assertEqual(img.size,(W,H))
                self.assertEqual(img.format,"PNG")
                self.assertEqual(img.mode,"RGB")
                # Distinct top left, middle and bottom palette / layout pixels.
                outputs[kind]=(data,img.getpixel((20,210)),img.getpixel((250,900)))
        self.assertEqual(len({v[0] for v in outputs.values()}),3)
        self.assertNotEqual(outputs["spotlight"][1],outputs["technical"][1])
        self.assertNotEqual(outputs["split"][2],outputs["technical"][2])

    def test_long_copy_and_missing_feature_lists_do_not_crash(self):
        concept={**self.base,"layout":"technical",
                 "headline":"Impossible to fit " * 25,
                 "subline":"Additional extended text " * 35,
                 "features":[]}
        data=render_concept(concept,self.photo)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_typography_stays_inside_bounding_region(self):
        img=Image.new("RGB",(600,270),"white")
        d=ImageDraw.Draw(img)
        _text(d,"WIDE TEXT "*45,(60,40,520,220),
              (55,50,44,38,31,25,20,16),"#112233","bold",5)
        # Writing can never extend past the right or bottom of its box.
        pixels=img.load()
        for y in range(270):
            for x in range(600):
                if not (60 <= x < 520 and 40 <= y < 220):
                    self.assertEqual(pixels[x,y],(255,255,255))


if __name__=="__main__":
    unittest.main()
