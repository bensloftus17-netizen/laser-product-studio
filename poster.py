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

def campaign_benefit(p):
    """Compact, defensible sales benefit from official product facts."""
    title=clean_name_for_poster(p).lower()
    corpus=' '.join(facts(p)).lower()+' '+str(p.get('description') or '').lower()
    if 'split hub' in title and ('strut' in corpus and ('leaving the hub' in corpus or 'without removing' in corpus)):
        return 'Remove & refit struts without removing the hub'
    if ('brake bleeder' in title or 'bleeding' in title) and ('one' in corpus or 'pump' in corpus or 'pressure' in corpus):
        return 'Controlled pressure bleeding for workshop servicing'
    if any(word in title for word in ('work lamp','under bonnet','inspection lamp')) and ('magnet' in corpus or 'hook' in corpus):
        return 'Hands-free illumination for hard-to-reach jobs'
    if ('bearing' in title or 'bush' in title) and ('remov' in corpus or 'fit' in corpus):
        return 'Remove & fit bushes and bearings with confidence'
    if 'press' in title and ('50 tonne' in title or '50 ton' in title):
        return '50-tonne capacity for professional workshop work'
    if facts(p):
        fact=short_features(p,1)[0]
        return fact[:106].rstrip(' ,.;') if len(fact)>106 else fact
    return short_purpose(p)[:106].rstrip(' ,.;')


def campaign_quick_facts(p):
    """A strictly factual three-cell bottom strip, no copied sales paragraphs."""
    output=[]
    title=clean_name_for_poster(p).lower()
    known=' '.join(facts(p)).lower()+' '+str(p.get('description') or '').lower()
    # Make the reference-like specifications recognizable when they are verified.
    if 'split hub' in title:
        if 'double' in known:output.append('DOUBLE-ENDED DESIGN')
        if re.search(r'\b10\s*mm\b',known):output.append('10MM HEX DRIVE')
        if re.search(r'\b15\s*mm\b',known):output.append('15MM MAX OPENING')
    if 'work lamp' in title or 'under bonnet' in title:
        if 'magnet' in known:output.append('MAGNETIC MOUNTING')
        if re.search(r'\b10\s*w(?:att)?\b',known):output.append('10W COB LIGHT')
        if 'usb-c' in known:output.append('USB-C RECHARGEABLE')
    if 'press' in title:
        if '50 tonne' in title or '50 ton' in title:output.append('50-TONNE CAPACITY')
        if 'air' in known:output.append('AIR-HYDRAULIC')
        if 'foot control' in known:output.append('FOOT CONTROL')
    for key,val in best_specs(p,5):
        item=(str(val)+' '+str(key)).upper().strip()
        if len(item)<32 and item not in output:output.append(item)
        if len(output)>=3:break
    if len(output)<3:
        for point in short_features(p,5):
            point=point.upper().strip(' .')
            if len(point)>37:point=point[:34].rsplit(' ',1)[0]+'…'
            if point not in output:output.append(point)
            if len(output)>=3:break
    return output[:3]


