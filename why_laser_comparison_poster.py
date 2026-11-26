"""V76: reference-inspired visual, evidence-led Laser-versus-competitor pages.

A4 landscape; blue Laser vs red competitor cards, genuine manufacturer photo
where available, a comparable-specification table, and a yellow conclusion.
One page per verified competitor. No fabricated RRP, method or superiority.
"""
from __future__ import annotations

import html
import io
import re
from xml.sax.saxutils import escape

from PIL import Image as PILImage
import requests
from competitor_finder import safe_image_url
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

PAGESIZE=landscape(A4)
PW,PH=PAGESIZE
BLUE=colors.HexColor("#075DA5")
DEEP=colors.HexColor("#052D51")
RED=colors.HexColor("#C81724")
PAPER=colors.HexColor("#F5F8FB")
INK=colors.HexColor("#172839")
MUTED=colors.HexColor("#52677C")
BORDER=colors.HexColor("#C6D6E5")
YELLOW=colors.HexColor("#FFC928")
PALE=colors.HexColor("#FFF5D9")


def clean(text,limit=280):
    return " ".join(str(text or "").replace("\x00","").split())[:limit]


def draw_text(c,text,x,y,width,height,*,size=10,bold=False,
              colour=INK,min_size=6.5,leading=None):
    """Fit complete source text inside fixed rectangles: never crop facts."""
    value=escape(clean(text,400))
    if not value:
        return 0
    font="Helvetica-Bold" if bold else "Helvetica"
    for candidate in (size,size-0.5,size-1,size-1.5,size-2,size-2.5,size-3,size-4):
        if candidate<min_size:continue
        style=ParagraphStyle(
            "fit",fontName=font,fontSize=candidate,
            leading=leading or candidate*1.19,textColor=colour,
            spaceAfter=0,spaceBefore=0,allowWidows=0,allowOrphans=0,
            splitLongWords=1)
        para=Paragraph(value,style)
        _,actual_h=para.wrap(width,height)
        if actual_h<=height-1:
            para.drawOn(c,x,y+height-actual_h)
            return actual_h
    # Shrink further for unusually long exact manufacturer descriptions.
    style=ParagraphStyle("fallback",fontName=font,fontSize=min_size,
                         leading=min_size*1.15,textColor=colour)
    para=Paragraph(value,style)
    _,actual_h=para.wrap(width,height)
    if actual_h<=height:
        para.drawOn(c,x,y+height-actual_h)
        return actual_h
    # No truncated claims. Replace only the rendering with a clear cue to
    # the clickable official source, while keeping full facts in the JSON.
    nofit=Paragraph("Full specification: see linked manufacturer source",
                    ParagraphStyle("nofit",fontName="Helvetica",fontSize=8,
                                   leading=9.5,textColor=MUTED))
    nofit.wrap(width,height)
    nofit.drawOn(c,x,y+height-12)
    return 12


def rounded(c,x,y,w,h,fill,border=None,r=9):
    c.setFillColor(fill)
    c.setStrokeColor(border or fill)
    c.setLineWidth(0.8)
    c.roundRect(x,y,w,h,r,stroke=bool(border),fill=1)


def _link(c,url,rect):
    if isinstance(url,str) and url.startswith("https://"):
        c.linkURL(url,rect,relative=0,thickness=0)


def image_or_placeholder(c,data,x,y,w,h,caption):
    rounded(c,x,y,w,h,colors.white,BORDER,6)
    if isinstance(data,(bytes,bytearray)) and data:
        try:
            with PILImage.open(io.BytesIO(data)) as source:
                source.load()
                photo=source.convert("RGB")
                iw,ih=photo.size
                if max(iw,ih)>800:
                    photo.thumbnail((800,800),PILImage.Resampling.LANCZOS)
                    iw,ih=photo.size
                ratio=min((w-12)/iw,(h-12)/ih)
                dw,dh=iw*ratio,ih*ratio
                c.drawImage(ImageReader(photo),x+(w-dw)/2,y+(h-dh)/2,
                            dw,dh,preserveAspectRatio=True,mask="auto")
                return True
        except (OSError,ValueError):
            pass
    c.setFillColor(colors.HexColor("#EAF1F7"))
    c.roundRect(x+9,y+15,w-18,h-30,6,stroke=0,fill=1)
    draw_text(c,caption,x+13,y+h/2-20,w-26,44,
              size=10,bold=True,colour=MUTED)
    return False


