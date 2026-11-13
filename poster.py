"""Laser Product Studio — three distinctly art-directed poster formats.

Only verified manufacturer data/photographs feed the output. This is a deterministic
visual design engine; it DOES NOT call generative image APIs or invent diagrams,
measurements, product accessories, prices, logos or extra product photographs.
"""
from __future__ import annotations
import io, re, textwrap, os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

NAVY='#0D2B4F'
BLUE='#0569B8'
CYAN='#19A6E5'
WHITE='#FFFFFF'
INK='#132B48'
MUTED='#4B6885'
PAPER='#F5F7FA'
PALE='#E8F1F8'
BORDER='#D2DFEB'

FONT_PATHS={
    'regular':['/usr/share/fonts/truetype/lato/Lato-Regular.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','DejaVuSans.ttf'],
    'bold':['/usr/share/fonts/truetype/lato/Lato-Heavy.ttf','/usr/share/fonts/truetype/lato/Lato-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','DejaVuSans-Bold.ttf'],
    'italic':['/usr/share/fonts/truetype/lato/Lato-HeavyItalic.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-BoldOblique.ttf','DejaVuSans-Bold.ttf'],
}
_fontcache={}
def font(size,kind='regular'):
    key=(int(size),kind)
    if key not in _fontcache:
        ans=None
        for path in FONT_PATHS.get(kind,FONT_PATHS['regular']):
            try:ans=ImageFont.truetype(path,int(size));break
            except (OSError,ValueError):pass
        if ans is None: ans=ImageFont.load_default(size=int(size))
        _fontcache[key]=ans
    return _fontcache[key]

def txt(d,pos,s,size=26,color=INK,style='regular',anchor=None):
    kwargs={'font':font(size,style),'fill':color}
    if anchor:kwargs['anchor']=anchor
    d.text((int(pos[0]),int(pos[1])),str(s),**kwargs)

def text_width(d,s,size=26,style='regular'):
    b=d.textbbox((0,0),str(s),font=font(size,style));return b[2]-b[0]

def lines(d,s,width,size,style='regular',max_lines=4):
    """Wrap content to pixel width; omit overflow with ellipsis."""
    words=str(s or '').replace('\n',' ').split()
    if not words:return []
    result=[]; current=''
    for word in words:
        candidate=(current+' '+word).strip()
        if text_width(d,candidate,size,style)<=width:
            current=candidate
        else:
            if current:result.append(current)
            current=word
            while text_width(d,current,size,style)>width and len(current)>3:
                current=current[:-1]
            if len(result)>=max_lines:break
    if current and len(result)<max_lines:result.append(current)
    if len(result)>max_lines:result=result[:max_lines]
    if len(words)>len(' '.join(result).split()):
        while result and text_width(d,result[-1]+'…',size,style)>width:
            result[-1]=result[-1][:-1]
        if result:result[-1]=result[-1].rstrip(' .')+'…'
    return result

def paragraph(d,s,x,y,w,size=24,color=INK,style='regular',limit=4,leading=1.25):
    for row in lines(d,s,w,size,style,max_lines=limit):
        txt(d,(x,y),row,size,color,style)
        y+=int(size*leading)
    return y

def fit_title(d,s,maxwidth,starts=(68,62,56,50,46),max_lines=3):
    for size in starts:
        rows=lines(d,s,maxwidth,size,'bold',max_lines=max_lines)
        if len(rows)<=2 and not (rows and rows[-1].endswith('…')):return size,rows
    return starts[-1],lines(d,s,maxwidth,starts[-1],'bold',max_lines=max_lines)

def rgb(color):return tuple(bytes.fromhex(color.lstrip('#')))

def gradient_image(w,h,c1,c2):
    from PIL import Image
    a=rgb(c1);b=rgb(c2)
    strip=Image.new('RGB',(1,h))
    for y in range(h):
        t=y/max(1,h-1)
        strip.putpixel((0,y),tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3)))
    return strip.resize((w,h))

