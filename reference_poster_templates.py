"""Reference-led Laser poster layouts: verified datasheet and workshop promotion.

The supplied reference pictures define the visual grammar, not tool pixels or
product claims. Only the caller's genuine manufacturer image is used as the
product hero; no generic AI-rendered tool can enter either template.
"""
from __future__ import annotations

import io
import re
from PIL import Image, ImageDraw, ImageColor

from poster import font
from poster_quality import record_text, record_area
from campaign_role_posters import actual_scene, brand, co_brand, product_photo
from ai_promo_renderer import verified_price

W, H = 1200, 1500
NAVY = (3, 20, 38, 255)
DEEP = (5, 34, 63, 255)
LASER_BLUE = (0, 111, 190, 255)
CYAN = (15, 168, 236, 255)
WHITE = (255, 255, 255, 255)
PALE = (212, 234, 246, 255)


def _rows(draw, text, width, face):
    """Wrap without silently clipping, abbreviating or changing a source fact."""
    lines = []
    line = ""
    for word in str(text or "").split():
        proposal = (line + " " + word).strip()
        if draw.textbbox((0, 0), proposal, font=face)[2] <= width:
            line = proposal
            continue
        if line:
            lines.append(line)
        line = ""
        for char in word:
            candidate = line + char
            if line and draw.textbbox((0, 0), candidate, font=face)[2] > width:
                lines.append(line)
                line = char
            else:
                line = candidate
    if line:
        lines.append(line)
    return lines


def _draw_fit(draw, text, box, *, maximum=48, minimum=16, max_lines=3,
              colour=WHITE, bold=True, role="text"):
    text = " ".join(str(text or "").split())
    if not text:
        return False
    x0, y0, x1, y1 = box
    for size in range(maximum, minimum - 1, -2):
        face = font(size, "bold" if bold else "regular")
        rows = _rows(draw, text, x1 - x0 - 2, face)
        step = round(size * 1.23)
        if len(rows) > max_lines or len(rows) * step > y1 - y0:
            continue
        if any((lambda b: b[0] < x0 or b[1] < y0 or b[2] > x1 or b[3] > y1)(
            draw.textbbox((x0, y0 + i * step), row, font=face))
            for i, row in enumerate(rows)):
            continue
        for i, row in enumerate(rows):
            draw.text((x0, y0 + i * step), row, font=face, fill=colour)
        record_text(text, box, rows, size, role)
        return True
    return False


def _required(draw, text, box, **kwargs):
    if not _draw_fit(draw, text, box, **kwargs):
        raise ValueError("Full verified text does not fit reference poster: " +
                         str(kwargs.get("role", "text")))


def _verified_facts(product, concept):
    """Keep complete, distinct official features; never invent kit contents."""
    original = [" ".join(x.split()).strip() for x in (product.get("features") or [])
                if isinstance(x, str) and x.strip()]
    for key, val in (product.get("specs") or {}).items():
        if isinstance(key, str) and isinstance(val, (str, int, float)):
            entry = key.strip() + ": " + str(val).strip()
            if key.strip() and str(val).strip():
                original.append(entry)
    offered = [concept.get("selling_point"), *(concept.get("features") or [])]
    choices = []
    for fact in [*offered, *original]:
        if not isinstance(fact, str):
            continue
        normal = " ".join(fact.split()).strip()
        if normal in original and normal not in choices:
            choices.append(normal)
    return choices


def _gradient(canvas, upper, lower, y0, y1):
    d = ImageDraw.Draw(canvas, "RGBA")
    for y in range(y0, y1, 6):
        t = (y - y0) / max(1, y1 - y0)
        c = tuple(round(upper[i] * (1 - t) + lower[i] * t) for i in range(3))
        d.rectangle((0, y, W, y + 6), fill=(*c, 255))


def _save(image):
    stream = io.BytesIO()
    image.convert("RGB").save(stream, "PNG", compress_level=3)
    return stream.getvalue()


def _bullets(draw, facts, *, top=1110, bottom=1420):
    """Select the maximum complete source facts that actually fit in the sheet."""
    if not facts:
        facts = ["Refer to the official manufacturer product listing for specifications."]
    for count in range(min(len(facts), 5), 0, -1):
        selected = facts[:count]
        for size in (25, 23, 21, 19, 17):
            face = font(size, "regular")
            lines = [_rows(draw, fact, 1042, face) for fact in selected]
            step = round(size * 1.27)
            heights = [len(r) * step + 13 for r in lines]
            if sum(heights) > bottom - top or any(len(r) > 5 for r in lines):
                continue
            y = top
            for fact, rows, height in zip(selected, lines, heights):
                draw.ellipse((58, y + 9, 71, y + 22), fill=WHITE)
                for i, row in enumerate(rows):
                    draw.text((95, y + i * step), row, font=face, fill=WHITE)
                record_text(fact, (95, y, 1150, y + height), rows, size, "detail")
                y += height
            return count
    raise ValueError("No full manufacturer information fits technical poster")


