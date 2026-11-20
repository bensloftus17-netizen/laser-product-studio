"""AI-composed, safe Pillow render of arbitrarily placed marketing zones.

Only the *layout* is generative. All visible words are official manufacturer
facts, the verified UK price, fixed review text, or brand text. Real source
product pixels are placed without any generative alteration or white card.
"""
from __future__ import annotations

import io
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageFilter

from poster import font
from poster_quality import record_text, record_area
from campaign_role_posters import actual_scene, brand, co_brand, product_photo, _wrap, _size
from promo_art_direction import draw_background_motif
from creative_director import validate_brief
from creative_expression import express_background
from ai_promo_renderer import verified_price

W,H=1200,1500
INK="#061A30"
WHITE="#FFFFFF"


def _box(region):
    x,y,w,h=region
    return (round(x*W/1000),round(y*H/1000),
            round((x+w)*W/1000),round((y+h)*H/1000))


def _text(draw,text,rect,*,base=64,minsize=20,bold=True,maxlines=4,role="text",colour=WHITE):
    """Never crop, overlap or silently ellipsise a factual sentence."""
    x0,y0,x1,y1=rect
    width=x1-x0
    height=y1-y0
    if not str(text or "").strip():
        raise ValueError("Missing verified poster text")
    for size in range(base,minsize-1,-2):
        rows=_wrap(draw,text,width,size,bold)
        step=round(size*1.24)
        face=font(size,"bold" if bold else "regular")
        # Line-count * leading is not a pixel-boundary check: ascenders,
        # descenders and glyph bearings can cross a small AI-authored zone.
        # Measure each glyph's actual painted extents *before* drawing.
        fits=(len(rows)<=maxlines and len(rows)*step<=height)
        if fits:
            for j,line in enumerate(rows):
                left,top,right,bottom=draw.textbbox(
                    (x0,y0+j*step),line,font=face)
                if (left<x0 or right>x1 or top<y0 or bottom>y1):
                    fits=False
                    break
        if fits:
            for j,line in enumerate(rows):
                draw.text((x0,y0+j*step),line,font=face,fill=colour)
            record_text(text,rect,rows,size,role)
            return
    raise ValueError("Verified copy does not fit AI-designed text zone")


def _background(scene,brief,variant):
    """The chosen real workshop photo or a non-white branded composition."""
    image=Image.new("RGBA",(W,H),INK)
    if brief["background"]=="workshop-photo" and scene:
        actual_scene(image,scene,(0,0,W,H),
                     brightness=(.52,.46,.57)[variant%3],blur=2.3,
                     focus=brief["photo_focus"])
    else:
        d=ImageDraw.Draw(image,"RGBA")
        for y in range(0,H,18):
            t=y/H
            d.rectangle((0,y,W,y+18),fill=(6+round(12*t),31+round(30*t),53+round(29*t),255))
        if brief["background"]=="industrial":
            for x in range(0,W,110):
                d.line((x,135,x,H-120),fill=(77,171,220,35),width=2)
            for y in range(190,H-150,130):
                d.line((40,y,W-40,y),fill=(77,171,220,30),width=2)
    image=draw_background_motif(image,{"graphic_motif":brief["motif"]})
    # Always darken only the background for white copy contrast. Tool pixels
    # are composited afterwards, unmodified.
    tint=Image.new("RGBA",(W,H),(4,20,35,64 if brief["mood"]=="energetic" else 91))
    image=Image.alpha_composite(image,tint)
    # Model-authored abstract shapes: freely positioned and coloured within
    # brand-approved inks, rendered behind all genuine tool and text layers.
    shape_layer=Image.new("RGBA",(W,H),(0,0,0,0))
    painter=ImageDraw.Draw(shape_layer,"RGBA")
    from PIL import ImageColor
    ink_map={"accent":ImageColor.getrgb(brief["accent"]),
             "cyan":(20,174,226),"white":(255,255,255)}
    for shape in brief.get("shapes",[]):
        x0,y0,x1,y1=_box(shape["box"])
        rgba=(*ink_map[shape["ink"]],shape["opacity"])
        kind=shape["kind"]
        if kind=="panel":
            painter.rounded_rectangle((x0,y0,x1,y1),radius=22,fill=rgba)
        elif kind=="outline":
            painter.rounded_rectangle((x0,y0,x1,y1),radius=18,
                                      outline=rgba,width=5)
        elif kind=="circle":
            painter.ellipse((x0,y0,x1,y1),outline=rgba,width=7)
        elif kind=="ribbon":
            painter.polygon(((x0+min(60,x1-x0),y0),(x1,y0),
                             (x1-min(60,x1-x0),y1),(x0,y1)),fill=rgba)
        elif kind=="line":
            painter.line((x0,y0,x1,y1),fill=rgba,width=7)
    return Image.alpha_composite(image,shape_layer)