def render_hero(p,blob,application_blob=None):
    """Photo-first reference-style 2:3 ad for ANY Laser SKU.

    Giant product-specific name on a white diagonal, strong blue official-logo
    header, large authentic tool shot over photographic manufacturer imagery,
    angled RRP ribbon (ex-VAT prominent), black spec strip and full-width
    blue footer. Does NOT redraw/change the tool or fabricate a workshop photo.
    """
    W,H=1200,1800
    photo=manufacturer_photo(blob)
    im=Image.new('RGB',(W,H),'#435565')
    # Background: manufacturer's own application photograph wherever available.
    # Other SKUs use an atmospheric, blurred *real product photograph* rather
    # than a simulated workshop with an invented tool or a bland flat panel.
    stage_rect=(0,190,W,1510)
    stage_h=stage_rect[3]-stage_rect[1]
    try:
        original=manufacturer_photo(application_blob) if application_blob else photo
        background=ImageOps.fit(original.convert('RGB'),(W,stage_h),Image.Resampling.LANCZOS,centering=(.50,.45))
        background=background.filter(ImageFilter.GaussianBlur(7 if application_blob else 55))
        tint=Image.new('RGB',background.size,'#213443')
        background=Image.blend(background,tint,.23 if application_blob else .62)
        im.paste(background,(0,stage_rect[1]))
    except Exception:
        gradient_box(im,stage_rect,'#5E6E7B','#253B4E')
    d=ImageDraw.Draw(im)
    # Faint steel surface horizon, deliberately graphic so it is not a faked
    # real product demonstration.
    d.polygon([(0,1292),(1200,1238),(1200,1510),(0,1510)],fill=(55,64,72))
    for n in range(13):
        y=1308+n*15
        d.line((0,y,1200,y-55),fill='#687887',width=1)

    # Render the authentic product large over the background.
    # Tall lamps and presses get a taller stage; horizontal kits fill the width.
    cropped=trim_photo(photo)
    aspect=cropped.width/max(1,cropped.height)
    if aspect<.64:
        stage=(270,607,1100,1410)
    elif aspect>1.45:
        stage=(4,679,1194,1407)
    else:
        stage=(28,644,1188,1424)
    place_cutout(im,photo,stage)
    d=ImageDraw.Draw(im)

    # Oversized, angular blue Laser masthead as in the supplied reference.
    d.polygon([(0,0),(770,0),(648,246),(0,267)],fill='#0457A8')
    d.polygon([(733,0),(772,0),(665,238),(628,242)],fill=WHITE)
    d.rectangle((0,0,575,12),fill='#138DDD')
    logo(d,64,30,143)

    # Huge white oblique product name banner, intentionally independent of
    # the image. Body text is never placed over the actual tool.
    d.polygon([(0,268),(1173,224),(1108,605),(0,643)],fill=WHITE)
    name=clean_name_for_poster(p).upper().replace(' - ',' ')
    # Retain every title word while trying 2 lines first for headline impact.
    chosen=None
    for maxlines in (2,3):
        for sz in (116,110,104,98,92,86,80,74,68,62,57,52):
            test=lines(d,name,1098,sz,'italic',max_lines=maxlines)
            if test and not test[-1].endswith('…') and len(test)<=maxlines:
                chosen=(sz,test)
                break
        if chosen:break
    if chosen is None:
        chosen=(52,lines(d,name,1098,52,'italic',max_lines=3))
    size,rows=chosen
    step=size+15
    title_y=307+(3-len(rows))*14
    for i,row in enumerate(rows):
        ink='#101417' if i==0 else '#005BAD'
        txt(d,(54,title_y+i*step),row,size,ink,'italic')

    # Part number, floating in a standalone blue wedge under the headline.
    d.polygon([(0,635),(457,615),(391,763),(0,777)],fill='#0759AF')
    sku=str(p.get('part') or '').upper()
    sku_size=128
    while sku_size>70 and text_width(d,sku,sku_size,'italic')>355:sku_size-=5
    txt(d,(52,647),sku,sku_size,WHITE,'italic')

    # Overlay the reference-style white benefit ribbon, not a paragraph panel.
    d.polygon([(0,1389),(765,1366),(703,1570),(0,1570)],fill=WHITE)
    d.line((61,1437,29,1541),fill='#0067BB',width=9)
    benefit=campaign_benefit(p)
    picked=None
    for sz in (50,47,44,41,38,35,32):
        rows=lines(d,benefit,575,sz,'italic',max_lines=3)
        if rows and not rows[-1].endswith('…'):
            picked=sz,rows
            break
    if picked is None:picked=(32,lines(d,benefit,575,32,'italic',max_lines=3))
    bsz,brows=picked
    benefit_y=1434+(3-len(brows))*13
    for idx,row in enumerate(brows):
        txt(d,(83,benefit_y+idx*(bsz+9)),row,bsz,'#11151C','italic')

    # Oversized right price wedge in the artwork (not a normal UI box).
    d.polygon([(779,1295),(1200,1295),(1200,1570),(675,1570)],fill='#0059B1')
    d.polygon([(779,1295),(1200,1295),(1200,1308),(775,1308)],fill='#17A3E5')
    price=prepared_price(p)
    if price:
        ex=price['secondary'].split(' EX VAT')[0]
        inc=price['primary']
        txt(d,(807,1323),'RRP',54,WHITE,'italic')
        amount_size=119
        while amount_size>40 and text_width(d,ex,amount_size,'italic')>455:
            amount_size-=5
        txt(d,(772,1382),ex,amount_size,WHITE,'italic')
        txt(d,(850,1516),'+ VAT',36,WHITE,'italic')
        txt(d,(1184,1546),inc+' INC VAT',17,'#D3EDFE','bold',anchor='ra')
    else:
        txt(d,(815,1385),'UK RRP',43,WHITE,'italic')
        txt(d,(785,1461),'VERIFY PRICE',40,WHITE,'italic')
        txt(d,(887,1530),'BEFORE RELEASE',23,WHITE,'bold')

    # Exact fact strip, NOT a row of repeated marketing paragraphs.
    d.rectangle((0,1570,W,1663),fill='#111316')
    points=campaign_quick_facts(p)
    for i in range(3):
        x=i*400
        if i:
            d.polygon([(x-14,1583),(x-4,1583),(x-20,1648),(x-30,1648)],fill='#0078CA')
        if i>=len(points):continue
        point=points[i]
        font_size=27
        rows=lines(d,point,356,font_size,'italic',max_lines=2)
        while font_size>18 and (len(rows)>1 or rows[-1].endswith('…')):
            font_size-=2;rows=lines(d,point,356,font_size,'italic',max_lines=2)
        for j,row in enumerate(rows):
            width=text_width(d,row,font_size,'italic')
            txt(d,(x+(400-width)//2,1596+j*(font_size+4)),row,font_size,WHITE,'italic')

    # Big brand-blue footer to echo the reference's full-width end card.
    gradient_box(im,(0,1690,W,H),'#0062B4','#003D83',vertical=False)
    d=ImageDraw.Draw(im)
    logo(d,39,1694,79)
    d.line((708,1703,681,1772),fill=WHITE,width=6)
    txt(d,(754,1717),'lasertools.co.uk',44,WHITE,'italic')
    txt(d,(1180,1780),'MARKETING DRAFT · VERIFY SOURCE, RRP & DESIGN BEFORE RELEASE',13,'#D2E9F8','bold',anchor='ra')
    return png(im)


def render_price(p,blob):
    """Distinct trade-counter sales graphic: landscape with a huge price wall.

    Different from the photographic portrait advert AND the technical catalogue.
    Product image is the genuine manufacturer photo. No inferred promotions.
    """
    W,H=1600,980
    im=Image.new('RGB',(W,H),'#F1F5F9')
    d=ImageDraw.Draw(im)
    # Left = product photography; no technical grid and no advertising background.
    d.rectangle((0,0,955,H),fill='#EFF5F9')
    d.polygon([(0,0),(720,0),(663,161),(0,172)],fill='#074F96')
    logo(d,53,13,98)
    d.polygon([(0,172),(955,161),(955,179),(0,190)],fill='#2CA4E7')
    # A subtle studio sweep makes the photograph feel more premium.
    d.ellipse((-240,252,1095,1260),fill='#E4EEF6')
    d.ellipse((-160,356,995,1200),outline='#CBDDEB',width=3)
    photo=manufacturer_photo(blob)
    place_cutout(im,photo,(28,267,935,835))
    d=ImageDraw.Draw(im)
    txt(d,(52,870),'LASER TOOLS · PRODUCT SPOTLIGHT',33,BLUE,'italic')
    txt(d,(52,927),'lasertools.co.uk',26,NAVY,'bold')
    # Right = almost full-height price wall, so the price is immediately legible.
    gradient_box(im,(956,0,W,H),'#004D99','#063560',vertical=False)
    d=ImageDraw.Draw(im)
    d.polygon([(956,0),(1054,0),(995,980),(956,980)],fill='#0985CF')
    d.rectangle((1019,72,1538,77),fill='#3CC2FC')
    txt(d,(1070,100),'PART NO.',33,'#BDDEFB','bold')
    sku=str(p.get('part','')).upper()
    sku_sz=103
    while sku_sz>52 and text_width(d,sku,sku_sz,'italic')>490:sku_sz-=5
    txt(d,(1063,135),sku,sku_sz,WHITE,'italic')
    title=clean_name_for_poster(p)
    font_size,rows=fit_title(d,title,455,(48,44,40,36,32,29),max_lines=3)
    for i,row in enumerate(rows[:3]):
        txt(d,(1062,290+i*(font_size+13)),row,font_size,WHITE,'bold')
    d.rectangle((1058,497,1540,499),fill='#48AFE9')
    d.rectangle((1060,516,1540,602),fill='#086AB9')
    txt(d,(1081,538),'UK MANUFACTURER RRP',29,WHITE,'bold')
    details=prepared_price(p)
    if details:
        ex=details['secondary'].split(' EX VAT')[0]
        inc=details['primary']
        sz=128
        while sz>55 and text_width(d,inc,sz,'bold')>492:sz-=5
        txt(d,(1052,622),inc,sz,WHITE,'bold')
        txt(d,(1072,757),'INCLUDING VAT',30,'#DBF3FF','bold')
        d.rectangle((1060,814,1536,818),fill='#319DD6')
        txt(d,(1073,836),ex+' EX VAT',42,WHITE,'bold')
    else:
        txt(d,(1075,633),'PRICE',76,WHITE,'bold')
        txt(d,(1070,736),'NOT VERIFIED',44,WHITE,'bold')
        txt(d,(1069,835),'REVIEW RRP BEFORE PUBLICATION',19,'#D9EEFF','bold')
    txt(d,(1574,947),'DRAFT · CHECK CURRENT PRICING',16,'#A9D2EB','bold',anchor='ra')
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
