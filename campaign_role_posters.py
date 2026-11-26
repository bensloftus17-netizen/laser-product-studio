"""Two deliberately different 1200x1500 campaign artboards.

These are typography/layout compositions, NOT generated pictures of tools:
the product is the original manufacturer photo, unchanged apart from resizing;
context comes from reviewed real stock / verified manufacturer application
photography and is labelled as illustrative context in export metadata.
"""
from __future__ import annotations

import io
import re
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from poster import font
from brand_assets import get_brand_image
from campaign_art_quality import inspected_product
from poster_quality import record_text, record_product
from promo_art_direction import draw_background_motif

W,H=1200,1500
NAVY="#071F37"
BLUE="#056EB0"
WHITE="#FFFFFF"
INK="#123754"


def _size(draw, line, size, bold=True):
    b=draw.textbbox((0,0),line,font=font(size,"bold" if bold else "regular"))
    return b[2]-b[0]


def _wrap(draw, text, width, size, bold):
    lines=[]
    row=""
    for word in str(text or "").split():
        new=(row+" "+word).strip()
        if _size(draw,new,size,bold)<=width:
            row=new
        else:
            if row:lines.append(row)
            row=""
            for char in word:
                if row and _size(draw,row+char,size,bold)>width:
                    lines.append(row)
                    row=char
                else:row+=char
    if row:lines.append(row)
    return lines


def fitted(draw, text, box, sizes, color, max_lines=3, bold=True):
    x0,y0,x1,y1=box
    w,h=max(1,x1-x0),max(1,y1-y0)
    for size in sizes:
        rows=_wrap(draw,text,w,size,bold)
        step=round(size*1.25)
        if len(rows)<=max_lines and len(rows)*step<=h:break
    else:
        size=sizes[-1]
        step=round(size*1.25)
        limit=max(1,min(max_lines,h//max(1,step)))
        original=rows
        rows=rows[:limit]
        if len(original)>limit and rows:
            last=rows[-1]
            while last and _size(draw,last+"…",size,bold)>w:last=last[:-1]
            rows[-1]=last.rstrip()+"…"
    for i,line in enumerate(rows):
        draw.text((x0,y0+i*step),line,font=font(size,"bold" if bold else "regular"),fill=color)
    record_text(text,box,rows,size,"headline" if size>=35 else "text")


def product_photo(canvas, blob, bounds, *, scale=1.0):
    """Safely isolate genuine tool pixels and place WITHOUT a white card.

    Real white/metal components stay original. If automatic edge segmentation
    is uncertain, retain the photograph on a *small dark mat*, mark the
    campaign for review and never silently paint an invented tool silhouette.
    """
    x0,y0,x1,y1=map(int,bounds)
    x0,y0=max(0,x0),max(0,y0)
    x1,y1=min(canvas.width,x1),min(canvas.height,y1)
    if x1<=x0 or y1<=y0:
        raise ValueError("Product has no space on the poster")
    info=inspected_product(blob)
    image=info["rgba"]
    w,h=max(1,x1-x0),max(1,y1-y0)
    limit_w=max(1,round(w*.94*min(scale,1.0)))
    limit_h=max(1,round(h*.94*min(scale,1.0)))
    ratio=min(limit_w/max(1,image.width),limit_h/max(1,image.height))
    image=image.resize((max(1,int(image.width*ratio)),
                        max(1,int(image.height*ratio))),Image.Resampling.LANCZOS)
    x=x0+(w-image.width)//2
    y=y0+(h-image.height)//2
    if not info["isolated"]:
        # Low-confidence photo: never fake extraction or allow a full-canvas
        # white rectangle. Deliberate smaller framed source-photo preview
        # requires a human cutout review before publication.
        d=ImageDraw.Draw(canvas)
        pad=15
        d.rounded_rectangle((max(0,x-pad),max(0,y-pad),
                             min(W,x+image.width+pad),min(H,y+image.height+pad)),
                            radius=16,fill="#16354F",outline="#6E9AB5",width=3)
    if info["isolated"]:
        from PIL import ImageStat
        alpha=image.getchannel("A")
        mean=sum(ImageStat.Stat(image.convert("RGB"),mask=alpha).mean)/3
        if mean<115:
            # Dark tool against a dark workshop? Lift the *background only*.
            # The original manufacturer pixels remain entirely untouched.
            spotlight=Image.new("RGBA",(W,H),(0,0,0,0))
            glow_draw=ImageDraw.Draw(spotlight,"RGBA")
            spread=max(24,round(min(image.size)*.12))
            glow_draw.ellipse((max(0,x-spread),max(0,y-spread),
                               min(W,x+image.width+spread),
                               min(H,y+image.height+spread)),
                              fill=(112,203,240,94))
            spotlight=spotlight.filter(ImageFilter.GaussianBlur(52))
            canvas.alpha_composite(spotlight)
        # A natural studio shadow behind genuine steel, not a tool redraw.
        shadow=Image.new("RGBA",image.size,(5,16,28,0))
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(17)).point(
            lambda value:int(value*.32)))
        canvas.alpha_composite(shadow,(x+8,y+14))
    canvas.alpha_composite(image,(x,y))
    record_product((x,y,x+image.width,y+image.height),
                   image.width*image.height/max(1,W*H),info["isolated"])
    return {"isolated":info["isolated"],"needs_manual_cutout":info["needs_manual_cutout"],
            "position":(x,y,x+image.width,y+image.height)}


