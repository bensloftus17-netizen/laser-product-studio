"""V76 visual-sales-sheet tests against uploaded reference's structural style.

No false price/fitment claims and no synthetic product pictures. All four
manual brake bleeder competitors get distinct visual A4 landscape pages.
"""
import io
import unittest

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
            self.assertIn("Key takeaway",text)
            self.assertIn("NOT APPROVED",text)
            self.assertIn("VIEW MANUFACTURER SOURCE",text)
            self.assertNotIn("£4,164.18",text)
            self.assertNotIn("Laser is superior",text)

    def test_blue_and_red_header_bands_are_visually_distinct(self):
        pdf=render_why_choose_laser_pdf(self.sheet)
        doc=fitz.open(stream=pdf,filetype="pdf")
        pix=doc[0].get_pixmap(matrix=fitz.Matrix(.8,.8),alpha=False)
        def pixel(x,y):
            offset=(int(y*.8)*pix.width+int(x*.8))*pix.n
            return pix.samples[offset:offset+3]
        # canvas origin bottom-left; pixmap origin top-left.
        laser=pixel(140,110) # header card top around 595-(278+223)=94
        rival=pixel(570,110)
        self.assertGreater(laser[2],laser[0],laser)
        self.assertGreater(rival[0],rival[2],rival)

    def test_laser_original_photo_can_be_embedded_without_reconstruction(self):
        image=PILImage.new("RGB",(800,550),(18,120,210))
        b=io.BytesIO();image.save(b,format="PNG")
        pdf=render_why_choose_laser_pdf(self.sheet,b.getvalue())
        document=fitz.open(stream=pdf,filetype="pdf")
        self.assertGreaterEqual(len(document[0].get_images(full=True)),1)
        self.assertIn("Laser Tools 4832",document[0].get_text())

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
                    self.assertIn(row["name"],allowed)
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
