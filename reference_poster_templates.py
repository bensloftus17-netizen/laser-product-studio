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
    """Place the complete source text by measuring *actual visible glyphs*.

    Pillow/FreeType font ascenders can extend outside the naive baseline area.
    Position relative to the measured glyph bounding box, not the baseline:
    this preserves every character without overflowing the intended box.
    """
    text=" ".join(str(text or "").split())
    if not text:return False
    x0,y0,x1,y1=box
    width,height=x1-x0,y1-y0
    if width<=4 or height<=4:return False
    for size in range(maximum,minimum-1,-2):
        face=font(size,"bold" if bold else "regular")
        rows=_rows(draw,text,width-4,face)
        if len(rows)>max_lines or not rows:continue
        glyphs=[draw.textbbox((0,0),line,font=face) for line in rows]
        if any(b[2]-b[0]>width-4 for b in glyphs):continue
        step=round(size*1.20)
        glyph_height=(len(rows)-1)*step+max(b[3]-b[1] for b in glyphs)
        if glyph_height>height-2:continue
        positions=[]
        for i,b in enumerate(glyphs):
            px=x0+2-b[0]
            py=y0+1+i*step-b[1]
            extent=draw.textbbox((px,py),rows[i],font=face)
            if (extent[0]<x0 or extent[1]<y0 or
                extent[2]>x1 or extent[3]>y1):
                break
            positions.append((px,py))
        if len(positions)!=len(rows):continue
        for (px,py),line in zip(positions,rows):
            draw.text((px,py),line,font=face,fill=colour)
        record_text(text,box,rows,size,role)
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
    title = " ".join(str(concept.get("edited_headline") or product["title"]).split()).upper()
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
                  scale=(0.99, 0.91, 0.95)[variant % 3])
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
                           distributor=None, variant=0, *, _photo_placer=None):
    """V71: use the user-supplied workshop photo/reference, NOT generic art.

    Keep the original public function signature and the existing source-safe
    PIL composition adapters to preserve the poster quality capture, genuine
    product pixels and price verification across all campaign render paths.
    """
    from workshop_reference_locked import render_locked_workshop_promo
    return render_locked_workshop_promo(
        product, official_photo, concept, scene, distributor, variant=variant,
        photo_placer=_photo_placer or product_photo,
        required=_required, source_facts=_verified_facts, save=_save)
