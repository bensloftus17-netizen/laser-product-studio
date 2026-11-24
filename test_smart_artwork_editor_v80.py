"""V80 — professional one-poster editor and memory-safe, verified gallery picker.

All tests are offline. The design planner chooses enumerated layout treatments,
never generates fictional product images or specifications. Photo picker always
requires the source SHA and the campaign's bearer token.
"""
import hashlib
import io
import json
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

import app as studio
from campaign_design_v80 import creative_recipe,recovery_variants
from campaign_director import plan_campaign
from campaign_art_quality import choose_best
from disk_campaign_store import StoredCampaign
from poster_live_edit import edit_campaign_poster


def image(colour):
    im=Image.new("RGB",(510,390),colour)
    b=io.BytesIO()
    im.save(b,format="PNG")
    return b.getvalue()


def fixture():
    p0=image("#16416d")
    p1=image("#335a7d")
    photos=[p0,p1]
    choices=[
        {"index":i,"source_url":f"https://www.lasertools.co.uk/items/XLarge/9365_{i}.png",
         "sha256":hashlib.sha256(blob).hexdigest(),
         "type":"packshot" if i==0 else "alternate","label":"Official source"}
        for i,blob in enumerate(photos)]
    product={
        "part":"9365","title":"Stainless Steel Ratchet Set 4pc",
        "source":"https://www.toolconnection.co.uk/products/9365-stainless-steel-ratchet-set",
        "features":["Set of four ratchets","Includes storage case"],
        "specs":{},"photo_gallery":[{"sha256":x["sha256"],
                                     "source_url":x["source_url"],
                                     "type":x["type"]} for x in choices],
    }
    concepts=[{
        "headline":"Stainless Steel Ratchet Set 4pc",
        "selling_point":"Set of four ratchets",
        "visual_plan":{"price_style":"panel",
                       "art_direction":{"price_style":"panel","headline_size":"normal"}},
        "family":"retail", "variant":0,"features":[]
    } for _ in range(3)]
    roles=("poster_technical","poster_price","poster_smart")
    manifest={
        "part":"9365","title":product["title"],
        "promo_template":"ai_original",
        "angles":[{"headline":product["title"],"selling_point":"Set of four ratchets",
                   "layout_variant":0,"name":r} for r in roles],
        "poster_photo_choices":choices,
        "artwork_photo_sources":{
            r:{k:choices[0][k] for k in ("source_url","sha256","type")}
            for r in roles},
        "artwork_quality":{r:{"variation":0,"passed":True} for r in roles},
    }
    from campaign_hub import FOLDERS
    zipped=io.BytesIO()
    with ZipFile(zipped,"w") as archive:
        for path in FOLDERS.values():
            archive.writestr(path,image("#0f4169"))
        archive.writestr("Campaign_Manifest.json",json.dumps(manifest))
        archive.writestr("05_Product_Info/Campaign_Summary.pdf",b"%PDF-1.4\n")
    ctx={
        "product":product,"genuine_photo":p0,"gallery_photos":photos,
        "role_photos":{r:p0 for r in roles},
        "concepts":concepts,"distributor":None,"scenes":[None,None,None],
    }
    return {"manifest":manifest,"images":{r:image("#0f4169") for r in roles},
            "editor_context":ctx,"archive":zipped.getvalue()},photos


