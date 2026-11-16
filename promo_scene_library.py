"""Curated, licensed REAL photography for contextual automotive advertisements.

Pexels images have a free commercial-use licence:
https://www.pexels.com/license/
Each entry is a verified photograph of the *context*, never a claim that the
manufacturer's actual tool is being used or endorsed by the photographer.
Never search/download arbitrary URLs supplied by Gemini or the browser.
Real official manufacturer in-situ imagery takes priority where available.
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
import os
import re

import requests
from PIL import Image

# Page IDs correspond to individual Pexels photographs inspected for relevance.
# "battery" shows a car battery with actual red/black jumper cables attached.
SCENE_PHOTOS = {
    "battery": (32282232, 32282233),
    "diagnostic": (8985448, 8986138),
    "brakes": (6870304, 6870299),
    "suspension": (8986101, 31097241),
    "engine": (8985517, 8986138),
    "hand_tools": (8985918, 8985615),
    "press": (5962644, 8985517),
    "welding": (10551343, 13296060),
    "workshop": (8986138, 15489247),
}
SCENE_LABELS = {
    "battery": "Battery service / charging leads",
    "diagnostic": "Vehicle diagnostics",
    "brakes": "Brake maintenance",
    "suspension": "Suspension / undercar service",
    "engine": "Engine service / access",
    "hand_tools": "Hand tools / workshop bench",
    "press": "Workshop machinery",
    "welding": "Automotive welding",
    "workshop": "Vehicle service workshop",
}

# Prioritise the *title*. Broader description terms should not override a
# battery charger simply because its documentation also mentions engine bay.
RULES = (
    ("battery", r"\b(?:battery|batteries|charger|charging|jump[\s-]?start(?:er)?|booster|maintainer|trickle)\b"),
    ("diagnostic", r"\b(?:diagnostic|obd|scanner|code[\s-]?reader|scan tool|multimeter|tester)\b"),
    ("brakes", r"\b(?:brake|caliper|disc|rotor|bleed(?:er|ing)?|clutch[\s&-]+brake)\b"),
    ("suspension", r"\b(?:suspension|strut|shock[\s-]?absorber|hub|bearing|ball joint|tie[\s-]?rod|wheel)\b"),
    ("press", r"\b(?:hydraulic[\s-]?press|workshop[\s-]?press|arbour[\s-]?press|press[\s-]?frame)\b"),
    ("welding", r"\b(?:weld(?:er|ing)?|solder|spot[\s-]?weld|mig|tig)\b"),
    ("engine", r"\b(?:glow[\s-]?plug|injector|pulley|crankshaft|camshaft|timing|engine|cylinder[\s-]?head|valve|turbo|puller|flywheel)\b"),
    ("hand_tools", r"\b(?:ratchet|socket|spanner|wrench|screwdriver|hex[\s-]?key|bit[\s-]?set|torx|pliers)\b"),
)


def classify_product(product: dict) -> str:
    """Choose an advertising *scene*, not a speculative vehicle fitment."""
    name = " ".join(str(product.get(k) or "") for k in ("title","name")).lower()
    detail = " ".join(str(product.get(k) or "") for k in ("description","category")).lower()
    for text in (name, detail[:500]):
        for family, expression in RULES:
            if re.search(expression, text, re.I):
                return family
    return "workshop"


def scene_reference(category: str, variation=0) -> dict:
    """Keep the exact photographer link traceable for commercial review."""
    if category not in SCENE_PHOTOS:
        category = "workshop"
    ids = SCENE_PHOTOS[category]
    asset_id = ids[int(variation)%len(ids)]
    return {
        "category": category,
        "description": SCENE_LABELS[category],
        "source": "Pexels free commercial-use photo",
        "page_url": f"https://www.pexels.com/photo/{asset_id}/",
        "photo_id": asset_id,
        "image_url": f"https://images.pexels.com/photos/{asset_id}/pexels-photo-{asset_id}.jpeg"
                     "?auto=compress&cs=tinysrgb&w=1600",
        "license_url": "https://www.pexels.com/license/",
    }


@lru_cache(maxsize=24)
def _fetch_licensed_photo(asset_id: int) -> bytes | None:
    # Network-free CI: unit tests verify selection without relying on third
    # party uptime. Production still loads actual licensed photographs.
    if os.getenv("DISABLE_STOCK_PHOTOS") == "1":
        return None
    # The domain and ID come only from curated source code constants, never
    # arbitrary URL input. Bound response size, image dimensions and timeout.
    url = f"https://images.pexels.com/photos/{asset_id}/pexels-photo-{asset_id}.jpeg"
    try:
        response = requests.get(url, params={"auto":"compress","cs":"tinysrgb","w":"1400"},
                                timeout=(2.5, 6), allow_redirects=False)
        if response.status_code != 200:
            return None
        if not response.headers.get("content-type","").lower().startswith("image/"):
            return None
        if len(response.content) > 4_000_000:
            return None
        img = Image.open(BytesIO(response.content))
        if img.format not in ("JPEG","PNG","WEBP") or img.width * img.height > 15_000_000:
            return None
        img.verify()
        return response.content
    except (requests.RequestException, ValueError, OSError, SyntaxError):
        return None


def find_scene(product: dict, variation=0, official_photo: bytes | None=None,
               prefer_official=False, category_override=None) -> tuple[bytes|None, dict]:
    category = (category_override if category_override in SCENE_PHOTOS
                else classify_product(product))
    if official_photo and prefer_official:
        return official_photo, {
            "category":category,
            "description":"Actual Laser Tools manufacturer application photograph",
            "source":"Official manufacturer application photo",
            "page_url":str(product.get("application_photo_source") or ""),
            "license_url":None,
        }
    ref=scene_reference(category,variation)
    loaded=_fetch_licensed_photo(ref["photo_id"])
    if loaded:
        return loaded,ref
    if official_photo:
        return official_photo,{
            "category":category,
            "description":"Actual Laser Tools manufacturer application photograph",
            "source":"Official manufacturer application photo",
            "page_url":str(product.get("application_photo_source") or ""),
            "license_url":None,
        }
    # A clean, photographic-style graphic fallback is better than an invented
    # drawing of the product operating or an unrelated automotive photograph.
    return None,{"category":category,"description":"Clean branded background (no verified scene photo loaded)",
                 "source":"No external photograph used","page_url":"","license_url":None}
