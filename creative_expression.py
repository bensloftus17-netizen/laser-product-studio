"""V60 — Model-directed colour, composition and typography treatment.

Brand-safe expression is intentionally broader than preselected templates.
Gemini can choose a palette, graphic architecture, and text treatment for
each item; factual text, genuine manufacturer photo and LASER logo remain
server-owned and unchanged. No model-supplied CSS, URLs or product pixels.
"""
from __future__ import annotations

from PIL import Image,ImageDraw

PALETTES={
    "laser_blue":       ((6,35,62),(7,91,154),(17,180,227)),
    "signal_yellow":    ((30,35,44),(220,151,21),(255,204,45)),
    "cold_cyan":        ((7,73,98),(12,151,185),(43,221,225)),
    "studio_silver":    ((47,70,86),(174,206,218),(210,231,236)),
    "graphite_orange":  ((32,36,43),(129,55,38),(243,132,44)),
    "electric_violet": ((30,29,72),(90,55,149),(161,120,230)),
    "workshop_teal":   ((7,57,58),(13,112,100),(62,209,174)),
}
PALETTE_NAMES=tuple(PALETTES)
TREATMENTS=(
    "photo_editorial","bold_geometry","clean_minimal",
    "cinematic","split_canvas","technical_infographic",
)
TEXT_TREATMENTS=("rail","panel","banner","underline","minimal")
HERO_TREATMENTS=("spotlight","clean_cutout","graphic_frame","floating")
DEFAULT_POSTER_PALETTE={
    "technical_application":"studio_silver",
    "price_promo":"signal_yellow",
    "product_selected":"electric_violet",
}
DEFAULT_FORMAT_PALETTE={
    "social_square":"signal_yellow",
    "social_story":"cold_cyan",
    "website_banner":"studio_silver",
    "email_header":"workshop_teal",
    "linkedin_graphic":"laser_blue",
    "landscape_ad":"graphite_orange",
}


def _select(value,options,default):
    return value if isinstance(value,str) and value in options else default


def normalise_expression(raw,*,role=None,kind=None):
    """Model chooses from safe primitives. Defaults favour visibly different art."""
    raw=raw if isinstance(raw,dict) else {}
    palette=DEFAULT_FORMAT_PALETTE.get(
        kind,DEFAULT_POSTER_PALETTE.get(role,"laser_blue"))
    return {
        "creative_palette":_select(raw.get("creative_palette"),PALETTE_NAMES,palette),
        "visual_treatment":_select(raw.get("visual_treatment"),TREATMENTS,
            "photo_editorial" if role=="technical_application" else
            "bold_geometry" if role=="price_promo" else
            "split_canvas" if role=="product_selected" else "clean_minimal"),
        "text_treatment":_select(raw.get("text_treatment"),TEXT_TREATMENTS,
            "panel" if role=="price_promo" else "underline"),
        "hero_treatment":_select(raw.get("hero_treatment"),HERO_TREATMENTS,
            "spotlight" if role=="product_selected" else "clean_cutout"),
    }


def format_palette(kind,candidate,seen=()):
    """Honour model colour choices unless repetition would create six clones."""
    candidate=_select(candidate,PALETTE_NAMES,DEFAULT_FORMAT_PALETTE[kind])
    if list(seen).count(candidate)>=2:
        # Different on-format compositions are more important than falsely
        # advertising an AI choice that produces six lookalike banners.
        candidate=next((name for name in (
            DEFAULT_FORMAT_PALETTE[kind],*PALETTE_NAMES)
                        if name not in seen),candidate)
    return candidate


