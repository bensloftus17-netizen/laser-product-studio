"""V49: grounded competitor comparisons, UK pricing and source provenance.

Never requires live external services: all web traffic is mocked. Covers
shopping results, actual retailer product markup, RSS, unrelated products,
SSRF, English UI, AI downgrades and Excel-safe exports.
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import unittest
from unittest.mock import patch

import requests
import app as studio
import competitor_finder as cf


LASER={
    "part":"9395",
    "title":"Front Wheel Bearing Kit - Mercedes Sprinter / VW Crafter",
    "description":"Bearing replacement kit for commercial vehicles.",
    "features":[
        "For front wheel bearing removal and installation",
        "For Mercedes-Benz Sprinter and Volkswagen Crafter",
        "Six threaded bars included"],
    "source":"https://www.toolconnection.co.uk/products/cars-vans/9395",
    "price":"£350.00 excluding VAT",
    "price_status":"Official UK RRP",
}
PRODUCT_URL="https://www.toolden.co.uk/products/bgs-technic-wheel-bearing-kit-sprinter-crafter"
TITLE="BGS Technic Front Wheel Bearing Kit Mercedes Sprinter VW Crafter"
DETAILS={
 "@context":"https://schema.org",
 "@type":"Product","name":TITLE,
 "sku":"BGS-2345","brand":{"@type":"Brand","name":"BGS Technic"},
 "offers":{"@type":"Offer","price":"187.99","priceCurrency":"GBP"}
}
PAGE=('<html lang="en"><head><title>'+TITLE+'</title>'+
      '<script type="application/ld+json">'+json.dumps(DETAILS)+
      '</script></head><body><h1>'+TITLE+'</h1></body></html>').encode()
RSS=b'''<?xml version="1.0"?>
<rss version="2.0"><channel><item>
<title>BGS Technic Front Wheel Bearing Kit Sprinter Crafter</title>
<link>https://www.toolden.co.uk/products/bgs-technic-wheel-bearing-kit-sprinter-crafter</link>
<description>Stocked in UK</description></item></channel></rss>'''


class DummyResponse:
    def __init__(self,*,data=None,body=b"",content_type="text/html",status=200):
        self._data=data
        self.content=body
        self.headers={"content-type":content_type}
        self.status_code=status
    def json(self):return self._data
    def raise_for_status(self):
        if self.status_code>=400:
            raise requests.HTTPError("Unexpected status")
    def __bool__(self):return self.status_code<400


class MockSearch:
    def __init__(self):
        self.calls=[]
        self.requests=0
    def get(self,url,**kwargs):
        self.calls.append(url)
        self.requests+=1
        if url==cf.SHOPPING_HOST:
            return DummyResponse(data={"shopping_results":[{
                "title":TITLE,"product_link":PRODUCT_URL,
                "source":"Toolden","extracted_price":187.99,
                "price":"£187.99",
            },{
                "title":"Laser Tools Front Wheel Bearing Kit",
                "product_link":"https://www.toolden.co.uk/laser-9395",
                "source":"Toolden","extracted_price":330,"price":"£330.00",
            },{
                "title":"Sealey Screwdriver Set",
                "product_link":"https://www.toolden.co.uk/sealey-screwdriver",
                "extracted_price":99,"price":"£99.00",
            }]})
        if url==cf.SECONDARY_SEARCH_HOST:
            return DummyResponse(status=404)
        if url==cf.SEARCH_HOST:
            return DummyResponse(body=RSS,content_type="application/rss+xml")
        if url==PRODUCT_URL:
            return DummyResponse(body=PAGE)
        # The bounded catalogue-lead catalogue now contains genuine
        # manufacturer pages. Simulate a temporarily unavailable listing.
        if cf.safe_url(url):
            return DummyResponse(status=404)
        raise AssertionError("Unsafe external request: "+url)
    def post(self,url,**kwargs):
        return DummyResponse(data={"candidates":[{
            "content":{"parts":[{"text":json.dumps({"downgrade":[
                {"id":0,"reason":"Check bearing installation equipment"}
            ]})}]}
        }]})


class CompetitorFinderTests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()

    def tearDown(self):
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()

    def test_tool_type_and_fitment_classification_cannot_claim_proven_equivalence(self):
        signature=cf.tool_signature(LASER)
        self.assertEqual(signature["type"],"wheel bearing")
        self.assertIn("sprinter",signature["fitments"])
        self.assertIn("crafter",signature["fitments"])
        likely=cf.match_status(signature,TITLE)
        self.assertIn("Likely equivalent",likely[0])
        self.assertIn("verify",likely[0].lower())
        partial=cf.match_status(signature,"Sealey Wheel Bearing Puller for Mercedes Sprinter")
        self.assertIn("coverage differs",partial[0])
        general=cf.match_status(signature,"Draper Wheel Bearing Service Kit")
        self.assertIn("application unverified",general[0])
        self.assertIsNone(cf.match_status(signature,"Draper 40pc Socket Set"))
        # An unknown title must still enter research, but can only produce
        # conservatively qualified search leads—not a guaranteed competitor.
        unknown=cf.tool_signature({"title":"Large component in the workshop"})
        self.assertEqual(unknown["category_source"],"official-title-derived")
        self.assertTrue(cf.search_queries(unknown))

    def test_price_from_official_currency_and_no_fabricated_vat(self):
        for value,expected in [
            ("£112.75","112.75"),("GBP 112","112.00"),
            (112.75,"112.75"),("0","0.00"),("£0.01","0.01"),
            ("£12,300.35","12300.35")]:
            actual=cf.price_from_raw(value)
            if value=="0":
                self.assertIsNone(actual)
            else:
                self.assertEqual(actual,expected)
        for bad in ("€120","$120","free",None,"-5","0","£0.00",
                    "1e9","9999999.99","25.00 + VAT"):
            self.assertIsNone(cf.price_from_raw(bad))
        product=cf.parse_product_page(PAGE,PRODUCT_URL,cf.tool_signature(LASER))
        self.assertEqual(product["price_gbp"],"187.99")
        self.assertEqual(product["part_number"],"BGS-2345")
        self.assertEqual(product["vat_basis"],"unknown")
        self.assertEqual(product["price_source"],"Retailer JSON-LD product offer")

    def test_rejects_non_gbp_and_aggregate_prices(self):
        schema={**DETAILS,"offers":{
            "@type":"Offer","price":"50","priceCurrency":"USD"}}
        page=('<html><head><title>'+TITLE+'</title>'+
              '<script type="application/ld+json">'+json.dumps(schema)+
              '</script></head></html>').encode()
        parsed=cf.parse_product_page(page,PRODUCT_URL,cf.tool_signature(LASER))
        self.assertIsNone(parsed["price_gbp"])
        schema["offers"]={"@type":"AggregateOffer","lowPrice":"5",
                          "priceCurrency":"GBP"}
        page=('<html><head><title>'+TITLE+'</title>'+
              '<script type="application/ld+json">'+json.dumps(schema)+
              '</script></head></html>').encode()
        parsed=cf.parse_product_page(page,PRODUCT_URL,cf.tool_signature(LASER))
        self.assertIsNone(parsed["price_gbp"])

    def test_seal_provenance_and_block_ssrf(self):
        for url in (
            "http://www.toolden.co.uk/anything",
            "https://127.0.0.1/secret",
            "https://169.254.169.254/latest/meta-data",
            "https://evil.example/anything",
            "https://toolden.co.uk.evil.example/anything",
            "file:///etc/passwd",
            "https://admin:pass@www.toolden.co.uk/anything",
            "https://www.toolden.co.uk:444/anything",
            "https://www.toolden.co.uk/\nInjected: true",
        ):
            self.assertFalse(cf.safe_url(url),url)
        self.assertTrue(cf.safe_url(PRODUCT_URL))
        search=MockSearch()
        self.assertIsNone(cf._get_product_page(
            "http://localhost/secrets",cf.tool_signature(LASER),search))
        self.assertEqual(search.calls,[])

    def test_shopping_results_cite_true_gbp_price_and_exclude_laser(self):
        search=MockSearch()
        rows,warning=cf.shopping_search(cf.tool_signature(LASER),search,api_key="test-key")
        self.assertIsNone(warning)
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row["brand"],"BGS Technic")
        self.assertEqual(row["price_gbp"],"187.99")
        self.assertEqual(row["price_source"],"Google Shopping listing")
        self.assertIn("verify",row["match_status"].lower())
        self.assertEqual(row["url"],PRODUCT_URL)
        params=search.calls
        self.assertEqual(params[0],cf.SHOPPING_HOST)

    def test_rss_only_permits_manufacturer_or_retailer_product_pages(self):
        search=MockSearch()
        matches,notice=cf.keyless_discovery(cf.tool_signature(LASER),search)
        self.assertIsNone(notice)
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["part_number"],"BGS-2345")
        self.assertEqual(matches[0]["price_gbp"],"187.99")
        self.assertEqual(search.calls.count(PRODUCT_URL),1)
        with self.assertRaises(ValueError):
            cf._parse_rss(b"<html><body>Blocked</body></html>")
        with self.assertRaises(ValueError):
            cf._parse_rss(b"not XML")

    def test_complete_research_without_serpapi_key_still_finds_genuine_products(self):
        search=MockSearch()
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            report=cf.research_competitors(LASER,session=search)
        self.assertEqual(report["count"],1)
        self.assertEqual(report["results"][0]["brand"],"BGS Technic")
        self.assertEqual(report["results"][0]["price_gbp"],"187.99")
        self.assertIn("Public product-page search",report["providers"])
        self.assertTrue(report["review_required"])
        self.assertTrue(any("key" in w.lower() for w in report["warnings"]))
        self.assertTrue(all(
            "gemini" not in u and "serpapi" not in u for u in search.calls))
        self.assertEqual(report["laser"]["part"],"9395")

    def test_ai_may_downgrade_never_upgrade_or_invent_prices(self):
        search=MockSearch()
        rows=[cf._build_result(TITLE,PRODUCT_URL,cf.tool_signature(LASER),
                               price=200,price_origin="Retailer JSON-LD product offer")]
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret",
                                     "GEMINI_MODEL":"gemini-3.5-flash-lite"}):
            note=cf._ai_review(LASER,cf.tool_signature(LASER),rows,search)
        self.assertIn("AI-assisted",note)
        self.assertEqual(rows[0]["match_status"],
                         "Similar tool — technical verification required")
        self.assertEqual(rows[0]["price_gbp"],"200.00")

    def test_no_results_are_explained_not_fabricated(self):
        search=MockSearch()
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            report=cf.research_competitors(
                {**LASER,"title":"Quantum Ignition Timing Kit for Unknown Tractor"},
                session=search)
        self.assertEqual(report["results"],[])
        self.assertTrue(any("does not prove" in w for w in report["warnings"]))

    def test_csv_has_source_url_and_escapes_excel_formulas(self):
        rows=[cf._build_result(TITLE,PRODUCT_URL,cf.tool_signature(LASER),
            sku="BGS-2345",seller="=HYPERLINK('x')",
            price="123.45",price_origin="Retailer JSON-LD product offer")]
        report={"laser":LASER,"results":rows,
                "checked_at_utc":"2026-11-19T09:00:00+00:00"}
        blob=cf.report_csv(report)
        self.assertTrue(blob.startswith(b"\xef\xbb\xbf"))
        csv_rows=list(csv.reader(io.StringIO(blob.decode("utf-8-sig"))))
        self.assertEqual(csv_rows[0][5],"UK advertised price GBP")
        self.assertEqual(csv_rows[1][5],"123.45")
        self.assertEqual(csv_rows[1][8],"'=HYPERLINK('x')")
        self.assertEqual(csv_rows[1][11],PRODUCT_URL)

    def test_flask_endpoint_cache_refresh_and_excel_export(self):
        fake={
            "laser":{"part":"9395","title":LASER["title"],
                     "tool_type":"wheel bearing"},
            "results":[cf._build_result(
                TITLE,PRODUCT_URL,cf.tool_signature(LASER),
                price="187.99",price_origin="Retailer JSON-LD product offer")],
            "checked_at_utc":"2026-11-19T09:00:00+00:00",
            "providers":["Public product-page search"],
            "warnings":[],"ai_matching":"Rules-based"}
        with patch.object(studio,"lookup",return_value=(LASER,b"official-source-photo")),\
             patch.object(studio,"research_competitors",return_value=fake) as fn:
            first=self.client.get("/api/competitors/9395")
            self.assertEqual(first.status_code,200,first.get_json())
            self.assertEqual(first.get_json()["count"] if "count" in
                first.get_json() else len(first.get_json()["results"]),1)
            again=self.client.get("/api/competitors/9395")
            self.assertEqual(again.status_code,200)
            self.assertTrue(again.get_json()["cached"])
            self.assertEqual(fn.call_count,1)
            self.assertIn("no-store",again.headers["Cache-Control"])
            sheet=self.client.get("/api/competitors/9395/export.csv")
            self.assertEqual(sheet.status_code,200)
            self.assertIn(b"187.99",sheet.data)
            self.assertIn(PRODUCT_URL.encode(),sheet.data)
            self.assertIn(b"Competitor part number",sheet.data)
            # No SKU was provided by this mocked listing: leave it unknown.
            self.assertIn("attachment",sheet.headers["Content-Disposition"])
            refresh=self.client.get("/api/competitors/9395?refresh=1")
            self.assertEqual(refresh.status_code,200)
            self.assertEqual(fn.call_count,2)

    def test_server_bounded_inflight_searches_and_export_requires_lookup(self):
        self.assertEqual(self.client.get(
            "/api/competitors/9395/export.csv").status_code,404)
        with patch.object(studio,"lookup",return_value=(LASER,None)):
            studio.COMPETITOR_REPORT_BUSY.acquire()
            try:
                busy=self.client.get("/api/competitors/9395")
                self.assertEqual(busy.status_code,429)
                self.assertIn("already running",busy.get_json()["error"])
            finally:
                studio.COMPETITOR_REPORT_BUSY.release()

    def test_ui_has_competitor_button_prices_sources_and_xss_escape(self):
        page=studio.V7_HOME_PAGE
        for identifier in ("competitorBtn","competitorPanel","competitorTitle",
                           "competitorStatus","competitorResults","competitorExport",
                           "competitorRefresh","competitorSources"):
            self.assertEqual(page.count('id="'+identifier+'"'),1,identifier)
        for term in ("Find competitors","UK advertised price",
                     "source","VAT unconfirmed","CSV",
                     "noopener noreferrer","function findCompetitors"):
            self.assertIn(term,page)
        self.assertIn("esc(item.title)",page)
        self.assertIn("esc(item.match_status)",page)
        self.assertIn("esc(url)",page)
        self.assertIn("url.startsWith('https://')",page)

    @unittest.skipUnless(shutil.which("node"),"Node.js needed for JS UI smoke")
    def test_browser_renders_credible_comparison_and_csv_link(self):
        src=studio.V7_HOME_PAGE
        start=src.index("// V49 — source-linked competitor research.")
        end=src.index("$('campaignBtn').addEventListener('click'",start)
        helper=src[start:end]
        js=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const els={};
const $=id=>{
 if(!els[id])els[id]={hidden:true,disabled:false,innerHTML:'',textContent:'',
    value:'9395',href:'',download:'',addEventListener(){}};
 return els[id];
};
const ctx={
 $,document:{querySelectorAll:()=>[]},esc:s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
              .replace(/"/g,'&quot;').replace(/'/g,'&#39;'),
 Date,URLSearchParams,Number,encodeURIComponent,
 fetch:async(url)=>({
   ok:true,headers:{get:()=> 'application/json'},
   json:async()=>({laser:{part:'9395',title:'Bearing Kit',tool_type:'wheel bearing'},
    results:[{brand:'BGS Technic',title:'<script>alert("bad")</script>',
     part_number:'BGS-2345',match_status:'Similar tool',
     match_evidence:'Verify it',seller:'Toolden',price_gbp:'187.99',
     vat_basis:'unknown',url:'https://www.toolden.co.uk/test',
     price_source:'Retailer JSON-LD product offer'}],
     providers:['Public product-page search'],
     checked_at_utc:'2026-11-19T09:00:00Z',warnings:[]})}),
 readApiJson:async r=>r.json()
};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
(async()=>{
 $('part').value='4832';
 $('competitorPart').value='9395';
 await ctx.findCompetitors(false);
 assert.equal($('part').value,'4832');
 assert.equal(els.competitorPanel.hidden,false);
 assert.equal(els.competitorExport.hidden,false);
 assert.match(els.competitorResults.innerHTML,/BGS Technic/);
 assert.match(els.competitorResults.innerHTML,/&lt;script>/);
 assert.doesNotMatch(els.competitorResults.innerHTML,/<script>/);
 assert.match(els.competitorResults.innerHTML,/£187.99/);
 assert.match(els.competitorResults.innerHTML,/VAT unconfirmed/);
 assert.match(els.competitorResults.innerHTML,/View source/);
 assert.match(els.competitorExport.href,/\/api\/competitors\/9395\/export.csv/);
 assert.equal(els.competitorBtn.disabled,false);
 console.log('Competitor comparison interactive UI and price provenance passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
""".replace("SOURCE",repr(helper))
        p=subprocess.run(["node","-e",js],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr)


if __name__=="__main__":
    unittest.main()
