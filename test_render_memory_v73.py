"""V73: free-512MiB memory protection without weakening artwork checks.

Offline functional tests cover progressively delivered PNGs, cleanup, cgroup
headroom, 429/503 protection during competing heavy jobs and PDF photo rescue.
"""
from __future__ import annotations

import io
import shutil
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import fitz
from PIL import Image

import app as studio
import memory_guard
from disk_campaign_store import StoredCampaign
from test_mobile_campaign_v47 import _png


class RenderMemoryProtectionV73Tests(unittest.TestCase):
    def setUp(self):
        self.client=studio.app.test_client()
        self.jobs=studio.CAMPAIGN_JOBS
        self.packs=studio.CAMPAIGN_PACKS
        self.slot=studio.CAMPAIGN_RENDER_SLOT
        studio.CAMPAIGN_JOBS={}
        studio.CAMPAIGN_PACKS={}
        studio.CAMPAIGN_RENDER_SLOT=threading.BoundedSemaphore(1)
        studio.COMPETITOR_REPORT_CACHE.clear()

    def tearDown(self):
        for job in studio.CAMPAIGN_JOBS.values():
            folder=job.get('preview_folder')
            if folder:
                shutil.rmtree(folder,ignore_errors=True)
        for item in studio.CAMPAIGN_PACKS.values():
            b=item.get('bundle')
            if isinstance(b,StoredCampaign):
                b.delete()
        studio.CAMPAIGN_JOBS=self.jobs
        studio.CAMPAIGN_PACKS=self.packs
        studio.CAMPAIGN_RENDER_SLOT=self.slot
        studio.COMPETITOR_REPORT_CACHE.clear()

    def begin(self):
        with patch.object(studio,"can_start_heavy",return_value=True),\
             patch("app.threading.Thread"):
            response=self.client.post('/api/campaign/start/6330',
                                      json={'distributor_brand':'none'})
        self.assertEqual(response.status_code,202,response.get_json())
        return response.json['job_id']

    def test_ready_previews_are_private_paths_not_duplicate_ram_bytes(self):
        job_id=self.begin()
        asset=_png()+b'M'*1_800_000
        studio._campaign_progress_update(
            job_id,'ready','poster_technical',asset,{"passed":True})
        state=studio.CAMPAIGN_JOBS[job_id]
        pointer=state['preview_images']['poster_technical']
        self.assertIsInstance(pointer,Path)
        self.assertTrue(pointer.exists())
        self.assertEqual(pointer.read_bytes(),asset)
        self.assertNotIsInstance(pointer,bytes)
        self.assertNotIn(asset,state.values())
        summary=self.client.get('/api/campaign/jobs/'+job_id)
        self.assertEqual(summary.status_code,200)
        self.assertNotIn("preview_images",summary.get_json())
        response=self.client.get('/api/campaign/job-assets/'+job_id+'/poster_technical')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data,asset)

    def test_failed_pack_keeps_approved_downloads_but_no_ram_copy(self):
        job_id=self.begin()
        correct=_png()
        def fail(part,body,progress=None):
            progress('planning')
            progress('ready','social_square',correct,{'passed':True})
            raise ValueError('One asset still failed the quality gate')
        with patch.object(studio,'_assemble_campaign_bundle',side_effect=fail):
            studio._run_campaign_job(job_id,'6330',{})
        progress=self.client.get('/api/campaign/jobs/'+job_id)
        self.assertEqual(progress.json['status'],'failed')
        self.assertEqual(self.client.get(
            '/api/campaign/job-assets/'+job_id+'/social_square').data,correct)
        self.assertIsInstance(studio.CAMPAIGN_JOBS[job_id]
                              ['preview_images']['social_square'],Path)

    def test_completed_job_drops_progress_files_and_uses_full_bundle(self):
        job_id=self.begin()
        folder=Path(studio.CAMPAIGN_JOBS[job_id]['preview_folder'])
        stream=io.BytesIO()
        with ZipFile(stream,'w') as zip:
            for key in studio.PROGRESS_ASSETS:
                zip.writestr(key+'.png',_png())
        bundle={'manifest':{
            'part':'6330',
            'images':[{'id':k,'path':k+'.png'} for k in studio.PROGRESS_ASSETS]},
            'images':{k:_png() for k in studio.PROGRESS_ASSETS},
            'archive':stream.getvalue()}
        def make(part,body,progress=None):
            progress('planning')
            for key in studio.PROGRESS_ASSETS:
                progress('ready',key,_png(),{'passed':True})
            return bundle
        with patch.object(studio,'_assemble_campaign_bundle',side_effect=make):
            studio._run_campaign_job(job_id,'6330',{})
        status=self.client.get('/api/campaign/jobs/'+job_id)
        self.assertEqual(status.json['status'],'ready')
        self.assertEqual(studio.CAMPAIGN_JOBS[job_id]['preview_images'],{})
        self.assertFalse(folder.exists())
        self.assertEqual(self.client.get(
            '/api/campaign/job-assets/'+job_id+'/poster_price').data,_png())
        self.assertEqual(self.client.get(
            '/api/campaign/download/'+status.json['token']).status_code,200)

    def test_stale_jobs_remove_their_private_temporary_files(self):
        old=self.begin()
        folder=Path(studio.CAMPAIGN_JOBS[old]['preview_folder'])
        studio.CAMPAIGN_JOBS[old]['expires']=time.time()-1
        studio.CAMPAIGN_RENDER_SLOT.release()   # Mocked worker never started
        new=self.begin()
        self.assertNotEqual(old,new)
        self.assertFalse(folder.exists())
        self.assertNotIn(old,studio.CAMPAIGN_JOBS)

    def test_risk_guard_denies_without_guessing_capacity(self):
        M=memory_guard.MIB
        with patch.object(memory_guard,'try_release_heap'):
            with patch.object(memory_guard,'current_memory',
                              return_value={'used_bytes':401*M,'limit_bytes':512*M}):
                self.assertFalse(memory_guard.can_start_heavy('campaign'))
                self.assertTrue(memory_guard.can_start_heavy('research'))
            with patch.object(memory_guard,'current_memory',
                              return_value={'used_bytes':300*M,'limit_bytes':512*M}):
                self.assertTrue(memory_guard.can_start_heavy('campaign'))
            with patch.object(memory_guard,'current_memory',
                              return_value={'used_bytes':None,'limit_bytes':None}):
                self.assertTrue(memory_guard.can_start_heavy('campaign'))

    def test_competitor_search_does_not_overlap_artwork(self):
        with patch.object(studio,'lookup') as lookup:
            with studio.CAMPAIGN_RENDER_SLOT:
                response=self.client.get('/api/competitors/9395')
                self.assertEqual(response.status_code,429)
                self.assertIn('Retry-After',response.headers)
        lookup.assert_not_called()

    def test_high_pressure_rejects_new_research_and_frees_both_slots(self):
        with patch.object(studio,'can_start_heavy',return_value=False),\
             patch.object(studio,'lookup') as lookup:
            response=self.client.get('/api/competitors/9395')
        self.assertEqual(response.status_code,503)
        lookup.assert_not_called()
        self.assertTrue(studio.CAMPAIGN_RENDER_SLOT.acquire(blocking=False))
        studio.CAMPAIGN_RENDER_SLOT.release()
        self.assertTrue(studio.COMPETITOR_REPORT_BUSY.acquire(blocking=False))
        studio.COMPETITOR_REPORT_BUSY.release()

    def test_high_pressure_stops_campaign_before_loading_giant_images(self):
        with patch.object(studio,'can_start_heavy',return_value=False),\
             patch.object(studio,'_assemble_campaign_bundle') as build:
            response=self.client.post('/api/campaign/6330',json={})
            self.assertEqual(response.status_code,503)
            started=self.client.post('/api/campaign/start/6330',json={})
            self.assertEqual(started.status_code,503)
        build.assert_not_called()
        self.assertTrue(studio.CAMPAIGN_RENDER_SLOT.acquire(blocking=False))
        studio.CAMPAIGN_RENDER_SLOT.release()

    def test_pdf_source_extract_uses_bounded_photo_pixels(self):
        photo=Image.new('RGB',(1700,1300),'#163D5D')
        buf=io.BytesIO()
        photo.save(buf,'PNG')
        pdf=fitz.open()
        page=pdf.new_page(width=600,height=810)
        page.insert_text((60,75),"9395")
        page.insert_text((60,100),"Front Wheel Bearing Kit")
        page.insert_image(fitz.Rect(42,135,480,505),stream=buf.getvalue())
        source=pdf.tobytes()
        pdf.close()
        product,photo_bytes=studio.parse_pis_pdf(
            source,'9395','https://www.lasertools.co.uk/pis/9395_PIS.pdf')
        self.assertEqual(product['part'],'9395')
        self.assertTrue(photo_bytes.startswith(b'\x89PNG'))
        with Image.open(io.BytesIO(photo_bytes)) as output:
            self.assertLessEqual(max(output.size),2100)


if __name__=='__main__':
    unittest.main()
