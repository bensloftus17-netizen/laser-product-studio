"""Why Choose Laser? Evidence-led, per-part comparison sales sheet (V72).

Only official Laser product facts and product-page verified competitor specifications
are eligible for factual claims. Missing competitor evidence is never interpreted
as a competitor weakness. UK retailer pricing and manufacturer RRP are not
silently compared. Produces a review-labelled one-page-or-more A4 PDF.
"""
from __future__ import annotations

import html
import io
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    KeepTogether, HRFlowable,
)

from competitor_finder import safe_url, safe_image_url

INK = colors.HexColor("#0B2745")
BLUE = colors.HexColor("#006EB9")
PALE = colors.HexColor("#EAF5FD")
MUTED = colors.HexColor("#51677C")
BORDER = colors.HexColor("#D9E6F0")
YELLOW = colors.HexColor("#F5C400")


def _clean(value, limit=240):
    raw = " ".join(str(value or "").split())
    raw = "".join(c for c in raw if ord(c) >= 32)
    return raw[:limit].strip()


def _safe_official(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (not parsed.username and not parsed.password and
            host in ("www.toolconnection.co.uk", "toolconnection.co.uk",
                     "lasertools.toolconnection.co.uk",
                     "www.lasertools.co.uk", "lasertools.co.uk")):
        return url
    return None


def _normal_key(key):
    key = re.sub(r"[^a-z0-9]+", " ", str(key or "").lower()).strip()
    aliases = {
        "number of pieces": "piece count", "pieces": "piece count",
        "no of pieces": "piece count", "piece count": "piece count",
        "weight": "weight", "product weight": "weight",
        "length": "length", "overall length": "length",
        "drive size": "drive size", "square drive": "drive size",
        "maximum capacity": "fluid capacity", "capacity": "fluid capacity",
        "tank capacity": "fluid capacity", "container capacity": "fluid capacity",
        "reservoir capacity": "fluid capacity", "fluid capacity": "fluid capacity",
        "operating pressure": "operating pressure",
        "maximum pressure": "maximum pressure",
        "maximum pressure rating": "maximum pressure",
        "max pressure": "maximum pressure",
        "pressure gauge": "gauge range", "gauge range": "gauge range",
        "euro adaptor neck": "adaptor neck",
        "adapter neck": "adaptor neck", "adaptor neck": "adaptor neck",
    }
    return aliases.get(key, key)


def _strengths(product):
    """Prioritise specific manufacturer features without AI embellishment."""
    facts = []
    for value in product.get("features") or []:
        if not isinstance(value, str):
            continue
        fact = _clean(value, 320)
        if len(fact) < 9 or fact.lower() in {x.lower() for x in facts}:
            continue
        # Avoid bare slogans and source-reference URLs masquerading as facts.
        if fact.startswith(("http://", "https://")):
            continue
        facts.append(fact)
    ranks = (
        (r"\b(?:suitable|compatible|applications?|sprinter|crafter|audi|bmw|mercedes)\b", 5),
        (r"\b(?:include[sd]?|supplied|pieces?|adapters?|heads?|sizes?|bars?)\b", 4),
        (r"\b(?:remove|install|press|test|inspect|repair|adjust|measure|access)\b", 3),
        (r"\b(?:mm|kg|nm|bar|volts?|watts?|lumens?|tonne|mAh)\b", 2),
    )
    def score(feature):
        hits = sum(weight for expression, weight in ranks
                   if re.search(expression, feature, re.I))
        return (-hits, len(feature))
    chosen = sorted(facts, key=score)[:5]
    # The current product title is a genuine official fact but not a feature.
    # Never substitute an invented advantage if manufacturer features are blank.
    return chosen


def _spec_value(value):
    """Normalise only equivalent unit spelling, without unit conversion.

    2L, 2 L and 2 litres are the same published capacity. Never classify a
    different value as an advantage just because its printed format differs.
    """
    text = _clean(value, 100).lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"(\d)\s*lit(?:re|er)s?\b", r"\1 l", text)
    text = re.sub(r"(\d)\s*l\b", r"\1 l", text)
    text = re.sub(r"(\d)\s*psi\b", r"\1 psi", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _official_specs(product):
    """Merge official technical specification fields with literal features.

    Many Tool Connection listings publish fluid capacity and pressures only
    in feature bullets, while the technical table contains only *packaged*
    dimensions. Extract narrowly labelled numeric values without guessing.
    """
    output = {}
    raw = product.get("specs") or {}
    if isinstance(raw, dict):
        for key, value in list(raw.items())[:36]:
            label, detail = _clean(key, 70), _clean(value, 100)
            if (label and detail and not detail.startswith(("http://","https://"))
                and not re.search(r"packaged|barcode|ean|shipping|carton",label,re.I)):
                output[_normal_key(label)] = (label, detail)
    features = " ".join(str(x) for x in product.get("features", [])
                        if isinstance(x, str))
    if re.search(r"\bbrake.{0,45}\bbleed",_clean(product.get("title"),180),re.I):
        checks = (
            ("fluid capacity", r"(\d+(?:\.\d+)?)\s*(?:l|litres?|liters?)\s+(?:capacity|tank|reservoir)",
             "Fluid capacity"),
            ("fluid capacity", r"(?:tank|reservoir|container|fluid)\s+(?:holds?\s+)?(?:capacity\s+)?(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:l|litres?|liters?)\b",
             "Fluid capacity"),
            ("operating pressure", r"operating\s+pressure\s*(?:rating\s*)?(?:of\s*)?(\d+(?:\.\d+)?)\s*psi",
             "Operating pressure"),
            ("maximum pressure", r"max(?:imum)?\s+pressure\s*(?:rating\s*)?(?:of\s*)?(\d+(?:\.\d+)?)\s*psi",
             "Maximum pressure"),
            ("gauge range", r"pressure\s+gauge\s*(?:from\s*)?(\d+\s*[-–]\s*\d+\s*psi)",
             "Gauge range"),
        )
        for key, pattern, label in checks:
            if key not in output:
                m = re.search(pattern,features,re.I)
                if m:
                    detail = m.group(1).strip()
                    if key in ("operating pressure","maximum pressure"):
                        detail+=" psi"
                    elif key=="fluid capacity":
                        detail+=" L"
                    output[key]=(label,detail)
    return output

def _verified_competitor_rows(report, product, max_rows=4):
    rows = []
    laser_specs = _official_specs(product)
    unique_products = set()
    for item in report.get("results") or []:
        if not isinstance(item, dict):
            continue
        # Search-index text, unrelated product classes, and unsupported URLs
        # are leads but cannot be used as verified comparative evidence.
        source = item.get("source_type")
        url = item.get("product_url") or item.get("url")
        if source not in ("retailer/manufacturer page",
                          "manufacturer catalogue reference") or not safe_url(url):
            continue
        brand = _clean(item.get("brand"), 55)
        title = _clean(item.get("title"), 180)
        if not brand or not title or brand == "Manufacturer unverified":
            continue
        status = _clean(item.get("match_status"), 170)
        if "verify" not in status.lower() and "similar" not in status.lower():
            status = "Comparable tool category; fitment and equivalence not proven"
        competitor_specs = item.get("verified_specs") or {}
        if not isinstance(competitor_specs, dict):
            competitor_specs = {}
        normalised = {
            _normal_key(key): (_clean(key, 70), _clean(value, 100))
            for key, value in competitor_specs.items()
            if isinstance(key, str) and isinstance(value, (str, int, float))
            and _clean(key) and _clean(value)
        }
        differences, shared = [], []
        for key, (label, laser_value) in laser_specs.items():
            rival = normalised.get(key)
            if not rival:
                continue
            competitor_value = rival[1]
            claim = {"attribute": label, "laser": laser_value,
                     "competitor": competitor_value,
                     "laser_source": _safe_official(product.get("source")),
                     "competitor_source": url}
            if _spec_value(laser_value) == _spec_value(competitor_value):
                shared.append(claim)
            else:
                differences.append(claim)
        # One manufacturer can have distinct product lines/capacities.
        # Deduplicate exact product URL/SKU, NOT all Draper or Sealey tools.
        product_key=(brand.casefold(),_clean(item.get("part_number") or url,190).casefold())
        if product_key in unique_products:
            continue
        unique_products.add(product_key)
        rows.append({
            "brand": brand, "title": title,
            "part_number": _clean(item.get("part_number"), 60) or None,
            "url": url, "match_status": status,
            # Genuine product photograph, sourced from this exact live
            # competitor listing. Dated catalogue leads have no photo.
            "image_url": (
                item.get("image_url") if
                source=="retailer/manufacturer page" and
                safe_image_url(
                    item.get("image_url"),url)
                else None),
            "evidence_type": ("dated manufacturer catalogue reference"
                              if source=="manufacturer catalogue reference"
                              else "live checked product page"),
            "source_checked_on": _clean(item.get("source_checked_on"),30) or None,
            "comparison_relationship": _clean(item.get("comparison_relationship"),100)
                                       or "Comparable category; technical fit unconfirmed",
            "verified_specifications": len(normalised),
            "published_differences": differences[:2],
            "shared_published_specs": shared[:2],
            "finding": ("Explicit published specification difference"
                        if differences else
                        "Shared published specification"
                        if shared else
                        "Direct technical advantage not established"),
        })
        if len(rows) >= max_rows:
            break
    return rows


def build_why_choose_laser(product, report):
    """Evidence-bearing, JSON-serialisable report for a specific official SKU."""
    part = _clean(product.get("part"), 16).upper()
    if not re.fullmatch(r"[A-Z0-9.-]{3,16}", part):
        raise ValueError("A verified Laser part number is required")
    official = _safe_official(product.get("source"))
    if not official:
        raise ValueError("Official Laser product source URL is required")
    title = _clean(product.get("title"), 190)
    if not title:
        raise ValueError("The official Laser product title is missing")
    if str((report.get("laser") or {}).get("part", "")).upper() != part:
        raise ValueError("Competitor research belongs to a different Laser product")
    if not report.get("checked_at_utc"):
        raise ValueError("A time-stamped competitor research report is required")
    strengths = _strengths(product)
    rivals = _verified_competitor_rows(report, product)
    comparisons = sum(len(r["published_differences"]) for r in rivals)
    return {
        "part": part, "title": title, "manufacturer": "Laser Tools",
        "official_source": official,
        "strengths": [{"text": feature, "source": official, "verified": True}
                      for feature in strengths],
        "competitors": rivals,
        "verified_differences": comparisons,
        "competitors_checked": len(rivals),
        "research_checked_at_utc": str(report["checked_at_utc"]),
        "status": ("Some explicit published differences identified"
                   if comparisons else
                   "No defensible technical superiority claim available"),
        "pricing_note": ("Laser manufacturer's RRP must not be directly "
                         "compared with competitors' retail offers. Pricing "
                         "is deliberately excluded from this sales sheet."),
        "caution": ("Dated manufacturer catalogue references are not live "
                    "stock or price verification. An unpublished competitor "
                    "feature is not evidence that the competitor lacks it. "
                    "Different published specifications "
                    "are not automatically proof of better performance. "
                    "Confirm exact compatibility, date and claims before use."),
        "review_required": True,
        "public_claim_approved": False,
    }


def compact_photo(photo):
    """Cache a small genuine official photo for PDF, not the full source bytes."""
    if not isinstance(photo, (bytes, bytearray)) or not photo or len(photo) > 7_000_000:
        return None
    try:
        with PILImage.open(io.BytesIO(photo)) as image:
            image.load()
            image.thumbnail((620, 400), PILImage.Resampling.LANCZOS)
            frame = PILImage.new("RGB", image.size, "white")
            if image.mode in ("RGBA", "LA"):
                frame.paste(image.convert("RGBA"), mask=image.convert("RGBA").getchannel("A"))
            else:
                frame.paste(image.convert("RGB"))
            target = io.BytesIO()
            frame.save(target, "JPEG", quality=82, optimize=True)
            return target.getvalue() if target.tell() < 250_000 else None
    except (OSError, ValueError):
        return None


def _p(text):
    return xml_escape(_clean(text, 360)).replace("\n", " ")


def _link(url, label):
    if not isinstance(url,str) or not url.startswith("https://"):
        return _p(label)
    return '<link href="' + html.escape(url, quote=True) + '" color="#006EB9">' + _p(label) + '</link>'


def render_why_choose_laser_pdf(sheet, photo_bytes=None):
    """Render the V76 reference-inspired landscape comparison PDF.

    A distinct blue Laser vs red competitor sheet is created for each
    source-checked rival. The engine shares exactly the JSON evidence shown
    in the browser, and never invents methods, images or pricing.
    """
    from why_laser_comparison_poster import render_visual_comparison_pdf
    return render_visual_comparison_pdf(sheet, photo_bytes)
