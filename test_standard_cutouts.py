"""Standard poster cutouts must match the tested AI manufacturer photo pipeline.

Regression for the *original* Hero, Technical and RRP posters: no flattened
white photo rectangle, true RGB/alpha compositing, and safe application photos.
"""
import io
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw

import poster
from ai_photo_effects import manufacturer_cutout


class StandardPosterCutoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        photo=Image.new("RGB",(600,420),(249,249,248))
        d=ImageDraw.Draw(photo)
        d.rounded_rectangle((100,75,507,334),radius=28,fill="#15364D")
        # A broad white photographic gap between the jaws of a scissor tool.
        d.rectangle((187,175,419,264),fill=(249,249,248))
        d.text((220,292),"LASER",fill="white")
        data=io.BytesIO();photo.save(data,format="PNG")
        cls.blob=data.getvalue()
        cls.product={
            "part":"8899","title":"Ball Joint Separator for JLR",
            "description":"Scissor-type separator for suspension joints.",
            "features":["For Land Rover and Jaguar suspension servicing.",
                        "Heavy-duty scissor-type construction."],
            "specs":{"Tool type":"Ball joint separator"},
            "price":"£144.16 excluding VAT"
        }

    def test_standard_uses_exact_same_cutout_as_ai(self):
        raw=poster.manufacturer_photo(self.blob)
        actual,worked=poster.isolated_photo(raw,self.blob)
        ai,ai_worked=manufacturer_cutout(self.blob)
        self.assertTrue(worked)
        self.assertEqual(worked,ai_worked)
        self.assertEqual(actual.size,ai.size)
        self.assertEqual(actual.tobytes(),ai.tobytes())
        center=actual.getchannel("A").getpixel(
            (actual.width//2,actual.height//2))
        self.assertLess(center,70,"White photographic opening should be transparent")

    def test_transparency_does_not_get_flattened_back_to_white(self):
        tool=Image.new("RGBA",(200,110),(0,0,0,0))
        d=ImageDraw.Draw(tool)
        d.rectangle((55,24,151,79),fill="#143A54")
        im=Image.new("RGB",(400,290),"#175581")
        with patch.object(poster,"manufacturer_cutout",return_value=(tool,True)):
            worked=poster.place_cutout(
                im,poster.manufacturer_photo(self.blob),
                (38,32,356,247),source_blob=self.blob)
        self.assertTrue(worked)
        self.assertEqual(im.getpixel((42,36)),(23,85,129))
        self.assertNotEqual(im.getpixel((200,140)),(255,255,255))
        # Technical image panels must also stay cool-blue where tool is absent.
        technical=Image.new("RGB",(400,290),"#092B4D")
        with patch.object(poster,"manufacturer_cutout",return_value=(tool,True)):
            poster.contain_photo(technical,poster.manufacturer_photo(self.blob),
                                 (28,32,369,252),background="#EAF2F8",
                                 cutout=True,source_blob=self.blob)
        self.assertEqual(technical.getpixel((33,37)),(234,242,248))
        self.assertNotEqual(technical.getpixel((33,37)),(255,255,255))

    def test_all_three_standard_posters_use_shared_manufacturer_cutout(self):
        for name,render,size in (
            ("Promotional",poster.render_hero,(1200,1800)),
            ("RRP",poster.render_price,(1600,980)),
        ):
            with self.subTest(name=name):
                with patch.object(poster,"manufacturer_cutout",
                                  wraps=manufacturer_cutout) as segmentation:
                    png=render(self.product,self.blob)
                    self.assertGreaterEqual(segmentation.call_count,1)
                with Image.open(io.BytesIO(png)) as result:
                    self.assertEqual(result.size,size)
                    self.assertEqual(result.mode,"RGB")
        for mode in ("light","medium","dense"):
            with self.subTest(technical_mode=mode), \
                 patch.object(poster,"technical_layout_mode",return_value=mode), \
                 patch.object(poster,"manufacturer_cutout",
                              wraps=manufacturer_cutout) as segmentation:
                png=poster.render_technical(self.product,self.blob)
                self.assertGreaterEqual(segmentation.call_count,1)
                with Image.open(io.BytesIO(png)) as result:
                    self.assertEqual(result.size,(1280,1590))
                    # The background outside the tool is light blue, not white.
                    self.assertNotEqual(result.getpixel((56,383)),
                                        (255,255,255))

    def test_technical_in_situ_image_remains_genuine(self):
        scene=Image.new("RGB",(640,420),"#3A6685")
        d=ImageDraw.Draw(scene)
        d.rectangle((155,80,545,365),fill="#A1B2C0")
        data=io.BytesIO();scene.save(data,format="PNG")
        with patch.object(poster,"technical_layout_mode",return_value="dense"):
            a=poster.render_technical(self.product,self.blob)
            b=poster.render_technical(self.product,self.blob,data.getvalue())
        self.assertNotEqual(a,b,"Real manufacturer application photo should remain available")

    def test_standard_assets_and_pdf_still_use_verified_source(self):
        assets=poster.create_posters(self.product,self.blob)
        self.assertEqual(set(assets),{"Hero","Technical","Price"})
        for png in assets.values():
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(poster.create_fact_sheet_pdf(self.product,self.blob)
                        .startswith(b"%PDF"))


if __name__=="__main__":
    unittest.main()
