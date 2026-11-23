"""V72: verified, product-specific Why Choose Laser? dossier and A4 PDF.

All tests are offline. No AI or live retailer calls and no manufactured
competitive advantage or product photograph.
"""
from __future__ import annotations

import io
import json
import time
import unittest
from unittest.mock import patch

import fitz

import app as studio
import competitor_finder as cf
from why_choose_laser import (
    build_why_choose_laser, render_why_choose_laser_pdf, compact_photo,
)
from test_competitor_finder_v49 import LASER, PRODUCT_URL, TITLE


def product():
    return {
        **LASER,
        "features":[
            "Six threaded bars included.",
            "Use with a standard workshop press.",
            "For Mercedes-Benz Sprinter and Volkswagen Crafter.",
            "Fit and remove bearings without dismantling the whole hub.",
        ],
        "specs":{"Piece count":"6", "Working width":"75 mm"},
    }


def report():
    return {
        "laser":{"part":"9395","title":LASER["title"]},
        "results":[{
            "brand":"BGS Technic","title":TITLE,
            "part_number":"BGS-2345",
            "product_url":PRODUCT_URL,"url":PRODUCT_URL,
            "source_type":"retailer/manufacturer page",
            "match_status":"Likely equivalent — verify applications and specifications",
            "verified_specs":{"Number of Pieces":"4","Working width":"75 mm"},
        }],
        "checked_at_utc":"2026-11-23T11:00:00+00:00",
        "warnings":[],"providers":["Public product-page search"],
    }


