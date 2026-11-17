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

def _fit(d,text,rect,sizes=(62,55,48,40),fill=WHITE,kind="bold",lines=3,align="left",role="text"):
    from ai_promo_renderer import _fit as original
    return original(d,text,rect,sizes,fill,kind,lines,align,role)


def _brand(d,primary,part,family="retail"):
    from ai_promo_renderer import _laser
    # Each art direction has its own masthead tone and header silhouette.
    masthead={"retail":"#052B51","premium":"#0A395A","trade":"#061D35"}.get(family,"#052B51")
    d.polygon([(0,0),(565,0),(493,169),(0,169)],fill=masthead)
    d.polygon([(526,0),(578,0),(505,169),(475,169)],fill=primary)
    _laser(d,55,30,dark=False)
    d.rounded_rectangle((57,191,308,254),radius=3,fill=primary)
    _fit(d,"PART  "+str(part),(76,198,292,248),(36,31),WHITE,"bold",1)


def _scene_base(photo_bytes,style,product,variation=0,scene_style=None):
    """Photo fills the page, with real photographic detail and brand-safe blue grade.

    If photography is unavailable, use a dark gradient, NEVER a fake rendered
    repair scene. This is deliberate and avoids implying a tool was used.
    """
    scene_style=scene_style if isinstance(scene_style,dict) else {}
    canvas=Image.new("RGBA",(W,H),NAVY)
    if photo_bytes:
        try:
            shot=ImageOps.exif_transpose(Image.open(io.BytesIO(photo_bytes))).convert("RGB")
            shot.thumbnail((2500,2500),Image.Resampling.LANCZOS)
            # Vary crop from one composition to another, respecting portrait ads.
            cen=scene_style.get("crop") or (
                (.5,.48) if style=="retail" else ((.65,.47) if style=="premium" else (.4,.57)))
            if not isinstance(cen,(list,tuple)) or len(cen)!=2:cen=(.5,.5)
            cen=tuple(max(.1,min(.9,float(v))) for v in cen)
            image=ImageOps.fit(shot,(W,H),method=Image.Resampling.LANCZOS,centering=cen)
            # Background is a contextual photograph, not the primary subject:
            # subdue colour/light and blur enough to lift the genuine product.
            image=ImageEnhance.Contrast(image).enhance(1.08)
            image=ImageEnhance.Color(image).enhance(
                float(scene_style.get("colour",.67)))
            image=ImageEnhance.Brightness(image).enhance(
                max(.4,min(1.0,1-float(scene_style.get("darkness",.26)))))
            image=image.filter(ImageFilter.GaussianBlur(
                max(0,min(8,float(scene_style.get("blur",3.0))))))
            canvas.alpha_composite(image.convert("RGBA"))
        except (ValueError,OSError):
            pass
    # AI-selected graphic motifs are painted only into the real scene layer,
    # BEFORE product cutouts, headlines and verified pricing are drawn.
    from promo_art_direction import draw_background_motif
    canvas=draw_background_motif(canvas,scene_style)
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
                colour,"bold",maxlines,role="headline")


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
    from poster_quality import record_area
    record_area("price",box)
    amount=price.get("amount") or "ON REQUEST"
    label=price.get("label") if price.get("amount") else "PRICE"
    vat=price.get("vat") or ""
    if style=="sticker":
        # Jagged promotional sticker: the source price itself never changes.
        import math
        cx,cy=(x0+x1)/2,(y0+y1)/2
        radius=min(x1-x0,y1-y0)*.45
        points=[]
        for j in range(32):
            theta=(j/32)*math.tau-math.pi/2
            rad=radius*(1 if j%2==0 else .89)
            points.append((int(cx+math.cos(theta)*rad),
                           int(cy+math.sin(theta)*rad)))
        d.ellipse((cx-radius-4,cy-radius+6,cx+radius+6,cy+radius+14),
                  fill="#092A44")
        d.polygon(points,fill=accent)
        _fit(d,label,(x0+37,cy-radius*.62,x1-37,cy-radius*.26),
             (28,24,20),ink,"bold",1,"center")
        _fit(d,amount,(x0+35,cy-radius*.19,x1-35,cy+radius*.35),
             (72,63,55,44,36),ink,"bold",2,"center")
        if vat:
            _fit(d,vat,(x0+39,cy+radius*.43,x1-39,cy+radius*.69),
                 (23,20,18),ink,"bold",1,"center")
        return
    if style=="corner":
        # Folded, angled corner ticket with a contrasting top fold.
        d.polygon([(x0+42,y0),(x1,y0),(x1,y1-32),
                   (x1-40,y1),(x0,y1),(x0,y0+42)],fill=accent)
        d.polygon([(x0+42,y0),(x0+42,y0+42),(x0,y0+42)],
                  fill="#FFFFFF")
        d.polygon([(x1-40,y1),(x1-40,y1-40),(x1,y1-32)],
                  fill="#0C3652")
        _fit(d,label,(x0+54,y0+16,x1-50,y0+61),
             (29,25,22),ink,"bold",1)
        _fit(d,amount,(x0+48,y0+76,x1-56,y1-52),
             (79,68,58,49,40),ink,"bold",2)
        if vat:
            _fit(d,vat,(x0+49,y1-43,x1-71,y1-17),
                 (20,18),ink,"bold",1)
        return
    if style=="panel":
        # Large two-tier promotional panel, distinct from the white plaque
        # and from a single-colour banner.
        d.rounded_rectangle((x0,y0,x1,y1),radius=20,
                            fill="#FFFFFF",outline=accent,width=5)
        header_h=min(66,int((y1-y0)*.33))
        d.rounded_rectangle((x0+5,y0+5,x1-5,y0+header_h),
                            radius=13,fill=accent)
        _fit(d,label,(x0+30,y0+16,x1-27,y0+header_h-5),
             (29,25,21),ink,"bold",1)
        _fit(d,amount,(x0+27,y0+header_h+10,x1-27,y1-41),
             (54,48,43,38,34,29) if amount=="ON REQUEST"
             else (85,73,62,52,41), "#061F38","bold",
             1 if amount=="ON REQUEST" else 2)
        if vat:
            _fit(d,vat,(x0+30,y1-36,x1-27,y1-12),
                 (21,19),"#061F38","bold",1,"right")
        return
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



