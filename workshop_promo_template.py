"""Reusable Laser Tools Workshop Showcase promotional poster, V64.

Based on the user-provided portrait reference: blue/black Laser header, real
workshop backdrop, generous genuine-product hero, metal workbench, feature
panels, conditional kit-contents area, strong verified-UK-price graphic and
Laser footer. This is NOT a flattened image: every panel has source-backed
dynamic content, and validated AI art direction controls colour accents,
hero emphasis, geometric treatment and photo focus. No AI-redrawn tools.
"""
from __future__ import annotations

import io
import re

from PIL import Image, ImageDraw, ImageFilter, ImageColor

from ai_promo_renderer import verified_price
from campaign_role_posters import (
    actual_scene, brand, co_brand, product_photo,
)
from flexible_canvas import _text
from poster_quality import record_area
from promo_selling_points import choose_feature
from creative_expression import PALETTES

W,H=1200,1500
CANVAS="#061728"
BRAND_BLUE=(0,157,225)
CYAN=(21,181,237)
WHITE="#FFFFFF"
BLUEGREY="#BEDBEA"
DESIGN_ID="workshop_showcase"
TEMPLATE_OPTIONS=("workshop_showcase","ai_original")


def validate_promo_template(value):
    if value is None:
        return DESIGN_ID
    if not isinstance(value,str) or value not in TEMPLATE_OPTIONS:
        raise ValueError("Unknown promotional poster template")
    return value


def _verified(product,concept):
    """Display only literal manufacturer claims already in the product record."""
    facts=[]
    official=[
        " ".join(str(item).split()).strip()
        for item in (product.get("features") or [])
        if isinstance(item,str) and str(item).strip()
    ]
    # Specs should be included only when the whole source row was verified.
    for label,val in (product.get("specs") or {}).items():
        if isinstance(label,str) and isinstance(val,(str,int,float)):
            label=" ".join(label.split())[:50]
            val=" ".join(str(val).split())[:65]
            if label and val:
                official.append(label+": "+val)
    for item in [concept.get("selling_point"),*(concept.get("features") or []),*official]:
        if not isinstance(item,str):
            continue
        value=" ".join(item.split()).strip()
        # Small source fact panels must contain WHOLE, readable claims, not
        # a truncated sentence or a microscopic multi-line paragraph.
        if value and value in official and value not in facts and len(value)<=90:
            facts.append(value)
    return facts[:9]


def _palette(concept):
    selected=(concept.get("creative_direction") or {}).get(
        "creative_palette","laser_blue")
    if selected not in PALETTES:
        selected="laser_blue"
    # Laser brand blue always dominates. Safe model accents are subordinate.
    chosen=PALETTES[selected][2]
    return selected,chosen


def _scene_base(scene,focus,variant):
    canvas=Image.new("RGBA",(W,H),CANVAS)
    used=actual_scene(
        canvas,scene,(0,170,W,1070),
        brightness=(.68,.56,.75)[variant],blur=(1.6,2.0,1.0)[variant],
        focus=focus
    ) if scene else False
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    draw=ImageDraw.Draw(layer,"RGBA")
    if not used:
        # Subtle architectural workshop cues, NOT a fabricated use-case or
        # vehicle. Authentic external workshop scene takes precedence.
        draw.rectangle((0,170,W,1070),fill=(9,40,63,255))
        for x in (65,420,880,1120):
            draw.rectangle((x,176,x+26,800),fill=(6,86,133,190))
            draw.rectangle((x+6,181,x+12,798),fill=(34,155,215,50))
        for x in (110,470,750):
            draw.rounded_rectangle((x,590,x+280,800),radius=15,
                                   fill=(10,61,103,207),
                                   outline=(27,115,165,142),width=5)
            for y in range(626,784,42):
                draw.line((x+22,y,x+258,y),fill=(146,188,210,140),width=5)
    else:
        draw.rectangle((0,170,W,1070),fill=(3,21,40,116))
    # Workshop lighting and perspective metal workbench are vector only.
    for index in range(5):
        x=140+index*185
        draw.line((x,198,x+170,198),fill=(64,169,227,65),width=4)
    canvas.alpha_composite(layer)
    return canvas


