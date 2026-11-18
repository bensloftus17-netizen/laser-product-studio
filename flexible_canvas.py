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
        if len(rows)<=maxlines and step*len(rows)<=height:
            for j,line in enumerate(rows):
                draw.text((x0,y0+j*step),line,font=font(size,"bold" if bold else "regular"),
                          fill=colour)
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


def render_creative_canvas(product,official_photo,concept,scene=None,
                           distributor=None,variant=0):
    brief=validate_brief(concept.get("creative_canvas"),concept.get("campaign_role"))
    if not brief:
        raise ValueError("Invalid AI creative layout")
    if variant not in (0,1,2):
        raise ValueError("Unknown candidate variation")
    image=_background(scene,brief,variant)
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
    _text(d,concept.get("headline") or product.get("title"),
          headline,base=size,minsize=25,maxlines=5,role="headline")

    proof=_box(zones["proof"])
    detail=concept.get("selling_point") or ""
    if detail:
        d.rectangle((proof[0],proof[1],min(proof[2],proof[0]+98),proof[1]+5),fill=accent)
        line=(proof[0],proof[1]+16,proof[2],proof[3])
        _text(d,detail,line,base=32,minsize=18,bold=False,maxlines=7,role="proof")
    else:
        _text(d,"Check official specifications before ordering.",
              proof,base=28,minsize=18,bold=False,maxlines=4,role="proof")

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
          (60,1420,1135,1457),base=23,minsize=18,maxlines=1,
          role="footer",colour="#E9F5FA")
    _text(d,"DRAFT FOR COMPANY REVIEW · VERIFY PRICE & APPLICATIONS",
          (60,1461,1135,1492),base=17,minsize=15,maxlines=1,
          role="footer",colour="#B7D7E8")
    out=io.BytesIO()
    image.convert("RGB").save(out,"PNG",optimize=True)
    return out.getvalue()
