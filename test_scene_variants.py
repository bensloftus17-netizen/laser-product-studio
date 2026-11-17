"""Regression suite for step 1 (photographic matching) and step 2 (nine layouts).

No model calls, network photos or unreviewed manufacturer claims. Tests exercise
the real Pillow render pipeline with an authentic-looking source packshot.
"""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw

from promo_scene_library import (
    SCENE_CANDIDATES,SCENE_PHOTOS,FAMILY_SCENE_STYLES,
    classify_product,scene_reference,find_scene,_fetch_licensed_photo,
)
from ai_promo_renderer import render_promo


def _sample_packshot():
    image=Image.new("RGB",(760,520),"white")
    d=ImageDraw.Draw(image)
    d.rounded_rectangle((113,76,665,458),radius=29,fill="#0A6AA8")
    d.rectangle((170,145,588,384),fill="#283746")
    d.rounded_rectangle((283,212,515,304),radius=9,fill="#4A6070")
    d.text((304,246),"LASER",fill="white")
    out=io.BytesIO();image.save(out,format="PNG")
    return out.getvalue()


def _sample_context():
    image=Image.new("RGB",(1400,900),"#415362")
    d=ImageDraw.Draw(image)
    d.rectangle((0,0,490,900),fill="#D1DADD")
    d.polygon([(700,100),(1400,100),(1160,870),(740,870)],
              fill="#1A405F")
    d.rectangle((845,390,1280,770),fill="#A5AEB5")
    output=io.BytesIO();image.save(output,format="JPEG")
    return output.getvalue()


class SceneDirectionV6Tests(unittest.TestCase):
    def test_every_product_category_has_checked_photography_and_three_family_styles(self):
        self.assertEqual(set(SCENE_CANDIDATES),set(SCENE_PHOTOS))
        self.assertEqual(set(FAMILY_SCENE_STYLES),{"retail","premium","trade"})
        for category,pool in SCENE_CANDIDATES.items():
            with self.subTest(category=category):
                self.assertGreaterEqual(len(pool),2)
                for photo_id,name,cx,cy in pool:
                    self.assertIsInstance(photo_id,int)
                    self.assertTrue(name)
                    self.assertTrue(0<=cx<=1 and 0<=cy<=1)
                refs=[scene_reference(category,0,family=f) for f in
                      ("retail","premium","trade")]
                self.assertEqual(len({tuple(ref["crop"]) for ref in refs}),3)
                self.assertEqual(len({ref["darkness"] for ref in refs}),3)
                for ref in refs:
                    self.assertIn(ref["photo_id"],{p[0] for p in pool})
                    self.assertIn("pexels.com",ref["page_url"])
                    self.assertTrue(ref["image_url"].startswith("https://images.pexels.com/"))

    def test_battery_charger_receives_cable_photos_and_family_directions(self):
        product={"part":"CH1234","title":"12V Battery Charger 10A"}
        self.assertEqual(classify_product(product),"battery")
        with patch("promo_scene_library._fetch_licensed_photo",return_value=b"original"):
            records=[find_scene(product,variation=i,family=f) for i,f in
                     enumerate(("retail","premium","trade"))]
        self.assertEqual({ref["category"] for _,ref in records},{"battery"})
        self.assertEqual(len({tuple(ref["crop"]) for _,ref in records}),3)
        self.assertIn("Battery",records[0][1]["description"])

    def test_official_in_situ_image_takes_priority_in_trade(self):
        product={"part":"9385","title":"Glow Plug Removal Kit",
                 "application_photo_source":"https://example.com/real-in-situ.jpg"}
        with patch("promo_scene_library._fetch_licensed_photo",return_value=b"stock"):
            shot,meta=find_scene(product,official_photo=b"official",
                                prefer_official=True,family="trade")
        self.assertEqual(shot,b"official")
        self.assertEqual(meta["source"],"Official manufacturer application photo")
        self.assertEqual(meta["family"],"trade")

    def test_unknown_photo_ids_are_never_fetched(self):
        _fetch_licensed_photo.cache_clear()
        with patch("promo_scene_library.requests.get") as fake:
            photo=_fetch_licensed_photo(999999999)
        self.assertIsNone(photo)
        fake.assert_not_called()

    def test_missing_source_retries_another_photo_only_in_same_category(self):
        product={"title":"12V Battery Charger with Leads","part":"CH1100"}
        ids=[scene_reference("battery",i,"retail")["photo_id"]
             for i in range(3)]
        def available_after_first(asset_id):
            return b"real_backdrop" if asset_id==ids[1] else None
        with patch("promo_scene_library._fetch_licensed_photo",
                   side_effect=available_after_first) as get:
            chosen,source=find_scene(product,variation=0,family="retail")
        self.assertEqual(chosen,b"real_backdrop")
        self.assertEqual(source["photo_id"],ids[1])
        self.assertEqual(get.call_count,2)
        self.assertEqual(source["category"],"battery")

    def test_stable_part_category_not_confused_by_generic_description(self):
        p={"title":"12V Battery Maintainer","description":"Engine bay service and workshop use"}
        self.assertEqual(classify_product(p),"battery")


class CreativeVariantsV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.photo=_sample_packshot()
        cls.context=_sample_context()
        cls.product={"part":"8899","title":"Ball Joint Separator - for JLR",
                     "features":["Heavy-duty scissor-type ball joint separator"],
                     "price":"£144.16 excluding VAT","price_source":"Manufacturer"}

    def _render(self,family,variant,editor=None):
        concept={"family":family,"variant":variant,
                 "headline":"Ball Joint Separator for JLR",
                 "subline":"Land Rover & Jaguar applications",
                 "features":self.product["features"]}
        direction=scene_reference("suspension",variant,family=family)
        return render_promo(concept,self.photo,self.product,
             editor={"background":"context","_scene_bytes":self.context,
                     "_scene_style":direction,
                     "show_subline":True,**(editor or {})})

    def test_all_nine_compositions_generate_legitimate_distinct_pngs(self):
        previews={}
        for family in ("retail","premium","trade"):
            for variant in (0,1,2):
                with self.subTest(family=family,variant=variant):
                    raw=self._render(family,variant)
                    self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))
                    with Image.open(io.BytesIO(raw)) as im:
                        self.assertEqual(im.size,(1200,1500))
                        self.assertEqual(im.mode,"RGB")
                        previews[(family,variant)]=im.resize((48,60)).tobytes()
        self.assertEqual(len(set(previews.values())),9)
        # A different layout family must produce significant pixel differences.
        for fam in ("retail","premium","trade"):
            a,b,c=(previews[(fam,v)] for v in (0,1,2))
            for x,y in ((a,b),(a,c),(b,c)):
                fraction=sum(abs(m-n)>50 for m,n in zip(x,y))/len(x)
                self.assertGreater(fraction,.075,(fam,fraction))

    def test_custom_editor_price_position_and_style_work_in_all_variants(self):
        for family in ("retail","premium","trade"):
            for variant in (0,1,2):
                with self.subTest(family=family,variant=variant):
                    normal=self._render(family,variant)
                    alt=self._render(family,variant,{
                        "price_style":"tag","price_position":"opposite",
                        "product_scale":95,"headline_size":"small"})
                    self.assertNotEqual(normal,alt)

    def test_product_scene_crop_metadata_changes_actual_rendering(self):
        a=self._render("premium",1)
        changed=self._render("premium",1,{
            "_scene_style":{"crop":(.15,.15),"colour":.9,
                            "darkness":.04,"blur":0.0}})
        self.assertNotEqual(a,changed)

if __name__=="__main__":
    unittest.main()
