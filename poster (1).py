"""Deterministic Laser-style marketing art from an authentic product photograph.
No AI-generated product images, schematics or technical measurements.
"""
from __future__ import annotations
import io, textwrap
from PIL import Image,ImageDraw,ImageFont,ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

NAVY='#11345C';BLUE='#0B5EA7';PALE='#EAF2FB';INK='#172E47';SUB='#516B85';WHITE='#FFFFFF';LINE='#D5E1ED';BKG='#F5F8FC'
FONT_R='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_I='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-BoldOblique.ttf'
def font(s,b=False,italic=False):
    """Use the preferred Laser-style fonts, but never let missing host fonts break posters.

    Render's free Linux image may not include the OS-level DejaVu font files.
    Pillow's own embedded default scalable font is always available as fallback.
    """
    chosen = FONT_I if italic else (FONT_B if b else FONT_R)
    try:
        return ImageFont.truetype(chosen, s)
    except (OSError, ValueError):
        return ImageFont.load_default(size=s)
def text(d,xy,t,size=28,color=INK,bold=False,italic=False):d.text(xy,str(t),font=font(size,bold,italic),fill=color)
def fit_lines(d,value,fontobj,width,max_lines=3):
    words=str(value or '').split(); lines=[];row=''
    for w in words:
        next_line=(row+' '+w).strip()
        if d.textbbox((0,0),next_line,font=fontobj)[2]<=width:row=next_line
        else:
            if row:lines.append(row)
            row=w
    if row:lines.append(row)
    if len(lines)>max_lines:
        lines=lines[:max_lines]
        while lines[-1] and d.textbbox((0,0),lines[-1]+'…',font=fontobj)[2]>width:lines[-1]=lines[-1][:-1]
        lines[-1]+='…'
    return lines

def write_wrap(d,xy,value,max_width,size=29,color=INK,weight=False,leading=1.35,max_lines=4):
    lines=fit_lines(d,value,font(size,weight),max_width,max_lines)
    for i,line in enumerate(lines):text(d,(xy[0],xy[1]+i*int(size*leading)),line,size,color,weight)
    return xy[1]+len(lines)*int(size*leading)

def section(d,x,y,w,title):
    d.rounded_rectangle((x,y,x+w,y+47),radius=4,fill=BLUE)
    text(d,(x+18,y+8),title.upper(),22,WHITE,True)

def header(im,d):
    d.rectangle((0,0,im.width,115),fill=NAVY)
    text(d,(48,14),'LASER',66,WHITE,italic=True)
    text(d,(54,83),'T  O  O  L  S',16,WHITE,True)
    d.rectangle((0,111,im.width,115),fill=BLUE)

def footer(im,d,p):
    H=im.height;d.rectangle((0,H-95,im.width,H),fill=NAVY)
    text(d,(52,H-66),f'LASER {p["part"]}  /  PRODUCT MARKETING DRAFT',23,WHITE,True)
    text(d,(52,H-29),'Source: official Laser Tools / Tool Connection product information · Review before publication',14,'#D9E6F3')

