"""Laser Tools AI promotional posters — three print-safe creative campaigns.

The artwork uses genuine, untouched manufacturer imagery; Gemini chooses short
marketing copy and verified feature bullets. Pricing is always supplied by the
site's verified product record, never by the language model.

Three contrasting compositions are intentional: retail = vivid/angular/bubble;
premium = bright/editorial/plaque; trade = industrial/diagonal/price ribbon.
"""
from __future__ import annotations

import io
import re
from PIL import Image, ImageDraw, ImageOps, ImageChops
from poster import font
from ai_photo_effects import compose_product

W, H = 1200, 1500
NAVY = "#0B2948"
INK = "#102D48"
BLUE = "#0874BF"
CYAN = "#24B4E9"
WHITE = "#FFFFFF"
SLATE = "#52718A"
LINE = "#DCE7F1"
FAMILIES = ("retail", "premium", "trade")
RETAIL_PALETTES = (
    {"blue": "#056DB9", "navy": "#092F56", "accent": "#FFC82E", "a_ink": "#0B2D48"},
    {"blue": "#0A65AF", "navy": "#0D2851", "accent": "#FF9D3D", "a_ink": "#142B43"},
    {"blue": "#175CB0", "navy": "#091F48", "accent": "#C5EB58", "a_ink": "#123048"},
)
PREMIUM_PALETTES = (
    {"paper": "#FCFBF8", "panel": "#F1F2F0", "navy": "#143956", "accent": "#B28D52"},
    {"paper": "#FBFDFF", "panel": "#E9F4FA", "navy": "#143956", "accent": "#0D95CD"},
    {"paper": "#F9FBFC", "panel": "#EAF1F4", "navy": "#143C56", "accent": "#418C9B"},
)
TRADE_PALETTES = (
    {"navy": "#0E263C", "mid": "#124A78", "accent": "#FFAA32", "pale": "#DEEDF5"},
    {"navy": "#061E39", "mid": "#08679B", "accent": "#25C4EC", "pale": "#E8F4FB"},
    {"navy": "#202D3A", "mid": "#165D82", "accent": "#D2E96B", "pale": "#EDF4F6"},
)
RRP_RE = re.compile(r"£\s*(\d[\d,]*(?:\.\d{1,2})?)")


def verified_price(product):
    """Respect price and VAT recorded by the source/staff. Never estimate either."""
    raw = str(product.get("price") or "").strip()
    m = RRP_RE.search(raw)
    if not m:
        return {"amount": None, "label": "PRICE ON REQUEST", "vat": "",
                "provenance": "No verified RRP available"}
    lower = raw.lower()
    vat = ("INC VAT" if "including vat" in lower or "inc vat" in lower
           else "EX VAT" if "excluding vat" in lower or "ex vat" in lower
           else "VAT STATUS TO CONFIRM")
    reviewed = str(product.get("price_source") or "").lower().startswith("staff entry")
    return {"amount": "£" + m.group(1), "label": "DRAFT UK RRP" if reviewed else "UK RRP",
            "vat": vat, "provenance": ("STAFF PRICE — APPROVAL REQUIRED" if reviewed else
                                        "CONFIRM CURRENT RRP BEFORE RELEASE")}


def _width(d, text, size, kind="bold"):
    b = d.textbbox((0, 0), str(text), font=font(size, kind))
    return b[2] - b[0]


def _split(d, text, max_width, size, kind):
    """Word wrap with special handling for long unbreakable SKU strings."""
    rows, current = [], ""
    for word in str(text or "").replace("\n", " ").split():
        possible = (current + " " + word).strip()
        if _width(d, possible, size, kind) <= max_width:
            current = possible
        else:
            if current:
                rows.append(current)
            current = ""
            for char in word:
                if current and _width(d, current + char, size, kind) > max_width:
                    rows.append(current)
                    current = char
                else:
                    current += char
    if current:
        rows.append(current)
    return rows


