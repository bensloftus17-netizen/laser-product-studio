"""Explainable, product-aware sales strategy with optional *bounded* AI choices.

The business/audience ideas are marketing hypotheses, NOT assertions about
customer demand, suitability, vehicle fitment, value or sales effectiveness.
Only facts taken verbatim from the manufacturer record enter output evidence.
Gemini is permitted to choose among vetted audience/angle/channel/fact IDs,
not to introduce arbitrary factual wording.
"""
from __future__ import annotations

from marketing_intelligence import (PROFILES, detect_category, rank_verified_features,
                                   is_related_product_reference)
from promo_selling_points import choose_feature
from official_taxonomy import category_from_product_url, select_marketing_fact

CHANNELS = {
    "email": {"label": "Targeted product email", "purpose": "Send a concise, relevant product introduction to a researched prospect."},
    "social": {"label": "Distributor social post", "purpose": "Raise product awareness with a genuine product image and verified detail."},
    "linkedin": {"label": "LinkedIn product update", "purpose": "Reach trade and professional buyers with practical product information."},
    "website": {"label": "Website product listing", "purpose": "Help customers check specifications before ordering."},
}
FOCUSES = {
    "price": "Price-led",
    "benefit": "Benefit-led",
    "application": "Application-led",
}
# These are possible sales audiences, not actual qualified prospect records.
AUDIENCE_OPTIONS = {
    "engine_timing": (
        ("engine_repair_workshops", "Engine repair and timing-belt workshops",
         "Engine timing tools address the documented locking and timing procedure."),
        ("marque_specialists", "Workshops specialising in relevant engine families",
         "Confirmed engine codes and vehicle applications matter for this specialist kit."),
        ("tool_distributors", "Automotive tool distributors",
         "Application-led materials help trade buyers check the correct timing kit."),
    ),
    "bearing_suspension": (
        ("commercial_workshops", "Commercial-vehicle repair workshops", "The kit is a specialist wheel-bearing or suspension service tool."),
        ("vehicle_specialists", "Relevant vehicle specialists", "Application details may matter for specialist repair businesses."),
        ("trade_distributors", "Automotive tool distributors", "Distributors can introduce the product to suitable professional customers."),
    ),
    "socket_ratchet": (
        ("independent_garages", "Independent automotive workshops", "Everyday tool sets can be presented through verified sizes and contents."),
        ("tool_distributors", "Tool retailers and mobile tool distributors", "Set contents and presentation are useful for trade product listings."),
        ("fleet_workshops", "Workshop maintenance teams", "Verified specifications may help evaluate the tool set."),
    ),
    "workshop_press": (
        ("workshop_equipment_buyers", "Workshop equipment buyers", "Presses are equipment purchases where confirmed capacity and dimensions matter."),
        ("repair_workshops", "Repair workshops with pressing work", "The actual workshop task and documented capacity guide suitability."),
        ("equipment_distributors", "Workshop equipment distributors", "Technical details can support trade sales conversations."),
    ),
    "diagnostic_electrical": (
        ("diagnostic_workshops", "Diagnostic and electrical specialists", "Verified measurement functions and operating ranges may be relevant."),
        ("independent_garages", "Independent automotive workshops", "The documented diagnostic functions can inform purchase decisions."),
        ("tool_distributors", "Automotive tool distributors", "Product comparisons require confirmed functions and specifications."),
    ),
    "bodyshop_repair": (
        ("bodyshop_workshops", "Body repair workshops", "The tool may address a documented repair application."),
        ("bodyshop_distributors", "Bodyshop supply distributors", "Specific applications can help match products with workshop needs."),
        ("fleet_repair", "Commercial repair operators", "Relevant repair tasks can be checked against product information."),
    ),
    "lighting_inspection": (
        ("independent_garages", "Independent automotive workshops", "Lighting and access features can support a workshop product pitch."),
        ("trade_distributors", "Trade tool distributors", "Verified brightness and run-time information can assist marketing."),
        ("vehicle_maintenance", "Vehicle maintenance teams", "The published functionality informs practical purchasing decisions."),
    ),
    "air_power": (
        ("mechanical_workshops", "Mechanical repair workshops", "Verified drive, torque and tool functions inform suitability."),
        ("trade_distributors", "Trade tool distributors", "Confirmed specifications can support product promotion."),
        ("fleet_workshops", "Fleet maintenance workshops", "Actual tool functions may be relevant to workshop jobs."),
    ),
    "workshop_service": (
        ("service_workshops", "Vehicle servicing workshops", "The documented servicing task is central to the purchase decision."),
        ("fleet_workshops", "Fleet service teams", "Capacity and service-application information may be useful."),
        ("trade_distributors", "Automotive tool distributors", "Product information can support relevant trade offers."),
    ),
    "threading_cutting": (
        ("mechanical_workshops", "Mechanical repair workshops", "Verified tool sizes and contents guide workshop selection."),
        ("trade_distributors", "Trade tool distributors", "Included sizes and set contents support a product listing."),
    ),
    "accessories_consumables": (
        ("trade_distributors", "Automotive parts and tool distributors", "Quantity, size and availability checks support ordering."),
        ("repair_workshops", "Repair workshops", "The confirmed part specification should drive suitability."),
    ),
    "general_hand_tools": (
        ("independent_garages", "Independent automotive workshops", "Confirmed dimensions and applications help assess suitability."),
        ("tool_distributors", "Tool retailers and distributors", "The real tool image and specified features support a product listing."),
    ),
}
DEFAULT_FOCUS = {
    "engine_timing": "application",
    "bearing_suspension": "application",
    "socket_ratchet": "benefit",
    "workshop_press": "benefit",
    "diagnostic_electrical": "benefit",
    "bodyshop_repair": "application",
    "lighting_inspection": "benefit",
    "air_power": "benefit",
    "workshop_service": "application",
    "threading_cutting": "benefit",
    "accessories_consumables": "price",
    "general_hand_tools": "benefit",
}
DEFAULT_CHANNELS = {
    "engine_timing": ("email", "website"),
    "bearing_suspension": ("email", "linkedin"),
    "socket_ratchet": ("social", "email"),
    "workshop_press": ("email", "website"),
    "diagnostic_electrical": ("email", "linkedin"),
    "bodyshop_repair": ("email", "social"),
    "lighting_inspection": ("social", "email"),
    "air_power": ("social", "email"),
    "workshop_service": ("email", "social"),
    "threading_cutting": ("social", "email"),
    "accessories_consumables": ("website", "social"),
    "general_hand_tools": ("social", "email"),
}


