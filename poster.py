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

def customer_features(p,n=5,maxlen=118):
    """Select compact, complete English sales facts; never paste catalogue size dumps.

    Long comma-separated kit-content inventories are kept in the audited source
    record but excluded from customer artwork. Statements are only shortened
    at genuine sentence/clause boundaries, never completed by invented wording.
    """
    out=[]
    for raw in facts(p):
        full=' '.join(raw.split()).strip(' •-')
        if not full:continue
        number_count=len(re.findall(r'\b\d+(?:[.,]\d+)?(?:mm|Nm|W|psi)?\b',full,re.I))
        if (len(full)>185 or (number_count>=7 and full.count(',')>=4)):
            continue
        # Split only on a known sentence or clause boundary, not arbitrarily
        # cutting "suitable for" vehicle lists into inaccurate claims.
        choices=[full]
        choices.extend(re.split(r'(?<=[.!?])\s+',full))
        choices.extend(re.split(r';\s*',full))
        phrase=next((v.strip(' .;') for v in choices if 16<=len(v.strip())<=maxlen),None)
        if not phrase:continue
        phrase=phrase[0].upper()+phrase[1:]
        if phrase.casefold() not in {v.casefold() for v in out}:
            out.append(phrase)
        if len(out)>=n:break
    return out

def short_features(p,n=3):
    """Short, source-true features; omit rather than print fragments or micro-text."""
    return customer_features(p,n,maxlen=91)


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
    return customer_features(p,amount,maxlen=125)

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
    """Readable product purpose with only manufacturer-supported English text."""
    content=' '.join(str(p.get('description') or '').split())
    if not content:
        concise=customer_features(p,1,145)
        return concise[0] if concise else 'See the official product information for application and operating details.'
    clauses=re.split(r'(?<=[.!?])\s+',content)
    # Keep the first coherent, manageable sentence instead of a miniature
    # paragraph that is unreadable when printed.
    line=next((v for v in clauses if 24<=len(v)<=198),None)
    if line:return line
    first=clauses[0]
    if len(first)<=210:return first
    # Cut at a clause boundary only, otherwise use a safe generic reference.
    chunks=re.split(r';\s+|,\s+(?=(?:with|and|for|which)\b)',first)
    for chunk in chunks:
        if 24<=len(chunk)<=195:return chunk.strip(' ,;')+'.'
    concise=customer_features(p,1,145)
    return concise[0] if concise else 'Refer to the official manufacturer product information.'


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

def technical_section(d,x,y,w,label,height=51):
    """Cobalt header with white lettering for the 9395-style engineering panels."""
    d.rectangle((x,y,x+w,y+height),fill='#0868AB')
    d.rectangle((x,y,x+8,y+height),fill='#2A99D7')
    txt(d,(x+19,y+10),label.upper(),26,WHITE,'bold')


def technical_card(im,box,background='#082748',border='#2075AC'):
    d=ImageDraw.Draw(im)
    x0,y0,x1,y1=box
    d.rectangle((x0,y0,x1,y1),fill=background,outline=border,width=3)
    return d


def technical_layout_mode(p):
    """Choose a *visual* density by product family and independent usable facts.

    Common small hand-tool sets should not become microscopic six-panel
    catalogues merely because the UK site publishes lots of specification rows.
    """
    title=product_name(p).lower()
    features=customer_features(p,6,125)
    specs=best_specs(p,7)
    simple=r'\b(?:ratchets?|spanners?|screwdrivers?|sockets?|pliers?|torx|bit sets?|hand tools?)\b'
    complex_product=r'(?:wheel bearing|bearing kit|hydraulic press|bearing puller|timing kit|gearbox|induction heater)'
    if re.search(simple,title) and not re.search(complex_product,title):
        return 'light'
    if len(features)>=4 and len(specs)>=4:
        return 'dense'
    if re.search(complex_product,title) and len(features)>=3 and len(specs)>=2:
        return 'dense'
    if len(specs)>=2 and len(features)>=2:
        return 'medium'
    if len(features)>=4 and len(specs)>=1:
        return 'medium'
    return 'light'


