"""Three genuinely different print compositions for optional Gemini creative concepts.

The model supplies creative copy and evidence selections. The render engine supplies
deliberately different photographic / editorial / technical art direction, rather
than placing all concepts in the same header-photo-footer skeleton. Images are
unaltered authentic manufacturer photographs on neutral mounting surfaces.
"""
from __future__ import annotations
import io
from PIL import Image, ImageDraw, ImageOps
from poster import font

W, H = 1200, 1500
NAVY = "#082B4C"
MID = "#0C4E7F"
BLUE = "#0066AF"
CYAN = "#20B7EA"
INK = "#12334F"
GREY = "#53708A"
PALE = "#EDF4FA"
WHITE = "#FFFFFF"
RULE = "#D9E6EF"


def _width(draw, value, size, kind="regular"):
    return draw.textbbox((0, 0), value, font=font(size, kind))[2]


def _wrap(draw, words, width, size, kind):
    """Full word wrapping; individual long words are split without spilling."""
    output, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if _width(draw, candidate, size, kind) <= width:
            current = candidate
            continue
        if current:
            output.append(current)
            current = ""
        segment = ""
        for ch in word:
            if segment and _width(draw, segment + ch, size, kind) > width:
                output.append(segment)
                segment = ch
            else:
                segment += ch
        current = segment
    if current:
        output.append(current)
    return output


