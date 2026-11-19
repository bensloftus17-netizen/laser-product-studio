"""V48: quality-gated progressive previews before the full nine-format ZIP."""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import time
import unittest
from unittest.mock import patch

from PIL import Image

import app as studio
from campaign_hub import build_campaign, FOLDERS
from test_campaign_hub import CampaignHubTests
from test_mobile_campaign_v47 import _bundle, _png


class ProgressiveCampaignTests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        with studio.CAMPAIGN_JOBS_LOCK:
            studio.CAMPAIGN_JOBS.clear()
        with studio.CAMPAIGN_PACK_LOCK:
            studio.CAMPAIGN_PACKS.clear()

    def tearDown(self):
        with studio.CAMPAIGN_JOBS_LOCK:
            studio.CAMPAIGN_JOBS.clear()
        with studio.CAMPAIGN_PACK_LOCK:
            studio.CAMPAIGN_PACKS.clear()

    def start_job(self):
        with patch("app.threading.Thread"):
            result=self.client.post("/api/campaign/start/6330",
                                    json={"distributor_brand":"none"})
        self.assertEqual(result.status_code,202,result.get_json())
        return result.get_json()["job_id"]

    def test_server_publishes_png_only_after_ready_event_not_render_or_critic(self):
        job=self.start_job()
        source=_png()
        studio._campaign_progress_update(job,"verifying_product")
        studio._campaign_progress_update(job,"rendering","poster_technical")
        studio._campaign_progress_update(job,"quality_checking","poster_technical")
        pending=self.client.get("/api/campaign/job-assets/"+job+"/poster_technical")
        self.assertEqual(pending.status_code,409)
        progress=self.client.get("/api/campaign/jobs/"+job).get_json()
        self.assertEqual(progress["ready_count"],0)
        self.assertEqual(progress["assets"]["poster_technical"]["status"],"quality_checking")
        self.assertNotIn("token",progress)
        studio._campaign_progress_update(job,"ready","poster_technical",source,
                                          {"passed":True,"score":94})
        current=self.client.get("/api/campaign/jobs/"+job).get_json()
        self.assertEqual(current["ready_count"],1)
        self.assertEqual(current["total_assets"],9)
        self.assertEqual(current["assets"]["poster_technical"]["status"],"ready")
        self.assertNotIn("token",current)
        self.assertNotIn("manifest",current)
        inline=self.client.get("/api/campaign/job-assets/"+job+"/poster_technical")
        self.assertEqual(inline.status_code,200)
        self.assertEqual(inline.mimetype,"image/png")
        self.assertEqual(inline.data,source)
        self.assertIn("inline",inline.headers["Content-Disposition"])
        attachment=self.client.get(
            "/api/campaign/job-assets/"+job+"/poster_technical?download=1")
        self.assertEqual(attachment.status_code,200)
        self.assertIn("attachment",attachment.headers["Content-Disposition"])
        self.assertIn("no-store",attachment.headers["Cache-Control"])
        self.assertEqual(attachment.data,source)
        self.assertNotIn("archive",current)

    def test_invalid_previews_and_unapproved_assets_never_leak(self):
        job=self.start_job()
        with self.assertRaises(ValueError):
            studio._campaign_progress_update(job,"ready","poster_price",
                                              b"bad-not-a-png",{"passed":True})
        self.assertEqual(
            self.client.get("/api/campaign/job-assets/"+job+"/poster_price").status_code,409)
        with self.assertRaises(ValueError):
            studio._campaign_progress_update(job,"ready","source_qr",_png())
        with self.assertRaises(ValueError):
            studio._campaign_progress_update(job,"whatever","poster_smart")
        self.assertEqual(
            self.client.get("/api/campaign/job-assets/"+job+"/source_qr").status_code,404)
        self.assertEqual(
            self.client.get("/api/campaign/job-assets/not-a-token/poster_price").status_code,404)
        self.assertEqual(
            self.client.get("/api/campaign/job-assets/"+("x"*32)+"/poster_price").status_code,404)

    def test_partial_approved_images_remain_available_when_other_format_fails(self):
        job=self.start_job()
        source=_png()
        def failed_generation(part,body,progress=None):
            progress("planning")
            progress("ready","poster_technical",source,{"passed":True})
            progress("rendering","social_story")
            progress("failed","social_story",None,{"issues":["Text clipped"]})
            raise ValueError("Incomplete campaign: social_story quality check failed")
        with patch("app._assemble_campaign_bundle",side_effect=failed_generation):
            studio._run_campaign_job(job,"6330",{})
        status=self.client.get("/api/campaign/jobs/"+job).get_json()
        self.assertEqual(status["status"],"failed")
        self.assertEqual(status["ready_count"],1)
        self.assertEqual(status["assets"]["social_story"]["status"],"failed")
        self.assertEqual(status["assets"]["social_story"]["error"],"Text clipped")
        self.assertEqual(self.client.get(
            "/api/campaign/job-assets/"+job+"/poster_technical").data,source)
        self.assertEqual(self.client.get(
            "/api/campaign/job-assets/"+job+"/social_story").status_code,409)
        self.assertNotIn("token",status)
        self.assertFalse(studio.CAMPAIGN_PACKS)

    def test_final_job_has_all_nine_assets_and_downloadable_zip(self):
        job=self.start_job()
        def successful(part,body,progress=None):
            progress("planning")
            for ident in FOLDERS:
                progress("rendering",ident)
                progress("quality_checking",ident)
                progress("ready",ident,_png(),{"passed":True})
            progress("finalising_pack")
            return _bundle(part)
        with patch("app._assemble_campaign_bundle",side_effect=successful):
            studio._run_campaign_job(job,"6330",{})
        result=self.client.get("/api/campaign/jobs/"+job).get_json()
        self.assertEqual(result["status"],"ready")
        self.assertEqual(result["stage"],"complete")
        self.assertEqual(result["ready_count"],9)
        self.assertEqual(result["total_assets"],9)
        self.assertIn("token",result)
        self.assertIn("manifest",result)
        self.assertEqual(studio.CAMPAIGN_JOBS[job]["preview_images"],{})
        self.assertEqual(self.client.get(
            "/api/campaign/job-assets/"+job+"/social_story").status_code,200)
        self.assertEqual(self.client.get(
            "/api/campaign/download/"+result["token"]).status_code,200)

    def test_real_campaign_emits_three_quality_checked_posters_before_format_files(self):
        CampaignHubTests.setUpClass()
        events=[]
        def report(stage,asset_id=None,payload=None,qa=None):
            events.append((stage,asset_id,qa,bytes(payload[:8]) if payload else None))
        with patch("campaign_hub.find_scene",return_value=(None,{})),\
             patch("campaign_hub.choose_best",return_value=(
                 CampaignHubTests.sample_poster(),{
                     "passed":True,"score":96,"variation":1,
                     "warnings":[],"candidates_checked":1})):
            bundle=build_campaign(
                CampaignHubTests.product,CampaignHubTests.photo,
                use_gemini=False,progress=report)
        ready=[(i,id) for i,(status,id,_,_) in enumerate(events) if status=="ready"]
        self.assertEqual([id for _,id in ready],list(FOLDERS))
        self.assertLess(next(i for i,(stage,_,_,_) in enumerate(events)
                             if stage=="reviewing_posters"),ready[0][0])
        self.assertLess(ready[2][0],ready[3][0])
        self.assertLess(ready[-1][0],next(i for i,(stage,_,_,_) in enumerate(events)
                                       if stage=="finalising_pack"))
        for _,id,qa,signature in (row for row in events if row[0]=="ready"):
            self.assertIsInstance(qa,dict)
            self.assertEqual(signature,b"\x89PNG\r\n\x1a\n")
        self.assertEqual(len(bundle["manifest"]["images"])>=9,True)
        self.assertTrue(bundle["archive"][:2]==b"PK")

    def test_failed_critic_never_publishes_unchecked_poster(self):
        from test_ai_creative_director_v45 import TECH,PRICE,SMART,PRODUCT,image_bytes
        events=[]
        raw=[
            {"creative_canvas":PRICE},{"creative_canvas":SMART},
            {"creative_canvas":TECH}
        ]
        image=_png()
        with patch("campaign_hub._concepts",return_value=(
                raw,"gemini-assisted",[])),\
             patch("campaign_hub.find_scene",return_value=(None,{})),\
             patch("campaign_hub.require_good_asset",return_value={"passed":True}),\
             patch("campaign_hub.choose_best",return_value=(image,{"passed":True})),\
             patch("campaign_hub.review_finished_artworks",return_value={
                 "method":"test","reviewed":True,"issues":{"poster_price":["white_halo"]},
                 "warning":None}),\
             patch("campaign_hub.check_distinctness",return_value={
                 "passed":True,"issues":[],"pairs":[]}):
            with self.assertRaisesRegex(ValueError,"white_halo"):
                build_campaign(PRODUCT,image_bytes(),use_gemini=True,
                               progress=lambda *args:events.append(args))
        self.assertTrue(any(e[0]=="reviewing_posters" for e in events))
        self.assertFalse(any(e[0]=="ready" for e in events))

    @unittest.skipUnless(shutil.which("node"),"Node.js required to exercise browser UI")
    def test_browser_progress_cards_reveal_ready_png_only_once(self):
        source=studio.V7_HOME_PAGE
        start=source.index("// A progressive campaign is not a lower-quality draft.")
        end=source.index("// Safari may close or suspend",start)
        js=source[start:end]
        script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const els={};
