"""V51: all official Laser part numbers can enter competitor discovery.

Regression matrix spans very different tool families, unknown makers and
products without direct competitors or retailer prices. No model-generated
product facts, unverified equivalence or fabricated numbers.
"""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import requests
import app as studio
import competitor_finder as cf

# Representative official-style names spanning diverse tool classes.
# These are test INPUTS, not a claim that these names exactly match the
# current website page of any given Laser part number.
TEST_TITLES={
    "9395":"Front Wheel Bearing Kit for Mercedes Sprinter VW Crafter",
    "9195":"Portable Endoscope Camera with Swivel Lens",
    "9365":"3pc Ratchet Set - 72 Tooth",
    "9197":"Rechargeable LED Under Bonnet Light",
    "8324":"Suspension Split Hub Knuckle Spreader",
    "4554":"Injector Return Flow Test Kit",
    "5101":"Electric Tyre Inflation Compressor",
    "5102":"Battery Cable Crimping Pliers",
    "5103":"Brake Caliper Piston Windback Tool",
    "5104":"Digital Paint Thickness Gauge",
    "5105":"Engine Mount Support Beam",
    "5106":"Cooling System Pressure Tester",
    "5107":"Workshop Foam Kneeling Pad",
    "5108":"Fluid Extractor and Pump",
    "5109":"Replacement Hose with Fitting",
    "5110":"Sensor Calibration Target",
    "5111":"Oil Filter Housing Removal Cup",
}
OTHER_PRODUCT_URL="https://www.toolden.co.uk/products/merchant-original-caliper-windback"
OTHER_TITLE="IndependentPro Brake Caliper Piston Windback Set"
OTHER_META={
    "@context":"https://schema.org","@type":"Product",
    "name":OTHER_TITLE, "brand":{"name":"IndependentPro"},
    "sku":"IP-123456",
    "offers":{"@type":"Offer","priceCurrency":"GBP","price":"82.50"}
}
PAGE=(
    "<html><head><title>"+OTHER_TITLE+"</title>"
    '<script type="application/ld+json">'+json.dumps(OTHER_META)+
    '</script></head><body><h1>'+OTHER_TITLE+'</h1></body></html>'
).encode("utf-8")


class Response:
    def __init__(self, *, content=b"",data=None,status=200,content_type="text/html"):
        self.content=content
        self._data=data
        self.status_code=status
        self.headers={"content-type":content_type}
    def raise_for_status(self):
        if self.status_code!=200:
            raise requests.HTTPError("Upstream unavailable")
    def json(self):return self._data


class AnyProductSearch:
    def __init__(self,*,fail_search=False,missing_product_page=False):
        self.calls=[]
        self.fail_search=fail_search
        self.missing_product_page=missing_product_page
    def get(self,url,**kwargs):
        self.calls.append((url,kwargs))
        if url==cf.SECONDARY_SEARCH_HOST:
            return Response(status=503)
        if url==cf.SEARCH_HOST:
            if self.fail_search:raise requests.Timeout("Bing timed out")
            return Response(
                content=("<rss version='2.0'><channel><item>"
                         "<title>"+OTHER_TITLE+"</title>"
                         "<link>"+OTHER_PRODUCT_URL+"</link>"
                         "</item></channel></rss>").encode(),
                content_type="application/rss+xml")
        if url==OTHER_PRODUCT_URL:
            if self.missing_product_page:
                return Response(status=503)
            return Response(content=PAGE)
        raise AssertionError("Unexpected mock web URL: "+url)
    def post(self,*args,**kwargs):
        raise AssertionError("AI source was not required for conservative search")


