"""V63 regression: recover genuine large Laser photo instead of 0/9 abort.

Mocked manufacturer HTTP responses model an exact-SKU 4554 source with three
bad thumbnail URLs followed by a usable master, plus a PDF-only rescue.
No AI, manipulated product, external retailer image or fake photo is accepted.
"""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from PIL import Image,ImageDraw

import app
from source_image_selection import (
    collect_official_photo_options,best_manufacturer_photo,
    source_photo_audit,
)

PART="4554"
UK_URL="https://www.toolconnection.co.uk/products/general-hand-tools/cutting-drilling/thread-repair/taps-dies/4554-metric-tap-die-set-110pc"
HOST="https://www.lasertools.co.uk/items/XLarge/"
LOW_URLS=[
    f"https://www.lasertools.co.uk/items/large/{PART}_{i}.jpg"
    for i in range(3)
]
MASTER=HOST+f"{PART}.jpg"
PDF=f"https://www.lasertools.co.uk/pis/{PART}_PIS.pdf"


def photo(width,height):
    # Represents photo bytes supplied by a manufacturer. Tests NEVER use an
    # upscaled version of a rejected thumbnail.
    im=Image.new("RGB",(width,height),"white")
    d=ImageDraw.Draw(im)
    d.rectangle((width//8,height//9,width*7//8,height*7//8),
                fill="#126DB5")
    for i in range(11):
        x=width//6+i*max(1,width//17)
        y=height//5+i*max(1,height//28)
        d.ellipse((x-5,y-5,x+5,y+5),fill="#213345")
    out=io.BytesIO()
    im.save(out,"JPEG",quality=91)
    return out.getvalue()


THUMB=photo(320,320)
LARGE=photo(820,930)


class Response:
    def __init__(self,url,blob):
        self.url=url
        self.content=blob
        self.ok=True
        self.headers={"Content-Type":"application/pdf" if url.endswith(".pdf")
                      else "image/jpeg" if ".jpg" in url else "text/html"}
        self.status_code=200


def ranking(blob):
    size=Image.open(io.BytesIO(blob)).size
    good=min(size)>=650 and size[0]*size[1]>=210000
    return (160 if good else 12),{
        "passed":good,"size":list(size),"edge_strength":55.0,
        "warnings":[],"issues":[] if good else
        ["Source product image is too small for professional poster artwork"],
    }


class SelectionV63Tests(unittest.TestCase):
    def test_fourth_verified_master_is_found_after_three_rejected_catalogue_images(self):
        urls=[*LOW_URLS,MASTER]
        visited=[]
        def fetch(url):
            visited.append(url)
            return Response(url,LARGE if url==MASTER else THUMB)
        results,checked=collect_official_photo_options(
            urls,fetch,lambda b:True,ranking,workers=2)
        self.assertEqual(len(checked),4)
        self.assertEqual(len(results),4)
        chosen=best_manufacturer_photo(results)
        self.assertEqual(chosen[2],MASTER)
        self.assertEqual(chosen[1],LARGE)
        report=source_photo_audit(results,checked,chosen)
        self.assertTrue(report["quality_passed"])
        self.assertEqual(report["dimensions"],[820,930])
        self.assertFalse(report["generated_or_upscaled"])

    def test_duplicate_and_broken_photo_urls_do_not_block_later_good_master(self):
        urls=[LOW_URLS[0],LOW_URLS[0],LOW_URLS[1],MASTER]
        def fetch(url):
            if url==LOW_URLS[1]:
                raise OSError("404 official master was removed")
            return Response(url,LARGE if url==MASTER else THUMB)
        results,checked=collect_official_photo_options(
            urls,fetch,lambda b:True,ranking,workers=2)
        self.assertEqual(len(checked),3)
        self.assertEqual(len(results),2)
        self.assertEqual(best_manufacturer_photo(results)[2],MASTER)

    def test_only_small_photos_stay_unapproved(self):
        results,checked=collect_official_photo_options(
            LOW_URLS,lambda url:Response(url,THUMB),
            lambda b:True,ranking,workers=2)
        result=best_manufacturer_photo(results)
        report=source_photo_audit(results,checked,result)
        self.assertFalse(report["quality_passed"])
        self.assertEqual(result[1],THUMB)
        self.assertEqual(report["dimensions"],[320,320])
        self.assertFalse(report["generated_or_upscaled"])

    def test_full_size_srcset_precedes_tiny_image(self):
        markup=(
            '<html><body><img src="/items/large/4554.jpg" '
            'srcset="/items/large/4554.jpg 320w, '
            '/items/XLarge/4554.jpg 1200w, '
            '/items/large/4554_at_angle.jpg 660w"></body></html>'
        ).encode()
        fake=lambda url,session=None,timeout=6:Response(url,markup)
        with patch.object(app,"official_get",side_effect=fake):
            sources=app.manufacturer_gallery_urls(PART)
        self.assertTrue(sources)
        self.assertEqual(sources[0],MASTER)
        self.assertEqual(len(sources),3)
        self.assertTrue(all("4554" in url for url in sources))

    def test_real_lookup_4554_keeps_genuine_best_master_without_pdf(self):
        attempts=[]
        def fetch(url,session=None,content_types=None,timeout=6):
            attempts.append(url)
            if url==UK_URL:
                return Response(url,b"<html><h1>Metric Tap and Die Set</h1></html>")
            if url in LOW_URLS:
                return Response(url,THUMB)
            if url==MASTER:
                return Response(url,LARGE)
            raise OSError("No manufacturer image at this exact URL")
        product={"part":PART,"title":"Metric Tap & Die Set 110pc",
                 "features":["110-piece metric tap and die set."],
                 "description":"Professional metric tap and die set.",
                 "specs":{"Pieces":"110"},
                 "price":None,"source":UK_URL,
                 "image_candidates":[]}
        with patch.object(app,"official_get",side_effect=fetch), \
             patch.object(app,"catalogue_url_for_part",return_value=UK_URL), \
             patch.object(app,"parse_html",return_value=product), \
             patch.object(app,"manufacturer_gallery_urls",
                          return_value=[*LOW_URLS,MASTER]), \
             patch.object(app,"preferred_manufacturer_photos",return_value=[]), \
             patch.object(app,"valid_image",return_value=True), \
             patch("asset_quality.manufacturer_image_rank",side_effect=ranking), \
             patch.object(app,"apply_official_taxonomy",side_effect=lambda p:p):
            result,blob=app.lookup(PART,force=True)
        app.CACHE.pop(PART,None)
        self.assertEqual(blob,LARGE)
        self.assertEqual(result["photo_source"],MASTER)
        self.assertTrue(result["photo_quality_selection"]["quality_passed"])
        self.assertEqual(result["photo_quality_selection"]["dimensions"],[820,930])
        self.assertGreaterEqual(result["photo_quality_selection"]["candidates_checked"],4)
        self.assertNotIn(PDF,attempts)

    def test_pdf_uses_authentic_embedded_photo_after_all_catalogue_images_fail(self):
        attempts=[]
        def fetch(url,session=None,content_types=None,timeout=6):
            attempts.append(url)
            if url==UK_URL:
                return Response(url,b"<html><h1>Metric Tap and Die Set</h1></html>")
            if url in LOW_URLS:
                return Response(url,THUMB)
            if url==PDF:
                return Response(url,b"%PDF-simulated")
            raise OSError("Other source unavailable")
        product={"part":PART,"title":"Metric Tap & Die Set 110pc",
                 "features":["110-piece metric tap and die set."],
                 "description":"Professional metric tap and die set.",
                 "specs":{"Pieces":"110"},
                 "price":None,"source":UK_URL,
                 "image_candidates":[]}
        with patch.object(app,"official_get",side_effect=fetch), \
             patch.object(app,"catalogue_url_for_part",return_value=UK_URL), \
             patch.object(app,"parse_html",return_value=product), \
             patch.object(app,"manufacturer_gallery_urls",
                          return_value=LOW_URLS), \
             patch.object(app,"preferred_manufacturer_photos",return_value=[]), \
             patch.object(app,"parse_pis_pdf",return_value=(product,LARGE)), \
             patch.object(app,"valid_image",return_value=True), \
             patch("asset_quality.manufacturer_image_rank",side_effect=ranking), \
             patch.object(app,"apply_official_taxonomy",side_effect=lambda p:p):
            result,blob=app.lookup(PART,force=True)
        app.CACHE.pop(PART,None)
        self.assertEqual(blob,LARGE)
        self.assertIn("#pdf-photo-embedded",result["photo_source"])
        self.assertTrue(result["photo_quality_selection"]["pdf_rescue_used"])
        self.assertTrue(result["photo_quality_selection"]["quality_passed"])

if __name__=="__main__":
    unittest.main()
