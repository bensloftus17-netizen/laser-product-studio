"""Native file-sharing regression tests: PNG and ZIP stay optional."""
import re
import shutil
import subprocess
import unittest

import app as studio


class NativeShareTests(unittest.TestCase):
    def test_every_download_area_offers_share_without_auto_opening(self):
        html = studio.V7_HOME_PAGE
        for control in ("campaignShareZip", "legacyShareZip", "aiEditorShare",
                        "shareNotice", "shareNoticeClose"):
            self.assertEqual(html.count('id="'+control+'"'), 1, control)
        self.assertIn("data-share-filename=", html)
        self.assertIn("data-ai-share=", html)
        self.assertIn("Share to apps", html)
        self.assertIn("Share graphic and message", html)
        self.assertIn("Rep Share Pack", html)
        self.assertEqual(html.count('id="campaignShareSocial"'), 1)
        self.assertIn("Preload ONLY after the user requests that individual share file.",html)
        self.assertIn("Share complete ZIP", html)
        self.assertIn("Share edited image to apps", html)
        self.assertIn("Share prepared ZIP", html)
        self.assertIn("Download complete ZIP", html)
        self.assertIn("Download PNG", html)
        self.assertIn("navigator.share(payload)", html)
        self.assertIn("navigator.canShare(payload)", html)
        self.assertIn("function prepareShareButtons(root)", html)
        self.assertIn("function shareDataImage(dataUrl,filename)", html)
        self.assertIn("Suggested captions are in the Copy Editor", html)
        # Generated campaign must render the gallery, NOT launch the share
        # sheet or a ZIP download without another deliberate user click.
        start=html.index("$('campaignBtn').addEventListener('click',async()=>{")
        end=html.index("$('distributorBrand').addEventListener('change'",start)
        handler=html[start:end]
        self.assertIn("showCampaign(data)",handler)
        self.assertNotIn("navigator.share",handler)
        self.assertNotIn("anchor.click()",handler)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for JS share gesture test")
    def test_native_share_calls_mobile_share_directly_on_click(self):
        html=studio.V7_HOME_PAGE
        start=html.index("// Native iOS/Android sharing.")
        end=html.index("function installMarketingHubLayout()",start)
        helper=html[start:end]
        js=r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const els = {};
const listeners = {};
let shareCalls = [], fetchCalls = 0, allowed = true;
function el(id) {
  if (!els[id]) els[id] = {hidden:true,disabled:false,textContent:'',dataset:{},
    addEventListener(type,fn){this.listener=fn;}};
  return els[id];
}
const sandbox = {
  document: {addEventListener(type,handler){listeners[type]=handler;}},
  $:el,updateRepShareGraphic(){},
  navigator: {
    canShare(data){return allowed && !!data.files?.length;},
    share(data){shareCalls.push(data);return Promise.resolve();}
  },
  File:class FakeFile {
    constructor(parts,name,options){this.parts=parts;this.name=name;this.type=options.type;}
  },
  Uint8Array, Promise,
  atob(encoded){return Buffer.from(encoded,'base64').toString('binary');},
  fetch(url){fetchCalls++;return Promise.resolve({
     ok:true,blob(){return Promise.resolve({body:'image'});}
  });},
  setTimeout(){return 1;}, clearTimeout(){}
};
vm.runInNewContext(process.argv[1],sandbox);
const clickTarget=(button)=>({target:{closest(selector){
  if(selector==='button[data-share-url]')return button;
  return null;
}}});
(async()=>{
  // data-URL image sharing must happen immediately on the user's tap.
  sandbox.shareDataImage('data:image/png;base64,aGVsbG8=', 'test.png');
  assert.equal(shareCalls.length,1);
  assert.equal(shareCalls[0].files[0].type,'image/png');
  assert.equal(shareCalls[0].files[0].name,'test.png');
  assert.equal(fetchCalls,0);

  // WebKit variants with share() but without canShare() can still receive
  // the actual image in their native share sheet from one direct tap.
  const originalCanShare=sandbox.navigator.canShare;
  delete sandbox.navigator.canShare;
  sandbox.shareDataImage('data:image/png;base64,aGVsbG8=', 'safari.png');
  assert.equal(shareCalls.length,2);
  assert.equal(shareCalls.at(-1).files[0].name,'safari.png');
  sandbox.navigator.canShare=originalCanShare;

  // A remote PNG is preloaded first and shared on a later user click,
  // without an asynchronous network call between click and share().
  const button={dataset:{shareUrl:'/api/campaign/assets/token/social_square',
    shareFilename:'LASER_7411_social_square.png'},
    disabled:false,textContent:'↗ Share PNG',title:''};
  sandbox.prepareShareButton(button);
  assert.equal(button.disabled,true);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(button.disabled,false);
  const callsBefore=shareCalls.length,fetchBefore=fetchCalls;
  listeners.click(clickTarget(button));
  assert.equal(shareCalls.length,callsBefore+1);
  assert.equal(fetchCalls,fetchBefore);
  assert.equal(shareCalls.at(-1).files[0].name,'LASER_7411_social_square.png');

  button.id='campaignShareSocial';
  el('repShareText').value='Reviewed message for the customer';
  listeners.click(clickTarget(button));
  assert.equal(shareCalls.at(-1).text,'Reviewed message for the customer');
  assert.equal(shareCalls.at(-1).files[0].type,'image/png');

  // Unsupported ZIP types never claim success and do not invoke a native
  // app share; the UI directs users to the existing download option.
  allowed=false;
  const noShare=shareCalls.length;
  sandbox.shareNativeFile(new sandbox.File(['zip'],'campaign.zip',{type:'application/zip'}));
  assert.equal(shareCalls.length,noShare);
  assert.match(el('shareNoticeText').textContent,/ZIP files directly/);
  assert.equal(el('shareNotice').hidden,false);
})().catch(e=>{console.error(e);process.exit(1);});
"""
        outcome=subprocess.run(
            ["node","-e",js,helper],capture_output=True,text=True,timeout=15
        )
        self.assertEqual(outcome.returncode,0,outcome.stderr)


if __name__=="__main__":
    unittest.main()
