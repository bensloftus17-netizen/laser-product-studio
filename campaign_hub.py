"""One-click, source-grounded Laser Tools distributor campaign packs.

The single call produces promotional posters, native social/web graphics,
channel-specific copy, product data, an optional verified-source QR and a ZIP.
No model can supply a price, photograph, application claim or stock promise.
When Gemini is unavailable, clearly labelled evidence-based concepts are used.
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw, ImageOps
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from ai_promo_renderer import FAMILIES, render_promo, verified_price
from brand_assets import BRAND_LABELS, get_brand_image
from marketing_intelligence import strategy_for
from campaign_strategy import explain_strategy
from poster import font
from promo_copy import compose_promotional_copy
from promo_selling_points import choose_feature, focus_concept

NAVY = "#0A2948"
BLUE = "#006EB8"
CYAN = "#16B1E7"
WHITE = "#FFFFFF"
YELLOW = "#F8C343"
TEXT = "#092A47"
FAMILIES_LABELS = ("Price-led", "Benefit-led", "Application-led")
FOLDERS = {
    "poster_price": "01_Posters/Price-led.png",
    "poster_benefit": "01_Posters/Benefit-led.png",
    "poster_application": "01_Posters/Application-led.png",
    "social_square": "02_Social/Facebook_Instagram_Square.png",
    "social_story": "02_Social/Instagram_Facebook_Story.png",
    "website_banner": "03_Web_Email/Website_Banner.png",
    "email_header": "03_Web_Email/Email_Header.png",
}
ALLOWED_SOURCE_HOSTS = {
    "www.lasertools.co.uk", "lasertools.co.uk",
    "lasertools.toolconnection.co.uk", "www.toolconnection.co.uk",
    "toolconnection.co.uk",
}


def _clean(value, limit=250):
    return " ".join(str(value or "").split())[:limit].rstrip(" ,:-;")


def _approved_source(product):
    value = str(product.get("source") or "").strip()
    url = urlparse(value)
    return value if url.scheme == "https" and url.hostname in ALLOWED_SOURCE_HOSTS else ""


def _render_png(image):
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _text_width(draw, content, size, bold=True):
    bbox = draw.textbbox((0, 0), content, font=font(size, "bold" if bold else "regular"))
    return bbox[2] - bbox[0]


def _wrap_text(draw, content, width, size, bold=True):
    words = str(content or "").replace("\n", " ").split()
    rows, row = [], ""
    for word in words:
        proposed = (row + " " + word).strip()
        if _text_width(draw, proposed, size, bold) <= width:
            row = proposed
            continue
        if row:
            rows.append(row)
            row = ""
        # Also handle unusually long part numbers / single words.
        for char in word:
            if row and _text_width(draw, row + char, size, bold) > width:
                rows.append(row)
                row = char
            else:
                row += char
    if row:
        rows.append(row)
    return rows


def _fitted(draw, text, box, sizes, fill, max_lines=3, bold=True):
    """Measure every line before drawing; ellipsise safely if necessary."""
    x1, y1, x2, y2 = box
    width, height = max(1, x2 - x1), max(1, y2 - y1)
    for size in sizes:
        rows = _wrap_text(draw, text, width, size, bold)
        step = int(size * 1.27)
        if len(rows) <= max_lines and len(rows) * step <= height:
            break
    else:
        size = sizes[-1]
        step = int(size * 1.27)
        allowed = max(1, min(max_lines, height // step))
        rows = _wrap_text(draw, text, width, size, bold)[:allowed]
        if rows:
            original = _wrap_text(draw, text, width, size, bold)
            if len(original) > allowed:
                last = rows[-1]
                while last and _text_width(draw, last + "...", size, bold) > width:
                    last = last[:-1]
                rows[-1] = last.rstrip() + "..."
    for i, line in enumerate(rows):
        draw.text((x1, y1 + i * step), line, font=font(size, "bold" if bold else "regular"), fill=fill)
    return len(rows) * step


def _product_panel(canvas, photo, box):
    x1, y1, x2, y2 = box
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=20, fill=WHITE)
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(photo))).convert("RGBA")
    # Manufacturer pixels stay intact; contain rather than crop or AI-redraw.
    image.thumbnail((max(1, x2 - x1 - 52), max(1, y2 - y1 - 52)), Image.Resampling.LANCZOS)
    px = x1 + (x2 - x1 - image.width) // 2
    py = y1 + (y2 - y1 - image.height) // 2
    canvas.paste(image, (px, py), image)


def _brand(canvas, part, distributor=None, compact=False):
    d = ImageDraw.Draw(canvas)
    size = 43 if compact else 64
    d.text((42, 30), "LASER", font=font(size, "bold"), fill=WHITE)
    d.text((48 + _text_width(d, "LASER", size), 48 if compact else 62),
           "TOOLS", font=font(21 if compact else 26, "bold"), fill=CYAN)
    x = 42 if compact else 52
    d.text((x, 91 if compact else 114), "PART " + _clean(part, 18),
           font=font(18 if compact else 23, "bold"), fill="#D7EFFA")
    if distributor:
        logo = get_brand_image(distributor)
        if logo is not None:
            mark = logo.convert("RGBA")
            mark.thumbnail((190 if compact else 225, 72), Image.Resampling.LANCZOS)
            panel = (canvas.width - mark.width - 36, 34, canvas.width - 22, 44 + mark.height)
            d.rounded_rectangle(panel, radius=8, fill=WHITE)
            canvas.paste(mark, (canvas.width - mark.width - 29, 39), mark)


def _price_line(product):
    info = verified_price(product)
    if not info["amount"]:
        return "PRICE ON REQUEST"
    return "{} {} {}".format(info["label"], info["amount"], info["vat"]).strip()


def _native_graphic(product, photo, distributor, kind, fact):
    """Independent formats with measured typography, not clipped poster crops."""
    sizes = {
        "social_square": (1080, 1080),
        "social_story": (1080, 1920),
        "website_banner": (1600, 600),
        "email_header": (1200, 420),
    }
    width, height = sizes[kind]
    canvas = Image.new("RGBA", (width, height), NAVY)
    d = ImageDraw.Draw(canvas)
    title = _clean(product.get("title"), 150) or "Laser Tools product"
    part = _clean(product.get("part"), 18)
    price = _price_line(product)
    if kind == "social_square":
        d.rectangle((0, 210, width, height), fill=BLUE)
        d.polygon([(0, 1000), (1080, 820), (1080, 1080), (0, 1080)], fill=NAVY)
        _brand(canvas, part, distributor)
        _fitted(d, title, (50, 200, 1025, 370), (64, 56, 48, 42, 36), WHITE, 3)
        _product_panel(canvas, photo, (100, 390, 980, 855))
        d.rounded_rectangle((62, 896, 1015, 1020), radius=10, fill=WHITE)
        _fitted(d, price, (90, 918, 980, 1001), (47, 41, 35, 28, 23), TEXT, 2)
    elif kind == "social_story":
        d.rectangle((0, 200, width, height), fill=BLUE)
        d.polygon([(0, 1620), (1080, 1400), (1080, 1920), (0, 1920)], fill=NAVY)
        _brand(canvas, part, distributor)
        _fitted(d, title, (58, 258, 1022, 515), (81, 72, 60, 52, 44), WHITE, 4)
        _product_panel(canvas, photo, (62, 558, 1018, 1360))
        _fitted(d, fact, (66, 1394, 1007, 1612), (41, 36, 31, 27, 24), WHITE, 4, bold=False)
        d.rounded_rectangle((64, 1655, 1012, 1830), radius=16, fill=WHITE)
        _fitted(d, price, (89, 1702, 990, 1798), (55, 48, 42, 34, 28), TEXT, 2)
        _fitted(d, "DRAFT  /  CHECK PRODUCT DETAILS BEFORE PUBLISHING",
                (72, 1854, 1000, 1893), (21, 18, 16), "#DBE9F2", 1, bold=False)
    else:
        compact = kind == "email_header"
        d.rectangle((0, height - 60, width, height), fill=BLUE)
        _brand(canvas, part, distributor, compact=True)
        left = (45, 160, int(width * 0.54), height - 74)
        title_sizes = (61, 53, 46, 38, 32, 26) if not compact else (44, 38, 32, 27, 22)
        _fitted(d, title, left, title_sizes, WHITE, 3)
        _product_panel(canvas, photo, (int(width * .58), 28, width - 24, height - 86))
        _fitted(d, price, (50, height - 52, width - 50, height - 12),
                (27, 24, 21, 18), WHITE, 1)
    return _render_png(canvas)


def _fallback_concepts(product):
    """Honest rule-based campaign direction when Gemini is down/not configured."""
    title = _clean(product.get("title"), 48).rstrip(" .")
    feature_list = [_clean(f, 175) for f in product.get("features", []) if isinstance(f, str)]
    variants = ("retail", "premium", "trade")
    result = []
    for index, family in enumerate(variants):
        focus = ("price", "benefit", "application")[index]
        proof = choose_feature(product, focus)
        concept = {
            "id": index, "family": family, "variant": index,
            "name": FAMILIES_LABELS[index] + " campaign",
            "headline": title,
            "subline": proof or title,
            "angle": FAMILIES_LABELS[index] + " marketing using the official record",
            "features": [proof] if proof and proof in feature_list else feature_list[:1],
            "part": str(product.get("part") or ""),
            "title": product.get("title"),
            "copy_direction": {"tone":"professional",
                               "hook": ("product", "feature", "application")[index],
                               "cta": "details"},
        }
        result.append(focus_concept(product, concept, index))
    return result


def _concepts(product, use_gemini):
    if use_gemini and os.environ.get("GEMINI_API_KEY", "").strip():
        try:
            from ai_concepts import propose
            found = propose(product)
            if len(found) == 3 and [c.get("family") for c in found] == list(FAMILIES):
                return found, "gemini-assisted", []
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            # Never present deterministic fallback as AI-generated copy.
            return _fallback_concepts(product), "verified-template-fallback", [
                "Gemini unavailable; campaign created with verified product rules. "
                "AI-specific wording was not generated."
            ]
    return _fallback_concepts(product), "verified-template-fallback", [
        "Gemini not configured; this pack uses source-verified marketing rules."
    ]


def _website_copy(product, concept):
    name = _clean(product.get("title"), 180)
    part = _clean(product.get("part"), 18)
    proof = _clean(concept.get("selling_point"), 175)
    if concept.get("focus") == "price":
        proof = choose_feature(product, "benefit")
    return "\n".join(v for v in [
        "Laser Tools " + part + " - " + name,
        proof,
        "Part number: " + part,
        _price_line(product),
        "See official specifications and confirm suitability before ordering.",
    ] if v)


def _copies(product, concepts):
    sets = []
    for index, concept in enumerate(concepts):
        copy = compose_promotional_copy(product, concept)
        copy["website_listing"] = _website_copy(product, concept)
        copy["short_message"] = (
            "Laser Tools " + _clean(product.get("part"), 18) + " - "
            + _clean(product.get("title"), 120) + ". "
            + _price_line(product) + ". Enquire for details."
        )
        copy["campaign_angle"] = FAMILIES_LABELS[index]
        sets.append(copy)
    return sets


def _copy_text(copies):
    items = []
    for copy in copies:
        items.append(
            "=== " + copy["campaign_angle"].upper() + " ===\n\n"
            + "SOCIAL MEDIA\n" + copy["social_caption"] + "\n\n"
            + "LINKEDIN\n" + copy["linkedin_post"] + "\n\n"
            + "EMAIL SUBJECT\n" + copy["email_subject"] + "\n\n"
            + "EMAIL BODY\n" + copy["email_body"] + "\n\n"
            + "HASHTAGS\n" + " ".join(copy["hashtags"]) + "\n\n"
            + "WEBSITE LISTING\n" + copy["website_listing"] + "\n\n"
            + "SHORT / WHATSAPP MESSAGE\n" + copy["short_message"]
        )
    return "\n\n-------------------------------\n\n".join(items) + (
        "\n\nDRAFT ONLY: Validate RRP, VAT, claims, suitability, images, customer brand "
        "permission and company approval before external publication.\n"
    )


def _summary_pdf(product, concepts, manifest):
    file = io.BytesIO()
    document = SimpleDocTemplate(file, pagesize=A4, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("LASER TOOLS | ONE-CLICK CAMPAIGN", styles["Title"]),
        Spacer(1, 12),
        Paragraph("DRAFT FOR COMPANY APPROVAL - NOT FOR AUTOMATIC PUBLICATION", styles["Heading3"]),
        Spacer(1, 8),
    ]
    fields = [
        ("Part number", product.get("part") or ""),
        ("Product", product.get("title") or ""),
        ("Category", manifest["category"]),
        ("Verified price", _price_line(product)),
        ("Source", manifest["source"] or "Not available"),
        ("Distributor", manifest["distributor"] or "Laser Tools only"),
        ("Generation method", manifest["generation_method"]),
    ]
    for k, value in fields:
        story.append(Paragraph("<b>" + escape(k) + ":</b> " + escape(str(value)), styles["Normal"]))
        story.append(Spacer(1, 7))
    story.append(Spacer(1, 12))
    for i, concept in enumerate(concepts):
        story.append(Paragraph(FAMILIES_LABELS[i] + " campaign", styles["Heading2"]))
        story.append(Paragraph(escape(str(concept.get("selling_point", ""))), styles["BodyText"]))
        story.append(Spacer(1, 9))
    strategy = manifest.get("marketing_strategy") or {}
    if strategy:
        story.append(Paragraph("Recommended marketing strategy", styles["Heading2"]))
        for label, value in [
            ("Recommendation method", strategy.get("method_label")),
            ("Suggested target audience", strategy.get("target_audience")),
            ("Main sales angle", strategy.get("primary_focus_label")),
            ("Recommended channels", ", ".join(x.get("label", "") for x in strategy.get("recommended_channels", []))),
            ("Official product evidence", strategy.get("proof_point") or "Feature proof not available"),
            ("Why this approach", strategy.get("reason")),
        ]:
            story.append(Paragraph("<b>" + escape(str(label)) + ":</b> " + escape(str(value or "")), styles["BodyText"]))
            story.append(Spacer(1, 7))
        story.append(Paragraph(
            "The target audience and channel choices are hypotheses for the sales team to validate, not confirmed leads.",
            styles["BodyText"]))
    story.append(Paragraph("Package contents", styles["Heading2"]))
    for path in manifest["files"]:
        story.append(Paragraph(escape(path), styles["Normal"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Review all wording, copyright, product fitment, current price and VAT treatment, "
        "brand-owner permissions and publication approval before using any asset.",
        styles["BodyText"]
    ))
    document.build(story)
    return file.getvalue()


def _source_qr(product):
    source = _approved_source(product)
    if not source:
        return None
    import qrcode
    qr = qrcode.QRCode(border=4, box_size=8, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(source)
    qr.make(fit=True)
    return _render_png(qr.make_image(fill_color="black", back_color="white").convert("RGB"))


def build_campaign(product, genuine_photo, distributor=None, *, use_gemini=True):
    """Return a complete archive plus previewable images and a public manifest.

    Never accept unverified images, pricing or technical claims from the browser.
    The caller must supply a verified official record + genuine manufacturer photo.
    """
    if not genuine_photo:
        raise ValueError("A genuine manufacturer product image is required.")
    if distributor and distributor not in BRAND_LABELS:
        raise ValueError("Unsupported distributor brand.")
    product = dict(product)
    product["marketing_direction"] = strategy_for(product)
    concepts, mode, warnings = _concepts(product, use_gemini)
    ai_choice = (concepts[0].get("ai_strategy_choice")
                 if mode == "gemini-assisted" and concepts else None)
    marketing_strategy = explain_strategy(product, ai_choice)
    image_assets = {}
    for index, concept in enumerate(concepts):
        key = ("poster_price", "poster_benefit", "poster_application")[index]
        image_assets[key] = render_promo(concept, genuine_photo, product, distributor,
                                         editor={"background": "clean",
                                                 "show_subline": True})
    # A specialised vehicle kit should foreground verified application,
    # whereas a socket set or a press needs its category-relevant proof.
    proof = marketing_strategy["proof_point"] or choose_feature(
        product, marketing_strategy["primary_focus"])
    for key in ("social_square", "social_story", "website_banner", "email_header"):
        image_assets[key] = _native_graphic(product, genuine_photo, distributor, key, proof)
    qr = _source_qr(product)
    if qr:
        image_assets["source_qr"] = qr

    copies = _copies(product, concepts)
    files = dict(FOLDERS)
    if qr:
        files["source_qr"] = "05_Product_Info/Official_Product_QR.png"
    file_paths = list(files.values()) + [
        "04_Copy/All_Channels.txt", "04_Copy/All_Channels.json",
        "05_Product_Info/Marketing_Strategy.txt",
        "05_Product_Info/Source_Record.json", "05_Product_Info/Campaign_Summary.pdf",
        "05_Product_Info/READ_FIRST.txt", "Campaign_Manifest.json",
    ]
    manifest = {
        "part": str(product.get("part", "")),
        "title": str(product.get("title", "")),
        "category": product["marketing_direction"].get("category_label", ""),
        "marketing_strategy": marketing_strategy,
        "source": _approved_source(product),
        "distributor": BRAND_LABELS.get(distributor) if distributor else None,
        "price": _price_line(product),
        "generation_method": mode,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "angles": [
            {"name": FAMILIES_LABELS[index], "focus": concept["focus"],
             "headline": str(concept.get("headline") or ""),
             "selling_point": str(concept.get("selling_point") or "")}
            for index, concept in enumerate(concepts)
        ],
        "copy": copies,
        "images": [
            {"id": key, "path": files[key]} for key in image_assets
        ],
        "files": file_paths,
        "warnings": warnings + [
            "All materials are drafts. Validate claims and RRP before publication.",
            "Distributor demo logos require written permission before publication."
            if distributor else "Product images and brand assets need publication approval.",
        ],
        "review_required": True,
    }
    note = (
        "LASER TOOLS ONE-CLICK CAMPAIGN - REVIEW REQUIRED\n\n"
        "The archive contains three distinct poster angles, social graphics, "
        "website/email banners, social/LinkedIn/email/website/WhatsApp copy, "
        "a product summary and the verified manufacturer source.\n\n"
        "The QR code (when included) links ONLY to an official product source.\n"
        "Generation: " + mode + "\n"
        + "\n".join(manifest["warnings"]) + "\n"
        "The ZIP does not publish or schedule any content.\n"
    )
    archive = io.BytesIO()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as z:
        for key, payload in image_assets.items():
            z.writestr(files[key], payload)
        z.writestr("04_Copy/All_Channels.txt", _copy_text(copies))
        z.writestr("04_Copy/All_Channels.json", json.dumps(copies, indent=2, ensure_ascii=False))
        strategy_note = (
            "LASER TOOLS — RECOMMENDED PRODUCT MARKETING STRATEGY (DRAFT)\n\n"
            + "Category: " + marketing_strategy["category_label"] + "\n"
            + "Method: " + marketing_strategy["method_label"] + "\n"
            + "Suggested audience: " + marketing_strategy["target_audience"] + "\n"
            + "Recommended angle: " + marketing_strategy["primary_focus_label"] + "\n"
            + "Recommended channels: " + ", ".join(
                c["label"] for c in marketing_strategy["recommended_channels"]) + "\n"
            + "Official evidence: " + (marketing_strategy["proof_point"] or "Unavailable") + "\n"
            + "Reason: " + marketing_strategy["reason"] + "\n\n"
            + "The audience is not a validated prospect. Review against the manufacturer's "
            "specifications and the sales team's research before external use.\n"
        )
        z.writestr("05_Product_Info/Marketing_Strategy.txt", strategy_note)
        z.writestr("05_Product_Info/Source_Record.json",
                   json.dumps(product, indent=2, ensure_ascii=False, default=str))
        z.writestr("05_Product_Info/READ_FIRST.txt", note)
        z.writestr("05_Product_Info/Campaign_Summary.pdf",
                   _summary_pdf(product, concepts, manifest))
        z.writestr("Campaign_Manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return {"archive": archive.getvalue(), "images": image_assets, "manifest": manifest}
