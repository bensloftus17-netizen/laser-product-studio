"""V47: mobile Safari full campaign recovery and preview/display regression."""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import unittest
from unittest.mock import patch

from PIL import Image

import app as studio
from campaign_hub import FOLDERS


def _png():
    result=io.BytesIO()
    Image.new("RGB",(100,100),"#0C4778").save(result,"PNG")
    return result.getvalue()


def _bundle(part="6330"):
    image=_png()
    keys=tuple(FOLDERS)
    return {
        "manifest":{
            "part":part,"title":"Official Source Product",
            "images":[{"id":k,"path":FOLDERS[k]} for k in keys],
            "generation_method":"verified-template-fallback",
            "files":list(FOLDERS.values()),
            "angles":[{"name":"Technical","role":"technical_application","headline":"Official Product",
                       "selling_point":"Confirmed manufacturer detail","focus":"application","family":"trade"},
                      {"name":"Price","role":"price_promo","headline":"Official Product",
                       "selling_point":"Confirmed manufacturer detail","focus":"price","family":"retail"},
                      {"name":"Product","role":"product_selected","headline":"Official Product",
                       "selling_point":"Confirmed manufacturer detail","focus":"benefit","family":"premium"}],
            "copy":[], "artwork_quality":{}, "marketing_strategy":{},
            "format_artwork_quality":{},
        },
        "images":{k:image for k in keys},
        "archive":b"PK\x05\x06"+b"\x00"*18,
    }


