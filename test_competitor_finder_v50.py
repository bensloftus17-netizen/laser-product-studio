"""V50: real inspection camera synonyms, Snap-on and GBP listing provenance."""
import io
import json
import os
import unittest
from unittest.mock import patch

import requests
import competitor_finder as cf
import app as studio


LASER_9195={
    "part":"9195",
    "title":'Portable Endoscope Camera - 5" Screen with 360° Swivel Lens',
    "description":"Professional inspection camera for automotive testing",
    "features":["5 inch screen", "3.9 mm swivelling 360 degree head"],
    "source":"https://www.toolconnection.co.uk/products/cars-vans/testing/inspection/inspection-cameras/9195-portable-endoscope-camera-5-screen-with-360-swivel-lens"
}
SNAP_URL=cf.INSPECTION_CAMERA_SEEDS[0]
SEALEY_URL=cf.INSPECTION_CAMERA_SEEDS[3]
DRAPER_URL=cf.INSPECTION_CAMERA_SEEDS[5]
EBAY_URL=cf.INSPECTION_CAMERA_SEEDS[6]
SNAP_TITLE="Snap-on BK7000 High-Definition Borescope with 5.5 mm Dual Imager"
SEALEY_TITLE='Sealey VS8118 Video Borescope 5.5mm Camera Dual Lens & 5" Screen'
DRAPER_TITLE="Draper Expert Rechargeable Pistol Grip Borescope 92578"


def page(title,body="",**details):
    meta=({"@context":"https://schema.org","@type":"Product",
           "name":title,**details} if details else {})
    ld=(f'<script type="application/ld+json">{json.dumps(meta)}</script>'
        if meta else "")
    return (f'<html lang="en"><head><title>{title}</title>{ld}</head>'
            f'<body><h1>{title}</h1>{body}</body></html>').encode("utf-8")


class FakeResponse:
    def __init__(self,content,content_type="text/html",status_code=200):
        self.content=content
        self.status_code=status_code
        self.headers={"content-type":content_type}
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError("fetch rejected")


class SearchSession:
    def __init__(self,fail_rss=False):
        self.urls=[]
        self.fail_rss=fail_rss
    def get(self,url,**kwargs):
        self.urls.append(url)
        if url==cf.SECONDARY_SEARCH_HOST:
            return FakeResponse(b"")
        if url==cf.SEARCH_HOST:
            if self.fail_rss:raise requests.Timeout("Search RSS unavailable")
            return FakeResponse(b'''<rss version="2.0"><channel><item>
             <title>Snap On BK5500 Visual Inspection Camera Snake Device Endoscope Bore Scope</title>
             <link>https://www.ebay.co.uk/itm/127057347158</link>
             </item></channel></rss>''',"application/rss+xml")
        pages={
            SNAP_URL:page(SNAP_TITLE),
            cf.INSPECTION_CAMERA_SEEDS[1]:page("Snap-on 5.5mm Dual Imaging Borescope BK7000"),
            cf.INSPECTION_CAMERA_SEEDS[2]:page(SEALEY_TITLE),
            SEALEY_URL:page(SEALEY_TITLE,
                '<div>Our Price £240.16 (inc VAT) £200.13 (ex VAT)</div>'+
                '<div>RRP £311.94</div>'),
            cf.INSPECTION_CAMERA_SEEDS[4]:page(DRAPER_TITLE,
                '<h2>In stock with retailer</h2>',
                sku="92578",brand={"name":"Draper"}),
            DRAPER_URL:page(DRAPER_TITLE,
                '<p>Guest Price £225.99</p><p>Was £239.99</p>'),
            EBAY_URL:page(
                "Snap On BK5500 Visual Inspection Camera Snake Device Endoscope Bore Scope",
                '<p>£119.79 or Best Offer</p><span>Condition: Used</span>')
        }
        if url in pages:return FakeResponse(pages[url])
        raise AssertionError("Unexpected request "+url)


