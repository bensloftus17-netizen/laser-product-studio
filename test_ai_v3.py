"""V3 promotional design studio tests: safe cutouts, source photos, editing options."""
import base64
import io
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

import app as studio
from ai_photo_effects import manufacturer_cutout, scene_category
from ai_promo_renderer import FAMILIES, render_promo
from ai_concepts import professional_headline


class StudioV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        photo=Image.new("RGB",(480,320),"white")
        d=ImageDraw.Draw(photo)
        d.rounded_rectangle((65,58,411,256),radius=24,fill="#112A4B")
        d.ellipse((206,103,335,221),fill="#FFFFFF")
        d.line((75,270,407,270),fill="#263C56",width=7)
        blob=io.BytesIO();photo.save(blob,format="PNG")
        cls.photo=blob.getvalue()
        cls.product={
            "part":"9385","title":"Crankshaft Pulley Puller Ford 2.0 EcoBlue",
            "description":"Pulley removal for Ford engines",
            "price":"£176.64 excluding VAT",
            "price_source":"Official manufacturer",
            "features":["For Ford EcoBlue crankshaft pulleys",
                        "Three-leg puller construction"],
            "specs":{}}
        cls.concept={"id":0,"part":"9385","title":cls.product["title"],
                     "family":"retail","name":"Retail Promo","variant":0,
                     "headline":"Ford EcoBlue Crankshaft Pulley Removal",
                     "subline":"Suitable for workshop pulley removal",
                     "angle":"Task-led promotion",
                     "features":[cls.product["features"][0]]}

    def test_white_background_becomes_transparent_without_erasing_white_tool_parts(self):
        img,worked=manufacturer_cutout(self.photo)
        self.assertTrue(worked)
        alpha=img.getchannel("A")
        self.assertLess(alpha.getpixel((0,0)),80)
        self.assertGreater(alpha.getpixel((img.width//2,img.height//2)),190)
        self.assertGreater(img.width,200)

    def test_nonwhite_photograph_is_not_aggressively_cut_out(self):
        photo=Image.new("RGB",(340,200),"#274E66")
        data=io.BytesIO();photo.save(data,format="PNG")
        img,worked=manufacturer_cutout(data.getvalue())
        self.assertFalse(worked)
        self.assertEqual(img.getchannel("A").getextrema(),(255,255))

    def test_product_scene_context_is_not_claimed_as_a_real_demonstration(self):
        self.assertEqual(scene_category(self.product),"engine")
        self.assertEqual(scene_category({"title":"Ratchet and socket set"}),"bench")
        baseline=render_promo(self.concept,self.photo,self.product)
        scenes=[]
        for family in FAMILIES:
            concept={**self.concept,"family":family}
            promo=render_promo(concept,self.photo,self.product,editor={
                "background":"context","display_mode":"shadow","product_scale":125,
                "product_x":-40,"product_y":25,"background_intensity":65,
                "price_style":"plaque","headline_size":"small",
                "show_subline":True,"shape_intensity":3})
            with Image.open(io.BytesIO(promo)) as img:
                self.assertEqual(img.size,(1200,1500))
                self.assertEqual(img.mode,"RGB")
            scenes.append(promo)
        self.assertEqual(len(set(scenes)),3)
        self.assertNotEqual(baseline,scenes[0])

    def test_cheesy_headlines_are_replaced_with_manufacturer_wording(self):
        self.assertEqual(
            professional_headline("Conquer Ford EcoBlue Pulley Repairs",self.product),
            self.product["title"][:48])
        self.assertEqual(
            professional_headline("Ford EcoBlue Crankshaft Pulley Removal",self.product),
            "Ford EcoBlue Crankshaft Pulley Removal")

    def _editing(self,updates=None,scene=None):
        edits={"headline":"Crankshaft Pulley Removal",
               "palette":0,"background":"context","price_position":"standard",
               "accent":"#FFBD32","background_colour":"#056DB9",
               "display_mode":"glow","price_style":"tag","headline_size":"large",
               "tone":"technical","product_scale":115,"product_x":-20,
               "product_y":10,"background_intensity":75,
               "shape_intensity":1,"show_subline":True,
               "subline":"Ford EcoBlue workshop application"}
        if updates:edits.update(updates)
        if scene:edits["scene_data"]="data:image/png;base64,"+base64.b64encode(scene).decode()
        return {"index":0,"concept":self.concept,"edits":edits}

    def test_new_editor_controls_are_valid_and_photo_is_source_owned(self):
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"render_ai_promo",wraps=render_promo) as renderer:
            response=studio.app.test_client().post("/api/ai/edit/9385",
                                                   json=self._editing())
        self.assertEqual(response.status_code,200,response.get_json())
        c=response.get_json()["concept"]
        self.assertEqual(c["editor"]["display_mode"],"glow")
        self.assertEqual(c["editor"]["price_style"],"tag")
        self.assertEqual(c["editor"]["product_x"],-20)
        self.assertEqual(c["editor"]["subline"] if "subline" in c["editor"] else c["subline"],"Ford EcoBlue workshop application")
        self.assertEqual(c["title"],self.product["title"])
        self.assertIs(renderer.call_args.args[1],self.photo)
        self.assertEqual(renderer.call_args.args[2]["price"],"£176.64 excluding VAT")

    def test_uploaded_workshop_image_is_background_only(self):
        scene=Image.new("RGB",(640,380),"#334D5A")
        d=ImageDraw.Draw(scene)
        d.rectangle((160,110,500,320),fill="#7292A3")
        out=io.BytesIO();scene.save(out,format="PNG")
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"render_ai_promo",wraps=render_promo) as renderer:
            response=studio.app.test_client().post(
                "/api/ai/edit/9385",json=self._editing(scene=out.getvalue()))
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(renderer.call_args.args[1],self.photo)
        self.assertEqual(renderer.call_args.kwargs["editor"]["_scene_bytes"],out.getvalue())
        self.assertNotIn("scene_data",response.get_json()["concept"]["editor"])
        self.assertNotIn("_scene_bytes",response.get_json()["concept"]["editor"])

    def test_official_application_photograph_is_used_only_for_context_campaign(self):
        source_photo=Image.new("RGB",(510,320),"#34566D")
        d=ImageDraw.Draw(source_photo)
        d.rectangle((50,45,420,280),fill="#627C89")
        buf=io.BytesIO();source_photo.save(buf,format="PNG")
        scene=buf.getvalue()
        licensed=b"licensed_context"
        product={**self.product,
            "application_photo_source":"https://www.lasertools.co.uk/items/9385_InSitu.jpg",
            "photo_source":"https://www.lasertools.co.uk/items/9385.jpg"}
        data=[{**self.concept,"id":i,"family":f} for i,f in enumerate(FAMILIES)]
        def choose(product,variation=0,official_photo=None,prefer_official=False,**kwargs):
            selected=official_photo if prefer_official else licensed
            return selected,{"category":"engine","source":"Official manufacturer application photo"
                        if prefer_official else "Pexels free commercial-use photo",
                             "page_url":"https://www.pexels.com/photo/8985517/",
                             "description":"Engine service","license_url":None}
        with patch.object(studio,"lookup",return_value=(product,self.photo)), \
             patch.dict(studio.APPLICATION_IMAGE_CACHE,{"9385":scene},clear=False), \
             patch.object(studio,"find_scene",side_effect=choose) as find, \
             patch.object(studio,"propose_ai_concepts",return_value=data), \
             patch.object(studio,"render_ai_promo",return_value=b"sample") as renderer:
            response=studio.app.test_client().post("/api/ai/concepts/9385",
                                                  json={"distributor_brand":"none"})
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(renderer.call_count,3)
        self.assertEqual(renderer.call_args_list[0].kwargs["editor"]["_scene_bytes"],licensed)
        self.assertEqual(renderer.call_args_list[1].kwargs["editor"]["_scene_bytes"],licensed)
        self.assertEqual(renderer.call_args_list[2].kwargs["editor"]["_scene_bytes"],scene)
        self.assertEqual(response.get_json()["concepts"][2]["scene"]["source"],
                         "Official manufacturer application photo")

    def test_unsafe_editor_options_rejected(self):
        for changes in [
            {"product_scale":500},{"product_x":200},{"shape_intensity":100},
            {"price_style":"fake_sale"},{"display_mode":"generated_tool"},
            {"background":"https://evil.example/asset.jpg"},
            {"headline_size":"gigantic"},{"scene_data":"data:image/png;base64,AAAA"},
            {"tone":"invent_fitment"},{"show_subline":"true"}]:
            with self.subTest(changes=changes), patch.object(
                studio,"lookup",return_value=(self.product,self.photo)):
                response=studio.app.test_client().post("/api/ai/edit/9385",
                                                      json=self._editing(changes))
            self.assertEqual(response.status_code,400,response.get_json())

    def test_headline_choices_route_uses_verified_product(self):
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"suggest_ai_headlines",
                          return_value=["Ford EcoBlue Pulley Puller",
                                        "Post-2023 Crankshaft Pulley Puller",
                                        "Ford 2.0 EcoBlue Service Puller"]) as gemini:
            response=studio.app.test_client().post("/api/ai/headlines/9385",
                                                   json={"index":0,"tone":"technical"})
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(len(response.get_json()["headlines"]),3)
        self.assertEqual(gemini.call_args.kwargs["tone"],"technical")

    def test_v3_controls_and_javascript_syntax(self):
        html=studio.V7_HOME_PAGE
        for identifier in ("aiEditDisplay","aiEditScale","aiEditX","aiEditY",
                           "aiEditPriceStyle","aiEditHeadlineSize","aiEditShowSubline",
                           "aiEditSceneFile","aiSceneRemove","aiSuggestHeadlines",
                           "aiHeadlineChoices","aiEditTone","aiEditIntensity",
                           "aiEditShapes"):
            self.assertIn('id="'+identifier+'"',html)
        if shutil.which("node"):
            source=re.search(r"<script>(.*?)</script>",html,re.S).group(1)
            result=subprocess.run(["node","--check"],input=source,text=True,
                                  capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