def gradient_box(im,box,c1,c2,vertical=True):
    x0,y0,x1,y1=map(int,box);w=x1-x0;h=y1-y0
    if w<=0 or h<=0:return
    if vertical:piece=gradient_image(w,h,c1,c2)
    else:piece=gradient_image(h,w,c1,c2).transpose(Image.Transpose.ROTATE_90)
    im.paste(piece,(x0,y0))

def bar(d,x,y,w,title,theme=BLUE,h=45):
    d.rectangle((x,y,x+w,y+h),fill=theme)
    txt(d,(x+17,y+8),title.upper(),25,WHITE,'bold')

def line(d,a,b,color=BORDER,width=2):d.line((a[0],a[1],b[0],b[1]),fill=color,width=width)

def logo(d,x=50,y=28,size=65,colour=WHITE):
    txt(d,(x,y),'LASER',size,colour,'italic')
    y2=y+int(size*1.14)
    line(d,(x+7,y2),(x+245*size//65,y2),colour,3)
    txt(d,(x+32,y2+5),'T O O L S',round(size*.19),colour,'bold')

def manufacturer_photo(blob):
    p=Image.open(io.BytesIO(blob));p.load()
    p=ImageOps.exif_transpose(p)
    if p.width*p.height>20_000_000:
        p.thumbnail((3800,3800),Image.Resampling.LANCZOS)
    return p.convert('RGBA')

def trim_photo(photo):
    """Remove excess nearly uniform border without changing product pixels."""
    p=photo.convert('RGB');w,h=p.size
    corners=[p.getpixel((0,0)),p.getpixel((w-1,0)),p.getpixel((0,h-1)),p.getpixel((w-1,h-1))]
    if max(max(v[i] for v in corners)-min(v[i] for v in corners) for i in range(3))>38:
        return photo
    bg=tuple(sum(v[i] for v in corners)//4 for i in range(3))
    diff=ImageChops.difference(p,Image.new('RGB',p.size,bg)).convert('L')
    diff=diff.point(lambda x:255 if x>38 else 0)
    bb=diff.getbbox()
    if not bb:return photo
    x0,y0,x1,y1=bb; padx=max(6,int((x1-x0)*.07));pady=max(6,int((y1-y0)*.07))
    return photo.crop((max(0,x0-padx),max(0,y0-pady),min(w,x1+padx),min(h,y1+pady)))

def contain_photo(im,photo,rect,padding=20,background=WHITE):
    x0,y0,x1,y1=map(int,rect)
    ImageDraw.Draw(im).rectangle((x0,y0,x1,y1),fill=background)
    img=trim_photo(photo).copy()
    available_w=max(1,x1-x0-padding*2); available_h=max(1,y1-y0-padding*2)
    # thumbnail() only shrinks images; enlarge smaller official photos too.
    # Preserve the original pixels, accepting that low-resolution source images
    # may remain less sharp than a manufacturer-supplied high-res photograph.
    scale=min(available_w/max(1,img.width),available_h/max(1,img.height))
    img=img.resize((max(1,int(img.width*scale)),max(1,int(img.height*scale))),Image.Resampling.LANCZOS)
    white=Image.new('RGBA',img.size,(255,255,255,255))
    white.alpha_composite(img)
    img=white.convert('RGB')
    x=x0+(x1-x0-img.width)//2;y=y0+(y1-y0-img.height)//2
    im.paste(img,(x,y))

def isolated_photo(photo):
    """Remove *only* the contiguous near-white studio background.

    No AI redraw or alteration of physical components. On a non-white source,
    preserve the entire image, avoiding aggressive threshold damage.
    """
    p=photo.copy().convert('RGBA')
    w,h=p.size
    if w*h>3_000_000:p.thumbnail((1600,1600),Image.Resampling.LANCZOS);w,h=p.size
    samples=[p.getpixel((int(w*a),int(h*b)))[:3] for a,b in [(0,0),(.99,0),(0,.99),(.99,.99)]]
    nearwhite=lambda c:min(c)>229 and max(c)-min(c)<22
    if sum(nearwhite(c) for c in samples)<3:return p,False
    # Fill connected near-white regions only, never delete bright internal details.
    # Work in a grayscale threshold mask then retain largest exterior area from edges.
    rgbimage=p.convert('RGB')
    pix=rgbimage.load();visited=bytearray(w*h)
    stack=[]
    for y in (0,h-1):
        for x in range(0,w,max(1,w//110)):
            if nearwhite(pix[x,y]):stack.append((x,y))
    for x in (0,w-1):
        for y in range(0,h,max(1,h//110)):
            if nearwhite(pix[x,y]):stack.append((x,y))
    # Fast bbox flood to transparent outside with restrained thresholds.
    from collections import deque
    q=deque(stack)
    while q:
        x,y=q.popleft();i=y*w+x
        if visited[i] or not nearwhite(pix[x,y]):continue
        visited[i]=1
        if x>0:q.append((x-1,y))
        if x<w-1:q.append((x+1,y))
        if y>0:q.append((x,y-1))
        if y<h-1:q.append((x,y+1))
    alpha=Image.new('L',(w,h),255)
    alpha.putdata([0 if t else 255 for t in visited])
    alpha=alpha.filter(ImageFilter.GaussianBlur(.55))
    p.putalpha(ImageChops.multiply(p.getchannel('A'),alpha))
    bb=p.getbbox()
    if bb:p=p.crop(bb)
    return p,True

def place_cutout(im,photo,box):
    cut,isolated=isolated_photo(trim_photo(photo))
    if not isolated:
        contain_photo(im,photo,box,padding=25,background='#EDF4FA')
        return
    x0,y0,x1,y1=box
    # Scale authentic source photo up as well as down. A thumbnail source should
    # not become a tiny speck in the advert (the resolution may still be limited).
    maxw,maxh=x1-x0-55,y1-y0-45
    factor=min(maxw/cut.width,maxh/cut.height)
    if factor>0:
        cut=cut.resize((max(1,round(cut.width*factor)),max(1,round(cut.height*factor))),Image.Resampling.LANCZOS)
    x=x0+(x1-x0-cut.width)//2;y=y0+(y1-y0-cut.height)//2
    shadow=Image.new('RGBA',im.size,(0,0,0,0));mask=cut.getchannel('A')
    ss=Image.new('RGBA',cut.size,(0,0,0,85));ss.putalpha(mask.point(lambda a:int(a*.30)))
    shadow.paste(ss,(x+12,y+15),ss)
    shadow=shadow.filter(ImageFilter.GaussianBlur(15))
    im.paste(Image.alpha_composite(im.convert('RGBA'),shadow).convert('RGB'))
    im.paste(cut,(x,y),cut)

def product_name(p):
    name=str(p.get('title') or 'Professional workshop tool').strip()
    part=str(p.get('part') or '').strip()
    if part:name=re.sub(r'^'+re.escape(part)+r'(?:\s+|\s*[-:–—]\s*)','',name,flags=re.I).strip()
    return name or 'Professional workshop tool'

def facts(p):
    return list(dict.fromkeys(' '.join(str(x).split()) for x in (p.get('features') or []) if str(x).strip()))

def props(p):
    return {str(k).strip():str(v).strip() for k,v in (p.get('specs') or {}).items() if str(v).strip()}

def best_specs(p,n=8):
    s=props(p)
    reject=('packaged','brand','barcode','country of origin','weight')
    priority=['length','dimension','voltage','wattage','power','material','capacity','run time','drive','diameter','number of pieces','standard','type','weight']
    def score(entry):
        key,val=entry;low=key.lower()
        return (sum(1 for a in reject if a in low),next((i for i,a in enumerate(priority) if a in low),99))
    entries=[(k,v) for k,v in s.items() if not k.lower().startswith('packaged')]
    entries.sort(key=score)
    return entries[:n]

def key_fact(p):
    for k,v in best_specs(p,7):
        if any(term in k.lower() for term in ('watt','power','lumens','drive','length','range','voltage','size','capacity','weight','pieces')):
            if len(str(v))<=30:return k,v
    return None

def choose_headline(p):
    source=(product_name(p)+' '+(p.get('description') or '')).lower()
    feat=' '.join(facts(p)).lower();alltext=source+' '+feat
    if any(w in source for w in ('brake bleeder','brake bleeding','bleeding kit')):
        return ('ONE-PERSON','BRAKE BLEEDING.')
    if any(w in source for w in ('workshop press','hydraulic press')):
        return ('PRESS WITH','CONFIDENCE.')
    if any(w in source for w in ('work lamp','work light','inspection light','under bonnet light')):
        return ('PUT THE JOB','IN THE SPOTLIGHT.')
    if any(w in source for w in ('bearing','hub puller')):
        return ('GET TO GRIPS','WITH BEARING WORK.')
    if 'split hub' in source or 'knuckle spreader' in source or 'strut spreader' in source:
        return ('MAKE ROOM.','GET THE JOB DONE.')
    if 'endoscope' in source or 'inspection camera' in source:
        return ('SEE THE','HIDDEN DETAILS.')
    if 'jump starter' in source or 'booster' in source:
        return ('POWER TO','GET MOVING.')
    if 'ratchet' in source:
        return ('SMALL TOOL.','BIG VERSATILITY.')
    if 'cutter' in source:
        return ('MAKE THE CUT.','KEEP MOVING.')
    if 'torque' in source:
        return ('PRECISION','AT WORK.')
    if 'under bonnet' in source or 'bonnet' in source:
        return ('LIGHT THE WAY','TO A BETTER JOB.')
    return ('BUILT FOR','THE JOB IN HAND.')

def short_features(p,n=3):
    """Extract small, grounded customer-facing phrases without inventing benefits."""
    result=[]
    for f in facts(p):
        s=re.sub(r'^(ideal for|suitable for|includes|features)\s+', '',f,flags=re.I)
        s=s.split(';')[0].split('. ')[0].strip(' .')
        if len(s)>96:
            s=re.split(r', | together with | which | and also ',s,1)[0]
        if len(s)>98:
            s=s.split(' (')[0]
            if len(s)>98:s=s[:95].rsplit(' ',1)[0]+'…'
        if s:
            s=s[0].upper()+s[1:]
            if s not in result:result.append(s)
        if len(result)>=n:break
    if not result and p.get('description'):result=[p['description'][:95]]
    return result

def png(im):
    buffer=io.BytesIO();im.save(buffer,'PNG',optimize=True)
    return buffer.getvalue()

def page_footer(d,W,H,p,color=NAVY):
    d.rectangle((0,H-62,W,H),fill=color)
    txt(d,(48,H-42),f'LASER  {p.get("part", "")}    •    MARKETING DRAFT / CHECK BEFORE PUBLICATION',19,WHITE,'bold')

# ---------------------------------------------------------------------------
# V5 — art direction matching the two user-supplied Laser reference posters.
# All source photographs are placed or cropped, never regenerated.
# Technical dimensions or drawings are never inferred from a photo.
# ---------------------------------------------------------------------------
from decimal import Decimal, ROUND_HALF_UP

def prepared_price(p):
    """Consistent UK RRP display: inc VAT prominent, ex VAT secondary.

    Uses the 20% UK standard VAT rate for this automotive tools pilot.
    Amounts are always labelled as calculated where a source supplied just one.
    """
    raw=str(p.get('price') or '').strip()
    match=re.search(r'£\s*([\d,]+(?:\.\d{1,2})?)',raw)
    if not match:return None
    try:amount=Decimal(match.group(1).replace(',',''))
    except Exception:return None
    if not amount.is_finite() or amount<=0:return None
    fmt=lambda a:f'£{a:,.2f}'
    text=raw.lower()
    is_ex=any(v in text for v in ('excluding vat','plus vat','exc vat','ex vat','excl vat'))
    is_inc=any(v in text for v in ('including vat','inc vat','inc. vat','incl vat'))
    if is_ex:
        inc=(amount*Decimal('1.20')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        return {'primary':fmt(inc),'basis':'INC VAT','secondary':f'{fmt(amount)} EX VAT',
                'source_basis':'UK RRP excluding VAT; inc VAT calculated at 20%.'}
    if is_inc:
        ex=(amount/Decimal('1.20')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        return {'primary':fmt(amount),'basis':'INC VAT','secondary':f'{fmt(ex)} EX VAT',
                'source_basis':'UK RRP including VAT; ex VAT calculated at 20%.'}
    return None


def clean_name_for_poster(p):
    name=product_name(p)
    # Preserve the manufacturer's product name; never invent a shorter substitute.
    return name.strip()

def feature_text(p,amount=4):
    return facts(p)[:amount]

def application_from_record(p):
    s=props(p)
    for k in ('Application','Applications','Vehicle application','Vehicle Application'):
        if s.get(k):return s[k]
    if p.get('applications'):
        x=p['applications'];return ' • '.join(map(str,x[:4])) if isinstance(x,list) else str(x)
    for x in facts(p):
        if re.search(r'\bapplications? (include|:)|\bsuitable for use with|\bfor use on|\bfor use with',x,re.I):
            return x
    if s.get('Vehicle manufacturer') and s.get('Vehicle model'):
        return s['Vehicle manufacturer']+' · '+s['Vehicle model']
    for x in facts(p):
        if re.search(r'\b(for removal|for fitting|ideal for|designed for)',x,re.I):return x
    return 'Refer to the official product listing for approved applications.'

def short_purpose(p):
    s=' '.join(str(p.get('description') or '').split())
    if not s:
        s=(facts(p) or ['See the manufacturer product information sheet.'])[0]
    # Use only an authentic description, shortened at a sentence boundary when feasible.
    first=re.split(r'(?<=[.!?])\s+',s)
    v=first[0]
    if len(v)<110 and len(first)>1:v+=' '+first[1]
    return v[:340] if len(v)>340 else v

def callout_feature(p,index=0,maxlen=75):
    fs=facts(p)
    s=fs[index%len(fs)] if fs else short_purpose(p)
    s=' '.join(s.split()).rstrip(' .')
    if len(s)>maxlen:s=s[:maxlen-2].rsplit(' ',1)[0]+'…'
    return s

def labelled_section(d,x,y,w,text,height=46):
    d.rectangle((x,y,x+w,y+height),fill=BLUE)
    txt(d,(x+16,y+8),text.upper(),24,WHITE,'italic')

def text_rows(d,text,x,y,w,size=22,maxrows=5,style='regular',fill=INK,leading=1.24):
    r=lines(d,text,w,size,style,max_lines=maxrows)
    for q in r:
        txt(d,(x,y),q,size,fill,style)
        y+=round(size*leading)
    return y

def photo_safe(im,photo,box,cutout=False):
    if cutout:
        place_cutout(im,photo,box)
    else:
        contain_photo(im,photo,box,padding=14,background=WHITE)

def render_technical(p,blob):
    """Reference 1: real Laser-style technical catalogue sheet with information hierarchy."""
    W,H=1280,1590
    im=Image.new('RGB',(W,H),WHITE)
    # Subtle catalogue paper rather than sci-fi effects.
    d=ImageDraw.Draw(im)
    gradient_box(im,(0,0,W,176),'#07355D','#092646',vertical=False)
    d=ImageDraw.Draw(im)
    d.polygon([(1190,0),(1280,0),(1220,176),(1124,176)],fill='#1166A0')
    logo(d,46,17,72)
    line(d,(421,23),(400,149),WHITE,4)
    txt(d,(464,12),'ENGINEERED',70,WHITE,'italic')
    txt(d,(464,88),'FOR THE JOB.',70,WHITE,'italic')
    d.rectangle((0,176,W,310),fill='#E9EEF3')
    d.polygon([(15,189),(260,189),(232,295),(15,295)],fill=BLUE)
    part=str(p.get('part',''))
    txt(d,(33,202),part,78,WHITE,'italic')
    name=clean_name_for_poster(p).upper()
    title_size,title_rows=fit_title(d,name,980,(52,48,43,39,36,32,28),max_lines=2)
    title_y=193 if len(title_rows)>1 else 220
    for i,row in enumerate(title_rows):txt(d,(283,title_y+i*(title_size+8)),row,title_size,NAVY,'italic')
    # Hero photo and right-side application + purpose panels.
    d.rectangle((20,327,830,887),outline='#B4C4D3',width=2,fill=WHITE)
    photo=manufacturer_photo(blob)
    photo_safe(im,photo,(26,332,824,882),cutout=False)
    d=ImageDraw.Draw(im)
    labelled_section(d,851,327,410,'APPLICATION')
    text_rows(d,application_from_record(p),868,389,376,24,6,fill=INK,leading=1.25)
    d.rectangle((851,561,1261,887),fill='#F0F4F8')
    labelled_section(d,851,561,410,'PURPOSE')
    text_rows(d,short_purpose(p),868,624,372,22,9,fill=INK,leading=1.28)
    # Horizontal separation aligns with the user's source sheet.
    line(d,(20,909),(1260,909),'#9FAEBB',2)
    labelled_section(d,20,932,610,'KEY FEATURES & FUNCTION')
    labelled_section(d,650,932,610,'VERIFIED TECHNICAL DATA')
    # Left: a feature table with strong hierarchy and alternating rows.
    f=feature_text(p,5)
    left_y=993
    max_left=1453
    if not f:f=['Refer to the manufacturer product information sheet for technical features.']
    hrow=min(100,max(81,(max_left-left_y)//len(f)))
    for i,s in enumerate(f):
        if left_y+hrow>1470:break
        d.rectangle((20,left_y,630,left_y+hrow),fill=WHITE if i%2 else '#F1F5F9',outline='#C8D4E0',width=1)
        d.rectangle((35,left_y+19,88,left_y+68),fill='#E3EEF6')
        txt(d,(44,left_y+26),f'{i+1:02}',24,BLUE,'bold')
        text_rows(d,s,103,left_y+16,500,19,3,fill=INK,leading=1.19)
        left_y+=hrow
    # Right: genuine product properties in a labelled table. No invented dimensions/diagrams.
    spec=best_specs(p,8)
    if not spec:
        spec=[('Details','Refer to official manufacturer product information sheet.')]
    right_y=993
    maxrows=min(8,len(spec));rh=min(78,(1454-right_y)//maxrows)
    for i,(k,v) in enumerate(spec[:maxrows]):
        if right_y+rh>1471:break
        d.rectangle((650,right_y,1260,right_y+rh),fill='#F1F5F9' if i%2==0 else WHITE,outline='#C8D4E0',width=1)
        text_rows(d,k,665,right_y+15,208,18,2,'bold',NAVY,1.15)
        text_rows(d,v,880,right_y+13,355,20,2,'regular',INK,1.13)
        right_y+=rh
    d.rectangle((20,1473,1260,1539),fill='#EAF1F8')
    txt(d,(35,1493),'SOURCE: OFFICIAL LASER TOOLS / TOOL CONNECTION PRODUCT INFORMATION',18,BLUE,'bold')
    txt(d,(35,1517),'Technical accuracy and use of imagery require approval before external release.',15,MUTED)
    d.rectangle((0,1547,W,H),fill=NAVY)
    txt(d,(30,1559),f'LASER TOOLS    |    {part}    |    PRODUCT TECHNICAL INFORMATION',19,WHITE,'bold')
    return png(im)

def render_hero(p,blob,application_blob=None):
    """Wide, visual campaign advert: genuine in-situ photograph where supplied.

    Not a datasheet and not a second price panel. Compared with the technical
    portrait, typography sits over a solid navy wing next to a full-bleed image.
    """
    W,H=1600,920
    im=Image.new('RGB',(W,H),'#08243F')
    gradient_box(im,(0,0,W,H),'#041C34','#0A4774',vertical=False)
    d=ImageDraw.Draw(im)
    # Right-hand photograph uses actual Laser manufacturer imagery only.
    x0,y0,x1,y1=665,0,1600,800
    if application_blob:
        try:
            scene=manufacturer_photo(application_blob).convert('RGB')
            scene=ImageOps.fit(scene,(x1-x0,y1-y0),Image.Resampling.LANCZOS,centering=(.5,.52))
            im.paste(scene,(x0,y0))
        except Exception:
            application_blob=None
    if not application_blob:
        d.rectangle((x0,0,x1,800),fill='#E4EDF5')
        # Make the official isolated product photograph dominant, without
        # inventing an application scene or cropping out the actual tool.
        place_cutout(im,manufacturer_photo(blob),(710,54,1562,768))
    d=ImageDraw.Draw(im)
    # Thick angled brand panel is separate from the image; cleaner than a white
    # photograph in another blue-framed card.
    d.polygon([(0,0),(805,0),(673,800),(0,800)],fill='#062748')
    d.polygon([(775,0),(825,0),(695,800),(648,800)],fill='#0C8ACA')
    d.rectangle((0,0,W,12),fill=CYAN)
    logo(d,58,35,71)
    d.rectangle((72,192,570,196),fill='#1CA4D8')
    line1,line2=choose_headline(p)
    for idx,(row,fill) in enumerate(((line1,WHITE),(line2,'#2DCBFF'))):
        size=70
        while size>43 and text_width(d,row,size,'italic')>580:size-=4
        txt(d,(64,242+idx*101),row,size,fill,'italic')
    name=clean_name_for_poster(p)
    sz,rows=fit_title(d,name,565,(39,36,33,30),max_lines=3)
    for i,row in enumerate(rows[:3]):
        txt(d,(69,471+i*(sz+9)),row,sz,WHITE,'bold')
    d.rectangle((68,689,300,695),fill=CYAN)
    txt(d,(70,721),'MADE FOR THE WORKSHOP',22,'#BBD8EA','bold')
    # Part number on its own solid panel so it reads against any source image.
    d.polygon([(1283,22),(1570,22),(1540,130),(1270,130)],fill='#075A9D')
    txt(d,(1322,36),str(p.get('part','')),76,WHITE,'italic')
    # A discreet approved-price badge on the advert; the separate sales graphic
    # remains the only poster where RRP is the primary focal point.
    uk_price=prepared_price(p)
    if uk_price:
        d.rounded_rectangle((1132,651,1575,792),radius=7,fill='#065EAA')
        d.rectangle((1132,651,1575,659),fill=CYAN)
        txt(d,(1154,669),'UK RRP INC VAT',24,WHITE,'bold')
        point_size=68
        while point_size>39 and text_width(d,uk_price['primary'],point_size,'bold')>408:point_size-=4
        txt(d,(1152,704),uk_price['primary'],point_size,WHITE,'bold')
    # An off-white benefits strip, not repeated spec blocks.
    d.rectangle((0,800,W,920),fill='#F2F7FB')
    points=short_features(p,3)
    if not points:points=[short_purpose(p)]
    for i,claim in enumerate(points[:3]):
        x=42+i*523
        if i:d.rectangle((x-18,822,x-15,883),fill='#C7DDE9')
        d.rectangle((x,822,x+35,856),fill=BLUE)
        txt(d,(x+11,825),str(i+1),23,WHITE,'bold')
        text_rows(d,claim,x+48,817,452,23,3,'bold',NAVY,1.17)
    txt(d,(1543,894),'LASER TOOLS  ·  MARKETING DRAFT',14,MUTED,'bold',anchor='ra')
    return png(im)


def render_price(p,blob):
    """Price-first square retailer graphic, intentionally unrelated to hero composition."""
    W,H=1200,1200
    im=Image.new('RGB',(W,H),WHITE)
    gradient_box(im,(0,0,W,137),'#095EA2','#003C78',vertical=False)
    d=ImageDraw.Draw(im)
    logo(d,47,18,60)
    d.rectangle((950,32,955,110),fill=CYAN)
    txt(d,(979,27),str(p.get('part','')),70,WHITE,'italic')
    d.rectangle((0,137,W,147),fill=CYAN)
    title=clean_name_for_poster(p)
    name_size,name_rows=fit_title(d,title,1100,(55,49,44,40,36,33),max_lines=2)
    title_y=175
    for i,row in enumerate(name_rows):
        txt(d,(52,title_y+i*(name_size+8)),row,name_size,NAVY,'bold')
    pic_y=max(300,title_y+len(name_rows)*(name_size+8)+20)
    d.rectangle((40,pic_y,1160,715),fill='#F3F7FA')
    photo=manufacturer_photo(blob)
    photo_safe(im,photo,(55,pic_y+8,1145,707),cutout=False)
    d=ImageDraw.Draw(im)
    d.rectangle((0,728,W,1130),fill=BLUE)
    d.polygon([(1040,728),(1200,728),(1200,1130),(897,1130)],fill='#04477D')
    data=prepared_price(p)
    if data:
        txt(d,(58,754),'UK MANUFACTURER RRP',34,'#D8F3FF','bold')
        price_size=152 if len(data['primary'])<=8 else 119
        while price_size>88 and text_width(d,data['primary'],price_size,'bold')>1070:price_size-=7
        txt(d,(45,818),data['primary'],price_size,WHITE,'bold')
        txt(d,(69,1020),data['basis'],31,'#D5F1FF','bold')
        txt(d,(425,1020),data['secondary'],31,WHITE,'bold')
    else:
        txt(d,(58,772),'UK MANUFACTURER RRP',35,'#D8F3FF','bold')
        txt(d,(59,845),'NOT VERIFIED',88,WHITE,'bold')
        txt(d,(61,1034),'REVIEW OFFICIAL PRODUCT PRICING',26,WHITE,'bold')
    d.rectangle((0,1130,W,H),fill=NAVY)
    txt(d,(49,1145),'lasertools.co.uk',24,WHITE,'bold')
    txt(d,(1155,1145),'DRAFT · CHECK PRICE BEFORE PUBLICATION',16,'#B7D4E5','bold',anchor='ra')
    return png(im)


def create_posters(p,blob,application_blob=None):
    if not blob:raise ValueError('A verified manufacturer product image is required.')
    return {
       'Hero':render_hero(p,blob,application_blob),
       'Technical':render_technical(p,blob),
       'Price':render_price(p,blob),
    }

def create_fact_sheet_pdf(p,blob):
    # Export the exact technical poster into A4; PNG and PDF cannot contradict.
    poster=Image.open(io.BytesIO(render_technical(p,blob))).convert('RGB')
    output=io.BytesIO()
    c=canvas.Canvas(output,pagesize=(595.28,841.89))
    c.drawImage(ImageReader(poster),0,0,width=595.28,height=841.89)
    c.save()
    return output.getvalue()

def create_marketing_copy(p):
    key=short_features(p,3)
    head=' '.join(choose_headline(p))
    price=prepared_price(p)
    price_line=(f"Manufacturer RRP: {price['primary']} ({price['basis']}). "
                f"{price['source_basis']}") if price else                'Manufacturer RRP: Not verified from retrieved source; do not publish an assumed price.'
    return f'''LASER TOOLS {p.get('part')} — {product_name(p)}\n\nPROMOTIONAL POSTER HEADLINE (DRAFT)\n{head}\n\nShort customer points:\n{chr(10).join('• '+v for v in key)}\n\nTECHNICAL POSTER\nUse only the verified description, source features and specs in the attached source record. No inferred measurements or diagrams.\n\nRRP / SALES POSTER\n{price_line}\n\nPRODUCT SOURCE\n{p.get('source','')}\n\nREVIEW REQUIRED: price, product image rights, application wording, technical correctness and brand approval.\n'''
