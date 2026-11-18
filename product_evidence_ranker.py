"""Evidence-ranked selling points for the individual Laser Tools product.

This is a product-aware scoring model, not an assertion of customer demand.
Only exact verified manufacturer feature strings can be returned. Identifies
the product's job before size/weight and filters unrelated accessory numbers.
"""
from __future__ import annotations

import re
from marketing_intelligence import detect_category, is_related_product_reference

FUNCTION_TERMS={
 "lighting_inspection":(("fan","speed","lumen","brightness","led","light","recharge","battery","runtime","run time","illumination","work lamp"),("dimensions","weight","height")),
 "engine_timing":(("camshaft","crankshaft","locking","timing","engine","belt","chain","fitment","application"),("dimensions","weight")),
 "bearing_suspension":(("bearing","hub","removal","installation","clamshell","suspension","workshop","vehicle"),("dimensions","weight")),
 "socket_ratchet":(("drive","teeth","tooth","ratchet","socket","pieces","set","stainless","size","contents"),("dimensions","weight")),
 "workshop_press":(("capacity","tonne","ton","hydraulic","ram","press","stroke","load"),("dimensions","weight")),
 "diagnostic_electrical":(("function","scan","read","test","voltage","measurement","range","diagnostic","circuit"),("dimensions","weight")),
 "workshop_service":(("service","removal","installation","transfer","repair","drain","fluid","operation"),("dimensions","weight")),
 "general_hand_tools":(("grip","handle","drive","application","remove","install","steel","size"),("weight",)),
}
THIRD_TERMS={
 "kit_contents":("includes","included","supplied","piece","contents","set","drive","sizes"),
 "workshop_solution":("remove","install","service","repair","workshop","use"),
 "capacity_specs":("capacity","tonne","hydraulic","ram","load","stroke"),
 "performance_specs":("brightness","lumen","fan","speed","runtime","recharge","battery","power","range"),
 "safety_specs":("rated","protection","insulated","volt","standard","safety"),
 "access_function":("access","grip","length","handle","tool","design"),
 "service_workflow":("service","remove","drain","install","transfer","replace"),
 "fitment_coverage":("application","engine","vehicle","models","fit"),
}
MEASURE_ONLY=re.compile(
 r"^\s*(?:dimensions?|weight|length|width|height|measurements?|size)\s*:",re.I)
WEAK=re.compile(r"\b(?:visit (?:our|the) website|full details|50.year warranty|"
 r"more information|see (?:laser )?part|refer to (?:part|product))\b",re.I)


def verified_candidates(product):
    result=[]
    for line in product.get("features") or []:
        if not isinstance(line,str):continue
        fact=" ".join(line.split())[:175].strip()
        if not fact or is_related_product_reference(fact):continue
        if fact not in result:result.append(fact)
    return result


def rank_product_facts(product,role,theme=None,excluded=()):
    category,_=detect_category(product)
    terms,less=FUNCTION_TERMS.get(category,FUNCTION_TERMS["general_hand_tools"])
    special=THIRD_TERMS.get(theme or "",())
    # Role 1: describe the actual job. Role 2: short scan-friendly feature.
    # Role 3: the selected category-specific additional selling point.
    selected_terms=special if role=="product_selected" and special else terms
    title_words=set(re.findall(r"[a-z]{3,}",str(product.get("title") or "").casefold()))
    excluded_set=set(excluded)
    ranking=[]
    for position,fact in enumerate(verified_candidates(product)):
        low=fact.casefold()
        matches=sum((len(selected_terms)-i)*5 for i,term in enumerate(selected_terms)
                    if term in low)
        title_matches=sum(1 for word in title_words if len(word)>=4 and word in low)
        score=matches+min(6,title_matches*2)
        if role=="price_promo":
            # Prefer a concise, specific product fact on a price advert.
            score-=max(0,(len(fact)-85)//7)
        elif role=="technical_application":
            # Only a functional claim deserves the hero technical slot.
            score+=8 if any(term in low for term in terms[:5]) else 0
        if MEASURE_ONLY.match(fact):
            score-=36 if category in ("lighting_inspection","engine_timing",
                                      "bearing_suspension") else 10
        if WEAK.search(low):score-=28
        if any(token in low for token in less):score-=7
        if fact in excluded_set:score-=10000
        ranking.append((score,-position,fact))
    return sorted(ranking,reverse=True)


def choose_verified_fact(product,role,theme=None,excluded=()):
    ranked=rank_product_facts(product,role,theme,excluded)
    if not ranked:return ""
    score,_,fact=ranked[0]
    if score<=-1000:return ""
    return fact
