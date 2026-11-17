"""Three evidence-based sales angles for the exact same Laser Tools product.

The model can propose headlines, but featured proof points are selected only
from source-verified feature strings or verified price information. No made-up
vehicle fitment, savings or technical claims can enter this layer.
"""
from __future__ import annotations

import re

from marketing_intelligence import rank_verified_features
from ai_promo_renderer import verified_price

FOCUS_BY_FAMILY={"retail":"price","premium":"benefit","trade":"application"}
LABELS={"price":"VERIFIED UK RRP","benefit":"WHY THIS TOOL",
        "application":"VEHICLE / WORKSHOP APPLICATION"}
APPLICATION_TERMS=re.compile(
    r"\b(?:application|suitable|fit(?:s|ment)?|compatible|"
    r"vehicle|engine|land rover|jaguar|ford|mercedes|vw|volkswagen|"
    r"bmw|audi|sprinter|crafter|transit|hub|bearing|brake|"
    r"wheel|axle|pulley|crankshaft|cylinder|installation|removal|"
    r"thread|range rover|discovery|workshop)\b",re.I)
BENEFIT_TERMS=re.compile(
    r"\b(?:allows?|enables?|ideal|prevent|reduce|eas(?:y|ier)|"
    r"access|durab|strength|heavy.duty|quick|time|"
    r"ergonomic|comfortable|compact|reach|versatile|"
    r"protect|safety|precise|torque|capacity|adjust|"
    r"scissor|portable|powered|battery|voltage|"
    r"complete|includes?|supplied|made|manufactured)\b",re.I)


def _clean_features(product):
    original=[str(x).strip() for x in product.get("features",[])
              if isinstance(x,str) and str(x).strip()]
    ordered=rank_verified_features(product,limit=10)
    result=[]
    for text in ordered+original:
        if text not in result:result.append(text)
    return result


def choose_feature(product, focus, exclude=()):
    approved=_clean_features(product)
    used=set(exclude)
    available=[v for v in approved if v not in used] or approved
    if not available:return ""
    if focus=="application":
        candidates=[v for v in available if APPLICATION_TERMS.search(v)]
        return (candidates or available)[0]
    if focus=="benefit":
        # A practical workshop advantage takes precedence over a fitment list,
        # even when an application sentence also says "includes".
        candidates=[v for v in available if BENEFIT_TERMS.search(v)
                    and not APPLICATION_TERMS.search(v)]
        if not candidates:
            candidates=[v for v in available if BENEFIT_TERMS.search(v)]
        return (candidates or available)[0]
    return available[0]


def focus_concept(product, concept, index, used_points=None):
    """Attach a distinct purpose; feature proof is copied verbatim from source.

    Missing application evidence does not become a fabricated vehicle claim.
    """
    result=dict(concept)
    family=result.get("family") or ("retail","premium","trade")[index%3]
    focus=FOCUS_BY_FAMILY.get(family,("price","benefit","application")[index%3])
    source=_clean_features(product)
    preferred=choose_feature(product,focus,used_points or ())
    if focus=="price":
        # Gemini can select any real manufacturer fact alongside the RRP.
        # Preserve that evidenced choice rather than imposing a generic one.
        user_candidates=concept.get("features") or []
        if isinstance(user_candidates,list):
            chosen=next((v for v in user_candidates if v in source),None)
            if chosen:preferred=chosen
    if preferred:
        # A one-point visible callout, not the same three cluttered bullet lists.
        result["features"]=[preferred]
    else:
        result["features"]=[]
    price=verified_price(product)
    if focus=="price":
        amount=price["amount"] or "ON REQUEST"
        vat=(" "+price["vat"]) if price["amount"] else ""
        selling_point=("UK RRP "+amount+vat) if price["amount"] else "PRICE ON REQUEST"
        result["angle"]="Price-led sales promotion based on the verified UK RRP"
    elif preferred:
        selling_point=preferred
        result["angle"]=("Documented workshop benefit" if focus=="benefit"
                          else "Verified product applications and practical workshop use")
    else:
        selling_point=str(product.get("title") or "Laser Tools product")
        result["angle"]=("Manufacturer product overview — no benefit details provided"
                         if focus=="benefit" else
                         "Product application requires manufacturer confirmation")
    result["focus"]=focus
    result["focus_label"]=LABELS[focus]
    result["selling_point"]=selling_point[:175]
    # Do not carry unverified AI subline claims into final artwork. The
    # feature is cut on a whole word boundary, never rewritten or invented.
    if focus=="price":
        result["subline"]=selling_point[:82]
    elif preferred:
        sub=preferred
        if len(sub)>82:
            sub=sub[:83].rsplit(" ",1)[0].rstrip(" ,;:-")
        result["subline"]=sub
    elif not result.get("subline"):
        result["subline"]=str(product.get("title") or "")[:82]
    return result
