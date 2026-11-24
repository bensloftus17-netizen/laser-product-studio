"""AI-directed, free-positioned design briefs for three Laser Tools posters.

The model owns the layout coordinates, mood, typographic approach and visual
hierarchy. The server owns every factual string, logo, price, product pixel and
permission boundary. No arbitrary CSS, HTML, image URLs, or AI-drawn tools.
Coordinates are per-mille of a 1200x1500 artboard, not template IDs.
"""
from __future__ import annotations

from itertools import combinations
from creative_families import FAMILIES as CREATIVE_FAMILIES, DEFAULT_FAMILY, FAMILY_MODES, FAMILY_MOOD
from creative_expression import normalise_expression
from promo_art_direction import PRICE_STYLES

ROLES=("technical_application","price_promo","product_selected")
ZONES=("headline","product","proof","price")
ACCENTS=("#13B5EC","#40C1E8","#FFC83A","#F9A842","#D9E75B","#FFFFFF",
         "#71D6EE","#F1E9D8")
BACKGROUNDS=("workshop-photo","studio-gradient","industrial")
MOODS=("bold","understated","editorial","technical","energetic")
MOTIFS=("none","speed-lines","circles","industrial-grid","diagonal-bars")
HEADLINE_STYLES=("massive","editorial","compact")
FOCUSES=("left","centre","right")
SHAPE_KINDS=("panel","outline","circle","ribbon","line")
SHAPE_INKS=("accent","cyan","white")
# Genuine model choices affect the actual rendered composition, not only copy.
COMPOSITION_MODES=("engineering-precision","commercial-impact","hero-spotlight",
                   "minimal-editorial","workshop-motion")


def _intersects(a,b):
    x,y,w,h=a
    u,v,p,q=b
    return max(0,min(x+w,u+p)-max(x,u))*max(0,min(y+h,v+q)-max(y,v))


def _valid_zone(value):
    if (not isinstance(value,(list,tuple)) or len(value)!=4
            or any(type(n) is not int for n in value)):
        return False
    x,y,w,h=value
    return x>=35 and y>=137 and w>0 and h>0 and x+w<=965 and y+h<=917