def _genuine_rival_photo(rival):
    """Optionally embed the exact product-page image, never generated art.

    This is deliberately small and fail-soft on Render Free. The URL must
    have passed the competitor source allowlist and match this product page.
    No redirects to untrusted hosts, no arbitrary user URL, and no more than
    800 KiB of downloaded content. SVGs and huge decoded photographs are
    rejected instead of filling 512 MiB RAM.
    """
    url=rival.get("image_url")
    source=rival.get("url")
    if not isinstance(url,str) or safe_image_url(url,source)!=url:
        return None
    try:
        with requests.get(url,timeout=(2.0,3.0),stream=True,
                          allow_redirects=False,
                          headers={"Accept":"image/jpeg,image/png,image/webp"}) as resp:
            if resp.status_code!=200:
                return None
            mime=resp.headers.get("content-type","").split(";",1)[0].lower()
            if mime not in ("image/jpeg","image/png","image/webp"):
                return None
            if int(resp.headers.get("content-length","0") or 0)>800_000:
                return None
            chunks=[]
            total=0
            for chunk in resp.iter_content(32768):
                total+=len(chunk)
                if total>800_000:
                    return None
                chunks.append(chunk)
        with PILImage.open(io.BytesIO(b"".join(chunks))) as image:
            w,h=image.size
            if w*h>6_000_000 or min(w,h)<100:
                return None
            if image.format in ("JPEG","MPO"):
                image.draft("RGB",(640,640))
            image.thumbnail((640,460),PILImage.Resampling.LANCZOS)
            original=image.convert("RGBA")
            # White paper is part of the output, not part of product pixels.
            canvas=PILImage.new("RGB",original.size,"white")
            canvas.paste(original,mask=original.getchannel("A"))
            dst=io.BytesIO()
            canvas.save(dst,format="JPEG",quality=84,optimize=True)
            return dst.getvalue() if dst.tell()<220_000 else None
    except (requests.RequestException,OSError,ValueError,TypeError):
        return None


def _bullet(c,value,x,y,width,colour,maxheight=34):
    c.setFillColor(colour)
    c.circle(x+4,y+maxheight-8,2.6,stroke=0,fill=1)
    draw_text(c,value,x+13,y,width-13,maxheight,
              size=9,bold=False,min_size=7.2)


def _facts_for_competitor(sheet,rival):
    """Published evidence, not imagined rival capabilities."""
    out=[clean(rival.get("comparison_relationship") or
               "Similar category; application compatibility not confirmed",155)]
    for row in (rival.get("published_differences") or [])[:2]:
        out.append(clean(row.get("attribute"),55)+": "+clean(row.get("competitor"),90))
    for row in (rival.get("shared_published_specs") or [])[:2]:
        out.append(clean(row.get("attribute"),55)+": "+clean(row.get("competitor"),90))
    if not rival.get("published_differences") and not rival.get("shared_published_specs"):
        out.append("No directly comparable published technical detail verified")
    if rival.get("source_checked_on"):
        out.append("Manufacturer details checked "+clean(rival["source_checked_on"],30))
    return out[:5]


def _features(sheet):
    facts=[clean(v.get("text"),160) for v in sheet.get("strengths") or []
           if isinstance(v,dict) and v.get("text")]
    return facts[:5] or ["No verified feature bullets available in official Laser listing"]


def _comparison_rows(rival):
    rows=[]
    keys=set()
    for kind in ("published_differences","shared_published_specs"):
        for spec in rival.get(kind) or []:
            key=clean(spec.get("attribute"),75)
            if not key or key.casefold() in keys:
                continue
            keys.add(key.casefold())
            rows.append({
                "name":key,
                "laser":clean(spec.get("laser"),110),
                "rival":clean(spec.get("competitor"),110),
                "difference":kind=="published_differences",
            })
    if not rows:
        rows=[{"name":"Published technical comparison",
               "laser":"Official features listed above",
               "rival":"No matching specification verified",
               "difference":False}]
    return [{
        "name":"Manufacturer RRP / list price",
        "laser":rival.get("_laser_rrp") or "Not verified",
        "rival":rival.get("manufacturer_rrp") or "Not verified",
        "difference":False,
    }, *rows[:3]]


