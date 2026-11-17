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
    "wheel_hub": (13010580, 17429096, 7367864),
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
    "wheel_hub": "Wheel hub / bearing replacement",
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
    ("wheel_hub", r"\b(?:wheel[\s-]?bearing|hub[\s-]?(?:bearing|puller|spreader|assembly|tool)|wheel[\s-]?hub|bearing[\s-]?(?:kit|tool|puller|installation|removal)|knuckle)\b"),
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


# STEP 1 — Product-aware commercial photography.
# Each photo is a real image from a fixed, human-reviewed Pexels page.
# New entries are intentionally conservative: only verified automotive scenes.
# (asset ID, scene name, preferred crop x, crop y)
SCENE_CANDIDATES = {
    "battery": [
        (32282232, "Battery with leads in engine bay", .48, .52),
        (5572260, "Real car battery charging clamps attached", .50, .50),
        (6473244, "Car battery with jump leads in the engine bay", .52, .50),
        (32282233, "Battery terminal connections close-up", .57, .47),
    ],
    "diagnostic": [
        (8985448, "Mechanic using automotive diagnostic equipment", .52, .50),
        (12271948, "Handheld vehicle diagnostic scanner in use", .50, .50),
        (13083209, "Technician working with diagnostic laptop", .50, .47),
        (13065692, "Technician diagnosing vehicle engine", .51, .50),
    ],
    "brakes": [
        (6870304, "Technician working on car brakes", .52, .47),
        (6870299, "Close-up mechanic servicing disc brake", .49, .50),
        (6870300, "Mechanic working on brake assembly", .51, .49),
    ],
    "suspension": [
        (8986101, "Mechanic repairing vehicle undercarriage", .55, .50),
        (8985618, "Mechanic inspecting car underside", .54, .43),
        (8986069, "Technician checking under a raised vehicle", .52, .50),
    ],
    "wheel_hub": [
        (13010580, "Wheel removed showing hub and brake disc", .50, .50),
        (17429096, "Mechanic servicing the vehicle wheel area", .53, .49),
        (7367864, "Car wheel maintenance in a real workshop", .52, .50),
    ],
    "engine": [
        (8985517, "Mechanic lifting car engine", .57, .54),
        (8985519, "Close-up technician working on engine", .52, .50),
        (8985927, "Engine inspection in workshop", .46, .50),
    ],
    "hand_tools": [
        (3855223, "Mechanic selecting sockets from workshop kit", .50, .51),
        (3855334, "Mechanic using socket and ratchet", .51, .49),
        (8985918, "Real automotive tool set on a workbench", .50, .47),
    ],
    "press": [
        (5962644, "Industrial hydraulic press equipment", .49, .48),
        (8985517, "Heavy equipment in automotive workshop", .48, .50),
    ],
    "welding": [
        (10551343, "Mechanic welding automotive components", .50, .51),
        (4489714, "Automotive repair and welding workshop", .52, .47),
    ],
    "workshop": [
        (15489247, "Mechanics at a professional car garage", .51, .50),
        (8985917, "Mechanic in professional workshop", .50, .50),
        (8985517, "Garage workshop machinery", .48, .50),
    ],
}
FAMILY_SCENE_STYLES = {
    # Retail has vivid context, visible in a real-photo band.
    "retail": {"crop_bias":(-.14, .04), "darkness":.16, "blur":2.5, "colour":.94},
    # Premium is slightly defocused with plenty of editorial whitespace.
    "premium":{"crop_bias":(.12,-.07), "darkness":.34, "blur":4.2, "colour":.73},
    # Trade is a darker in-workshop image with clear equipment context.
    "trade":  {"crop_bias":(.03,.08), "darkness":.49, "blur":2.8, "colour":.78},
}