def actual_scene(canvas,blob,box,brightness=.72,blur=1.2,focus="centre"):
    """Real context remains a separate background region, never a fake tool."""
    if not blob:return False
    x0,y0,x1,y1=box
    try:
        pic=Image.open(io.BytesIO(blob)).convert("RGB")
        pic.thumbnail((2100,2100),Image.Resampling.LANCZOS)
        centred={"left":(.32,.5),"centre":(.5,.5),"right":(.68,.5)}.get(
            focus,(.5,.5))
        cropped=ImageOps.fit(pic,(x1-x0,y1-y0),Image.Resampling.LANCZOS,
                             centering=centred)
        cropped=ImageEnhance.Brightness(cropped).enhance(brightness)
        if blur:cropped=cropped.filter(ImageFilter.GaussianBlur(blur))
        canvas.paste(cropped,(x0,y0))
        return True
    except (OSError,ValueError):
        return False


def brand(draw,part,background=NAVY,light=True):
    ink=WHITE if light else NAVY
    draw.text((54,38),"LASER",font=font(66,"bold"),fill=ink)
    draw.text((58,111),"TOOLS",font=font(19,"bold"),fill=ink)
    fitted(draw,"PART "+str(part),(824,68,1154,120),(34,28,23),ink,1)


def co_brand(canvas,distributor):
    if not distributor:return
    mark=get_brand_image(distributor)
    if mark is None:return
    mark=mark.convert("RGBA")
    mark.thumbnail((200,76),Image.Resampling.LANCZOS)
    x=580
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((x-12,28,x+mark.width+12,132),radius=10,fill="#FFFFFF")
    canvas.paste(mark,(x,42),mark)


def _clip_facts(concept):
    all_facts=[]
    for fact in concept.get("features") or []:
        text=" ".join(str(fact).split())[:175]
        if text and text not in all_facts:all_facts.append(text)
        if len(all_facts)>=3:break
    selling=" ".join(str(concept.get("selling_point") or "").split())[:175]
    if selling and selling not in all_facts:all_facts.insert(0,selling)
    return all_facts[:3]


