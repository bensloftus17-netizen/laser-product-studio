"""V76 visual-sales-sheet tests against uploaded reference's structural style.

No false price/fitment claims and no synthetic product pictures. All four
manual brake bleeder competitors get distinct visual A4 landscape pages.
"""
import io
import unittest
from unittest.mock import patch

import fitz
from PIL import Image as PILImage

import app as studio
from test_competitor_4832_v74 import LASER_4832, CompetitorBrakeBleederV74Tests
from why_choose_laser import build_why_choose_laser,render_why_choose_laser_pdf
from why_laser_comparison_poster import _takeaway, _comparison_rows, PAGESIZE


class VisualComparisonV76Tests(unittest.TestCase):
    def setUp(self):
        self.report,_=CompetitorBrakeBleederV74Tests().report()
        self.sheet=build_why_choose_laser(LASER_4832,self.report)

    def test_one_visual_page_per_comparable_manufacturer_product(self):
        output=render_why_choose_laser_pdf(self.sheet)
        doc=fitz.open(stream=output,filetype="pdf")
        self.assertEqual(doc.page_count,4)
        for page in doc:
            self.assertEqual(round(page.rect.width),842)
            self.assertEqual(round(page.rect.height),595)
            text=page.get_text()
            self.assertIn("Laser Tools 4832 vs",text)
            self.assertIn("COMPARISON",text)
            self.assertIn("Why choose Laser?",text)
            self.assertIn("NOT APPROVED",text)
            self.assertIn("VIEW MANUFACTURER SOURCE",text)
            self.assertNotIn("£4,164.18",text)
            self.assertNotIn("Laser is superior",text)

    def test_blue_and_red_header_bands_are_visually_distinct(self):
        pdf=render_why_choose_laser_pdf(self.sheet)
        doc=fitz.open(stream=pdf,filetype="pdf")
        fills=[item["fill"] for item in doc[0].get_drawings()
               if item.get("fill") and len(item["fill"])>=3]
        # Inspect the actual PDF vector fills, not unreliable raster
        # coordinates that can land on the white lettering.
        self.assertTrue(any(v[2]>v[0]*1.5 and v[2]>v[1]*1.1
                            for v in fills),fills)
        self.assertTrue(any(v[0]>v[2]*1.7 and v[0]>v[1]*1.5
                            for v in fills),fills)
        self.assertTrue(any(v[0]>.9 and v[1]>.55 and v[2]<.3
                            for v in fills),fills)

    def test_laser_original_photo_can_be_embedded_without_reconstruction(self):
        image=PILImage.new("RGB",(800,550),(18,120,210))
        b=io.BytesIO();image.save(b,format="PNG")
        pdf=render_why_choose_laser_pdf(self.sheet,b.getvalue())
        document=fitz.open(stream=pdf,filetype="pdf")
        self.assertGreaterEqual(len(document[0].get_images(full=True)),1)
        self.assertIn("Laser Tools 4832",document[0].get_text())

    def test_verified_competitor_photo_can_appear_in_pdf_without_ai_redraw(self):
        original=PILImage.new("RGB",(450,340),(155,82,53))
        rival_photo=PILImage.new("RGB",(410,310),(60,110,155))
        out=io.BytesIO()
        rival_out=io.BytesIO()
        original.save(out,format="JPEG")
        rival_photo.save(rival_out,format="JPEG")
        revised={**self.sheet,"competitors":[{
            **self.sheet["competitors"][0],
            "image_url":"https://www.drapertools.com/images/22495.jpg",
        }]}
        from why_laser_comparison_poster import _genuine_rival_photo
        with patch("why_laser_comparison_poster._genuine_rival_photo",
                   return_value=rival_out.getvalue()) as fetch:
            pdf=render_why_choose_laser_pdf(revised,out.getvalue())
        fetch.assert_called_once()
        page=fitz.open(stream=pdf,filetype="pdf")[0]
        self.assertGreaterEqual(len(page.get_images(full=True)),2)

    def test_unsafe_photo_urls_are_not_fetched(self):
        from why_laser_comparison_poster import _genuine_rival_photo
        with patch("why_laser_comparison_poster.requests.get") as request:
            result=_genuine_rival_photo({
                "url":"https://www.drapertools.com/product/22495/",
                "image_url":"https://example.org/unverified-lookalike.jpg"})
            self.assertIsNone(result)
            request.assert_not_called()

    def test_every_rival_has_the_source_url_as_a_clickable_pdf_link(self):
        document=fitz.open(stream=render_why_choose_laser_pdf(self.sheet),filetype="pdf")
        all_links=[link.get("uri","") for page in document
                   for link in page.get_links()]
        self.assertIn(self.sheet["official_source"],all_links)
        for competitor in self.sheet["competitors"]:
            self.assertIn(competitor["url"],all_links)

    def test_table_only_contains_documented_specifications(self):
        for rival in self.sheet["competitors"]:
            rows=_comparison_rows(rival)
            allowed={str(x["attribute"]) for key in (
                "published_differences","shared_published_specs")
                for x in rival[key]}
            for row in rows:
                if allowed:
                    self.assertIn(row["name"],allowed | {"Manufacturer RRP / list price"})
                    self.assertIn("laser",row)
                    self.assertIn("rival",row)
            conclusion=_takeaway(self.sheet,rival)
            self.assertFalse("Laser is cheaper" in conclusion)
            self.assertFalse("proven superior" in conclusion)

    def test_missing_competitors_still_produces_honest_full_visual_sheet(self):
        sheet=build_why_choose_laser(LASER_4832,{
            **self.report,"results":[]})
        pdf=render_why_choose_laser_pdf(sheet)
        doc=fitz.open(stream=pdf,filetype="pdf")
        self.assertEqual(doc.page_count,1)
        text=doc[0].get_text()
        self.assertIn("No accessible competitor product pages",text)
        self.assertIn("NOT APPROVED",text)

    def test_html_screen_uses_own_comparison_pages_and_source_images(self):
        page=studio.V7_HOME_PAGE
        self.assertIn("why-compare-dual",page)
        self.assertIn("why-compare-table",page)
        self.assertIn("why-compare-takeaway",page)
        self.assertIn("whyLaserClose",page)
        self.assertIn("whyLaserBrowserPack.photo_base64",page)
        self.assertIn("r.image_url",page)
        self.assertIn("NOT APPROVED FOR CUSTOMER DISTRIBUTION",page)


if __name__=="__main__":
    unittest.main()
