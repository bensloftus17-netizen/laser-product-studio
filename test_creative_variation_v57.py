"""V57 regressions: real creative direction, pixels, verified copy and ZIP.

No Gemini or external network is necessary. Tests exercise the actual Pillow
layers plus a nine-asset integration path with honest format inheritance.
"""
from __future__ import annotations

import copy
import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image,ImageDraw

from creative_director import validate_brief
from creative_families import (
    FAMILIES,ROLES,FORMAT_PARENTS,choose_format_parents,
    source_supported_headline,sanitize_contract,diversify_concepts,
    copy_diversity,layout_diversity,
)
from flexible_canvas import _role_art_direction,render_creative_canvas
from format_creative import draw_family_background,FORMATS,FORMAT_ORDER
from poster_quality import capture
from campaign_hub import FOLDERS,build_campaign
from campaign_distinctness import check_distinctness
from test_ai_creative_director_v45 import (
    PRICE,SMART,TECH,PRODUCT,image_bytes,fake_photo)
from test_ai_formats_v46 import FOUR


def native_png(kind):
    width,height=FORMATS[kind][:2]
    image=Image.new("RGB",(width,height),"#0A2948")
    d=ImageDraw.Draw(image)
    d.polygon(((0,height//2),(width,height//4),
               (width,3*height//4),(0,3*height//4)),fill="#178CD0")
    out=io.BytesIO();image.save(out,"PNG")
    return out.getvalue()


class CreativeVariationV57Tests(unittest.TestCase):
    def test_six_families_render_six_materially_different_backdrops(self):
        empty=Image.new("RGBA",(1200,1500),"#082B48")
        raw=validate_brief(TECH,"technical_application")
        poster_comparisons=[]
        format_comparisons=[]
        for family in FAMILIES:
            brief={**raw,"creative_family":family}
            backdrop=_role_art_direction(empty,brief,"technical_application")
            poster_comparisons.append(backdrop.resize((40,50)).tobytes())
            canvas=draw_family_background(
                Image.new("RGBA",(1080,1920),"#082B48"),family)
            format_comparisons.append(canvas.resize((40,50)).tobytes())
        self.assertEqual(len(set(poster_comparisons)),6)
        self.assertEqual(len(set(format_comparisons)),6)

    def test_same_official_photo_six_different_families_no_untrusted_copy(self):
        photo=image_bytes()
        outputs=[]
        with patch("flexible_canvas.product_photo",side_effect=fake_photo) as cutout:
            for family in FAMILIES:
                canvas={**TECH,"creative_family":family}
                concept={"campaign_role":"technical_application",
                         "creative_canvas":canvas,
                         "headline":"Ratchet Set 4pc",
                         "selling_point":"Set of four ratchets."}
                with capture() as tracked:
                    output=render_creative_canvas(
                        PRODUCT,photo,concept,variant=1)
                self.assertFalse(any(x["truncated"] for x in tracked.texts))
                self.assertTrue(tracked.products)
                self.assertTrue(any(t["role"]=="headline" for t in tracked.texts))
                outputs.append(Image.open(io.BytesIO(output))
                               .resize((60,75)).tobytes())
        self.assertEqual(len(set(outputs)),6)
        self.assertEqual(cutout.call_count,6)
        self.assertTrue(all(call.args[1]==photo for call in cutout.call_args_list))

    def test_model_direction_is_sanitized_and_repeated_families_corrected(self):
        raws=[copy.deepcopy(TECH),copy.deepcopy(PRICE),copy.deepcopy(SMART)]
        concepts=[]
        for role,canvas in zip(ROLES,raws):
            canvas["creative_family"]="engineering_grid"
            concepts.append({
                "campaign_role":role,
                "creative_canvas":canvas,
                "creative_direction":sanitize_contract(
                    {"creative_family":"engineering_grid",
                     "headline_strategy":"free_money",
                     "price_emphasis":"dominant"},role),
                "visual_plan":{},
            })
        before=[copy.deepcopy(c["creative_canvas"]["zones"]) for c in concepts]
        changed=diversify_concepts(concepts)
        self.assertEqual(changed,["price_promo","product_selected"])
        self.assertEqual([c["creative_canvas"]["zones"] for c in concepts],before)
        self.assertEqual(len({c["creative_direction"]["creative_family"]
                              for c in concepts}),3)
        self.assertEqual(concepts[0]["creative_direction"]["price_emphasis"],"none")
        self.assertTrue(all(c["creative_direction"]["headline_strategy"] in
                            ("application","price","benefit") for c in concepts))

    def test_model_copy_uses_only_source_backed_words_not_offers(self):
        self.assertEqual(source_supported_headline(
            "Ratchet Set 4pc",PRODUCT),"Ratchet Set 4pc")
        for fabricated in ("50% DISCOUNT FREE SHIPPING",
                           "Ultimate unbeatable ratchet guarantee",
                           "Fits every car in Europe"):
            self.assertIsNone(source_supported_headline(fabricated,PRODUCT))
        self.assertEqual(len(FAMILIES),6)

    def test_format_parent_mapping_includes_three_distinct_angles(self):
        parents=choose_format_parents({})
        self.assertEqual(parents,FORMAT_PARENTS)
        self.assertEqual(set(parents.values()),set(ROLES))
        self.assertEqual(parents["linkedin_graphic"],"technical_application")
        self.assertEqual(parents["social_story"],"price_promo")
        invalid={kind:"price_promo" for kind in FORMAT_ORDER}
        adapted=choose_format_parents(invalid)
        self.assertEqual(set(adapted.values()),set(ROLES))
        self.assertEqual(adapted["linkedin_graphic"],"technical_application")
        self.assertEqual(adapted["landscape_ad"],"price_promo")

    def test_sameness_gate_rejects_repeated_family_and_cloned_art(self):
        concepts=[
            {"creative_canvas":validate_brief(raw,role),
             "creative_direction":sanitize_contract(
                 {"creative_family":"engineering_grid"},role),
             "campaign_role":role,
             "selling_point":"Exactly the same marketing line"}
            for role,raw in zip(ROLES,(TECH,PRICE,SMART))]
        self.assertTrue(copy_diversity(concepts))
        clones=[{**validate_brief(raw,role),"creative_family":"engineering_grid"}
                for role,raw in zip(ROLES,(TECH,PRICE,SMART))]
        self.assertTrue(layout_diversity(clones))
        full=io.BytesIO()
        Image.new("RGB",(1200,1500),"#173A54").save(full,"PNG")
        picture=full.getvalue()
        report=check_distinctness(
            dict.fromkeys(("poster_technical","poster_price","poster_smart"),
                          picture),concepts)
        self.assertFalse(report["passed"])
        self.assertTrue(any("duplicate" in problem for problem in report["issues"]))
        self.assertTrue(all("perceptual_hash_distance" in p for p in report["pairs"]))

    def test_full_pack_inherits_all_three_marketing_angles_and_meta(self):
        concepts=[
            {"creative_canvas":PRICE,"ai_format_canvases":FOUR,
             "creative_direction":{"creative_family":"commercial_burst"},
             "ai_verified_features":["Supplied with a carry case."]},
            {"creative_canvas":SMART,
             "creative_direction":{"creative_family":"premium_spotlight"},
             "ai_verified_features":["Set of four ratchets."]},
            {"creative_canvas":TECH,
             "creative_direction":{"creative_family":"engineering_grid"},
             "ai_verified_features":["Four drive options for workshop use."]},
        ]
        poster=image_bytes(1200,1500)
        events=[]
        seen=[]
        def generate(kind,brief,*args,**kwargs):
            seen.append((kind,brief["headline_role"],brief["creative_family"]))
            return native_png(kind),{
                "passed":True,"render_engine":"ai-original-format-canvas",
                "native_dimensions":list(FORMATS[kind][:2]),
            }
        with patch("campaign_hub._concepts",return_value=(
                 concepts,"gemini-assisted",[])), \
             patch("campaign_hub.require_good_asset",
                   return_value={"passed":True}), \
             patch("campaign_hub.find_scene",return_value=(
                 None,{"source":"No external photograph used","category":"hand_tools"})), \
             patch("campaign_hub.choose_best",return_value=(
                 poster,{"passed":True,"score":95,"variation":1})), \
             patch("campaign_hub.review_finished_artworks",return_value={
                 "reviewed":True,"method":"test","issues":{},"warning":None}), \
             patch("campaign_hub.check_distinctness",return_value={
                 "passed":True,"issues":[],"pairs":[]}), \
             patch("campaign_hub.generate_format",side_effect=generate), \
             patch("campaign_hub._native_graphic",return_value=native_png("social_square")):
            # Our raw concepts do not contain native artboards, so this call
            # deliberately exercises the VERIFIED, inherited backup route.
            pack=build_campaign(PRODUCT,image_bytes(),use_gemini=True,
                                progress=lambda *args:events.append(args))
        self.assertEqual(len(pack["manifest"]["images"])-1,9)
        self.assertEqual(pack["manifest"]["creative_plan"]["creative_families"],
                         ["engineering_grid","commercial_burst","premium_spotlight"])
        self.assertEqual(pack["manifest"]["creative_plan"]["format_parent_roles"],
                         FORMAT_PARENTS)
        self.assertEqual(pack["manifest"]["angles"][0]["creative_family"],
                         "engineering_grid")
        self.assertEqual(pack["manifest"]["angles"][1]["headline_strategy"],"price")
        reports=pack["manifest"]["format_artwork_quality"]
        self.assertEqual(len(seen),6)
        self.assertEqual([role for _,role,_ in seen],
                         [FORMAT_PARENTS[k] for k in FORMAT_ORDER])
        self.assertEqual(len({reports[k]["parent_role"] for k in FORMAT_ORDER}),3)
        self.assertEqual(len({reports[k]["creative_family"] for k in FORMAT_ORDER}),3)
        self.assertTrue(all("parent_role" in reports[k] for k in FORMAT_ORDER))
        with ZipFile(io.BytesIO(pack["archive"])) as z:
            self.assertTrue(all(path in z.namelist() for path in FOLDERS.values()))
        self.assertEqual(len([e for e in events if e[0]=="ready" and e[1] in FOLDERS]),9)


if __name__=="__main__":
    unittest.main()