const id='j'.repeat(32);
function el(k){
 if(!els[k])els[k]={hidden:true,textContent:'',innerHTML:'',
  dataset:{},href:'',src:'',title:''};
 return els[k];
}
const ctx={$:el,Set,encodeURIComponent,retainVerifiedCampaignPNG:()=>{},useCampaignLocalJob:()=>{}};
vm.createContext(ctx);
vm.runInContext(SOURCE,ctx);
const assets={poster_technical:{status:'ready'},
              poster_price:{status:'quality_checking'},
              social_story:{status:'queued'}};
ctx.renderProgressGallery(id,{
 status:'running',stage:'reviewing_posters',ready_count:1,assets});
assert.equal(els.campaignProgress.hidden,false);
assert.equal(els.previews.hidden,true);
assert.equal(els.campaignResults.hidden,true);
assert.match(els.campaignProgressCount.textContent,/1 of 9/);
assert.equal(els['progress-save-poster_technical'].hidden,false);
assert.equal(els['progress-img-poster_technical'].hidden,false);
assert.match(els['progress-img-poster_technical'].src,/job-assets\/j+/);
assert.equal(el('progress-img-poster_price').src,'');
assert.equal(el('progress-save-poster_price').hidden,true);
assert.match(els['progress-state-poster_price'].textContent,/Quality checking/);
ctx.renderProgressGallery(id,{
 status:'running',stage:'rendering_formats',ready_count:1,assets});
assert.equal(vm.runInContext('progressDisplayed.size',ctx),1);
ctx.renderProgressGallery(id,{
 status:'failed',stage:'failed',
 assets:{...assets,social_story:{status:'failed',error:'Missing verified photo'}}});
assert.match(els.campaignProgressZip.textContent,/ZIP unavailable/);
assert.equal(els['progress-img-poster_technical'].hidden,false);
assert.equal(els['progress-state-social_story'].title,'Missing verified photo');
assert.equal(els.campaignProgressGrid.innerHTML.match(/campaign-progress-card/g).length,9);
""".replace("SOURCE",repr(js))
        out=subprocess.run(["node","-e",script],capture_output=True,text=True,timeout=20)
        self.assertEqual(out.returncode,0,out.stdout+"\n"+out.stderr)


if __name__=="__main__":
    unittest.main()
