"""Laser Product Studio - high-impact, evidence-grounded AI creative art direction.

Unlike the first prototype, this module composes six radically different print
design families and uses large authentic product photography, not repeated
header/photo/footer cards. The model chooses both the visual family and the
commercial focus; the image compositor handles print-safe placement.
"""
from __future__ import annotations

import io
from math import sin, cos, pi
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from poster import font

W, H = 1200, 1500
NAVY = "#071F36"
DARK = "#0A2C4D"
DEEP = "#06192C"
BLUE = "#0472BC"
COBALT = "#0966BD"
CYAN = "#20B9F0"
PALE = "#EFF6FB"
PAPER = "#F9FBFD"
INK = "#0F293F"
SLATE = "#52718A"
LINE = "#D6E3ED"
WHITE = "#FFFFFF"
GOLD = "#F7CA55"

IMPACT_STYLES = ("cinematic", "retail", "diagonal", "industrial")
EDITORIAL_STYLES = ("editorial", "minimal", "feature")
TECHNICAL_STYLES = ("blueprint", "data")
STYLE_GROUPS = (IMPACT_STYLES, EDITORIAL_STYLES, TECHNICAL_STYLES)
VALID_STYLES = frozenset(s for family in STYLE_GROUPS for s in family)


def _w(d, txt, size, weight="bold"):
    box = d.textbbox((0, 0), str(txt), font=font(size, weight))
    return box[2]-box[0]


def _wrap(d, txt, size, width, weight):
    """Break at words, but also safely split an unusually long identifier."""
    result = []
    line = ""
    for word in str(txt or "").replace("\n", " ").split():
        candidate = (line+" "+word).strip()
        if _w(d,candidate,size,weight) <= width:
            line = candidate
            continue
        if line:
            result.append(line)
            line = ""
        part = ""
        for c in word:
            if part and _w(d,part+c,size,weight) > width:
                result.append(part)
                part=c
            else:
                part+=c
        line = part
    if line:
        result.append(line)
    return result


def _txt(d, content, rect, sizes, fill=INK, weight="bold", max_lines=3,
         align="left", overflow="ellipsis"):
    """All typography is measured, sized and bounded BEFORE rendering."""
    x,y,x2,y2 = map(int,rect)
    width=max(1,x2-x)
    height=max(1,y2-y)
    if not str(content or "").strip():
        return y
    sizes=tuple(sizes) if isinstance(sizes,(list,tuple)) else (sizes,)
    chosen=None
    for size in sizes:
        rows=_wrap(d,content,size,width,weight)
        step=int(size*1.24)
        if len(rows)<=max_lines and len(rows)*step<=height:
            chosen=(size,rows,step)
            break
    if chosen is None:
        size=sizes[-1]
        rows=_wrap(d,content,size,width,weight)
        step=int(size*1.24)
        allowed=max(1,min(max_lines,height//step))
        if len(rows)>allowed:
            rows=rows[:allowed]
            end=rows[-1].rstrip()
            while end and _w(d,end+"…",size,weight)>width:
                end=end[:-1]
            rows[-1]=end.rstrip()+"…" if overflow=="ellipsis" else end.rstrip()
        chosen=(size,rows,step)
    size,rows,step=chosen
    for line in rows:
        xx=x
        if align=="center": xx=x+(width-_w(d,line,size,weight))//2
        if align=="right": xx=x2-_w(d,line,size,weight)
        d.text((xx,y),line,font=font(size,weight),fill=fill)
        y+=step
    return y


def _brand(d, x=60, y=44, dark=False, small=False):
    color=NAVY if dark else WHITE
    size=65 if small else 87
    _txt(d,"LASER",(x,y,x+(size*5.7),y+size+30),(size,),color,"bold",1)
    _txt(d,"TOOLS",(x+3,y+size+3,x+205,y+size+35),(16 if small else 18,),
         BLUE if dark else CYAN,"bold",1)


def _label(d, content, x, y, color=CYAN):
    _txt(d,content.upper(),(x,y,W-48,y+42),(21,19,17),color,"bold",1)


def _bar(d,x,y,width,color=CYAN,height=8):
    d.rectangle((x,y,x+width,y+height),fill=color)


def _grid(d, spacing=90, fg="#204A69",left=0,top=0,right=W,bottom=H):
    for x in range(left,right+1,spacing):
        d.line((x,top,x,bottom),fill=fg,width=1)
    for y in range(top,bottom+1,spacing):
        d.line((left,y,right,y),fill=fg,width=1)


def _photocut(original):
    """Remove ONLY near-white edge-connected background; never redraw a tool.

    A jpeg with a dark or contextual background is kept as an ordinary image
    in a photographic mount. For a white manufacturer packshot we flood-fill
    from the corners, preserving disconnected chrome highlights.
    """
    src=ImageOps.exif_transpose(Image.open(io.BytesIO(original))).convert("RGBA")
    corners=((0,0),(src.width-1,0),(0,src.height-1),(src.width-1,src.height-1))
    white_corners=0
    for x,y in corners:
        r,g,b,a=src.getpixel((x,y))
        if min(r,g,b)>=233 and max(r,g,b)-min(r,g,b)<=26:
            white_corners+=1
    if white_corners<3:
        return src,False
    for p in corners:
        r,g,b,a=src.getpixel(p)
        if min(r,g,b)>=233:
            ImageDraw.floodfill(src,p,(255,255,255,0),thresh=26)
    alpha=src.getchannel("A")
    bbox=alpha.getbbox()
    if not bbox:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(original))).convert("RGBA"),False
    removed=src.width*src.height-sum(1 for v in alpha.getdata() if v>0)
    if removed/(src.width*src.height)<0.09:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(original))).convert("RGBA"),False
    return src.crop(bbox),True


