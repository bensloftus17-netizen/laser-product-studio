"""V74: real manufacturer alternatives for Laser 4832, not fabricated prices.

Tests deliberately simulate Bing RSS, UK Shopping and manufacturer servers
being unavailable. The verified official manufacturer catalogue references
must still give source-linked, dated product comparisons and a useful PDF.
"""
from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

import fitz

import competitor_finder as finder
from competitor_catalogue import catalogue_references
from test_competitor_finder_v49 import DummyResponse
from why_choose_laser import build_why_choose_laser, render_why_choose_laser_pdf

LASER_4832 = {
    "part": "4832",
    "title": "Manual Pressure Brake Bleeder 2L",
    "description": (
        "Manual brake bleeder designed for use with most master cylinder "
        "reservoirs with Euro Adaptor (reservoir neck 44mm)."
    ),
    "features": [
        "2L capacity tank.",
        "One way syphoning method.",
        "Operating pressure 10psi; maximum pressure rating 30psi.",
        "Quick connector and pressure release valve. Pressure gauge 0 - 70psi (0 - 5 bar).",
    ],
    "specs": {"Packaged Width (mm)":"192", "Packaged Height (mm)":"174"},
    "price": "£114.70 plus VAT",
    "source": ("https://www.toolconnection.co.uk/products/cars-vans/"
               "brakes/brake-bleeding/brake-bleeders-manual/"
               "4832-manual-pressure-brake-bleeder-2l"),
}
EXPECTED={
    "22495": "Draper",
    "12724211": "Hilka",
    "VS820": "Sealey",
    "29358": "Draper",
}


class NoKeyOrManufacturerSearch:
    def __init__(self):
        self.urls=[]
    def get(self,url,**kwargs):
        self.urls.append(url)
        return DummyResponse(status=503)
    def post(self,*args,**kwargs):
        raise AssertionError("No AI review required")


class ActualPageFixture(NoKeyOrManufacturerSearch):
    def get(self,url,**kwargs):
        self.urls.append(url)
        if url.endswith("/pump-action-brake-bleeder/"):
            content=(
                '<html><head><title>Draper Manual Pressure Brake Bleeder 2L 22495</title>'
                '</head><body><h1>Draper Manual Pressure Brake Bleeder 2L 22495</h1>'
                '<div>2L clean fluid capacity, a pressure gauge and quick release '
                'connector for manually pumping brakes.</div></body></html>'
            )
            return DummyResponse(body=content.encode())
        return DummyResponse(status=503)