def validate_brief(raw,role):
    """Reject bad AI compositions before they can be sent to Pillow.

    No snapping to any legacy grid: *valid* arbitrarily positioned rectangular
    zones are preserved exactly. Rejection is safer than silently turning an
    AI concept into a pre-existing poster template.
    """
    if role not in ROLES or not isinstance(raw,dict):
        return None
    zones=raw.get("zones")
    if not isinstance(zones,dict):
        return None
    required=("headline","product","proof")+(
        ("price",) if role=="price_promo" else ())
    if any(not _valid_zone(zones.get(key)) for key in required):
        return None
    clean={key:list(zones[key]) for key in required}
    headline=clean["headline"]
    photo=clean["product"]
    proof=clean["proof"]
    if (headline[2]<300 or headline[3]<85 or photo[2]<270
            or photo[3]<250 or proof[2]<230 or proof[3]<65):
        return None
    if role=="price_promo" and (
            clean["price"][2]<220 or clean["price"][3]<80):
        return None
    text_zones=[key for key in required if key!="product"]
    for a,b in combinations(text_zones,2):
        if _intersects(clean[a],clean[b]):
            return None
    # Text must not lie underneath the genuine product photo. A designer can
    # overlap decorative panels, but not cover the actual source tool or copy.
    for key in text_zones:
        if _intersects(clean[key],photo):
            return None
    def choice(key,values,default):
        value=raw.get(key)
        return value if isinstance(value,str) and value in values else default
    # Decorative vector objects can be placed freely behind all text and
    # tool pixels. No arbitrary model scripts, URLs or new product silhouettes.
    shapes=[]
    raw_shapes=raw.get("shapes",[])
    if isinstance(raw_shapes,list):
        for item in raw_shapes[:8]:
            if not isinstance(item,dict):continue
            kind=item.get("kind")
            rect=item.get("box")
            ink=item.get("ink")
            opacity=item.get("opacity",45)
            if (kind not in SHAPE_KINDS or ink not in SHAPE_INKS or
                not isinstance(rect,(list,tuple)) or len(rect)!=4 or
                any(type(n) is not int for n in rect) or
                type(opacity) is not int):continue
            x,y,w,h=rect
            if (x<0 or y<0 or w<=0 or h<=0 or
                x+w>1000 or y+h>1000):continue
            shapes.append({"kind":kind,"box":list(rect),"ink":ink,
                           "opacity":max(10,min(85,opacity))})
    # Only safe enumerated style choices. Tool pixels, claims and price remain
    # locked to the official manufacturer record.
    mode_family={
        "engineering-precision":"engineering_grid",
        "commercial-impact":"commercial_burst",
        "hero-spotlight":"premium_spotlight",
        "minimal-editorial":"editorial_split",
        "workshop-motion":"workshop_motion",
    }
    explicit_family=raw.get("creative_family")
    if explicit_family in CREATIVE_FAMILIES:
        chosen_family=explicit_family
        chosen_mode=FAMILY_MODES[chosen_family]
    else:
        # V55 clients passed composition_mode but no creative_family. Keep
        # that genuine existing model choice working, rather than silently
        # resetting everything to engineering_grid.
        chosen_mode=choice("composition_mode",COMPOSITION_MODES,
                           FAMILY_MODES[DEFAULT_FAMILY[role]])
        chosen_family=mode_family[chosen_mode]
    return {
        "zones":clean,
        "shapes":shapes,
        "background":choice("background",BACKGROUNDS,"workshop-photo"),
        "mood":choice("mood",MOODS,"editorial"),
        "motif":choice("motif",MOTIFS,"none"),
        "headline_style":choice("headline_style",HEADLINE_STYLES,"massive"),
        "price_style":choice("price_style",PRICE_STYLES,"panel")
                       if role=="price_promo" else "panel",
        "photo_focus":choice("photo_focus",FOCUSES,"centre"),
        "accent":choice("accent",ACCENTS,"#13B5EC"),
        "creative_family":chosen_family,
        "background_mood":FAMILY_MOOD[chosen_family],
        "composition_mode":chosen_mode,
        **normalise_expression(raw,role=role),
        "source":"ai-freeform-canvas",
    }