class WhyChooseLaserV72Tests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()

    def tearDown(self):
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()

    def test_comparison_is_only_explicit_same_attribute_value(self):
        sheet=build_why_choose_laser(product(),report())
        self.assertEqual(sheet["part"],"9395")
        self.assertEqual(sheet["verified_differences"],1)
        competitor=sheet["competitors"][0]
        difference=competitor["published_differences"][0]
        self.assertEqual((difference["laser"],difference["competitor"]),("6","4"))
        self.assertEqual(difference["laser_source"],product()["source"])
        self.assertEqual(difference["competitor_source"],PRODUCT_URL)
        self.assertEqual(len(competitor["shared_published_specs"]),1)
        self.assertTrue(sheet["review_required"])
        self.assertFalse(sheet["public_claim_approved"])
        self.assertNotIn("superior",json.dumps(sheet).lower())

    def test_search_leads_and_shopping_prices_never_certify_superiority(self):
        data=report()
        data["results"][0]["source_type"]="unverified search-index title"
        data["results"].append({
            "brand":"Snap-on", "title":"Wheel Bearing Kit", "url":PRODUCT_URL,
            "product_url":PRODUCT_URL, "source_type":"shopping",
            "verified_specs":{"Piece count":"2"}, "price_gbp":"600",
        })
        sheet=build_why_choose_laser(product(),data)
        self.assertEqual(sheet["competitors_checked"],0)
        self.assertEqual(sheet["verified_differences"],0)
        self.assertIn("No defensible",sheet["status"])
        self.assertNotIn("£600",json.dumps(sheet))
        self.assertNotIn("Snap-on",json.dumps(sheet))
        self.assertTrue(sheet["strengths"])

    def test_unmatched_specs_do_not_create_fake_difference(self):
        data=report()
        data["results"][0]["verified_specs"]={"Warranty":"1 year"}
        sheet=build_why_choose_laser(product(),data)
        self.assertEqual(sheet["verified_differences"],0)
        self.assertIn("Direct technical advantage not established",
                      sheet["competitors"][0]["finding"])

    def test_mismatch_and_unapproved_official_source_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"different Laser product"):
            build_why_choose_laser(product(),{
                **report(),"laser":{"part":"9195"}})
        with self.assertRaisesRegex(ValueError,"Official Laser"):
            build_why_choose_laser({
                **product(),"source":"https://toolconnection.co.uk.evil.test/9395"},report())

    def test_product_json_ld_property_values_only_and_links_cited(self):
        parsed={
            "@context":"https://schema.org","@type":"Product",
            "name":TITLE,"brand":{"@type":"Brand","name":"BGS Technic"},
            "additionalProperty":[
                {"@type":"PropertyValue","name":"Piece count","value":4},
                {"@type":"PropertyValue","name":"Working width","value":"75","unitText":"mm"},
                {"@type":"PropertyValue","name":"Shipping price","value":"19.99"},
                {"@type":"PropertyValue","name":"URL","value":"https://unsafe.test"},
                {"@type":"PropertyValue","name":"Durability","value":None},
            ]
        }
        page=(
            "<html><head><title>"+TITLE+"</title>"+
            '<script type="application/ld+json">'+json.dumps(parsed)+
            '</script></head><body><h1>'+TITLE+"</h1></body></html>"
        ).encode()
        found=cf.parse_product_page(page,PRODUCT_URL,cf.tool_signature(product()))
        self.assertEqual(found["verified_specs"]["Piece count"],"4")
        self.assertEqual(found["verified_specs"]["Working width"],"75 mm")
        self.assertNotIn("Shipping price",found["verified_specs"])
        self.assertNotIn("URL",found["verified_specs"])

    def test_a4_pdf_uses_real_sources_not_made_up_superiority(self):
        sheet=build_why_choose_laser(product(),report())
        pdf=render_why_choose_laser_pdf(sheet)
        document=fitz.open(stream=pdf,filetype="pdf")
        self.assertGreaterEqual(document.page_count,1)
        self.assertEqual(round(document[0].rect.width),595)
        text="\n".join(page.get_text() for page in document)
        self.assertIn("WHY CHOOSE LASER?",text)
        self.assertIn("Six threaded bars included",text)
        self.assertIn("BGS Technic",text)
        self.assertIn("Published difference",text)
        self.assertIn("NOT APPROVED",text)
        self.assertNotIn("Laser is cheaper",text)
        links=[link.get("uri","") for page in document for link in page.get_links()]
        self.assertIn(product()["source"],links)
        self.assertIn(PRODUCT_URL,links)

    def test_no_verified_competitors_is_an_honest_laser_only_draft(self):
        source=report()
        source["results"]=[]
        sheet=build_why_choose_laser(product(),source)
        pdf=render_why_choose_laser_pdf(sheet)
        contents=" ".join(page.get_text() for page in fitz.open(stream=pdf,filetype="pdf"))
        self.assertIn("No accessible competitor product pages",contents)
        self.assertIn("not",sheet["caution"].lower())

    def test_reuse_cached_search_and_return_pdf_without_research_again(self):
        with patch.object(studio,"lookup",return_value=(product(),None)) as lookup,\
             patch.object(studio,"research_competitors",return_value=report()) as research:
            response=self.client.get("/api/competitors/9395")
            self.assertEqual(response.status_code,200,response.get_data(as_text=True))
            preview=self.client.get("/api/competitors/9395/why-laser")
            self.assertEqual(preview.status_code,200,preview.get_data(as_text=True))
            self.assertEqual(preview.json["part"],"9395")
            sheet=self.client.get("/api/competitors/9395/why-laser.pdf")
            self.assertEqual(sheet.status_code,200,sheet.get_data(as_text=True)[:150])
            self.assertTrue(sheet.data.startswith(b"%PDF-"))
            self.assertIn("application/pdf",sheet.content_type)
            self.assertIn("attachment",sheet.headers["Content-Disposition"])
            self.assertIn("no-store",sheet.headers["Cache-Control"])
            self.assertEqual(lookup.call_count,1)
            self.assertEqual(research.call_count,1)

    def test_cache_expiry_and_part_number_isolation(self):
        self.assertEqual(self.client.get(
            "/api/competitors/9395/why-laser").status_code,404)
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE["9395"]={
                "expires":time.time()-10,"report":report(),
                "official_product":product(),"official_photo_preview":None}
        self.assertEqual(self.client.get(
            "/api/competitors/9395/why-laser.pdf").status_code,404)
        self.assertEqual(self.client.get(
            "/api/competitors/9195/why-laser").status_code,404)

    def test_html_injection_is_escaped_in_pdf(self):
        data=product()
        data["features"]=['Includes 6 bars <script>alert(1)</script>']
        sheet=build_why_choose_laser(data,report())
        pdf=render_why_choose_laser_pdf(sheet)
        all_text=" ".join(p.get_text() for p in fitz.open(stream=pdf,filetype="pdf"))
        self.assertIn("Includes 6 bars",all_text)
        self.assertNotIn("PDF render failed",all_text)

    def test_compact_product_photo_accepts_real_png_and_rejects_invalid(self):
        from PIL import Image as PILImage
        original=PILImage.new("RGBA",(500,400),(100,120,160,255))
        out=io.BytesIO()
        original.save(out,format="PNG")
        smaller=compact_photo(out.getvalue())
        self.assertTrue(smaller.startswith(b"\xff\xd8"))
        self.assertLess(len(smaller),250000)
        self.assertIsNone(compact_photo(b"not an image"))

    def test_website_offers_sales_sheet_only_through_competitor_research(self):
        page=studio.V7_HOME_PAGE
        self.assertIn('id="whyLaserBtn"',page)
        self.assertIn('id="whyLaserPanel"',page)
        self.assertIn('id="whyLaserPdf"',page)
        self.assertIn("async function buildWhyLaserSheet()",page)
        self.assertIn("/why-laser.pdf",page)


if __name__=="__main__":
    unittest.main()