def _story_copy(concept):
    """Use one short manufacturer-derived phrase, never a long URL/paragraph."""
    text=str(concept.get("selling_point") or "")
    # Original manufacturer wording can include pointers to OTHER product
    # pages or long URLs; neither is useful as a poster headline.
    import re
    text=re.split(r"https?://|www\.",text,maxsplit=1,flags=re.I)[0]
    text=re.split(r"\bFor full details\b|\bTo order\b",text,maxsplit=1,flags=re.I)[0]
    text=" ".join(text.split()).strip(" ,;.:")
    if len(text)>132:
        # Source excerpt only: no model-created technical claims. Prefer a
        # complete first sentence and display full info in campaign copy.
        sentence=re.split(r"(?<=[.!?])\s+",text)[0]
        if 24<len(sentence)<=132:text=sentence
        else:
            limit=text.rfind(" ",0,130)
            text=text[:limit if limit>72 else 128].rstrip(" ,;")+"."
    return text


def _contextual_base(scene,variant=0,tone="#07243C",art=None):
    art=art or {}
    canvas=Image.new("RGBA",(W,H),tone)
    if scene:
        x0,y0,x1,y1=(0,190,1200,1240)
        mood={"bright":1.13,"balanced":1.0,"dramatic":.83}.get(
            art.get("background_mood"),1.0)
        actual_scene(canvas,scene,(x0,y0,x1,y1),
                     brightness=(.60,.52,.68)[variant%3]*mood,blur=1.7,
                     focus=art.get("photo_focus","centre"))
    # Decorative art direction is applied only to the background, never
    # to manufacturer tool pixels or factual copy.
    if art.get("graphic_motif"):
        canvas=draw_background_motif(canvas,art)
    # Brand-blue gradient overlay, not an arbitrary photo covered in white.
    shade=Image.new("RGBA",(W,H),(0,0,0,0))
    draw=ImageDraw.Draw(shade)
    for y in range(180,1330,4):
        alpha=round(88+72*(y-180)/1150)
        draw.rectangle((0,y,W,y+4),fill=(4,26,48,alpha))
    canvas=Image.alpha_composite(canvas,shade)
    return canvas


def _export(canvas):
    buffer=io.BytesIO()
    canvas.convert("RGB").save(buffer,"PNG",optimize=False,compress_level=3)
    return buffer.getvalue()


def technical_poster(product,official_photo,concept,scene=None,distributor=None):
    """Dark application editorial: a large, properly cut-out genuine hero."""
    part=product.get("part","")
    variation=int(concept.get("variant") or 0)%3
    accent=(concept.get("visual_plan") or {}).get("accent","#15B6E4")
    plan=concept.get("visual_plan") or {}
    art=plan.get("art_direction") or {}
    canvas=_contextual_base(scene,variation,tone="#08273F",art=art)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,W,190),fill="#082541")
    d.rectangle((0,181,W,192),fill=accent)
    brand(d,part)
    co_brand(canvas,distributor)
    d.rectangle((46,248,58,303),fill=accent)
    fitted(d,"APPLICATION / TECHNICAL",(81,252,1120,307),
           (33,30,27),accent,1)
    fitted(d,concept.get("headline") or product.get("title","Laser Tools product"),
           (58,331,1124,540),(65,59,52,45,40,35,30),WHITE,3)
    # Three distinct approved compositions; larger product, controlled scale.
    if variation==0:hero=(395,550,1155,1175)
    elif variation==1:hero=(382,555,1160,1195)
    else:hero=(404,565,1170,1186)
    product_photo(canvas,official_photo,hero,
                  scale=min(1.16,max(.86,art.get("product_scale",104)/100)))
    d=ImageDraw.Draw(canvas,"RGBA")
    # A small technical information rail balances the tool, not a massive
    # white product photograph panel.
    d.rounded_rectangle((47,823,373,1142),radius=17,fill=(5,32,54,218),
                        outline=(63,159,201,180),width=2)
    d.rectangle((72,852,83,900),fill=accent)
    fact=_story_copy(concept)
    # A dimensional or weight spec is technical data, not an application:
    # label it correctly instead of claiming an unverified use case.
    spec_label=bool(re.match(
        r"^(?:Dimensions|Weight|Length|Width|Height|Power|Voltage|Brightness|Charging time)\s*:",
        fact,flags=re.I))
    fitted(d,"KEY SPECIFICATIONS" if spec_label else "THE APPLICATION",
           (105,856,345,917),(23,21,19),accent,2)
    if fact:
        fitted(d,fact,(75,938,344,1108),(27,25,22,20,18,16),WHITE,6,bold=False)
    d.rectangle((0,1214,W,H),fill=(4,25,44,245))
    d.rectangle((53,1253,1138,1262),fill=accent)
    fitted(d,"TECHNICAL FOCUS",(62,1287,1137,1332),
           (28,25,22),accent,1)
    verified=[
        str(x).strip() for x in concept.get("features") or []
        if str(x).strip() and str(x).strip()!=str(concept.get("selling_point") or "").strip()
    ]
    secondary=_story_copy({"selling_point":verified[0]}) if verified else ""
    fitted(d,secondary or "Check the official product record for full specifications.",
           (62,1349,1133,1427),(28,25,22,19,17),WHITE,3,bold=False)
    fitted(d,"DRAFT / VERIFY APPLICATIONS BEFORE PUBLICATION",
           (61,1462,1132,1487),(17,15,13),"#B9D7EB",1,bold=False)
    return _export(canvas)


