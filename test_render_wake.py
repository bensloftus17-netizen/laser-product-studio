"""Regression tests for Render HTML wake page reaching JSON-only API clients.

The existing product lookup route worked after deployment, but clients used
response.json() unconditionally. Free-host cold starts can return HTML outside
Flask. This tests the browser helper, safe retries and user-facing messaging.
"""
import re
import shutil
import subprocess
import unittest

from app import V7_HOME_PAGE


class RenderWakeUpTests(unittest.TestCase):
    def test_api_clients_check_response_type_and_use_safe_lookup_retries(self):
        html=V7_HOME_PAGE
        self.assertIn("async function readApiJson(response)",html)
        self.assertIn("async function lookupWithWakeRetry(url)",html)
        self.assertIn("Render is waking up. Retrying product lookup",html)
        self.assertIn("const data=await lookupWithWakeRetry(",html)
        self.assertNotIn("const data=await res.json()",html)
        # All POST actions validate response type, but are NOT retried
        # automatically, which could duplicate expensive AI requests.
        self.assertGreaterEqual(html.count("const data=await readApiJson("),3)
        self.assertEqual(html.count("lookupWithWakeRetry("),2)

    @unittest.skipUnless(shutil.which("node"),"Node.js not installed")
    def test_html_wake_screen_is_retried_then_json_succeeds_in_browser_logic(self):
        src=V7_HOME_PAGE
        start=src.index("// Render's free-hosting wake/deploy screen")
        end=src.index("async function load(part)",start)
        functions=src[start:end]
        script=r"""
const vm=require('node:vm');
const assert=require('node:assert/strict');
let statusMessages=[];
const context={
  fetch:null,
  setState:(message)=>{statusMessages.push(message)},
  setTimeout:(callback,delay)=>callback()
};
vm.createContext(context);
vm.runInContext(SOURCE,context);
const html={
  status:200,ok:true,
  headers:{get:()=> 'text/html; charset=utf-8'},
  json:()=>{throw Error('should NEVER parse HTML') }
};
const ok={
  status:200,ok:true,
  headers:{get:()=> 'application/json'},
  json:async()=>({product:{part:'8899'},photo_url:'/api/photo/8899'})
};
const missing={
  status:404,ok:false,
  headers:{get:()=> 'application/json'},
  json:async()=>({error:'Part not found'})
};
(async()=>{
 let calls=0;
 context.fetch=async()=>{calls++;return calls===1?html:ok;};
 const out=await context.lookupWithWakeRetry('/api/lookup/8899');
 assert.equal(out.product.part,'8899');
 assert.equal(calls,2);
 assert.equal(statusMessages.length,1);
 assert.match(statusMessages[0],/waking up/i);

 let thrown;
 try{await context.readApiJson(html);}catch(e){thrown=e;}
 assert.match(thrown.message,/starting up|unavailable/i);
 assert.equal(thrown.retryable,true);

 thrown=null;
 calls=0;
 context.fetch=async()=>{calls++;return missing;};
 try{await context.lookupWithWakeRetry('/api/lookup/nope');}
 catch(e){thrown=e;}
 assert.equal(calls,1,'Expected a 404 JSON not to be retried');
 assert.equal(thrown.message,'Part not found');

 // The POST parser must reject HTML immediately without executing fetch.
 thrown=null;
 try{await context.readApiJson(html);}catch(e){thrown=e;}
 assert.ok(thrown);
 console.log('Render wake HTML/retry and JSON API checks passed.');
})().catch(err=>{console.error(err);process.exitCode=1});
""".replace("SOURCE",repr(functions))
        result=subprocess.run(["node","-e",script],capture_output=True,
                              text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
