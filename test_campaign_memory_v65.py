"""V65: do not crash the 512 MiB Render worker building nine original assets.

Proves approved PNG/ZIP bytes are disk-backed instead of cached in Python,
downloads/editor/resume still work, expensive renders cannot overlap, and
Pillow overlays/photo preflight retain source pixels and image dimensions.
"""
from __future__ import annotations

import io
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image,ImageDraw

import app as studio
import asset_quality
from ai_photo_effects import _cutout_png
from campaign_art_quality import inspected_product
from creative_expression import express_background
from disk_campaign_store import StoredCampaign,store_campaign
from test_mobile_campaign_v47 import _bundle, _png


def real_archive(bundle):
    stream=io.BytesIO()
    with ZipFile(stream,"w") as z:
        for k,v in bundle["images"].items():
            z.writestr(k+".png",v)
        z.writestr("Campaign_Manifest.json","{}")
    bundle["archive"]=stream.getvalue()
    return bundle


class CampaignMemoryV65Tests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        self.old_slot=studio.CAMPAIGN_RENDER_SLOT
        studio.CAMPAIGN_RENDER_SLOT=threading.BoundedSemaphore(1)
        self.stored=[]
        self.saved_packs=studio.CAMPAIGN_PACKS
        studio.CAMPAIGN_PACKS={}

    def tearDown(self):
        for entry in studio.CAMPAIGN_PACKS.values():
            bundle=entry.get("bundle")
            if isinstance(bundle,StoredCampaign):
                bundle.delete()
        studio.CAMPAIGN_PACKS=self.saved_packs
        studio.CAMPAIGN_RENDER_SLOT=self.old_slot
        for pack in self.stored:
            pack.delete()

    def test_saved_pack_keeps_full_resolution_png_and_zip_off_heap(self):
        original=real_archive(_bundle("6330"))
        original["editor_context"]={
            "product":{"part":"6330","title":"Verified socket product"},
            "genuine_photo":_png(),
            "scenes":[None,_png(),None],
            "concepts":[{"headline":"Factory wording"}]*3,
            "distributor":None}
        pack=store_campaign(original)
        self.stored.append(pack)
        self.assertEqual(pack["manifest"],original["manifest"])
        self.assertEqual(pack["images"]["poster_price"],_png())
        self.assertEqual(pack["archive"],original["archive"])
        self.assertTrue(pack.archive_path.is_file())
        self.assertTrue(pack["images"].path_for("poster_price").is_file())
        self.assertTrue(pack["images"].path_for("poster_price").parent.is_dir())
        self.assertEqual(pack["editor_context"]["genuine_photo"],_png())
        self.assertEqual(pack["editor_context"]["scenes"][1],_png())
        self.assertEqual(pack["editor_context"]["scenes"][0],None)
        self.assertFalse(
            any(isinstance(value,bytes) for value in vars(pack).values()))
        with ZipFile(pack.archive_path) as z:
            self.assertEqual(z.read("poster_technical.png"),_png())

    def test_resume_downloads_and_private_image_links_after_persisting(self):
        bundle=real_archive(_bundle("6330"))
        token=studio._save_campaign_bundle(bundle)
        disk=studio._get_campaign_pack(token)
        self.assertIsInstance(disk,StoredCampaign)
        self.assertTrue(disk.archive_path.exists())
        self.assertEqual(self.client.get(
            "/api/campaign/manifest/"+token).get_json()["manifest"]["part"],"6330")
        self.assertEqual(self.client.get(
            "/api/campaign/download/"+token).data,bundle["archive"])
        self.assertEqual(self.client.get(
            "/api/campaign/assets/"+token+"/poster_price").data,_png())
        self.assertEqual(self.client.get(
            "/api/campaign/assets/"+token+"/poster_price?download=1").status_code,200)
        self.assertEqual(self.client.get(
            "/api/campaign/assets/"+token+"/bad-key").status_code,404)

    def test_stale_pack_eviction_clears_private_files_and_does_not_keep_png_in_ram(self):
        original=real_archive(_bundle())
        token=studio._save_campaign_bundle(original)
        disk=studio._get_campaign_pack(token)
        folder=disk.folder
        studio.CAMPAIGN_PACKS[token]["expires"]=time.time()-1
        self.assertIsNone(studio._get_campaign_pack(token))
        self.assertFalse(folder.exists())
        self.assertNotIn(token,studio.CAMPAIGN_PACKS)

    def test_completed_editor_context_is_reloaded_and_persists_later_revisions(self):
        original=real_archive(_bundle())
        original["editor_context"]={
            "product":{"part":"6330"},
            "genuine_photo":_png(),
            "scenes":[None,None,None],
            "concepts":[{"headline":"Original"} for _ in range(3)],
            "distributor":None}
        pack=store_campaign(original)
        self.stored.append(pack)
        first=pack["editor_context"]
        first["concepts"][0]["headline"]="Verified revised headline"
        pack.save_editor(first)
        self.assertEqual(pack["editor_context"]["concepts"][0]["headline"],
                         "Verified revised headline")
        pack["images"]["poster_price"]=_png()
        pack["manifest"]={"part":"6330","poster_revision":2}
        self.assertEqual(pack["manifest"]["poster_revision"],2)

    def test_no_simultaneous_sync_and_async_campaign_rendering(self):
        with studio.CAMPAIGN_RENDER_SLOT:
            # The semaphore is already held by another expensive operation.
            with patch.object(studio,"_assemble_campaign_bundle") as build:
                result=self.client.post("/api/campaign/6330",json={})
                self.assertEqual(result.status_code,429)
                self.assertEqual(result.headers["Retry-After"],"30")
                async_result=self.client.post("/api/campaign/start/6330",json={})
                self.assertEqual(async_result.status_code,429)
                build.assert_not_called()

    def test_synchronous_exception_releases_render_lock(self):
        with patch.object(studio,"_assemble_campaign_bundle",
                          side_effect=ValueError("official source unavailable")):
            result=self.client.post("/api/campaign/6330",json={})
        self.assertEqual(result.status_code,400)
        self.assertTrue(studio.CAMPAIGN_RENDER_SLOT.acquire(blocking=False))
        studio.CAMPAIGN_RENDER_SLOT.release()

    def test_quality_caches_are_small_and_clearable(self):
        self.assertLessEqual(inspected_product.cache_info().maxsize,2)
        self.assertLessEqual(_cutout_png.cache_info().maxsize,2)
        studio._release_campaign_image_caches()
        self.assertEqual(inspected_product.cache_info().currsize,0)
        self.assertEqual(_cutout_png.cache_info().currsize,0)

    def test_inplace_rgba_overlay_matches_exact_original_pixels(self):
        for name in ("laser_blue","signal_yellow","studio_silver"):
            original=Image.new("RGBA",(360,450),"#0F3A5C")
            copy=original.copy()
            existing=express_background(
                original,name,"split_canvas",
                zones={"headline":(20,70,150,170)},variant=1)
            self.assertEqual(original.getpixel((0,100)),(15,58,92,255))
            inplace=express_background(
                copy,name,"split_canvas",
                zones={"headline":(20,70,150,170)},
                variant=1,inplace=True)
            self.assertIs(inplace,copy)
            self.assertEqual(existing.tobytes(),inplace.tobytes())

    def test_photo_qa_no_longer_resizes_shared_cached_manufacturer_cutout(self):
        image=Image.new("RGBA",(900,1000),(22,63,110,255))
        d=ImageDraw.Draw(image)
        d.rectangle((100,120,800,880),fill=(5,125,195,210))
        source={
            "rgba":image,
            "isolated":True,
            "needs_manual_cutout":False,
            "source_warning":None,
        }
        raw=io.BytesIO()
        image.convert("RGB").save(raw,"PNG")
        with patch("asset_quality.inspected_product",return_value=source):
            asset_quality.inspect_asset(raw.getvalue())
        self.assertEqual(source["rgba"].size,(900,1000))
        self.assertEqual(source["rgba"].getpixel((100,120)),(5,125,195,210))

if __name__=="__main__":
    unittest.main()
