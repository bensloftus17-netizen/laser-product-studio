"""V78: an ordinary product preview or competitor lookup cannot OOM Render
by downloading and decoding an entire 18-image manufacturer carousel.

Full multi-photo campaigns still request approved gallery images explicitly,
and each candidate is scored with the existing, unweakened QA.
"""
from __future__ import annotations
import io
import threading
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw

import app


def photo():
    im=Image.new("RGB",(840,760),"white")
    draw=ImageDraw.Draw(im)
    draw.ellipse((110,95,735,655),fill="#164B82")
    out=io.BytesIO()
    im.save(out,format="JPEG")
    return out.getvalue()

PART="9517"
UK="https://www.toolconnection.co.uk/products/workshop/9517-multi-blade-pneumatic-scraper-kit"
MASTER="https://www.lasertools.co.uk/items/XLarge/9517.jpg"
PRODUCT={
    "part":PART,"title":"Multi-Blade Pneumatic Scraper Kit",
    "description":"Air powered gasket scraper.",
    "features":["Five official scraper blades."],
    "specs":{"Blades":"5"},
    "image_candidates":[MASTER],
    "source":UK,
    "price":None,
}
DATA=photo()


class Reply:
    def __init__(self,url,body):
        self.url=url
        self.content=body


class LightweightLookupV78Tests(unittest.TestCase):
    def tearDown(self):
        app.CACHE.pop(PART,None)
        from official_photo_gallery import discard_gallery
        discard_gallery(PART)

    def make_request(self,*,collect_gallery=False):
        fetched=[]
        def get(url,session=None,content_types=None,timeout=None):
            fetched.append(url)
            if url==MASTER:
                return Reply(MASTER,DATA)
            if url==UK:
                return Reply(UK,b"<html><h1>Multi-Blade Pneumatic Scraper Kit</h1></html>")
            raise OSError("Source unavailable")
        with patch.object(app,"official_get",side_effect=get),\
             patch.object(app,"catalogue_url_for_part",return_value=UK),\
             patch.object(app,"parse_html",return_value=dict(PRODUCT)),\
             patch.object(app,"manufacturer_gallery_urls",
                          side_effect=AssertionError("full catalogue scan unexpectedly started")) as gallery,\
             patch.object(app,"preferred_manufacturer_photos",return_value=[MASTER]),\
             patch.object(app,"valid_image",return_value=True),\
             patch("asset_quality.manufacturer_image_rank",
                   return_value=(130,{"passed":True,"size":[840,760]})),\
             patch.object(app,"apply_official_taxonomy",side_effect=lambda p:p):
            item,image=app.lookup(PART,force=True,collect_gallery=collect_gallery)
        return item,image,fetched,gallery

    def test_competitor_and_hero_lookup_does_not_open_full_gallery(self):
        item,image,fetched,gallery=self.make_request()
        self.assertEqual(image,DATA)
        self.assertEqual(item["photo_source"],MASTER)
        self.assertEqual(item["photo_gallery_count"],0)
        self.assertFalse(item["gallery_complete"])
        gallery.assert_not_called()
        self.assertEqual(fetched.count(MASTER),1)

    def test_cached_lightweight_product_needs_full_gallery_upgrade(self):
        item,image,_,_=self.make_request()
        self.assertFalse(item["gallery_complete"])
        self.assertEqual(image,DATA)
        from official_photo_gallery import load_gallery
        self.assertEqual(load_gallery(PART),[])

    def test_manufacturer_qa_releases_decoded_buffers_after_a_photo(self):
        with patch.object(app,"_release_campaign_image_caches") as release:
            self.make_request()
        self.assertGreaterEqual(release.call_count,2)

    def test_lookup_is_serialised_across_parallel_http_threads(self):
        self.assertTrue(callable(app.lookup))
        self.assertTrue(hasattr(app.lookup,"__wrapped__"))
        self.assertTrue(isinstance(app.LOOKUP_SERIAL_LOCK,type(threading.RLock())))

    def test_build_campaign_requests_full_gallery_explicitly(self):
        from inspect import getsource
        source=getsource(app._assemble_campaign_bundle)
        self.assertIn("collect_gallery=True",source)
        self.assertIn("gallery_images=load_gallery(part)",source)


if __name__=="__main__":
    unittest.main()