def _fit(d, text, box, sizes=(38, 34, 30, 26, 22), colour=INK,
         weight="bold", max_lines=3, align="left", role="text"):
    """Draw inside an explicit safe rectangle: no overflowing typography."""
    x0, y0, x1, y1 = box
    max_width, max_height = int(x1-x0), int(y1-y0)
    if not str(text or "").strip() or max_width <= 0 or max_height <= 0:
        return int(y0)
    fitted = None
    for size in sizes:
        lines = _split(d, text, max_width, size, weight)
        step = int(size * 1.28)
        if len(lines) <= max_lines and len(lines) * step <= max_height:
            fitted = size, lines, step
            break
    if fitted is None:
        size = sizes[-1]
        lines = _split(d, text, max_width, size, weight)
        step = int(size * 1.28)
        limit = max(1, min(max_lines, max_height // step))
        if len(lines) > limit:
            lines = lines[:limit]
            last = lines[-1].rstrip()
            while last and _width(d, last + "…", size, weight) > max_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + "…"
        fitted = size, lines, step
    size, lines, step = fitted
    from poster_quality import record_text
    record_text(text,box,lines,size,role)
    y = int(y0)
    for line in lines:
        if align == "center":
            x = x0 + (max_width - _width(d, line, size, weight)) / 2
        elif align == "right":
            x = x1 - _width(d, line, size, weight)
        else:
            x = x0
        d.text((int(x), y), line, font=font(size, weight), fill=colour)
        y += step
    return y


def _laser(d, x=60, y=45, dark=False):
    col = NAVY if dark else WHITE
    d.text((x, y), "LASER", font=font(82, "italic"), fill=col)
    d.line((x + 7, y + 93, x + 308, y + 93), fill=col, width=5)
    d.text((x + 39, y + 104), "T O O L S", font=font(19, "bold"), fill=col)


def _photo_bounds(photo):
    """Trim only outer near-white whitespace; never alter product pixels."""
    p = ImageOps.exif_transpose(Image.open(io.BytesIO(photo)))
    p.load()
    if p.width * p.height > 16_000_000:
        p.thumbnail((3400, 3400), Image.Resampling.LANCZOS)
    img = p.convert("RGBA")
    # Alpha transparency is an authoritative, non-destructive silhouette.
    if "A" in p.getbands():
        alpha = img.getchannel("A")
        bound = alpha.getbbox()
        return img.crop(bound) if bound else img
    rgb = p.convert("RGB")
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((rgb.width-1, 0)),
               rgb.getpixel((0, rgb.height-1)), rgb.getpixel((rgb.width-1, rgb.height-1))]
    if min(min(ch) for ch in corners) < 238:
        return img
    # A very light uniform edge is padding. Do not change the image's pixels.
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, WHITE)).convert("L")
    mask = diff.point(lambda v: 255 if v > 27 else 0)
    bbox = mask.getbbox()
    if bbox and (bbox[2]-bbox[0]) * (bbox[3]-bbox[1]) > rgb.width * rgb.height * .13:
        pad = max(14, int(min(rgb.size) * .018))
        bbox = (max(0, bbox[0]-pad), max(0, bbox[1]-pad),
                min(rgb.width, bbox[2]+pad), min(rgb.height, bbox[3]+pad))
        return img.crop(bbox)
    return img