class UniversalCompetitorTests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()
    def tearDown(self):
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()

    def test_8567_finds_insulated_hex_and_star_catalogue_alternatives(self):
        class Offline:
            def get(self,*args,**kwargs):
                raise requests.Timeout("Public source unavailable")
        product={"part":"8567","title":"VDE Extra Long Hex/Star Key Wrench 19pc"}
        result=cf.research_competitors(product,session=Offline(),shopping_key="",enable_ai=False)
        self.assertEqual({row["part_number"] for row in result["results"]},{"AK7177","AK7178"})
        self.assertTrue(all(row["source_type"]=="manufacturer catalogue reference"
                            for row in result["results"]))
        self.assertIsNone(cf.match_status(cf.tool_signature(product),"Extra Long Hex Key Set 9pc"))

    def test_9380_returns_catalogue_alternatives_when_public_sources_fail(self):
        product={"part":"9380","title":"Hub Nut Socket & Bit Master Set for German Vehicles - 50th Anniversary"}
        class Offline:
            def get(self,*args,**kwargs):
                raise requests.Timeout("Public source unavailable")
        result=cf.research_competitors(product,session=Offline(),shopping_key="",enable_ai=False)
        self.assertEqual(result["laser"]["tool_type"],"hub nut socket set")
        self.assertEqual({row["brand"] for row in result["results"]},{"Sealey","Bergen"})
        self.assertTrue(all(row["price_gbp"] is None for row in result["results"]))
        signature=cf.tool_signature(product)
        self.assertIsNone(cf.match_status(signature,"Universal Impact Socket Set 10pc"))
        self.assertIsNone(cf.match_status(signature,"32mm Axle Nut Socket"))

    def test_wrapped_search_links_are_unwrapped_without_following_redirects(self):
        import base64
        from urllib.parse import quote
        payload=base64.urlsafe_b64encode(OTHER_PRODUCT_URL.encode()).decode().rstrip("=")
        bing="https://www.bing.com/ck/a?u=a1"+payload
        duck="//duckduckgo.com/l/?uddg="+quote(OTHER_PRODUCT_URL,safe="")
        self.assertEqual(cf._search_result_url(bing),OTHER_PRODUCT_URL)
        self.assertEqual(cf._search_result_url(duck),OTHER_PRODUCT_URL)
        self.assertEqual(cf._search_result_url("//duckduckgo.com/l/?uddg="+
            quote("http://127.0.0.1/",safe="")),"")

    def test_generic_type_uses_second_index_when_primary_candidates_are_unrelated(self):
        from urllib.parse import quote
        signature=cf.tool_signature({"title":"Grease Pressure Adaptor"})
        target="https://www.toolden.co.uk/products/grease-pressure-adaptor"
        class Search:
            def get(self,url,**kwargs):
                if url==cf.SEARCH_HOST:
                    return Response(content=b"<rss><channel><item><title>Paint Brush</title><link>https://www.toolden.co.uk/products/paint-brush</link></item></channel></rss>")
                if url=="https://html.duckduckgo.com/html/":
                    return Response(content=('<a class="result__a" href="//duckduckgo.com/l/?uddg='+
                        quote(target,safe="")+'">Workshop Grease Pressure Adaptor</a>').encode())
                self.assertion(url)
            @staticmethod
            def assertion(url):
                raise requests.Timeout(url)
        rows,_=cf.keyless_discovery(signature,Search())
        self.assertEqual([row["product_url"] for row in rows],[target])
        self.assertEqual(rows[0]["source_type"],"unverified search-index title")

    def test_every_official_style_product_has_a_safe_search_signature(self):
        for part,title in TEST_TITLES.items():
            with self.subTest(part=part):
                product={"part":part,"title":title,
                         "description":"Tools for workshop maintenance",
                         "features":[]}
                sig=cf.tool_signature(product)
                self.assertTrue(sig["type"],sig)
                self.assertTrue(sig["type_terms"],sig)
                self.assertEqual(sig["title"],title)
                self.assertIn(sig["category_source"],{
                    "fixed-category-rule","verified-alias-rule",
                    "official-title-derived"})
                q=cf.search_queries(sig)
                self.assertGreaterEqual(len(q),2)
                self.assertTrue(all(8<len(x)<150 for x in q),q)

    def test_unknown_tool_type_does_not_return_unsupported_http_422(self):
        for part in ("5103","5104","5105","5107","5110","5111"):
            title=TEST_TITLES[part]
            product={"part":part,"title":title,"description":title}
            with patch.object(studio,"lookup",return_value=(product,b"official-photo")),\
                 patch.object(studio,"research_competitors",return_value={
                     "laser":{"part":part,"title":title,
                              "tool_type":cf.tool_signature(product)["type"],
                              "category_source":"official-title-derived"},
                     "count":0,"results":[],"providers":[],
                     "warnings":["No verified alternative was found"],
                     "checked_at_utc":"2026-11-19T10:00:00Z"}):
                response=self.client.get("/api/competitors/"+part+"?refresh=1")
            self.assertEqual(response.status_code,200,
                (part,response.get_json()))
            self.assertEqual(response.get_json()["results"],[])

    def test_open_type_matching_conservative_and_accessories_excluded(self):
        sig=cf.tool_signature({"title":"Brake Caliper Piston Windback Tool"})
        self.assertIn(sig["category_source"],(
            "official-title-derived","fixed-category-rule"))
        true=cf.match_status(sig,OTHER_TITLE)
        self.assertIsNotNone(true)
        self.assertTrue("verify" in true[0].lower() or
                        "compare specifications" in true[0].lower())
        for bad in (
            "Draper Brake Caliper Spare Cable Attachment",
            "Sealey Brake Caliper Piston Replacement Bracket",
            "IndependentPro Socket Set for Brake Service",
            "Laser Tools Digital LED Light",
            "Draper Caliper Piston Seal Repair Kit",
        ):
            self.assertIsNone(cf.match_status(sig,bad),bad)
        underhood=cf.tool_signature({
            "title":"Rechargeable LED Under Bonnet Light"})
        self.assertIn(underhood["category_source"],
                      ("official-title-derived","fixed-category-rule",
                       "verified-alias-rule"))
        self.assertEqual(underhood["type"],"under bonnet light")
        self.assertIsNotNone(cf.match_status(
            underhood,"Sealey Rechargeable LED Under Bonnet Light"))
        self.assertIsNone(cf.match_status(
            underhood,"Sealey Under Bonnet Battery Holding Bracket"))

    def test_unknown_manufacturer_from_structured_listing_is_not_excluded(self):
        sig=cf.tool_signature({"title":"Brake Caliper Piston Windback Tool"})
        row=cf.parse_product_page(PAGE,OTHER_PRODUCT_URL,sig)
        self.assertEqual(row["brand"],"IndependentPro")
        self.assertEqual(row["part_number"],"IP-123456")
        self.assertEqual(row["price_gbp"],"82.50")
        self.assertEqual(row["vat_basis"],"unknown")
        self.assertEqual(row["price_source"],"Retailer JSON-LD product offer")
        self.assertEqual(row["url"],OTHER_PRODUCT_URL)

    def test_verified_source_and_unknown_industry_are_reported_without_fake_prices(self):
        product={"part":"5103","title":"Brake Caliper Piston Windback Tool"}
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            report=cf.research_competitors(
                product,session=AnyProductSearch(),enable_ai=False)
        self.assertEqual(report["count"],1)
        self.assertEqual(report["results"][0]["brand"],"IndependentPro")
        self.assertEqual(report["results"][0]["price_gbp"],"82.50")
        self.assertIn(report["laser"]["category_source"],(
            "official-title-derived","fixed-category-rule"))
        self.assertTrue(
            any("title" in w.lower() for w in report["warnings"]) or
            report["laser"]["category_source"]=="fixed-category-rule")
        self.assertTrue(any(x in (
            report["results"][0]["match_status"].lower()+
            report["results"][0]["match_evidence"].lower())
            for x in ("verify","compare specifications","need checking")))

    def test_search_index_lead_has_no_fake_sku_or_price(self):
        product={"part":"5103","title":"Brake Caliper Piston Windback Tool"}
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            report=cf.research_competitors(
                product,session=AnyProductSearch(missing_product_page=True),
                enable_ai=False)
        self.assertEqual(report["count"],1)
        row=report["results"][0]
        self.assertIsNone(row["price_gbp"])
        self.assertIsNone(row["part_number"])
        self.assertEqual(row["source_type"],"unverified search-index title")
        self.assertIn("Search lead",row["match_status"])
        self.assertIn("could not be verified",row["match_evidence"])
        self.assertEqual(row["url"],OTHER_PRODUCT_URL)

    def test_no_merchant_results_is_honest_and_not_http_failure(self):
        product={"part":"5110","title":"Sensor Calibration Target"}
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            report=cf.research_competitors(
                product,session=AnyProductSearch(fail_search=True),
                enable_ai=False)
        self.assertEqual(report["count"],0)
        self.assertEqual(report["results"],[])
        self.assertTrue(any("No source-verified competitor" in x for x in report["warnings"]))
        self.assertTrue(any("unavailable" in x.lower() for x in report["warnings"]))

    def test_new_brand_does_not_overwrite_laser_exclusion(self):
        sig=cf.tool_signature({"title":"Brake Caliper Piston Windback Tool"})
        self.assertIsNone(cf._build_result(
            "Laser Tools Brake Caliper Piston Windback Tool",
            OTHER_PRODUCT_URL,sig,brand="Laser Tools",
            price="99.99",price_origin="Google Shopping listing"))
        self.assertIsNone(cf._build_result(
            "IndependentPro Socket Set 100pc",OTHER_PRODUCT_URL,sig,
            brand="IndependentPro",price="99.99",
            price_origin="Google Shopping listing"))

if __name__=="__main__":
    unittest.main()
