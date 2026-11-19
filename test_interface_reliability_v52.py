"""V52: responsive layout and resilient complete-campaign loading.

Uses the real Flask routes and isolated Node browser scripts (network mocked).
No live Gemini, manufacturer fetch, made-up photo or cheaper QA mode required.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
import unittest
from unittest.mock import patch

import app as studio
from test_mobile_campaign_v47 import _bundle


class InterfaceAndReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=studio.V7_HOME_PAGE
        with open("static/styles.css",encoding="utf-8") as file:
            cls.css=file.read()

    def setUp(self):
        self.client=studio.app.test_client()
        with studio.CAMPAIGN_PACK_LOCK:
            studio.CAMPAIGN_PACKS.clear()
        with studio.CAMPAIGN_JOBS_LOCK:
            studio.CAMPAIGN_JOBS.clear()

    def tearDown(self):
        with studio.CAMPAIGN_PACK_LOCK:
            studio.CAMPAIGN_PACKS.clear()
        with studio.CAMPAIGN_JOBS_LOCK:
            studio.CAMPAIGN_JOBS.clear()

    def test_photo_has_separate_desktop_column_and_never_obscures_main_copy(self):
        stylesheet=self.css
        self.assertIn("V52: keep UI content strictly OUT of the hero",stylesheet)
        start=stylesheet.index("/* V52: keep UI content")
        end=stylesheet.index("/* V52 navigation",start)
        scoped=stylesheet[start:end]
        self.assertIn("position:absolute",stylesheet[
            stylesheet.index(".studio-hero-art{"):][:350])
        self.assertIn("width:calc(72% - 27px)",scoped)
        self.assertIn("max-width:calc(72% - 27px)",scoped)
        self.assertIn(".studio-main .searchpanel>.studio-hero-art{width:28%}",scoped)
        self.assertIn("@media(max-width:1180px)",scoped)
        self.assertIn("display:none!important",scoped)
        self.assertIn("width:100%;max-width:100%",scoped)
        self.assertIn(".studio-main .searchpanel #competitorPanel",scoped)
        self.assertIn(".studio-main .searchpanel #campaignStatus",scoped)
        self.assertIn("overflow-x:auto",scoped)
        self.assertIn("white-space:normal",scoped)

    def test_action_buttons_labels_and_9_artwork_cards_do_not_require_fixed_width(self):
        css=self.css
        self.assertIn("grid-template-columns:repeat(auto-fit,minmax(min(100%,170px),1fr))",css)
        self.assertIn("grid-template-columns:minmax(0,1fr)",css)
        self.assertIn(".asset-workspace .campaign-asset .campaign-asset-actions",css)
        self.assertIn(".studio-main .campaign-results-heading h3",css)
        self.assertIn(".studio-main .searchpanel .lookup-heading h2",css)
        self.assertIn(".studio-main .searchpanel .campaign-start",css)
        self.assertIn(".studio-top-links",css)
        self.assertIn("v52-responsive-recovery",self.html)
        self.assertEqual(self.html.count('id="heroProductPhoto"'),1)
        self.assertEqual(self.html.count('id="competitorPanel"'),1)

    def test_completed_pack_can_be_opened_after_old_15_minute_limit(self):
        self.assertEqual(studio.CAMPAIGN_PACK_TTL,45*60)
        self.assertEqual(studio.CAMPAIGN_JOB_TTL,55*60)
        token=studio._save_campaign_bundle(_bundle())
        with studio.CAMPAIGN_PACK_LOCK:
            entry=studio.CAMPAIGN_PACKS[token]
            entry["expires"]=time.time()+20*60
        usable=self.client.get("/api/campaign/assets/"+token+"/poster_technical")
        self.assertEqual(usable.status_code,200,usable.get_json(silent=True))
        self.assertEqual(usable.mimetype,"image/png")
        with studio.CAMPAIGN_PACK_LOCK:
            studio.CAMPAIGN_PACKS[token]["expires"]=time.time()-1
        expired=self.client.get("/api/campaign/assets/"+token+"/poster_technical")
        self.assertEqual(expired.status_code,404)
        self.assertIn("expired",expired.get_json()["error"].lower())

    def test_recovery_message_and_progress_status_are_honest(self):
        page=self.html
        self.assertIn("Date.now()-state.savedAt>45*60*1000",page)
        self.assertIn("Links are temporary (up to 45 minutes",page)
        self.assertIn("Connection interrupted while checking progress",page)
        self.assertIn("Retrying automatically",page)
        self.assertIn("retryable===true",page)
        self.assertIn("Use Reopen Campaign",page)
        self.assertIn("getRecoverableCampaign()",page)
        self.assertIn("recover.status==='running'",page)
        self.assertIn("startFullQualityCampaign(part,body)",page)
        self.assertIn("Another full-quality campaign is being prepared",page)
        self.assertIn("renderProgressGallery(started.job_id",page)
        self.assertIn("retainVerifiedCampaignPNG(jobId,id,url)",page)
        self.assertIn("campaignLocalPNGs",page)
        self.assertIn("source_qr",page)

    @unittest.skipUnless(shutil.which("node"),"Node.js is needed for browser JS test")
    def test_transient_progress_network_error_retries_same_job(self):
        start=self.html.index("async function pollMobileCampaign(job_id)")
        end=self.html.index("async function resumeLastMobileCampaign()",start)
        script=self.html[start:end]
        node=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const jobId='j'.repeat(32);
let requests=[],viewed=[],status='';
const state={};
const $=id=>(state[id]||(state[id]={textContent:''}));
const context={
 $,TypeError,Error,Promise,encodeURIComponent,
 PROGRESS_STAGE_LABELS:{planning:'Planning',complete:'Complete'},
 renderProgressGallery:(job,data)=>viewed.push([job,data.status]),
 readApiJson:async response=>response.value,
 fetch:async(url,opts)=>{
  requests.push({url,method:opts.method||'GET'});
  if(requests.length===1)throw new TypeError('Failed to fetch');
  if(requests.length===2)return {value:{status:'running',stage:'planning',
      ready_count:0,elapsed_seconds:20}};
  return {value:{status:'ready',stage:'complete',token:'z'.repeat(32),
      manifest:{part:'8899',title:'Official product',images:[]}}};
 },
 setTimeout:resolve=>resolve()
};
vm.createContext(context);vm.runInContext(SOURCE,context);
(async()=>{
 const output=await context.pollMobileCampaign(jobId);
 assert.equal(output.status,'ready');
 assert.equal(requests.length,3);
 assert.equal(requests.every(r=>r.url.endsWith(jobId)&&r.method==='GET'),true);
 assert.equal(viewed.length,2);
 assert.equal(viewed[1][1],'ready');
 assert.match(state.campaignStatus.textContent,/graphics ready/);
})().catch(error=>{console.error(error);process.exitCode=1});
""".replace("SOURCE",repr(script))
        proc=subprocess.run(["node","-e",node],capture_output=True,
                            text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stdout+"\n"+proc.stderr)

    @unittest.skipUnless(shutil.which("node"),"Node.js is needed for browser JS test")
    def test_server_busy_auto_retry_does_not_double_start(self):
        start=self.html.index("// Free Render only runs one high-resolution job")
        end=self.html.index("$('campaignBtn').addEventListener('click'",start)
        script=self.html[start:end]
        node=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
