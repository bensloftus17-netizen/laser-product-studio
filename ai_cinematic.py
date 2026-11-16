"""Three cinematic, REAL-PHOTOGRAPHY automotive sales poster compositions.

This is a graphic/layout engine, not synthetic product rendering:
- Only genuine manufacturer product pixels are used for the hero.
- Background photography comes from verified manufacturer application shots,
  commercially licensed Pexels stock photos or editor-provided photographs.
- Claims, price and VAT are passed in from source-verified product records.
- All brand text is programmatically typeset for sharp, editable future exports.
"""
from __future__ import annotations

import io
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from ai_photo_effects import compose_product
from poster import font

W,H=1200,1500
NAVY="#061D34"; WHITE="#FFFFFF"; CYAN="#13B5EC"; PALE="#DDECF5"
COLOURS={
    "retail":(
        {"primary":"#067EC7","accent":"#F6D343","ink":"#061F38"},
        {"primary":"#0F6EBA","accent":"#F9A842","ink":"#061F38"},
        {"primary":"#164F9A","accent":"#D9E75B","ink":"#061F38"},
    ),
    "premium":(
        {"primary":"#0979B9","accent":"#E6F1F8","ink":"#0B2F50"},
        {"primary":"#149AC6","accent":"#F1E9D8","ink":"#0B2F50"},
        {"primary":"#387E98","accent":"#E8F4F4","ink":"#0B2F50"},
    ),
    "trade":(
        {"primary":"#057BB9","accent":"#F3B43F","ink":"#061F38"},
        {"primary":"#0F83BD","accent":"#40C1E8","ink":"#061F38"},
        {"primary":"#2D708E","accent":"#E5DB6B","ink":"#061F38"},
    ),
}

def _fit(d,text,rect,sizes=(62,55,48,40),fill=WHITE,kind="bold",lines=3,align="left"):
    from ai_promo_renderer import _fit as original
    return original(d,text,rect,sizes,fill,kind,lines,align)


def _brand(d,primary,part,family="retail"):
    from ai_promo_renderer import _laser
    # Each art direction has its own masthead tone and header silhouette.
    masthead={"retail":"#052B51","premium":"#0A395A","trade":"#061D35"}.get(family,"#052B51")
    d.polygon([(0,0),(565,0),(493,169),(0,169)],fill=masthead)
    d.polygon([(526,0),(578,0),(505,169),(475,169)],fill=primary)
    _laser(d,55,30,dark=False)
    d.rounded_rectangle((57,191,308,254),radius=3,fill=primary)
    _fit(d,"PART  "+str(part),(76,198,292,248),(36,31),WHITE,"bold",1)


def _scene_base(photo_bytes,style,product,variation=0):
    """Photo fills the page, with real photographic detail and brand-safe blue grade.

    If photography is unavailable, use a dark gradient, NEVER a fake rendered
    repair scene. This is deliberate and avoids implying a tool was used.
    """
    from ai_photo_effects import photo_backdrop
    canvas=Image.new("RGBA",(W,H),NAVY)
    if photo_bytes:
        try:
            shot=ImageOps.exif_transpose(Image.open(io.BytesIO(photo_bytes))).convert("RGB")
            shot.thumbnail((2500,2500),Image.Resampling.LANCZOS)
            # Vary crop from one composition to another, respecting portrait ads.
            cen=(.5,.48) if style=="retail" else ((.65,.47) if style=="premium" else (.4,.57))
            image=ImageOps.fit(shot,(W,H),method=Image.Resampling.LANCZOS,centering=cen)
            # Background is a contextual photograph, not the primary subject:
            # subdue colour/light and blur enough to lift the genuine product.
            image=ImageEnhance.Contrast(image).enhance(1.08)
            image=ImageEnhance.Color(image).enhance(.67)
            image=ImageEnhance.Brightness(image).enhance(.74)
            image=image.filter(ImageFilter.GaussianBlur(3.0))
            canvas.alpha_composite(image.convert("RGBA"))
        except (ValueError,OSError):
            pass
    # Multiply bottom and side darkness, not a simple opaque blue rectangle.
    overlay=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    for y in range(H):
        frac=y/H
        opacity=int(89+121*frac)
        d.line((0,y,W,y),fill=(4,18,33,opacity),width=1)
    canvas=Image.alpha_composite(canvas,overlay)
    return canvas


def _glass(canvas,box,colour=(4,24,43,206),radius=0):
    d=ImageDraw.Draw(canvas,"RGBA")
    if radius:d.rounded_rectangle(box,fill=colour,radius=radius)
    else:d.rectangle(box,fill=colour)


def _headline(d,concept,box,sizes,colour=WHITE,maxlines=4,editor=None):
    ratio={"small":.87,"normal":1,"large":1.13}.get((editor or {}).get("headline_size","normal"),1)
    return _fit(d,concept.get("headline"),box,
                tuple(max(23,int(v*ratio)) for v in sizes),
                colour,"bold",maxlines)