def brief_signature(brief):
    """Coarse comparison for concept distinctness, not a restrictive grid."""
    zones=brief.get("zones",{})
    head=zones.get("headline",[0,0,0,0])
    photo=zones.get("product",[0,0,0,0])
    return (int(head[0]//130),int(head[1]//140),
            int(photo[0]//130),int(photo[1]//140),
            brief.get("background"),brief.get("headline_style"),
            brief.get("creative_family"))


def distinct_briefs(briefs):
    """A model returning the same composition three times must try again."""
    if len(briefs)!=3 or any(not isinstance(b,dict) for b in briefs):
        return False
    signatures=[brief_signature(b) for b in briefs]
    if len(set(signatures))!=3:
        return False
    positions=[tuple(b["zones"]["product"][:2]) for b in briefs]
    family_count=len(set(b.get("creative_family") for b in briefs))
    # Model-controlled layouts and brand-safe family decisions must differ.
    return len(set(positions))>=2 and family_count==3


def creative_instruction():
    """Prompt appendix for the existing single Gemini call.

    Geometry is creative and free-positioned; code rejects unsafe overlaps.
    The legacy art_direction remains supported for the manual poster editor.
    """
    return (
        "IMPORTANT: You are the creative director, not a template selector. "
        "For EACH of the 3 concepts, also return a creative_canvas object. "
        "Design the composition yourself, uniquely for this actual product. "
        "Use normalized integer coordinates from 0 to 1000. "
        "creative_canvas.zones is an object with headline, product, proof "
        "and (for the retail/price concept) price, each an [x,y,width,height] "
        "array of integers. The visual artboard has a fixed branding strip "
        "at y=0..130 and a review footer at y=920..1000. "
        "Place every zone inside x=35..965 and y=137..917. "
        "Leave substantial room for headlines and a clearly visible genuine "
        "product cutout: headline width >=300 height >=85, product width >=270 "
        "height >=250, proof width >=230 height >=65, and price (where needed) "
        "width >=220 height >=80. Text zones may not overlap each other or "
        "the product zone. Place nothing below footer or under the brand. "
        "Choose your own arbitrary positions and dimensions, NOT template IDs. "
        "Respond with creative_canvas.background one of workshop-photo, "
        "studio-gradient, industrial; mood one of bold, understated, editorial, "
        "technical, energetic; motif one of none, speed-lines, circles, "
        "industrial-grid, diagonal-bars; headline_style one of massive, "
        "editorial, compact; photo_focus one of left, centre, right; "
        "accent one of #13B5EC #40C1E8 #FFC83A #F9A842 #D9E75B "
        "#FFFFFF #71D6EE #F1E9D8. "
        "Optionally create up to eight custom vector background shapes, "
        "each as creative_canvas.shapes array item with kind one of panel, "
        "outline, circle, ribbon, line; box [x,y,width,height] using integer "
        "0..1000 coordinates inside the artboard; ink one of accent, cyan, "
        "white; opacity integer 10..85. Their geometry is entirely YOUR "
        "design decision. These are abstract background objects only, never "
        "tools, extra products, words or brand logos. "
        "Let the product's REAL shape, function and intended audience guide "
        "the design. All three canvases must have visibly different "
        "composition, product position, headline hierarchy and mood. "
        "Do NOT supply product pixels, imagined photos, new technical claims "
        "or any text for the poster: the server inserts verified source text. "
        "For EACH poster include creative_family as one of engineering_grid, "
        "commercial_burst, premium_spotlight, workshop_motion, editorial_split, "
        "toolkit_coverage. Choose THREE DIFFERENT families. The chosen family "
        "must suit the manufacturer's product type and this poster's selling "
        "angle. Avoid 3 navy backgrounds: prefer different colour hierarchy, "
        "real workshop photography where available, price banners, hero scale "
        "and negative space. The renderer gives each family a visibly different "
        "background structure; the exact tool photo is always unchanged. "
        "Choose creative_palette (laser_blue, signal_yellow, cold_cyan, "
        "studio_silver, graphite_orange, electric_violet, workshop_teal). "
        "Let your choice transform LARGE AREAS of the poster rather than "
        "always ending up navy. Choose three visually different palettes, "
        "including bold trade-quality tones, a lighter cool editorial "
        "composition, and high-impact promotional contrast where relevant. "
        "Choose visual_treatment from photo_editorial, bold_geometry, "
        "clean_minimal, cinematic, split_canvas, technical_infographic; "
        "text_treatment from rail, panel, banner, underline, minimal; "
        "hero_treatment from spotlight, clean_cutout, graphic_frame, floating. "
        "The application applies your actual choices under the REAL, untouched "
        "manufacturer photo and verified copy, with safe contrast panels. "
        "Invent no photographic tools, logos, specs or unsupported slogans. "
        "Also include background_mood as structured_workshop, bold_promotion, "
        "premium_studio, workshop_action, editorial, or organised_kit. "
        "Choose a DIFFERENT composition_mode for each poster: one of "
        "engineering-precision, commercial-impact, hero-spotlight, "
        "minimal-editorial, workshop-motion. This controls genuine background "
        "shape language, depth, rhythm and typographic surroundings, not just "
        "colour. Match the style to this particular tool type and the selling "
        "story. Use three visually separate arrangements rather than three "
        "similar navy gradients. Product image and copy positions remain your "
        "unique model-authored coordinates with no text or tool redraws. "
        "Avoid cheap white rectangles, clashing text, and tiny product heroes."
    )