def _photo_stage(photo_bytes, region, darken=.12, blur=2.2, scene_style=None):
    """Crop REAL application/background photography to a given campaign region."""
    x0,y0,x1,y1=map(int,region)
    w,h=x1-x0,y1-y0
    scene_style=scene_style if isinstance(scene_style,dict) else {}
    if not photo_bytes:
        return Image.new("RGBA",(w,h),"#D3E1E8")
    try:
        source=ImageOps.exif_transpose(Image.open(io.BytesIO(photo_bytes))).convert("RGB")
        source.thumbnail((2400,2400),Image.Resampling.LANCZOS)
        centre=scene_style.get("crop",(.5,.5))
        if not isinstance(centre,(tuple,list)) or len(centre)!=2:centre=(.5,.5)
        centre=tuple(max(.1,min(.9,float(v))) for v in centre)
        img=ImageOps.fit(source,(w,h),method=Image.Resampling.LANCZOS,centering=centre)
        img=ImageEnhance.Color(img).enhance(
            float(scene_style.get("colour",.7)))
        img=ImageEnhance.Brightness(img).enhance(
            max(.43,1-float(scene_style.get("darkness",darken))))
        blur=max(0,min(8,float(scene_style.get("blur",blur))))
        if blur:img=img.filter(ImageFilter.GaussianBlur(blur))
        from promo_art_direction import draw_background_motif
        return draw_background_motif(img,scene_style)
    except (OSError,ValueError):
        return Image.new("RGBA",(w,h),"#D3E1E8")