def _takeaway(sheet,rival):
    if rival.get("reasons_to_choose"):
        return "Why choose Laser? "+" ".join(rival["reasons_to_choose"])
    changed=rival.get("published_differences") or []
    shared=rival.get("shared_published_specs") or []
    strengths=_features(sheet)
    if changed:
        spec=changed[0]
        return ("Key takeaway: published "+clean(spec.get("attribute"),50)+
                " differs (Laser "+clean(spec.get("laser"),65)+
                "; "+clean(rival.get("brand"),40)+" "+
                clean(spec.get("competitor"),65)+
                "). This alone does not prove greater performance or value.")
    if shared:
        spec=shared[0]
        return ("Key takeaway: both published sources list "+
                clean(spec.get("attribute"),50)+" as "+
                clean(spec.get("laser"),65)+
                ". Laser's separately verified product features are shown above; "
                "no performance superiority is established.")
    if strengths:
        return ("Key takeaway: Laser officially lists "+
                strengths[0]+
                ". A like-for-like technical advantage over this competitor "
                "has not yet been verified.")
    return ("Key takeaway: both are research leads; independently verify "
            "fitment and technical performance before any comparative claim.")


def _card(c,x,y,w,h,name,title,colour,bullets,photo,source,missing_caption):
    rounded(c,x,y,w,h,colors.white,colour,9)
    c.setFillColor(colour)
    c.roundRect(x,y+h-34,w,34,8,stroke=0,fill=1)
    c.rect(x,y+h-34,w,15,stroke=0,fill=1)
    draw_text(c,name,x+11,y+h-29,w-22,25,size=16,bold=True,
              colour=colors.white,min_size=10)
    photo_x,photo_y,photo_w,photo_h=x+10,y+42,161,137
    image_or_placeholder(c,photo,photo_x,photo_y,photo_w,photo_h,missing_caption)
    start=x+184
    draw_text(c,title,start,y+h-78,w-195,34,
              size=9.5,bold=True,min_size=7.2)
    yy=y+h-116
    for value in bullets[:4]:
        _bullet(c,value,start,yy-25,w-195,colour,maxheight=29)
        yy-=34
    c.setStrokeColor(BORDER)
    c.line(x+11,y+35,x+w-11,y+35)
    c.setFillColor(colour)
    c.setFont("Helvetica-Bold",8.7)
    c.drawString(x+13,y+18,"VIEW MANUFACTURER SOURCE")
    _link(c,source,(x+9,y+5,x+w-7,y+36))


def _table(c,rival):
    x,y,w,h=19,56,PW-38,125
    rows=_comparison_rows(rival)
    c.setLineWidth(.7)
    c.setStrokeColor(BORDER)
    c.setFillColor(colors.HexColor("#EDF1F6"))
    c.roundRect(x,y,w,h,6,stroke=1,fill=1)
    labelw=193
    rest=(w-labelw)/2
    header=26
    c.setFillColor(DEEP)
    c.rect(x+labelw,y+h-header,rest,header,fill=1,stroke=0)
    c.setFillColor(RED)
    c.rect(x+labelw+rest,y+h-header,rest,header,fill=1,stroke=0)
    draw_text(c,"COMPARISON",x+12,y+h-21,labelw-20,18,
              size=10,bold=True)
    draw_text(c,"LASER TOOLS "+clean(rival.get("_laser_part"),14),
              x+labelw+10,y+h-22,rest-20,19,
              size=10.5,bold=True,colour=colors.white)
    draw_text(c,clean(rival.get("brand"),45)+" "+clean(rival.get("part_number"),40),
              x+labelw+rest+10,y+h-22,rest-20,19,
              size=10.5,bold=True,colour=colors.white)
    c.setStrokeColor(colors.HexColor("#BCCAD7"))
    c.line(x+labelw,y,x+labelw,y+h)
    c.line(x+labelw+rest,y,x+labelw+rest,y+h)
    row_height=(h-header)/len(rows)
    for i,r in enumerate(rows):
        by=y+h-header-(i+1)*row_height
        if i%2==0:
            c.setFillColor(colors.white)
            c.rect(x+1,by,w-2,row_height,stroke=0,fill=1)
        if r["difference"]:
            c.setFillColor(colors.HexColor("#DFF0FF"))
            c.rect(x+1,by,5,row_height,stroke=0,fill=1)
        draw_text(c,r["name"],x+11,by+3,labelw-20,row_height-6,
                  size=10,bold=True,min_size=7.5)
        draw_text(c,r["laser"],x+labelw+10,by+3,rest-20,row_height-6,
                  size=9.4,min_size=7)
        draw_text(c,r["rival"],x+labelw+rest+10,by+3,rest-20,row_height-6,
                  size=9.4,min_size=7)
        if i<len(rows)-1:
            c.setStrokeColor(BORDER)
            c.line(x,by,x+w,by)


