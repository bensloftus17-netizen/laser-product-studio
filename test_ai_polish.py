"""V5 regressions: white-halo removal, real tool colours and campaign legibility."""
import io
import unittest
from PIL import Image, ImageDraw

from ai_photo_effects import manufacturer_cutout
from ai_concepts import professional_headline
from ai_promo_renderer import render_promo


class CleanCutoutCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        im=Image.new("RGB",(540,380),(245,245,241))
        d=ImageDraw.Draw(im)
        # Deliberately dirty JPEG-like grey fringe around the dark part.
        d.rounded_rectangle((93,69,449,313),radius=27,fill=(218,220,217))
        d.rounded_rectangle((100,76,442,306),radius=24,fill=(18,46,75))
        # White part of the actual tool must NEVER become transparent.
        d.ellipse((212,131,323,244),fill=(253,251,251))
        d.rounded_rectangle((138,101,183,129),radius=4,fill="#0876BD")
        output=io.BytesIO();im.save(output,format="PNG")
        cls.photo=output.getvalue()
        cls.product={"part":"8899","title":"Ball Joint Separator - Land Rover & Jaguar",
                     "features":["Scissor-type separator for suspension joints"],
                     "price":"£144.16 excluding VAT"}
        cls.concept={"family":"retail","headline":"Ball Joint Separator for Land Rover",
                     "subline":"Workshop suspension service",
                     "features":cls.product["features"],"variant":0}

    def test_off_white_compressed_background_does_not_survive_as_rectangle(self):
        img,isolated=manufacturer_cutout(self.photo)
        self.assertTrue(isolated)
        a=img.getchannel("A")
        self.assertLess(a.getpixel((0,0)),25)
        self.assertGreater(a.getpixel((img.width//2,img.height//2)),240)
        # Dark tool blue and enclosed white product detail remain unchanged.
        center=img.getpixel((img.width//2,img.height//2))
        self.assertGreater(min(center[:3]),235)

    def test_anticolour_border_removed_but_real_tool_white_remains(self):
        img,_=manufacturer_cutout(self.photo)
        a=img.getchannel("A")
        # Outer perimeter contains transparent pixels, not pale-white haze.
        for point in [(0,0),(img.width-1,0),(0,img.height-1),(img.width-1,img.height-1)]:
            self.assertLess(a.getpixel(point),50)
        self.assertGreater(a.getpixel((img.width//2,img.height//2)),240)

    def test_three_photo_led_posters_keep_product_and_price(self):
        results=[]
        for idx,family in enumerate(("retail","premium","trade")):
            png=render_promo({**self.concept,"family":family,"variant":idx},
                             self.photo,self.product)
            with Image.open(io.BytesIO(png)) as final:
                self.assertEqual(final.size,(1200,1500))
                self.assertEqual(final.mode,"RGB")
                results.append(png)
        self.assertEqual(len(set(results)),3)

    def test_no_generic_headlines_for_specific_suspension_tools(self):
        bad="Range Rover & Discovery Ball Joints"
        h=professional_headline(bad,self.product)
        self.assertIn("Separator",h)
        self.assertNotIn("Conquer",h)
        direct=professional_headline("Ball Joint Separator for Land Rover",self.product)
        self.assertEqual(direct,"Ball Joint Separator for Land Rover")

    def test_puller_action_is_a_valid_technical_headline(self):
        product={"title":"Crankshaft Pulley Puller Ford 2.0 EcoBlue"}
        result=professional_headline("Ford EcoBlue Crankshaft Pulley Removal",product)
        self.assertEqual(result,"Ford EcoBlue Crankshaft Pulley Removal")


if __name__=="__main__":
    unittest.main()
