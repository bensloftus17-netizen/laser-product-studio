"""V58: genuine product photographs, direct links and search coverage.

The product names in this test are representative test inputs. They are not
manufacturer-verified comparisons; mocked source pages simulate real markup.
"""
from __future__ import annotations
import json
import os
import unittest
from unittest.mock import patch

import requests
import competitor_finder as cf
import app as studio

CASES={
    "9395":(
        "Front Wheel Bearing Kit for Mercedes Sprinter VW Crafter",
        "BGS Technic Wheel Bearing Tool Kit for Sprinter Crafter",
    ),
    "9469":(
        "Open Spanner Torque Wrench Set 20-210Nm",
        "Draper Open End Torque Spanner Set",
    ),
    "9365":(
        "3pc Ratchet Set 72 Tooth",
        "Sealey Reversible Ratchet Set",
    ),
    "9197":(
        "Rechargeable LED Under Bonnet Light",
        "Sealey Engine Bay Work Lamp",
    ),
    "8324":(
        "Suspension Split Hub Knuckle Spreader",
        "KS Tools Strut Hub Splitter",
    ),
    "9372":(
        "50t Workshop Hydraulic Press",
        "Draper Workshop Hydraulic Press 50 Tonne",
    ),
    "4554":(
        "Injector Return Flow Test Kit",
        "Sealey Diesel Injector Leak-off Tester",
    ),
    "9195":(
        "Portable Endoscope Camera with Swivel Lens",
        "Snap-on Automotive Video Borescope Camera",
    ),
}
IMAGE="https://cdn11.bigcommerce.com/s-brand/images/products/2000/genuine-product.jpg"
URL_ROOT="https://www.toolden.co.uk/products/competitor-"
def product_url(part):
    return URL_ROOT+part

def page(title,url,photo=IMAGE):
    product={"@context":"https://schema.org","@type":"Product",
             "name":title,
             "brand":{"@type":"Brand","name":title.split(" ")[0]},
             "sku":"SOURCED-MODEL-123",
             "image":photo,
             "offers":{"@type":"Offer","price":"124.95","priceCurrency":"GBP"}}
    return ("<html><head><title>"+title+"</title>"+
            '<meta property="og:image" content="'+photo+'">'+
            '<script type="application/ld+json">'+json.dumps(product)+
            "</script></head><body><h1>"+title+"</h1></body></html>").encode()

class Response:
    def __init__(self,content=b"",status=200,ctype="text/html"):
        self.content=content
        self.status_code=status
        self.headers={"content-type":ctype}
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError("Not available")

class SearchFixture:
    def __init__(self,part,title):
        self.part=part
        self.title=title
        self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append(url)
        if url==cf.SEARCH_HOST:
            if kwargs.get("params",{}).get("format")!="rss":
                return Response(b"<html><body>Search unavailable</body></html>")
            xml=("<rss><channel><item><title>"+self.title+"</title><link>"+
                 product_url(self.part)+"</link></item></channel></rss>")
            return Response(xml.encode(),ctype="application/rss+xml")
        if url==product_url(self.part):
            return Response(page(self.title,url))
        return Response(status=404)