def _verified_features(product):
    features = []
    is_timing = detect_category(product)[0] == "engine_timing"
    for raw in (product.get("features") or [])[:12]:
        if not isinstance(raw, str):
            continue
        fact = " ".join(raw.strip().split())[:175]
        if is_timing and is_related_product_reference(fact):
            # Related Laser products are valid reference notes but not
            # the core marketing evidence for the timing kit itself.
            continue
        if fact and fact not in features:
            features.append(fact)
    return features


def _official_classification(product):
    return product.get("official_taxonomy") or category_from_product_url(
        product.get("source"), product.get("part"))


def strategy_options(product):
    """Only these options may be selected by a model for this product."""
    category, evidence = detect_category(product)
    official = _official_classification(product)
    if official:
        audiences = [
            {"id": "category_audience_"+str(i), "label": name,
             "reason": official["marketing"]["reason"]}
            for i, name in enumerate(official["marketing"]["audiences"])
        ]
    else:
        audiences = [
            {"id": code, "label": label, "reason": reason}
            for code, label, reason in AUDIENCE_OPTIONS.get(
                category, AUDIENCE_OPTIONS["general_hand_tools"])
        ]
    return {
        "category": category,
        "category_label": (official["breadcrumb"] if official else PROFILES[category]["label"]),
        "category_evidence": evidence,
        "official_category": official,
        "audiences": audiences,
        "focus_options": list(FOCUSES),
        "channel_options": [{"id": name, "label": details["label"]}
                            for name, details in CHANNELS.items()],
        "proof_options": [{"index": i, "verified_manufacturer_fact": fact}
                          for i, fact in enumerate(_verified_features(product))],
    }