def _photo_panel(base, photo, box, inset=32, rounded=28):
    """Large crisp product photograph framed cleanly; no AI-generated tool pixels."""
    x0, y0, x1, y1 = [int(v) for v in box]
    d = ImageDraw.Draw(base)
    # Flat design shadow behind the mount, not attached to the product image.
    d.rounded_rectangle((x0+12, y0+15, x1+12, y1+15), radius=rounded,
                        fill=(8, 32, 55, 48))
    d.rounded_rectangle((x0, y0, x1, y1), radius=rounded, fill=WHITE)
    photo_img = _photo_bounds(photo)
    available_w, available_h = x1-x0-inset*2, y1-y0-inset*2
    if available_w < 1 or available_h < 1:
        return
    ratio = min(available_w/photo_img.width, available_h/photo_img.height)
    # PIL.thumbnail does not upscale; full-size hero has to scale deliberately.
    size = (max(1, round(photo_img.width*ratio)), max(1, round(photo_img.height*ratio)))
    if size != photo_img.size:
        photo_img = photo_img.resize(size, Image.Resampling.LANCZOS)
    xx = x0 + (x1-x0-photo_img.width)//2
    yy = y0 + (y1-y0-photo_img.height)//2
    base.alpha_composite(photo_img, (xx, yy))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((x0, y0, x1, y1), radius=rounded, outline="#DCE5EF", width=2)


