"""V80: lightweight product-category creative guidance and safe layout recovery.

Only chooses integers / enumerated styles from the existing Pillow renderers.
Does not call AI, load artwork or images, or introduce another render process.
Never edits genuine tool pixels, supplier features, price or VAT.
"""
from __future__ import annotations

import hashlib

# Distinct roles receive different direction, not three recoloured packshots.
# All controls pass through promo_art_direction.normalise_art_direction.
CATEGORY_VISUALS={
 "engine_timing":("industrial-grid","diagonal-bars","circles"),
 "bearing_suspension":("industrial-grid","speed-lines","diagonal-bars"),
 "socket_ratchet":("circles","speed-lines","none"),
 "workshop_press":("industrial-grid","diagonal-bars","none"),
 "diagnostic_electrical":("industrial-grid","speed-lines","circles"),
 "lighting_inspection":("none","speed-lines","circles"),
 "bodyshop_repair":("diagonal-bars","speed-lines","none"),
 "air_power":("industrial-grid","speed-lines","diagonal-bars"),
 "threading_cutting":("industrial-grid","diagonal-bars","none"),
 "workshop_service":("industrial-grid","speed-lines","circles"),
 "accessories_consumables":("none","diagonal-bars","circles"),
 "general_hand_tools":("industrial-grid","speed-lines","none"),
}
ROLE_FOCUS=("right","left","centre")
ROLE_HEADLINE=("small","large","normal")
ROLE_PRICE_STYLE=("panel","sticker","plaque")
ROLE_MOOD=("balanced","bright","dramatic")
ROLE_SCALE=(104,117,109)
ALLOWED_CATEGORIES=frozenset(CATEGORY_VISUALS)


def creative_recipe(category,role,part=""):
    """Three distinctly composed, product-appropriate suggestions.

    Facts are read only from the official product record elsewhere. The same
    part/category/role gives reproducible recommendations with no model call.
    """
    roles=("technical_application","price_promo","product_selected")
    if role not in roles:raise ValueError("Unrecognised campaign role")
    index=roles.index(role)
    kind=category if category in ALLOWED_CATEGORIES else "general_hand_tools"
    # Stable small X/y placement offsets avoid accidental identical geometry
    # across product codes while remaining inside existing bounded controls.
    seed=int.from_bytes(hashlib.sha256(
        (str(part)+"/"+kind).encode("utf-8")).digest()[:2],"big")
    offsets=(-6,0,6)
    return {
        "photo_focus":ROLE_FOCUS[index],
        "product_scale":ROLE_SCALE[index],
        "product_x":offsets[(seed+index)%3],
        "product_y":0,
        "headline_size":ROLE_HEADLINE[index],
        "graphic_motif":CATEGORY_VISUALS[kind][index],
        "background_mood":ROLE_MOOD[index],
        "price_style":ROLE_PRICE_STYLE[index],
        "price_position":"opposite" if index==1 else "standard",
    }


def recovery_variants(first):
    """At most three existing, QA-checked layouts, no extra image batch."""
    if type(first) is not int or first not in (0,1,2):
        raise ValueError("Unknown layout variation")
    return (first,(first+1)%3,(first+2)%3)
