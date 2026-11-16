"""AI promotional poster editor regression and tamper-safety tests."""
import io
import json
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw

import app as studio
from ai_promo_renderer import render_promo, FAMILIES

class AiPosterEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        photo=Image.new("RGB",(440,280),"white")
        d=ImageDraw.Draw(photo)
        d.rounded_rectangle((90,70,370,225),fill="#0D4485",radius=24)
        d.ellipse((230,110,320,195),fill="#E42C30")
        blob=io.BytesIO();photo.save(blob,format="PNG")
        cls.photo=blob.getvalue()
        cls.product={"part":"9364","title":"Laser Tools Ratchet Set 3pc",
                     "price":"£101.48 excluding VAT","price_source":"Official manufacturer",
                     "description":"Three piece ratchet set","features":[
                         "Chrome vanadium ratchets","1/4 inch ratchet mechanism",
                         "Three drive sizes"],"specs":{}}
        cls.concept={"part":"9364","title":"Laser Tools Ratchet Set 3pc",
                     "family":"retail","id":0,"variant":0,
                     "headline":"Three ratchets, one kit","subline":"Ratchet set",
                     "name":"Retail Promo","angle":"Trade promotion",
                     "features":["Chrome vanadium ratchets","Three drive sizes"]}

    def call_editor(self,payload):
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)):
            return studio.app.test_client().post("/api/ai/edit/9364",json=payload)

    def payload(self,**edits):
        defaults={"headline":"ONE KIT. THREE RATCHETS.","palette":1,
                  "background":"rings","price_position":"opposite",
                  "accent":"#FF9D3D","background_colour":"#125EB0"}
        defaults.update(edits)
        return {"index":0,"concept":self.concept,"edits":defaults,
                "distributor_brand":"none"}

    def test_apply_changes_keeps_real_photo_price_and_source_facts(self):
        payload=self.payload()
        payload["concept"]={**self.concept,"features":[
            "Invented 9000Nm torque","Chrome vanadium ratchets"]}
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"render_ai_promo",wraps=render_promo) as render:
            response=studio.app.test_client().post("/api/ai/edit/9364",json=payload)
            self.assertEqual(response.status_code,200,response.get_json())
            new=response.get_json()["concept"]
            self.assertEqual(new["headline"],"ONE KIT. THREE RATCHETS.")
            self.assertEqual(new["variant"],1)
            self.assertEqual(new["family"],"retail")
            self.assertEqual(new["editor"]["background"],"rings")
            self.assertEqual(new["editor"]["price_position"],"opposite")
            self.assertEqual(new["features"],["Chrome vanadium ratchets"])
            self.assertEqual(new["part"],self.product["part"])
            self.assertEqual(new["title"],self.product["title"])
            self.assertTrue(new["preview"].startswith("data:image/png;base64,"))
            self.assertIs(render.call_args.args[1],self.photo)
            self.assertEqual(render.call_args.args[2]["price"],"£101.48 excluding VAT")
            self.assertEqual(render.call_args.kwargs["editor"]["accent"],"#FF9D3D")

    def test_custom_colours_price_placement_and_backgrounds_change_artwork(self):
        source=self.concept
        baseline=render_promo(source,self.photo,self.product)
        for family in FAMILIES:
            concept={**source,"family":family}
            a=render_promo(concept,self.photo,self.product)
            b=render_promo(concept,self.photo,self.product,editor={
                "price_position":"opposite","background":"grid",
                "accent":"#E6E452","background_colour":"#9344B8"})
            self.assertNotEqual(a,b)
            with Image.open(io.BytesIO(b)) as img:
                self.assertEqual(img.size,(1200,1500))
                self.assertEqual(img.mode,"RGB")
        self.assertTrue(baseline.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_forbid_forged_sku_design_unsafe_colors_and_empty_headline(self):
        bad_cases=[
            {"index":9},
            {"concept":{**self.concept,"part":"9395"}},
            {"concept":{**self.concept,"family":"trade"}},
            {"edits":{**self.payload()["edits"],"accent":"red"}},
            {"edits":{**self.payload()["edits"],"palette":200}},
            {"edits":{**self.payload()["edits"],"background":"url()"}},
            {"edits":{**self.payload()["edits"],"headline":"  "}},
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad):
                response=self.call_editor({**self.payload(),**bad})
                self.assertEqual(response.status_code,400,response.get_json())

    def test_price_cannot_be_changed_using_editor_data(self):
        payload=self.payload()
        payload["edits"]["price"]="£0.01 excluding VAT"
        payload["concept"]["price"]="£0.01 excluding VAT"
        response=self.call_editor(payload)
        self.assertEqual(response.status_code,200)
        # Staff-entered price is accepted ONLY after review, never from concept.
        without_review=self.payload()
        without_review["staff_rrp_ex"]="5.25"
        response=self.call_editor(without_review)
        self.assertNotEqual(response.status_code,200)
        reviewed=self.payload()
        reviewed.update({"staff_rrp_ex":"59.99","staff_rrp_reviewed":True,
                         "staff_rrp_basis":"inc"})
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"render_ai_promo",return_value=b"png") as render:
            response=studio.app.test_client().post("/api/ai/edit/9364",json=reviewed)
            self.assertEqual(response.status_code,200)
            self.assertEqual(render.call_args.args[2]["price"],"£59.99 including VAT")

    def test_regenerate_updates_single_family_only(self):
        next_concept={"headline":"Fresh campaign","subline":"New marketing",
                      "name":"Only retail","angle":"Different marketing",
                      "features":["Three drive sizes"]}
        payload={**self.payload(),"regenerate":True}
        with patch.object(studio,"lookup",return_value=(self.product,self.photo)), \
             patch.object(studio,"propose_ai_concepts",return_value=[next_concept]) as gemini:
            response=studio.app.test_client().post("/api/ai/edit/9364",json=payload)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(response.get_json()["concept"]["headline"],"Fresh campaign")
        self.assertEqual(response.get_json()["concept"]["family"],"retail")
        gemini.assert_called_once()
        self.assertEqual(gemini.call_args.kwargs["only_family"],"retail")

    def test_editor_front_end_controls_and_valid_javascript(self):
        html=studio.V7_HOME_PAGE
        for element in ("aiEditor","aiEditHeadline","aiEditPalette","aiEditAccent",
                        "aiEditBgColour","aiEditBackground","aiEditPricePosition",
                        "aiEditRegenerate","aiEditApply","aiEditorDownload"):
            self.assertIn('id="'+element+'"',html)
        self.assertIn("renderAiGallery()",html)
        self.assertIn("data-ai-edit",html)
        self.assertIn("/api/ai/edit/",html)
        # Node is available on GitHub Actions runners. Syntax check prevents
        # one malformed string from breaking the entire poster website.
        if shutil.which("node"):
            script=re.search(r"<script>(.*?)</script>",html,re.S).group(1)
            checked=subprocess.run(["node","--check"],input=script,text=True,
                                   capture_output=True,timeout=10)
            self.assertEqual(checked.returncode,0,checked.stderr)

if __name__=="__main__":
    unittest.main()