def _text(draw, text, rect, sizes, color=INK, kind="bold", max_lines=4, align="left"):
    """Fit text to a fixed bounded region; never paint past its box."""
    x, y, x2, y2 = rect
    width, height = int(x2-x), int(y2-y)
    words = str(text or "").replace("\n", " ").split()
    if not words:
        return y
    sizes = list(sizes)
    if not sizes:
        sizes = [28]
    chosen = None
    for size in sizes:
        output = _wrap(draw, words, width, size, kind)
        step = int(size * 1.23)
        if len(output) <= max_lines and len(output)*step <= height:
            chosen = (size, output, step)
            break
    if chosen is None:
        size = sizes[-1]
        output = _wrap(draw, words, width, size, kind)
        step = int(size*1.23)
        limit = max(1, min(max_lines, height//step))
        output = output[:limit]
        if output:
            # Ellipsis on genuine overflow. Never silently clip at image edge.
            if len(_wrap(draw, words, width, size, kind)) > limit:
                end = output[-1].rstrip()
                while end and _width(draw, end+"…", size, kind)>width:
                    end=end[:-1]
                output[-1]=end.rstrip()+"…"
        chosen = (size, output, step)
    size, output, step = chosen
    for line in output:
        xx = x
        if align == "center":
            xx = x + (width-_width(draw, line, size, kind))//2
        elif align == "right":
            xx = x2-_width(draw,line,size,kind)
        draw.text((int(xx),int(y)),line,font=font(size,kind),fill=color)
        y+=step
    return y


def _mark(draw, x, y, dark=False):
    primary = NAVY if dark else WHITE
    draw.text((x,y),"LASER",font=font(82,"bold"),fill=primary)
    draw.text((x+2,y+86),"TOOLS  /  PROFESSIONAL WORKSHOP EQUIPMENT",font=font(17,"bold"),
              fill=BLUE if dark else CYAN)


def _photo(canvas, photo, rect, border=True):
    """Authentic, unaltered manufacturer packshot placed inside a white mount."""
    x0,y0,x1,y1=map(int,rect)
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((x0,y0,x1,y1),radius=20,fill=WHITE,
                        outline=RULE if border else WHITE,width=3)
    image=ImageOps.exif_transpose(Image.open(io.BytesIO(photo)))
    bbox=(x1-x0-56,y1-y0-56)
    if image.mode in ("RGBA","LA") or "transparency" in image.info:
        image=image.convert("RGBA")
        image.thumbnail(bbox,Image.Resampling.LANCZOS)
        pos=(x0+(x1-x0-image.width)//2,y0+(y1-y0-image.height)//2)
        canvas.paste(image,pos,image)
    else:
        image=ImageOps.contain(image.convert("RGB"),bbox,Image.Resampling.LANCZOS)
        pos=(x0+(x1-x0-image.width)//2,y0+(y1-y0-image.height)//2)
        canvas.paste(image,pos)


def _subtext(draw, text, rect, color=GREY, sizes=(29,26,23,20), max_lines=3):
    return _text(draw,text,rect,sizes,color,"regular",max_lines)


def _badge(draw, text, rect, fill, text_color=WHITE):
    draw.rounded_rectangle(rect,radius=10,fill=fill)
    x,y,x2,y2=rect
    _text(draw,text,(x+14,y+9,x2-12,y2-6),(22,20,18),text_color,"bold",2)


def _footer(draw, left=60, dark=True):
    line_color="#476985" if dark else RULE
    color="#B9D1E3" if dark else GREY
    draw.line((left,H-95,W-left,H-95),fill=line_color,width=2)
    _text(draw,"DRAFT ARTWORK  •  VERIFY PRODUCT CLAIMS BEFORE PUBLICATION",
          (left,H-76,W-left,H-35),(16,15,14),color,"bold",1)


def _distributor(canvas, brand):
    if not brand:
        return
    from brand_assets import get_brand_image
    logo=get_brand_image(brand)
    if logo is None:
        return
    logo=logo.copy().convert("RGBA")
    logo.thumbnail((188,75),Image.Resampling.LANCZOS)
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((W-270,45,W-45,150),radius=12,fill=WHITE)
    x=(W-270)+(225-logo.width)//2
    y=45+(105-logo.height)//2
    canvas.paste(logo,(x,y),logo)


def _impact(concept,photo):
    """Campaign-style hero, dark cinematic framing, large central packshot."""
    canvas=Image.new("RGB",(W,H),NAVY)
    d=ImageDraw.Draw(canvas)
    d.polygon([(0,0),(W,0),(W,450),(960,555),(0,475)],fill="#0F456E")
    d.rectangle((0,0,16,H),fill=CYAN)
    d.polygon([(955,0),(W,0),(W,345),(1010,380)],fill="#1269A6")
    _mark(d,65,48)
    _text(d,"01 / PRODUCT SPOTLIGHT",(68,200,790,245),(20,18),CYAN,"bold",1)
    _text(d,concept.get("headline"),(65,252,1135,440),
          (78,71,64,58,51,46,40,36),WHITE,"bold",3)
    # Strong independent product image, not a shared thumbnail panel.
    d.rounded_rectangle((58,480,1142,1145),radius=28,fill="#C6E1F3")
    _photo(canvas,photo,(72,496,1128,1130),False)
    d=ImageDraw.Draw(canvas)
    d.rectangle((72,1150,1128,1160),fill=CYAN)
    _text(d,"LASER TOOLS  /  "+str(concept.get("part","")),
          (70,1190,1130,1245),(31,28),CYAN,"bold",1)
    _subtext(d,concept.get("subline"),(70,1250,1130,1370),
             color=WHITE,sizes=(30,27,24,21),max_lines=3)
    _footer(d,70)
    return canvas


def _editorial(concept,photo):
    """Magazine advert: tall blue left text column, edge-led right photograph."""
    canvas=Image.new("RGB",(W,H),"#F8FBFD")
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,490,1500),fill=NAVY)
    d.rectangle((490,0,506,1500),fill=CYAN)
    d.rectangle((506,0,W,18),fill=BLUE)
    _mark(d,54,48)
    _text(d,"02 / WORKSHOP APPLICATION",(54,215,465,270),
          (19,17,15),CYAN,"bold",2)
    _text(d,concept.get("headline"),(53,302,464,680),
          (66,59,53,48,43,38,34,29,25),WHITE,"bold",7)
    d.line((55,720,426,720),fill=CYAN,width=6)
    _subtext(d,concept.get("subline"),(55,761,454,1055),
             color="#E3F1FB",sizes=(33,29,25,22,19),max_lines=8)
    d.rectangle((55,1190,426,1296),fill="#13659C")
    _text(d,"PART NUMBER",(74,1209,405,1244),(19,17),WHITE,"bold",1)
    _text(d,str(concept.get("part","")),(72,1240,409,1300),(51,46),WHITE,"bold",1)
    _text(d,"GENUINE LASER TOOLS PRODUCT",(530,65,1150,122),(25,22,20),BLUE,"bold",1)
    d.line((530,135,1140,135),fill=RULE,width=3)
    _photo(canvas,photo,(530,180,1150,1025),True)
    d=ImageDraw.Draw(canvas)
    d.rectangle((530,1055,1150,1065),fill=CYAN)
    _text(d,concept.get("title"),(530,1090,1150,1235),
          (43,37,32,28,24),INK,"bold",4)
    _subtext(d,concept.get("angle"),(530,1270,1145,1400),
             color=GREY,sizes=(25,22,20,18),max_lines=4)
    _footer(d,530,False)
    return canvas


def _technical(concept,photo):
    """Catalogue-style information graphic with large SKU and two evidence cards."""
    canvas=Image.new("RGB",(W,H),WHITE)
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,W,185),fill=NAVY)
    d.rectangle((0,185,W,199),fill=CYAN)
    _mark(d,62,42)
    _text(d,"03 / PRODUCT DETAILS",(61,233,800,272),(21,19),BLUE,"bold",1)
    _text(d,"PART NUMBER",(62,325,440,362),(20,19),GREY,"bold",1)
    _text(d,str(concept.get("part","")),(50,365,480,555),
          (124,110,99,88,78,70),NAVY,"bold",1)
    d.rectangle((62,577,455,592),fill=CYAN)
    _text(d,concept.get("headline"),(61,626,463,934),
          (53,48,42,37,33,29,25),INK,"bold",6)
    _photo(canvas,photo,(499,279,1148,919),True)
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,975,W,H),fill=PALE)
    _text(d,"VERIFIED PRODUCT HIGHLIGHTS",(61,1006,1150,1052),
          (25,22),NAVY,"bold",1)
    features=concept.get("features",[]) or []
    if not features:
        features=[str(concept.get("title","Laser Tools equipment"))]
    feature_rects=[(61,1075,570,1350),(590,1075,1140,1350)]
    for i,rect in enumerate(feature_rects):
        x,y,x2,y2=rect
        d.rounded_rectangle(rect,radius=18,fill=WHITE,outline=RULE,width=2)
        _text(d,str(i+1).zfill(2),(x+25,y+22,x+120,y+87),
              (45,40),BLUE,"bold",1)
        value=features[i%len(features)]
        _subtext(d,value,(x+25,y+95,x2-25,y2-19),
                 color=INK,sizes=(31,28,25,22,20,18),max_lines=7)
    _footer(d,61,False)
    return canvas


def render_concept(concept,image_bytes,distributor=None):
    """Render one AI-directed poster and return a full-size PNG for review."""
    layout=concept.get("layout","spotlight")
    renderer={"spotlight":_impact,"split":_editorial,"technical":_technical}.get(layout,_impact)
    canvas=renderer(concept,image_bytes)
    _distributor(canvas,distributor)
    output=io.BytesIO()
    canvas.save(output,"PNG",optimize=True)
    return output.getvalue()
