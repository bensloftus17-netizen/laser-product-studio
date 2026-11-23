"""V57 creative-direction contract for independently branded Laser campaigns.

AI chooses a bounded family, hierarchy and tone, but never manufacturers'
claims, photos, UK RRP, vehicle fitments or unapproved product silhouettes.
"""
from __future__ import annotations
import re
from difflib import SequenceMatcher
from creative_expression import (
    normalise_expression, PALETTE_NAMES, DEFAULT_POSTER_PALETTE,
)

FAMILIES=(
    "engineering_grid","commercial_burst","premium_spotlight",
    "workshop_motion","editorial_split","toolkit_coverage",
)
ROLES=("technical_application","price_promo","product_selected")
DEFAULT_FAMILY=dict(zip(ROLES,FAMILIES[:3]))
COPY_TONES=("technical","commercial","professional","practical","premium")
HEADLINES=("application","price","benefit","product","kit_contents","feature")
PROOFS=("use_case","verified_spec","value_point","differentiator","kit_contents")
HERO_SIZES=("dominant","balanced","supporting")
PRICE_EMPHASIS=("none","dominant","supporting")
BACKGROUND_MOODS=(
    "structured_workshop","bold_promotion","premium_studio",
    "workshop_action","editorial","organised_kit",
)
ROLE_OPTIONS={
    "technical_application":{
        "copy_tone":"technical","headline_strategy":"application",
        "proof_strategy":"verified_spec","hero_emphasis":"balanced",
        "price_emphasis":"none",
    },
    "price_promo":{
        "copy_tone":"commercial","headline_strategy":"price",
        "proof_strategy":"value_point","hero_emphasis":"supporting",
        "price_emphasis":"dominant",
    },
    "product_selected":{
        "copy_tone":"premium","headline_strategy":"benefit",
        "proof_strategy":"differentiator","hero_emphasis":"dominant",
        "price_emphasis":"supporting",
    },
}
FAMILY_MOOD=dict(zip(FAMILIES,BACKGROUND_MOODS))
FORMAT_PARENTS={
    "social_square":"price_promo",
    "social_story":"price_promo",
    "website_banner":"product_selected",
    "email_header":"technical_application",
    "linkedin_graphic":"technical_application",
    "landscape_ad":"product_selected",
}
# V69: six native outputs have individual format-specific art direction.
# Parent role selects selling point and approved context, NOT a copied poster
# composition. These six visual families are distinct by default.
FORMAT_VISUAL_FAMILIES={
    "social_square":"commercial_burst",
    "social_story":"editorial_split",
    "website_banner":"premium_spotlight",
    "email_header":"toolkit_coverage",
    "linkedin_graphic":"engineering_grid",
    "landscape_ad":"workshop_motion",
}
FORMAT_VISUAL_TREATMENTS={
    "social_square":"bold_geometry",
    "social_story":"split_canvas",
    "website_banner":"cinematic",
    "email_header":"clean_minimal",
    "linkedin_graphic":"technical_infographic",
    "landscape_ad":"photo_editorial",
}
_FORMAT_TREATMENTS=tuple(FORMAT_VISUAL_TREATMENTS.values())


def validate_poster_reference_roles(engines, promo_template):
    """Never let one of the three poster slots inherit another's template.

    The workshop reference supplied by the user is exclusive to poster 02,
    technical poster 01 is always the clean source-backed product sheet, and
    poster 03 must be independently directed. Called before the extra six
    native formats are generated, so a wrong mapping stops immediately.
    """
    if not isinstance(engines,dict):
        raise ValueError("Missing poster render-engine records")
    if engines.get("poster_technical")!="laser-technical-reference":
        raise ValueError("Technical poster reference layout was not retained.")
    workshop_slots=[
        key for key,value in engines.items()
        if value=="laser-workshop-promo-reference"
    ]
    if promo_template=="workshop_showcase":
        if workshop_slots!=["poster_price"]:
            raise ValueError(
                "Workshop reference must be used for the price poster only.")
    elif workshop_slots:
        raise ValueError("Workshop reference was used without selection.")
    if engines.get("poster_smart") in (
        "laser-workshop-promo-reference","laser-technical-reference"):
        raise ValueError("Product-selected poster duplicated a fixed reference.")
    return True