def _co_brand(base, distributor):
    if not distributor or distributor == "none":
        return
    from brand_assets import get_brand_image
    logo = get_brand_image(distributor)
    if logo is None:
        return
    logo = logo.convert("RGBA")
    logo.thumbnail((190, 79), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((908, 45, 1152, 158), radius=15, fill=WHITE)
    x = 908+(244-logo.width)//2
    y = 45+(113-logo.height)//2
    base.alpha_composite(logo, (x, y))


def _features(d, concept, boxes, dot, fg, text_sizes=(23, 21, 19, 17)):
    features = list(concept.get("features") or [])[:len(boxes)]
    for line, (x0, y0, x1, y1) in zip(features, boxes):
        d.ellipse((x0, y0+10, x0+14, y0+24), fill=dot)
        _fit(d, line, (x0+28, y0, x1, y1), text_sizes, fg, "regular", 3)


def _footer(d, dark=True):
    fg = "#AEC3D6" if dark else "#657D91"
    rule = "#385F7A" if dark else LINE
    d.line((56, 1448, 1144, 1448), fill=rule, width=2)
    _fit(d, "DRAFT ARTWORK  •  VERIFY ALL PRODUCT CLAIMS & RRP",
         (58, 1461, 1140, 1496), (16, 15, 14), fg, "bold", 1)


def _price_circle(d, price, box, accent, fg):
    x0, y0, x1, y1 = box
    d.ellipse((x0+12, y0+14, x1+12, y1+14), fill="#123651")
    d.ellipse(box, fill=accent)
    d.ellipse((x0+15, y0+15, x1-15, y1-15), outline=WHITE, width=3)
    if price["amount"]:
        _fit(d, price["label"], (x0+20, y0+59, x1-20, y0+99),
             (24, 21), fg, "bold", 1, "center")
        _fit(d, price["amount"], (x0+20, y0+126, x1-20, y0+219),
             (76, 66, 56, 48, 40, 33), fg, "bold", 2, "center")
        _fit(d, price["vat"], (x0+22, y0+248, x1-22, y0+292),
             (23, 20), fg, "bold", 1, "center")
    else:
        _fit(d, "PRICE", (x0+25, y0+104, x1-25, y0+148),
             (34, 29), fg, "bold", 1, "center")
        _fit(d, "ON REQUEST", (x0+20, y0+165, x1-20, y0+226),
             (32, 27, 23), fg, "bold", 1, "center")


def _sizes(values, editor):
    setting=(editor or {}).get("headline_size","normal")
    ratio={"small":.84,"normal":1.0,"large":1.17}.get(setting,1.)
    return tuple(max(17,int(v*ratio)) for v in values)


def _render_price(d, price, bounds, style, accent, dark_ink=NAVY, panel_bg=WHITE):
    """Switchable price badges, always based on the same verified RRP."""
    x0,y0,x1,y1=map(int,bounds)
    width,height=x1-x0,y1-y0
    value=price["amount"] or "ON REQUEST"
    label=price["label"] if price["amount"] else "CURRENT PRICE"
    fg=_price_ink(accent)
    if style=="bubble":
        side=min(width,height)-12
        left=x0+(width-side)//2
        top=y0+(height-side)//2
        if side>=310:
            _price_circle(d,price,(left,top,left+side,top+side),accent,fg)
        else:
            # Compact badge for trade strips; avoid the large standard
            # badge's vertical positioning crossing the poster footer.
            d.ellipse((left,top,left+side,top+side),fill=accent)
            d.ellipse((left+5,top+5,left+side-5,top+side-5),outline=WHITE,width=3)
            _fit(d,label,(left+12,top+25,left+side-12,top+65),
                 (20,17,14),fg,"bold",1,"center")
            _fit(d,value,(left+9,top+80,left+side-9,top+145),
                 (42,36,29,25,21),fg,"bold",2,"center")
            if price["amount"]:
                _fit(d,price["vat"],(left+13,top+154,left+side-13,top+185),
                     (17,15),fg,"bold",1,"center")
        return
    if style=="tag":
        d.polygon([(x0+30,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0+28)],fill=accent)
        d.polygon([(x0+30,y0),(x0+30,y0+30),(x0,y0+30)],fill="#FFFFFF")
        _fit(d,label,(x0+37,y0+23,x1-23,y0+65),(27,23,19),fg,"bold",1)
        _fit(d,value,(x0+28,y0+80,x1-26,y1-20),
             (75,67,58,48,37,29),fg,"bold",2)
        return
    if style=="banner":
        d.rounded_rectangle(bounds,radius=11,fill=accent)
        d.rectangle((x0,y0+15,x0+9,y1-15),fill=panel_bg)
        _fit(d,label,(x0+35,y0+22,x1-22,y0+62),(26,23,20),fg,"bold",1)
        _fit(d,value,(x0+32,y0+71,x1-20,y1-23),(87,76,65,51,43,35),fg,"bold",2)
        if price["amount"]:
            _fit(d,price["vat"],(x0+34,y1-43,x1-23,y1-14),(19,17),fg,"regular",1,"right")
        return
    # Premium plaque (also valid as a retail or trade alternative).
    d.rounded_rectangle(bounds,radius=22,fill=WHITE,outline=accent,width=5)
    _fit(d,label,(x0+30,y0+25,x1-30,y0+73),(27,24,20),dark_ink,"bold",1)
    _fit(d,value,(x0+25,y0+93,x1-25,y1-52),(72,62,53,44,35,27),dark_ink,"bold",2)
    if price["amount"]:
        _fit(d,price["vat"],(x0+30,y1-38,x1-25,y1-13),(21,18),dark_ink,"regular",1)


def _mix(hexcolor,anchor,portion):
    """Blend a user's colour with the brand's legible light/dark foundation."""
    a=tuple(int(hexcolor[i:i+2],16) for i in (1,3,5))
    b=tuple(int(anchor[i:i+2],16) for i in (1,3,5))
    return "#"+"".join(f"{round(a[j]*portion+b[j]*(1-portion)):02X}" for j in range(3))


def _price_ink(hexcolor):
    r,g,b=(int(hexcolor[i:i+2],16)/255 for i in (1,3,5))
    v=0.2126*r+0.7152*g+0.0722*b
    return NAVY if v>.52 else WHITE


def _customize_palette(p,editor,family):
    opts=editor or {}
    p=dict(p)
    accent=opts.get("accent")
    if isinstance(accent,str) and re.fullmatch(r"#[0-9a-fA-F]{6}",accent):
        p["accent"]=accent
    bg=opts.get("background_colour")
    if isinstance(bg,str) and re.fullmatch(r"#[0-9a-fA-F]{6}",bg):
        if family=="retail":
            p["blue"]=_mix(bg,"#056DB9",.75)
        elif family=="premium":
            p["paper"]=_mix(bg,"#FFFFFF",.28)
            p["panel"]=_mix(bg,"#E8EEF2",.35)
        elif family=="trade":
            p["navy"]=_mix(bg,"#061E34",.38)
    return p


def _background_art(d, mode, region, colour, dark, intensity=2):
    """Optional brand-safe graphic motifs; strength 0-3 is user controlled."""
    intensity=max(0,min(3,int(intensity)))
    if intensity==0:return
    x0,y0,x1,y1=region
    stroke=("#315D81" if dark else "#D8E5EF")
    width=max(1,2*intensity)
    if mode=="grid":
        stride=max(66,144-18*intensity)
        for x in range(x0+28,x1,stride):
            d.line((x,y0,x,y1),fill=stroke,width=width)
        for y in range(y0+28,y1,stride):
            d.line((x0,y,x1,y),fill=stroke,width=width)
    elif mode=="rings":
        cx,cy=x1-65,(y0+y1)//2
        for r in (125,220,315,420):
            d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=stroke,width=width+2)
        d.ellipse((cx-14,cy-14,cx+14,cy+14),fill=colour)
    elif mode in ("clean","context","workshop","bench","engine") and intensity==3:
        # A restrained accent motif on the decorative side, not over headline.
        for j in range(3):
            offset=j*41
            d.line((x1-160+offset,y0+25,x1-30+offset,y0+95),fill=stroke,width=6)


