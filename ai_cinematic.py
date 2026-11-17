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
        # A plaque always has white paper; text stays navy regardless of the
        # custom accent (which may itself be dark enough to need white text).
        plaque_ink="#061F38"
        d.polygon([(x0+28,y0),(x1,y0),(x1-25,y1),(x0,y1)],fill=WHITE)
        d.line([(x0+28,y0),(x1,y0),(x1-25,y1),(x0,y1),(x0+28,y0)],
               fill=accent,width=6,joint="curve")
        _fit(d,label,(x0+49,y0+22,x1-45,y0+72),(26,22),plaque_ink,"bold",1)
        _fit(d,amount,(x0+42,y0+79,x1-46,y1-23),
             (76,64,53,43,34),plaque_ink,"bold",2)
        if vat:_fit(d,vat,(x0+45,y1-41,x1-46,y1-12),(20,17),plaque_ink,"bold",1,"right")
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


def _readable_ink(accent,default="#061F38"):
    """Keep RRP legible even when the user picks a dark custom badge colour."""
    try:
        r,g,b=(int(accent[i:i+2],16) for i in (1,3,5))
        luminance=.2126*r+.7152*g+.0722*b
        return WHITE if luminance<135 else default
    except (TypeError,ValueError):
        return default



def _photo_stage(photo_bytes, region, darken=.12, blur=2.2):
    """Crop REAL application/background photography to a given campaign region."""
    x0,y0,x1,y1=map(int,region)
    w,h=x1-x0,y1-y0
    if not photo_bytes:
        return Image.new("RGBA",(w,h),"#D3E1E8")
    try:
        source=ImageOps.exif_transpose(Image.open(io.BytesIO(photo_bytes))).convert("RGB")
        source.thumbnail((2400,2400),Image.Resampling.LANCZOS)
        img=ImageOps.fit(source,(w,h),method=Image.Resampling.LANCZOS)
        img=ImageEnhance.Color(img).enhance(.7)
        img=ImageEnhance.Brightness(img).enhance(max(.48,1-darken))
        if blur:img=img.filter(ImageFilter.GaussianBlur(blur))
        return img.convert("RGBA")
    except (OSError,ValueError):
        return Image.new("RGBA",(w,h),"#D3E1E8")


def _small_label(d,label,box,colour=WHITE):
    return _fit(d,label,box,(27,24,21,18),colour,"bold",1)


