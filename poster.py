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
    """Dark, campaign-led portrait advert. Real product pixels, no invented workshop scene."""
    W,H=1240,1510
    im=Image.new('RGB',(W,H),'#071A31')
    gradient_box(im,(0,0,W,570),'#061C34','#075593',vertical=False)
    d=ImageDraw.Draw(im)
    d.polygon([(1050,0),(1240,0),(1094,570),(912,570)],fill='#0674B8')
    d.polygon([(1144,0),(1240,0),(1189,360),(1080,360)],fill='#0D94D0')
    logo(d,54,28,75)
    line(d,(760,75),(760,151),'#6FADD9',3)
    txt(d,(790,68),str(p.get('part','')),91,WHITE,'italic')
    line(d,(54,182),(1185,182),'#6F9CC0',2)
    first,second=choose_headline(p)
    for idx,(head,colour) in enumerate([(first,WHITE),(second,'#36BDFC')]):
        sz=71
        if text_width(d,head,sz,'italic')>1130:sz=62
        txt(d,(54,220+idx*91),head,sz,colour,'italic')
    name=clean_name_for_poster(p)
    title_size,rows=fit_title(d,name,1100,(48,44,40,36,33),max_lines=2)
    for i,row in enumerate(rows):
        txt(d,(58,418+i*(title_size+9)),row,title_size,WHITE,'bold')
    # Split the stage into a graphic sales column and an oversized official photo.
    d.rectangle((35,570,1205,1234),fill='#ECF3F8')
    d.rectangle((52,588,450,1217),fill='#0A3459')
    d.rectangle((470,588,1190,1217),fill=WHITE)
    d=ImageDraw.Draw(im)
    txt(d,(78,615),'WHY IT WORKS',30,'#54C7FB','bold')
    points=short_features(p,3)
    if not points:
        points=[short_purpose(p)]
    y=687
    for i,claim in enumerate(points[:3]):
        if y>1150:break
        d.rectangle((78,y+8,91,y+22),fill=CYAN)
        y=text_rows(d,claim,108,y,314,25,4,'bold',WHITE,1.2)+37
    # Keep the manufacturer photo completely accurate. The backdrop is graphic,
    # not a fabricated photo of the tool being used.
    photo=manufacturer_photo(blob)
    photo_safe(im,photo,(476,596,1184,1210),cutout=False)
    d=ImageDraw.Draw(im)
    d.rectangle((0,1234,W,1457),fill='#0569B8')
    d.polygon([(0,1234),(786,1234),(690,1457),(0,1457)],fill='#094675')
    txt(d,(49,1269),'PROFESSIONAL WORKSHOP',27,'#ABDFFA','bold')
    txt(d,(47,1309),'LASER TOOLS',48,WHITE,'italic')
    txt(d,(48,1376),'ENGINEERED FOR THE JOB.',26,WHITE,'bold')
    price=prepared_price(p)
    if price:
        txt(d,(835,1255),'UK RRP',31,'#D8F1FF','bold')
        amount=price['primary']
        size=68 if len(amount)<=10 else 55
        txt(d,(825,1300),amount,size,WHITE,'bold')
        txt(d,(825,1386),price['basis'],21,WHITE,'bold')
    else:
        txt(d,(810,1300),'SEE PRODUCT',42,WHITE,'bold')
        txt(d,(811,1353),'DETAILS',42,WHITE,'bold')
    d.rectangle((0,1457,W,H),fill='#061A2E')
    txt(d,(49,1472),'lasertools.co.uk',25,WHITE,'bold')
    txt(d,(1186,1478),'DRAFT · VERIFY CLAIMS AND RRP',17,'#A9CBE1','bold',anchor='ra')
    return png(im)


def render_price(p,blob):
    """Bright retailer price card — landscape, intentionally unlike the dark hero."""
    W,H=1600,1000
    im=Image.new('RGB',(W,H),'#FAFCFE')
    d=ImageDraw.Draw(im)
    gradient_box(im,(0,0,W,142),'#066EB8','#003D76',vertical=False)
    d=ImageDraw.Draw(im)
    logo(d,48,13,64)
    d.rectangle((1272,25,1277,118),fill='#66C4F7')
    txt(d,(1302,35),str(p.get('part','')),75,WHITE,'italic')
    d.rectangle((0,142,1600,156),fill=CYAN)
    title=clean_name_for_poster(p)
    size,rows=fit_title(d,title,1470,(60,53,47,42,38,34),max_lines=2)
    for i,row in enumerate(rows):
        txt(d,(58,183+i*(size+6)),row,size,NAVY,'bold')
    top=max(340,183+len(rows)*(size+6)+26)
    # Full-sized genuine product photography on clean neutral white.
    d.rectangle((49,top,847,838),fill='#EEF4F8')
    d.polygon([(49,top),(307,top),(49,top+246)],fill='#DDECF7')
    photo=manufacturer_photo(blob)
    photo_safe(im,photo,(70,top+10,825,820),cutout=False)
    d=ImageDraw.Draw(im)
    # Price is the primary graphic, not a small badge.
    d.rectangle((879,top,1555,837),fill='#005BA6')
    d.rectangle((879,top,1555,top+14),fill=CYAN)
    txt(d,(916,top+40),'MANUFACTURER UK RRP',31,'#DDF5FF','bold')
    d.rectangle((912,top+95,1523,top+97),fill='#4CB2EF')
    data=prepared_price(p)
    if data:
        amount=data['primary']
        amount_size=111 if len(amount)<=9 else 88
        if text_width(d,amount,amount_size,'bold')>610:amount_size=75
        txt(d,(910,top+128),amount,amount_size,WHITE,'bold')
        txt(d,(917,top+265),data['basis'],31,WHITE,'bold')
        txt(d,(917,top+310),data['secondary'],27,'#D5F1FF')
    else:
        txt(d,(913,top+130),'RRP',82,WHITE,'bold')
        txt(d,(917,top+238),'NOT VERIFIED',49,WHITE,'bold')
        txt(d,(918,top+313),'DO NOT PUBLISH AS PRICED',22,'#FFF1D0','bold')
    txt(d,(915,top+390),'CHECK CURRENT RRP BEFORE USE',21,'#EAF8FF','bold')
    # Thin benefit strip rather than another technical summary.
    d.rectangle((0,857,W,1000),fill='#0B2B4A')
    firsts=short_features(p,2)
    for i in range(2):
        x=55+i*780
        d.rectangle((x,884,x+6,953),fill=CYAN)
        text_rows(d,firsts[i] if i<len(firsts) else short_purpose(p),x+25,882,720,25,3,'bold',WHITE,1.2)
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
    price=prepared_price(p)
    price_line=(f"Manufacturer RRP: {price['primary']} ({price['basis']}). "
                f"{price['source_basis']}") if price else                'Manufacturer RRP: Not verified from retrieved source; do not publish an assumed price.'
    return f'''LASER TOOLS {p.get('part')} — {product_name(p)}\n\nPROMOTIONAL POSTER HEADLINE (DRAFT)\n{head}\n\nShort customer points:\n{chr(10).join('• '+v for v in key)}\n\nTECHNICAL POSTER\nUse only the verified description, source features and specs in the attached source record. No inferred measurements or diagrams.\n\nRRP / SALES POSTER\n{price_line}\n\nPRODUCT SOURCE\n{p.get('source','')}\n\nREVIEW REQUIRED: price, product image rights, application wording, technical correctness and brand approval.\n'''