def render_technical_reference(product, official_photo, concept, scene=None,
                               distributor=None, variant=0):
    """Blue/white product information sheet based on reference image two."""
    if not official_photo or not product.get("title"):
        raise ValueError("Technical reference requires an official photo and title")
    canvas = Image.new("RGBA", (W, H), NAVY)
    _gradient(canvas, (0, 91, 160), (4, 57, 109), 0, 1030)
    d = ImageDraw.Draw(canvas, "RGBA")
    # Wide branded header and part-number divider.
    d.rectangle((0, 0, W, 178), fill=(0, 79, 151, 255))
    d.rectangle((0, 174, W, 182), fill=CYAN)
    brand(d, str(product.get("part") or ""))
    co_brand(canvas, distributor)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rectangle((0, 181, W, 383), fill=WHITE)
    title = " ".join(str(product["title"]).split()).upper()
    _required(d, title, (51, 200, 1150, 310), maximum=65, minimum=25,
              max_lines=3, colour=DEEP, role="headline")
    facts = _verified_facts(product, concept)
    application = next((x for x in facts if re.search(
        r"\bapplications?\b|\bvehicles?\b|\bfitment\b", x, re.I)), None)
    if application:
        if not _draw_fit(d, application, (55, 320, 1140, 374),
                         maximum=29, minimum=17, max_lines=2,
                         colour=DEEP, bold=False, role="application"):
            _required(d, "TECHNICAL PRODUCT INFORMATION", (55, 324, 1140, 373),
                      maximum=27, minimum=20, max_lines=1, colour=DEEP,
                      role="label")
    else:
        _required(d, "TECHNICAL PRODUCT INFORMATION", (55, 324, 1140, 373),
                  maximum=27, minimum=20, max_lines=1, colour=DEEP,
                  role="label")
    # Reference: concise white benefit above the large authentic product hero.
    intro = next((x for x in facts if x != application and len(x) <= 178), None)
    if intro:
        _draw_fit(d, intro, (56, 403, 1147, 503), maximum=32,
                  minimum=19, max_lines=3, colour=WHITE,
                  bold=True, role="proof")
    hero_top = 516 if intro else 440
    product_photo(canvas, official_photo, (45, hero_top, 1155, 1022),
                  scale=(0.99, 1.04, 1.0)[variant % 3])
    # Clear factual information section, not generic boxes around tiny text.
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rectangle((0, 1035, W, H), fill=(0, 77, 144, 255))
    d.rectangle((45, 1064, 1155, 1069), fill=PALE)
    _required(d, "Additional Information", (52, 1076, 1149, 1128),
              maximum=38, minimum=28, max_lines=1, colour=WHITE,
              role="section_heading")
    # Additional Information lists full verified facts rather than blank space.
    _bullets(d, facts, top=1142, bottom=1437)
    d.rectangle((0, 1453, W, H), fill=(0, 42, 88, 255))
    _required(d, "LASER TOOLS | OFFICIAL PRODUCT PHOTO | DRAFT FOR REVIEW",
              (56, 1461, 1155, 1494), maximum=18, minimum=14,
              max_lines=1, colour=PALE, role="footer")
    return _save(canvas)


def _panel(draw, title, value, box, *, label_color=CYAN, role="detail"):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=11, fill=(3, 26, 48, 247),
                           outline=(12, 158, 232, 255), width=3)
    draw.rectangle((x0 + 13, y0 + 11, x0 + 19, y1 - 12), fill=label_color)
    _required(draw, title, (x0 + 32, y0 + 12, x1 - 12, y0 + 48),
              maximum=23, minimum=17, max_lines=1, role="label")
    if not _draw_fit(draw, value, (x0 + 32, y0 + 54, x1 - 16, y1 - 12),
                     maximum=20, minimum=13, max_lines=5, bold=False,
                     colour=PALE, role=role):
        _required(draw, "SEE OFFICIAL PRODUCT DETAILS",
                  (x0 + 32, y0 + 54, x1 - 16, y1 - 12),
                  maximum=18, minimum=13, max_lines=4,
                  bold=False, colour=PALE, role=role)