def _role_art_direction(image,brief,role):
    """Six visibly different branded compositions underneath authentic pixels.

    AI controls which family to use and the free-positioned headline/photo
    zones. These are intentionally different *architectures*, not small motif
    or stripe variations. Tool photos and factual words are layered later.
    """
    from PIL import ImageColor
    accent=ImageColor.getrgb(brief["accent"])
    family=brief.get("creative_family") or {
        "technical_application":"engineering_grid",
        "price_promo":"commercial_burst",
        "product_selected":"premium_spotlight"}.get(role,"editorial_split")
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer,"RGBA")
    bx=_box(brief["zones"]["product"])
    cx=(bx[0]+bx[2])//2
    cy=(bx[1]+bx[3])//2
    if family=="engineering_grid":
        d.rectangle((0,180,W,1390),fill=(3,35,55,105))
        for x in range(30,W,92):
            d.line((x,190,x,1390),fill=(68,184,223,64),width=2)
        for y in range(190,1390,92):
            d.line((28,y,W-28,y),fill=(67,184,224,50),width=2)
        for y in range(265,1320,80):
            d.line((53,y,113,y),fill=(*accent,165),width=5)
        d.rectangle((52,230,68,1310),fill=(*accent,135))
        d.arc((cx-300,cy-300,cx+300,cy+300),
              10,330,fill=(*accent,115),width=6)
    elif family=="commercial_burst":
        d.polygon(((0,360),(W,230),(W,870),(0,1070)),
                  fill=(*accent,178))
        d.polygon(((0,1040),(W,720),(W,955),(0,1290)),
                  fill=(12,117,185,190))
        d.polygon(((0,1260),(W,1040),(W,1325),(0,1370)),
                  fill=(245,185,39,170))
        for offset in range(4):
            d.line(((0,1150-offset*38),(W,750-offset*38)),
                   fill=(255,235,132,116),width=7)
        # Legible white copy even when a model positions text over bright art.
        for key in ("headline","proof","price"):
            if key in brief["zones"]:
                x0,y0,x1,y1=_box(brief["zones"][key])
                d.rounded_rectangle((x0-14,y0-13,x1+14,y1+13),
                                    radius=18,fill=(5,26,43,219),
                                    outline=(255,213,90,162),width=3)
    elif family=="premium_spotlight":
        d.rectangle((0,180,W,1390),fill=(2,13,31,164))
        for radius,alpha,width in ((520,18,40),(435,54,20),
                                   (350,100,10),(275,120,4)):
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),
                      outline=(*accent,alpha),width=width)
        d.rounded_rectangle((45,220,W-45,1350),radius=36,
                            outline=(*accent,85),width=2)
        d.rectangle((82,1340,W-82,1350),fill=(*accent,160))
    elif family=="workshop_motion":
        d.polygon(((0,215),(670,215),(W,940),(W,1240),(650,560),(0,400)),
                  fill=(1,132,168,137))
        for shift in (-250,20,290):
            d.polygon(((shift,760),(shift+105,760),
                       (shift+830,1335),(shift+670,1335)),
                      fill=(30,198,217,139))
        d.arc((cx-390,cy-390,cx+390,cy+390),
              10,320,fill=(*accent,162),width=12)
        d.polygon(((0,1220),(W,900),(W,1320),(0,1370)),
                  fill=(4,29,47,194))
    elif family=="editorial_split":
        d.polygon(((0,180),(W//2,180),(W//3,1380),(0,1380)),
                  fill=(16,83,123,190))
        d.polygon(((W//2,180),(W,180),(W,1380),(W//3,1380)),
                  fill=(4,22,38,115))
        d.line((W//2,195,W//3,1365),fill=(*accent,205),width=9)
        d.line((76,1314,W-65,1314),fill=(*accent,122),width=5)
        for x in (80,103,126):
            d.line((x,240,x,480),fill=(212,239,247,118),width=3)
    elif family=="toolkit_coverage":
        d.rectangle((0,180,W,1390),fill=(7,66,76,118))
        for j in range(5):
            y=335+j*189
            d.rounded_rectangle((72,y,1130,y+126),radius=14,
                                fill=(9,35,53,127),
                                outline=(*accent,148),width=3)
            d.rectangle((85,y+16,102,y+105),fill=(*accent,183))
        for x in (130,335,540,745,950):
            d.line((x,222,x,270),fill=(208,239,246,158),width=5)
        d.rounded_rectangle((68,244,W-68,1350),radius=25,
                            outline=(*accent,120),width=4)
    return Image.alpha_composite(image,layer)


def render_creative_canvas(product,official_photo,concept,scene=None,
                           distributor=None,variant=0,text_safety=0):
    brief=validate_brief(concept.get("creative_canvas"),concept.get("campaign_role"))
    if not brief:
        raise ValueError("Invalid AI creative layout")
    if variant not in (0,1,2):
        raise ValueError("Unknown candidate variation")
    if text_safety not in (0,1,2):
        raise ValueError("Unknown text recovery level")
    image=_background(scene,brief,variant)
    image=_role_art_direction(image,brief,concept.get("campaign_role"))
    # The former dark-navy underpainting made even completely different AI
    # canvases look alike. Let Gemini's safe colour and compositional choice
    # alter broad real pixels behind the protected official product photo.
    image=express_background(
        image,brief["creative_palette"],brief["visual_treatment"],
        zones={k:_box(v) for k,v in brief["zones"].items() if k!="product"},
        variant=variant,hero_treatment=brief["hero_treatment"],inplace=True)
    accent=brief["accent"]
    d=ImageDraw.Draw(image,"RGBA")
    # Fixed brand safe areas; the art direction controls all other geometry.
    d.rectangle((0,0,W,176),fill=(3,17,32,248))
    d.rectangle((0,173,W,180),fill=accent)
    d.rectangle((0,1390,W,H),fill=(3,17,32,250))
    d.rectangle((48,1392,W-48,1399),fill=accent)
    brand(d,product.get("part",""))
    co_brand(image,distributor)

    zones=brief["zones"]
    hero=_box(zones["product"])
    # Graphic art may vary without moving facts off the model's safe canvas.
    d=ImageDraw.Draw(image,"RGBA")
    if brief["mood"] in ("bold","energetic"):
        x0,y0,x1,y1=hero
        d.rounded_rectangle((max(5,x0-15),max(181,y0-15),
                             min(W-5,x1+15),min(1380,y1+15)),
                            radius=32,outline=(24,167,218,100),width=3)
    emphasis=(concept.get("creative_direction") or {}).get("hero_emphasis","balanced")
    factor={"dominant":1.045,"balanced":.98,"supporting":.93}.get(emphasis,.98)
    product_photo(image,official_photo,hero,scale=(.94,1.0,.98)[variant]*factor)

    d=ImageDraw.Draw(image,"RGBA")
    headline=_box(zones["headline"])
    # Art-direction determines the typographic hierarchy, not a fixed family.
    size={"massive":86,"editorial":69,"compact":59}[brief["headline_style"]]
    # A non-text decorative rail introduces rhythm without smearing original tool.
    treatment=brief["text_treatment"]
    if treatment=="rail" or (treatment=="minimal" and brief["headline_style"]=="massive"):
        d.rectangle((headline[0]-11,headline[1],
                     headline[0]-3,min(headline[3],headline[1]+125)),fill=accent)
    elif treatment=="underline":
        d.rectangle((headline[0],headline[3]-5,
                     min(headline[2],headline[0]+round((headline[2]-headline[0])*.64)),
                     headline[3]-1),fill=accent)
    elif treatment in ("panel","banner"):
        d.rounded_rectangle(
            (headline[0]-12,headline[1]-8,headline[2]+12,headline[3]+9),
            radius=10 if treatment=="banner" else 23,
            fill=(3,23,43,238 if treatment=="banner" else 184),
            outline=accent,width=3)
    # Text-repair levels genuinely change typography AND its painted zone;
    # the prior image/lighting-only retry had no effect on clipped copy.
    inset=(0,11,20)[text_safety]
    safe_head=(headline[0]+inset,headline[1]+inset,
               headline[2]-inset,headline[3]-inset)
    _text(d,concept.get("headline") or product.get("title"),
          safe_head,base=max(43,size-(0,14,26)[text_safety]),
          minsize=23,maxlines=5,role="headline")

    proof=_box(zones["proof"])
    detail=concept.get("selling_point") or ""
    if detail:
        d.rectangle((proof[0],proof[1],min(proof[2],proof[0]+98),proof[1]+5),fill=accent)
        line=(proof[0]+inset,proof[1]+16+inset,
              proof[2]-inset,proof[3]-inset)
        _text(d,detail,line,base=32-(0,5,9)[text_safety],
              minsize=18,bold=False,maxlines=7,role="proof")
    else:
        line=(proof[0]+inset,proof[1]+inset,
              proof[2]-inset,proof[3]-inset)
        _text(d,"Check official specifications before ordering.",
              line,base=28-(0,3,6)[text_safety],
              minsize=18,bold=False,maxlines=4,role="proof")

    if concept.get("campaign_role")=="price_promo":
        rect=_box(zones["price"])
        d.rounded_rectangle(rect,radius=18,fill=(8,45,75,245),outline=accent,width=4)
        record_area("price",rect)
        x0,y0,x1,y1=rect
        p=verified_price(product)
        if p["amount"]:
            line=p["amount"]
            vat=p.get("vat") or "VAT STATUS TO CONFIRM"
            caption=(p.get("label") or "UK RRP")+" · "+vat
        else:
            line="PRICE ON REQUEST"
            caption="Contact us for product information"
        _text(d,line,(x0+15,y0+13,x1-15,y0+round((y1-y0)*.65)),
              base=47,minsize=21,maxlines=2,role="price")
        _text(d,caption,(x0+15,y0+round((y1-y0)*.65),x1-15,y1-7),
              base=22,minsize=14,maxlines=2,bold=False,role="price_caption",
              colour="#D8EDF7")
    # Fixed source-confirmation footer (never arbitrarily created by the model).
    d=ImageDraw.Draw(image,"RGBA")
    _text(d,"LASER TOOLS  |  OFFICIAL PRODUCT PHOTOGRAPH",
          (70,1410,1125,1448),base=23,minsize=18,maxlines=1,
          role="footer",colour="#E9F5FA")
    _text(d,"DRAFT FOR COMPANY REVIEW · VERIFY PRICE & APPLICATIONS",
          (70,1450,1125,1482),base=17,minsize=15,maxlines=1,
          role="footer",colour="#B7D7E8")
    out=io.BytesIO()
    image.convert("RGB").save(out,"PNG",optimize=False,compress_level=3)
    return out.getvalue()
