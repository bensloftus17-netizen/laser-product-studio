"""Two deliberately different 1200x1500 campaign artboards.

These are typography/layout compositions, NOT generated pictures of tools:
the product is the original manufacturer photo, unchanged apart from resizing;
context comes from reviewed real stock / verified manufacturer application
photography and is labelled as illustrative context in export metadata.
"""
from __future__ import annotations

import io
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from poster import font
from brand_assets import get_brand_image

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


def product_photo(canvas, blob, bounds):
    x0,y0,x1,y1=bounds
    try:
        image=ImageOps.exif_transpose(Image.open(io.BytesIO(blob))).convert("RGBA")
    except (OSError,ValueError) as exc:
        raise ValueError("Original manufacturer image could not be read") from exc
    image.thumbnail((max(1,x1-x0-42),max(1,y1-y0-42)),Image.Resampling.LANCZOS)
    x=x0+(x1-x0-image.width)//2
    y=y0+(y1-y0-image.height)//2
    # Preserve manufacturer pixels; any transparent source uses its alpha.
    canvas.paste(image,(x,y),image)


def actual_scene(canvas,blob,box,brightness=.72,blur=1.2):
    """Real context remains a separate background region, never a fake tool."""
    if not blob:return False
    x0,y0,x1,y1=box
    try:
        pic=Image.open(io.BytesIO(blob)).convert("RGB")
        pic.thumbnail((2100,2100),Image.Resampling.LANCZOS)
        cropped=ImageOps.fit(pic,(x1-x0,y1-y0),Image.Resampling.LANCZOS)
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


def technical_poster(product,official_photo,concept,scene=None,distributor=None):
    """Application/spec editorial layout: *no huge price bubble*."""
    part=product.get("part","")
    canvas=Image.new("RGBA",(W,H),"#F2F7FB")
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,1200,186),fill=NAVY)
    d.rectangle((0,181,1200,193),fill="#0A90D2")
    brand(d,part)
    co_brand(canvas,distributor)
    d.rectangle((56,238,1105,252),fill="#0A90D2")
    fitted(d,"APPLICATION / TECHNICAL",(58,282,1105,339),(36,32,26),"#0671AA",1)
    fitted(d,product.get("title","Laser Tools product"),(55,355,1130,550),
           (75,66,58,51,44,38,32),INK,3)
    # The contextual photo is intentionally separate from the genuine product
    # panel. The image is not evidence of specific vehicle fitment.
    actual_scene(canvas,scene,(0,610,1200,985),brightness=.55,blur=2)
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((54,642,1146,1203),radius=22,fill=WHITE,
                        outline="#C8DFEB",width=4)
    product_photo(canvas,official_photo,(93,665,1098,1169))
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,1227,1200,1500),fill=NAVY)
    d.rectangle((58,1262,67,1436),fill="#19A9DB")
    proof=_clip_facts(concept)
    fitted(d,"VERIFIED PRODUCT INFORMATION",(95,1269,1093,1313),
           (29,26,22), "#A7E2FC",1)
    if proof:
        fitted(d,proof[0],(96,1332,1122,1433),
               (31,27,24,21,19),WHITE,3,bold=False)
    else:
        fitted(d,"Review the manufacturer information for confirmed applications and specifications.",
               (96,1332,1122,1433),(26,23,21),WHITE,3,bold=False)
    fitted(d,"DRAFT · VERIFY APPLICATIONS BEFORE PUBLICATION",
           (62,1467,1135,1494),(16,14), "#CAE4F0",1,bold=False)
    out=io.BytesIO();canvas.convert("RGB").save(out,"PNG",optimize=True)
    return out.getvalue()


def smart_poster(product,official_photo,concept,scene=None,distributor=None):
    """Split editorial storytelling focused on a product-specific third angle."""
    part=product.get("part","")
    plan=concept.get("visual_plan") or {}
    theme=concept.get("third_angle") or "workshop_solution"
    accent=plan.get("accent","#18AED8")
    variant=int(concept.get("variant") or 0)%3
    paper=("#FBFBF8","#F3F9FB","#F7F9F5")[variant]
    canvas=Image.new("RGBA",(W,H),paper)
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,1200,180),fill=NAVY)
    d.rectangle((0,169,1200,187),fill=accent)
    brand(d,part)
    co_brand(canvas,distributor)
    actual_scene(canvas,scene,(520,348,1200,1070),brightness=.82,blur=1.6)
    d=ImageDraw.Draw(canvas)
    # Poster Three is NOT a second price advert: a large product image takes
    # the left panel while real workshop context is visible on the right.
    d.polygon([(0,340),(755,340),(590,1109),(0,1109)],fill="#DCEEF6")
    d.rounded_rectangle((41,418,765,1090),radius=20,fill=WHITE)
    product_photo(canvas,official_photo,(55,427,746,1072))
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,1120,1200,1500),fill=paper)
    d.rectangle((59,1154,1140,1165),fill=accent)
    fitted(d,"THE EXTRA ANGLE · "+str(concept.get("name","PRODUCT DETAIL")).upper(),
           (59,214,1141,271),(34,30,26),BLUE,2)
    fitted(d,product.get("title","Laser Tools product"),
           (60,274,1139,373),(50,43,37,30,26),INK,2)
    proof=_clip_facts(concept)
    fitted(d,theme.replace("_"," ").upper(),(62,1196,1140,1249),
           (39,34,29),BLUE,1)
    if proof:
        fitted(d,proof[0],(61,1281,1136,1411),
               (40,35,31,27,23),INK,3,bold=False)
    else:
        fitted(d,"Explore this product's official specifications before ordering.",
               (61,1281,1136,1411),(32,28,23),INK,3,bold=False)
    fitted(d,"GENUINE LASER TOOLS PRODUCT PHOTO · DRAFT FOR REVIEW",
           (63,1457,1135,1489),(18,16,14),"#507187",1,bold=False)
    out=io.BytesIO();canvas.convert("RGB").save(out,"PNG",optimize=True)
    return out.getvalue()
