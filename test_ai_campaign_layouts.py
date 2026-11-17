"""Prevent a regression to three identical navy-header promotional layouts.

The three image families must have different dominant composition, legible
manufacturer product imagery, reliable RRP badges and no background-only white
rectangle inside an open-frame tool.
"""
import io
import unittest
from PIL import Image,ImageDraw
from ai_photo_effects import manufacturer_cutout
from ai_promo_renderer import render_promo


def demo_tool():
    img=Image.new("RGB",(700,520),(246,246,244))
    d=ImageDraw.Draw(img)
    # Dark jaws at distinct angles create a non-square hole, like a scissor
    # type ball-joint tool; source background through the opening is white.
    d.polygon([(110,130),(540,92),(552,144),(122,183)],fill="#242E33")
    d.polygon([(122,397),(545,341),(552,390),(115,449)],fill="#242E33")
    d.polygon([(522,115),(564,118),(570,374),(530,370)],fill="#1D262C")
    d.polygon([(126,168),(171,171),(175,422),(132,421)],fill="#27353C")
    d.polygon([(214,209),(476,177),(482,306),(213,338)],fill=(246,246,244))
    d.text((242,366),"LASER",fill=(252,252,252))
    buf=io.BytesIO();img.save(buf,format="PNG")
    return buf.getvalue()


class DistinctCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product={"part":"8899","title":"Ball Joint Separator for JLR",
                     "features":["Scissor-type tool for suspension joints"],
                     "price":"£144.16 excluding VAT"}
        cls.image=demo_tool()

    def test_manufacturer_photo_opening_is_not_an_opaque_white_slab(self):
        cutout,isolated=manufacturer_cutout(self.image)
        self.assertTrue(isolated)
        # Sampling the same off-white polygon must be transparent; real tool
        # metal above and below the gap stays opaque.
        a=cutout.getchannel("A")
        # Cropped tool bbox starts near x=110, y=92.
        self.assertLess(a.getpixel((210,158)),65)
        self.assertGreater(a.getpixel((210,35)),200)

    def test_retail_premium_trade_have_different_compositional_backgrounds(self):
        images={}
        for family in ("retail","premium","trade"):
            concept={"family":family,"variant":0,
                     "headline":"Ball Joint Separator for JLR",
                     "subline":"Scissor-type workshop tool",
                     "features":self.product["features"]}
            png=render_promo(concept,self.image,self.product)
            with Image.open(io.BytesIO(png)) as img:
                images[family]=img.convert("RGB").copy()

        # Retail is now vibrant and bright, Premium is pale editorial, while
        # Trade is intentionally a dark, full-bleed photographic campaign.
        for family in ("retail","premium"):
            r,g,b=images[family].getpixel((35,700))
            self.assertGreater((r+g+b)/3,160)
        r,g,b=images["trade"].getpixel((35,700))
        self.assertLess((r+g+b)/3,155)

        # Their centre and side compositions must differ substantially,
        # not just by recolouring the same shapes or changing the headline.
        scaled=[v.resize((30,38)).tobytes() for v in images.values()]
        for i in range(3):
            for j in range(i+1,3):
                a,b=scaled[i],scaled[j]
                divergent=sum(1 for p,q in zip(a,b) if abs(p-q)>55)
                self.assertGreater(divergent/(len(a)),.08)

    def test_price_placement_and_style_controls_still_work(self):
        for family in ("retail","premium","trade"):
            concept={"family":family,"variant":0,
                     "headline":"Ball Joint Separator for JLR",
                     "subline":"For workshop suspension repair",
                     "features":self.product["features"]}
            original=render_promo(concept,self.image,self.product)
            edited=render_promo(concept,self.image,self.product,editor={
                "price_position":"opposite","price_style":"tag",
                "headline_size":"large","show_subline":True})
            self.assertNotEqual(original,edited)


if __name__=="__main__":
    unittest.main()
