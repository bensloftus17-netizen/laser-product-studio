"""Director of one *product-specific* Laser Tools campaign.

Three mandatory but different roles:
  1. Technical / application: explains genuine use, kit or fitment.
  2. Price-led: bold and simple; price is never invented.
  3. Product-selected: *different* benefit chosen for the specific product.

Gemini can suggest the third creative role in the EXISTING concepts request.
The server validates that choice against the manufacturer's category and
source record. If the model is unavailable, the category-specific plan runs
with a transparent verified-source fallback. No model is allowed to invent
product pictures, fitment, results or technical claims.
"""
from __future__ import annotations

import hashlib
import re

from marketing_intelligence import (detect_category, rank_verified_features,
                                    is_related_product_reference)
from official_taxonomy import category_from_product_url
from promo_scene_library import classify_product
from promo_selling_points import choose_feature

ROLES = ("technical_application", "price_promo", "product_selected")
POSTER_LABELS = ("Application / Technical", "Price-led Promotion", "Recommended Extra Angle")
# Third-angle options are product-specific and mutually exclusive with a
# generic application sheet or price promotion.
THIRD_ANGLES = {
    "fitment_coverage": ("Engine / vehicle coverage", "application"),
    "kit_contents": ("What's included in the kit", "benefit"),
    "workshop_solution": ("Workshop task / solution", "benefit"),
    "capacity_specs": ("Capacity and capability", "benefit"),
    "performance_specs": ("Verified performance details", "benefit"),
    "safety_specs": ("Safety and rated use", "benefit"),
    "access_function": ("Access and tool functionality", "benefit"),
    "service_workflow": ("Service and maintenance task", "benefit"),
}
CATEGORY_THIRD = {
    "engine_timing": "kit_contents",
    "bearing_suspension": "workshop_solution",
    "socket_ratchet": "kit_contents",
    "workshop_press": "capacity_specs",
    "diagnostic_electrical": "performance_specs",
    "lighting_inspection": "performance_specs",
    "bodyshop_repair": "workshop_solution",
    "air_power": "performance_specs",
    "threading_cutting": "access_function",
    "workshop_service": "service_workflow",
    "accessories_consumables": "kit_contents",
    "general_hand_tools": "access_function",
}
LENS_THIRD = {
    "application_fitment": "fitment_coverage",
    "kit_contents": "kit_contents",
    "capacity_equipment": "capacity_specs",
    "electrical_testing": "performance_specs",
    "ev_safety": "safety_specs",
    "ppe_specification": "safety_specs",
    "lighting_visibility": "performance_specs",
    "fluids_service": "service_workflow",
    "bodyshop_application": "workshop_solution",
    "measurement_specs": "performance_specs",
    "torque_precision": "performance_specs",
    "individual_drive_tools": "access_function",
    "cordless_power": "performance_specs",
    "bicycle_maintenance": "service_workflow",
    "motorcycle_service": "service_workflow",
    "materials_consumables": "kit_contents",
}
# Different tool types should not just change the colour of the same poster.
# The renderer implements THREE intentionally separate layouts, with
# per-product variation of position, crop, accent and photographic scene.
CATEGORY_SCENES = {
    "engine_timing": "engine", "bearing_suspension": "wheel_hub",
    "socket_ratchet": "hand_tools", "workshop_press": "press",
    "diagnostic_electrical": "diagnostic", "lighting_inspection": "engine",
    "bodyshop_repair": "suspension", "air_power": "hand_tools",
    "threading_cutting": "hand_tools", "workshop_service": "workshop",
    "accessories_consumables": "hand_tools", "general_hand_tools": "hand_tools",
}
CATEGORY_ACCENTS = {
    "engine_timing": ("#16B9EE", "#FFC83A", "#D9EC54"),
    "bearing_suspension": ("#16B1EA", "#F6B73C", "#38C3E0"),
    "socket_ratchet": ("#32B6EA", "#FDC23D", "#88CFDE"),
    "workshop_press": ("#55B4D4", "#FFB52E", "#D9E75B"),
    "diagnostic_electrical": ("#52C7EB", "#FBC22D", "#5ED4C5"),
    "lighting_inspection": ("#99DEEA", "#FFD94F", "#BDE66A"),
    "bodyshop_repair": ("#45BBD9", "#F5B634", "#E9C865"),
    "air_power": ("#47B8D3", "#F7C344", "#AEDF79"),
    "general_hand_tools": ("#2CB7E8", "#F8BD31", "#63D7DB"),
}


