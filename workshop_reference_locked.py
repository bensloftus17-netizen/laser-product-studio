"""V71 fixed Workshop Showcase: actual user-supplied photographic reference.

Poster 02 owns this composition. The source image provides the workshop and
steel workbench photographed in the user's template; no AI rebuilds its
geometry, tool silhouette, or imagery. Genuine manufacturer product pixels
are placed separately, and only source-verified facts/price enter panels.
"""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from PIL import Image, ImageDraw

from ai_promo_renderer import verified_price
from brand_assets import get_brand_image
from poster import font
from poster_quality import record_area

W, H = 1200, 1500
DARK = (2, 16, 31, 255)
PANEL = (1, 21, 39, 255)
CYAN = (0, 162, 240, 255)
PALE = (212, 236, 248, 255)
WHITE = (255, 255, 255, 255)
SOURCE_PATH = Path(__file__).resolve().parent / "assets" / "workshop_reference_photo.b64"


def reference_scene():
    """Open the bundled crop of the *actual* supplied workshop photo.

    It is intentionally stored as ASCII base64 because the repo's assisted
    file editor accepts UTF-8. Fail closed rather than silently replacing the
    selected photograph with a generic AI scene.
    """
    encoded = SOURCE_PATH.read_text(encoding="ascii").strip()
    blob = base64.b64decode(encoded, validate=True)
    with Image.open(io.BytesIO(blob)) as original:
        original.load()
        if original.format != "WEBP" or original.size != (280, 210):
            raise ValueError("User workshop reference asset is not the approved crop")
        return original.convert("RGBA").resize((W, 810), Image.Resampling.BICUBIC)


def _fact_panels(d, source_facts, required):
    """Use literal official facts only; select content that fits each panel."""
    all_facts = list(dict.fromkeys(f.strip() for f in source_facts if isinstance(f, str) and f.strip()))
    kit = next((f for f in all_facts if re.search(
        r"\b(includes?|contains?|comprises?|supplied with|kit contents|consists of)\b",
        f, re.I)), None)
    descriptions = [f for f in all_facts if f != kit]
    chosen = []
    for f in sorted(descriptions, key=lambda x: (len(x) > 105, len(x))):
        if f not in chosen and len(chosen) < 3:
            chosen.append(f)
    while len(chosen) < 3:
        chosen.append("Check official Laser Tools product information")
    columns = (
        (25, 268), (279, 555), (566, 838)
    )
    names = ("KEY FEATURE", "WORKSHOP USE", "PRODUCT DETAIL")
    for name, fact, (x0, x1) in zip(names, chosen, columns):
        d.rectangle((x0, 1052, x1, 1056), fill=CYAN)
        required(d, name, (x0+9, 1073, x1-7, 1112),
                 maximum=23, minimum=16, max_lines=1,
                 colour=WHITE, role="panel_label")
        required(d, fact, (x0+9, 1122, x1-8, 1236),
                 maximum=23, minimum=13, max_lines=6, bold=False,
                 colour=PALE, role="detail")
    # Right panel preserves reference's bright cyan KIT CONTENTS header if
    # source-backed, otherwise changes that label to PRODUCT INFORMATION.
    d.rectangle((858, 1038, W, 1085), fill=(0, 125, 205, 255))
    required(d, "KIT CONTENTS" if kit else "PRODUCT INFORMATION",
             (874, 1047, 1187, 1082), maximum=25, minimum=16,
             max_lines=1, colour=WHITE, role="panel_label")
    required(d, kit or "Refer to the official product description for included items.",
             (875, 1103, 1183, 1235),
             maximum=23, minimum=13, max_lines=7,
             bold=False, colour=PALE, role="contents")


def _logo(d, x, y, width=470):
    # Reconstruct the branded LASER/TOOLS typography at native resolution
    # so the supplied lower-resolution photo crop never blurs the logo.
    size=107 if width >= 400 else 73
    d.text((x, y), "LASER", font=font(size, "bold"), fill=WHITE)
    underline_y=y+size+17
    d.rectangle((x, underline_y, x+124 if width>=400 else x+86,
                 underline_y+7), fill=CYAN)
    d.text((x+145 if width>=400 else x+105, y+size-5),
           "TOOLS", font=font(34 if width>=400 else 22, "bold"), fill=WHITE)
    d.rectangle((x+345 if width>=400 else x+240, underline_y,
                 x+width, underline_y+7), fill=CYAN)