def choose_native_visuals(kind, family=None, treatment=None, used_families=(),
                          used_treatments=()):
    """Retain valid independent AI choices; repair repeated/invalid ones.

    Never changes the model's verified text zones, product source pixels or
    role-specific technical/price/benefit claims. AI style is preferred only
    when it does not make all six formats repeat the same composition.
    """
    if kind not in FORMAT_VISUAL_FAMILIES:
        raise ValueError("Unsupported native campaign format")
    fallback_family=FORMAT_VISUAL_FAMILIES[kind]
    selected_family=family if family in FAMILIES else fallback_family
    if selected_family in used_families:
        selected_family=next(
            (candidate for candidate in (fallback_family,*FAMILIES)
             if candidate not in used_families),fallback_family)
    fallback_treatment=FORMAT_VISUAL_TREATMENTS[kind]
    selected_treatment=(
        treatment if treatment in _FORMAT_TREATMENTS else fallback_treatment)
    if selected_treatment in used_treatments:
        selected_treatment=next(
            (candidate for candidate in (fallback_treatment,*_FORMAT_TREATMENTS)
             if candidate not in used_treatments),fallback_treatment)
    return selected_family,selected_treatment


# Native formats can inherit a different angle when warranted, but the
# distributed campaign always uses all three angles.
ALLOWED_FORMAT_PARENTS={
    "social_square":("price_promo","product_selected"),
    "social_story":("price_promo","product_selected"),
    "website_banner":("product_selected","technical_application"),
    "email_header":("technical_application","product_selected"),
    "linkedin_graphic":("technical_application",),
    "landscape_ad":("product_selected","price_promo"),
}
FAMILY_MODES={
    "engineering_grid":"engineering-precision",
    "commercial_burst":"commercial-impact",
    "premium_spotlight":"hero-spotlight",
    "workshop_motion":"workshop-motion",
    "editorial_split":"minimal-editorial",
    "toolkit_coverage":"engineering-precision",
}


def _choice(value,allowed,default):
    return value if isinstance(value,str) and value in allowed else default


def sanitize_contract(raw,role,*,family=None):
    """Validate AI creative options, never allow unconstrained instructions."""
    if role not in ROLES:
        raise ValueError("Unknown campaign role")
    raw=raw if isinstance(raw,dict) else {}
    default=ROLE_OPTIONS[role]
    selected=_choice(family or raw.get("creative_family"),FAMILIES,DEFAULT_FAMILY[role])
    contract={
        "creative_family":selected,
        "composition_mode":FAMILY_MODES[selected],
        "background_mood":FAMILY_MOOD[selected],
        "copy_tone":_choice(raw.get("copy_tone"),COPY_TONES,default["copy_tone"]),
        "headline_strategy":_choice(
            raw.get("headline_strategy"),HEADLINES,default["headline_strategy"]),
        "proof_strategy":_choice(
            raw.get("proof_strategy"),PROOFS,default["proof_strategy"]),
        "hero_emphasis":_choice(
            raw.get("hero_emphasis"),HERO_SIZES,default["hero_emphasis"]),
        "price_emphasis":_choice(
            raw.get("price_emphasis"),PRICE_EMPHASIS,default["price_emphasis"]),
        **normalise_expression(raw,role=role),
    }
    # Intent is fixed by the server even if Gemini supplies a wrong flag.
    contract["headline_strategy"]=default["headline_strategy"]
    contract["price_emphasis"]=default["price_emphasis"]
    if role=="technical_application":
        contract["proof_strategy"]="use_case" if contract["proof_strategy"]=="use_case" else "verified_spec"
    if role=="price_promo":
        contract["proof_strategy"]="value_point"
    if role=="product_selected" and contract["proof_strategy"]=="value_point":
        contract["proof_strategy"]="differentiator"
    return contract