def explain_strategy(product, ai_choice=None):
    """Build source-based strategy; ignore all unconstrained model claims."""
    options = strategy_options(product)
    category = options["category"]
    official = options.get("official_category")
    lens = (official or {}).get("marketing") or {}
    audiences = options["audiences"]
    facts = _verified_features(product)
    source = product.get("source") or ""
    default_focus = lens.get("focus") or DEFAULT_FOCUS[category]
    recommended_fact = (
        select_marketing_fact(product, facts, lens) if lens
        else choose_feature(product, default_focus)
    )
    index = facts.index(recommended_fact) if recommended_fact in facts else 0

    choice = ai_choice if isinstance(ai_choice, dict) else {}
    valid_ai_audience = (
        isinstance(choice.get("audience_id"), str)
        and choice["audience_id"] in {a["id"] for a in audiences}
    )
    valid_ai_focus = (
        isinstance(choice.get("primary_focus"), str)
        and choice["primary_focus"] in FOCUSES
    )
    valid_ai_proof = type(choice.get("proof_index")) is int and 0 <= choice["proof_index"] < len(facts)
    raw_channels = choice.get("channels")
    valid_ai_channels = (
        isinstance(raw_channels, list) and len(raw_channels) == 2
        and len(set(str(x) for x in raw_channels)) == 2
        and all(isinstance(x, str) and x in CHANNELS for x in raw_channels)
    )
    accepted = all((valid_ai_audience, valid_ai_focus, valid_ai_proof, valid_ai_channels))
    if accepted:
        audience = next(a for a in audiences if a["id"] == choice["audience_id"])
        focus = choice["primary_focus"]
        index = choice["proof_index"]
        channels = list(raw_channels)
    else:
        audience = audiences[0]
        focus = default_focus
        channels = list(lens.get("channels") or DEFAULT_CHANNELS[category])

    # Do not claim verified pricing when missing. This affects the actual
    # campaign emphasis, not just dashboard wording.
    if focus == "price" and not product.get("price"):
        focus = "benefit"
    proof = facts[index] if facts else ""
    if focus == "application":
        chosen = choose_feature(product, "application")
        if chosen and chosen not in facts:
            chosen = ""
        if chosen and any(t in chosen.lower() for t in ("sprinter", "crafter", "mercedes", "volkswagen", "vw", "application", "vehicle", "fit", "compatible")):
            proof = chosen
        elif not facts:
            proof = ""
    if lens and not accepted and facts:
        proof = select_marketing_fact(product, facts, lens)
    if not proof:
        ranked = rank_verified_features(product, category, 1)
        proof = ranked[0] if ranked else ""

    channel_details = [{"id": c, **CHANNELS[c]} for c in channels]
    why = (
        (lens.get("reason") or audience["reason"]) + " Recommend " + FOCUSES[focus].lower()
        + " content using a manufacturer-supplied fact, then lead with "
        + " and ".join(CHANNELS[c]["label"].lower() for c in channels) + "."
    )
    return {
        "category": category,
        "category_label": options["category_label"],
        "category_evidence": options["category_evidence"],
        "official_category_path": official["path"] if official else [],
        "official_category_source": official["source"] if official else None,
        "marketing_lens": {"id": lens.get("id"), "label": lens.get("label"),
                           "reason": lens.get("reason")} if lens else None,
        "method": "gemini-validated-choice" if accepted else "category-rules-fallback",
        "method_label": (
            "Gemini-selected from verified options"
            if accepted else "Product-aware verified-source recommendation"
        ),
        "target_audience": audience["label"],
        "audience_id": audience["id"],
        "audience_status": "Suggested audience — research and sales-team validation required",
        "primary_focus": focus,
        "primary_focus_label": FOCUSES[focus],
        "recommended_channels": channel_details,
        "proof_point": proof,
        "reason": why,
        "evidence": {
            "manufacturer_part": str(product.get("part") or ""),
            "manufacturer_title": str(product.get("title") or ""),
            "product_category_derived_from": options["category_evidence"],
            "proof_from_manufacturer_features": bool(proof),
            "source": str(source),
        },
        "review_required": True,
    }