def smart_poster(product,official_photo,concept,scene=None,distributor=None):
    """Feature-led split-story ad, never a second price or technical flyer."""
    from flexible_canvas import _text

    part=product.get("part","")
    plan=concept.get("visual_plan") or {}
    theme=str(concept.get("name") or "PRODUCT HIGHLIGHT")
    variation=int(concept.get("variant") or 0)%3
    accent=plan.get("accent","#1BB6D4")
    art=plan.get("art_direction") or {}
    canvas=_contextual_base(scene,variation,tone="#06223A",art=art)
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,W,186),fill="#081E34")
    d.rectangle((0,175,W,190),fill=accent)
    brand(d,part)
    co_brand(canvas,distributor)
    _text(d,"LASER / PRODUCT SPOTLIGHT",(54,243,1135,290),
          base=30,minsize=22,maxlines=1,colour=accent)
    _text(d,concept.get("headline") or product.get("title","Laser Tools product"),
          (52,304,1146,542),base=66,minsize=26,maxlines=5,role="headline")
    # A broad colored architectural shape behind, but NEVER white paper.
    # Photographic workshop context remains on the right and the original
    # tool silhouette is clearly legible in front of both.
    if variation==0:
        d.polygon([(0,595),(745,595),(580,1208),(0,1208)],
                  fill=(9,67,101,225))
        hero=(112,570,1100,1192)
    elif variation==1:
        d.polygon([(0,642),(870,551),(785,1210),(0,1210)],
                  fill=(7,79,112,220))
        hero=(72,572,1128,1201)
    else:
        d.polygon([(0,555),(690,633),(733,1202),(0,1202)],
                  fill=(8,57,88,226))
        hero=(118,554,1138,1185)
    product_photo(canvas,official_photo,hero,
                  scale=min(1.16,max(.86,art.get("product_scale",104)/100)))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,1201,W,H),fill=(6,29,52,248))
    d.rectangle((54,1237,1144,1247),fill=accent)
    _text(d,theme.upper(),(61,1255,1140,1334),
          base=34,minsize=22,maxlines=2,colour=accent)
    detail=_story_copy(concept)
    if detail:
        _text(d,detail,(61,1345,1133,1448),
              base=30,minsize=18,maxlines=4,bold=False,role="proof")
    _text(d,"GENUINE PRODUCT PHOTO · DRAFT FOR REVIEW",
          (61,1461,1133,1492),base=16,minsize=12,maxlines=1,
          colour="#B9D7EB",bold=False)
    return _export(canvas)
