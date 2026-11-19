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
    return [_clean(v) for v in (product.get("features") or [])
            if isinstance(v,str) and _clean(v)]


def _proof(product,concept,focus):
    """Only source features, never client-submitted/model-invented assertions."""
    facts=_source_features(product)
    selected=concept.get("features") or []
    if focus=="price" and isinstance(selected,list):
        for value in selected:
            if value in facts:
                return value
    # Premium must lead with a benefit, Trade with a documented application.
    # Re-evaluate source facts rather than trusting user-supplied poster data.
    verified=choose_feature(product,focus)
    return verified if verified in facts else (facts[0] if facts else "")


def _price(product):
    details=verified_price(product)
    if not details["amount"]:
        return "Price on request"
    label=details["label"]
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
    # A final language check protects direct calls and older cached product
    # records, not just the normal manufacturer lookup and campaign pipeline.
    from app import normalise_product_language
    product=normalise_product_language(product)
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

    # The three messages now have genuinely different jobs:
    # 1 price / ordering, 2 product benefit, 3 workshop application.
    # Keep the *actual manufacturer claim* intact in every variant.
    tags=_hashtags(product)
    if focus=="price":
        hook=f"Laser Tools {part} | Price and product enquiry"
        social=[short+".",price_line,fact_line,cta]
        linkedin=[hook,short+".",price_line,fact_line,cta]
        email_intro=f"We're sharing the pricing and product details for {ref}."
        subject_prefix="Product and pricing enquiry"
    elif focus=="benefit":
        hook=f"Product detail | {short}"
        social=[fact_line,f"A closer look at {short}.",price_line,cta] if fact_line else [
            f"Take a closer look at {short}.",price_line,cta]
        linkedin=[hook,fact_line,price_line,cta]
        email_intro=f"Here's a closer look at {ref}: {product_name}."
        subject_prefix="Product details"
    else:
        hook=f"Workshop application | {short}"
        social=[f"Workshop applications | {short}.",fact_line,price_line,cta] if fact_line else [
            f"Workshop product information: {short}.",price_line,cta]
        linkedin=[hook,short+".",fact_line,price_line,cta]
        email_intro=f"Please find the manufacturer product information for {ref}."
        subject_prefix="Technical overview"

    if direction["tone"]=="direct" and focus=="price":
        linkedin[0]=f"Laser Tools {part} | Product enquiry"
    elif direction["tone"]=="practical":
        linkedin.append("Check the intended application in the official product information.")

    if direction["hook"]=="feature" and fact_line:
        # The model may reorder only an *existing verified fact*, not write
        # the promotional claim itself.
        social=[fact_line]+[line for line in social if line!=fact_line]
    elif direction["hook"]=="application" and focus=="application":
        social[0]=fact_line or ("Workshop application | "+short+".")

    social_caption="\n".join(line for line in social if line)[:1700]
    linkedin_post="\n\n".join(line for line in linkedin if line) + "\n\n" + " ".join(tags[:4])
    subject=f"{subject_prefix}: Laser Tools {part} | {product_name}"[:110]

    email_body="\n\n".join([
        "Hello,",
        email_intro,
        fact_line,
        price_line,
        f"Please review the official product details and suitability. {cta}",
        "Kind regards,\n[Your name]",
    ] if fact_line else [
        "Hello,",email_intro,price_line,
        f"Please review the official product details and suitability. {cta}",
        "Kind regards,\n[Your name]",
    ])
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
