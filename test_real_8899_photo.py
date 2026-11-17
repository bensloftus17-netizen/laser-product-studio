"""Optional live-source check: the REAL official 8899 manufacturer JPG.

Runs in CI when the public Laser Tools image host is reachable. The test
doesn't modify, fake or replace the genuine tool photograph.
"""
import io
import unittest
import requests
from PIL import Image,ImageChops
from ai_photo_effects import manufacturer_cutout


class Genuine8899WhiteGapTests(unittest.TestCase):
    def test_manufacturer_8899_jpg_has_no_large_opaque_white_paper(self):
        try:
            r=requests.get("https://www.lasertools.co.uk/items/xlarge/8899.jpg",
                           timeout=(3,12))
            r.raise_for_status()
            image=Image.open(io.BytesIO(r.content))
            image.verify()
        except (requests.RequestException,ValueError,OSError) as exc:
            self.skipTest("Public manufacturer image unavailable: "+str(exc)[:110])
        cutout,isolated=manufacturer_cutout(r.content)
        self.assertTrue(isolated,"Official 8899 JPG failed safe background separation")
        alpha=cutout.getchannel("A")
        rgb=cutout.convert("RGB")
        lo=ImageChops.darker(ImageChops.darker(rgb.getchannel("R"),
                              rgb.getchannel("G")),rgb.getchannel("B"))
        hi=ImageChops.lighter(ImageChops.lighter(rgb.getchannel("R"),
                              rgb.getchannel("G")),rgb.getchannel("B"))
        white=ImageChops.multiply(
             lo.point(lambda v:255 if v>=226 else 0),
             ImageChops.subtract(hi,lo).point(lambda v:255 if v<=31 else 0))
        white=ImageChops.multiply(white,alpha.point(lambda a:255 if a>=200 else 0))
        remaining=white.histogram()[255]
        fraction=remaining/(cutout.width*cutout.height)
        print("Official 8899 cutout dimensions:",cutout.size,
              "remaining opaque paper-white fraction:",round(fraction,4),
              "original source:",r.url)
        # Small white LASER lettering is permitted. A large rectangular
        # white gap through the scissor arms is NOT.
        self.assertLess(fraction,.038,
                        "A broad opaque white hole remains inside official 8899 tool")


if __name__=="__main__":
    unittest.main()
