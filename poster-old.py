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
    img=trim_photo(photo).copy();img.thumbnail((max(1,x1-x0-padding*2),max(1,y1-y0-padding*2)),Image.Resampling.LANCZOS)
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
    """Return display amounts only when the manufacturer's record contains a price.
    VAT-inclusive amount is derived *only* from an explicitly VAT-exclusive price.
    """
    raw=str(p.get('price') or '').strip()
    match=re.search(r'£\s*([\d,]+(?:\.\d{2})?)',raw)
    if not match:return None
    try: amount=Decimal(match.group(1).replace(',',''))
    except Exception:return None
    text=raw.lower()
    fmt=lambda v:f'£{v:,.2f}'
    if any(t in text for t in ('excluding vat','plus vat','exc vat','ex vat','excl vat')):
        # UK standard-rate goods: show explicit derivation, not a manufacturer quotation.
        inc=(amount*Decimal('1.20')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        return {'primary':fmt(inc),'basis':'INC VAT @ 20%','secondary':f'{fmt(amount)} ex VAT',
                'source_basis':'Manufacturer RRP excluding VAT; inclusive amount calculated at 20%.'}
    if any(t in text for t in ('including vat','inc vat','inc. vat','incl vat')):
        return {'primary':fmt(amount),'basis':'INC VAT','secondary':'MANUFACTURER RRP',
                'source_basis':'Manufacturer RRP including VAT.'}
    return {'primary':fmt(amount),'basis':'VAT BASIS UNVERIFIED','secondary':'CHECK SOURCE BEFORE USE',
            'source_basis':'VAT basis not explicit in retrieved official listing.'}

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

def render_hero(p,blob):
    """Reference 2: high-impact bright sales advert, huge product with price badge."""
    W,H=1240,1510
    im=Image.new('RGB',(W,H),WHITE)
    gradient_box(im,(0,0,W,172),'#086FB8','#074987',vertical=False)
    d=ImageDraw.Draw(im)
    logo(d,55,12,76)
    d.rectangle((970,41,974,133),fill=WHITE)
    txt(d,(1000,38),str(p.get('part','')),79,WHITE,'italic')
    name=clean_name_for_poster(p)
    sz,namerows=fit_title(d,name,1138,(76,69,63,57,52,47,42),max_lines=3)
    title_y=204
    for i,t in enumerate(namerows):txt(d,(52,title_y+i*(sz+10)),t,sz,'#090F18','bold')
    # One explicit product-use claim is better than multiple generic invented promises.
    byline_y=title_y+len(namerows)*(sz+10)+20
    byline=callout_feature(p,0,148)
    d.rectangle((56,byline_y+4,64,byline_y+91),fill=BLUE)
    ending=text_rows(d,byline,90,byline_y,1080,31,3,fill='#111E2D',leading=1.16)
    # Large real product photograph is the star.
    photo_top=max(500,ending+28)
    photo_bottom=1137
    d.rectangle((20,photo_top,1220,photo_bottom),fill='#FCFDFE')
    photo=manufacturer_photo(blob)
    # Keep image dominant and allow a secondary cropped usage in the distinct other posters.
    photo_safe(im,photo,(50,photo_top+15,1172,photo_bottom-14),cutout=True)
    d=ImageDraw.Draw(im)
    # Reference price badge overlaps photo only, very different from technical sheet.
    price=prepared_price(p)
    if price:
        badge=(761,932,1220,1137)
        d.polygon([(badge[0]+32,badge[1]),(badge[2],badge[1]),(badge[2],badge[3]),(badge[0],badge[3])],fill='#085BA6')
        txt(d,(824,956),'RRP',43,WHITE,'bold')
        v=price['primary']
        fs=79 if len(v)<10 else 65
        txt(d,(812,1005),v,fs,WHITE,'bold')
        txt(d,(1193,1084),price['basis'],21,WHITE,'bold',anchor='ra')
        txt(d,(1186,1113),price['secondary'],17,'#DFEFFF',anchor='ra')
    else:
        # Missing price must never trigger a fabricated price or misleading RRP badge.
        d.polygon([(877,1010),(1220,1010),(1220,1137),(842,1137)],fill=BLUE)
        txt(d,(913,1029),'LASER',34,WHITE,'italic')
        txt(d,(906,1072),f'PART NO. {p.get("part","")}',26,WHITE,'bold')
    # Two readable benefit panels from different genuine feature claims.
    line(d,(35,1165),(1205,1165),BLUE,3)
    feat=feature_text(p,3)
    for i in range(2):
        x=45+i*595
        if i>0: d.rectangle((616,1191,620,1365),fill=BLUE)
        d.rectangle((x,1190,x+554,1362),fill='#F5F8FB')
        txt(d,(x+20,1208),f'{i+1:02}  KEY BENEFIT',23,BLUE,'bold')
        text_rows(d,feat[i+1] if i+1<len(feat) else (feat[i] if i<len(feat) else short_purpose(p)),x+20,1250,514,25,4,'bold',INK,1.12)
    d.rectangle((0,1425,W,H),fill=NAVY)
    txt(d,(40,1448),'LASER TOOLS',32,WHITE,'italic')
    txt(d,(1200,1453),'lasertools.co.uk',25,WHITE,'bold',anchor='ra')
    txt(d,(41,1487),'PRODUCT MARKETING DRAFT • SOURCE CLAIMS MUST BE APPROVED',14,'#C8DDEE')
    return png(im)

def render_price(p,blob):
    """Third style: a landscape price-first retailer POS graphic, distinct from both references."""
    W,H=1600,1000
    im=Image.new('RGB',(W,H),WHITE)
    gradient_box(im,(0,0,705,H),'#102F52','#041A32')
    d=ImageDraw.Draw(im)
    logo(d,45,32,69)
    line(d,(53,169),(621,169),'#477EA7',2)
    txt(d,(54,198),'LASER PART NUMBER',29,'#B3DAF6','bold')
    txt(d,(52,240),str(p.get('part','')),107,WHITE,'italic')
    d.rectangle((54,384,625,389),fill=CYAN)
    txt(d,(54,415),'MANUFACTURER',25,'#B9E2F8','bold')
    txt(d,(54,448),'RECOMMENDED RETAIL PRICE',25,'#B9E2F8','bold')
    pr=prepared_price(p)
    if pr:
        size=97 if len(pr['primary'])<=10 else 78
        txt(d,(48,516),pr['primary'],size,WHITE,'bold')
        txt(d,(57,637),pr['basis'],25,'#9FE2FE','bold')
        txt(d,(57,676),pr['secondary'],24,'#E0F2FC')
    else:
        txt(d,(52,523),'PRICE',86,WHITE,'bold')
        txt(d,(52,612),'ON REQUEST',49,'#ABDBFC','bold')
        txt(d,(56,684),'No verified RRP supplied',23,'#D4E9F7')
    d.rectangle((55,765,625,892),fill='#0A5B95')
    txt(d,(73,786),'TRADE PRODUCT SPOTLIGHT',24,WHITE,'bold')
    text_rows(d,callout_feature(p,0,76),73,824,521,20,2,fill=WHITE,leading=1.16)
    # Photo panel with a clipped photo from the genuine supplied official image.
    d.rectangle((711,0,W,885),fill='#EDF2F6')
    photo=manufacturer_photo(blob)
    photo_safe(im,photo,(732,80,1569,856),cutout=True)
    d=ImageDraw.Draw(im)
    d.rectangle((700,0,W,33),fill=BLUE)
    d.rectangle((705,862,W,1000),fill=WHITE)
    name=clean_name_for_poster(p)
    size,names=fit_title(d,name,820,(40,37,33,29,25),max_lines=2)
    for i,row in enumerate(names):txt(d,(740,881+i*size*1.1),row,size,NAVY,'bold')
    d.rectangle((0,940,700,1000),fill=BLUE)
    txt(d,(52,957),'PROMOTIONAL PRICE CARD  •  REVIEW BEFORE PUBLISHING',18,WHITE,'bold')
    return png(im)


def create_posters(p,blob):
    if not blob:raise ValueError('A verified manufacturer product image is required.')
    return {
       'Hero':render_hero(p,blob),
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
    value,vat=price_parts(p)
    price_line=f'Manufacturer RRP: {value} ({vat})' if value else 'Manufacturer RRP: Not verified from retrieved source; do not publish an assumed price.'
    return f'''LASER TOOLS {p.get('part')} — {product_name(p)}\n\nPROMOTIONAL POSTER HEADLINE (DRAFT)\n{head}\n\nShort customer points:\n{chr(10).join('• '+v for v in key)}\n\nTECHNICAL POSTER\nUse only the verified description, source features and specs in the attached source record. No inferred measurements or diagrams.\n\nRRP / SALES POSTER\n{price_line}\n\nPRODUCT SOURCE\n{p.get('source','')}\n\nREVIEW REQUIRED: price, product image rights, application wording, technical correctness and brand approval.\n'''"""Deterministic Laser-style marketing art from an authentic product photograph.
No AI-generated product images, schematics or technical measurements.
"""
from __future__ import annotations
import io, textwrap
from PIL import Image,ImageDraw,ImageFont,ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor"""Laser Product Studio — three distinctly art-directed poster formats.

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
    img=trim_photo(photo).copy();img.thumbnail((max(1,x1-x0-padding*2),max(1,y1-y0-padding*2)),Image.Resampling.LANCZOS)
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
    """Return display amounts only when the manufacturer's record contains a price.
    VAT-inclusive amount is derived *only* from an explicitly VAT-exclusive price.
    """
    raw=str(p.get('price') or '').strip()
    match=re.search(r'£\s*([\d,]+(?:\.\d{2})?)',raw)
    if not match:return None
    try: amount=Decimal(match.group(1).replace(',',''))
    except Exception:return None
    text=raw.lower()
    fmt=lambda v:f'£{v:,.2f}'
    if any(t in text for t in ('excluding vat','plus vat','exc vat','ex vat','excl vat')):
        # UK standard-rate goods: show explicit derivation, not a manufacturer quotation.
        inc=(amount*Decimal('1.20')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        return {'primary':fmt(inc),'basis':'INC VAT @ 20%','secondary':f'{fmt(amount)} ex VAT',
                'source_basis':'Manufacturer RRP excluding VAT; inclusive amount calculated at 20%.'}
    if any(t in text for t in ('including vat','inc vat','inc. vat','incl vat')):
        return {'primary':fmt(amount),'basis':'INC VAT','secondary':'MANUFACTURER RRP',
                'source_basis':'Manufacturer RRP including VAT.'}
    return {'primary':fmt(amount),'basis':'VAT BASIS UNVERIFIED','secondary':'CHECK SOURCE BEFORE USE',
            'source_basis':'VAT basis not explicit in retrieved official listing.'}

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

def render_hero(p,blob):
    """Reference 2: high-impact bright sales advert, huge product with price badge."""
    W,H=1240,1510
    im=Image.new('RGB',(W,H),WHITE)
    gradient_box(im,(0,0,W,172),'#086FB8','#074987',vertical=False)
    d=ImageDraw.Draw(im)
    logo(d,55,12,76)
    d.rectangle((970,41,974,133),fill=WHITE)
    txt(d,(1000,38),str(p.get('part','')),79,WHITE,'italic')
    name=clean_name_for_poster(p)
    sz,namerows=fit_title(d,name,1138,(76,69,63,57,52,47,42),max_lines=3)
    title_y=204
    for i,t in enumerate(namerows):txt(d,(52,title_y+i*(sz+10)),t,sz,'#090F18','bold')
    # One explicit product-use claim is better than multiple generic invented promises.
    byline_y=title_y+len(namerows)*(sz+10)+20
    byline=callout_feature(p,0,148)
    d.rectangle((56,byline_y+4,64,byline_y+91),fill=BLUE)
    ending=text_rows(d,byline,90,byline_y,1080,31,3,fill='#111E2D',leading=1.16)
    # Large real product photograph is the star.
    photo_top=max(500,ending+28)
    photo_bottom=1137
    d.rectangle((20,photo_top,1220,photo_bottom),fill='#FCFDFE')
    photo=manufacturer_photo(blob)
    # Keep image dominant and allow a secondary cropped usage in the distinct other posters.
    photo_safe(im,photo,(50,photo_top+15,1172,photo_bottom-14),cutout=True)
    d=ImageDraw.Draw(im)
    # Reference price badge overlaps photo only, very different from technical sheet.
    price=prepared_price(p)
    if price:
        badge=(761,932,1220,1137)
        d.polygon([(badge[0]+32,badge[1]),(badge[2],badge[1]),(badge[2],badge[3]),(badge[0],badge[3])],fill='#085BA6')
        txt(d,(824,956),'RRP',43,WHITE,'bold')
        v=price['primary']
        fs=79 if len(v)<10 else 65
        txt(d,(812,1005),v,fs,WHITE,'bold')
        txt(d,(1193,1084),price['basis'],21,WHITE,'bold',anchor='ra')
        txt(d,(1186,1113),price['secondary'],17,'#DFEFFF',anchor='ra')
    else:
        # Missing price must never trigger a fabricated price or misleading RRP badge.
        d.polygon([(877,1010),(1220,1010),(1220,1137),(842,1137)],fill=BLUE)
        txt(d,(913,1029),'LASER',34,WHITE,'italic')
        txt(d,(906,1072),f'PART NO. {p.get("part","")}',26,WHITE,'bold')
    # Two readable benefit panels from different genuine feature claims.
    line(d,(35,1165),(1205,1165),BLUE,3)
    feat=feature_text(p,3)
    for i in range(2):
        x=45+i*595
        if i>0: d.rectangle((616,1191,620,1365),fill=BLUE)
        d.rectangle((x,1190,x+554,1362),fill='#F5F8FB')
        txt(d,(x+20,1208),f'{i+1:02}  KEY BENEFIT',23,BLUE,'bold')
        text_rows(d,feat[i+1] if i+1<len(feat) else (feat[i] if i<len(feat) else short_purpose(p)),x+20,1250,514,25,4,'bold',INK,1.12)
    d.rectangle((0,1425,W,H),fill=NAVY)
    txt(d,(40,1448),'LASER TOOLS',32,WHITE,'italic')
    txt(d,(1200,1453),'lasertools.co.uk',25,WHITE,'bold',anchor='ra')
    txt(d,(41,1487),'PRODUCT MARKETING DRAFT • SOURCE CLAIMS MUST BE APPROVED',14,'#C8DDEE')
    return png(im)

def render_price(p,blob):
    """Third style: a landscape price-first retailer POS graphic, distinct from both references."""
    W,H=1600,1000
    im=Image.new('RGB',(W,H),WHITE)
    gradient_box(im,(0,0,705,H),'#102F52','#041A32')
    d=ImageDraw.Draw(im)
    logo(d,45,32,69)
    line(d,(53,169),(621,169),'#477EA7',2)
    txt(d,(54,198),'LASER PART NUMBER',29,'#B3DAF6','bold')
    txt(d,(52,240),str(p.get('part','')),107,WHITE,'italic')
    d.rectangle((54,384,625,389),fill=CYAN)
    txt(d,(54,415),'MANUFACTURER',25,'#B9E2F8','bold')
    txt(d,(54,448),'RECOMMENDED RETAIL PRICE',25,'#B9E2F8','bold')
    pr=prepared_price(p)
    if pr:
        size=97 if len(pr['primary'])<=10 else 78
        txt(d,(48,516),pr['primary'],size,WHITE,'bold')
        txt(d,(57,637),pr['basis'],25,'#9FE2FE','bold')
        txt(d,(57,676),pr['secondary'],24,'#E0F2FC')
    else:
        txt(d,(52,523),'PRICE',86,WHITE,'bold')
        txt(d,(52,612),'ON REQUEST',49,'#ABDBFC','bold')
        txt(d,(56,684),'No verified RRP supplied',23,'#D4E9F7')
    d.rectangle((55,765,625,892),fill='#0A5B95')
    txt(d,(73,786),'TRADE PRODUCT SPOTLIGHT',24,WHITE,'bold')
    text_rows(d,callout_feature(p,0,76),73,824,521,20,2,fill=WHITE,leading=1.16)
    # Photo panel with a clipped photo from the genuine supplied official image.
    d.rectangle((711,0,W,885),fill='#EDF2F6')
    photo=manufacturer_photo(blob)
    photo_safe(im,photo,(732,80,1569,856),cutout=True)
    d=ImageDraw.Draw(im)
    d.rectangle((700,0,W,33),fill=BLUE)
    d.rectangle((705,862,W,1000),fill=WHITE)
    name=clean_name_for_poster(p)
    size,names=fit_title(d,name,820,(40,37,33,29,25),max_lines=2)
    for i,row in enumerate(names):txt(d,(740,881+i*size*1.1),row,size,NAVY,'bold')
    d.rectangle((0,940,700,1000),fill=BLUE)
    txt(d,(52,957),'PROMOTIONAL PRICE CARD  •  REVIEW BEFORE PUBLISHING',18,WHITE,'bold')
    return png(im)


def create_posters(p,blob):
    if not blob:raise ValueError('A verified manufacturer product image is required.')
    return {
       'Hero':render_hero(p,blob),
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
    value,vat=price_parts(p)
    price_line=f'Manufacturer RRP: {value} ({vat})' if value else 'Manufacturer RRP: Not verified from retrieved source; do not publish an assumed price.'
    return f'''LASER TOOLS {p.get('part')} — {product_name(p)}\n\nPROMOTIONAL POSTER HEADLINE (DRAFT)\n{head}\n\nShort customer points:\n{chr(10).join('• '+v for v in key)}\n\nTECHNICAL POSTER\nUse only the verified description, source features and specs in the attached source record. No inferred measurements or diagrams.\n\nRRP / SALES POSTER\n{price_line}\n\nPRODUCT SOURCE\n{p.get('source','')}\n\nREVIEW REQUIRED: price, product image rights, application wording, technical correctness and brand approval.\n'''
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