def render_visual_comparison_pdf(sheet,photo_bytes=None):
    """One A4 landscape visual comparison per source-verified competitor."""
    if not sheet.get("review_required") or sheet.get("public_claim_approved") is not False:
        raise ValueError("Why Choose Laser must be a review-labelled draft")
    rivals=sheet.get("competitors") or [{
        "brand":"NO VERIFIED COMPETITOR",
        "title":"No accessible competitor product pages have been verified",
        "part_number":"",
        "url":None,
        "comparison_relationship":"Do not claim superiority on this evidence",
        "published_differences":[],"shared_published_specs":[],
    }]
    output=io.BytesIO()
    c=canvas.Canvas(output,pagesize=PAGESIZE,
                    pageCompression=1)
    c.setTitle("Why Choose Laser? "+clean(sheet.get("part"),18)+" — visual comparison")
    c.setAuthor("Laser Product Studio — Internal review draft")
    laser_url=sheet.get("official_source")
    # Fetch at most two exact manufacturer/retailer product photographs.
    # Avoid turning a 4-page comparison into four extra network stalls.
    rival_photos={}
    for candidate in rivals[:2]:
        if candidate.get("image_url"):
            rival_photos[candidate.get("url")]=_genuine_rival_photo(candidate)
    for idx,rival in enumerate(rivals[:4],1):
        c.setFillColor(PAPER)
        c.rect(0,0,PW,PH,stroke=0,fill=1)
        name=("Laser Tools "+clean(sheet.get("part"),16)+
              " vs "+clean(rival.get("brand"),50)+" "+
              clean(rival.get("part_number"),40))
        draw_text(c,name,20,PH-54,PW-40,40,size=26,bold=True,min_size=16)
        draw_text(c,clean(sheet.get("title"),170)+" | evidence-based product comparison",
                  20,PH-80,PW-40,23,size=13,bold=True,colour=MUTED)
        draw_text(c,"INTERNAL DRAFT · MANUFACTURER SOURCE CHECK REQUIRED",
                  20,PH-96,530,12,size=8,bold=True,colour=RED)
        draw_text(c,"WHY CHOOSE LASER?",PW-182,PH-96,161,12,
                  size=9,bold=True,colour=BLUE)
        panel_y=190
        gap=10
        panel_w=(PW-48)/2
        left_x=19
        right_x=left_x+panel_w+gap
        _card(c,left_x,panel_y,panel_w,223,
              "Laser Tools "+clean(sheet.get("part"),18),
              clean(sheet.get("title"),170),BLUE,
              _features(sheet),photo_bytes,laser_url,
              "OFFICIAL PRODUCT PHOTO UNAVAILABLE")
        _card(c,right_x,panel_y,panel_w,223,
              clean(rival.get("brand"),60)+" "+clean(rival.get("part_number"),50),
              clean(rival.get("title"),170),RED,
              _facts_for_competitor(sheet,rival),
              # Competitor photos are only permitted if bytes are independently
              # source-verified; absent inputs are never AI-created or copied
              # from another similar-looking tool.
              rival_photos.get(rival.get("url")),
              rival.get("url"),
              "COMPETITOR PHOTO NOT VERIFIED")
        with_name={**rival,"_laser_part":sheet.get("part"),"_laser_rrp":sheet.get("manufacturer_rrp")}
        _table(c,with_name)
        if sheet.get("manufacturer_rrp"):
            _link(c,sheet.get("rrp_source"),(212,132,515,153))
        if rival.get("manufacturer_rrp"):
            _link(c,rival.get("rrp_source"),(516,132,PW-19,153))
        rounded(c,19,422,PW-38,72,PALE,YELLOW,8)
        c.setFillColor(YELLOW)
        c.circle(46,458,18,fill=1,stroke=0)
        c.setStrokeColor(DEEP)
        c.setLineWidth(3)
        c.line(37,458,43,452)
        c.line(43,452,55,467)
        draw_text(c,_takeaway(sheet,rival),
                  76,430,PW-110,56,size=12,bold=True,min_size=9.2)
        draw_text(c,"Manufacturer list pricing and product evidence · "+
                  clean(sheet.get("research_checked_at_utc"),40),
                  19,34,PW-38,12,size=8,colour=MUTED)
        draw_text(c,"DRAFT — NOT APPROVED FOR CUSTOMER DISTRIBUTION",
                  19,17,550,13,size=9,bold=True,colour=RED)
        c.setFillColor(MUTED)
        c.setFont("Helvetica",8)
        c.drawRightString(PW-19,20,str(idx)+" / "+str(min(len(rivals),4)))
        _link(c,laser_url,(left_x, panel_y,left_x+panel_w,panel_y+223))
        _link(c,rival.get("url"),(right_x,panel_y,right_x+panel_w,panel_y+223))
        c.showPage()
    c.save()
    return output.getvalue()