def _clean(s, limit=150):
    return " ".join(str(s or "").split())[:limit].rstrip(" ,:-;")


def _category(product):
    official=product.get("official_taxonomy") or category_from_product_url(
        product.get("source"), product.get("part"))
    category,_=detect_category(product)
    lens=(official or {}).get("marketing") or {}
    return category, lens, official


def third_angle_options(product):
    """Only permitted category-relevant extra angles; no model free text."""
    category,lens,_=_category(product)
    primary=CATEGORY_THIRD.get(category) or LENS_THIRD.get(lens.get("id")) or "access_function"
    # The first poster is always application/technical; do not use another
    # application/fitment poster as the supposedly new third creative.
    if primary=="fitment_coverage":primary="workshop_solution"
    alternate={
        "fitment_coverage":"kit_contents",
        "kit_contents":"workshop_solution",
        "workshop_solution":"access_function",
        "capacity_specs":"workshop_solution",
        "performance_specs":"access_function",
        "safety_specs":"access_function",
        "service_workflow":"access_function",
        "access_function":"workshop_solution",
    }[primary]
    return list(dict.fromkeys((primary,alternate)))


def _choose_third(product, requested=None):
    available=third_angle_options(product)
    return requested if isinstance(requested,str) and requested in available else available[0]


def _verified_facts(product):
    facts=[]
    for item in product.get("features") or []:
        if not isinstance(item,str):
            continue
        if is_related_product_reference(item):
            continue
        fact=_clean(item,175)
        if fact and fact not in facts:
            facts.append(fact)
    return facts


def _pick_proof(product, role, theme, excluded):
    """Prioritise 2-3 DIFFERENT verified facts, never fabricate one."""
    category,lens,_=_category(product)
    facts=_verified_facts(product)
    if not facts:
        return ""
    terms={
        "fitment_coverage":("vehicle","engine","model","application","designed for","fits"),
        "kit_contents":("include","piece","contents","supplied","set","size","drive"),
        "workshop_solution":("remove","install","repair","service","without","workshop"),
        "capacity_specs":("capacity","tonne","load","stroke","pressure","height"),
        "performance_specs":("lumen","runtime","run time","battery","range","rpm","volt","torque"),
        "safety_specs":("rated","1000v","volt","protection","standard","test"),
        "access_function":("access","grip","handle","length","drive","size","design"),
        "service_workflow":("service","transfer","drain","repair","replace","remove"),
    }
    technical_by_category={
        "engine_timing":("camshaft","crankshaft","timed","belt replacement","engine","application","vehicle"),
        "bearing_suspension":("bearing","removal","installation","vehicle","application","hub"),
        "workshop_press":("capacity","pressing","workshop","application"),
        "socket_ratchet":("drive","ratchet","size","set","tooth"),
        "diagnostic_electrical":("testing","measurement","diagnostic","range"),
    }
    cues=(technical_by_category.get(category,("application","vehicle","engine","timing","fit"))
          if role=="technical_application"
          else ("include","supplied","capacity","size","handle") if role=="price_promo"
          else terms.get(theme,("benefit","use")))
    source_rank=rank_verified_features(product,category,8)
    by_fact={value:i for i,value in enumerate(source_rank)}
    # Model text cannot enter this list; all choices are exact manufacturer facts.
    scored=[]
    for index,fact in enumerate(facts):
        low=fact.casefold()
        score=sum((len(cues)-i)*5 for i,word in enumerate(cues) if word in low)
        score+=max(0,8-by_fact.get(fact,9))
        if fact in excluded:
            score-=1000
        # A reference to an additional Laser item is not a strong proof for
        # the advertised product, especially timing kits.
        if re.search(r"\b(?:laser\s+)?part\s*(?:no\.?|number)\s*[:#]?\s*\d{3,6}\b",fact,re.I):
            score-=150
        scored.append((score,-index,fact))
    return max(scored)[2]


