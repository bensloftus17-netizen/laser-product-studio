"""V77: genuine multi-photo Laser gallery, dedupe, disk cache and role routing.

No external requests. Every sample image represents original manufacturer
bytes in the test fixtures; the pipeline may choose but never redraw a tool.
"""
import hashlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

from PIL import Image,ImageDraw

import app
import campaign_hub
from official_photo_gallery import (
    gallery_urls_from_html,distinct_gallery,store_gallery,load_gallery,
    discard_gallery,_signature,
)
from source_image_selection import collect_official_photo_options


BASE="https://www.toolconnection.co.uk/products/cars-vans/9395-wheel-bearing-kit"
SKU="9395"


def photo(which,size=(850,750)):
    im=Image.new("RGB",size,"white")
    d=ImageDraw.Draw(im)
    if which==0:
        d.ellipse((100,90,760,680),fill="#173E65")
        d.ellipse((275,245,575,535),fill="white")
    elif which==1:
        d.rectangle((120,190,715,545),fill="#123B66")
        d.ellipse((245,170,580,610),fill="#AABBC9")
    elif which==2:
        d.polygon(((80,500),(440,80),(780,480),(600,660)),fill="#175B8A")
        d.rectangle((230,240,670,590),outline="#152736",width=25)
    else:
        d.rounded_rectangle((110,105,760,620),radius=70,fill="#1D4F75")
        d.line((160,220,730,560),fill="#F5B42A",width=50)
    result=io.BytesIO()
    im.save(result,format="JPEG",quality=89)
    return result.getvalue()


def source(url,blob,score=130):
    return (score,blob,url,{"passed":True,"size":[850,750],
                             "issues":[],"warnings":[]})


class Response:
    def __init__(self,url,body):
        self.url=url
        self.content=body