def _retail(concept, photo, product, price, variation, editor=None):
    """Energetic campaign: blue / white chevrons, large hero and yellow RRP bubble."""
    p = _customize_palette(RETAIL_PALETTES[variation % len(RETAIL_PALETTES)],editor,"retail")
    canvas = Image.new("RGBA", (W, H), p["blue"])
    d = ImageDraw.Draw(canvas)
    d.polygon([(0, 0), (W, 0), (W, 499), (0, 641)], fill=p["navy"])
    d.polygon([(935, 0), (1200, 0), (1200, 503), (1030, 516)], fill="#138FDA")
    d.polygon([(0, 632), (1200, 480), (1200, 650), (0, 788)], fill=WHITE)
    d.polygon([(0, 1167), (1200, 1082), (1200, 1500), (0, 1500)], fill=p["navy"])
    d.polygon([(0, 1170), (1200, 1083), (1200, 1112), (0, 1200)], fill=p["accent"])
    editor=editor or {}
    _background_art(d,editor.get("background","clean"),(0,38,1200,499),p["accent"],True,editor.get("shape_intensity",2))
    _laser(d)
    _fit(d, "PRODUCT PROMOTION  /  PART " + str(product.get("part", "")),
         (60, 214, 865, 255), (25, 22), "#6ED4FF", "bold", 1)
    _fit(d, concept.get("headline"), (56, 290, 1100, 493),
         _sizes((94,84,74,66,58,51,44),editor),WHITE,"bold",3)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(60,540,1125,614),(33,29,26,23),p["navy"],"bold",2)
    _fit(d, product.get("title"), (60, 661, 1125, 747),
         (42, 37, 33, 29, 25), p["navy"], "bold", 2)
    if editor.get("price_position")=="opposite":
        compose_product(canvas,photo,(382,754,1143,1150),editor,product,editor.get("_scene_bytes"))
        circle=(34,838,399,1203)
    else:
        compose_product(canvas,photo,(56,754,867,1150),editor,product,editor.get("_scene_bytes"))
        circle=(803,838,1168,1203)
    d=ImageDraw.Draw(canvas)
    _render_price(d,price,circle,
                  editor.get("price_style","bubble"),p["accent"],p["navy"])
    _features(d, concept, [(64, 1248, 1132, 1316), (64, 1321, 1132, 1392)],
              p["accent"], WHITE, (29, 26, 22, 19))
    _footer(d)
    return canvas


