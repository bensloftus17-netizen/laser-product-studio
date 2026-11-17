"""Regression for white photographic backgrounds *inside* a metal tool's frame.

A scissor-style ball-joint separator encloses a real hole between dark jaws.
That hole must show the advert's workshop photograph, not source photo paper.
Large white manufactured parts and small LASER lettering must remain intact.
"""
import io
import unittest
from PIL import Image,ImageDraw
from ai_photo_effects import manufacturer_cutout
from ai_promo_renderer import render_promo


class WhiteGapRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        photo=Image.new("RGB",(640,480),(248,248,246))
        draw=ImageDraw.Draw(photo)
        draw.rounded_rectangle((105,90,553,393),radius=16,fill=(33,42,49))
        # The open space between metal jaws is part of the BACKGROUND.
        draw.rectangle((212,192,426,307),fill=(248,248,246))
        # Separate pale LASER logo on the dark steel -- real product detail.
        draw.text((173,346),"LASER",fill=(250,250,250))
        # Pale metallic hardware is also part of the genuine tool.
        draw.ellipse((460,128,522,188),fill=(223,226,229))
        buf=io.BytesIO();photo.save(buf,format="PNG")
        cls.photo=buf.getvalue()

    def test_enclosed_white_rectangle_becomes_transparent(self):
        cutout,isolated=manufacturer_cutout(self.photo)
        self.assertTrue(isolated)
        # cropping uses only the outer mask bounds; locate the original
        # interior gap relative to those bounds, which should be near centre.
        alpha=cutout.getchannel("A")
        self.assertLess(alpha.getpixel((cutout.width//2,cutout.height//2)),50)
        self.assertGreater(alpha.getpixel((35,35)),230)

    def test_white_laser_markings_and_pale_metal_stay_opaque(self):
        cutout,isolated=manufacturer_cutout(self.photo)
        self.assertTrue(isolated)
        # The logo is below the gap and pale hardware is right of it.
        alpha=cutout.getchannel("A")
        self.assertGreater(alpha.getpixel((85,267)),220)
        self.assertGreater(alpha.getpixel((378,69)),220)

    def test_all_three_posters_keep_real_gap_transparent(self):
        product={"part":"8899","title":"Ball Joint Separator for JLR",
                 "features":["Scissor-type tool for Land Rover and Jaguar"],
                 "price":"£144.16 excluding VAT"}
        versions=[]
        for family in ("retail","premium","trade"):
            concept={"family":family,"headline":"Ball Joint Separator for JLR",
                     "subline":"Suspension service",
                     "features":product["features"],"variant":0}
            png=render_promo(concept,self.photo,product)
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
            versions.append(png)
        self.assertEqual(len(set(versions)),3)


if __name__=="__main__":
    unittest.main()
