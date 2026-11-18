"""Original AI-designed square, Story and banner artwork, never poster resizing.

The AI controls format-specific coordinates, visual rhythm, optional verified
proof/price, scene choice and vector shapes. The server controls all copy,
real product pixels, logos, licensing, margins and objective quality gates.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from itertools import combinations

from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter, ImageStat, ImageColor

from asset_quality import require_good_asset
from campaign_art_quality import inspected_product
from creative_director import ACCENTS, BACKGROUNDS, MOODS, MOTIFS, HEADLINE_STYLES, SHAPE_KINDS, SHAPE_INKS
from flexible_canvas import _text
from poster import font
from poster_quality import record_text, record_product, capture
from brand_assets import get_brand_image
from ai_promo_renderer import verified_price

# x/y/width/height in integer 0..1000 coordinates. These are not templates:
# the model controls all placements within each destination's safe area.
FORMATS = {
    "social_square": (1080, 1080, 150, 905),
    "social_story": (1080, 1920, 160, 860),
    "website_banner": (1600, 600, 230, 880),
    "email_header": (1200, 420, 245, 845),
    "linkedin_graphic": (1200, 627, 225, 865),
    "landscape_ad": (1600, 900, 205, 895),
}
FORMAT_ORDER = tuple(FORMATS)
ROLE_IDS = ("technical_application", "price_promo", "product_selected")
TEXT_COL = "#FFFFFF"


def _rect(box, size):
    w,h=size
    x,y,a,b=box
    return (round(x*w/1000), round(y*h/1000),
            round((x+a)*w/1000), round((y+b)*h/1000))


def _overlap(a,b):
    return max(0,min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])) * max(
        0,min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]))


def validate_format_canvas(kind, raw, feature_count=0):
    """Keep valid freeform positions unchanged; reject unsafe model layouts."""
    if kind not in FORMATS or not isinstance(raw,dict):
        return None
    width,height,top,bottom=FORMATS[kind]
    supplied=raw.get("zones")
    if not isinstance(supplied,dict):
        return None
    compact=kind in ("website_banner","email_header","linkedin_graphic","landscape_ad")
    required=("headline","product") if compact else ("headline","product","proof")
    allowed=set(required)|{"proof","price"}
    zones={}
    for key,value in supplied.items():
        if key not in allowed or not isinstance(value,(list,tuple)) or len(value)!=4:
            return None
        if any(type(n) is not int for n in value):
            return None
        x,y,w,h=value
        if x<35 or x+w>965 or y<top or y+h>bottom or w<=0 or h<=0:
            return None
        zones[key]=list(value)
    if any(name not in zones for name in required):
        return None
    product=zones["product"]
    heading=zones["headline"]
    if product[2]<260 or product[3]<(310 if compact else 265):
        return None
    if heading[2]<(280 if compact else 320) or heading[3]<95:
        return None
    if "proof" in zones and (zones["proof"][2]<220 or zones["proof"][3]<70):
        return None
    if "price" in zones and (zones["price"][2]<215 or zones["price"][3]<105):
        return None
    if any(_overlap(zones[a],zones[b]) for a,b in combinations(zones,2)):
        return None
    # Customer logos and permanent review footers live outside all AI zones.
    def choice(k,options,default):
        v=raw.get(k)
        return v if isinstance(v,str) and v in options else default
    role=choice("headline_role",ROLE_IDS,"product_selected")
    scene=choice("scene_role",ROLE_IDS,role)
    index=raw.get("proof_feature_index")
    if type(index) is not int or not 0<=index<feature_count:
        index=None
    shapes=[]
    if isinstance(raw.get("shapes"),list):
        for item in raw["shapes"][:8]:
            if not isinstance(item,dict):continue
            k=item.get("kind")
            ink=item.get("ink")
            box=item.get("box")
            opacity=item.get("opacity",35)
            if (k not in SHAPE_KINDS or ink not in SHAPE_INKS or
                type(opacity) is not int or not isinstance(box,(list,tuple)) or
                len(box)!=4 or any(type(n) is not int for n in box)):
                continue
            x,y,w,h=box
            if x<0 or y<0 or w<=0 or h<=0 or x+w>1000 or y+h>1000:continue
            shapes.append({"kind":k,"ink":ink,"box":list(box),
                           "opacity":max(10,min(80,opacity))})
    return {
        "zones":zones,
        "background":choice("background",BACKGROUNDS,"workshop-photo"),
        "mood":choice("mood",MOODS,"editorial"),
        "motif":choice("motif",MOTIFS,"none"),
        "headline_style":choice("headline_style",HEADLINE_STYLES,"editorial"),
        "photo_focus":choice("photo_focus",("left","centre","right"),"centre"),
        "accent":choice("accent",ACCENTS,"#13B5EC"),
        "headline_role":role,
        "scene_role":scene,
        "proof_feature_index":index,
        "shapes":shapes,
        "source":"AI-format-specific-canvas",
    }


def format_instruction():
    """One Gemini response asks for four unique canvases, not scaled posters."""
    return (
        "Also output a top-level format_canvases object containing EXACTLY SIX "
        "independently designed artwork briefs, keyed social_square (1080x1080), "
        "social_story (1080x1920), website_banner (1600x600), email_header "
        "(1200x420), linkedin_graphic (1200x627), and landscape_ad "
        "(1600x900). Design EACH from scratch for its own aspect ratio, "
        "viewer attention and medium. NEVER copy/scale any of the three poster "
        "compositions into these formats. Each brief has zones with headline, "
        "product and optional proof/price regions, each [x,y,width,height] "
        "integers normalized 0..1000; social_square and social_story MUST also "
        "have proof. Safe x=35..965. Safe y ranges: square 150..905, Story "
        "160..860 (leave app UI overlays clear), website_banner 230..880, "
        "email_header 245..845, linkedin_graphic 225..865, and landscape_ad "
        "205..895. Do not let ANY zones overlap. Product zone "
        "minimum normalized width 260 and height 310 on banners or 265 for "
        "social; headline width minimum 320 social or 280 banners, height "
        "minimum 95; proof min width 220 height 70; price min width 215 "
        "height 105. On banners choose a horizontal composition with "
        "minimal copy and a wide product hero; on Story create a clear vertical "
        "sequence and leave generous mobile tap overlays; square should have "
        "a strong immediate hook; email header should be concise and legible; "
        "LinkedIn should suit professional trade buyers with concise evidence; "
        "the landscape advert should offer a strong horizontal hero and clear "
        "marketing hierarchy. "
        "Each brief also returns headline_role and scene_role each one of "
        "technical_application, price_promo, product_selected; "
        "proof_feature_index is an integer referring to the supplied official "
        "features array (or -1 for none). No new or invented claims. "
        "Choose background workshop-photo/studio-gradient/industrial, "
        "mood bold/understated/editorial/technical/energetic, motif "
        "none/speed-lines/circles/industrial-grid/diagonal-bars, "
        "headline_style massive/editorial/compact, photo_focus "
        "left/centre/right, and accent one of #13B5EC #40C1E8 #FFC83A "
        "#F9A842 #D9E75B #FFFFFF #71D6EE #F1E9D8. Optional shapes array "
        "up to six decorative objects: {kind:panel/outline/circle/ribbon/line, "
        "box:[x,y,w,h], ink:accent/cyan/white, opacity:10..80}. "
        "The genuine photo will be composited by the application; no AI "
        "image URLs, invented tool photos, logos, text or price values."
    )


def _background(kind, brief, scene, variant):
    w,h,*_=FORMATS[kind]
    canvas=Image.new("RGBA",(w,h),(7,28,48,255))
    if scene and brief["background"]=="workshop-photo":
        try:
            source=Image.open(io.BytesIO(scene)).convert("RGB")
            centre={"left":(.3,.5),"centre":(.5,.5),"right":(.7,.5)}[brief["photo_focus"]]
            photo=ImageOps.fit(source,(w,h),Image.Resampling.LANCZOS,
                               centering=centre)
            photo=ImageEnhance.Brightness(photo).enhance((.49,.56)[variant%2])
            photo=photo.filter(ImageFilter.GaussianBlur(max(1,h/900)))
            canvas.paste(photo,(0,0))
        except (OSError,ValueError):pass
    else:
        d=ImageDraw.Draw(canvas,"RGBA")
        for y in range(0,h,16):
            t=y/max(1,h)
            d.rectangle((0,y,w,y+16),fill=(6+round(14*t),30+round(24*t),
                                           52+round(28*t),255))
        if brief["background"]=="industrial":
            for x in range(0,w,max(60,w//13)):
                d.line((x,0,x,h),fill=(55,182,229,35),width=2)
    d=ImageDraw.Draw(canvas,"RGBA")
    motif=brief["motif"]
    if motif in ("diagonal-bars","speed-lines"):
        for j in range(6):
            x=round(w*(.32+j*.12))
            d.line((x,-h//6,x-w//3,h+h//6),fill=(42,189,230,35),
                   width=max(2,w//130))
    elif motif=="circles":
        for fraction in (.19,.33,.5):
            radius=round(min(w,h)*fraction)
            cx,cy=round(w*.76),round(h*.51)
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),
                      outline=(55,194,230,43),width=4)
    elif motif=="industrial-grid":
        for yy in range(0,h,max(70,h//11)):
            d.line((0,yy,w,yy),fill=(44,168,221,32),width=2)
    overlay=Image.new("RGBA",(w,h),(3,17,31,60 if brief["mood"]=="energetic" else 82))
    canvas=Image.alpha_composite(canvas,overlay)
    shapes=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(shapes,"RGBA")
    ink={"accent":ImageColor.getrgb(brief["accent"]),
         "cyan":(30,180,237),"white":(240,251,255)}
    for shape in brief["shapes"]:
        box=_rect(shape["box"],(w,h))
        rgba=(*ink[shape["ink"]],shape["opacity"])
        k=shape["kind"]
        if k=="panel":
            d.rounded_rectangle(box,radius=min(20,max(4,h//70)),fill=rgba)
        elif k=="outline":
            d.rounded_rectangle(box,radius=min(20,max(4,h//70)),
                                outline=rgba,width=max(2,w//280))
        elif k=="circle":
            d.ellipse(box,outline=rgba,width=max(2,w//200))
        elif k=="ribbon":
            x0,y0,x1,y1=box
            d.polygon([(x0+min(40,x1-x0),y0),(x1,y0),
                       (x1-min(40,x1-x0),y1),(x0,y1)],fill=rgba)
        elif k=="line":
            d.line((box[0],box[1],box[2],box[3]),
                   fill=rgba,width=max(2,w//240))
    return Image.alpha_composite(canvas,shapes)


def _hero(canvas,blob,bounds,variant=0):
    data=inspected_product(blob)
    if not data["isolated"]:
        raise ValueError("Official product photo cannot be isolated without a white background")
    image=data["rgba"].copy()
    x0,y0,x1,y1=bounds
    avail_w,avail_h=x1-x0,y1-y0
    scale=(.96,1.0)[variant%2]
    ratio=min(avail_w/max(1,image.width),avail_h/max(1,image.height))*scale
    if ratio<=0:raise ValueError("Product image cannot fit the artwork")
    image=image.resize((max(1,int(image.width*ratio)),
                        max(1,int(image.height*ratio))),Image.Resampling.LANCZOS)
    x=x0+(avail_w-image.width)//2
    y=y0+(avail_h-image.height)//2
    # Preserve manufacturer colour/shape pixel values, including white parts.
    canvas.alpha_composite(image,(x,y))
    alpha=image.getchannel("A")
    visible=alpha.getbbox()
    if not visible:raise ValueError("Manufacturer cutout is empty")
    fraction=round((visible[2]-visible[0])*(visible[3]-visible[1])/
                   max(1,canvas.width*canvas.height),4)
    record_product((x,y,x+image.width,y+image.height),fraction,True)


def _headline(title,role,product):
    # Copy is never supplied as arbitrary model prose.
    if role and role in ROLE_IDS:
        candidate=title.get(role) if isinstance(title,dict) else None
        if candidate:return str(candidate)
    return str(product.get("title") or "Laser Tools product")


def _label(canvas,part,distributor):
    w,h=canvas.size
    d=ImageDraw.Draw(canvas,"RGBA")
    band=round(h*.137)
    d.rectangle((0,0,w,band),fill=(5,23,42,248))
    d.rectangle((0,band-5,w,band),fill="#13B5EC")
    x,y=round(w*.04),round(h*.028)
    size=max(16,min(50,round(h*.07)))
    d.text((x,y),"LASER",font=font(size,"bold"),fill="white")
    if h>550:
        d.text((x,y+round(size*.97)),"TOOLS",
               font=font(max(12,round(size*.38)),"bold"),fill="white")
    part_text="PART "+str(part or "")[:18]
    d.text((round(w*.75),y+round(size*.2)),part_text,
           font=font(max(12,min(30,round(size*.48))),"bold"),fill="#DAF1FA")
    if distributor:
        logo=get_brand_image(distributor)
        if logo is not None:
            mark=logo.convert("RGBA")
            mark.thumbnail((round(w*.18),round(band*.7)),Image.Resampling.LANCZOS)
            bx=round(w*.55)
            by=max(2,(band-mark.height)//2)
            d.rounded_rectangle((bx-7,by-5,bx+mark.width+7,by+mark.height+5),
                                radius=6,fill="#FFFFFF")
            canvas.alpha_composite(mark,(bx,by))
    d.rectangle((0,round(h*.94),w,h),fill=(4,22,40,252))
    footer="DRAFT · VERIFY FACTS AND PRICE BEFORE PUBLICATION"
    font_size=max(11,min(18,round(h*.021)))
    # Footer is deliberately independent of model zones.
    d.text((round(w*.035),round(h*.958)),footer,
           font=font(font_size,"regular"),fill="#CDE1EF")


def _fit_text(draw,text,region,kind,style="editorial",is_headline=False):
    w,h,*_=FORMATS[kind]
    base=min(74,round((.059 if is_headline else .035)*h))
    if kind in ("website_banner","email_header","linkedin_graphic","landscape_ad"):
        base=min(64,max(26,round(.071*h if is_headline else .045*h)))
    base=int(base*{"massive":1.12,"editorial":1.0,"compact":.87}.get(style,1))
    if is_headline:
        return _text(draw,text,region,base=max(base,23),
                     minsize=max(15,round(h*.025)),
                     maxlines=5,role="headline")
    return _text(draw,text,region,base=max(22,base),
                 minsize=max(13,round(h*.018)),
                 bold=False,maxlines=5,role="proof")


def render_format_canvas(kind,brief,product,photo,*,scenes=(),headlines=None,
                         facts=(),distributor=None,variant=0):
    """Render a real-format original composition from a validated AI brief."""
    validated=validate_format_canvas(kind,brief,len(facts))
    if not validated:raise ValueError("Invalid format-specific AI artwork geometry")
    if variant not in (0,1):raise ValueError("Unsupported format rendering variation")
    brief=validated
    w,h,*_=FORMATS[kind]
    roles=dict(zip(ROLE_IDS,range(3)))
    scene_idx=roles[brief["scene_role"]]
    scene=scenes[scene_idx] if len(scenes)>scene_idx else None
    canvas=_background(kind,brief,scene,variant)
    _label(canvas,product.get("part"),distributor)
    region=brief["zones"]
    _hero(canvas,photo,_rect(region["product"],(w,h)),variant)
    d=ImageDraw.Draw(canvas,"RGBA")
    accent=brief["accent"]
    heading=_headline(headlines,brief["headline_role"],product)
    rect=_rect(region["headline"],(w,h))
    if brief["headline_style"]=="massive":
        rail=max(3,w//280)
        d.rectangle((rect[0]-rail*3,rect[1],rect[0]-rail,
                     min(rect[3],rect[1]+round(h*.10))),fill=accent)
    _fit_text(d,heading,rect,kind,brief["headline_style"],True)
    proof_idx=brief["proof_feature_index"]
    chosen=str(facts[proof_idx]) if proof_idx is not None else ""
    if "proof" in region and not chosen:
        chosen=next((str(v) for v in facts if str(v).strip()),"")
    if "proof" in region:
        rect=_rect(region["proof"],(w,h))
        d.rectangle((rect[0],rect[1],rect[0]+min(round(w*.07),rect[2]-rect[0]),
                     rect[1]+max(3,h//240)),fill=accent)
        if chosen:
            inset=max(7,round(h*.009))
            _fit_text(d,chosen,(rect[0],rect[1]+inset,rect[2],rect[3]),
                      kind,"compact")
    if "price" in region:
        rect=_rect(region["price"],(w,h))
        d.rounded_rectangle(rect,radius=max(7,round(h*.014)),
                            fill=(6,36,63,242),outline=accent,width=max(2,w//380))
        from poster_quality import record_area
        record_area("price",rect)
        p=verified_price(product)
        label=(str(p["amount"])+((" · "+str(p["vat"])) if p.get("vat") else "")
               if p.get("amount") else "PRICE ON REQUEST")
        inset=max(8,round(w*.009))
        _text(d,label,(rect[0]+inset,rect[1]+6,
                       rect[2]-inset,rect[3]-5),
              base=max(24,round(h*.05)),minsize=max(14,round(h*.025)),
              maxlines=3,role="price")
    out=io.BytesIO()
    canvas.convert("RGB").save(out,"PNG",optimize=False,compress_level=3)
    return out.getvalue()


def quality_check_format(blob,kind,tracked,source_report):
    """Hard image/text/source rejection; no OCR or false AI style guarantees."""
    w,h,*_=FORMATS[kind]
    reasons=[]
    try:
        image=Image.open(io.BytesIO(blob))
        image.load()
        if image.size!=(w,h):reasons.append("Incorrect native aspect ratio/dimensions")
        preview=image.convert("RGB").resize((100,100),Image.Resampling.BILINEAR)
        pixels=list(preview.getdata())
        whiten=sum(min(p)>=243 and max(p)-min(p)<15 for p in pixels)/len(pixels)
        contrast=sum(ImageStat.Stat(preview).stddev)/3
        if whiten>.37:reasons.append("Excessive white-background area")
        if contrast<17:reasons.append("Insufficient poster contrast")
    except (OSError,ValueError):
        return {"passed":False,"issues":["Corrupted format artwork"],"score":0}
    if not source_report.get("passed"):
        reasons.append("Product photo failed authenticity/quality preflight")
    text=tracked.texts
    if not any(t["role"]=="headline" for t in text):
        reasons.append("Missing headline")
    if any(t["truncated"] for t in text):
        reasons.append("Text was clipped")
    if any(t["box"][0]<0 or t["box"][1]<0 or
           t["box"][2]>w or t["box"][3]>h for t in text):
        reasons.append("Text outside format canvas")
    products=tracked.products
    if not products or max(p["visible_fraction"] for p in products)<.032:
        reasons.append("Product hero too small")
    score=max(0,100-len(reasons)*24-max(0,round((.2-whiten)*-10)))
    return {"passed":not reasons,"issues":list(dict.fromkeys(reasons)),
            "score":score,"native_dimensions":[w,h],
            "render_engine":"ai-original-format-canvas",
            "white_fraction":round(whiten,4),
            "source_photo_verified":True}


def generate_format(kind,brief,product,photo,*,scenes=(),headlines=None,
                    facts=(),distributor=None,source_report=None):
    """Two bounded renders using the same AI-authored layout; reject failures."""
    report=source_report or require_good_asset(photo)
    successes=[]
    attempts=[]
    for variant in (0,1):
        try:
            with capture() as tracking:
                output=render_format_canvas(
                    kind,brief,product,photo,scenes=scenes,headlines=headlines,
                    facts=facts,distributor=distributor,variant=variant)
            checked=quality_check_format(output,kind,tracking,report)
        except (ValueError,OSError,TypeError,KeyError) as exc:
            checked={"passed":False,"score":0,"issues":[str(exc)[:160]]}
            output=None
        checked["variation"]=variant
        attempts.append(checked)
        if checked["passed"]:successes.append((output,checked))
    if not successes:
        detail="; ".join(dict.fromkeys(
            issue for item in attempts for issue in item["issues"]))
        raise ValueError("AI "+kind+" artwork rejected by quality controls: "+detail[:300])
    best=max(successes,key=lambda item:item[1]["score"])
    outcome=dict(best[1])
    outcome["candidates_checked"]=len(attempts)
    outcome["rejected_candidates"]=sum(not a["passed"] for a in attempts)
    return best[0],outcome
