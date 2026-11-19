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
    """Amplify each different model composition without drawing any fake tools.

    Earlier canvases shared almost the same navy background even when the
    model supplied different freeform placements. These transparent bands,
    industrial rails and spotlight rings respond to the *AI's actual product
    zone and selected brand colour*. All shapes sit behind genuine copy and
    manufacturer artwork and may never replace the creative-canvas zones.
    """
    from PIL import ImageColor
    accent=ImageColor.getrgb(brief["accent"])
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer,"RGBA")
    product=_box(brief["zones"]["product"])
    cx=(product[0]+product[2])//2
    cy=(product[1]+product[3])//2
    mode=brief.get("composition_mode") or (
        "engineering-precision" if role=="technical_application" else
        "commercial-impact" if role=="price_promo" else "hero-spotlight")
    if mode=="engineering-precision":
        # Technical engineering precision: photo-context and measured rails.
        for y in range(245,1330,84):
            d.line((65,y,110,y),fill=(*accent,78),width=3)
        for x in range(80,1120,185):
            d.line((x,245,x,1305),fill=(*accent,19),width=2)
        d.line((62,245,62,1315),fill=(*accent,80),width=4)
        for offset in (56,104,152):
            d.arc((cx-270-offset//2,cy-270-offset//2,
                   cx+270+offset//2,cy+270+offset//2),
                  28,300,fill=(*accent,38),width=3)
    elif mode=="commercial-impact":
        # Commercial energy: sweeping geometry, rather than technical grid.
        d.polygon(((0,830),(W,335),(W,615),(0,1120)),
                  fill=(*accent,49))
        d.polygon(((0,1180),(W,775),(W,870),(0,1295)),
                  fill=(*accent,32))
        d.line(((0,1120),(W,620)),fill=(*accent,120),width=9)
        d.ellipse((cx-290,cy-290,cx+290,cy+290),
                  outline=(*accent,64),width=10)
    elif mode=="hero-spotlight":
        # Product / premium: a bold centrepiece with quieter circular depth.
        for radius,alpha,width in ((440,43,8),(356,47,5),(275,51,3)):
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),
                      outline=(*accent,alpha),width=width)
        d.polygon(((W-250,182),(W,182),(W,1160),(W-90,1120)),
                  fill=(*accent,35))
        d.line((75,1325,W-75,1325),fill=(*accent,99),width=5)
    elif mode=="minimal-editorial":
        # Quieter, premium negative space: fine offset lines, not the grid.
        d.polygon(((0,185),(W//5,185),(W//3,1390),(0,1390)),
                  fill=(*accent,25))
        d.line((W-90,220,W-90,1310),fill=(*accent,85),width=5)
        d.line((W-130,250,W-130,1290),fill=(*accent,35),width=3)
    elif mode=="workshop-motion":
        # A brand-safe energetic workshop treatment without fictional parts.
        for shift,alpha in ((-230,50),(-30,60),(170,41)):
            d.polygon(((shift,400),(shift+290,400),
                       (shift+1050,1180),(shift+760,1180)),
                      fill=(*accent,alpha))
        d.arc((cx-330,cy-330,cx+330,cy+330),
              0,290,fill=(*accent,90),width=6)
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
    product_photo(image,official_photo,hero,scale=(.94,1.0,.98)[variant])

    d=ImageDraw.Draw(image,"RGBA")
    headline=_box(zones["headline"])
    # Art-direction determines the typographic hierarchy, not a fixed family.
    size={"massive":86,"editorial":69,"compact":59}[brief["headline_style"]]
    # A non-text decorative rail introduces rhythm without smearing original tool.
    if brief["headline_style"]=="massive":
        d.rectangle((headline[0]-9,headline[1],
                     headline[0]-3,min(headline[3],headline[1]+95)),fill=accent)
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