def _workbench(canvas,accent,variant,style):
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer,"RGBA")
    top=(820,856,838)[variant]
    # Resemble the metallic display surface in the supplied template.
    d.polygon(((0,top+120),(W,top-20),(W,1088),(0,1118)),
              fill=(116,147,167,224))
    for n in range(15):
        t=n/15
        y=top+round(115*t)
        alpha=int(70+56*(1-t))
        d.line((0,y,W,max(0,y-150)),fill=(189,215,229,alpha),width=2)
    d.polygon(((0,1075),(W,1048),(W,1124),(0,1150)),
              fill=(14,34,55,246))
    d.line((0,1075,W,1048),fill=(*accent,195),width=7)
    # AI-selected decoration modifies the same brand-safe architecture.
    if style=="bold_geometry":
        d.polygon(((0,760),(205,685),(220,755),(0,847)),
                  fill=(*accent,112))
    elif style=="technical_infographic":
        for x in range(50,1190,70):
            d.line((x,630,x,1060),fill=(*accent,42),width=2)
    elif style=="cinematic":
        d.ellipse((285,320,970,1030),outline=(*accent,95),width=16)
    elif style=="split_canvas":
        d.polygon(((0,455),(245,390),(260,820),(0,870)),
                  fill=(2,51,86,120))
    canvas.alpha_composite(layer)
    return canvas


def _panel(draw,box,title,accent):
    x0,y0,x1,y1=box
    draw.rounded_rectangle(box,radius=14,fill=(4,24,42,249),
                           outline=(*accent,255),width=4)
    draw.rectangle((x0+12,y0+13,x0+20,y1-14),fill=(*accent,255))
    # Header is static design text, not a claim.
    _text(draw,title,(x0+33,y0+17,x1-14,y0+57),
          base=29,minsize=16,maxlines=1,role="label")


def _draw_brand_footer(canvas,product,accent):
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,1380,W,H),fill=(2,15,31,250))
    d.line((0,1380,W,1380),fill=(*accent,255),width=6)
    d.polygon(((420,1400),(W,1400),(W,1500),(345,1500)),
              fill=(0,91,154,234))
    d.polygon(((487,1395),(W,1395),(W,1445),(452,1445)),
              fill=(*accent,120))
    _text(d,"LASER TOOLS",(65,1401,390,1457),
          base=43,minsize=27,maxlines=1,role="brand_footer")
    _text(d,"DRAFT · VERIFY DETAILS BEFORE PUBLICATION",
          (478,1465,1133,1494),base=19,minsize=15,maxlines=1,
          role="footer",colour="#DCEEF7")


