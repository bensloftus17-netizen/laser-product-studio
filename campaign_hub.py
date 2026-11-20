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
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

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
from campaign_director import plan_campaign, POSTER_LABELS, ROLES
from campaign_role_posters import technical_poster, smart_poster
from campaign_art_quality import choose_best, campaign_consistency, photo_relevance
from creative_director import distinct_briefs
from creative_families import (
    diversify_concepts, choose_format_parents, copy_diversity,
    DEFAULT_FAMILY, FORMAT_PARENTS,
)
from creative_expression import (
    express_background, format_palette, DEFAULT_FORMAT_PALETTE,
)
from flexible_canvas import render_creative_canvas
from workshop_promo_template import (
    render_workshop_showcase,validate_promo_template,
)
from asset_quality import require_good_asset
from campaign_distinctness import check_distinctness
from creative_qa import review_finished_artworks, reconcile_with_measured_geometry
from format_creative import (FORMAT_ORDER, validate_format_canvas,
                             generate_format,quality_check_safe_native)
from product_evidence_ranker import verified_candidates
from promo_scene_library import find_scene, classify_product

NAVY = "#0A2948"
BLUE = "#006EB8"
CYAN = "#16B1E7"
WHITE = "#FFFFFF"
YELLOW = "#F8C343"
TEXT = "#092A47"
FAMILIES_LABELS = POSTER_LABELS
FOLDERS = {
    "poster_technical": "01_Posters/01_Application_Technical.png",
    "poster_price": "01_Posters/02_Price_Promotion.png",
    "poster_smart": "01_Posters/03_Product_Selected.png",
    "social_square": "02_Social/Facebook_Instagram_Square.png",
    "social_story": "02_Social/Instagram_Facebook_Story.png",
    "website_banner": "03_Web_Email/Website_Banner.png",
    "email_header": "03_Web_Email/Email_Header.png",
    "linkedin_graphic": "02_Social/LinkedIn_Graphic.png",
    "landscape_ad": "03_Web_Email/Landscape_Advert.png",
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
    image.convert("RGB").save(buffer, format="PNG", optimize=False,compress_level=3)
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
    """Use the genuine product cutout in every Story, banner and social image.

    Prior versions inserted the uncut white packshot in a giant white card.
    The image now sits directly on the coloured/real-photo composition.
    """
    from campaign_art_quality import inspected_product
    from PIL import ImageFilter
    x1,y1,x2,y2=box
    details=inspected_product(photo)
    image=details["rgba"].copy()
    max_w=max(1,x2-x1-36)
    max_h=max(1,y2-y1-36)
    scale=min(max_w/max(1,image.width),max_h/max(1,image.height))
    image=image.resize((max(1,round(image.width*scale)),
                        max(1,round(image.height*scale))),Image.Resampling.LANCZOS)
    px=x1+(x2-x1-image.width)//2
    py=y1+(y2-y1-image.height)//2
    if not details["isolated"]:
        d=ImageDraw.Draw(canvas)
        d.rounded_rectangle((px-11,py-11,px+image.width+11,py+image.height+11),
                            radius=13,fill="#133A59",outline="#5596B7",width=2)
    else:
        shadow=Image.new("RGBA",image.size,(1,16,32,0))
        shadow.putalpha(image.getchannel("A").filter(
            ImageFilter.GaussianBlur(13)).point(lambda v:int(v*.31)))
        canvas.alpha_composite(shadow,(px+6,py+9))
    canvas.alpha_composite(image,(px,py))


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


def _native_graphic(product, photo, distributor, kind, fact, scene=None,
                    visual_plan=None,creative_family=None,headline=None,
                    creative_palette=None,visual_treatment="bold_geometry"):
    """Product-specific stories and banners with genuine workshop context.

    Supporting photography is curated or approved; original tool image is
    presented separately, never AI-redrawn or represented as a documented
    demonstration.
    """
    sizes = {
        "social_square": (1080, 1080),
        "social_story": (1080, 1920),
        "website_banner": (1600, 600),
        "email_header": (1200, 420),
        "linkedin_graphic": (1200, 627),
        "landscape_ad": (1600, 900),
    }
    width, height = sizes[kind]
    canvas = Image.new("RGBA", (width, height), NAVY)
    if scene:
        try:
            from PIL import ImageEnhance, ImageFilter
            actual = Image.open(io.BytesIO(scene)).convert("RGB")
            actual.thumbnail((1900,1900),Image.Resampling.LANCZOS)
            region = (
                (0,190,width,height) if kind=="social_square" else
                (0,250,width,1610) if kind=="social_story" else
                (width//2,0,width,height)
            )
            sx,sy,ex,ey=region
            contextual=ImageOps.fit(actual,(ex-sx,ey-sy),Image.Resampling.LANCZOS)
            contextual=ImageEnhance.Brightness(contextual).enhance(.47)
            contextual=contextual.filter(ImageFilter.GaussianBlur(1.6))
            canvas.paste(contextual,(sx,sy))
        except (OSError,ValueError):
            pass
    if creative_family:
        from format_creative import draw_family_background
        canvas=draw_family_background(canvas,creative_family)
    if creative_palette:
        # The fallback must retain the AI's parent campaign direction and
        # contrast-safe colour language; it is NOT passed off as AI-original.
        if kind=="social_square":
            safe={"headline":(50,200,1025,370),"price":(62,896,1015,1020)}
        elif kind=="social_story":
            safe={"headline":(58,258,1022,515),
                  "proof":(66,1394,1007,1612),
                  "price":(64,1655,1012,1830)}
        else:
            safe={"headline":(45,160,int(width*.54),height-74)}
        canvas=express_background(
            canvas,creative_palette,visual_treatment,zones=safe,inplace=True)
    d = ImageDraw.Draw(canvas)
    title = _clean(product.get("title"), 150) or "Laser Tools product"
    # Verified source-title excerpt prevents tiny ellipsised fallback copy.
    # The SKU is also displayed separately and unchanged in the brand bar.
    if len(title)>58:
        from campaign_director import _headline
        title=_headline(product,"price_promo",None,None)
    if headline:
        # This headline is source-filtered during campaign planning.
        title=_clean(headline,82)
    part = _clean(product.get("part"), 18)
    price = _price_line(product)
    if kind == "social_square":
        if not scene and not creative_palette:
            d.rectangle((0, 210, width, height), fill=BLUE)
        d.polygon([(0, 1000), (1080, 820), (1080, 1080), (0, 1080)], fill=NAVY)
        _brand(canvas, part, distributor)
        _fitted(d, title, (50, 200, 1025, 370), (64, 56, 48, 42, 36), WHITE, 3)
        _product_panel(canvas, photo, (100, 390, 980, 855))
        d.rounded_rectangle((62, 896, 1015, 1020), radius=13,
                            fill="#092C4A",outline="#42ABD9",width=3)
        _fitted(d, price, (90, 918, 980, 1001),
                (47, 41, 35, 28, 23), WHITE, 2)
    elif kind == "social_story":
        if not scene and not creative_palette:
            d.rectangle((0, 200, width, height), fill=BLUE)
        d.polygon([(0, 1620), (1080, 1400), (1080, 1920), (0, 1920)], fill=NAVY)
        _brand(canvas, part, distributor)
        _fitted(d, title, (58, 258, 1022, 515), (81, 72, 60, 52, 44), WHITE, 4)
        _product_panel(canvas, photo, (62, 558, 1018, 1360))
        _fitted(d, fact, (66, 1394, 1007, 1612), (41, 36, 31, 27, 24), WHITE, 4, bold=False)
        d.rounded_rectangle((64, 1655, 1012, 1830), radius=16,
                            fill="#092C4A",outline="#5CCBE8",width=4)
        _fitted(d, price, (89, 1702, 990, 1798),
                (55, 48, 42, 34, 28), WHITE, 2)
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
        copy["campaign_angle"] = concepts[index].get("name") or FAMILIES_LABELS[index]
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


def build_campaign(product, genuine_photo, distributor=None, *, use_gemini=True,
                   application_photo=None, progress=None,
                   promo_template="workshop_showcase",spill_archive=False):
    """Return a complete archive plus previewable images and a public manifest.

    Never accept unverified images, pricing or technical claims from the browser.
    The caller must supply a verified official record + genuine manufacturer photo.
    """
    def _emit(stage, asset_id=None, payload=None, report=None):
        # Only server-trusted render bytes pass through this callback. In
        # particular, "ready" is emitted AFTER all required poster reviews,
        # campaign distinctness checks, and format-specific QA have passed.
        if progress is not None:
            progress(stage,asset_id,payload,report)

    if not genuine_photo:
        raise ValueError("A genuine manufacturer product image is required.")
    promo_template=validate_promo_template(promo_template)
    _emit("planning")
    if distributor and distributor not in BRAND_LABELS:
        raise ValueError("Unsupported distributor brand.")
    # Final defence even when a caller passes a previously cached record or
    # bypasses the normal lookup. The same English-only facts then reach all
    # posters, Gemini planning, channel copy, stories, banners and the ZIP.
    from app import normalise_product_language
    product = normalise_product_language(product)
    product["marketing_direction"] = strategy_for(product)
    raw_concepts, mode, warnings = _concepts(product, use_gemini)
    ai_choice = (raw_concepts[0].get("ai_strategy_choice")
                 if mode == "gemini-assisted" and raw_concepts else None)
    marketing_strategy = explain_strategy(product, ai_choice)
    # The three posters are *always* technical, commercial and a third angle
    # selected for the actual product. Their layouts are not variations of one
    # general-purpose poster template.
    concepts, creative_plan = plan_campaign(
        product, raw_concepts if mode == "gemini-assisted" else [], marketing_strategy)
    corrected_families=diversify_concepts(concepts)
    if corrected_families:
        warnings.append(
            "Gemini repeated creative families. The artwork director assigned "
            "unused brand-safe families for "+", ".join(corrected_families)+
            "; original AI product/text positions were retained.")
    creative_plan["family_corrections"]=corrected_families
    creative_plan["creative_families"]=[
        c["creative_direction"]["creative_family"] for c in concepts]
    creative_enabled=(mode=="gemini-assisted" and
                      distinct_briefs([c.get("creative_canvas") for c in concepts]))
    if mode=="gemini-assisted" and not creative_enabled:
        warnings.append(
            "AI did not provide three safe, genuinely different freeform compositions; "
            "used validated legacy layouts instead. Regenerate for AI creative direction.")
    asset_report=require_good_asset(genuine_photo) if creative_enabled else None
    creative_plan["render_engine"]=(
        "ai-authored-freeform-layout" if creative_enabled else "verified-legacy-layout")
    creative_plan["promo_template"]=promo_template
    creative_plan["promo_reference"]="user-supplied workshop showcase" if promo_template=="workshop_showcase" else "AI original composition"
    creative_plan["model_authored_canvases"]=(
        [concept.get("creative_canvas") for concept in concepts]
        if creative_enabled else [])
    duplicate_issues = campaign_consistency(concepts)+copy_diversity(concepts)
    if duplicate_issues:
        raise ValueError("Campaign needs different sales messages: "+
                         "; ".join(duplicate_issues))
    _emit("finding_context")
    scenes = []
    scene_references = []
    for index, concept in enumerate(concepts):
        visual=concept["visual_plan"]
        # The model may select an angle but NEVER an arbitrary photo URL.
        # Scene choices come from fixed, licensed photography and, where
        # available, an official genuine product application photograph.
        picture, ref = find_scene(
            product,variation=visual["scene_index"],
            official_photo=application_photo,
            prefer_official=(index in (0,2) and bool(application_photo)),
            category_override=visual["scene_category"],
            family=concept["family"])
        match=photo_relevance(product,visual["scene_category"],ref)
        if not match["supported"]:
            # Source appears unrelated to this product category. Using no
            # context photograph is preferable to an irrelevant stock scene.
            picture=None
            ref={"category":visual["scene_category"],
                 "description":"Branded background (irrelevant photo rejected)",
                 "source":"No external photograph used","page_url":"","license_url":None}
        scenes.append(picture)
        scene_references.append({
            "role":concept["campaign_role"],
            "category":ref.get("category"),"description":ref.get("description"),
            "source":ref.get("source"),"page_url":ref.get("page_url"),
            "license_url":ref.get("license_url"),
            "note":"Context photo, not evidence of this exact tool in use.",
            "relevance_score":match["score"],
            "relevance_warning":match["warning"],
        })
    _emit("rendering_posters")
    image_assets = {}
    quality_reports = {}
    # Real variant selection. Test 3 distinct creative compositions per role;
    # reject large white zones, unreadable text, damaged PNGs and low contrast.
    # All candidates reuse the same verified product pixels and scene sources.
    from poster_quality import capture

    def _geometry(tracked, *, measured_text=False):
        from poster_quality import _overlap
        texts=[t for t in tracked.texts if str(t.get("text") or "").strip()]
        main=[t for t in texts if t.get("role")=="headline"]
        overlaps=any(
            other is not title and _overlap(title["box"],other["box"])>
                .27*min(
                    (title["box"][2]-title["box"][0])*
                    (title["box"][3]-title["box"][1]),
                    (other["box"][2]-other["box"][0])*
                    (other["box"][3]-other["box"][1]))
            for title in main for other in texts
        )
        return {
            "truncated": any(t["truncated"] for t in texts),
            "out_of_bounds": any(
                t["box"][0]<0 or t["box"][1]<0 or t["box"][2]>1200
                or t["box"][3]>1500 for t in texts),
            "overlaps": overlaps,
            "missing_headline":not main,
            # Only the freeform renderer has measured each *painted glyph*.
            # Do not grant legacy/price-fallback layouts this proof.
            "text_bounds_verified":bool(measured_text and texts and main),
            "product_bounds_verified":bool(
                tracked.products and all(p.get("isolated") for p in tracked.products)),
            "product_visible_fraction":max(
                (p.get("visible_fraction",0) for p in tracked.products),
                default=None),
        }

    def _role_candidate(index, renderer, variant):
        candidate = dict(concepts[index])
        candidate["variant"]=variant
        with capture() as tracked:
            output = renderer(product,genuine_photo,candidate,
                              scenes[index],distributor)
        return output,_geometry(tracked)

    def _verified_safe_candidate(index, variant):
        """Last-resort distinct legacy composition; still subject to full QA.

        The AI's original genuine product pixels, approved factual record,
        price and actual scene are unchanged. No template is advertised as
        an AI-authored artboard.
        """
        if index==0:
            return _role_candidate(index,technical_poster,variant)
        if index==2:
            return _role_candidate(index,smart_poster,variant)
        candidate=dict(concepts[1])
        candidate["variant"]=variant
        visual=candidate["visual_plan"]
        styles=(visual.get("price_style") or "panel","tag","plaque")
        context_style={
            "crop":((.46,.46),(.56,.55),(.42,.52))[variant],
            "darkness":(.29,.25,.32)[variant],
            "blur":(2.0,2.4,1.8)[variant],"colour":.82,
        }
        detail={}
        output=render_promo(candidate,genuine_photo,product,distributor,editor={
            "background":"context","_scene_bytes":scenes[1],
            "_scene_style":context_style,"show_subline":False,
            "price_style":styles[variant],
            "accent":visual["accent"],
            "product_scale":(115,105,112)[variant],
            "product_x":visual.get("art_direction",{}).get("product_x",0),
            "product_y":visual.get("art_direction",{}).get("product_y",0),
            "price_position":visual.get("art_direction",{}).get("price_position","standard"),
            "headline_size":visual.get("art_direction",{}).get("headline_size","normal"),
            "_quality_report":detail})
        return output,{"truncated":False,"out_of_bounds":False,
                       "overlaps":bool(detail.get("issues"))}

    if creative_enabled:
        # A model-authored text zone (or a source-backed reference poster
        # panel) can be too small for an exact manufacturer claim. Previous
        # code aborted all nine assets after just the initial three variants.
        # Try progressively safer complete-text layouts, then a separately
        # labelled legacy renderer. Every attempt still passes choose_best's
        # genuine-photo, text, contrast and bounds gates. No approval bypass.
        for index,key in enumerate(("poster_technical","poster_price","poster_smart")):
            _emit("rendering",key)
            scene_warning={"warning":scene_references[index]["relevance_warning"]}
            def _creative_candidate(variant,index=index,key=key,text_safety=0):
                with capture() as tracked:
                    if (key=="poster_price" and
                            promo_template=="workshop_showcase" and text_safety==0):
                        poster=render_workshop_showcase(
                            product,genuine_photo,concepts[index],scenes[index],
                            distributor,variant=variant)
                    else:
                        poster=render_creative_canvas(
                            product,genuine_photo,concepts[index],scenes[index],
                            distributor,variant=variant,text_safety=text_safety)
                return poster,_geometry(tracked,measured_text=True)
            failures=[]
            selected=None
            engine=("workshop-showcase-ai-variation"
                    if key=="poster_price" and promo_template=="workshop_showcase"
                    else "ai-freeform-canvas")
            for safety in (0,1,2):
                # When the reference workshop template is too cramped, the
                # fallback is explicitly an AI-original layout, not a secretly
                # altered Workshop Showcase graphic.
                try:
                    selected=choose_best(
                        lambda variant,safety=safety:_creative_candidate(
                            variant,text_safety=safety),
                        ROLES[index],genuine_photo,preferred_variant=1,
                        scene_relevance=scene_warning)
                    if safety:
                        engine="ai-freeform-text-recovery"
                        warnings.append(
                            key+" used an independently checked AI-original "
                            "layout with full-size-safe verified copy.")
                    break
                except ValueError as exc:
                    failures.append(str(exc)[:240])
            if selected is None:
                try:
                    selected=choose_best(
                        lambda variant:_verified_safe_candidate(index,variant),
                        ROLES[index],genuine_photo,
                        scene_relevance=scene_warning)
                    engine="verified-safe-layout"
                    warnings.append(
                        key+" used a separately labelled, validated safe "
                        "layout because the original art could not fit "
                        "verified source text.")
                except ValueError as exc:
                    failures.append(str(exc)[:240])
            if selected is None:
                _emit("failed",key,report={"issues":[
                    failures[-1] if failures else "No valid poster layout"]})
                raise ValueError(
                    "No verified layout could render "+key+
                    "; last failure: "+(failures[-1] if failures
                                        else "unknown quality issue"))
            image_assets[key],quality_reports[key]=selected
            quality_reports[key]["render_engine"]=engine
            if failures:
                quality_reports[key]["recovered_after_failed_variants"]=len(failures)
            _emit("quality_checking",key)
    else:
        _emit("rendering","poster_technical")
        image_assets["poster_technical"],quality_reports["poster_technical"] = choose_best(
            lambda variant:_role_candidate(0,technical_poster,variant),
            "technical_application",genuine_photo,
            preferred_variant=concepts[0]["visual_plan"]["preferred_variant"],
            scene_relevance={"warning":scene_references[0]["relevance_warning"]})
        _emit("quality_checking","poster_technical")
        _emit("rendering","poster_price")
        retail=concepts[1]
        visual=retail["visual_plan"]
    
        def _price_candidate(variant):
            if promo_template=="workshop_showcase":
                with capture() as tracked:
                    output=render_workshop_showcase(
                        product,genuine_photo,retail,scenes[1],
                        distributor,variant=variant)
                return output,_geometry(tracked,measured_text=True)
            candidate=dict(retail)
            candidate["variant"]=variant
            preferred_style=visual.get("price_style")
            styles=(preferred_style or "panel","tag","plaque")
            # Different price layouts are assessed before delivery. The price
            # remains verified and the real tool cutout is always reused.
            context_style={
                "crop":((.46,.46),(.56,.55),(.42,.52))[variant],
                "darkness":(.29,.25,.32)[variant],
                "blur":(2.0,2.4,1.8)[variant],"colour":.82,
            }
            detail={}
            output=render_promo(candidate,genuine_photo,product,distributor,editor={
                "background":"context","_scene_bytes":scenes[1],
                "_scene_style":context_style,"show_subline":False,
                "price_style":styles[variant],
                "accent":visual["accent"],
                "product_scale":(115,105,112)[variant],
                "product_x":visual.get("art_direction",{}).get("product_x",0),
                "product_y":visual.get("art_direction",{}).get("product_y",0),
                "price_position":visual.get("art_direction",{}).get("price_position","standard"),
                "headline_size":visual.get("art_direction",{}).get("headline_size","normal"),
                "_quality_report":detail})
            return output,{"truncated":False,"out_of_bounds":False,
                           "overlaps":bool(detail.get("issues"))}
    
        image_assets["poster_price"],quality_reports["poster_price"] = choose_best(
            _price_candidate,"price_promo",genuine_photo,
            preferred_variant=concepts[1]["visual_plan"]["preferred_variant"],
            scene_relevance={"warning":scene_references[1]["relevance_warning"]})
        if promo_template=="workshop_showcase":
            quality_reports["poster_price"]["render_engine"]="workshop-showcase-verified-variation"
        _emit("quality_checking","poster_price")
        _emit("rendering","poster_smart")
        image_assets["poster_smart"],quality_reports["poster_smart"] = choose_best(
            lambda variant:_role_candidate(2,smart_poster,variant),
            "product_selected",genuine_photo,
            preferred_variant=concepts[2]["visual_plan"]["preferred_variant"],
            scene_relevance={"warning":scene_references[2]["relevance_warning"]})
        _emit("quality_checking","poster_smart")
    # Format art is independently checked. Publish the six approved social,
    # web and email graphics even if a poster's later vision review fails.
    # This does not make a failed poster or a partial ZIP downloadable.
    _emit("rendering_formats")
    proof = marketing_strategy["proof_point"] or choose_feature(
        product, marketing_strategy["primary_focus"])
    # V46: all six additional marketing formats have their OWN AI-designed layout,
    # tailored to its native width, height, safe areas and viewing context.
    # The model provides coordinates and feature indices, never source pixels,
    # copy, prices or arbitrary image URLs.
    supplied_formats = (raw_concepts[0].get("ai_format_canvases") or {}
                        if mode=="gemini-assisted" and raw_concepts else {})
    if not isinstance(supplied_formats,dict):
        supplied_formats={}
    model_facts=[str(f).strip()[:175] for f in product.get("features",[])
                 if isinstance(f,str) and str(f).strip()][:12]
    verified_set=set(verified_candidates(product))
    format_facts=[f if f in verified_set else "" for f in model_facts]
    headlines={concept["campaign_role"]:concept.get("headline") or product.get("title")
               for concept in concepts}
    parent_choices=(raw_concepts[0].get("format_parent_roles") or {}
                    if mode=="gemini-assisted" and raw_concepts else {})
    format_parents=choose_format_parents(parent_choices)
    creative_plan["format_parent_roles"]=dict(format_parents)
    format_reports={}
    format_canvases={}
    palette_choices={}
    used_format_palettes=[]
    failed_formats=[]
    for key in FORMAT_ORDER:
        _emit("rendering",key)
        parent_role=format_parents[key]
        scene_idx=ROLES.index(parent_role)
        parent=concepts[scene_idx]
        parent_style=parent["creative_direction"]
        parent_family=parent_style["creative_family"]
        parent_headline=parent.get("headline") or product.get("title")
        parent_proof=parent.get("selling_point") or proof
        brief=validate_format_canvas(key,supplied_formats.get(key),len(format_facts))
        # Gemini may choose an original palette for every native format.
        # If it omitted colour or repeated the same one everywhere, use a
        # truthful differentiated brand-safe alternative rather than six
        # default-navy replicas.
        original_palette=brief.get("creative_palette") if brief else None
        palette=format_palette(key,original_palette,used_format_palettes)
        used_format_palettes.append(palette)
        palette_choices[key]=palette
        if brief:
            brief["creative_palette"]=palette
            # Inherit a *different* source-backed campaign angle; keep the
            # model's independently authored native-format geometry intact.
            brief={**brief,"headline_role":parent_role,
                   "scene_role":parent_role,"creative_family":parent_family}
            if parent_proof in format_facts:
                brief["proof_feature_index"]=format_facts.index(parent_proof)
        try:
            if brief and mode=="gemini-assisted":
                # Any failed native-format artwork is rejected rather than
                # quietly shipping a white product rectangle or cropped text.
                output,report=generate_format(
                    key,brief,product,genuine_photo,scenes=scenes,
                    headlines=headlines,facts=format_facts,distributor=distributor,
                    source_report=asset_report)
                image_assets[key]=output
                format_reports[key]=report
                format_canvases[key]=brief
            else:
                image_assets[key]=_native_graphic(
                    product,genuine_photo,distributor,key,parent_proof,
                    scene=scenes[scene_idx],visual_plan=creative_plan,
                    creative_family=parent_family,headline=parent_headline,
                    creative_palette=palette)
                format_reports[key]={
                    "render_engine":"verified-legacy-layout","passed":None,
                    "parent_role":parent_role,"creative_family":parent_family,
                    "creative_palette":palette,"visual_treatment":"bold_geometry",
                    "warning":"AI did not return an approved native-format canvas; "
                              "older renderer used. Manual artwork review required."}
                if mode=="gemini-assisted":
                    warnings.append("No safe AI original layout for "+key+
                                    "; the existing format layout was used.")
            format_reports[key]["parent_role"]=parent_role
            format_reports[key]["creative_family"]=parent_family
            format_reports[key]["creative_palette"]=palette
            format_reports[key]["visual_treatment"]=(
                brief["visual_treatment"] if brief else "bold_geometry")
            # Individual files become visible only after their normal image
            # gate succeeds (the AI format renderer already checks two
            # variants). We do not resize, remove QA or shorten Gemini work.
            _emit("ready",key,image_assets[key],format_reports[key])
        except (ValueError,OSError,RuntimeError) as exc:
            # An AI-authored text zone can be impossible to fill with the
            # exact verified wording. Never ship clipped copy or lose the
            # entire campaign for one Story or banner. Create a separately
            # labelled native-size recovery using genuine product pixels and
            # the source-approved selling point; inspect the resulting PNG.
            recovered=False
            if brief and mode=="gemini-assisted":
                try:
                    source_gate=asset_report or require_good_asset(genuine_photo)
                    safe_fact=min(
                        (f for f in format_facts if f),
                        key=len,default=proof)
                    native=_native_graphic(
                        product,genuine_photo,distributor,key,
                        parent_proof if parent_proof else safe_fact,
                        scene=scenes[scene_idx],visual_plan=creative_plan,
                        creative_family=parent_family,headline=parent_headline,
                        creative_palette=palette)
                    report=quality_check_safe_native(native,key,source_gate)
                    if not report["passed"]:
                        raise ValueError("; ".join(report["issues"]))
                    report["recovered_from"]=str(exc)[:200]
                    report["parent_role"]=parent_role
                    report["creative_family"]=parent_family
                    report["creative_palette"]=palette
                    report["visual_treatment"]="bold_geometry"
                    image_assets[key]=native
                    format_reports[key]=report
                    warnings.append(
                        key+" used a verified native-layout recovery when "
                        "the AI text zones were too small.")
                    _emit("ready",key,native,report)
                    recovered=True
                except (ValueError,OSError,RuntimeError) as recovery_error:
                    failed_formats.append(
                        (key,"AI rejected: "+str(exc)[:115]+
                         "; verified backup rejected: "+
                         str(recovery_error)[:115]))
            if not recovered:
                if not (brief and mode=="gemini-assisted"):
                    failed_formats.append((key,str(exc)[:220]))
                _emit("failed",key,report={"issues":[failed_formats[-1][1]]})
    creative_plan["format_palettes"]=palette_choices
    _emit("reviewing_posters")
    # Inspect actual poster pixels and diversity before producing the ZIP.
    distinctness=check_distinctness(image_assets,concepts)
    if creative_enabled and not distinctness["passed"]:
        raise ValueError("AI artwork rejected for repeated compositions: "+
                         "; ".join(distinctness["issues"]))
    critic={"reviewed":False,"method":"legacy-layout-geometry-only",
            "issues":{},"warning":None}
    if creative_enabled:
        critic=reconcile_with_measured_geometry(
            review_finished_artworks(image_assets),quality_reports)
        blocking={key:codes for key,codes in critic["issues"].items() if codes}
        if blocking:
            # Keep the actual AI artboards and genuine manufacturer pixels.
            # V52 retried only one variant, then failed the whole campaign with
            # a generic message even if another bounded variant was available.
            # Each repaired candidate still has to pass deterministic geometry
            # checks AND a new independent visual review of the final pixels.
            poster_ids=("poster_technical","poster_price","poster_smart")
            original_variants={
                key:int(quality_reports[key].get("variation",1))
                for key in poster_ids
            }
            for attempt in (1,2):
                local_rejections={}
                for index,key in enumerate(poster_ids):
                    if key not in blocking:
                        continue
                    codes=blocking[key]
                    # Alternate scale/exposure cannot repair a genuinely bad
                    # photo cutout, blurred manufacturer source or duplicate
                    # layout. Never approve these by disabling the critic.
                    if any(code in codes for code in (
                            "white_box","white_halo","blurry_product",
                            "duplicate_layout")):
                        raise ValueError("AI visual review rejected "+key+
                                         ": "+", ".join(codes)+
                                         ". A better genuine source photo or "
                                         "fresh creative plan is required.")
                    alternative=(original_variants[key]+attempt)%3
                    def _repair_candidate(variant,index=index):
                        with capture() as tracked:
                            payload=render_creative_canvas(
                                product,genuine_photo,concepts[index],
                                scenes[index],distributor,variant=variant,
                                text_safety=attempt)
                        return payload,_geometry(tracked,measured_text=True)
                    try:
                        revised,report=choose_best(
                            _repair_candidate,ROLES[index],genuine_photo,
                            variants=(alternative,))
                    except ValueError as exc:
                        # A failed local layout never replaces a previously
                        # validated image. Try the last unused variant below.
                        local_rejections[key]=str(exc)[:150]
                        continue
                    image_assets[key]=revised
                    quality_reports[key]=report
                    quality_reports[key]["auto_repaired"]=True
                    quality_reports[key]["visual_repair_attempt"]=attempt
                    quality_reports[key]["render_engine"]="ai-freeform-canvas"
                next_review=reconcile_with_measured_geometry(
                    review_finished_artworks(image_assets),quality_reports)
                if not next_review["reviewed"]:
                    raise ValueError(
                        "AI visual re-review became unavailable after a "
                        "rejected poster. Unapproved artwork was not released.")
                updated={
                    key:codes for key,codes in next_review["issues"].items()
                    if codes
                }
                # A failed deterministic variant cannot be declared fixed by
                # a second nondeterministic visual-critic response.
                for key in local_rejections:
                    updated.setdefault(key,blocking[key])
                blocking=updated
                critic=next_review
                if not blocking:
                    break
            if blocking:
                # Typography-safe AI rerenders might still be refused. Recover
                # the specific failing roles with a separate, proven layout
                # renderer rather than abandoning unrelated poster artwork.
                # This is NOT an AI-authored design and must be labelled as such.
                recovery={}
                for index,key in enumerate(poster_ids):
                    if key not in blocking:continue
                    if any(code in blocking[key] for code in (
                            "white_box","white_halo","blurry_product")):
                        continue
                    try:
                        revised,report=choose_best(
                            lambda variant,index=index:_verified_safe_candidate(index,variant),
                            ROLES[index],genuine_photo,
                            scene_relevance={"warning":
                                scene_references[index]["relevance_warning"]})
                    except (ValueError,OSError,RuntimeError):
                        continue
                    image_assets[key]=revised
                    quality_reports[key]=report
                    quality_reports[key]["render_engine"]="verified-safe-layout"
                    quality_reports[key]["recovered_from_ai_visual_issue"]=list(blocking[key])
                    recovery[key]=True
                if recovery:
                    safe_review=reconcile_with_measured_geometry(
                        review_finished_artworks(image_assets),quality_reports)
                    if not safe_review["reviewed"]:
                        raise ValueError(
                            "Independent visual review became unavailable for "
                            "repaired poster artwork. No unreviewed poster was released.")
                    critic=safe_review
                    blocking={key:codes for key,codes in safe_review["issues"].items()
                              if codes}
                    if not blocking:
                        creative_plan["render_engine"]="mixed-ai-and-verified-safe-layout"
                        creative_plan["verified_safe_recoveries"]=list(recovery)
                        warnings.append(
                            "The independent AI critic rejected one or more original "
                            "artboards. Those roles use separate verified-safe "
                            "layouts, approved by all remaining quality checks.")
            if blocking:
                detail="; ".join(
                    key+": "+", ".join(sorted(set(codes)))
                    for key,codes in sorted(blocking.items()))
                raise ValueError(
                    "Poster layouts failed independent visual review after real "
                    "text repairs and a safe layout recovery: "+detail+
                    ". No unapproved posters have been released.")
            distinctness=check_distinctness(image_assets,concepts)
            if not distinctness["passed"]:
                raise ValueError("Revised artwork is not visually distinct.")
        if critic.get("warning"):
            warnings.append(critic["warning"])
    # The batch critic must approve the complete poster set before ANY
    # poster is revealed as ready. A later rejected design therefore never
    # leaks an unreviewed intermediate poster to the user.
    for key in ("poster_technical","poster_price","poster_smart"):
        _emit("ready",key,image_assets[key],quality_reports[key])
    # Never claim success or build a ZIP while a native format is missing;
    # unlike V54, already-approved posters now remain downloadable even
    # when a particular Story or banner cannot be recovered.
    if failed_formats:
        raise ValueError("Incomplete campaign; failed quality checks: "+
                         "; ".join(k+": "+reason for k,reason in failed_formats))
    _emit("finalising_pack")
    creative_plan["format_render_engines"]={
        key:format_reports[key]["render_engine"] for key in FORMAT_ORDER}
    qr = _source_qr(product)
    if qr:
        image_assets["source_qr"] = qr

    copies = _copies(product, concepts)
    title=_clean(product.get("title"),130)
    story_fact=concepts[0].get("selling_point") or "Review official product specifications."
    smart_fact=concepts[2].get("selling_point") or "Review official product specifications."
    social_suggestions={
        "instagram_story":[
            {"slide":1,"suggestion":"Introduce the product","text":"LASER "+str(product.get("part") or "")+" · "+title},
            {"slide":2,"suggestion":"Show its documented application","text":story_fact},
            {"slide":3,"suggestion":"Highlight the selected extra angle","text":smart_fact},
        ],
        "whatsapp":"Laser Tools "+str(product.get("part") or "")+" — "+title+
                   ". See official details to confirm suitability before ordering.",
        "instagram_caption":copies[0]["social_caption"],
        "review_note":"Suggested layout and wording only. Review product information, confirm application and obtain company approval before posting.",
    }
    files = dict(FOLDERS)
    if qr:
        files["source_qr"] = "05_Product_Info/Official_Product_QR.png"
    file_paths = list(files.values()) + [
        "04_Copy/All_Channels.txt", "04_Copy/All_Channels.json",
        "04_Copy/Instagram_Story_Suggestions.txt",
        "05_Product_Info/Marketing_Strategy.txt",
        "05_Product_Info/Source_Record.json", "05_Product_Info/Campaign_Summary.pdf",
        "05_Product_Info/READ_FIRST.txt", "Campaign_Manifest.json",
    ]
    manifest = {
        "part": str(product.get("part", "")),
        "title": str(product.get("title", "")),
        "category": product["marketing_direction"].get("category_label", ""),
        "marketing_strategy": marketing_strategy,
        "creative_plan": creative_plan,
        "promo_template":promo_template,
        "artwork_quality": quality_reports,
        "format_artwork_quality": format_reports,
        "ai_format_canvases": format_canvases,
        "product_photo_quality":asset_report,
        "creative_critic":{
            "method":critic["method"],"reviewed":critic["reviewed"],
            "issues":critic["issues"],"warning":critic["warning"],
            "geometry_disagreements":critic.get("geometry_disagreements",{})},
        "campaign_distinctness":distinctness,
        "scene_photography": scene_references,
        "poster_editor":{
            "manufacturer_title":str(product.get("title") or "")[:160],
            "verified_features":verified_candidates(product)[:24],
            "allowed_roles":["poster_technical","poster_price","poster_smart"],
            "review_notice":"Headline must use the verified product title; featured facts must come from the source. Pricing is locked.",
        },
        "poster_revision":0,
        "social_suggestions": social_suggestions,
        "source": _approved_source(product),
        "distributor": BRAND_LABELS.get(distributor) if distributor else None,
        "price": _price_line(product),
        "generation_method": mode,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "angles": [
            {"name": concept.get("name") or FAMILIES_LABELS[index],
             "role":ROLES[index], "focus": concept["focus"],
             "third_angle":concept.get("third_angle"),
             "layout":("Workshop Showcase · AI creative variations"
                       if index==1 and promo_template=="workshop_showcase" else
                       "Verified-safe recovery" if quality_reports[
                          ("poster_technical","poster_price","poster_smart")[index]
                       ].get("render_engine")=="verified-safe-layout" else
                       "AI original composition" if creative_enabled
                       else concept["family"]),
             "headline": str(concept.get("headline") or ""),
             "selling_point": str(concept.get("selling_point") or ""),
             "creative_family":concept["creative_direction"]["creative_family"],
             "composition_mode":concept["creative_direction"]["composition_mode"],
             "headline_strategy":concept["creative_direction"]["headline_strategy"],
             "proof_strategy":concept["creative_direction"]["proof_strategy"],
             "copy_tone":concept["creative_direction"]["copy_tone"],
             "hero_emphasis":concept["creative_direction"]["hero_emphasis"],
             "price_emphasis":concept["creative_direction"]["price_emphasis"],
             "creative_palette":concept["creative_direction"]["creative_palette"],
             "visual_treatment":concept["creative_direction"]["visual_treatment"],
             "text_treatment":concept["creative_direction"]["text_treatment"],
             "hero_treatment":concept["creative_direction"]["hero_treatment"]}
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
    # Live server uses a private on-disk ZIP sink. Nine already-compressed
    # PNGs must not be duplicated into a second giant BytesIO buffer while
    # all originals are in RAM; tests/direct consumers retain the old bytes
    # contract by omitting spill_archive.
    archive=(tempfile.NamedTemporaryFile(
        mode="w+b",suffix=".zip",prefix="laser-campaign-staging-",
        delete=False) if spill_archive else io.BytesIO())
    try:
      with ZipFile(archive, "w", compression=ZIP_DEFLATED) as z:
        for key, payload in image_assets.items():
            z.writestr(files[key], payload, compress_type=ZIP_STORED)
        z.writestr("04_Copy/All_Channels.txt", _copy_text(copies))
        z.writestr("04_Copy/All_Channels.json", json.dumps(copies, indent=2, ensure_ascii=False))
        z.writestr("04_Copy/Instagram_Story_Suggestions.txt", "\n\n".join(
            "Story frame "+str(v["slide"])+" — "+v["suggestion"]+"\n"+v["text"]
            for v in social_suggestions["instagram_story"])+"\n\n"+
            social_suggestions["review_note"])
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
        # The audit-only raw supplier fragments are not customer-facing
        # material. They can include rejected German/Dutch/French sentences.
        public_record={key:value for key,value in product.items()
                       if key!="source_raw_features"}
        z.writestr("05_Product_Info/Source_Record.json",
                   json.dumps(public_record, indent=2, ensure_ascii=False, default=str))
        z.writestr("05_Product_Info/READ_FIRST.txt", note)
        z.writestr("05_Product_Info/Campaign_Summary.pdf",
                   _summary_pdf(product, concepts, manifest))
        z.writestr("Campaign_Manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
      if spill_archive:
          archive.flush()
          archive.close()
          archive_payload={"archive_path":Path(archive.name)}
      else:
          archive_payload={"archive":archive.getvalue()}
    except Exception:
      archive.close()
      if spill_archive:
          try: os.unlink(archive.name)
          except FileNotFoundError: pass
      raise
    return {**archive_payload,"images": image_assets,
            "manifest": manifest,
            # Server-only context; NEVER sent in response/ZIP. Needed for
            # changing a single poster without re-fetching/regenerating AI.
            "editor_context":{"product":product,"genuine_photo":genuine_photo,
                              "scenes":scenes,"concepts":concepts,
                              "distributor":distributor}}