def technical_copy_rows(d,content,width,height,sizes=(37,34,31,29,26,24),style='regular'):
    """Fit complete source-backed sentences without arbitrary truncated claims."""
    phrase=' '.join(str(content or '').split())
    for size in sizes:
        count=max(1,int(height/(size*1.35)))
        result=lines(d,phrase,width,size,style,max_lines=count)
        if result and not result[-1].endswith('…'):
            return size,result
    return None,[]


def technical_body(d,content,x,y,width,height,sizes=(37,34,31,28,25),
                   colour=WHITE,style='regular',center=False):
    size,rows=technical_copy_rows(d,content,width,height,sizes,style)
    if size is None:
        # Do not publish a cut-off spec. Source text remains in the record.
        return False
    used=len(rows)*round(size*1.35)
    if center:y+=max(0,(height-used)//2)
    for row in rows:
        txt(d,(x,y),row,size,colour,style)
        y+=round(size*1.35)
    return True


def technical_masthead(im,p,mode):
    """Shared technical brand system, distinct from promotional/RRP posters."""
    W,H=im.size
    gradient_box(im,(0,0,W,H),'#072847','#031528')
    gradient_box(im,(15,15,1265,139),'#075EAD','#03294D',vertical=False)
    d=ImageDraw.Draw(im)
    d.rectangle((15,15,1265,22),fill='#39A8E4')
    logo(d,45,15,76)
    d.line((1002,35,1002,116),fill='#39B5EC',width=3)
    sku=str(p.get('part','')).strip()
    sku_size=80
    while sku_size>51 and text_width(d,sku,sku_size,'italic')>218:
        sku_size-=4
    txt(d,(1031,35),sku,sku_size,WHITE,'italic')
    title=clean_name_for_poster(p).upper()
    title_size,rows=fit_title(d,title,1190,(56,53,50,46,43,39,35),max_lines=2)
    for idx,line in enumerate(rows[:2]):
        txt(d,(34,158+idx*(title_size+9)),line,title_size,WHITE,'bold')
    # For simple tools show a useful category, not an irrelevant
    # "confirm vehicle applications" placeholder.
    app=application_from_record(p)
    has_application=bool(app) and not app.startswith('Refer to the official') and len(app)<132
    if has_application:
        technical_body(d,app,36,276,1175,52,sizes=(23,22,20),colour='#D1E8F8')
    elif mode=='light':
        txt(d,(38,276),'PROFESSIONAL WORKSHOP TOOL',23,'#A7DDF7','bold')
    else:
        txt(d,(38,276),'PRODUCT INFORMATION  /  TECHNICAL OVERVIEW',23,'#A7DDF7','bold')
    d.rectangle((31,333,1249,338),fill='#2296D5')


def technical_feature_tiles(im,p,y0,y1,features,specs):
    """Expand 1–3 meaningful facts to the full available page width."""
    items=[]
    for f in features:
        if f not in items:items.append(f)
        if len(items)>=3:break
    # If there is no English bullet, show short verified spec pairs instead.
    if not items:
        items=[f'{k}: {v}' for k,v in specs[:3] if len(str(k))+len(str(v))<88]
    if not items:
        return 0
    count=len(items)
    gutter=16
    left,right=31,1249
    panel_width=(right-left-(count-1)*gutter)/count
    for idx,detail in enumerate(items):
        x0=round(left+idx*(panel_width+gutter))
        x1=round(x0+panel_width)
        technical_card(im,(x0,y0,x1,y1),background='#0D3357',border='#1D80B8')
        d=ImageDraw.Draw(im)
        technical_section(d,x0,y0,x1-x0,f'FEATURE {idx+1:02d}',height=52)
        pad=27
        usable_width=x1-x0-2*pad
        sizes=((41,38,34,31,28,25) if count==1
               else (35,32,29,27,24) if count==2
               else (31,28,25,23,21))
        if not technical_body(d,detail,x0+pad,y0+83,usable_width,y1-y0-112,
                              sizes=sizes,center=True):
            technical_body(d,detail,x0+pad,y0+83,usable_width,y1-y0-111,
                           sizes=(21,20,19))
    return count


def add_distributor_badge(im, distributor_brand, rect):
    """Add an authentic distributor logo to a white co-brand badge.

    Do not edit, redraw, stretch, colorise or invent the customer's logo.
    Laser stays primary; the dealer logo is a secondary sign-off.
    """
    if not distributor_brand:
        return False
    from brand_assets import get_brand_image
    original=get_brand_image(distributor_brand)
    if original is None:
        return False
    d=ImageDraw.Draw(im)
    x0,y0,x1,y1=[int(i) for i in rect]
    if x1<=x0 or y1<=y0:
        return False
    d.rounded_rectangle((x0,y0,x1,y1),radius=13,fill=WHITE,
                        outline='#C7DDEB',width=3)
    iw=max(1,x1-x0-28)
    ih=max(1,y1-y0-18)
    fitted=ImageOps.contain(original.convert('RGB'),(iw,ih),Image.Resampling.LANCZOS)
    cx=x0+(x1-x0-fitted.width)//2
    cy=y0+(y1-y0-fitted.height)//2
    im.paste(fitted,(cx,cy))
    return True


def render_technical(p,blob,application_blob=None,distributor_brand=None):
    """Adaptive navy technical artwork: LIGHT, MEDIUM, DENSE.

    - LIGHT: larger real photo and expanded content; no empty spec boxes
    - MEDIUM: comfortable two-panel overview, features and core specifications
    - DENSE: 9395-style technical sheet with multiple factual sections
    """
    W,H=1280,1590
    im=Image.new('RGB',(W,H),'#031B34')
    mode=technical_layout_mode(p)
    technical_masthead(im,p,mode)
    d=ImageDraw.Draw(im)
    photo=manufacturer_photo(blob)
    features=customer_features(p,6,125)
    specs=best_specs(p,7)
    purpose=short_purpose(p)

    if mode=='light':
        # Spacious, product-led hand-tool sheet. A simple ratchet should fill
        # the page without fabricated technical measurements or empty grids.
        has_tiles=bool(features or specs)
        photo_end=1007 if has_tiles else 1195
        technical_card(im,(31,356,1249,photo_end),background='#EEF4FA')
        contain_photo(im,photo,(41,366,1239,photo_end-10),
                      padding=42 if has_tiles else 50,background=WHITE)
        purpose_y=1026 if has_tiles else 1214
        purpose_end=1249 if has_tiles else 1492
        technical_card(im,(31,purpose_y,1249,purpose_end),background='#092B4D')
        d=ImageDraw.Draw(im)
        technical_section(d,31,purpose_y,1218,'PRODUCT OVERVIEW',height=53)
        technical_body(d,purpose,63,purpose_y+77,1145,purpose_end-purpose_y-94,
                       sizes=(39,36,33,30,27,24),center=True)
        if has_tiles:
            technical_feature_tiles(im,p,1267,1492,features,specs)
    elif mode=='medium':
        # A product with some specs but no huge list: readable hero image,
        # purpose and two large independently useful information panels.
        technical_card(im,(31,356,809,1011),background='#EBF3F9')
        contain_photo(im,photo,(41,366,799,1001),padding=36,background=WHITE)
        technical_card(im,(831,356,1249,1011),background='#0A2B4B')
        d=ImageDraw.Draw(im)
        technical_section(d,831,356,418,'PRODUCT PURPOSE')
        technical_body(d,purpose,856,440,362,534,
                       sizes=(35,32,30,28,26,23),center=True)
        tech_items=features[:4]
        technical_card(im,(31,1031,632,1492),background='#0C3154')
        d=ImageDraw.Draw(im)
        technical_section(d,31,1031,601,'KEY FEATURES')
        yy=1107
        for fact in tech_items:
            d.ellipse((49,yy+8,62,yy+21),fill='#3EAEE8')
            size,rr=technical_copy_rows(d,fact,530,88,
                                        sizes=(29,27,25,23))
            if not rr:continue
            for t in rr:
                txt(d,(79,yy),t,size,WHITE)
                yy+=round(size*1.3)
            yy+=22
            if yy>1464:break
        technical_card(im,(653,1031,1249,1492),background='#0C3154')
        d=ImageDraw.Draw(im)
        if specs:
            technical_section(d,653,1031,596,'PRODUCT SPECIFICATIONS')
            for i,(key,val) in enumerate(specs[:5]):
                yy=1111+i*74
                if yy+60>1481:break
                if i%2==0:d.rectangle((673,yy-9,1228,yy+53),fill='#154061')
                txt(d,(696,yy),str(key).upper(),20,'#71C5F0','bold')
                technical_body(d,str(val),695,yy+27,500,35,
                               sizes=(25,22,20))
        else:
            technical_section(d,653,1031,596,'IN THE WORKSHOP')
            if application_blob:
                try:
                    photo2=manufacturer_photo(application_blob)
                    contain_photo(im,photo2,(666,1097,1236,1479),
                                  padding=8,background=WHITE)
                except Exception:
                    technical_body(ImageDraw.Draw(im),purpose,680,1140,526,260,
                                   sizes=(32,29,27))
            else:
                technical_body(d,purpose,681,1130,531,270,
                               sizes=(32,30,28))
    else:
        # High-information specialist kit: two-column image / purpose, features,
        # real workshop photo or specifications, and supporting bottom panels.
        technical_card(im,(31,355,775,777),background='#EAF2F8')
        contain_photo(im,photo,(41,365,765,767),padding=20,background=WHITE)
        technical_card(im,(796,355,1249,777),background='#082B4C')
        d=ImageDraw.Draw(im)
        technical_section(d,796,355,453,'PRODUCT PURPOSE')
        technical_body(d,purpose,820,429,402,327,
                       sizes=(28,26,24,22,21),center=True)

        technical_card(im,(31,798,619,1248),background='#0A2C4C')
        d=ImageDraw.Draw(im)
        technical_section(d,31,798,588,'KEY FEATURES')
        yy=866
        for fact in features[:5]:
            size,rr=technical_copy_rows(d,fact,523,92,
                                        sizes=(23,22,21,20))
            if not rr:continue
            if yy+len(rr)*30+12>1235:break
            d.ellipse((50,yy+8,63,yy+21),fill='#2FA9E5')
            for v in rr:
                txt(d,(78,yy),v,size,WHITE)
                yy+=30
            yy+=13

        technical_card(im,(641,798,1249,1248),background='#0A2C4C')
        d=ImageDraw.Draw(im)
        scene_ready=False
        if application_blob:
            try:
                scene=manufacturer_photo(application_blob)
                contain_photo(im,scene,(653,861,1237,1235),
                              padding=6,background=WHITE)
                scene_ready=True
            except Exception:pass
        d=ImageDraw.Draw(im)
        technical_section(d,641,798,608,'IN THE WORKSHOP' if scene_ready
                          else 'VERIFIED TECHNICAL DATA')
        if not scene_ready:
            for i,(key,val) in enumerate(specs[:5]):
                yy=865+i*71
                if yy+61>1230:break
                if i%2==0:d.rectangle((653,yy-6,1235,yy+58),fill='#154061')
                txt(d,(671,yy),str(key).upper(),20,'#7CD2F8','bold')
                technical_body(d,str(val),671,yy+26,537,38,
                               sizes=(24,22,20))

        technical_card(im,(31,1268,619,1492),background='#0B3152')
        technical_card(im,(641,1268,1249,1492),background='#0B3152')
        d=ImageDraw.Draw(im)
        if scene_ready and specs:
            technical_section(d,31,1268,588,'KEY SPECIFICATIONS')
            yy=1337
            for key,val in specs[:3]:
                txt(d,(52,yy),str(key).upper(),20,'#74C9F2','bold')
                technical_body(d,str(val),255,yy-1,327,45,
                               sizes=(23,21,19))
                yy+=49
        else:
            technical_section(d,31,1268,588,'PRODUCT APPLICATION')
            app=application_from_record(p)
            if app.startswith('Refer to the official'):
                app=features[0] if features else purpose
            technical_body(d,app,53,1338,531,128,
                           sizes=(27,24,22,20))

        technical_section(d,641,1268,608,'WORKSHOP NOTE')
        note='Check the official fitting instructions and approved applications before use.'
        technical_body(d,note,665,1337,548,129,
                       sizes=(26,24,22))

    # A compact upper co-brand badge leaves the Laser logo and part number readable.
    add_distributor_badge(im,distributor_brand,(562,27,890,129))
    # A consistent, uncluttered footer across all three content densities.
    d=ImageDraw.Draw(im)
    d.rectangle((31,1515,1249,1557),fill='#0C477C',outline='#2A91C5',width=2)
    txt(d,(49,1526),'toolconnection.co.uk',23,WHITE,'bold')
    txt(d,(1226,1527),'LASER TOOLS  ·  REVIEW BEFORE PUBLICATION',
        15,'#C9E5F6','bold',anchor='ra')
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
    if ('tap' in title and 'die' in title) and '110' in (title+' '+corpus):
        return '110-piece metric tap and die set for workshop thread cutting'
    if 'tap' in title and 'die' in title:
        return 'Professional tap and die tools for thread cutting'
    if 'ball joint separator' in title and 'scissor' in corpus:
        return 'Controlled separation of vehicle ball joints'
    if 'ball joint separator' in title:
        return 'Separate ball joints with confidence'
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
    if 'tap' in title and 'die' in title:
        if re.search(r'\b110\s*(?:pc|pieces?|piece)\b',title+' '+known):
            output.append('110 PIECE METRIC SET')
        if 'split dies' in known:
            output.append('SPLIT DIES INCLUDED')
        if 'blow-mould' in known or 'moulded case' in known:
            output.append('STORAGE CASE INCLUDED')
    if 'split hub' in title:
        if 'double' in known:output.append('DOUBLE-ENDED DESIGN')
        if re.search(r'\b10\s*mm\b',known):output.append('10MM HEX DRIVE')
        if re.search(r'\b15\s*mm\b',known):output.append('15MM MAX OPENING')
    if 'ball joint separator' in title:
        if 'scissor' in known:output.append('SCISSOR-TYPE DESIGN')
        if re.search(r'\b31\s*mm\b',known):output.append('31MM INNER OPENING')
        if re.search(r'\b52\s*mm\b',known):output.append('52MM OUTER OPENING')
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
        for point in customer_features(p,6,maxlen=42):
            point=point.upper().strip(' .')
            if len(point)<=39 and point not in output:output.append(point)
            if len(output)>=3:break
    return output[:3]


def choose_fitted_lines(d, message, width, height, sizes, style='italic', max_lines=3,
                        line_spacing=1.13):
    """Return a fully fitting, untruncated layout or no lines.

    PIL's drawing API will happily paint underneath another panel. Every line
    must pass both width and height checks before the first pixel is painted.
    """
    phrase=' '.join(str(message or '').split())
    for size in sizes:
        rows=lines(d,phrase,width,size,style,max_lines=max_lines)
        if not rows or any(row.endswith('…') for row in rows):
            continue
        if ' '.join(rows).strip()!=phrase:
            continue
        advance=int(round(size*line_spacing))
        bbox=[d.textbbox((0,0),row,font=font(size,style)) for row in rows]
        full_height=(len(rows)-1)*advance+max(box[3] for box in bbox)
        if all(text_width(d,row,size,style)<=width for row in rows) and full_height<=height:
            return size, rows, advance
    return None, [], 0


def draw_fitted_panel_copy(d, message, x, y, width, height, sizes,
                           style='italic', colors=None, max_lines=3):
    """Center fitted words inside an explicit protected rectangle."""
    size,rows,advance=choose_fitted_lines(
        d,message,width,height,sizes,style,max_lines=max_lines)
    if size is None:
        return False
    bounds=[d.textbbox((0,0),row,font=font(size,style)) for row in rows]
    low=min(b[1] for b in bounds)
    high=max(b[3] for b in bounds)
    total=(len(rows)-1)*advance+high-low
    top=y+max(0,(height-total)//2)-low
    for i,row in enumerate(rows):
        ink=(colors[i] if colors and i<len(colors) else
             colors[-1] if colors else '#11151C')
        txt(d,(x,top+i*advance),row,size,ink,style)
    return True


def render_hero(p,blob,application_blob=None,distributor_brand=None):
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
    add_distributor_badge(im,distributor_brand,(858,28,1174,182))
    d=ImageDraw.Draw(im)

    # Huge white oblique product name banner, intentionally independent of
    # the image. Body text is never placed over the actual tool.
    d.polygon([(0,268),(1173,224),(1108,605),(0,643)],fill=WHITE)
    name=clean_name_for_poster(p).upper().replace(' - ',' ')
    # Protected white headline slab: y=288..583, x=54..1050. Using
    # measured glyph bounds avoids spilling onto the product or number tab.
    drawn=draw_fitted_panel_copy(
        d,name,54,286,1000,300,
        sizes=(92,86,80,74,68,62,56,50,44,38,32),
        style='italic',colors=['#101417','#005BAD','#005BAD'],max_lines=3)
    if not drawn:
        # Never crop a long title; a smaller manufacturer-backed display
        # name can still be paired with the full name in the technical PDF.
        short=product_name(p).upper()
        draw_fitted_panel_copy(d,short,54,286,1000,300,
                               sizes=(70,62,54,48,42,36,30,26),
                               style='italic',max_lines=4)

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
    # The white ribbon ends at y=1570. Keep actual letter pixels fully in
    # x=84..625 and y=1404..1555, regardless of title or tool category.
    if not draw_fitted_panel_copy(d,benefit,84,1401,535,154,
                                  sizes=(47,44,41,38,35,32,29,26,23),
                                  style='italic',max_lines=3):
        # Product category text is guaranteed to be grounded in the title.
        category=clean_name_for_poster(p)
        draw_fitted_panel_copy(d,category,84,1401,535,154,
                               sizes=(34,30,27,24,21,19),
                               style='italic',max_lines=3)

    # Oversized right price wedge in the artwork (not a normal UI box).
    d.polygon([(779,1295),(1200,1295),(1200,1570),(675,1570)],fill='#0059B1')
    d.polygon([(779,1295),(1200,1295),(1200,1308),(775,1308)],fill='#17A3E5')
    price=prepared_price(p)
    if price:
        ex=price['secondary'].split(' EX VAT')[0]
        inc=price['primary']
        txt(d,(838,1323),'UK RRP',43,WHITE,'italic')
        # Price stays entirely in the blue wedge; right edge x=1183.
        # Do not use x=772 plus up to 455px: that runs off the canvas.
        amount_ok=draw_fitted_panel_copy(d,ex,832,1391,343,111,
                                         sizes=(112,103,94,86,78,71,64,57,50,43,36),
                                         style='italic',colors=[WHITE],max_lines=1)
        if not amount_ok:
            txt(d,(836,1414),'SEE PRICE',38,WHITE,'italic')
        txt(d,(842,1504),'+ VAT',32,WHITE,'italic')
        txt(d,(1178,1539),inc+' INC VAT',17,'#D3EDFE','bold',anchor='ra')
    else:
        txt(d,(810,1334),'CURRENT PRICE',38,WHITE,'italic')
        txt(d,(764,1415),'ON REQUEST',57,WHITE,'italic')
        txt(d,(811,1517),'ASK YOUR DISTRIBUTOR',22,WHITE,'bold')

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
        sz,rows,step=choose_fitted_lines(
            d,point,340,67,(27,25,23,21,19,17),'italic',max_lines=2)
        if sz is None:
            continue
        full=(len(rows)-1)*step+sz
        y=1581+max(0,(68-full)//2)
        for j,row in enumerate(rows):
            width=text_width(d,row,sz,'italic')
            txt(d,(x+(400-width)//2,y+j*step),row,sz,WHITE,'italic')

    # Big brand-blue footer to echo the reference's full-width end card.
    gradient_box(im,(0,1690,W,H),'#0062B4','#003D83',vertical=False)
    d=ImageDraw.Draw(im)
    logo(d,39,1694,79)
    d.line((708,1703,681,1772),fill=WHITE,width=6)
    txt(d,(754,1717),'lasertools.co.uk',44,WHITE,'italic')
    txt(d,(1180,1780),'MARKETING DRAFT · VERIFY SOURCE, RRP & DESIGN BEFORE RELEASE',13,'#D2E9F8','bold',anchor='ra')
    return png(im)


def render_price(p,blob,distributor_brand=None):
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
    place_cutout(im,photo,(28,250,935,751))
    d=ImageDraw.Draw(im)
    # Two fast, useful buyer benefits in a white strip under the genuine photo.
    d.rectangle((38,773,938,913),fill=WHITE)
    d.rectangle((38,773,938,779),fill=BLUE)
    sales_points=short_features(p,2)
    if not sales_points:sales_points=[short_purpose(p)]
    for i,claim in enumerate(sales_points[:2]):
        xpos=56+i*441
        if i:d.rectangle((480,793,483,887),fill='#D6E4EF')
        d.rectangle((xpos,805,xpos+12,821),fill=BLUE)
        paragraph(d,claim,xpos+27,796,391,23,INK,'bold',limit=3,leading=1.2)
    txt(d,(45,931),'LASER TOOLS  ·  PRODUCT SPOTLIGHT',25,BLUE,'italic')
    txt(d,(651,937),'lasertools.co.uk',19,NAVY,'bold')
    add_distributor_badge(im,distributor_brand,(723,23,931,147))
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
    details=prepared_price(p)
    txt(d,(1081,538),'UK MANUFACTURER RRP' if details else 'PRICE ENQUIRIES',29,WHITE,'bold')
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
        txt(d,(1075,632),'PRICE',70,WHITE,'bold')
        txt(d,(1072,735),'ON REQUEST',48,WHITE,'bold')
        txt(d,(1068,839),'CONTACT YOUR DISTRIBUTOR',24,'#D9EEFF','bold')
    txt(d,(1574,947),'DRAFT · CHECK CURRENT PRICING',16,'#A9D2EB','bold',anchor='ra')
    return png(im)


def create_posters(p,blob,application_blob=None,distributor_brand=None):
    if not blob:raise ValueError('A verified manufacturer product image is required.')
    return {
       'Hero':render_hero(p,blob,application_blob,distributor_brand),
       'Technical':render_technical(p,blob,application_blob,distributor_brand),
       'Price':render_price(p,blob,distributor_brand),
    }

def create_fact_sheet_pdf(p,blob,application_blob=None,distributor_brand=None):
    # Export the exact technical poster into A4; PNG and PDF cannot contradict.
    poster=Image.open(io.BytesIO(render_technical(p,blob,application_blob,distributor_brand))).convert('RGB')
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
                f"{price['source_basis']}") if price else                'Manufacturer RRP: Not available from verified UK sources. Enquire with your distributor; never assume a price.'
    return f'''LASER TOOLS {p.get('part')} — {product_name(p)}\n\nPROMOTIONAL POSTER HEADLINE (DRAFT)\n{head}\n\nShort customer points:\n{chr(10).join('• '+v for v in key)}\n\nTECHNICAL POSTER\nUse only the verified description, source features and specs in the attached source record. No inferred measurements or diagrams.\n\nRRP / SALES POSTER\n{price_line}\n\nPRODUCT SOURCE\n{p.get('source','')}\n\nREVIEW REQUIRED: price, product image rights, application wording, technical correctness and brand approval.\n'''