def render_workshop_showcase(product,official_photo,concept,scene=None,
                             distributor=None,variant=0):
    """Generate the reference-inspired price poster from genuine product data.

    Three variants are evaluated by the existing independent art QA. Model
    choices affect palette, workshop lighting, hierarchy and styling, not
    text provenance, exact price, manufacturer pixels or branding.
    """
    if variant not in (0,1,2):
        raise ValueError("Unknown workshop showcase variant")
    if concept.get("campaign_role")!="price_promo":
        raise ValueError("Workshop showcase is a price-led poster only")
    if not official_photo:
        raise ValueError("Manufacturer photograph required")
    palette,accent=_palette(concept)
    direction=concept.get("creative_direction") or {}
    style=direction.get("visual_treatment","photo_editorial")
    focus={"workshop_motion":"right","editorial_split":"left"}.get(
        direction.get("creative_family"),"centre")
    canvas=_scene_base(scene,focus,variant)
    canvas=_workbench(canvas,accent,variant,style)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,W,192),fill=(2,17,34,252))
    d.rectangle((0,187,W,194),fill=(*accent,255))
    d.polygon(((900,0),(W-120,0),(W-264,192),(840,192)),
              fill=(5,75,132,190))
    brand(d,str(product.get("part") or ""))
    co_brand(canvas,distributor)
    d=ImageDraw.Draw(canvas,"RGBA")

    title=str(product.get("title") or "").strip()
    if not title:
        raise ValueError("Manufacturer product title is required")
    d.polygon(((46,215),(1123,215),(1081,358),(46,358)),
              fill=(2,21,37,231))
    d.line((46,356,1090,356),fill=(*accent,235),width=5)
    _text(d,title.upper(),(66,224,1092,312),
          base=(65,60,70)[variant],minsize=28,maxlines=2,role="headline")
    # The price/marketing role is clear even when no RRP is available.
    _text(d,"WORKSHOP PRODUCT PROMOTION",(70,317,963,351),
          base=24,minsize=18,maxlines=1,role="subline",
          colour=BLUEGREY)

    # Main product/photo hero dominates the workbench, not a small thumbnail.
    emphasis=direction.get("hero_emphasis","balanced")
    hero={
        "dominant":(109,401,1102,1028),
        "balanced":(137,414,1086,1028),
        "supporting":(185,415,1059,1009),
    }.get(emphasis,(137,414,1086,1028))
    # Genuine manufacturer pixels remain completely untouched.
    product_photo(canvas,official_photo,hero,
                  scale=(1.0,.96,1.045)[variant])

    facts=_verified(product,concept)
    primary=facts[0] if facts else None
    secondary=next((item for item in facts[1:]
                    if item!=primary),None)
    # Only source-backed kit contents get the 'KIT CONTENTS' label.
    kit_fact=next((item for item in facts if re.search(
        r"\b(?:includes|contains|comprises|supplied with|consists of|kit contents)\b",
        item,re.I)),None)
    other=next((item for item in facts
                if item not in (primary,secondary,kit_fact)),None)
    right_head="KIT CONTENTS" if kit_fact else "PRODUCT DETAILS"
    right_fact=kit_fact or other or secondary or primary

    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,1110,W,1382),fill=(2,22,42,250))
    d.line((0,1110,W,1110),fill=(*accent,255),width=6)
    _panel(d,(32,1130,390,1245),"KEY FEATURES",accent)
    _panel(d,(407,1130,763,1245),"WORKSHOP USE" if secondary else
           "TOOL DETAILS",accent)
    _panel(d,(780,1130,1168,1245),right_head,accent)
    # Each claim is painted in a measured, bounded text region.
    _text(d,primary or "View official product specifications.",
          (65,1178,373,1239),base=22,minsize=14,bold=False,
          maxlines=3,role="proof")
    _text(d,secondary or "Confirm suitability before ordering.",
          (440,1178,747,1239),base=22,minsize=14,bold=False,
          maxlines=3,role="detail")
    _text(d,right_fact or "See the manufacturer product listing.",
          (811,1178,1154,1239),base=22,minsize=14,bold=False,
          maxlines=3,role="kit_details")

    price=verified_price(product)
    d.polygon(((42,1260),(700,1260),(666,1368),(18,1368)),
              fill=(4,34,61,255))
    d.line((42,1260,699,1260),fill=(*accent,255),width=5)
    d.line((18,1368,668,1368),fill=(*accent,255),width=5)
    record_area("price",(44,1265,687,1367))
    amount=price.get("amount") or "PRICE ON REQUEST"
    label=price.get("label") or "PRICE ON REQUEST"
    if price.get("amount"):
        caption=label+"  ·  "+(price.get("vat") or "VAT STATUS TO CONFIRM")
    else:
        caption="ENQUIRE FOR CURRENT UK PRICE"
    _text(d,amount,(68,1277,652,1337),
          base=55 if price.get("amount") else 43,
          minsize=22,maxlines=1,role="price")
    _text(d,caption,(68,1334,653,1365),base=19,minsize=15,
          bold=False,maxlines=1,role="price_caption",colour="#C5E6F6")
    d.polygon(((745,1261),(1143,1261),(1174,1368),(725,1368)),
              fill=(0,89,153,190))
    _text(d,"LASER TOOLS",(768,1292,1144,1346),
          base=45,minsize=25,maxlines=1,role="brand")
    _draw_brand_footer(canvas,product,accent)

    output=io.BytesIO()
    canvas.convert("RGB").save(output,"PNG",compress_level=3)
    return output.getvalue()