class CompetitorBrakeBleederV74Tests(unittest.TestCase):
    def report(self,session=None,product=None):
        session=session or NoKeyOrManufacturerSearch()
        with patch.dict(os.environ,{"SERPAPI_KEY":"","GEMINI_API_KEY":""}):
            return finder.research_competitors(
                product or LASER_4832,session=session,enable_ai=False),session

    def test_category_recognises_source_tool(self):
        sig=finder.tool_signature(LASER_4832)
        self.assertEqual(sig["type"],"brake bleeder")
        self.assertEqual(sig["category_source"],"fixed-category-rule")
        self.assertEqual(len(catalogue_references(sig["type"])),4)
        self.assertTrue(all(finder.safe_url(x["url"])
                            for x in catalogue_references(sig["type"])))

    def test_zero_search_provider_access_still_returns_four_real_sources(self):
        report,session=self.report()
        self.assertEqual(report["count"],4,report)
        self.assertEqual(report["manufacturer_catalogue_references"],4)
        self.assertEqual(report["verified_product_pages"],0)
        got={x["part_number"]:x["brand"] for x in report["results"]}
        self.assertEqual(got,EXPECTED)
        self.assertTrue(all(
            x["source_type"]=="manufacturer catalogue reference" and
            x["source_checked_on"]=="2026-11-23" and
            x["price_gbp"] is None and x["image_url"] is None
            for x in report["results"]))
        self.assertEqual(len(session.urls),4)
        self.assertTrue(all(
            url in {r["url"] for r in catalogue_references("brake bleeder")}
            for url in session.urls))
        self.assertIn("manufacturer catalogue",str(report["warnings"]).lower())

    def test_source_sku_family_not_hardcoded_to_4832(self):
        second={**LASER_4832,"part":"9991",
                "title":"Manual Brake Bleeder 2 Litre"}
        report,_=self.report(product=second)
        self.assertEqual(report["laser"]["part"],"9991")
        self.assertGreaterEqual(report["count"],3)

    def test_unrelated_category_does_not_leak_brake_kit_comparisons(self):
        product={**LASER_4832,"part":"9365","title":"3 Piece Ratchet Set"}
        self.assertNotEqual(finder.tool_signature(product)["type"],"brake bleeder")
        self.assertEqual(catalogue_references(
            finder.tool_signature(product)["type"]),[])

    def test_live_manufacturer_listing_is_preferred_with_dated_specs(self):
        report,_=self.report(ActualPageFixture())
        draper=next(x for x in report["results"]
                    if x["part_number"]=="22495")
        self.assertEqual(draper["source_type"],"retailer/manufacturer page")
        self.assertEqual(draper["verified_specs"]["Fluid capacity"],"2 L")
        self.assertEqual(draper["source_checked_on"],"2026-11-23")
        self.assertEqual(report["verified_product_pages"],1)
        self.assertEqual(report["manufacturer_catalogue_references"],3)

    def test_dated_evidence_appears_in_why_choose_laser_sheet(self):
        report,_=self.report()
        sheet=build_why_choose_laser(LASER_4832,report)
        self.assertEqual(sheet["part"],"4832")
        self.assertEqual(len(sheet["competitors"]),4)
        brands=[(c["brand"],c["part_number"]) for c in sheet["competitors"]]
        self.assertIn(("Hilka","12724211"),brands)
        self.assertIn(("Draper","22495"),brands)
        self.assertIn(("Draper","29358"),brands)
        self.assertIn(("Sealey","VS820"),brands)
        self.assertTrue(sheet["verified_differences"]>=1)
        draper=next(c for c in sheet["competitors"]
                    if c["part_number"]=="22495")
        self.assertTrue(any(
            x["attribute"]=="Fluid capacity" and x["laser"]=="2 L"
            for x in draper["shared_published_specs"]))
        self.assertTrue(any("Manufacturer catalogue" in c["evidence_type"]
                            or c["evidence_type"].startswith("dated")
                            for c in sheet["competitors"]))
        self.assertIn("Dated manufacturer catalogue",sheet["caution"])

    def test_branded_source_linked_pdf_contains_verified_competitors(self):
        report,_=self.report()
        sheet=build_why_choose_laser(LASER_4832,report)
        pdf=render_why_choose_laser_pdf(sheet)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        document=fitz.open(stream=pdf,filetype="pdf")
        text="\n".join(page.get_text() for page in document)
        self.assertIn("Draper",text)
        self.assertIn("Hilka",text)
        self.assertIn("Sealey",text)
        self.assertIn("NOT APPROVED",text)
        all_links=[
            link.get("uri","") for page in document
            for link in page.get_links()]
        for product in catalogue_references("brake bleeder"):
            self.assertIn(product["url"],all_links)
        self.assertNotIn("Laser is superior",text)

    def test_no_pricing_or_safety_claims_in_fallback(self):
        report,_=self.report()
        for candidate in report["results"]:
            self.assertIsNone(candidate["price_gbp"])
            self.assertIsNone(candidate["image_url"])
            self.assertNotIn("proven equivalent",candidate["match_evidence"].lower())
        summary=build_why_choose_laser(LASER_4832,report)
        self.assertFalse(summary["public_claim_approved"])
        self.assertTrue(summary["review_required"])


if __name__=="__main__":
    unittest.main()
