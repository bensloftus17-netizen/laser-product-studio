"""AI-assisted promotional copy for Laser Tools poster campaigns.

One existing Gemini request selects feature IDs, campaign focus and copy tone;
this module turns those validated choices into ready-to-edit marketing drafts.
Every technical statement is copied verbatim from the manufacturer's verified
features. No invented vehicle fitments, promotions, prices, website URLs or
performance claims. No extra paid API request.
"""
from __future__ import annotations

import re

from ai_promo_renderer import verified_price
from promo_scene_library import classify_product
from promo_selling_points import choose_feature

TONE_CHOICES=("direct","practical","professional")
HOOK_CHOICES=("product","application","feature")
CTA_CHOICES=("details","enquire","specifications")
FAMILY_FOCUS={"retail":"price","premium":"benefit","trade":"application"}
CATEGORY_TAGS={
    "battery":("#BatteryCharging","#BatteryMaintenance"),
    "diagnostic":("#VehicleDiagnostics","#DiagnosticTools"),
    "brakes":("#BrakeService","#BrakeTools"),
    "wheel_hub":("#WheelBearingTools","#HubService"),
    "suspension":("#SuspensionTools","#VehicleMaintenance"),
    "engine":("#EngineTools","#EngineService"),
    "hand_tools":("#HandTools","#SocketSets"),
    "press":("#WorkshopEquipment","#HydraulicPress"),
    "welding":("#WeldingTools","#VehicleRepair"),
    "workshop":("#WorkshopTools","#AutomotiveTools"),
}
CTA_LINES={
    "details":"See the full product details before ordering.",
    "enquire":"Ask for more information about this part number.",
    "specifications":"Review the full product specifications and applications.",
}


def _clean(value,limit=185):
    return " ".join(str(value or "").split())[:limit].rstrip(" ,;:-")


def normalise_copy_direction(raw):
    """Constrain optional Gemini writing choices. Reject arbitrary model claims."""
    if not isinstance(raw,dict):
        raw={}
    return {
        "tone":raw.get("tone") if raw.get("tone") in TONE_CHOICES else "professional",
        "hook":raw.get("hook") if raw.get("hook") in HOOK_CHOICES else "product",
        "cta":raw.get("cta") if raw.get("cta") in CTA_CHOICES else "details",
    }


def _source_features(product):
    return [_clean(v) for v in product.get("features",[])
            if isinstance(v,str) and _clean(v)]


def _proof(product,concept,focus):
    """Only source features, never client-submitted/model-invented assertions."""
    facts=_source_features(product)
    selected=concept.get("features") or []
    if isinstance(selected,list):
        for value in selected:
            if value in facts:
                return value
    verified=choose_feature(product,focus)
    return verified if verified in facts else (facts[0] if facts else "")


def _price(product):
    details=verified_price(product)
    if not details["amount"]:
        return "Price on request"
    label=details["label"].title()
    vat=details["vat"]
    vat_label={
        "EX VAT":"ex VAT",
        "INC VAT":"inc VAT",
        "VAT STATUS TO CONFIRM":"VAT status to confirm",
    }.get(vat,"VAT status to confirm")
    return f"{label}: {details['amount']} ({vat_label})"


def _hashtags(product):
    category=classify_product(product)
    tags=["#LaserTools","#AutomotiveTools"]
    tags.extend(CATEGORY_TAGS.get(category,CATEGORY_TAGS["workshop"]))
    # Vehicle brands are only included if verified in the product title or
    # original manufacturer features; not from AI-generated headlines.
    evidence=" ".join([_clean(product.get("title"))]+_source_features(product)).lower()
    verified_brands=(
        ("land rover","#LandRover"),
        ("jaguar","#Jaguar"),
        ("volkswagen","#Volkswagen"),
        ("mercedes","#MercedesBenz"),
        ("ford","#Ford"),
        ("bmw","#BMW"),
        ("audi","#Audi"),
    )
    for name,tag in verified_brands:
        if re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",evidence):
            tags.append(tag)
            break
    tags.append("#WorkshopTools")
    return list(dict.fromkeys(tags))[:6]


def compose_promotional_copy(product,concept):
    """Return copy for all four channels after the poster concept is validated.

    The hook and tone come from Gemini's existing concept call; factual claims
    and price are regenerated from the official/current reviewed product
    record so no client-supplied values can forge marketing claims.
    """
    product_name=_clean(product.get("title"),145) or "Laser Tools product"
    part=_clean(product.get("part"),22)
    family=str(concept.get("family") or "retail")
    focus=FAMILY_FOCUS.get(family,"price")
    direction=normalise_copy_direction(concept.get("copy_direction"))
    fact=_proof(product,concept,focus)
    price=_price(product)
    cta=CTA_LINES[direction["cta"]]
    ref=f"Laser Tools part {part}" if part else "This Laser Tools product"
    short=f"{product_name} | Part {part}" if part else product_name
    fact_line=(fact.rstrip(".")+"." if fact else "")
    price_line=price.rstrip(".")+"."

    # The three families lead with different verified evidence, not simply
    # the same caption reworded three times.
    if focus=="price":
        social=[short+".",price_line]
        if fact_line:social.append(fact_line)
        social.append(cta)
        linkedin=[
            f"Product spotlight: {short}",
            price_line,
        ]
        if fact_line:linkedin.append(fact_line)
        linkedin.append(cta)
    elif focus=="benefit":
        social=[f"On the bench: {short}."]
        if fact_line:social.append(fact_line)
        social.extend([price_line,cta])
        linkedin=[f"Workshop product spotlight — {short}"]
        if fact_line:linkedin.append(fact_line)
        linkedin.extend([price_line,cta])
    else:
        social=[f"For workshop applications: {short}."]
        if fact_line:social.append(fact_line)
        social.extend([price_line,cta])
        linkedin=[f"Workshop applications | {short}"]
        if fact_line:linkedin.append(fact_line)
        linkedin.extend([price_line,cta])

    if direction["tone"]=="direct":
        linkedin[0]=linkedin[0].replace("Product spotlight:","Laser Tools |")
    elif direction["tone"]=="practical":
        linkedin.append("Check the product information for the intended application.")

    tags=_hashtags(product)
    social_caption="\n".join(social[:5])
    linkedin_post="\n\n".join(linkedin[:5])+"\n\n"+" ".join(tags[:4])
    subject=f"Laser Tools {part} | {product_name}"[:110] if part else product_name[:110]

    body=[
        "Hello,",
        f"We're highlighting {ref}: {product_name}.",
    ]
    if fact_line:body.append(fact_line)
    body.extend([
        price_line,
        f"Please review the product details and suitability for your customers. {cta}",
        "Kind regards,\n[Your name]",
    ])
    email_body="\n\n".join(body)
    return {
        "social_caption":social_caption,
        "linkedin_post":linkedin_post,
        "email_subject":subject,
        "email_body":email_body,
        "hashtags":tags,
        "source_claims":[fact] if fact else [],
        "focus":focus,
        "review_required":True,
        "generated_with":"Gemini-directed structure and verified manufacturer content",
    }
