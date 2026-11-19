"""V59: real 9197 lamp taxonomy, verified manufacturer links and correct hero."""
from __future__ import annotations
import json
import os
import unittest
from unittest.mock import patch
import requests

import app as studio
import competitor_finder as cf


TITLE="Under Bonnet Compact Work Lamp 10W COB Infrared"
URL_LED142="https://www.sealey.co.uk/rechargeable-flexible-under-bonnet-light-10w-cob-led-led142/"
URL_LED141="https://www.sealey.co.uk/under-bonnet-rechargeable-light-9w-smd-led-led141/"
PHOTO="https://www.sealey.co.uk/media/products/LED142.jpg"


class Response:
    def __init__(self,body=b"",status=200,ctype="text/html"):
        self.content=body
        self.status_code=status
        self.headers={"content-type":ctype}
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError("Upstream unavailable")


class LampSearch:
    def __init__(self,allow_official_page=False):
        self.allow_official_page=allow_official_page
        self.urls=[]
    def get(self,url,**kwargs):
        self.urls.append(url)
        if url==cf.SEARCH_HOST:
            if kwargs.get("params",{}).get("format")=="rss":
                return Response(b"<rss><channel></channel></rss>",
                                ctype="application/rss+xml")
            return Response(b"<html><ol id='b_results'></ol></html>")
        if self.allow_official_page and url==URL_LED142:
            source={
                "@context":"https://schema.org","@type":"Product",
                "name":"Sealey Rechargeable Flexible Under-Bonnet Light 10W COB LED LED142",
                "sku":"LED142","brand":{"@type":"Brand","name":"Sealey"},
                "image":PHOTO,
                "offers":{"@type":"Offer","priceCurrency":"GBP","price":"44.90"},
            }
            body=(
                "<html><head><title>"+source["name"]+"</title>"+
                '<script type="application/ld+json">'+json.dumps(source)+
                "</script></head><body><h1>"+source["name"]+"</h1></body></html>"
            )
            return Response(body.encode())
        # A blocked manufacturer website should never create fake image or
        # prices, yet previously researched official URLs remain usable leads.
        return Response(status=503)


class GenuineLamp9197Tests(unittest.TestCase):
    def test_exact_live_9197_product_title_is_under_bonnet_work_lamp(self):
        product={"part":"9197","title":TITLE,
                 "description":"500mm magnetic bar work lamp with infrared sensor."}
        sig=cf.tool_signature(product)
        self.assertEqual(sig["type"],"under bonnet light")
        self.assertEqual(sig["category_source"],"verified-alias-rule")
        self.assertNotEqual(sig["type"],"work lamp cob infrared")
        queries=cf.search_queries(sig)
        self.assertTrue(any("LED142" in q for q in queries))
        self.assertTrue(any("LED141" in q for q in queries))
        self.assertTrue(any("65391" in q for q in queries))
        for candidate in (
            "Sealey Rechargeable Flexible Under-Bonnet Light 10W COB LED LED142",
            "Sealey Under-Bonnet Rechargeable Light 9W SMD LED LED141",
            "Draper Expert 50 SMD LED Under Bonnet Rechargeable Inspection Lamp 65391",
        ):
            result=cf.match_status(sig,candidate)
            self.assertIsNotNone(result,candidate)
            self.assertNotIn("confirmed equivalent",result[0].lower())

    def test_alias_covers_hyphenated_underbonnet_names_but_not_unrelated_tools(self):
        for official in (
            "Rechargeable Under-Bonnet Inspection Lamp",
            "Underhood LED Engine Work Light",
            "Under bonnet Compact Work Lamp 10W COB Infrared",
        ):
            with self.subTest(official=official):
                sig=cf.tool_signature({"title":official})
                self.assertEqual(sig["type"],"under bonnet light")
        self.assertIsNone(cf.match_status(
            cf.tool_signature({"title":TITLE}),
            "Sealey Under Bonnet Light Battery Charger Kit"))
        self.assertEqual(cf.tool_signature({
            "title":"Portable Endoscope Camera with Swivel Lens"
        })["type"],"inspection camera")

    def test_official_catalogue_links_visible_if_search_server_blocked(self):
        fixture=LampSearch()
        product={"part":"9197","title":TITLE}
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            result=cf.research_competitors(
                product,session=fixture,enable_ai=False)
        self.assertEqual(result["laser"]["tool_type"],"under bonnet light")
        self.assertGreaterEqual(result["count"],3,result)
        self.assertEqual(result["verified_product_pages"],0)
        self.assertEqual(result["images_found"],0)
        self.assertEqual(result["search_only_leads"],result["count"])
        urls={r["url"] for r in result["results"]}
        self.assertIn(URL_LED142,urls)
        self.assertIn(URL_LED141,urls)
        for row in result["results"]:
            self.assertIsNone(row["price_gbp"])
            self.assertIsNone(row["image_url"])
            self.assertIsNone(row["part_number"])
            self.assertEqual(row["product_url"],row["url"])
            self.assertIn("verify",row["match_status"].lower())
            self.assertEqual(row["source_type"],"unverified search-index title")
            self.assertTrue(cf.safe_url(row["url"]))

    def test_verified_live_sealey_page_produces_real_image_price_and_sku(self):
        fixture=LampSearch(allow_official_page=True)
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            result=cf.research_competitors(
                {"part":"9197","title":TITLE},session=fixture,enable_ai=False)
        official=[row for row in result["results"] if row["url"]==URL_LED142]
        self.assertEqual(len(official),1)
        row=official[0]
        self.assertEqual(row["part_number"],"LED142")
        self.assertEqual(row["image_url"],PHOTO)
        self.assertEqual(row["image_source"],"Product JSON-LD photo")
        self.assertEqual(row["price_gbp"],"44.90")
        self.assertEqual(row["price_source"],"Retailer JSON-LD product offer")
        self.assertEqual(row["source_type"],"retailer/manufacturer page")
        self.assertGreaterEqual(result["verified_product_pages"],1)
        self.assertGreaterEqual(result["images_found"],1)

    def test_homepage_photo_tracks_part_input_and_search(self):
        page=studio.V7_HOME_PAGE
        self.assertIn("function showOfficialHero(part)",page)
        self.assertIn("showOfficialHero(selected)",page)
        self.assertIn("showOfficialHero(part);",page)
        self.assertIn("photo.src='/api/photo/'+encodeURIComponent(clean)",page)
        self.assertIn("onload=\"this.hidden=false\"",page)
        self.assertIn("V59 competitor classification",page)


if __name__=="__main__":
    unittest.main()