def _small_label(d,label,box,colour=WHITE):
    return _fit(d,label,box,(27,24,21,18),colour,"bold",1)


def _retail(concept,photo,product,price,variation,editor,background):
    """RETAIL: cobalt/yellow high-impact counter promotion.

    Full-width bright campaign, enormous product, headline within a white
    angular ribbon and an unmistakable oversized RRP bubble. No side-column.
    """
    p=COLOURS["retail"][variation%3]
    royal=("#056AB7","#0755A1","#1456A8")[variation%3]
    accent=_accent(editor,p["accent"])
    canvas=Image.new("RGBA",(W,H),royal)
    # Real workshop photography is a deliberately limited band rather than
    # the same full-bleed image treatment used by Trade.
    canvas.alpha_composite(_photo_stage(
        background,(0,515,1200,1224),.36,3,editor.get("_scene_style")), (0,515))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,0),(1200,0),(1200,495),(0,550)],fill=(2,61,118,255))
    d.polygon([(0,469),(1200,427),(1200,486),(0,532)],fill=accent)
    d.polygon([(0,1192),(1200,1103),(1200,1500),(0,1500)],fill=(3,39,76,247))
    d.polygon([(0,1182),(1200,1094),(1200,1118),(0,1207)],fill=accent)
    # Big authentic tool with an isolated transparent silhouette.
    _product(canvas,photo,product,(46,505,1155,1241),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,288),(1140,288),(1070,492),(0,492)],fill=(255,255,255,248))
    d.polygon([(0,498),(1082,498),(1082,514),(0,514)],fill=accent)
    _brand(d,p["primary"],product.get("part",""),family="retail")
    _fit(d,concept.get("focus_label","TRADE COUNTER OFFER"),(690,98,1139,152),
         (29,25,23),accent,"bold",1,"right")
    _headline(d,concept,(61,321,1035,465),(89,80,69,61,53),
              "#062D4D",2,editor)
    # Pricing dominates; unlike Premium/Trade it lives in an oversized circle.
    price_style=editor.get("price_style","bubble")
    box=(798,1060,1178,1440) if editor.get("price_position")!="opposite" else (27,1060,407,1440)
    if price_style!="bubble":
        box=(530,1250,1160,1436) if editor.get("price_position")!="opposite" else (39,1250,672,1436)
    d=ImageDraw.Draw(canvas)
    _rrp(d,price,box,price_style,accent,_readable_ink(accent,p["ink"]))
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(47,1205,770,1282),
             (32,29,26,23),WHITE,"bold",2)
    _features(d,concept,[(53,1324,760,1409)],accent)
    _footer(d)
    return canvas