let tries=0,types=[],waits=[];
const state={};
const ctx={
 $:id=>(state[id]||(state[id]={textContent:''})),
 TypeError,Error,Promise,JSON,encodeURIComponent,
 setTimeout:(cb,ms)=>{waits.push(ms);cb()},
 fetch:async(url,opts)=>{
  tries++;types.push({url,method:opts.method});
  if(tries===1)return {status:429,headers:{get:()=> '8'}};
  return {status:202,headers:{get:()=>null},json:async()=>({job_id:'x'.repeat(32)})};
 },
 readApiJson:async r=>r.json()
};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
(async()=>{
 const result=await ctx.startFullQualityCampaign('9395',{distributor_brand:'none'});
 assert.equal(result.job_id,'x'.repeat(32));
 assert.equal(tries,2);
 assert.equal(types[0].method,'POST');
 assert.equal(types[0].url,'/api/campaign/start/9395');
 assert.deepEqual(waits,[8000]);
 assert.match(state.campaignStatus.textContent,/retry automatically/);
})().catch(error=>{console.error(error);process.exitCode=1});
""".replace("SOURCE",repr(script))
        proc=subprocess.run(["node","-e",node],capture_output=True,
                            text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stdout+"\n"+proc.stderr)

    @unittest.skipUnless(shutil.which("node"),"Node.js is needed for browser JS test")
    def test_verified_png_is_kept_locally_for_lazy_scroll_after_server_expiry(self):
        start=self.html.index("// V52: keep a verified PNG copy")
        end=self.html.index("// A progressive campaign is not a lower-quality draft.",start)
        script=self.html[start:end]
        node=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
let count=0,revoked=[];
const id='poster_price',job='j'.repeat(32);
const progressImg={src:'',hidden:true,closest:()=>({})},open={href:'',hidden:true},
      save={href:'',hidden:true};
const image={src:''},link={href:''},download={href:''},share={dataset:{}},
      load={textContent:''},retry={hidden:false};
const card={querySelector:sel=>({
 'img':image,'a[aria-label]':link,'.campaign-save-image':download,
 'button[data-share-url]':share,'[data-load-state]':load,
 '[data-retry-asset]':retry
})[sel]};
const els={
 ['progress-img-'+id]:progressImg,['progress-open-'+id]:open,
 ['progress-save-'+id]:save,campaignShareSocial:{dataset:{}}
};
const ctx={
 $:key=>els[key]||null,Map,Blob,Promise,console,
 campaignData:{token:'t'.repeat(32)},progressJobShown:job,
 document:{querySelector:()=>card},
 fetch:async(url)=>{
  count++;
  return {ok:true,blob:async()=>new Blob(['valid-image-data-1234567890'],
                                  {type:'image/png'})};
 },
 URL:{createObjectURL:()=>'blob:verified-1',
      revokeObjectURL:url=>revoked.push(url)}
};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
(async()=>{
 ctx.useCampaignLocalJob(job);
 ctx.retainVerifiedCampaignPNG(job,id,'/api/campaign/job-assets/'+job+'/'+id);
 ctx.retainVerifiedCampaignPNG(job,id,'/api/campaign/job-assets/'+job+'/'+id);
 await vm.runInContext('campaignLocalPending.get("poster_price")',ctx);
 assert.equal(count,1);
 assert.equal(progressImg.src,'blob:verified-1');
 assert.equal(image.src,'blob:verified-1');
 assert.equal(download.href,'blob:verified-1');
 assert.equal(share.dataset.shareUrl,'blob:verified-1');
 assert.equal(retry.hidden,true);
 assert.match(load.textContent,/safely loaded/);
 ctx.useCampaignLocalJob('k'.repeat(32));
 assert.deepEqual(revoked,['blob:verified-1']);
})().catch(error=>{console.error(error);process.exitCode=1});
""".replace("SOURCE",repr(script))
        proc=subprocess.run(["node","-e",node],capture_output=True,
                            text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stdout+"\n"+proc.stderr)


if __name__=="__main__":
    unittest.main()
