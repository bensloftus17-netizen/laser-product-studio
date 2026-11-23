/* V75: execute the *actual* button function under a simulated asleep server.
 * If the button accidentally fetches /why-laser again, this test fails.
 * Offline test; real source validation and actual PDF are checked in Python.
 */
'use strict';
const fs=require('fs');
const vm=require('vm');
const assert=require('assert');
const html=fs.readFileSync('app.py','utf8');
function between(a,b){
 const first=html.indexOf(a);
 const last=html.indexOf(b,first);
 assert(first>=0&&last>first, 'Function markers missing: '+a);
 return html.slice(first,last);
}
const support=between('let competitorShownPart=null, competitorBusy=false;',
                      'const competitorPriceLabel =');
const onclick=between('async function buildWhyLaserSheet(){',
                      "$('whyLaserBtn').addEventListener('click',buildWhyLaserSheet);");

const elements={
 part:{value:'4832'},
 whyLaserPanel:{hidden:true},
 whyLaserStatus:{textContent:''},
 whyLaserContent:{textContent:''},
 whyLaserPdf:{hidden:true,href:'',download:''},
 whyLaserBtn:{disabled:false},
};
let fetchCount=0, blobCreated=0, revoked=0, displayed=null;
const testContext=vm.createContext({
 $:key=>{
   assert(Object.hasOwn(elements,key),'Unexpected page element: '+key);
   return elements[key];
 },
 fetch:async ()=>{fetchCount++;throw Error('Render worker is asleep!')},
 URL:{
  createObjectURL:blob=>{
   blobCreated++;
   assert.strictEqual(blob.type,'application/pdf');
   assert(blob.size>5);
   return 'blob:offline-source-checked';
  },
  revokeObjectURL:()=>{revoked++},
 },
 Blob,Uint8Array,atob,
 console,
 displayWhyLaserSheet:sheet=>{displayed=sheet},
 encodeURIComponent,
 readApiJson:async ()=>{throw Error('Must not request JSON')},
});
vm.runInContext(support+'\n'+onclick,testContext,{timeout:2000});
const sheet={part:'4832',title:'Laser Brake Bleeder',review_required:true,
 public_claim_approved:false,competitors:[{brand:'Draper'}]};
const pdf=Buffer.from('%PDF-1.4\nsource-backed mock','ascii').toString('base64');
vm.runInContext(
 'competitorShownPart="4832";whyLaserBrowserPack='+JSON.stringify({
  sheet,pdf_base64:pdf,
 })+';',testContext);
(async()=>{
 await vm.runInContext('buildWhyLaserSheet()',testContext,{timeout:2000});
 assert.strictEqual(fetchCount,0,'Do not call Render after clicking the button');
 assert.strictEqual(blobCreated,1,'PDF must be created from already sourced bytes');
 assert.strictEqual(displayed.part,'4832');
 assert.strictEqual(displayed.public_claim_approved,false);
 assert.strictEqual(elements.whyLaserPdf.href,'blob:offline-source-checked');
 assert.strictEqual(elements.whyLaserPdf.hidden,false);
 assert.strictEqual(elements.whyLaserBtn.disabled,false);
 assert(elements.whyLaserStatus.textContent.includes('even if Render restarts'));
 elements.part.value='9395';
 await vm.runInContext('buildWhyLaserSheet()',testContext,{timeout:2000});
 assert.strictEqual(elements.whyLaserPdf.hidden,true,
                    'Never display previous part PDF after input changes');
 assert.strictEqual(fetchCount,0);
 vm.runInContext('clearWhyLaserBrowserPack()',testContext,{timeout:2000});
 assert.strictEqual(revoked,1,'Old Blob URL must not leak');
 console.log('PASS: Why Choose Laser button and downloadable PDF survive simulated worker shutdown');
})().catch(error=>{console.error(error);process.exit(1)});