class RichCompetitorCoverageTests(unittest.TestCase):
    def test_images_are_tied_to_real_structured_product_pages(self):
        sig=cf.tool_signature({"title":CASES["9395"][0]})
        result=cf.parse_product_page(
            page(CASES["9395"][1],product_url("9395")),
            product_url("9395"),sig)
        self.assertEqual(result["image_url"],IMAGE)
        self.assertEqual(result["image_source"],"Product JSON-LD photo")
        self.assertEqual(result["product_url"],product_url("9395"))
        self.assertEqual(result["price_gbp"],"124.95")
        self.assertEqual(result["part_number"],"SOURCED-MODEL-123")
        self.assertIn("verify",result["match_status"].lower())

    def test_relative_original_page_hero_image_and_missing_image(self):
        sig=cf.tool_signature({"title":CASES["9365"][0]})
        url=product_url("9365")
        markup=("<html><head><title>"+CASES["9365"][1]+"</title>"+
            '<meta property="og:image" content="/media/product-ratchet.jpg">'+
            "</head><body><h1>"+CASES["9365"][1]+"</h1></body></html>")
        row=cf.parse_product_page(markup.encode(),url,sig)
        self.assertEqual(row["image_url"],
                         "https://www.toolden.co.uk/media/product-ratchet.jpg")
        self.assertEqual(row["image_source"],"Product page hero image")
        self.assertIsNone(cf.parse_product_page(
            markup.replace('content="/media/product-ratchet.jpg"',
                           'content="https://unsafe.example/image.jpg"').encode(),
            url,sig)["image_url"])

    def test_rejects_fake_or_dangerous_remote_image_links(self):
        page_url=product_url("9197")
        unsafe=(
            "http://www.toolden.co.uk/product.jpg",
            "data:image/png;base64,AA==",
            "javascript:alert(1)",
            "https://127.0.0.1/internal.jpg",
            "https://evil.example/image.jpg",
            "https://toolden.co.uk.evil.example/photo.png",
            "https://www.toolden.co.uk:8080/img.png",
            "https://www.toolden.co.uk/assets/company-logo.svg",
        )
        self.assertTrue(all(cf.safe_image_url(x,page_url) is None
                            for x in unsafe))
        self.assertEqual(cf.safe_image_url(IMAGE,page_url),IMAGE)

    def test_shopping_thumbnail_has_source_not_fake_image(self):
        sig=cf.tool_signature({"title":CASES["9197"][0]})
        thumbnails="https://encrypted-tbn0.gstatic.com/images?q=tbn:test"
        data={"shopping_results":[{
            "title":CASES["9197"][1],
            "link":product_url("9197"),
            "source":"Toolden UK",
            "thumbnail":thumbnails,
            "price":"£69.99","extracted_price":69.99,
        }]}
        found=cf._parse_shopping(data,sig)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["image_url"],thumbnails)
        self.assertEqual(found[0]["image_source"],
                         "Google Shopping product thumbnail")
        self.assertEqual(found[0]["price_gbp"],"69.99")

    def test_eight_different_part_numbers_discover_source_pages(self):
        for part,(laser,competitor) in CASES.items():
            with self.subTest(part=part):
                sig=cf.tool_signature({"title":laser})
                self.assertIsNotNone(cf.match_status(sig,competitor))
                fixture=SearchFixture(part,competitor)
                with patch.dict(os.environ,{"GEMINI_API_KEY":"",
                                           "SERPAPI_KEY":""}):
                    result=cf.research_competitors({
                        "part":part,"title":laser,"features":[],
                        "source":"https://www.toolconnection.co.uk/products/"
                                 +part},session=fixture,enable_ai=False)
                self.assertEqual(result["count"],1,result)
                self.assertEqual(result["images_found"],1,result)
                self.assertEqual(result["product_links_found"],1,result)
                row=result["results"][0]
                self.assertEqual(row["url"],product_url(part))
                self.assertEqual(row["image_url"],IMAGE)
                self.assertEqual(row["price_gbp"],"124.95")
                self.assertIn("verify",row["match_status"].lower()
                              +row["match_evidence"].lower())

    def test_bing_html_fallback_has_only_allowed_real_merchant_urls(self):
        html=(
            "<html><body><ol id='b_results'>"
            "<li class='b_algo'><h2><a href='"+product_url("9395")+"'>"+
            CASES["9395"][1]+"</a></h2></li>"
            "<li class='b_algo'><h2><a href='https://evil.example/tool'>"
            "Cheap unverified product</a></h2></li>"
            "</ol></body></html>").encode()
        found=cf._parse_search_html(html)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["url"],product_url("9395"))

    def test_one_result_keeps_sourced_photo_when_merged_with_other_provider(self):
        sig=cf.tool_signature({"title":CASES["9395"][0]})
        photo=cf._build_result(CASES["9395"][1],product_url("9395"),
            sig,brand="BGS Technic",image_url=IMAGE,
            image_origin="Product JSON-LD photo")
        quote=cf._build_result(CASES["9395"][1],product_url("9395"),
            sig,brand="BGS Technic",price="128.95",
            price_origin="Google Shopping listing")
        merged=cf._distinct([photo,quote])
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]["image_url"],IMAGE)
        self.assertEqual(merged[0]["price_gbp"],"128.95")

    def test_ui_displays_photos_and_explicit_product_page_link(self):
        page=studio.V7_HOME_PAGE
        self.assertIn("item.image_url",page)
        self.assertIn("competitor-photo-cell",page)
        self.assertIn("View competitor product",page)
        self.assertIn("Product photo from source",page)
        self.assertIn("noopener noreferrer",page)
        self.assertIn("esc(imageUrl)",page)
        self.assertIn("Source photo unavailable",page)
        self.assertIn("v58-competitor-photos",page)

if __name__=="__main__":
    unittest.main()