def render_promo_reference(product, official_photo, concept, scene=None,
                           distributor=None, variant=0):
    """Workshop workbench promotion using reference image three's composition."""
    if not official_photo or not product.get("title"):
        raise ValueError("Promo reference requires an official photo and title")
    canvas = Image.new("RGBA", (W, H), NAVY)
    used = actual_scene(canvas, scene, (0, 170, W, 1110),
                        brightness=(.81, .69, .76)[variant % 3], blur=1.3,
                        focus=("centre", "left", "right")[variant % 3]) if scene else False
    d = ImageDraw.Draw(canvas, "RGBA")
    if not used:
        # Draw perspective workshop architecture if licensed context is absent.
        d.rectangle((0, 170, W, 1110), fill=(10, 54, 84, 255))
        for x in (65, 405, 880, 1120):
            d.rectangle((x, 170, x + 21, 800), fill=(0, 99, 172, 255))
        for x in (90, 510, 900):
            d.rounded_rectangle((x, 310, x + 200, 685), radius=12,
                                fill=(15, 67, 102, 255),
                                outline=(46, 124, 186, 255), width=4)
    # Steel workbench and cool-toned lighting, drawn BEHIND genuine product.
    d.polygon(((0, 820), (W, 735), (W, 1062), (0, 1103)),
              fill=(105, 138, 166, 243))
    for index in range(22):
        y = 840 + 10 * index
        d.line((0, y + 53, W, y - 29), fill=(177, 204, 221, 69), width=2)
    d.rectangle((0, 0, W, 174), fill=(2, 16, 31, 255))
    d.rectangle((0, 173, W, 181), fill=CYAN)
    brand(d, str(product.get("part") or ""))
    co_brand(canvas, distributor)
    d = ImageDraw.Draw(canvas, "RGBA")
    # Legible title/proposition above the real tool, not an empty photo frame.
    d.rounded_rectangle((40, 211, 1160, 369), radius=17,
                        fill=(1, 19, 36, 230),
                        outline=(11, 161, 237, 222), width=3)
    _required(d, str(product["title"]).upper(), (66, 229, 1138, 316),
              maximum=53, minimum=23, max_lines=3, role="headline")
    _required(d, "WORKSHOP PRODUCT PROMOTION",
              (67, 322, 1070, 361), maximum=24, minimum=18,
              max_lines=1, colour=PALE, role="subline")
    product_photo(canvas, official_photo, (56, 390, 1146, 1010),
                  scale=(1.0, 1.05, .98)[variant % 3])
    # Three filled information panels, including a contents box only when
    # the manufacturer explicitly lists included parts.
    facts = _verified_facts(product, concept)
    first = next((x for x in facts if len(x) <= 115), None)
    second = next((x for x in facts if x != first and len(x) <= 115), None)
    kit = next((x for x in facts if re.search(
        r"\b(includes|contains|comprises|supplied with|consists of|kit contents)\b",
        x, re.I)), None)
    third = kit or next((x for x in facts if x not in (first, second)
                         and len(x) <= 115), None)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rectangle((0, 1020, W, 1290), fill=(1, 18, 36, 249))
    d.line((0, 1020, W, 1020), fill=CYAN, width=5)
    _panel(d, "KEY FEATURES", first or "Review official specifications",
           (27, 1041, 402, 1265), role="feature")
    _panel(d, "WORKSHOP USE" if second else "PRODUCT DETAILS",
           second or "See manufacturer product listing",
           (413, 1041, 787, 1265), role="application")
    _panel(d, "KIT CONTENTS" if kit else "PRODUCT INFORMATION",
           third or "Refer to the official catalogue",
           (798, 1041, 1173, 1265), role="contents")
    # Genuine reviewed UK price, or honest enquiry instead of a fabricated RRP.
    price = verified_price(product)
    amount = price.get("amount") or "PRICE ON REQUEST"
    caption = ((price.get("label") or "UK RRP") + " · " +
               (price.get("vat") or "VAT STATUS TO CONFIRM")) if price.get("amount") \
              else "ENQUIRE FOR CURRENT UK PRICE"
    d.polygon(((38, 1300), (739, 1300), (710, 1410), (38, 1410)),
              fill=(0, 101, 183, 255))
    record_area("price", (38, 1300, 739, 1410))
    _required(d, amount, (64, 1308, 696, 1365), maximum=52, minimum=24,
              max_lines=1, role="price")
    _required(d, caption, (64, 1370, 699, 1403), maximum=19, minimum=14,
              max_lines=1, bold=False, role="price_caption")
    d.polygon(((758, 1310), (W, 1298), (W, 1411), (726, 1410)),
              fill=(1, 65, 122, 250))
    _required(d, "LASER TOOLS", (787, 1338, 1160, 1393),
              maximum=40, minimum=26, max_lines=1, role="brand")
    d.rectangle((0, 1420, W, H), fill=(2, 15, 31, 255))
    d.polygon(((410, 1420), (W, 1420), (W, H), (345, H)),
              fill=(0, 105, 184, 255))
    _required(d, "LASER TOOLS", (47, 1438, 405, 1490),
              maximum=35, minimum=24, max_lines=1, role="brand_footer")
    _required(d, "DRAFT — VERIFY PRICE AND PRODUCT DETAILS",
              (470, 1451, 1160, 1491), maximum=18, minimum=14,
              max_lines=1, role="footer")
    return _save(canvas)