def render_locked_workshop_promo(product, official_photo, concept, scene=None,
                                 distributor=None, variant=0,
                                 photo_placer=None, required=None,
                                 source_facts=None, save=None):
    """Exact reference-driven geometry; variant only scales the REAL product."""
    if not product.get("title") or not official_photo:
        raise ValueError("Workshop reference requires verified title and photo")
    if not (callable(photo_placer) and callable(required)
            and callable(source_facts) and callable(save)):
        raise ValueError("Locked workshop renderer requires source-safe adapters")
    canvas=Image.new("RGBA", (W,H), DARK)
    # Exact photographic workshop & steel workbench FROM USER TEMPLATE.
    canvas.alpha_composite(reference_scene(), (0, 259))
    d=ImageDraw.Draw(canvas, "RGBA")
    # Original template: tall LASER header and single horizontal blue line.
    d.rectangle((0, 0, W, 265), fill=(2, 15, 28, 255))
    _logo(d, 68, 33, 470)
    d.rectangle((0, 262, W, 269), fill=CYAN)
    required(d, "PART "+str(product.get("part") or ""),
             (831, 74, 1170, 126), maximum=43, minimum=22,
             max_lines=1, role="part_number")
    if distributor:
        mark=get_brand_image(distributor)
        if mark is not None:
            mark=mark.convert("RGBA")
            mark.thumbnail((176, 100), Image.Resampling.LANCZOS)
            d.rounded_rectangle((620, 54, 824, 165), radius=11, fill=WHITE)
            canvas.alpha_composite(mark,(722-mark.width//2,107-mark.height//2))
    d=ImageDraw.Draw(canvas, "RGBA")
    # A discreet label within the real workshop image, not the giant navy
    # product-title block from the old generic poster generator.
    d.rounded_rectangle((42, 303, 1156, 420), radius=8,
                        fill=(0, 15, 29, 214), outline=(14, 143, 213, 210), width=2)
    required(d, str(product["title"]).upper(), (67, 321, 1139, 406),
             maximum=52, minimum=21, max_lines=3,
             role="headline")
    # Hero floats ABOVE the steel workbench and BELOW the photograph's title.
    # Placement uses the manufacturer image unchanged (apart from resize).
    photo_placer(canvas,official_photo,(75, 438, 1120, 1012),
                 scale=(1.0, 1.04, .96)[variant%3])
    d=ImageDraw.Draw(canvas, "RGBA")
    # Lower information bays reproduce the user reference's 3-column grid
    # plus separate right-hand kit/product information bay.
    d.rectangle((0, 1024, W, 1260), fill=(0, 20, 39, 246))
    d.line((0, 1026, W, 1026), fill=CYAN, width=5)
    d.rectangle((16, 1042, 845, 1242), outline=CYAN, width=3)
    d.line((277, 1044, 277, 1240), fill=CYAN, width=3)
    d.line((562, 1044, 562, 1240), fill=CYAN, width=3)
    d.rectangle((858, 1038, 1192, 1242), outline=CYAN, width=3)
    _fact_panels(d,source_facts(product,concept),required)
    # Original reference's full-width black/blue footer with an angled
    # electric-blue price panel instead of an extra generic price card.
    d.rectangle((0, 1260, W, H), fill=(1, 22, 43, 255))
    d.line((0, 1274, W, 1274), fill=CYAN, width=5)
    d.polygon(((590, 1294), (W,1294), (W,H), (390,H)),
              fill=(0, 91, 167, 255))
    d.polygon(((578, 1294), (610,1294), (410,H), (378,H)),
              fill=CYAN)
    _logo(d, 48, 1321, 300)
    price=verified_price(product)
    amount=price.get("amount") or "PRICE ON REQUEST"
    suffix=((price.get("label") or "UK RRP")+" · "+
            (price.get("vat") or "VAT TO CONFIRM")) if price.get("amount") \
           else "ENQUIRE FOR CURRENT UK PRICE"
    record_area("price",(617, 1328, 1175, 1440))
    required(d, amount, (625,1329,1164,1396),
             maximum=58, minimum=25, max_lines=1,
             role="price")
    required(d, suffix, (625, 1397, 1166, 1431),
             maximum=22, minimum=15, max_lines=1,
             bold=False, colour=PALE, role="price_caption")
    required(d, "DRAFT — CHECK PRODUCT DETAILS BEFORE PUBLICATION",
             (620, 1460, 1176, 1493), maximum=16, minimum=12,
             max_lines=1, bold=False, colour=PALE, role="footer")
    return save(canvas)