class GalleryV77Tests(unittest.TestCase):
    def tearDown(self):
        discard_gallery(SKU)

    def test_gathers_main_jsonld_carousel_srcset_lazy_and_alt_views(self):
        original=(
            '<script type="application/ld+json">'+json.dumps({
                "@type":"Product","sku":SKU,
                "image":[
                    "https://www.lasertools.co.uk/items/XLarge/9395.jpg",
                    "https://www.toolconnection.co.uk/media/opaque-hash-A.webp",
                ]})+'</script>'
            '<section class="product-gallery">'
            '<img alt="Laser 9395 front bearing kit" '
            'src="/media/9395-thumb.jpg" '
            'data-zoom-image="/media/9395-alt-angle.jpg" '
            'srcset="/media/9395-320.jpg 320w, '
            '/media/9395-1600.jpg 1600w">'
            '<img alt="Laser 9395 close-up" data-src="/media/opaque-detail.webp">'
            '<img alt="Different product 9195" src="/media/9195.jpg">'
            '<img src="https://evil.example/9395.jpg" alt="Laser 9395">'
            '<img src="/media/company-logo.svg" alt="Laser 9395">'
            '</section>'
        )
        approved=lambda url:urlparse(url).hostname in (
            "www.toolconnection.co.uk","www.lasertools.co.uk")
        found=gallery_urls_from_html(original,BASE,SKU,approved)
        self.assertTrue(found)
        self.assertIn("https://www.lasertools.co.uk/items/XLarge/9395.jpg",found)
        self.assertIn("https://www.toolconnection.co.uk/media/opaque-hash-A.webp",found)
        self.assertIn("https://www.toolconnection.co.uk/media/opaque-detail.webp",found)
        self.assertIn("https://www.toolconnection.co.uk/media/9395-1600.jpg",found)
        self.assertNotIn("https://www.toolconnection.co.uk/media/9195.jpg",found)
        self.assertFalse(any("evil.example" in x or x.endswith(".svg") for x in found))

    def test_duplicate_pictures_different_sizes_do_not_count_as_alt_heroes(self):
        main=source("https://www.lasertools.co.uk/items/XLarge/9395.jpg",photo(0))
        scaled=source("https://www.lasertools.co.uk/items/large/9395.jpg",
                      photo(0,(850,750)))
        extra=source("https://www.lasertools.co.uk/items/XLarge/9395_2.jpg",photo(1))
        second=source("https://www.lasertools.co.uk/items/XLarge/9395_3.jpg",photo(2))
        gallery=distinct_gallery([main,scaled,extra,second],main)
        self.assertEqual(len(gallery),3,[(x["source_url"],x["type"]) for x in gallery])
        self.assertEqual(len({x["sha256"] for x in gallery}),3)
        self.assertTrue(all(x["passed"] for x in gallery))

    def test_rejects_bad_thumbnail_even_if_gallery_lists_it_first(self):
        main=source("https://www.lasertools.co.uk/items/XLarge/9395.jpg",photo(0))
        rejected=(200,photo(1),"https://www.lasertools.co.uk/items/large/9395_2.jpg",
                  {"passed":False,"size":[320,300]})
        gallery=distinct_gallery([rejected,main],main)
        self.assertEqual(len(gallery),1)
        self.assertEqual(gallery[0]["source_url"],main[2])

    def test_more_than_one_real_photo_is_collected_after_first_pass(self):
        urls=[f"https://www.lasertools.co.uk/items/XLarge/9395_{i}.jpg"
              for i in range(6)]
        images={url:photo([0,0,1,1,2,3][n]) for n,url in enumerate(urls)}
        checked=[]
        def fetch(url):
            checked.append(url)
            return Response(url,images[url])
        def rank(blob):
            return 100,{"passed":True,"size":[850,750]}
        options,attempted=collect_official_photo_options(
            urls,fetch,lambda x:True,rank,max_checks=6,workers=2,
            min_distinct_good=3,distinct_signature=_signature)
        self.assertGreaterEqual(len(attempted),5)
        self.assertEqual(len(attempted),len(checked))
        self.assertGreaterEqual(len(distinct_gallery(options,options[0])),3)

    def test_gallery_is_private_disk_not_more_render_ram_cache(self):
        records=distinct_gallery([
            source("https://www.lasertools.co.uk/items/XLarge/9395.jpg",photo(0)),
            source("https://www.lasertools.co.uk/items/XLarge/9395_2.jpg",photo(1)),
            source("https://www.lasertools.co.uk/items/XLarge/9395_3.jpg",photo(2))
        ],source("https://www.lasertools.co.uk/items/XLarge/9395.jpg",photo(0)))
        public=store_gallery(SKU,records)
        self.assertEqual(len(public),3)
        self.assertFalse(any("_path" in row or "blob" in row for row in public))
        self.assertEqual(len(load_gallery(SKU)),3)
        self.assertTrue(all(isinstance(blob,bytes) for blob in load_gallery(SKU)))
        discard_gallery(SKU)
        self.assertEqual(load_gallery(SKU),[])

    def test_poster_editor_source_images_are_persisted_separately(self):
        from disk_campaign_store import StoredCampaign
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="gallery-edit-") as tmp:
            folder=Path(tmp)
            original=photo(0)
            second=photo(1)
            third=photo(2)
            stored=StoredCampaign(folder,{"part":SKU},[])
            role_photos={
                "poster_technical":original,
                "poster_price":second,
                "poster_smart":third,
            }
            stored.save_editor({
                "product":{"part":SKU,"title":"Verified Laser kit"},
                "genuine_photo":original,
                "role_photos":role_photos,
                "scenes":[None,None,None],
                "concepts":[{"headline":"Original"} for _ in range(3)],
                "distributor":None,
            })
            recovered=stored["editor_context"]
            self.assertEqual(recovered["role_photos"],role_photos)
            self.assertEqual(recovered["genuine_photo"],original)
            self.assertFalse(any(
                key.startswith("_") for key in recovered["role_photos"]))

    def test_fallback_with_one_manufacturer_image_is_safe(self):
        original=photo(0)
        refs=[{"sha256":hashlib.sha256(original).hexdigest(),
               "source_url":"https://www.lasertools.co.uk/items/XLarge/9395.jpg",
               "type":"packshot"}]
        from test_campaign_hub import CampaignHubTests
        CampaignHubTests.setUpClass()
        product={**CampaignHubTests.product,"part":SKU,"photo_gallery":refs,
                 "photo_source":refs[0]["source_url"],
                 "source":"https://www.toolconnection.co.uk/products/cars-vans/9395-kit"}
        expected_photo_for_role={}
        sampled_png=CampaignHubTests.sample_poster()
        def choose(render,role,source_blob,*args,**kwargs):
            expected_photo_for_role[role]=source_blob
            return sampled_png,{"passed":True}
        with patch("campaign_hub.find_scene",return_value=(None,{})), \
             patch("campaign_hub.choose_best",side_effect=choose), \
             patch("campaign_hub._native_graphic",return_value=sampled_png), \
             patch("campaign_hub.require_good_asset",return_value={"passed":True}), \
             patch("campaign_hub._source_qr",return_value=None):
            bundle=campaign_hub.build_campaign(
                product,original,use_gemini=False,gallery_images=[original])
        self.assertEqual(len(expected_photo_for_role),3)
        self.assertTrue(all(blob==original for blob in expected_photo_for_role.values()))
        self.assertEqual(len(bundle["manifest"]["artwork_photo_sources"]),9)

    def test_three_posters_get_three_different_verified_hero_photos(self):
        from test_campaign_hub import CampaignHubTests
        CampaignHubTests.setUpClass()
        blobs=[photo(i) for i in (0,1,2,3)]
        refs=[{"sha256":hashlib.sha256(blob).hexdigest(),
               "source_url":f"https://www.lasertools.co.uk/items/XLarge/9395_{i}.jpg",
               "type":"alternate" if i else "packshot"}
              for i,blob in enumerate(blobs)]
        product={**CampaignHubTests.product,"part":SKU,"photo_gallery":refs,
                 "photo_source":refs[0]["source_url"],
                 "source":"https://www.toolconnection.co.uk/products/cars-vans/9395-kit"}
        seen={}
        formats={}
        png=CampaignHubTests.sample_poster()
        def choose(renderer,role,source_blob,*args,**kwargs):
            seen[role]=source_blob
            return png,{"passed":True}
        def native(product,photo,distributor,key,*args,**kwargs):
            formats[key]=photo
            return png
        with patch("campaign_hub.find_scene",return_value=(None,{})), \
             patch("campaign_hub.choose_best",side_effect=choose), \
             patch("campaign_hub._native_graphic",side_effect=native), \
             patch("campaign_hub.require_good_asset",return_value={"passed":True}), \
             patch("campaign_hub._source_qr",return_value=None):
            bundle=campaign_hub.build_campaign(
                product,blobs[0],use_gemini=False,gallery_images=blobs)
        self.assertEqual(seen["technical_application"],blobs[0])
        self.assertEqual(seen["price_promo"],blobs[1])
        self.assertEqual(seen["product_selected"],blobs[2])
        self.assertEqual(len(formats),6)
        self.assertGreaterEqual(len(set(formats.values())),3)
        provenance=bundle["manifest"]["artwork_photo_sources"]
        self.assertNotEqual(provenance["poster_technical"]["sha256"],
                            provenance["poster_price"]["sha256"])
        self.assertNotEqual(provenance["poster_price"]["sha256"],
                            provenance["poster_smart"]["sha256"])
        self.assertTrue(all(ref["source_url"].startswith("https://")
                            for ref in provenance.values()))