def _premium(concept,photo,product,price,variation,editor,background):
    """PREMIUM: bright editorial design, significant white space and true photo.

    No dark overlay on the typography, no angular retail masthead and no
    circular price burst. Photography occupies an intentional right-hand
    column, product sits across the boundary at a larger scale.
    """
    p=COLOURS["premium"][variation%3]
    ink="#082D4C";blue=p["primary"];accent=_accent(editor,blue)
    paper=("#FBFBF8","#F8FBFD","#F7FAF9")[variation%3]
    canvas=Image.new("RGBA",(W,H),paper)
    # Manufacturer product is NOT inside a white photographic box. This light
    # art direction uses a faded real workshop photo only in right column.
    scene=(676,398,1200,1198)
    canvas.alpha_composite(_photo_stage(
        background,scene,.36,4,editor.get("_scene_style")), (scene[0],scene[1]))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,14),fill=blue)
    d.rectangle((0,394,1200,413),fill=blue)
    d.rectangle((58,456,657,1170),fill=(234,241,245,255))
    d.rectangle((657,413,676,1198),fill=blue)
    # Hero image centred across the pale and photographic halves.
    _product(canvas,photo,product,(78,459,1141,1153),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    from ai_promo_renderer import _laser
    _laser(d,55,40,dark=True)
    _fit(d,concept.get("focus_label","LASER / PRODUCT SPOTLIGHT"),(703,107,1141,151),
         (28,25,21),blue,"bold",1,"right")
    _fit(d,"PART  "+str(product.get("part","")),(56,201,720,256),
         (40,36,31),blue,"bold",1)
    _headline(d,concept,(55,266,1139,390),(87,78,69,60,52),
              ink,2,editor)
    # Extra white content panel below photo keeps RRP separate from the hero.
    d.rectangle((0,1198,1200,1500),fill=paper)
    d.rectangle((0,1198,1200,1214),fill=blue)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(58,1234,636,1294),
             (31,27,24),ink,"regular",2)
    _features(d,concept,[(59,1316,626,1408)],blue,ink)
    price_style=editor.get("price_style","plaque")
    box=(705,1241,1152,1429) if editor.get("price_position")!="opposite" else (57,1241,506,1429)
    d=ImageDraw.Draw(canvas)
    _rrp(d,price,box,price_style,accent,_readable_ink(accent,ink))
    _footer(d,light=True)
    return canvas


def _trade(concept,photo,product,price,variation,editor,background):
    """TRADE: cinematic workshop scene, tool dominates upper image, bottom copy.

    No left-column dark navy title. The product sits against a full-bleed real
    photo; an authoritative dark bottom strip carries copy and a huge banner.
    """
    p=COLOURS["trade"][variation%3]
    blue=p["primary"];accent=_accent(editor,p["accent"])
    canvas=_scene_base(background,"trade",product,variation,editor.get("_scene_style"))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,234),fill=(2,19,35,225))
    d.polygon([(0,237),(1200,220),(1200,251),(0,266)],fill=blue)
    # The open workshop/photo area covers most of the composition.
    _product(canvas,photo,product,(71,265,1170,1020),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,995),(1200,937),(1200,1500),(0,1500)],
              fill=(3,20,37,247))
    d.polygon([(0,987),(1200,929),(1200,948),(0,1006)],fill=blue)
    _brand(d,blue,product.get("part",""),family="trade")
    _fit(d,concept.get("focus_label","WORKSHOP ESSENTIALS"),(728,90,1138,146),
         (29,26,22),accent,"bold",1,"right")
    _headline(d,concept,(51,1042,1145,1201),
              (91,81,71,61,53),WHITE,2,editor)
    if editor.get("show_subline"):
        _fit(d,concept.get("subline"),(55,1220,702,1275),
             (28,25,22),PALE,"regular",2)
    _features(d,concept,[(57,1315,710,1400)],blue)
    # Wide RRP banner running across the lower right in contrast to Retail's
    # price bubble and Premium's small boxed price.
    price_style=editor.get("price_style","banner")
    box=(747,1225,1152,1427) if editor.get("price_position")!="opposite" else (45,1225,458,1427)
    if price_style=="banner":
        box=(696,1217,1154,1430) if editor.get("price_position")!="opposite" else (50,1217,511,1430)
    d=ImageDraw.Draw(canvas)
    _rrp(d,price,box,price_style,accent,_readable_ink(accent,p["ink"]))
    _footer(d)
    return canvas


def render_campaign(concept,photo,product,price,variation,editor=None,scene_photo=None):
    editor=dict(editor or {})
    family=concept.get("family","retail")
    if family not in ("retail","premium","trade"):
        raise ValueError("Unknown photographic campaign family")
    layout=int(variation)%3
    if layout in (1,2):
        from ai_variant_layouts import render_variant
        return render_variant(family,layout,concept,photo,product,price,editor,scene_photo)
    return {"retail":_retail,"premium":_premium,"trade":_trade}[family](
        concept,photo,product,price,variation,editor,scene_photo)