def express_background(image,palette,treatment,*,zones=None,variant=0,
                       hero_treatment="clean_cutout"):
    """Paint broad, high-contrast visual architecture BEHIND exact tool/copy.

    The optional real workshop photograph remains visible where possible.
    The brand strip/footer are drawn after this, over the untouched final
    product source pixels. Text safety backplates are applied to the model's
    actual safe zones; white verified wording therefore remains legible on
    light, cyan or amber sections.
    """
    palette=_select(palette,PALETTE_NAMES,"laser_blue")
    treatment=_select(treatment,TREATMENTS,"photo_editorial")
    hero_treatment=_select(hero_treatment,HERO_TREATMENTS,"clean_cutout")
    colours=PALETTES[palette]
    w,h=image.size
    x0,y0,x1,y1=0,round(h*.13),w,round(h*.93)
    # Preserve real workshop photo under translucent colour wash; no tool
    # pixels are present here yet. A broad colour change is intentional.
    overlay=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(overlay,"RGBA")
    base,mid,highlight=colours
    d.rectangle((x0,y0,x1,y1),fill=(*base,159 if palette=="laser_blue" else 192))
    if treatment=="photo_editorial":
        d.polygon(((0,y0),(int(w*.37),y0),(int(w*.56),y1),(0,y1)),
                  fill=(*mid,210))
        d.rectangle((0,int(h*.84),w,int(h*.90)),fill=(*highlight,159))
    elif treatment=="bold_geometry":
        d.polygon(((0,int(h*.24)),(w,y0),(w,int(h*.63)),
                   (0,int(h*.79))),fill=(*mid,233))
        d.polygon(((0,int(h*.69)),(w,int(h*.47)),(w,y1),
                   (0,y1)),fill=(*highlight,178))
        for k in range(3):
            yy=int(h*(.79-k*.055))
            d.line((0,yy,w,yy-int(h*.17)),fill=(*highlight,222),
                   width=max(4,w//200))
    elif treatment=="clean_minimal":
        d.rectangle((int(w*.56),y0,w,y1),fill=(*mid,222))
        d.rectangle((int(w*.54),y0,int(w*.565),y1),fill=(*highlight,226))
        d.line((int(w*.09),int(h*.77),int(w*.48),int(h*.77)),
               fill=(*highlight,224),width=max(4,w//230))
    elif treatment=="cinematic":
        d.ellipse((int(-w*.16),int(h*.19),int(w*.78),int(h*.96)),
                  fill=(*mid,170))
        d.ellipse((int(w*.3),int(h*.08),int(w*1.4),int(h*.92)),
                  fill=(*highlight,65))
        d.rectangle((0,int(h*.86),w,y1),fill=(*base,215))
    elif treatment=="split_canvas":
        d.polygon(((0,y0),(int(w*.6),y0),
                   (int(w*.38),y1),(0,y1)),fill=(*mid,225))
        d.polygon(((int(w*.61),y0),(w,y0),(w,y1),
                   (int(w*.39),y1)),fill=(*highlight,163))
        d.line((int(w*.6),y0,int(w*.39),y1),
               fill=(*base,227),width=max(7,w//140))
    elif treatment=="technical_infographic":
        d.rectangle((0,y0,w,y1),fill=(*mid,128))
        step=max(48,w//13)
        for x in range(0,w,step):
            d.line((x,y0,x,y1),fill=(*highlight,96),width=2)
        for y in range(y0,y1,step):
            d.line((0,y,w,y),fill=(*highlight,82),width=2)
        d.rectangle((int(w*.055),int(h*.27),int(w*.07),int(h*.85)),
                    fill=(*highlight,219))
    if hero_treatment=="spotlight":
        d.ellipse((int(w*.42),int(h*.22),int(w*.97),int(h*.79)),
                  outline=(*highlight,190),width=max(6,w//110))
    elif hero_treatment=="graphic_frame":
        d.rounded_rectangle((int(w*.35),int(h*.23),int(w*.94),int(h*.81)),
                            radius=max(12,w//70),outline=(*highlight,173),
                            width=max(5,w//160))
    elif hero_treatment=="floating":
        d.ellipse((int(w*.48),int(h*.69),int(w*.90),int(h*.76)),
                  fill=(*base,144),outline=(*highlight,155),
                  width=max(3,w//280))
    # High contrast is mandatory even when the model chooses a pale palette.
    # Zones are pixel boxes, not AI-supplied text, and do not overlap products.
    if isinstance(zones,dict):
        for key in ("headline","proof","price"):
            region=zones.get(key)
            if region and len(region)==4:
                ax,ay,bx,by=(int(v) for v in region)
                if bx<=ax or by<=ay:continue
                pad=max(5,w//175)
                d.rounded_rectangle((
                    max(0,ax-pad),max(y0,ay-pad),min(w,bx+pad),
                    min(y1,by+pad)),
                    radius=max(8,w//130),
                    fill=(*base,222 if palette=="studio_silver" else 194),
                    outline=(*highlight,110),width=max(2,w//400))
    return Image.alpha_composite(image.convert("RGBA"),overlay)
