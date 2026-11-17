"""Gemini art direction must influence real layouts without inventing assets."""
import io
import json
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

from promo_art_direction import (
    PRICE_STYLES,normalise_art_direction,editor_preferences,scene_treatment,
    draw_background_motif)
from ai_promo_renderer import render_promo
from ai_concepts import propose


def packshot():
    im=Image.new("RGB",(600,400),"white")
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((86,72,505,334),radius=20,fill="#183958")
    b=io.BytesIO();im.save(b,format="PNG");return b.getvalue()


class AIArtDirectionTests(unittest.TestCase):
    def test_untrusted_model_fields_cannot_inject_urls_or_arbitrary_colours(self):
        art=normalise_art_direction({
            "layout_variant":77,"price_style":"flash-sale",
            "accent":"https://evil.site/invalid",
            "product_scale":500,"product_x":-1000,"product_y":"42",
            "graphic_motif":"javascript:alert()",
            "photo_focus":"bottom","background_mood":"photo_of_a_fake_tool"},
            family="retail")
        self.assertEqual(art["layout_variant"],0)
        self.assertIn(art["price_style"],PRICE_STYLES)
        self.assertEqual(art["product_scale"],125)
        self.assertEqual(art["product_x"],-30)
        self.assertEqual(art["product_y"],0)
        self.assertEqual(art["graphic_motif"],"speed-lines")
        self.assertEqual(art["photo_focus"],"centre")

    def test_model_can_choose_9_layouts_and_verified_product_is_unchanged(self):
        product={"title":"Battery Charger 12V", "part":"9385",
                 "price":"£129.00 excluding VAT",
                 "features":["12V charging with protective features"]}
        feature=product["features"][0]
        raw=[]
        for i in range(3):
            raw.append({
                "name":"Campaign","headline":"12V Battery Charger",
                "angle":"Verified charging features","subline":feature,
                "feature_ids":[0],
                "art_direction":{
                    "layout_variant":i,"price_style":("bubble","plaque","banner")[i],
                    "accent":("#F6D343","#13B5EC","#F9A842")[i],
                    "product_scale":110,"product_x":0,"product_y":0,
                    "graphic_motif":("circles","none","industrial-grid")[i],
                    "photo_focus":("left","centre","right")[i],
                    "background_mood":("bright","balanced","dramatic")[i],
                }
            })
        class MockResponse:
            status_code=200
            def raise_for_status(self):pass
            def json(self):return {
                "candidates":[{"content":{"parts":[{"text":json.dumps({"concepts":raw})}]}}]}
        with patch.dict("os.environ",{"GEMINI_API_KEY":"test-key"}), \
             patch("ai_concepts.requests.post",return_value=MockResponse()):
            concepts=propose(product)
        self.assertEqual([c["variant"] for c in concepts],[0,1,2])
        self.assertEqual([c["art_direction"]["photo_focus"] for c in concepts],
                         ["left","centre","right"])
        self.assertTrue(all(c["part"]=="9385" for c in concepts))
        self.assertTrue(all(c["features"]==[feature] for c in concepts))

    def test_scene_crop_mood_and_real_photo_motif_change_image(self):
        source={"crop":(.5,.5),"darkness":.25,"colour":.8}
        art=normalise_art_direction({
            "photo_focus":"right","graphic_motif":"circles",
            "background_mood":"dramatic","layout_variant":2},"trade")
        result=scene_treatment(source,art)
        self.assertGreater(result["crop"][0],.5)
        self.assertGreater(result["darkness"],source["darkness"])
        self.assertEqual(result["graphic_motif"],"circles")
        image=Image.new("RGB",(500,500),"#245676")
        painted=draw_background_motif(image,result)
        self.assertNotEqual(painted.tobytes(),image.convert("RGBA").tobytes())

    def test_editor_preferences_contain_no_model_image_or_price_fields(self):
        editor=editor_preferences(normalise_art_direction({
            "price":"£0.01","product_image":"fake.png",
            "layout_variant":1,"product_scale":113},"premium"))
        self.assertNotIn("price",editor)
        self.assertNotIn("product_image",editor)
        self.assertEqual(editor["product_scale"],113)

    def test_render_changes_when_ai_changes_layout(self):
        source=packshot()
        product={"title":"Ball Joint Separator","part":"8899",
                 "price":"£144.16 excluding VAT",
                 "features":["Suspension joint separator for workshop use"]}
        outputs=[]
        for layout in (0,1,2):
            concept={"family":"premium","variant":layout,
                     "headline":"Ball Joint Separator",
                     "features":product["features"]}
            art=normalise_art_direction({
                "layout_variant":layout,"graphic_motif":"circles",
                "price_style":"plaque"},"premium",layout)
            png=render_promo(concept,source,product,
               editor={**editor_preferences(art),
                       "_scene_style":scene_treatment({},art)})
            outputs.append(png)
        self.assertEqual(len(set(outputs)),3)


if __name__=="__main__":
    unittest.main()
