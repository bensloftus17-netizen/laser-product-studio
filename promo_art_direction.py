"""Validated AI art direction for photography-led trade marketing.

The generative model selects a composition and bounded visual parameters.
Rendering remains deterministic Pillow using only real manufacturer photos,
verified price information and approved stock photography. No arbitrary model
image/URL/brand names are accepted.
"""
from __future__ import annotations

import re

LAYOUTS=(0,1,2)
PRICE_STYLES=("bubble","plaque","banner","tag","sticker","corner","panel")
MOTIFS=("none","speed-lines","circles","industrial-grid","diagonal-bars")
FOCUSES=("left","centre","right")
MOODS=("bright","balanced","dramatic")
ACCENTS=("#F6D343","#F9A842","#13B5EC","#D9E75B","#40C1E8",
         "#F1E9D8","#E8F4F4","#FFCB5B","#FFFFFF")
HEADLINE_SIZES=("small","normal","large")
PRICE_POSITIONS=("standard","opposite")


def _safe_choice(value,allowed,default):
    return value if isinstance(value,str) and value in allowed else default


def _safe_integer(value,lower,upper,default):
    if type(value) is not int:return default
    return max(lower,min(upper,value))


def normalise_art_direction(raw,family="retail",fallback_variant=0):
    """Untrusted Gemini fields are a creative *suggestion*, not rendering code."""
    if not isinstance(raw,dict):raw={}
    defaults={
        "retail":{"price_style":"bubble","accent":"#F6D343",
                  "motif":"speed-lines","mood":"bright"},
        "premium":{"price_style":"plaque","accent":"#13B5EC",
                   "motif":"none","mood":"balanced"},
        "trade":{"price_style":"banner","accent":"#F9A842",
                 "motif":"industrial-grid","mood":"dramatic"},
    }.get(family,{"price_style":"banner","accent":"#F9A842",
                    "motif":"none","mood":"balanced"})
    return {
        "layout_variant":_safe_integer(raw.get("layout_variant"),0,2,
                                       fallback_variant%3),
        "price_style":_safe_choice(raw.get("price_style"),
                                    PRICE_STYLES,defaults["price_style"]),
        "price_position":_safe_choice(raw.get("price_position"),
                                       PRICE_POSITIONS,"standard"),
        "accent":_safe_choice(raw.get("accent"),ACCENTS,defaults["accent"]),
        "product_scale":_safe_integer(raw.get("product_scale"),85,125,104),
        "product_x":_safe_integer(raw.get("product_x"),-30,30,0),
        "product_y":_safe_integer(raw.get("product_y"),-30,30,0),
        "headline_size":_safe_choice(raw.get("headline_size"),
                                     HEADLINE_SIZES,"normal"),
        "graphic_motif":_safe_choice(raw.get("graphic_motif"),
                                      MOTIFS,defaults["motif"]),
        "photo_focus":_safe_choice(raw.get("photo_focus"),FOCUSES,"centre"),
        "background_mood":_safe_choice(raw.get("background_mood"),
                                        MOODS,defaults["mood"]),
    }


def editor_preferences(art):
    """Editable controls; model may not change manufacturer assets or VAT."""
    return {k:art[k] for k in ("price_style","price_position","accent",
            "product_scale","product_x","product_y","headline_size") if k in art}


def scene_treatment(source,art):
    """Mildly change the crop/mood of *real* licensed background photography."""
    scene=dict(source or {})
    crop=scene.get("crop",(.5,.5))
    if not isinstance(crop,(list,tuple)) or len(crop)!=2:crop=(.5,.5)
    shift={"left":-.12,"centre":0,"right":.12}.get(
          art.get("photo_focus"),0)
    try:x,y=(float(crop[0]),float(crop[1]))
    except (ValueError,TypeError):x,y=.5,.5
    scene["crop"]=(max(.13,min(.87,x+shift)),max(.15,min(.85,y)))
    defaults={"bright":(-.08,.09),"balanced":(0,0),"dramatic":(.09,-.09)}
    dh,dc=defaults.get(art.get("background_mood"),(0,0))
    scene["darkness"]=max(.08,min(.65,float(scene.get("darkness",.27))+dh))
    scene["colour"]=max(.5,min(1.05,float(scene.get("colour",.75))+dc))
    scene["graphic_motif"]=art.get("graphic_motif","none")
    return scene


def draw_background_motif(photo,style):
    """Decorative motifs on the background only, NEVER on the product/copy."""
    from PIL import Image,ImageDraw
    motif=str((style or {}).get("graphic_motif") or "none")
    result=photo.convert("RGBA")
    # Consistent RGBA even when the model requests "none"; Pillow's
    # alpha_composite requires identical modes and previously crashed when
    # a legacy concept provided no motif.
    if motif not in MOTIFS or motif=="none":return result
    w,h=result.size
    overlay=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(overlay,"RGBA")
    stroke=(54,190,239,52)
    if motif=="speed-lines":
        for j in range(8):
            xx=int(w*(.48+j*.085))
            d.line((xx,-h*.08,xx-h*.28,h*1.15),fill=stroke,
                   width=max(2,int(w*.008)))
    elif motif=="circles":
        cx,cy=int(w*.75),int(h*.53)
        for fraction in (.18,.34,.52,.72):
            r=int(min(w,h)*fraction)
            d.ellipse((cx-r,cy-r,cx+r,cy+r),
                      outline=stroke,width=max(2,int(w*.005)))
    elif motif=="industrial-grid":
        for x in range(0,w,max(50,int(w*.12))):
            d.line((x,0,x,h),fill=(90,191,228,38),width=2)
        for y in range(0,h,max(50,int(h*.13))):
            d.line((0,y,w,y),fill=(90,191,228,38),width=2)
    elif motif=="diagonal-bars":
        for j in range(5):
            x=int(w*(.45+j*.13))
            d.polygon([(x,0),(x+max(10,int(w*.035)),0),
                       (x-int(w*.24),h),(x-int(w*.24)-max(10,int(w*.035)),h)],
                      fill=(10,162,226,35))
    return Image.alpha_composite(result,overlay)