def _headline(product, role, theme, fact):
    """Genuine product name anchors every headline; no made-up outcomes."""
    title=re.sub(r"^laser\s+tools?\s*","",_clean(product.get("title"),100),flags=re.I).strip()
    if role=="technical_application":
        return title[:74]
    if role=="price_promo":
        return title[:74]
    # Smart poster's label points to a *type of evidence*, not an
    # unverifiable benefit or a promised timesaving/performance outcome.
    return (THIRD_ANGLES[theme][0]+" — "+title)[:92]


def _variation(product, role, category):
    digest=hashlib.sha256(
        (str(product.get("part") or "")+"/"+str(category)+"/"+role).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:2],"big")%3, int.from_bytes(digest[2:4],"big")


def plan_campaign(product, model_concepts=None, marketing_strategy=None):
    """Return three distinct concepts and a transparent, source-grounded plan."""
    model_concepts=model_concepts or []
    model_choice=(model_concepts[0].get("ai_strategy_choice") or {}
                  if model_concepts and isinstance(model_concepts[0],dict) else {})
    third=_choose_third(product, model_choice.get("third_angle"))
    category,lens,official=_category(product)
    scene=CATEGORY_SCENES.get(category,classify_product(product))
    photo_variants=("trade","retail","premium")
    family_map=("trade","retail","premium")
    role_focus=("application","price",THIRD_ANGLES[third][1])
    used=set()
    planned=[]
    scenes=[]
    for i,role in enumerate(ROLES):
        fact=_pick_proof(product,role,third,used)
        if fact:used.add(fact)
        variation,seed=_variation(product,role,category)
        # AI's wording is used only if it is a literal manufacturer feature.
        # Every generated display headline retains the genuine product noun.
        facts=[fact] if fact else []
        if role=="technical_application":
            for extra in _verified_facts(product):
                if extra!=fact and len(facts)<3:facts.append(extra)
        title=_headline(product,role,third,fact)
        role_label=POSTER_LABELS[i] if i<2 else THIRD_ANGLES[third][0]
        concept={
            "id":i,"family":family_map[i],"variant":variation,
            "focus":role_focus[i],
            "focus_label":("TECHNICAL / APPLICATION" if i==0 else
                           "PRICE / PRODUCT PROMOTION" if i==1 else
                           "PRODUCT-SPECIFIC / "+THIRD_ANGLES[third][0].upper()),
            "campaign_role":role,
            "third_angle":third if i==2 else None,
            "name":role_label,
            "headline":title,
            "subline":fact or _clean(product.get("title"),110),
            "angle":role_label+" using verified manufacturer information",
            "features":facts,
            "selling_point":fact,
            "copy_direction":{"tone":"professional",
                              "hook":"application" if i==0 else "product" if i==1 else "feature",
                              "cta":"specifications" if i==0 else "enquire"},
            "part":str(product.get("part") or ""),"title":str(product.get("title") or ""),
            "visual_plan":{
                "layout_family":family_map[i],
                "scene_category":scene,
                "scene_index":seed+i,
                "accent":CATEGORY_ACCENTS.get(category,CATEGORY_ACCENTS["general_hand_tools"])[i],
                "price_style":("plaque","bubble","panel")[i],
                "photo_focus":("right","left","centre")[variation],
                "purpose":role_label,
                "supporting_image_rule":"real approved contextual photo, never a redrawn tool",
            },
        }
        planned.append(concept)
        scenes.append({
            "role":role,"layout":family_map[i],"scene_category":scene,
            "variation":variation,"why":(
                "Explains documented application and specifications" if i==0
                else "Promotes confirmed product price or price on request" if i==1
                else "Uses "+THIRD_ANGLES[third][0].lower()+
                     " because of this product category and its verified features"
            )
        })
    return planned,{
        "part":str(product.get("part") or ""),
        "product_type":category,
        "official_category_path":(official or {}).get("path",[]),
        "third_angle":third,
        "third_angle_label":THIRD_ANGLES[third][0],
        "selection_method":(
            "gemini-validated-category-choice"
            if model_choice.get("third_angle")==third else "category-evidence-fallback"
        ),
        "different_roles":list(ROLES),
        "creative_decisions":scenes,
        "reason":(
            "Distinct technical, price and "+THIRD_ANGLES[third][0].lower()+
            " creative directions for this product, with actual manufacturer imagery."
        ),
    }