class BorescopeCompetitorsTests(unittest.TestCase):
    def test_source_9195_is_inspection_camera_not_unsupported_type(self):
        sig=cf.tool_signature(LASER_9195)
        self.assertEqual(sig["type"],"inspection camera")
        self.assertEqual(sig["fitments"],[])
        aliases=(
            "Snap-on BK7000 HD Borescope with Dual Imager",
            "Sealey VS8118 Video Borescope Camera",
            "Draper Expert Boroscope Inspection Tool",
            "Snap-on BK5500 Visual Inspection Device",
            "Inspection Camera 5.5mm with Screen",
            "Portable Endoscope 3.9mm Inspection Device",
            "Snake Camera 1080P Inspection",
            "Professional Videoscope with 5 inch screen",
        )
        for name in aliases:
            with self.subTest(name=name):
                matched=cf.match_status(sig,name)
                self.assertIsNotNone(matched)
                self.assertIn("Comparable inspection camera",matched[0])
                self.assertIn("articulation",matched[1])
        for name in (
            "Sealey Torque Wrench 1/2in",
            "Draper Socket Set 4pc",
            "Snap-on Diagnosis Scanner OBD-II",
            "BGS 5 inch LED Workshop Lamp",
            "Camera Adaptor Case for BK7000",
        ):
            self.assertIsNone(cf.match_status(sig,name),name)

    def test_brand_and_manufacturer_urls_are_accepted(self):
        self.assertEqual(cf.detect_brand(SNAP_TITLE),"Snap-on")
        self.assertTrue(cf.safe_url(SNAP_URL))
        self.assertTrue(cf.safe_url("https://www.snapon.co.uk/news/borescope"))
        self.assertTrue(cf.safe_url(SEALEY_URL))
        self.assertTrue(cf.safe_url(DRAPER_URL))
        self.assertTrue(cf.safe_url(EBAY_URL))
        for url in ("https://snapon.com.evil.test/bk7000",
                    "http://shop.snapon.com/BK7000",
                    "https://127.0.0.1/latest",
                    "https://www.ebay.co.uk:444/itm/127057347158"):
            self.assertFalse(cf.safe_url(url))

    def test_search_queries_use_relevant_brands_and_synonyms(self):
        q=cf.search_queries(cf.tool_signature(LASER_9195))
        self.assertGreaterEqual(len(q),3)
        combined=" ".join(q).lower()
        self.assertIn("snap-on",combined)
        self.assertIn("borescope",combined)
        self.assertIn("sealey",combined)
        self.assertIn("draper",combined)
        self.assertTrue(all("bearing" not in item for item in q))

    def test_live_page_price_parsing_never_confuses_rrp_with_sale_price(self):
        sig=cf.tool_signature(LASER_9195)
        session=SearchSession()
        snap=cf._get_product_page(SNAP_URL,sig,session)
        self.assertEqual(snap["brand"],"Snap-on")
        self.assertEqual(snap["price_gbp"],None)
        sealey=cf._get_product_page(SEALEY_URL,sig,session)
        self.assertEqual(sealey["price_gbp"],"240.16")
        self.assertEqual(sealey["vat_basis"],"inc")
        self.assertEqual(sealey["price_source"],"Visible UK retailer product price")
        draper=cf._get_product_page(DRAPER_URL,sig,session)
        self.assertEqual(draper["price_gbp"],"225.99")
        self.assertEqual(draper["vat_basis"],"unknown")
        ebay=cf._get_product_page(EBAY_URL,sig,session)
        self.assertEqual(ebay["price_gbp"],"119.79")
        self.assertEqual(ebay["brand"],"Snap-on")
        self.assertEqual(ebay["listing_condition"],"Used")
        self.assertEqual(ebay["vat_basis"],"unknown")
        self.assertTrue(all(x["match_status"].startswith("Comparable inspection camera")
                            for x in [snap,sealey,draper,ebay]))

    def test_price_parser_disallows_unrelated_markup_and_guesses(self):
        sig=cf.tool_signature(LASER_9195)
        # No "Our Price" label; a historic RRP is NOT a current quote.
        sample=page(SEALEY_TITLE,'<div>RRP £311.94</div><div>Was £279</div>')
        parsed=cf.parse_product_page(sample,SEALEY_URL,sig)
        self.assertIsNone(parsed["price_gbp"])
        # Repeated generic random-pound headings cannot set a price.
        sample=page(SNAP_TITLE,'<div>£999.99</div><div>£7.99 delivery</div>')
        parsed=cf.parse_product_page(sample,SNAP_URL,sig)
        self.assertIsNone(parsed["price_gbp"])
        # Unrecognised product pages are never treated as a camera.
        self.assertIsNone(cf.parse_product_page(
            page("Draper 200pc Socket Set","<div>Guest Price £300</div>"),
            DRAPER_URL,sig))

    def test_when_rss_fails_verified_catalogue_still_has_snapon_and_priced_competitors(self):
        session=SearchSession(fail_rss=True)
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            report=cf.research_competitors(LASER_9195,session=session,enable_ai=False)
        self.assertEqual(report["laser"]["tool_type"],"inspection camera")
        self.assertGreaterEqual(report["count"],3)
        self.assertIn("Snap-on",{r["brand"] for r in report["results"]})
        self.assertIn("Sealey",{r["brand"] for r in report["results"]})
        self.assertIn("Draper",{r["brand"] for r in report["results"]})
        self.assertTrue(any(r["price_gbp"]=="240.16" and r["vat_basis"]=="inc"
                            for r in report["results"]))
        self.assertTrue(any(r["price_gbp"]=="225.99"
                            for r in report["results"]))
        self.assertTrue(any(r["listing_condition"]=="Used"
                            for r in report["results"]))
        self.assertTrue(any("unavailable" in w.lower() for w in report["warnings"]))
        self.assertIn(SNAP_URL,session.urls)
        self.assertIn(DRAPER_URL,session.urls)

    def test_uk_shopping_results_accept_snapon_endoscope_aliases(self):
        sig=cf.tool_signature(LASER_9195)
        data={"shopping_results":[
            {"title":SNAP_TITLE,"product_link":SNAP_URL,
             "brand":"Snap-on","extracted_price":420,"price":"£420",
             "condition":"new"},
            {"title":"Snap On BK5500 Borescope Inspection Device",
             "product_link":EBAY_URL,"brand":"Snap-on",
             "extracted_price":110,"price":"£110","condition":"used"},
            {"title":"BGS Diagnostic Scanner","product_link":"https://toolden.co.uk/scan",
             "brand":"BGS Technic","extracted_price":25,"price":"£25"}]}
        rows=cf._parse_shopping(data,sig)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["brand"],"Snap-on")
        self.assertEqual(rows[1]["listing_condition"],"Used")
        self.assertEqual(rows[0]["price_source"],"Google Shopping listing")

    def test_flask_9195_not_422_and_csv_preserves_condition(self):
        session=SearchSession(fail_rss=True)
        with patch.object(studio,"lookup",return_value=(LASER_9195,b"real-photo")),\
             patch.object(studio,"research_competitors",
                          side_effect=lambda p:cf.research_competitors(
                              p,session=session,enable_ai=False)):
            client=studio.app.test_client()
            response=client.get("/api/competitors/9195?refresh=1")
            self.assertEqual(response.status_code,200,response.get_json())
            data=response.get_json()
            self.assertTrue(any(r["brand"]=="Snap-on" for r in data["results"]))
            self.assertTrue(any(r["price_gbp"] for r in data["results"]))
            csv_response=client.get("/api/competitors/9195/export.csv")
            self.assertEqual(csv_response.status_code,200)
            self.assertIn(b"119.79",csv_response.data)
            self.assertIn(b"Used",csv_response.data)


if __name__=="__main__":
    unittest.main()
