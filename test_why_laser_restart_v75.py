"""V75: sales sheets survive Render Free's process-local cache disappearing.

The initial competitor response contains an immutable, source-linked comparison
and actual PDF bytes for the browser to keep. Restarting/killing the worker
cannot invalidate that already downloaded review-labelled document.
"""
from __future__ import annotations

import base64
import io
import time
import unittest
from unittest.mock import patch

import fitz

import app as studio
from test_competitor_4832_v74 import LASER_4832, CompetitorBrakeBleederV74Tests


class RestartSafeWhyLaserV75Tests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()
        self.fixture=CompetitorBrakeBleederV74Tests()
        self.comparison,_=self.fixture.report()

    def tearDown(self):
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()

    def fetch(self, part='4832'):
        product={**LASER_4832, 'part': part}
        comparison={**self.comparison,'laser':{**self.comparison['laser'],'part':part}}
        with patch.object(studio,'lookup',return_value=(product,None)) as lookup,\
             patch.object(studio,'research_competitors',return_value=comparison) as research,\
             patch.object(studio,'can_start_heavy',return_value=True):
            result=self.client.get('/api/competitors/'+part)
            self.assertEqual(result.status_code,200,result.get_data(as_text=True)[:300])
            lookup.assert_called_once()
            research.assert_called_once()
            return result.get_json()

    def test_original_research_response_includes_complete_pdf_and_evidence(self):
        answer=self.fetch()
        pack=answer['why_laser_pack']
        self.assertEqual(pack['sheet']['part'],'4832')
        self.assertEqual(len(pack['sheet']['competitors']),4)
        self.assertFalse(pack['sheet']['public_claim_approved'])
        self.assertTrue(pack['review_required'])
        self.assertEqual(pack['prepared_from'],
                         'same-source-checked-competitor-research')
        pdf=base64.b64decode(pack['pdf_base64'],validate=True)
        self.assertTrue(pdf.startswith(b'%PDF-'))
        document=fitz.open(stream=pdf,filetype='pdf')
        text=' '.join(p.get_text() for p in document)
        for name in ('Sealey','Draper','Hilka','NOT APPROVED'):
            self.assertIn(name,text)
        self.assertLess(len(pdf),900_000)

    def test_report_and_pdf_remain_valid_after_server_memory_is_lost(self):
        answer=self.fetch()
        verified_pack=answer['why_laser_pack']
        with studio.COMPETITOR_REPORT_LOCK:
            studio.COMPETITOR_REPORT_CACHE.clear()
        self.assertEqual(
            self.client.get('/api/competitors/4832/why-laser').status_code,404)
        # The old feature failed HERE. The browser now already has both pieces.
        self.assertEqual(verified_pack['sheet']['part'],'4832')
        pdf=base64.b64decode(verified_pack['pdf_base64'],validate=True)
        self.assertEqual(pdf[:5],b'%PDF-')
        self.assertIn('4832',fitz.open(stream=pdf,filetype='pdf')[0].get_text())

    def test_subsequent_cached_result_includes_evidence_pack(self):
        self.fetch()
        cached=self.client.get('/api/competitors/4832')
        self.assertEqual(cached.status_code,200)
        payload=cached.get_json()
        self.assertTrue(payload['cached'])
        self.assertEqual(payload['why_laser_pack']['sheet']['part'],'4832')
        self.assertTrue(payload['why_laser_pack']['pdf_base64'])

    def test_one_part_never_uses_another_parts_pdf(self):
        first=self.fetch()
        second=self.fetch('4833')
        self.assertEqual(first['why_laser_pack']['sheet']['part'],'4832')
        self.assertEqual(second['why_laser_pack']['sheet']['part'],'4833')
        one=base64.b64decode(first['why_laser_pack']['pdf_base64'])
        two=base64.b64decode(second['why_laser_pack']['pdf_base64'])
        self.assertNotEqual(one,two)
        self.assertIn('4833',fitz.open(stream=two,filetype='pdf')[0].get_text())

    def test_failed_pdf_generation_does_not_erase_approved_comparison(self):
        with patch.object(studio,'render_why_choose_laser_pdf',
                          side_effect=RuntimeError('PDF encoder broken')):
            report=self.fetch()
        self.assertEqual(report['count'],4)
        self.assertEqual(len(report['why_laser_pack']['sheet']['competitors']),4)
        self.assertIsNone(report['why_laser_pack']['pdf_base64'])

    def test_website_has_browser_side_pdf_blob_and_local_first_click(self):
        page=studio.V7_HOME_PAGE
        self.assertIn('whyLaserBrowserPack',page)
        self.assertIn('showWhyLaserEvidencePack(whyLaserBrowserPack,part)',page)
        self.assertIn('URL.createObjectURL(',page)
        self.assertIn("new Blob([bytes],{type:'application/pdf'})",page)
        self.assertIn('URL.revokeObjectURL(',page)


if __name__=='__main__':
    unittest.main()
