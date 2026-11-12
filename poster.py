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
def font(s,b=False,italic=False):return ImageFont.truetype(FONT_I if italic else FONT_B if b else FONT_R,s)
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

def render_hero(p,blob):
    im,d=basic();header(im,d)
    text(d,(52,148),f'PRODUCT NO. {p["part"]}',31,BLUE,True)
    end=write_wrap(d,(52,207),p['title'],1085,53,NAVY,True,max_lines=3,leading=1.13)
    py=max(330,end+24)
    d.rounded_rectangle((52,py,1148,py+664),14,fill='#FFFFFF',outline=LINE,width=2)
    photo_paste(im,blob,(72,py+14,1128,py+646))
    yy=py+698
    section(d,52,yy,1096,'PRODUCT HIGHLIGHTS')
    yy+=72
    for i,v in enumerate((p.get('features') or [])[:3]):
        if yy>im.height-242:break
        d.ellipse((63,yy+12,75,yy+24),fill=BLUE)
        yy=write_wrap(d,(94,yy),v,1020,27,INK,max_lines=2,leading=1.4)+12
    footer(im,d,p)
    return png(im)

def render_technical(p,blob):
    im,d=basic();header(im,d)
    text(d,(52,146),'TECHNICAL PRODUCT INFORMATION',25,BLUE,True)
    text(d,(52,191),p['part'],55,NAVY,True)
    title_end=write_wrap(d,(260,195),p['title'],860,35,NAVY,True,max_lines=2,leading=1.25)
    py=max(290,title_end+34)
    d.rounded_rectangle((52,py,600,py+485),10,fill=WHITE,outline=LINE,width=2)
    photo_paste(im,blob,(65,py+6,586,py+474))
    d.rounded_rectangle((631,py,1148,py+485),10,fill=BKG,outline=LINE,width=2)
    text(d,(657,py+23),'PRODUCT PURPOSE',23,BLUE,True)
    desc=p.get('description') or (p.get('features') or [''])[0]
    write_wrap(d,(657,py+75),desc,452,24,INK,max_lines=10,leading=1.47)
    spec_y=py+520
    section(d,52,spec_y,1096,'VERIFIED SPECIFICATIONS')
    y=spec_y+66
    specs=list((p.get('specs') or {}).items())[:8]
    if not specs:
        text(d,(74,y+10),'Refer to the official product information sheet for specifications.',23,SUB)
    for i,(key,value) in enumerate(specs):
        rowh=58
        d.rectangle((52,y,1148,y+rowh),fill=WHITE if i%2 else '#F2F6FA')
        text(d,(72,y+16),key[:35],22,NAVY,True)
        write_wrap(d,(502,y+16),value,620,21,INK,max_lines=1)
        y+=rowh
    if y < 1320 and p.get('features'):
        feature_y=max(y+20,1010)
        section(d,52,feature_y,1096,'ADDITIONAL VERIFIED PRODUCT FEATURES')
        feature_y+=65
        for item in p.get('features',[])[:3]:
            if feature_y>1440:break
            d.ellipse((67,feature_y+12,79,feature_y+24),fill=BLUE)
            feature_y=write_wrap(d,(96,feature_y),item,1000,23,INK,max_lines=2,leading=1.4)+10
    footer(im,d,p)
    return png(im)

def render_applications(p,blob):
    im,d=basic();header(im,d)
    text(d,(52,154),'WHERE IT WORKS',56,NAVY,True)
    image_pill(d,52,233,f'LASER {p["part"]}')
    end=write_wrap(d,(52,301),p['title'],1080,41,NAVY,True,max_lines=2)
    py=max(420,end+22)
    d.rounded_rectangle((52,py,1148,py+530),14,fill=WHITE,outline=LINE,width=2)
    photo_paste(im,blob,(72,py+10,1128,py+520))
    y=py+565;section(d,52,y,1096,'APPLICATIONS / TYPICAL USES')
    y+=70
    uses=p.get('applications') or p.get('features',[])[:3]
    if not uses:uses=['See official product information for exact application details.']
    for item in uses[:4]:
        if y>1400:break
        d.ellipse((63,y+9,76,y+22),fill=BLUE)
        y=write_wrap(d,(96,y),item,1010,28,INK,max_lines=2,leading=1.4)+13
    footer(im,d,p)
    return png(im)

def render_social(p,blob):
    im,d=basic(1080,1080);d.rectangle((0,0,1080,106),fill=NAVY)
    text(d,(47,12),'LASER',63,WHITE,italic=True)
    text(d,(59,77),'TOOLS',14,WHITE,True)
    text(d,(740,48),'PRODUCT SPOTLIGHT',23,WHITE,True)
    text(d,(49,130),str(p['part']),57,BLUE,True)
    e=write_wrap(d,(49,205),p['title'],982,42,NAVY,True,max_lines=3,leading=1.18)
    y=max(356,e+28)
    d.rounded_rectangle((40,y,1040,y+475),11,fill=WHITE,outline=LINE,width=2)
    photo_paste(im,blob,(58,y+13,1022,y+462))
    d.rectangle((0,1010,1080,1080),fill=BLUE)
    tagline=(p.get('features') or ['Find out more at Laser Tools'])[0]
    write_wrap(d,(43,920),tagline,980,23,INK,max_lines=3,leading=1.35)
    text(d,(43,1032),'OFFICIAL PRODUCT INFORMATION · DRAFT FOR REVIEW',18,WHITE,True)
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