def _premium(concept, photo, product, price, variation, editor=None):
    """Clean premium creative: editorial navy title, framed hero, boxed RRP plaque."""
    p = _customize_palette(PREMIUM_PALETTES[variation % len(PREMIUM_PALETTES)],editor,"premium")
    canvas = Image.new("RGBA", (W, H), p["paper"])
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, W, 16), fill=p["navy"])
    d.polygon([(0, 1032), (1200, 960), (1200, 1500), (0, 1500)], fill=p["panel"])
    d.rectangle((59, 231, 1140, 237), fill=p["accent"])
    editor=editor or {}
    _background_art(d,editor.get("background","clean"),(25,250,1170,564),p["accent"],False,editor.get("shape_intensity",2))
    _laser(d, dark=True)
    _fit(d, "LASER PRODUCT PROMOTION", (59, 194, 890, 233),
         (23, 20), p["accent"], "bold", 1)
    _fit(d, concept.get("headline"), (60, 289, 1130, 484),
         _sizes((89,80,70,61,54,47),editor),p["navy"],"bold",3)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(61,488,1125,532),(27,24,21),p["navy"],"regular",1)
    _fit(d, "PART " + str(product.get("part", "")),
         (60, 541, 940, 582) if editor.get("show_subline") else (60,505,940,565),
         (39, 34, 30), p["accent"], "bold", 1)
    compose_product(canvas,photo,(57,594,1143,1038),editor,product,editor.get("_scene_bytes"))
    d = ImageDraw.Draw(canvas)
    opposite=editor.get("price_position")=="opposite"
    text_x=508 if opposite else 61
    text_x2=1135 if opposite else 692
    boxx=57 if opposite else 740
    _fit(d,product.get("title"),(text_x,1073,text_x2,1207),
         (43,39,34,30,26),p["navy"],"bold",3)
    _features(d,concept,[(text_x+2,1255,text_x2,1314),(text_x+2,1320,text_x2,1392)],
              p["accent"],p["navy"],(24,21,19,17))
    _render_price(d,price,(boxx,1100,boxx+403,1405),
                  editor.get("price_style","plaque"),p["accent"],p["navy"])
    _footer(d, dark=False)
    return canvas


def _trade(concept, photo, product, price, variation, editor=None):
    """Trade-counter campaign: dark navy, high-contrast diagonals and RRP ribbon."""
    p = _customize_palette(TRADE_PALETTES[variation % len(TRADE_PALETTES)],editor,"trade")
    canvas = Image.new("RGBA", (W, H), p["navy"])
    d = ImageDraw.Draw(canvas)
    d.polygon([(624, 0), (1200, 0), (1200, 1210), (816, 1210)], fill=p["mid"])
    d.polygon([(1062, 0), (1200, 0), (1200, 1109), (1153, 1103)], fill="#0F3659")
    for shift in range(5):
        d.line((665+shift*142, 1118, 1025+shift*142, 245), fill="#2B82AA", width=4)
    d.polygon([(0, 1159), (1200, 1055), (1200, 1112), (0, 1218)], fill=p["accent"])
    d.rectangle((0, 1210, W, H), fill="#081C31")
    editor=editor or {}
    _background_art(d,editor.get("background","clean"),(15,250,1200,1155),p["accent"],True,editor.get("shape_intensity",2))
    _laser(d)
    _fit(d, "TRADE PROMOTION   •   PART " + str(product.get("part", "")),
         (58, 199, 885, 250), (24, 21), p["accent"], "bold", 1)
    _fit(d, concept.get("headline"), (56, 304, 566, 668),
         _sizes((76,68,61,54,47,41,36,30),editor),WHITE,"bold",5)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(60,673,518,710),
             (23,20,18),p["pale"],"regular",1)
    d.rectangle((60, 715, 448, 726), fill=p["accent"])
    _fit(d, product.get("title"), (59, 770, 528, 952),
         (37, 33, 29, 26, 23), WHITE, "bold", 4)
    compose_product(canvas,photo,(548,370,1150,1070),editor,product,editor.get("_scene_bytes"))
    d = ImageDraw.Draw(canvas)
    _features(d, concept, [(59, 996, 508, 1065), (59, 1072, 508, 1152)],
              p["accent"], p["pale"], (23, 20, 18, 16))
    opposite=editor.get("price_position")=="opposite"
    price_style=editor.get("price_style","banner")
    if price_style=="banner":
        _fit(d,price["label"] if price["amount"] else "CURRENT PRICE",
             (500 if opposite else 60,1242,1144 if opposite else 700,1297),
             (28,25),p["accent"],"bold",1,"right" if opposite else "left")
        _fit(d,price["amount"] or "ON REQUEST",
             (290 if opposite else 56,1311,1144 if opposite else 943,1421),
             (100,89,77,65,55,46,39),WHITE,"bold",2,"right" if opposite else "left")
        if price["amount"]:
            _fit(d,price["vat"],(60 if opposite else 944,1355,280 if opposite else 1144,1411),
                 (25,22),WHITE,"bold",1)
    else:
        start=713 if opposite else 58
        end=1144 if opposite else 489
        badge_box=(start,1215,end,1428)
        _render_price(d,price,badge_box,price_style,p["accent"],p["navy"])
    _footer(d)
    return canvas