def photo_paste(im,blob,rect):
    picture=Image.open(io.BytesIO(blob)).convert('RGBA')
    bg=Image.new('RGBA',picture.size,(255,255,255,255))
    bg.alpha_composite(picture)
    picture=bg.convert('RGB')
    x0,y0,x1,y1=rect
    area_w=x1-x0-22;area_h=y1-y0-22
    picture.thumbnail((area_w,area_h),Image.Resampling.LANCZOS)
    center=(x0+(x1-x0-picture.width)//2,y0+(y1-y0-picture.height)//2)
    im.paste(picture,center)

def basic(w=1200,h=1600):
    im=Image.new('RGB',(w,h),WHITE);return im,ImageDraw.Draw(im)

def image_pill(d,x,y,copy):
    f=font(21,True)
    width=min(1020,d.textbbox((0,0),str(copy),font=f)[2]+32)
    d.rounded_rectangle((x,y,x+width,y+40),9,fill=PALE)
    text(d,(x+16,y+8),str(copy)[:55],21,BLUE,True)

def small_rule(d,y):d.line((50,y,1150,y),fill=LINE,width=2)

# ---- Catalogue-inspired responsive print compositions ----
# All technical statements below come directly from the verified input record.
# We NEVER draw unverified dimensions, schematic diagrams, or additional components.

PAPER='#F6F8FA'; STEEL='#E7EAED'; DARK='#102B49'; CYAN='#128CCB'; RULE='#C9D3DC'

def rect(d,xy,fill=WHITE,outline=None,width=1):
    d.rectangle(xy,fill=fill,outline=outline,width=width)

def fmt_title(p):
    import re
    return re.sub(r'^'+re.escape(str(p.get('part','')).strip())+r'[ :–—-]*','',str(p.get('title') or 'Product information'),flags=re.I).strip()

def draw_label(d,x,y,w,label,h=38):
    rect(d,(x,y,x+w,y+h),BLUE)
    text(d,(x+15,y+7),label.upper(),21,WHITE,True,italic=True)

def draw_logo(d,x=44,y=24):
    text(d,(x,y),'LASER',72,WHITE,True,True)
    rect(d,(x+6,y+86,x+252,y+89),WHITE)
    text(d,(x+70,y+94),'T O O L S',17,WHITE,True)

def catalogue_header(im,d,compact=False):
    W=im.width;H=158 if not compact else 131
    rect(d,(0,0,W,H),NAVY)
    d.polygon([(W-240,0),(W,0),(W-45,H),(W-295,H)],fill='#0E426B')
    rect(d,(0,H-5,W,H),BLUE)
    if compact:
        text(d,(45,19),'LASER',62,WHITE,True,True)
        text(d,(57,90),'T O O L S',15,WHITE,True)
        text(d,(W-350,55),'ENGINEERED FOR THE JOB.',22,WHITE,True,True)
    else:
        draw_logo(d)
        rect(d,(360,25,363,H-25),WHITE)
        text(d,(414,21),'ENGINEERED',58,WHITE,True,True)
        text(d,(414,82),'FOR THE JOB.',58,WHITE,True,True)

def catalogue_footer(im,d,p,source_note=False):
    W,H=im.size
    rect(d,(0,H-59,W,H),NAVY)
    text(d,(30,H-43),f'LASER {p.get("part","")}  |  PRODUCT CONTENT DRAFT',18,WHITE,True)
    if source_note:
        text(d,(W-333,H-39),'VERIFY BEFORE PUBLICATION',15,'#D4E2F2',True)

def name_strip(d,p,y=176,W=1240):
    rect(d,(0,y-2,W,y+111),'#EAF0F6')
    d.polygon([(20,y+12),(270,y+12),(252,y+95),(20,y+95)],fill=BLUE)
    sku=str(p.get('part',''))
    size=65 if len(sku)<=5 else 50
    text(d,(41,y+15),sku,size,WHITE,True,True)
    name=fmt_title(p).upper()
    for k,s in enumerate((45,40,35,30,27)):
        lines=fit_lines(d,name,font(s,True),940,max_lines=2)
        if len(lines)<=1 or s==27:break
    for i,line in enumerate(lines):
        text(d,(281,y+26+i*46),line,s,NAVY,True,True)

def photo_panel(im,d,blob,area,light=True):
    x0,y0,x1,y1=area
    rect(d,area,WHITE if light else '#EDF2F7',outline=RULE,width=2)
    # Keep the manufacturer's photograph genuine; rescale proportionally only.
    photo_paste(im,blob,(x0+10,y0+10,x1-10,y1-10))

def wrapped(d,content,x,y,w,sz=24,max_lines=6,spacing=1.31,bold=False,color=INK):
    if content is None or str(content).strip()=='':return y
    lines=fit_lines(d,str(content),font(sz,bold),w,max_lines=max_lines)
    for line in lines:
        text(d,(x,y),line,sz,color,bold)
        y+=round(sz*spacing)
    return y

def bullet_rows(d,items,x,y,w,sz=22,limit=5,bottom=1600):
    for raw in [str(v).strip() for v in items if str(v).strip()][:limit]:
        if y+sz*2>bottom:break
        rect(d,(x,y+9,x+11,y+20),BLUE)
        y=wrapped(d,raw,x+25,y,w-31,sz,max_lines=3,spacing=1.29)+12
    return y

def spec_rows(d,specs,x,y,w,limit=6,bottom=1600):
    entries=list((specs or {}).items())[:limit]
    for i,(key,val) in enumerate(entries):
        if y+61>bottom:break
        if i%2==0:rect(d,(x,y-2,x+w,y+56),'#F0F4F8')
        rect(d,(x,y+55,x+w,y+56),RULE)
        wrapped(d,key,x+11,y+13,int(w*.39),19,max_lines=2,bold=True,color=NAVY)
        wrapped(d,val,x+int(w*.40),y+13,int(w*.57),18,max_lines=2,color=INK)
        y+=61
    return y

def unique_usable_features(p):
    raw=p.get('features') or []
    selected=[]
    for item in raw:
        t=' '.join(str(item).split())
        if t and t not in selected:selected.append(t)
    return selected

def choose_glance(p):
    specs=p.get('specs') or {}
    picks=[]
    for k,v in specs.items():
        key=str(k).lower()
        if not any(z in key for z in ('packaged','barcode','brand','country of origin')) and len(str(v))<60:
            picks.append((str(k),str(v)))
    return picks[:4]

def panel(d,x,y,w,h,title,body,sz=21):
    rect(d,(x,y,x+w,y+h),WHITE,outline=RULE,width=2)
    draw_label(d,x,y,w,title,h=40)
    if isinstance(body,list):bullet_rows(d,body,x+16,y+57,w-32,sz,limit=4,bottom=y+h-8)
    else:wrapped(d,body,x+16,y+56,w-32,sz,max_lines=max(3,int((h-64)/(sz*1.25))),spacing=1.29)


def render_technical(p,blob):
    W,H=1240,(1455 if (p.get('specs') or {}) else 1270)
    im,d=basic(W,H);rect(d,(0,0,W,H),PAPER)
    catalogue_header(im,d)
    name_strip(d,p,174,W)
    photo_panel(im,d,blob,(20,296,837,836))
    desc=p.get('description') or ((p.get('features') or [''])[0])
    glimpse=choose_glance(p)
    if glimpse:
        txt=[f'{k}: {v}' for k,v in glimpse[:3]]
        panel(d,857,296,362,201,'AT A GLANCE',txt,20)
    else:
        panel(d,857,296,362,201,'APPLICATION', (p.get('features') or ['Check official product specification'])[0],21)
    panel(d,857,514,362,322,'PURPOSE',desc,21)
    d.line((20,854,1218,854),fill=RULE,width=2)
    Lx,Rx=20,639;Cw=581
    draw_label(d,Lx,870,Cw,'KEY FEATURES')
    feat=unique_usable_features(p)
    specs=p.get('specs') or {}
    # Where no formal specifications were published, split the verified features
    # across both columns instead of repeating the product description.
    left_feat=feat if specs else feat[:max(2,(len(feat)+1)//2)]
    bullet_rows(d,left_feat,Lx+18,931,Cw-36,23,limit=5,bottom=1375)
    if specs:
        draw_label(d,Rx,870,Cw,'TECHNICAL SPECIFICATIONS')
        spec_rows(d,specs,Rx,930,Cw,limit=7,bottom=1385)
    elif len(feat)>2:
        draw_label(d,Rx,870,Cw,'WORKSHOP DETAILS')
        bullet_rows(d,feat[len(left_feat):],Rx+18,931,Cw-36,23,limit=4,bottom=1375)
    else:
        draw_label(d,Rx,870,Cw,'MORE INFORMATION')
        wrapped(d,'Consult the official Laser Tools product information sheet for detailed fitting and operating instructions.',Rx+18,940,Cw-36,23,max_lines=6)
    catalogue_footer(im,d,p,True)
    return png(im)


def render_hero(p,blob):
    W,H=1240,1320
    im,d=basic(W,H);rect(d,(0,0,W,H),PAPER)
    catalogue_header(im,d)
    name_strip(d,p,174,W)
    photo_panel(im,d,blob,(20,296,1219,921))
    draw_label(d,20,938,1200,'WHY CHOOSE THIS TOOL?')
    feat=unique_usable_features(p)
    yy=1012
    for i,t in enumerate(feat[:3]):
        if yy>1350:break
        rect(d,(20,yy+2,75,yy+54),BLUE)
        text(d,(35,yy+10),f'0{i+1}',30,WHITE,True)
        yy=wrapped(d,t,96,yy+3,1100,27,max_lines=2,spacing=1.34)+28
    if not feat:
        wrapped(d,p.get('description',''),38,1010,1130,29,max_lines=7)
    catalogue_footer(im,d,p,True)
    return png(im)


def render_applications(p,blob):
    W,H=1240,1455
    im,d=basic(W,H);rect(d,(0,0,W,H),PAPER)
    catalogue_header(im,d)
    name_strip(d,p,174,W)
    photo_panel(im,d,blob,(20,296,1219,870))
    draw_label(d,20,891,1200,'APPLICATION / WORKSHOP USE')
    # The manufacturer facts often don't contain a separate verified fitment list.
    # Do not invent vehicle models or applications; pull only existing source text.
    use=p.get('applications')
    if not use:
        use=unique_usable_features(p)[:3]
    bullet_rows(d,use,40,966,1150,27,limit=4,bottom=1210)
    draw_label(d,20,1250,1200,'PRODUCT PURPOSE')
    wrapped(d,p.get('description') or (unique_usable_features(p) or [''])[0],40,1309,1150,23,max_lines=3)
    catalogue_footer(im,d,p,True)
    return png(im)


def render_social(p,blob):
    W,H=1080,1080
    im,d=basic(W,H);rect(d,(0,0,W,H),PAPER)
    catalogue_header(im,d,compact=True)
    rect(d,(0,132,W,261),'#EAF0F6')
    d.polygon([(29,151),(239,151),(220,244),(29,244)],fill=BLUE)
    text(d,(46,159),str(p.get('part','')),60,WHITE,True,True)
    name=fmt_title(p).upper()
    lines=fit_lines(d,name,font(36,True),780,2)
    for i,line in enumerate(lines):text(d,(255,168+42*i),line,36,NAVY,True)
    photo_panel(im,d,blob,(30,279,1050,814))
    draw_label(d,30,834,1020,'KEY FEATURE')
    feat=unique_usable_features(p)
    wrapped(d,feat[0] if feat else p.get('description',''),50,890,975,26,max_lines=4)
    rect(d,(0,1024,W,H),NAVY)
    text(d,(42,1043),f'LASER {p.get("part","")}  |  PRODUCT SPOTLIGHT',18,WHITE,True)
    return png(im)

def png(im):
    s=io.BytesIO();im.save(s,format='PNG',optimize=True);return s.getvalue()

def create_posters(p,blob):
    if not blob:raise ValueError('Official photo required')
    return {'Hero':render_hero(p,blob),'Technical':render_technical(p,blob),'Applications':render_applications(p,blob),'Social':render_social(p,blob)}

def create_fact_sheet_pdf(p,blob):
    out=io.BytesIO(); c=canvas.Canvas(out,pagesize=(595,842))
    def line(s,x,y,maxlen=103):
        for j,ch in enumerate(textwrap.wrap(str(s),maxlen)):
            c.drawString(x,y-j*13,ch[:110])
        return y-(j+1)*13 if s else y
    c.setFillColor(HexColor(NAVY));c.rect(0,774,595,68,fill=1,stroke=0)
    c.setFont('Helvetica-BoldOblique',29);c.setFillColor(HexColor(WHITE));c.drawString(30,800,'LASER TOOLS')
    c.setFillColor(HexColor(BLUE));c.setFont('Helvetica-Bold',14);c.drawString(30,745,'TECHNICAL PRODUCT INFORMATION')
    c.setFillColor(HexColor(INK));c.setFont('Helvetica-Bold',24);c.drawString(30,714,'PART '+p['part'])
    c.setFont('Helvetica-Bold',14);y=line(p['title'],30,684,65)
    try:c.drawImage(ImageReader(io.BytesIO(blob)),340,455,210,210, preserveAspectRatio=True,anchor='c')
    except Exception:pass
    c.setFont('Helvetica',9);y=line(p.get('description') or '',30,620,64)
    c.setFont('Helvetica-Bold',12);c.setFillColor(HexColor(BLUE));c.drawString(30,445,'FEATURES'); y=424
    c.setFillColor(HexColor(INK));c.setFont('Helvetica',9)
    for f in p.get('features',[])[:5]:y=line('• '+f,30,y,107)-6
    y=min(y-20,280); c.setFillColor(HexColor(BLUE));c.setFont('Helvetica-Bold',12);c.drawString(30,y,'SPECIFICATIONS');y-=19
    c.setFillColor(HexColor(INK));c.setFont('Helvetica',9)
    for k,v in list(p.get('specs',{}).items())[:9]:y=line(f'{k}: {v}',30,y,108)-7
    c.setFillColor(HexColor(SUB));c.setFont('Helvetica',7)
    c.drawString(30,40,'SOURCE: '+p['source'][:104]);c.drawString(30,28,'Draft generated from official public information. Check all claims and images before publication.')
    c.save();return out.getvalue()

def create_marketing_copy(p):
    items='\n'.join('• '+x for x in p.get('features',[])[:5]);source=p.get('source','')
    return f'''LASER TOOLS {p['part']} — {p['title']}\n\nSOCIAL POST (DRAFT)\nProduct spotlight: Laser Tools {p['part']} — {p['title']}.\n{p.get('description','')}\n\nKey features:\n{items}\n\nMore information: {source}\n\nDISTRIBUTOR EMAIL (DRAFT)\nSubject: Laser Tools {p['part']} | Product Spotlight\n\nHello,\n\nWe're highlighting part {p['part']}, {p['title']}.\n{p.get('description','')}\n\nHighlights:\n{items}\n\nTechnical and product information: {source}\n\nAll copy requires technical and marketing approval before publication.\n'''