class MobileCampaignRecoveryTests(unittest.TestCase):
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

    def _started(self,part="6330"):
        # Never spin up a real background thread in unit tests; run the exact
        # queued job synchronously after first asserting the HTTP 202 status.
        worker=patch("app.threading.Thread")
        thread=worker.start()
        self.addCleanup(worker.stop)
        response=self.client.post(
            "/api/campaign/start/"+part,
            json={"distributor_brand":"none","staff_rrp_reviewed":False})
        self.assertEqual(response.status_code,202,response.get_json())
        job=response.get_json()["job_id"]
        self.assertRegex(job,r"^[A-Za-z0-9_-]{24,64}$")
        kwargs=thread.call_args.kwargs
        self.assertEqual(kwargs["target"],studio._run_campaign_job)
        self.assertEqual(kwargs["args"][0],job)
        return job,kwargs["target"],kwargs["args"]

    def test_mobile_start_returns_immediately_and_finished_pack_is_resumable(self):
        with patch("app._assemble_campaign_bundle",return_value=_bundle()) as render:
            job,work,args=self._started()
            queued=self.client.get("/api/campaign/jobs/"+job)
            self.assertEqual(queued.status_code,200)
            self.assertEqual(queued.get_json()["status"],"queued")
            self.assertNotIn("manifest",queued.get_json())
            work(*args)
            self.assertEqual(render.call_count,1)
            completed=self.client.get("/api/campaign/jobs/"+job)
            self.assertEqual(completed.status_code,200)
            payload=completed.get_json()
            self.assertEqual(payload["status"],"ready")
            self.assertEqual(payload["part"],"6330")
            self.assertEqual(len(payload["manifest"]["images"]),len(FOLDERS))
            token=payload["token"]
            resumed=self.client.get("/api/campaign/manifest/"+token)
            self.assertEqual(resumed.status_code,200)
            self.assertEqual(resumed.get_json()["manifest"],payload["manifest"])
            self.assertIn("no-store",resumed.headers["Cache-Control"])
            asset=self.client.get("/api/campaign/assets/"+token+"/poster_technical")
            self.assertEqual(asset.status_code,200)
            self.assertEqual(asset.data,_png())
            archive=self.client.get("/api/campaign/download/"+token)
            self.assertEqual(archive.status_code,200)
            self.assertEqual(archive.data,_bundle()["archive"])

    def test_bounded_generation_reports_rejection_without_fake_success(self):
        with patch("app._assemble_campaign_bundle",
                   side_effect=ValueError("Verified tool photo cannot be isolated")):
            job,work,args=self._started()
            work(*args)
            response=self.client.get("/api/campaign/jobs/"+job).get_json()
            self.assertEqual(response["status"],"failed")
            self.assertIn("photo",response["error"])
            self.assertNotIn("manifest",response)
        self.assertEqual(studio.CAMPAIGN_PACKS,{})

    def test_no_unbounded_mobile_jobs(self):
        with patch("app.threading.Thread") as fake:
            payload={"distributor_brand":"none"}
            self.assertEqual(self.client.post(
                "/api/campaign/start/6330",json=payload).status_code,202)
            self.assertEqual(self.client.post(
                "/api/campaign/start/6728",json=payload).status_code,202)
            blocked=self.client.post("/api/campaign/start/9395",json=payload)
            self.assertEqual(blocked.status_code,429)
            self.assertIn("already",blocked.get_json()["error"])
            self.assertEqual(fake.call_count,2)

    def test_mobile_job_and_completed_token_are_not_guessable(self):
        for path in ("/api/campaign/jobs/not-real",
                     "/api/campaign/manifest/not-real",
                     "/api/campaign/jobs/"+("a"*34)):
            response=self.client.get(path)
            self.assertEqual(response.status_code,404)
        self.assertEqual(self.client.post("/api/campaign/start/!",
                           json={}).status_code,400)
        self.assertEqual(self.client.post("/api/campaign/start/6330",
                           json={"huge":"x"*4000}).status_code,400)

    def test_html_distinguishes_three_previews_from_full_campaign(self):
        html=studio.V7_HOME_PAGE
        for ident in ("previewBuildFull","previewCampaignCallout",
                      "campaignAssetCount","campaignRecovery","campaignResume"):
            self.assertEqual(html.count('id="'+ident+'"'),1,ident)
        self.assertIn("These are only three quick previews",html)
        self.assertIn("Build All 9 Graphics",html)
        self.assertIn("/api/campaign/start/",html)
        self.assertIn("/api/campaign/jobs/",html)
        self.assertIn("/api/campaign/manifest/",html)
        self.assertIn("sessionStorage.setItem(CAMPAIGN_RESUME_KEY",html)
        self.assertIn("renderCampaignGallery(data);",html)
        # Paint images *before* sharing helpers/copy editing; a slow Safari
        # share API must not prevent the gallery showing.
        begin=html.index("function showCampaign(data)")
        gallery=html.index("renderCampaignGallery(data);",begin)
        share=html.index("prepareShareButtons($('campaignResults'));",begin)
        self.assertLess(gallery,share)
        self.assertIn("loading=\"'+(index<3?'eager':'lazy')+'\"",html)

    def test_hidden_preview_css_overrides_specific_grid_display(self):
        with open("static/styles.css",encoding="utf-8") as fp:
            css=fp.read()
        self.assertIn(".asset-workspace .previews[hidden]",css)
        self.assertIn(".campaign-mobile-recovery[hidden]",css)
        self.assertIn(".preview-campaign-callout[hidden]",css)
        self.assertIn("display:none!important",css)
        self.assertIn("grid-template-columns:minmax(0,1fr)",css)

    @unittest.skipUnless(shutil.which("node"),"Node.js needed for mobile resume test")
    def test_safari_browser_recovers_running_campaign_after_reload(self):
        html=studio.V7_HOME_PAGE
        start=html.index("// Safari may close or suspend the page")
        end=html.index("function showCampaign(data)",start)
        helpers=html[start:end]
        node=r"""
const vm=require('node:vm');
const assert=require('node:assert/strict');
const store=new Map(),els={},requests=[];
let stage=0,received=null;
const ctx={
 sessionStorage:{
  getItem:k=>store.get(k)||null,
  setItem:(k,v)=>store.set(k,v),
  removeItem:k=>store.delete(k)
 },
 $:(id)=>{
  if(!els[id])els[id]={hidden:true,disabled:false,
   textContent:'',addEventListener(type,fn){this.handler=fn;}};
  return els[id];
 },
 Date,Promise,console,encodeURIComponent,
 setTimeout:cb=>cb(),
 fetch:async(url)=>{
  requests.push(url);
  if(url.includes('/jobs/')){
    stage++;
    return {ok:true,headers:{get:()=> 'application/json'},
      json:async()=>stage<2?{status:'running'}:
       {status:'ready',token:'t'.repeat(32),
        manifest:{part:'6330',title:'Laser Tools',images:Array.from({length:9},(_,i)=>({id:String(i)}))}}};
  }
  throw Error('Unexpected URL '+url);
 },
 readApiJson:async(result)=>result.json(),
 showCampaign:(data)=>{received=data;},
 active:null,activePhoto:null,inflight:false
};
vm.createContext(ctx);
vm.runInContext(SOURCE,ctx);
(async()=>{
 ctx.rememberMobileJob('j'.repeat(32),'6330');
 assert.equal(els.campaignRecovery.hidden,false);
 assert.equal(ctx.getRecoverableCampaign().status,'running');
 await ctx.resumeLastMobileCampaign();
 assert.equal(received.manifest.part,'6330');
 assert.equal(ctx.getRecoverableCampaign().status,'ready');
 assert.equal(stage,2);
 assert.equal(els.part.value,'6330');
 assert.match(els.campaignStatus.textContent,/Recovered your complete campaign/);
 assert.equal(els.campaignResume.disabled,false);
 console.log('Safari mobile campaign interruption and re-open flow passed');
})().catch(err=>{console.error(err);process.exitCode=1});
""".replace("SOURCE",repr(helpers))
        result=subprocess.run(["node","-e",node],capture_output=True,
                              text=True,timeout=25)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)


if __name__=="__main__":
    unittest.main()