class V80ProductStudioTests(unittest.TestCase):
    def test_reference_editor_draws_the_verified_edited_headline(self):
        import poster_quality
        for asset_id in ("poster_technical","poster_price"):
            with self.subTest(asset_id=asset_id):
                bundle,_=fixture()
                bundle["manifest"]["promo_template"]="workshop_showcase"
                def render_and_inspect(render,role,photo,**kwargs):
                    # Keep the actual artwork renderer and capture its drawn copy.
                    with patch("reference_poster_templates.record_text",wraps=poster_quality.record_text) as recorded:
                        png,_=render(0)
                    headlines=[call.args[0] for call in recorded.call_args_list
                               if len(call.args)>4 and call.args[4]=="headline"]
                    self.assertIn("RATCHET SET 4PC",headlines)
                    return png,{"variation":0,"passed":True}
                with patch("poster_live_edit.choose_best",side_effect=render_and_inspect), \
                     patch("campaign_hub._summary_pdf",return_value=b"%PDF-1.4"):
                    response=edit_campaign_poster(bundle,asset_id,{
                        "headline":"Ratchet Set 4pc","feature_index":-1,"layout_variant":0})
                self.assertEqual(response["revision"],1)

    def test_full_kit_fits_even_when_layout_crosses_artboard_edge(self):
        from PIL import ImageDraw
        from campaign_role_posters import product_photo
        src=Image.new("RGBA",(180,80),(0,0,0,0))
        draw=ImageDraw.Draw(src)
        draw.rectangle((0,10,26,69),fill="#ff0000")
        draw.rectangle((153,10,179,69),fill="#00ff00")
        canvas=Image.new("RGBA",(100,80),"black")
        with patch("campaign_role_posters.inspected_product",return_value={
                "rgba":src,"isolated":True,"needs_manual_cutout":False}):
            placed=product_photo(canvas,b"official kit",(-55,1,90,79),scale=1.4)
        x0,y0,x1,y1=placed["position"]
        self.assertGreaterEqual(x0,0)
        self.assertLessEqual(x1,canvas.width)
        self.assertEqual(canvas.getpixel((x0+4,(y0+y1)//2))[:3],(255,0,0))
        self.assertEqual(canvas.getpixel((x1-5,(y0+y1)//2))[:3],(0,255,0))


    def test_design_director_is_product_and_role_specific_without_extra_ai(self):
        technical=creative_recipe("socket_ratchet","technical_application","9365")
        price=creative_recipe("socket_ratchet","price_promo","9365")
        smart=creative_recipe("socket_ratchet","product_selected","9365")
        self.assertEqual(len({x["photo_focus"] for x in
                             (technical,price,smart)}),3)
        self.assertEqual(len({x["headline_size"] for x in
                             (technical,price,smart)}),3)
        self.assertEqual(creative_recipe("socket_ratchet",
                         "price_promo","9365"),price)
        press=creative_recipe("workshop_press","price_promo","9365")
        self.assertNotEqual(price["graphic_motif"],press["graphic_motif"])
        product,_=fixture()
        concepts,plan=plan_campaign(product["editor_context"]["product"])
        for i,c in enumerate(concepts):
            self.assertEqual(c["visual_plan"]["category_design_recipe"]["photo_focus"],
                             ("right","left","centre")[i])
        self.assertEqual(len(concepts),3)
        self.assertIn("creative_decisions",plan)

    def test_existing_three_QA_checked_layouts_repair_failed_text_without_batch(self):
        attempted=[]
        good=b"png-layout-1"
        def render(variant):
            attempted.append(variant)
            return (b"png-layout-"+str(variant).encode(),
                    {"truncated":variant==0})
        def audit(image,role,source_info=None,text_status=None):
            passed=not text_status["truncated"]
            return {"passed":passed,"score":90 if passed else 0,
                    "issues":[] if passed else ["Text does not fit its design area"],
                    "warnings":[]}
        with patch("campaign_art_quality.inspected_product",return_value={}),\
             patch("campaign_art_quality.visual_review",side_effect=audit):
            out,report=choose_best(render,"price_promo",b"actual-source",
                          variants=recovery_variants(0),early_exit=True)
        self.assertEqual(attempted,[0,1])
        self.assertEqual(out,good)
        self.assertEqual(report["candidates_checked"],2)
        self.assertEqual(report["rejected_candidates"],1)

    def test_poster_photo_picker_accepts_only_exact_verified_campaign_photo(self):
        bundle,photos=fixture()
        from campaign_hub import FOLDERS
        def return_poster(render,role,photo,**kwargs):
            self.assertEqual(photo,photos[1])
            self.assertEqual(kwargs["variants"],(0,1,2))
            self.assertTrue(kwargs["early_exit"])
            return image("#183d6d"),{"variation":1,"passed":True,"score":98}
        with patch("poster_live_edit.require_good_asset",
                   return_value={"passed":True}) as verified,\
             patch("poster_live_edit.choose_best",
                   side_effect=return_poster) as generator,\
             patch("campaign_hub._summary_pdf",return_value=b"%PDF-1.4\n"):
            result=edit_campaign_poster(bundle,"poster_price",{
                "headline":"Ratchet Set 4pc","feature_index":-1,"layout_variant":0,
                "photo_index":1,"price_style":"plaque","headline_size":"large"})
        self.assertEqual(generator.call_count,1)
        verified.assert_called_once_with(photos[1])
        self.assertTrue(result["quality"]["auto_repaired"])
        self.assertEqual(bundle["editor_context"]["role_photos"]["poster_price"],photos[1])
        self.assertEqual(bundle["manifest"]["angles"][1]["layout_variant"],1)
        self.assertEqual(bundle["manifest"]["artwork_photo_sources"]
                         ["poster_price"]["sha256"],hashlib.sha256(photos[1]).hexdigest())
        with ZipFile(io.BytesIO(bundle["archive"])) as archive:
            self.assertEqual(archive.read(FOLDERS["poster_price"]),bundle["images"]["poster_price"])

    def test_disk_stored_poster_edit_streams_zip_and_preserves_other_assets(self):
        bundle,photos=fixture()
        from disk_campaign_store import _atomic_file
        from campaign_hub import FOLDERS
        with tempfile.TemporaryDirectory(prefix="v80-zip-") as folder:
            stored=StoredCampaign(Path(folder),bundle["manifest"],[])
            (Path(folder)/"images").mkdir()
            for role,payload in bundle["images"].items():
                stored["images"][role]=payload
            _atomic_file(stored.archive_path,bundle["archive"])
            stored.save_editor(bundle["editor_context"])
            unchanged=stored["images"]["poster_smart"]
            def validated(render,role,photo,**kwargs):
                self.assertEqual(photo,photos[1])
                return image("#1b85b1"),{"passed":True,"variation":0,"score":94}
            # Streamed edit must NEVER call the in-memory campaign archive
            # getter. Temporarily reject that access and exercise a real ZIP.
            original_get=StoredCampaign.__getitem__
            def guard(instance,key):
                if key=="archive":
                    raise AssertionError("Edited a disk-backed campaign by materialising full ZIP in RAM")
                return original_get(instance,key)
            with patch.object(StoredCampaign,"__getitem__",guard),\
                 patch("poster_live_edit.choose_best",side_effect=validated),\
                 patch("poster_live_edit.require_good_asset",
                       return_value={"passed":True}),\
                 patch("campaign_hub._summary_pdf",
                       return_value=b"%PDF-1.4\n"):
                result=edit_campaign_poster(stored,"poster_technical",{
                    "headline":"Ratchet Set 4pc","feature_index":-1,
                    "layout_variant":0,"photo_index":1})
            self.assertEqual(result["revision"],1)
            self.assertEqual(stored["images"]["poster_smart"],unchanged)
            self.assertEqual(stored.gallery_photo(1),photos[1])
            self.assertEqual(stored["editor_context"]["role_photos"]["poster_technical"],photos[1])
            with ZipFile(stored.archive_path) as zipped:
                self.assertEqual(zipped.read(FOLDERS["poster_technical"]),
                                 stored["images"]["poster_technical"])
                self.assertEqual(zipped.read(FOLDERS["poster_smart"]),unchanged)
                self.assertEqual(
                    json.loads(zipped.read("Campaign_Manifest.json"))["poster_revision"],1)

    def test_invalid_or_forged_photo_selection_never_changes_bundle(self):
        for bad in (True,-1,4,88,"1"):
            bundle,_=fixture()
            before=bundle["archive"]
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                edit_campaign_poster(bundle,"poster_price",{
                    "headline":"Ratchet Set 4pc","feature_index":-1,
                    "layout_variant":0,"photo_index":bad})
            self.assertEqual(bundle["archive"],before)
        bundle,photos=fixture()
        bundle["editor_context"]["gallery_photos"][1]=image("#E1DCDC")
        with self.assertRaisesRegex(ValueError,"no longer matches"):
            edit_campaign_poster(bundle,"poster_price",{
                "headline":"Ratchet Set 4pc","feature_index":-1,
                "layout_variant":0,"photo_index":1})

    def test_private_disk_gallery_serves_verified_photo_without_decoding(self):
        bundle,photos=fixture()
        token=secrets.token_urlsafe(24)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            stored=StoredCampaign(folder,bundle["manifest"],[])
            stored.save_editor(bundle["editor_context"])
            self.assertEqual(stored.gallery_photo(1),photos[1])
            self.assertEqual(stored.gallery_path(1).read_bytes(),photos[1])
            with self.assertRaises(ValueError):
                stored.gallery_path(10)
            studio.CAMPAIGN_PACKS[token]={
                "bundle":stored,"expires":time.time()+300}
            try:
                client=studio.app.test_client()
                good=client.get("/api/campaign/photos/"+token+"/1")
                self.assertEqual(good.status_code,200)
                self.assertEqual(good.data,photos[1])
                self.assertEqual(good.mimetype,"image/png")
                self.assertEqual(good.headers["X-Content-Type-Options"],"nosniff")
                self.assertEqual(client.get(
                    "/api/campaign/photos/invalid/1").status_code,404)
                self.assertEqual(client.get(
                    "/api/campaign/photos/"+token+"/9").status_code,404)
            finally:
                studio.CAMPAIGN_PACKS.pop(token,None)

    def test_editor_frontend_shows_actual_photo_choices_preview_and_controls(self):
        page=studio.V7_HOME_PAGE
        for control in ("posterEditPreview","posterEditPhotoPicker",
                        "posterEditPriceStyle","posterEditHeadlineSize",
                        "posterEditSave","posterEditFeature","posterEditVariant"):
            self.assertIn('id="'+control+'"',page)
        self.assertIn("campaign_poster_edit.js?v=89",page)
        self.assertIn("v80-visual-editor",page.lower())


    def test_v81_campaign_survives_worker_index_loss_and_fifth_campaign(self):
        from campaign_hub import FOLDERS
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(studio,"CAMPAIGN_PACK_ROOT",Path(temp)), \
             patch.object(studio,"CAMPAIGN_PACKS",{}):
            tokens=[]
            for _ in range(5):
                bundle,photos=fixture()
                tokens.append(studio._save_campaign_bundle(bundle))
            token=tokens[0]
            self.assertIsNotNone(studio._get_campaign_pack(token))
            studio.CAMPAIGN_PACKS.clear()
            client=studio.app.test_client()
            self.assertEqual(client.get("/api/campaign/manifest/"+token).status_code,200)
            self.assertEqual(client.get("/api/campaign/photos/"+token+"/1").data,photos[1])
            updated=image("#2982ad")
            def validated(render,role,photo,**kwargs):
                self.assertEqual(photo,photos[1])
                return updated,{"passed":True,"variation":0,"score":94}
            with patch.object(studio,"can_start_heavy",return_value=True), \
                 patch("poster_live_edit.choose_best",side_effect=validated), \
                 patch("poster_live_edit.require_good_asset",return_value={"passed":True}), \
                 patch("campaign_hub._summary_pdf",return_value=b"%PDF-1.4\\n"):
                response=client.post("/api/campaign/edit/"+token+"/poster_technical",json={
                    "headline":"Ratchet Set 4pc","feature_index":-1,
                    "layout_variant":0,"photo_index":1})
                self.assertEqual(response.status_code,200,response.get_data(as_text=True))
                studio.CAMPAIGN_PACKS.clear()
                second=client.post("/api/campaign/edit/"+token+"/poster_technical",json={
                    "headline":"Ratchet Set 4pc","feature_index":-1,"layout_variant":0})
                self.assertEqual(second.status_code,200,second.get_data(as_text=True))
                self.assertEqual(second.get_json()["revision"],2)
            studio.CAMPAIGN_PACKS.clear()
            self.assertEqual(client.get("/api/campaign/assets/"+token+"/poster_technical").data,updated)
            with ZipFile(io.BytesIO(client.get("/api/campaign/download/"+token).data)) as archive:
                self.assertEqual(archive.read(FOLDERS["poster_technical"]),updated)
                self.assertEqual(json.loads(archive.read("Campaign_Manifest.json"))["poster_revision"],2)

    def test_v81_active_campaign_refreshes_expiry_without_loading_zip(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(studio,"CAMPAIGN_PACK_ROOT",Path(temp)), \
             patch.object(studio,"CAMPAIGN_PACKS",{}):
            bundle,_=fixture()
            token=studio._save_campaign_bundle(bundle)
            studio.CAMPAIGN_PACKS[token]["expires"]=time.time()+60
            self.assertIsNotNone(studio._get_campaign_pack(token))
            self.assertGreater(studio.CAMPAIGN_PACKS[token]["expires"],time.time()+3600)
            self.assertIsNone(studio._get_campaign_pack("x"*32))



    def test_v82_generated_feature_headline_does_not_block_photo_only_edit(self):
        bundle,photos=fixture()
        generated="Set of four ratchets"
        bundle["editor_context"]["concepts"][2]["headline"]=generated
        bundle["manifest"]["angles"][2]["headline"]=generated
        token=secrets.token_urlsafe(24)
        with tempfile.TemporaryDirectory() as temp, patch.object(studio,"CAMPAIGN_PACK_ROOT",Path(temp)), patch.object(studio,"CAMPAIGN_PACKS",{}):
            token=studio._save_campaign_bundle(bundle)
            client=studio.app.test_client()
            def validate(render,role,photo,**kwargs):
                self.assertEqual(photo,photos[1])
                return image("#2982ad"),{"passed":True,"variation":1,"score":94}
            with patch.object(studio,"can_start_heavy",return_value=True), patch("poster_live_edit.choose_best",side_effect=validate), patch("poster_live_edit.require_good_asset",return_value={"passed":True}), patch("campaign_hub._summary_pdf",return_value=b"%PDF-1.4"):
                edits={"headline":generated,"feature_index":0,"layout_variant":1,"photo_index":1}
                response=client.post("/api/campaign/edit/"+token+"/poster_smart",json=edits)
                self.assertEqual(response.status_code,200,response.get_data(as_text=True))
                self.assertEqual(response.get_json()["manifest"]["angles"][2]["headline"],generated)
                edits["headline"]="Guaranteed 500 percent better"
                rejected=client.post("/api/campaign/edit/"+token+"/poster_smart",json=edits)
                self.assertEqual(rejected.status_code,400)

if __name__=="__main__":
    unittest.main()