def diversify_concepts(concepts):
    """Keep AI layout geometry while correcting repeated family selections.

    This is explicitly flagged as a correction; it cannot be misrepresented as
    an original model choice. Family choices are still rendered materially.
    """
    used=set()
    used_colours=set()
    corrected=[]
    for index,concept in enumerate(concepts):
        role=ROLES[index]
        selected=concept.get("creative_direction") or {}
        candidate=sanitize_contract(selected,role)
        family=candidate["creative_family"]
        if family in used:
            available=[f for f in FAMILIES if f not in used]
            wanted=DEFAULT_FAMILY[role]
            family=wanted if wanted in available else available[0]
            candidate=sanitize_contract(selected,role,family=family)
            corrected.append(role)
        used.add(family)
        # Independent art direction must not collapse back into three navy
        # canvases when Gemini repeats its favourite colour choice.
        colour=candidate["creative_palette"]
        if colour in used_colours:
            preferred=DEFAULT_POSTER_PALETTE[role]
            colour=next((p for p in (preferred,*PALETTE_NAMES)
                         if p not in used_colours),colour)
            candidate["creative_palette"]=colour
            if role not in corrected:corrected.append(role)
        used_colours.add(colour)
        concept["creative_direction"]=candidate
        brief=concept.get("creative_canvas")
        if isinstance(brief,dict):
            # Never move AI-authored zones; only alter its safe style choice.
            brief=dict(brief)
            brief["creative_family"]=family
            brief["composition_mode"]=candidate["composition_mode"]
            brief["background_mood"]=candidate["background_mood"]
            for key in ("creative_palette","visual_treatment",
                        "text_treatment","hero_treatment"):
                brief[key]=candidate[key]
            concept["creative_canvas"]=brief
        visual=concept.get("visual_plan")
        if isinstance(visual,dict):
            visual["creative_family"]=family
    return corrected


def choose_format_parents(raw,*,role_families=None):
    """Accept only safe, diverse assignments across the six native formats."""
    assignments={}
    raw=raw if isinstance(raw,dict) else {}
    for kind,default in FORMAT_PARENTS.items():
        value=raw.get(kind)
        assignments[kind]=_choice(value,ALLOWED_FORMAT_PARENTS[kind],default)
    # Any user/model choice still includes technical, price and benefit angles.
    if set(assignments.values())!=set(ROLES):
        assignments=dict(FORMAT_PARENTS)
    return assignments


def source_supported_headline(candidate,product):
    """Accept model wording only if all its meaningful words occur in source.

    Exact source terms, safe conjunctions and simple grammatical rearrangement
    are permitted. No inferred advantages or unsupported action claims.
    """
    if not isinstance(candidate,str):
        return None
    candidate=" ".join(candidate.split()).strip(" -:.,!")[:80]
    if not candidate or len(candidate)>75:
        return None
    record=" ".join(str(x) for x in (
        product.get("title") or "",product.get("description") or "",
        *(product.get("features") or []),
        *(f"{k} {v}" for k,v in (product.get("specs") or {}).items())))
    tokenize=lambda t:set(re.findall(r"[a-z0-9]+",t.lower()))
    words=tokenize(candidate)-{"for","and","the","a","with","of","to","in","on"}
    if not words or not words.issubset(tokenize(record)):
        return None
    if any(hype in candidate.casefold() for hype in
           ("best","ultimate","saving","discount","guarantee","faster")):
        return None
    return candidate


def copy_diversity(concepts):
    """Actionable copy QA; names/part numbers need not differ across posters."""
    issues=[]
    if len(concepts)!=3:
        return ["Missing one of the three marketing angles"]
    roles=[c.get("campaign_role") for c in concepts]
    if roles!=list(ROLES):
        issues.append("Campaign roles are not technical, price and third angle")
    families=[(c.get("creative_direction") or {}).get("creative_family") for c in concepts]
    if len(set(families))<3:
        issues.append("Three posters repeat a creative family")
    proofs=[re.sub(r"\s+"," ",str(c.get("selling_point") or "")).strip().casefold()
            for c in concepts]
    nonempty=[s for s in proofs if s]
    if len(nonempty)>1 and len(set(nonempty))==1:
        issues.append("Every poster repeats the same proof")
    headlines=[str(c.get("headline") or "").strip().casefold() for c in concepts]
    # A product name legitimately appears more than once, but must not be
    # the only headline strategy for the entire campaign.
    if len(set(headlines))==1 and len(set(nonempty))<=1:
        issues.append("All poster text repeats the same campaign message")
    return issues


def layout_diversity(briefs):
    if len(briefs)!=3 or any(not isinstance(b,dict) for b in briefs):
        return ["Three complete creative briefs are required"]
    families=[b.get("creative_family") for b in briefs]
    issues=[]
    if len(set(families))<3:
        issues.append("Creative families are repeated")
    heads=[b["zones"]["headline"] for b in briefs]
    heroes=[b["zones"]["product"] for b in briefs]
    if len({tuple(v) for v in heroes})<2:
        issues.append("Product hero placement is identical in all posters")
    if len({tuple(v) for v in heads})<2:
        issues.append("Headline placement is identical in all posters")
    return issues


def text_similarity(a,b):
    return SequenceMatcher(None,
        re.sub(r"\s+"," ",str(a).lower()),
        re.sub(r"\s+"," ",str(b).lower())).ratio()