def _features(d,concept,boxes,primary=CYAN,fg=WHITE):
    """One large verified selling point beats several unreadable paragraphs."""
    features=[str(x).strip() for x in concept.get("features",[]) if str(x).strip()]
    if not features or not boxes:return
    x0,y0,x1,y1=boxes[0]
    d.rounded_rectangle((x0,y0+7,x0+9,y0+73),fill=primary,radius=4)
    _fit(d,features[0],(x0+28,y0,x1,y1),
         (36,33,30,27,23),fg,"regular",3)


def _product(canvas,photo,product,box,editor=None):
    opts=dict(editor or {})
    # Background was already photographed full-bleed; use only true product
    # pixels here. Never redraw or synthesise the kit or claimed use.
    opts["background"]="clean"
    opts["_scene_bytes"]=None
    if "product_scale" not in opts:opts["product_scale"]=121
    if "display_mode" not in opts:opts["display_mode"]="shadow"
    return compose_product(canvas,photo,box,opts,product)


def _footer(d,light=False):
    colour="#BFD2E2" if not light else "#466C85"
    d.line((54,1455,1145,1455),fill=colour,width=2)
    _fit(d,"DRAFT ARTWORK  •  VERIFY RRP & PRODUCT CLAIMS",
         (59,1464,1142,1497),(17,15,13),colour,"bold",1)


def _rrp(d,price,box,style,accent,ink="#071F37"):
    """Different strong promo price treatments share verified data and VAT."""
    x0,y0,x1,y1=map(int,box)
    amount=price.get("amount") or "ON REQUEST"
    label=price.get("label") if price.get("amount") else "PRICE"
    vat=price.get("vat") or ""
    if style=="bubble":
        side=min(x1-x0,y1-y0)
        x0+=((x1-x0)-side)//2;y0+=((y1-y0)-side)//2
        x1,y1=x0+side,y0+side
        d.ellipse((x0+9,y0+9,x1+9,y1+9),fill="#00192F")
        d.ellipse((x0,y0,x1,y1),fill=accent)
        d.ellipse((x0+11,y0+11,x1-11,y1-11),outline=WHITE,width=3)
        _fit(d,label,(x0+22,y0+45,x1-22,y0+87),(27,24,21),ink,"bold",1,"center")
        _fit(d,amount,(x0+19,y0+113,x1-19,y0+216),
             (69,60,51,42,33),ink,"bold",2,"center")
        if vat:_fit(d,vat,(x0+20,y0+233,x1-20,y0+276),(22,18),ink,"bold",1,"center")
        return
    if style=="plaque":
        d.polygon([(x0+28,y0),(x1,y0),(x1-25,y1),(x0,y1)],fill=WHITE)
        d.line([(x0+28,y0),(x1,y0),(x1-25,y1),(x0,y1),(x0+28,y0)],
               fill=accent,width=6,joint="curve")
        _fit(d,label,(x0+49,y0+22,x1-45,y0+72),(26,22),ink,"bold",1)
        _fit(d,amount,(x0+42,y0+79,x1-46,y1-23),
             (76,64,53,43,34),ink,"bold",2)
        if vat:_fit(d,vat,(x0+45,y1-41,x1-46,y1-12),(20,17),ink,"bold",1,"right")
        return
    # Strong split-colour banner/corner tag treatment
    if style=="tag":
        d.polygon([(x0+45,y0),(x1,y0),(x1,y1),(x0,y1),(x0+32,y0+37)],fill=accent)
        d.polygon([(x0+45,y0),(x0+45,y0+42),(x0,y0+42)],fill=WHITE)
    else:
        d.polygon([(x0,y0),(x1-38,y0),(x1,y1),(x0+33,y1)],fill=accent)
    _fit(d,label,(x0+60,y0+17,x1-65,y0+66),(31,26,22),ink,"bold",1)
    _fit(d,amount,(x0+55,y0+69,x1-63,y1-29),
         (91,79,66,55,44,36),ink,"bold",2)
    if vat:_fit(d,vat,(x0+58,y1-38,x1-66,y1-12),(21,18),ink,"bold",1,"right")


def _accent(editor,colour):
    custom=(editor or {}).get("accent")
    if isinstance(custom,str) and len(custom)==7 and custom[0]=="#":
        try:int(custom[1:],16);return custom
        except ValueError:pass
    return colour