RENDERERS = {"retail": _retail, "premium": _premium, "trade": _trade}


def render_promo(concept, photo, product, distributor=None, editor=None):
    """Generate one professional 1200x1500 PNG; caller controls creative family."""
    family = concept.get("family", "retail")
    if family not in RENDERERS:
        raise ValueError("Unknown promotional design family")
    price = verified_price(product)
    variant = int(concept.get("variant", 0)) % 3
    opts=dict(editor) if isinstance(editor,dict) else {}
    opts.setdefault("display_mode","shadow")
    opts.setdefault("background","context")
    # True photographic advertisement rather than flat catalogue-box layouts.
    # Scene bytes originate only from a verified manufacturer image, a curated
    # Pexels photograph or a user-approved upload, never model-generated tools.
    from ai_cinematic import render_campaign
    from poster_quality import capture, review
    scene=opts.get("_scene_bytes") if opts.get("background") in (
        "context","workshop","bench","engine") else None
    # Quality gate: repair oversized product positioning, typography and
    # layouts automatically, without drawing invented product photography.
    # Each attempt is an independent render of an original manufacturer image.
    best=None
    for attempt in range(3):
        proposal=dict(concept)
        controls=dict(opts)
        if attempt==1:
            # Preserve the user's composition where possible. Reduce zoom,
            # cap offsets to safe ranges and first reflow typography.
            controls["product_scale"]=min(90,int(opts.get("product_scale",100)))
            controls["product_x"]=max(-30,min(30,int(opts.get("product_x",0))))
            controls["product_y"]=max(-30,min(30,int(opts.get("product_y",0))))
            controls["headline_size"]="small"
        elif attempt==2:
            controls["product_scale"]=90
            controls["product_x"]=0
            controls["product_y"]=0
            controls["headline_size"]="small"
            proposal["variant"]=(variant+1)%3
        with capture() as tracked:
            canvas=render_campaign(proposal,photo,product,price,
                int(proposal.get("variant",0)),controls,scene)
            _co_brand(canvas,distributor)
            out=io.BytesIO()
            canvas.convert("RGB").save(out,format="PNG",optimize=True)
            png=out.getvalue()
        quality=review(png,tracked,price,proposal,photo)
        quality["attempts"]=attempt+1
        quality["auto_corrected"]=attempt>0
        quality["layout_variant"]=int(proposal.get("variant",0))%3
        quality["effective_editor"]={key:controls[key] for key in (
            "product_scale","product_x","product_y","headline_size")
            if key in controls}
        if quality["passed"]:
            if isinstance(editor,dict) and isinstance(editor.get("_quality_report"),dict):
                editor["_quality_report"].update(quality)
            return png
        best=quality
    if isinstance(editor,dict) and isinstance(editor.get("_quality_report"),dict):
        editor["_quality_report"].update(best or {})
    raise RuntimeError("Poster quality check rejected this design: "+
        "; ".join((best or {}).get("issues") or ["unknown layout error"]))