def _glow(base,box,color=(6,145,222,135),blur=105):
    x,y,x2,y2=map(int,box)
    overlay=Image.new("RGBA",base.size,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    d.ellipse((x,y,x2,y2),fill=color)
    overlay=overlay.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(overlay)


def _product(base, photo, region, floating=True, shadow=True):
    """Source photograph isolated/scaled to a dominant footprint, no fake tool."""
    x,y,x2,y2=map(int,region)
    src,isolated=_photocut(photo)
    maxw,maxh=x2-x,y2-y
    src.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
    xx=x+(maxw-src.width)//2
    yy=y+(maxh-src.height)//2
    if not isolated:
        # When the manufacturer image is not on plain white, show it without
        # potentially distorting the actual scene or tool silhouette.
        d=ImageDraw.Draw(base)
        d.rounded_rectangle((x-12,y-12,x2+12,y2+12),radius=24,
                            fill=WHITE,outline=LINE,width=2)
    if shadow and isolated:
        # Shadow is generated from the original image's alpha mask, never
        # an AI-generated representation of the physical tool.
        alpha=src.getchannel("A")
        glow=Image.new("RGBA",base.size,(0,0,0,0))
        layer=Image.new("RGBA",src.size,(0,0,0,130))
        glow.paste(layer,(xx+20,yy+24),alpha)
        shadow_layer=glow.filter(ImageFilter.GaussianBlur(35))
        base.alpha_composite(shadow_layer)
    base.alpha_composite(src,(xx,yy))
    return (xx,yy,xx+src.width,yy+src.height)


def _brand_logo(base,brand):
    if not brand:return
    from brand_assets import get_brand_image
    logo=get_brand_image(brand)
    if logo is None:return
    logo=logo.copy().convert("RGBA")
    logo.thumbnail((200,72),Image.Resampling.LANCZOS)
    d=ImageDraw.Draw(base)
    d.rounded_rectangle((W-275,39,W-40,143),radius=12,fill=WHITE)
    x=W-275+(235-logo.width)//2
    y=39+(104-logo.height)//2
    base.alpha_composite(logo,(x,y))


def _bottom(d, product, color=WHITE, on_dark=True):
    c="#A9CADE" if on_dark else SLATE
    d.line((54,H-119,W-54,H-119),fill=CYAN if on_dark else LINE,width=2)
    _txt(d,"LASER TOOLS  /  "+str(product.get("part","")),
         (58,H-99,560,H-52),(23,20),color,"bold",1)
    _txt(d,"DRAFT  •  FACT CHECK BEFORE DISTRIBUTION",
         (640,H-96,W-54,H-49),(15,13),c,"bold",1,align="right")


def _short_feature(concept):
    f=concept.get("features") or []
    return str(f[0]) if f else str(concept.get("title",""))


def _cinematic(concept,photo):
    """Dark cinematic full-bleed hero, studio glow, no repetitive panel."""
    base=Image.new("RGBA",(W,H),(6,24,43,255))
    _glow(base,(230,510,1180,1320),blur=160,color=(0,151,236,170))
    _glow(base,(-150,740,550,1370),blur=135,color=(10,86,159,160))
    d=ImageDraw.Draw(base)
    d.polygon([(840,0),(1200,0),(1200,740),(1045,690)],fill="#0D4675")
    d.polygon([(0,1475),(0,1210),(1200,1000),(1200,1070)],fill="#103F66")
    _brand(d)
    _label(d,"THE PRODUCT / REIMAGINED",58,186)
    _txt(d,concept.get("headline"),(55,255,1140,495),
         (91,82,73,65,58,51,44),WHITE,"bold",3)
    _bar(d,57,520,210,CYAN,10)
    _product(base,photo,(68,585,1130,1180),shadow=True)
    d=ImageDraw.Draw(base)
    _txt(d,concept.get("subline"),(58,1240,1130,1365),
         (38,34,30,27,24),WHITE,"regular",3)
    _bottom(d,concept)
    return base


def _retail(concept,photo):
    """Retail blue/white angular campaign; huge white surface and typographic SKU."""
    base=Image.new("RGBA",(W,H),(8,112,195,255))
    d=ImageDraw.Draw(base)
    d.polygon([(0,0),(1200,0),(1200,495),(0,675)],fill="#074B91")
    d.polygon([(0,645),(1200,460),(1200,1180),(0,1375)],fill=WHITE)
    d.polygon([(0,1375),(1200,1170),(1200,1500),(0,1500)],fill=NAVY)
    d.polygon([(1000,0),(1200,0),(1200,470),(1135,480)],fill=CYAN)
    _brand(d)
    _label(d,"TOOL SPOTLIGHT",58,190,color="#9BE6FF")
    _txt(d,concept.get("headline"),(58,263,1135,490),
         (87,78,70,63,56,49,43),WHITE,"bold",3)
    _bar(d,65,680,380,BLUE,12)
    _txt(d,"PART NO. "+str(concept.get("part","")),(64,720,1090,820),
         (62,55,50),NAVY,"bold",1)
    _product(base,photo,(90,820,1110,1230),shadow=True)
    d=ImageDraw.Draw(base)
    _txt(d,concept.get("subline"),(65,1295,1130,1392),
         (36,31,28,24),WHITE,"regular",2)
    _bottom(d,concept)
    return base


def _diagonal(concept,photo):
    """High-energy asymmetric diagonal with floating original product photo."""
    base=Image.new("RGBA",(W,H),(5,26,45,255))
    d=ImageDraw.Draw(base)
    d.polygon([(450,0),(1200,0),(1200,1400),(0,1400)],fill="#026FB7")
    d.polygon([(750,0),(1200,0),(1200,1400),(510,1400)],fill="#0D81C5")
    for shift in (0,130,260,390):
        d.line((200+shift,1350,900+shift,220),fill="#4DCAF6",width=4)
    d.rectangle((0,0,23,H),fill=CYAN)
    _brand(d)
    _label(d,"PROFESSIONAL WORKSHOP EQUIPMENT",61,194)
    _txt(d,concept.get("headline"),(58,275,1100,510),
         (85,76,68,61,54,47),WHITE,"bold",3)
    _glow(base,(160,650,1130,1250),blur=92,color=(2,28,55,145))
    _product(base,photo,(125,620,1130,1235),shadow=True)
    d=ImageDraw.Draw(base)
    d.rectangle((0,1280,W,H),fill=NAVY)
    _txt(d,concept.get("subline"),(63,1300,1130,1395),
         (33,29,26,23),WHITE,"regular",2)
    _bottom(d,concept)
    return base


def _industrial(concept,photo):
    """Hard-edged near-black industrial equipment campaign."""
    base=Image.new("RGBA",(W,H),(19,28,36,255))
    d=ImageDraw.Draw(base)
    _grid(d,130,"#263643")
    d.rectangle((0,0,W,22),fill=CYAN)
    d.rectangle((0,1410,W,H),fill=BLUE)
    d.polygon([(0,970),(W,690),(W,790),(0,1080)],fill="#0C4D77")
    d.polygon([(0,1100),(W,805),(W,875),(0,1170)],fill="#125F8D")
    _brand(d)
    _label(d,"INDUSTRIAL / LASER TOOLS",60,192)
    _txt(d,concept.get("headline"),(58,256,1110,570),
         (98,88,78,69,61,54,47),WHITE,"bold",4)
    _product(base,photo,(125,635,1110,1240),shadow=True)
    d=ImageDraw.Draw(base)
    d.rectangle((0,1270,W,H),fill=NAVY)
    _txt(d,concept.get("subline"),(61,1287,1140,1391),
         (34,30,27,24),WHITE,"regular",2)
    _bottom(d,concept)
    return base


def _editorial(concept,photo):
    """Premium editorial: bright paper, oversized part number, large right hero."""
    base=Image.new("RGBA",(W,H),(250,252,254,255))
    d=ImageDraw.Draw(base)
    d.polygon([(0,0),(W,0),(W,435),(0,550)],fill="#E8F3FA")
    d.rectangle((0,0,W,14),fill=BLUE)
    _brand(d,dark=True)
    _label(d,"LASER / PRODUCT EDITION",58,181,color=BLUE)
    # Airy editorial hierarchy, almost no blocks.
    _txt(d,concept.get("headline"),(58,270,1115,560),
         (93,83,74,66,59,52,46),NAVY,"bold",4)
    _bar(d,60,595,350,CYAN,11)
    _txt(d,concept.get("subline"),(59,633,1100,760),
         (37,33,29,26),SLATE,"regular",3)
    _txt(d,str(concept.get("part","")),(48,800,1148,1075),
         (270,245,220,195), "#D4E7F4","bold",1)
    _product(base,photo,(80,870,1100,1340),shadow=True)
    d=ImageDraw.Draw(base)
    _bottom(d,concept,color=NAVY,on_dark=False)
    return base


def _minimal(concept,photo):
    """Design-studio minimal: towering vertical strip, negative space and hero."""
    base=Image.new("RGBA",(W,H),(255,255,255,255))
    d=ImageDraw.Draw(base)
    d.rectangle((0,0,158,H),fill=NAVY)
    d.rectangle((158,0,177,H),fill=CYAN)
    d.rectangle((230,0,W,14),fill=BLUE)
    _txt(d,"LASER",(230,42,860,143),(88,79),NAVY,"bold",1)
    _label(d,"A NEW LOOK AT THE WORKSHOP",230,178,color=BLUE)
    _txt(d,concept.get("headline"),(226,265,1120,560),
         (89,78,69,61,54,47,41),NAVY,"bold",4)
    _txt(d,concept.get("subline"),(231,584,1110,705),
         (34,30,26,23),SLATE,"regular",3)
    _txt(d,str(concept.get("part","")),(234,760,1120,900),
         (115,104,90), "#D2E4F0","bold",1)
    _product(base,photo,(225,815,1130,1335),shadow=True)
    d=ImageDraw.Draw(base)
    _txt(d,"PART "+str(concept.get("part","")),(20,1200,153,1412),
         (33,28,24),WHITE,"bold",3,align="center")
    _bottom(d,concept,color=NAVY,on_dark=False)
    return base


def _feature(concept,photo):
    """Modern trade catalogue page, huge photo, two highlighted evidence panels."""
    base=Image.new("RGBA",(W,H),(246,250,254,255))
    d=ImageDraw.Draw(base)
    d.rectangle((0,0,W,198),fill=NAVY)
    _brand(d)
    _label(d,"BUILT AROUND THE JOB",62,239,color=BLUE)
    _txt(d,concept.get("headline"),(61,300,1130,532),
         (85,77,69,61,54,47),INK,"bold",3)
    d.line((61,549,1126,549),fill=LINE,width=3)
    _product(base,photo,(83,580,1115,1125),shadow=True)
    d=ImageDraw.Draw(base)
    d.rectangle((0,1160,W,H),fill=BLUE)
    _txt(d,concept.get("subline"),(63,1190,1136,1338),
         (38,34,30,26),WHITE,"regular",3)
    _bottom(d,concept)
    return base


def _blueprint(concept,photo):
    """Architectural technical blueprint: grid and real photo, verified text."""
    base=Image.new("RGBA",(W,H),(6,36,66,255))
    d=ImageDraw.Draw(base)
    _grid(d,60,"#17446A")
    d.rectangle((0,0,W,16),fill=CYAN)
    _brand(d)
    _label(d,"TECHNICAL / PRODUCT RECORD",60,202)
    _txt(d,concept.get("headline"),(58,270,1100,492),
         (78,70,62,55,49,42),WHITE,"bold",3)
    d.rectangle((62,515,1136,535),fill=CYAN)
    # Product mount deliberately contrasts the dark grid with crisp authentic photo.
    _product(base,photo,(124,575,1075,1110),shadow=False)
    d=ImageDraw.Draw(base)
    d.line((60,1140,1140,1140),fill=CYAN,width=4)
    _txt(d,"APPLICATION / SPECIFICATION",(61,1165,1130,1200),
         (22,19),CYAN,"bold",1)
    _txt(d,_short_feature(concept),(61,1215,1135,1360),
         (34,30,27,24,21),WHITE,"regular",4)
    _bottom(d,concept)
    return base


def _data(concept,photo):
    """White technical fact-led sheet, huge SKU with two confirmed highlights."""
    base=Image.new("RGBA",(W,H),(255,255,255,255))
    d=ImageDraw.Draw(base)
    d.rectangle((0,0,W,198),fill=BLUE)
    _brand(d)
    _label(d,"SPECIFICATION / PRODUCT FOCUS",60,244,color=BLUE)
    _txt(d,str(concept.get("part","")),(51,292,1120,540),
         (230,210,180),NAVY,"bold",1)
    d.line((60,550,1135,550),fill=CYAN,width=9)
    _product(base,photo,(75,586,1130,1070),shadow=True)
    d=ImageDraw.Draw(base)
    d.rectangle((0,1110,W,H),fill=PALE)
    _txt(d,concept.get("headline"),(56,1125,1140,1252),
         (54,49,44,38,34),INK,"bold",3)
    _txt(d,_short_feature(concept),(59,1265,1135,1380),
         (31,28,25,22),SLATE,"regular",3)
    _bottom(d,concept,color=NAVY,on_dark=False)
    return base


RENDERERS = {
    "cinematic":_cinematic, "retail":_retail, "diagonal":_diagonal, "industrial":_industrial,
    "editorial":_editorial, "minimal":_minimal, "feature":_feature,
    "blueprint":_blueprint, "data":_data,
}


def render_concept(concept, image_bytes, distributor=None):
    """Produce a printable 1200x1500 RGB PNG using only real product pixels."""
    style=concept.get("visual_style") or concept.get("layout") or "cinematic"
    if style not in RENDERERS:
        style="cinematic"
    base=RENDERERS[style](concept,image_bytes)
    _brand_logo(base,distributor)
    output=io.BytesIO()
    base.convert("RGB").save(output,"PNG",optimize=True)
    return output.getvalue()