def _retail(concept,photo,product,price,variation,editor,background):
    """RETAIL: central floating product, horizontal headline and huge RRP burst.

    Distinct from other campaign families: product centred in photography
    and a circular callout, not a persistent left-hand title strip.
    """
    p=COLOURS["retail"][variation%3];blue=p["primary"]
    accent=_accent(editor,p["accent"])
    canvas=_scene_base(background,"retail",product,variation)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,263),fill=(2,23,43,240))
    d.polygon([(0,249),(1200,222),(1200,270),(0,306)],fill=blue)
    d.polygon([(0,467),(1200,420),(1200,500),(0,551)],fill=(7,60,101,105))
    d.polygon([(0,1170),(1200,1075),(1200,1500),(0,1500)],fill=(2,22,40,246))
    d.polygon([(0,1161),(1200,1066),(1200,1082),(0,1180)],fill=blue)
    # The original manufacturer tool sits centre stage against real photo.
    _product(canvas,photo,product,(94,505,1055,1202),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    # Strong solid headline above the product, never behind it.
    d.rounded_rectangle((40,303,1160,511),radius=18,fill=(2,23,43,236))
    _brand(d,blue,product.get("part",""),family="retail")
    _small_label(d,"TRADE COUNTER PROMOTION",(627,82,1128,135),accent)
    _headline(d,concept,(73,336,1119,479),(86,77,68,59,52,45),WHITE,2,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(57,1190,785,1256),
             (29,26,23,20),PALE,"regular",2)
    _features(d,concept,[(62,1280,748,1394)],blue,WHITE)
    price_style=editor.get("price_style","bubble")
    if price_style=="bubble":
        box=(809,1066,1166,1423) if editor.get("price_position")!="opposite" else (36,1066,393,1423)
    else:
        box=(741,1234,1162,1430) if editor.get("price_position")!="opposite" else (42,1234,463,1430)
    d=ImageDraw.Draw(canvas)
    _rrp(d,price,box,price_style,accent,_readable_ink(accent,p["ink"]))
    _footer(d)
    return canvas


def _premium(concept,photo,product,price,variation,editor,background):
    """PREMIUM: clean *light* editorial ad with a contained photo stage.

    Its composition deliberately uses negative space, navy-on-white typography,
    an uncluttered product hero and an outlined RRP plaque.
    """
    p=COLOURS["premium"][variation%3]
    blue=p["primary"];accent=_accent(editor,blue)
    paper=("#F8FBFC","#FAFBF7","#F6FAFA")[variation%3]
    canvas=Image.new("RGBA",(W,H),paper)
    stage=(532,468,1200,1234)
    canvas.alpha_composite(_photo_stage(background,stage,darken=.30,blur=4),
                           (stage[0],stage[1]))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,19),fill=blue)
    d.rectangle((0,466,532,1237),fill=("#EAF2F7","#F1F2EB","#E9F3F2")[variation%3])
    d.rectangle((532,466,545,1237),fill=blue)
    d.rectangle((0,1238,1200,1500),fill=paper)
    # Product is composed BEFORE top copy so any oversize image cannot
    # obscure the real text; hero appears on two different background zones.
    _product(canvas,photo,product,(148,480,1100,1205),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    # Deliberate editorial brand masthead (not retail's dark diagonal).
    from ai_promo_renderer import _laser
    _laser(d,57,45,dark=True)
    d.rounded_rectangle((57,205,337,264),radius=5,fill=blue)
    _small_label(d,"PART  "+str(product.get("part","")),(75,215,320,257),WHITE)
    _small_label(d,"PRODUCT SPOTLIGHT",(778,91,1146,151),blue)
    d.line((56,304,1143,304),fill=blue,width=5)
    _headline(d,concept,(55,335,1145,449),
              (85,74,64,54,47),p["ink"],2,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(57,1065,486,1183),
             (32,28,24,21),p["ink"],"regular",3)
    _features(d,concept,[(55,1268,593,1399)],blue,p["ink"])
    price_style=editor.get("price_style","plaque")
    box=(688,1247,1150,1423) if editor.get("price_position")!="opposite" else (56,1247,520,1423)
    d=ImageDraw.Draw(canvas)
    _rrp(d,price,box,price_style,accent,_readable_ink(accent,p["ink"]))
    _footer(d,light=True)
    return canvas


def _trade(concept,photo,product,price,variation,editor,background):
    """TRADE: split-screen workshop photograph and strong right-hand text.

    The product occupies an entire LEFT hero image zone, while copy is in a
    dedicated RIGHT column; the bottom contains a full-width price banner.
    """
    p=COLOURS["trade"][variation%3]
    blue=p["primary"];accent=_accent(editor,p["accent"])
    canvas=_scene_base(background,"trade",product,variation)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,247),fill=(2,22,40,241))
    d.polygon([(722,248),(1200,248),(1200,1190),(722,1190)],
              fill=(3,23,40,238))
    d.polygon([(705,246),(733,246),(733,1190),(705,1190)],fill=blue)
    d.polygon([(0,1190),(1200,1190),(1200,1500),(0,1500)],fill=(3,21,39,248))
    d.rectangle((0,1180,1200,1202),fill=blue)
    _product(canvas,photo,product,(25,315,750,1180),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    _brand(d,blue,product.get("part",""),family="trade")
    _small_label(d,"WORKSHOP CAMPAIGN",(798,93,1160,158),accent)
    _small_label(d,"APPLICATION / TOOL",(758,307,1154,368),accent)
    _headline(d,concept,(755,410,1155,770),
              (75,67,59,52,45,38),WHITE,5,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(759,800,1153,922),
             (30,26,23,20),PALE,"regular",3)
    _features(d,concept,[(756,973,1152,1120)],blue,WHITE)
    price_style=editor.get("price_style","banner")
    box=(185,1240,1146,1434) if editor.get("price_position")!="opposite" else (57,1240,1017,1434)
    d=ImageDraw.Draw(canvas)
    _rrp(d,price,box,price_style,accent,_readable_ink(accent,p["ink"]))
    _footer(d)
    return canvas


def render_campaign(concept,photo,product,price,variation,editor=None,scene_photo=None):
    editor=dict(editor or {})
    family=concept.get("family","retail")
    if family not in ("retail","premium","trade"):
        raise ValueError("Unknown photographic campaign family.")
    return {"retail":_retail,"premium":_premium,"trade":_trade}[family](
        concept,photo,product,price,variation,editor,scene_photo)
