"""Automatic promotional-artwork QA, repair guidance, and safe rejection.

Render-time geometry is more dependable than OCR: each _fit call and image
placement records what was actually drawn. QA does not fabricate prices,
vehicle compatibility or manufacturer products. It is intentionally
conservative about white product components: only large paper-white areas
with evidence of an original white packshot are flagged.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image, ImageChops, ImageFilter, ImageStat

_CURRENT=ContextVar("laser_promo_quality_capture",default=None)
SIZE=(1200,1500)


@dataclass
class QualityCapture:
    texts:list=field(default_factory=list)
    areas:list=field(default_factory=list)
    products:list=field(default_factory=list)


@contextmanager
def capture():
    result=QualityCapture()
    token=_CURRENT.set(result)
    try:
        yield result
    finally:
        _CURRENT.reset(token)


def record_text(content,rect,lines,size,role="text"):
    current=_CURRENT.get()
    if current is None:return
    text=str(content or "").strip()
    current.texts.append({
        "text":text,"box":tuple(int(v) for v in rect),
        "lines":tuple(lines),"font_size":int(size),"role":role,
        "truncated":any("…" in line for line in lines),
    })


def record_area(role,box):
    current=_CURRENT.get()
    if current is None:return
    current.areas.append({"role":role,"box":tuple(int(v) for v in box)})


def record_product(box,visible_fraction,isolated):
    current=_CURRENT.get()
    if current is None:return
    current.products.append({"box":tuple(int(v) for v in box),
                             "visible_fraction":round(float(visible_fraction),4),
                             "isolated":bool(isolated)})


def _overlap(a,b):
    x0,y0,x1,y1=a
    u0,v0,u1,v1=b
    width=max(0,min(x1,u1)-max(x0,u0))
    height=max(0,min(y1,v1)-max(y0,v0))
    return width*height


def assess_text_and_geometry(capture:QualityCapture,price:dict,concept:dict):
    """Detect clipped/overlapping key elements, missing RRP or cropped tool."""
    failures=[]
    warnings=[]
    headings=[t for t in capture.texts if t["role"]=="headline"]
    if not headings:
        failures.append("Headline was not drawn")
    elif any(t["truncated"] for t in headings):
        failures.append("Headline text was clipped")
    for t in capture.texts:
        x0,y0,x1,y1=t["box"]
        if x0<0 or y0<0 or x1>SIZE[0] or y1>SIZE[1] or x1<=x0 or y1<=y0:
            warnings.append("Text safe area extends beyond the poster")
            break
    products=capture.products
    if not products:
        failures.append("Product photograph was not placed")
    elif any(p["visible_fraction"]<.94 for p in products):
        failures.append("Product photograph cropped by its frame")
    if any(not p["isolated"] for p in products):
        warnings.append("Manufacturer photo could not be cut out confidently")
    price_areas=[a["box"] for a in capture.areas if a["role"]=="price"]
    if not price_areas:
        failures.append("RRP badge missing")
    # The amount is required as rendered text, not merely as a product-data
    # field. Partial matches still count since different VAT labels use
    # separate lines and the source data is independently verified.
    amount=price.get("amount") or "ON REQUEST"
    drawn=" ".join(" ".join(t["lines"]) for t in capture.texts).upper()
    if str(amount).upper() not in drawn:
        failures.append("Verified price not visibly rendered")
    if price.get("amount") and price.get("vat") and price["vat"] not in drawn:
        failures.append("Verified VAT status not visibly rendered")
    for h in headings:
        for pr in price_areas:
            if _overlap(h["box"],pr)>0:
                failures.append("Headline overlaps price display")
                break
    # This identifies direct rectangular collisions where they would hide
    # actual headline content. Product over a workshop photograph is normal.
    return {"passed":not failures,"issues":list(dict.fromkeys(failures)),
            "warnings":list(dict.fromkeys(warnings)),
            "headline_checked":True,"price_checked":True,
            "product_checked":True}


def white_paper_warning(original_blob:bytes):
    """Flag likely unresolved white packshot backgrounds, not white tool parts."""
    from ai_photo_effects import manufacturer_cutout
    try:
        source=Image.open(BytesIO(original_blob)).convert("RGB")
        cut,isolated=manufacturer_cutout(original_blob)
    except (OSError,ValueError):
        return "Manufacturer product image could not be analysed"
    if not isolated:
        # Real garage photographs have colourful borders; those legitimately
        # retain their original pixels rather than having a fake cutout.
        corners=(source.getpixel((0,0)),source.getpixel((source.width-1,0)),
                 source.getpixel((0,source.height-1)),
                 source.getpixel((source.width-1,source.height-1)))
        if all(min(px)>215 and max(px)-min(px)<38 for px in corners):
            return "White packshot requires manual cutout review"
        return None
    rgb=cut.convert("RGB")
    lo=ImageChops.darker(ImageChops.darker(rgb.getchannel("R"),
                          rgb.getchannel("G")),rgb.getchannel("B"))
    hi=ImageChops.lighter(ImageChops.lighter(rgb.getchannel("R"),
                          rgb.getchannel("G")),rgb.getchannel("B"))
    light=lo.point(lambda v:255 if v>=245 else 0)
    neutral=ImageChops.subtract(hi,lo).point(lambda v:255 if v<=18 else 0)
    alpha=cut.getchannel("A").point(lambda v:255 if v>=240 else 0)
    white=ImageChops.multiply(ImageChops.multiply(light,neutral),alpha)
    if white.histogram()[255]/max(1,cut.width*cut.height)>.13:
        return "Large paper-white patch may remain within the tool image"
    return None


def review(rendered:bytes,tracked:QualityCapture,price:dict,
           concept:dict,source_blob:bytes|None=None):
    result=assess_text_and_geometry(tracked,price,concept)
    try:
        photo=Image.open(BytesIO(rendered))
        photo.verify()
        if photo.size!=SIZE:
            result["issues"].append("Poster dimensions are incorrect")
    except (OSError,ValueError):
        result["issues"].append("Poster image is unreadable")
    if source_blob:
        note=white_paper_warning(source_blob)
        if note:result["warnings"].append(note)
    result["issues"]=list(dict.fromkeys(result["issues"]))
    result["warnings"]=list(dict.fromkeys(result["warnings"]))
    result["passed"]=not result["issues"]
    result["status"]="passed" if result["passed"] and not result["warnings"] else (
        "review" if result["passed"] else "rejected")
    return result