def scene_reference(category: str, variation=0, family=None) -> dict:
    """Choose known real photographs with family-dependent crop and treatment.

    Family changes treatment and crop independently of the part number.
    This prevents three posters with identically composed stock backgrounds.
    """
    if category not in SCENE_CANDIDATES:
        category="workshop"
    family=family if family in FAMILY_SCENE_STYLES else "retail"
    pool=SCENE_CANDIDATES[category]
    # Older integrations can still pass any integer. Rotate across the pool
    # deterministically; never fetch arbitrary user or Gemini URLs.
    index=int(variation)%len(pool)
    asset_id,label,cx,cy=pool[index]
    style=FAMILY_SCENE_STYLES[family]
    bias_x,bias_y=style["crop_bias"]
    x=max(.15,min(.85,cx+bias_x))
    y=max(.15,min(.85,cy+bias_y))
    return {
        "category":category,
        "description":label,
        "scene_type":category,
        "family":family,
        "crop":(round(x,3),round(y,3)),
        "darkness":style["darkness"],
        "blur":style["blur"],
        "colour":style["colour"],
        "source":"Pexels free commercial-use photo",
        "page_url":f"https://www.pexels.com/photo/{asset_id}/",
        "photo_id":asset_id,
        "image_url":f"https://images.pexels.com/photos/{asset_id}/pexels-photo-{asset_id}.jpeg"
                    "?auto=compress&cs=tinysrgb&w=1600",
        "license_url":"https://www.pexels.com/license/",
    }


@lru_cache(maxsize=32)
def _fetch_licensed_photo(asset_id: int) -> bytes | None:
    """Read only our fixed, vetted photo IDs, with bounded downloads."""
    if os.getenv("DISABLE_STOCK_PHOTOS")=="1":
        return None
    allowed={p[0] for pool in SCENE_CANDIDATES.values() for p in pool}
    if asset_id not in allowed:
        return None
    url=f"https://images.pexels.com/photos/{asset_id}/pexels-photo-{asset_id}.jpeg"
    try:
        response=requests.get(url,params={"auto":"compress","cs":"tinysrgb","w":"1400"},
                              timeout=(2.5,6),allow_redirects=False,stream=True)
        if response.status_code!=200:
            response.close();return None
        if not response.headers.get("content-type","").lower().startswith("image/"):
            response.close();return None
        content=bytearray()
        try:
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content)>4_000_000:
                    return None
        finally:
            response.close()
        image=Image.open(BytesIO(content))
        if image.format not in ("JPEG","PNG","WEBP") or image.width*image.height>15_000_000:
            return None
        image.verify()
        return bytes(content)
    except (requests.RequestException,ValueError,OSError):
        return None


def find_scene(product:dict,variation=0,official_photo:bytes|None=None,
               prefer_official=False,category_override=None,family=None)->tuple[bytes|None,dict]:
    """Use authentic application photography when available, else checked stock.

    Descriptions are context, not a claim that a licensed stock image depicts
    the exact Laser tool or demonstrates a product-specific fitment.
    """
    category=category_override if category_override in SCENE_CANDIDATES else classify_product(product)
    family=family if family in FAMILY_SCENE_STYLES else "retail"
    style=FAMILY_SCENE_STYLES[family]
    if official_photo and prefer_official:
        return official_photo,{
            "category":category,
            "description":"Actual Laser Tools manufacturer application photograph",
            "source":"Official manufacturer application photo",
            "page_url":str(product.get("application_photo_source") or ""),
            "license_url":None,"scene_type":category,"family":family,
            "crop":(.5,.5),"darkness":style["darkness"],
            "blur":style["blur"],"colour":style["colour"],
        }
    ref=scene_reference(category,variation,family=family)
    loaded=_fetch_licensed_photo(ref["photo_id"])
    if loaded:
        return loaded,ref
    # No false claims and no invented AI workshop photo if external photo is
    # unavailable. A verified manufacturer image is our safe fallback.
    if official_photo:
        return official_photo,{
            "category":category,
            "description":"Actual Laser Tools manufacturer application photograph",
            "source":"Official manufacturer application photo",
            "page_url":str(product.get("application_photo_source") or ""),
            "license_url":None,"scene_type":category,"family":family,
            "crop":(.5,.5),"darkness":style["darkness"],
            "blur":style["blur"],"colour":style["colour"],
        }
    return None,{
        "category":category,
        "description":"Clean branded artwork (real background unavailable)",
        "source":"No external photograph used",
        "page_url":"","license_url":None,"scene_type":category,
        "family":family,"crop":ref["crop"],"darkness":style["darkness"],
        "blur":style["blur"],"colour":style["colour"],
    }