def _retail(concept,photo,product,price,variation,editor,background):
    p=COLOURS["retail"][variation%3];blue=_accent(editor,p["primary"])
    yellow=_accent(editor,p["accent"])
    canvas=_scene_base(background,"retail",product,variation)
    d=ImageDraw.Draw(canvas,"RGBA")
    # Broad asymmetric, photo-revealing angular header plate.
    d.polygon([(0,0),(850,0),(641,800),(0,860)],fill=(3,23,45,231))
    d.polygon([(752,0),(834,0),(646,752),(597,752)],fill=blue)
    d.polygon([(0,742),(388,677),(388,1150),(0,1230)],fill=(2,30,57,185))
    d.polygon([(0,1270),(1200,1187),(1200,1500),(0,1500)],fill=(3,23,45,242))
    d.polygon([(0,1259),(1200,1176),(1200,1196),(0,1281)],fill=blue)
    _product(canvas,photo,product,(328,452,1190,1302),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    # Headline is drawn AFTER the cutout, so no product can conceal copy.
    d.polygon([(0,269),(705,265),(630,811),(0,856)],fill=(3,22,41,166))
    _brand(d,blue,product.get("part",""),family="retail")
    _headline(d,concept,(58,312,663,611),(81,72,63,54,46),WHITE,4,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(62,632,629,725),(31,27,24),PALE,"regular",2)
    _features(d,concept,[(62,945,414,1090)],blue)
    d=ImageDraw.Draw(canvas)
    price_style=editor.get("price_style","bubble")
    box=(822,1060,1168,1406) if editor.get("price_position")!="opposite" else (45,1070,391,1416)
    if price_style!="bubble":
        box=(190,1278,1110,1431) if editor.get("price_position")!="opposite" else (60,1278,975,1431)
    _rrp(d,price,box,price_style,yellow,p["ink"])
    _footer(d)
    return canvas


def _premium(concept,photo,product,price,variation,editor,background):
    p=COLOURS["premium"][variation%3];blue=_accent(editor,p["primary"])
    accent=_accent(editor,p["accent"])
    canvas=_scene_base(background,"premium",product,variation)
    d=ImageDraw.Draw(canvas,"RGBA")
    # Long diagonal left column with actual photo visible behind product.
    d.polygon([(0,0),(807,0),(541,1470),(0,1500)],fill=(4,25,44,239))
    d.polygon([(723,0),(751,0),(492,1470),(460,1497)],fill=blue)
    d.polygon([(0,1275),(1200,1138),(1200,1500),(0,1500)],fill=(3,22,39,220))
    _product(canvas,photo,product,(470,355,1190,1245),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,258),(657,245),(534,1130),(0,1193)],fill=(3,24,43,155))
    _brand(d,blue,product.get("part",""),family="premium")
    _headline(d,concept,(62,312,632,616),(81,71,62,55,45),WHITE,4,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(62,643,600,723),(32,28,24),PALE,"regular",2)
    d.rounded_rectangle((62,772,463,785),radius=4,fill=blue)
    _features(d,concept,[(62,875,477,1035)],blue)
    d=ImageDraw.Draw(canvas)
    price_style=editor.get("price_style","plaque")
    box=(560,1203,1140,1417) if editor.get("price_position")!="opposite" else (65,1208,670,1417)
    _rrp(d,price,box,price_style,accent,p["ink"])
    _footer(d)
    return canvas


def _trade(concept,photo,product,price,variation,editor,background):
    p=COLOURS["trade"][variation%3];blue=_accent(editor,p["primary"])
    accent=_accent(editor,p["accent"])
    canvas=_scene_base(background,"trade",product,variation)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,225),fill=(1,20,36,230))
    d.polygon([(0,218),(910,178),(785,654),(0,740)],fill=(2,24,44,224))
    d.polygon([(1140,0),(1200,0),(805,1250),(770,1250)],fill=blue)
    d.polygon([(0,1176),(1200,1115),(1200,1500),(0,1500)],fill=(3,20,38,246))
    d.polygon([(0,1165),(1200,1105),(1200,1124),(0,1184)],fill=blue)
    _product(canvas,photo,product,(205,459,1185,1206),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,252),(794,238),(727,663),(0,735)],fill=(3,22,40,160))
    _brand(d,blue,product.get("part",""),family="trade")
    _headline(d,concept,(59,284,780,573),(89,78,68,59,51),WHITE,4,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(62,593,761,663),(29,25,22),PALE,"regular",2)
    d=ImageDraw.Draw(canvas)
    # Grounded short feature strips; no claims fabricated by renderer.
    d.rounded_rectangle((55,884,400,1128),radius=15,fill=(5,30,49,225))
    _features(d,concept,[(76,934,381,1097)],blue)
    price_style=editor.get("price_style","banner")
    box=(475,1228,1142,1426) if editor.get("price_position")!="opposite" else (55,1228,805,1426)
    _rrp(d,price,box,price_style,accent,p["ink"])
    _footer(d)
    return canvas


def render_campaign(concept,photo,product,price,variation,editor=None,scene_photo=None):
    editor=dict(editor or {})
    family=concept.get("family","retail")
    if family not in ("retail","premium","trade"):
        raise ValueError("Unknown cinematic campaign family.")
    # Editor custom palette still works, via overlay-grade accent and warm price.
    return {"retail":_retail,"premium":_premium,"trade":_trade}[family](
        concept,photo,product,price,variation,editor,scene_photo)
