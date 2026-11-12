"""Laser Product Studio: official-source data -> authentic-photo marketing assets.
Public-site pilot. Not affiliated with the official Laser Tools website.
"""
from __future__ import annotations
import io, re, json, time, zipfile, hashlib, logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from functools import lru_cache
from typing import Any

import fitz
import requests
from bs4 import BeautifulSoup
from PIL import Image
from flask import Flask, request, jsonify, send_file, render_template

from poster import create_posters, create_fact_sheet_pdf, create_marketing_copy

app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=10*1024*1024
logging.basicConfig(level=logging.INFO)
ALLOWED={'www.lasertools.co.uk','lasertools.co.uk','lasertools.toolconnection.co.uk','www.toolconnection.co.uk','toolconnection.co.uk'}
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; LaserProductStudioPilot/1.0; product-content-review)', 'Accept':'text/html,application/pdf,image/avif,image/webp,image/jpeg,image/png,*/*'}
CACHE: dict[str, tuple[float,dict,bytes|None]]={}

class LookupErrorPublic(Exception): pass

def sku_clean(text):
    part=(text or '').strip().upper()
    if not re.fullmatch(r'[0-9A-Z.-]{3,16}',part):raise LookupErrorPublic('Please enter a valid Laser part number.')
    return part

def authorized_url(url):
    p=urlparse(url)
    return p.scheme=='https' and p.hostname in ALLOWED and p.port is None

def official_get(url,session=requests, content_types=None):
    if not authorized_url(url): raise LookupErrorPublic('Source URL is not on an approved Laser/Tool Connection domain.')
    r=session.get(url,headers=HEADERS,timeout=12,allow_redirects=True)
    if not authorized_url(r.url):raise LookupErrorPublic('Official source redirected outside the approved domains.')
    if not r.ok:raise LookupErrorPublic(f'Official source returned HTTP {r.status_code}')
    if len(r.content)>12*1024*1024:raise LookupErrorPublic('Official source exceeded size limit.')
    if content_types and not any(x in r.headers.get('Content-Type','').lower() for x in content_types):
        # some servers don't declare PDF MIME correctly, allow signature instead
        if 'pdf' in content_types and r.content[:4]==b'%PDF': pass
        else: raise LookupErrorPublic('Official site returned an unexpected file type.')
    return r

def normalize(s):return re.sub(r'\s+',' ',str(s or '')).strip()

def select_bullets(soup):
    candidates=[]
    for ul in soup.find_all(['ul','ol']):
        vals=[normalize(x.get_text(' ',strip=True)) for x in ul.find_all('li',recursive=False)]
        vals=[x for x in vals if len(x)>26 and len(x)<520 and not re.search(r'(cookie|newsletter|terms and conditions|privacy|basket|login|shop by|contact us)',x,re.I)]
        if vals and (not ul.find_parent(['nav','footer','header'])):candidates.append(vals)
    if not candidates:return []
    candidates.sort(key=lambda x:(min(len(x),7),sum(len(v) for v in x)),reverse=True)
    return candidates[0][:8]

def parse_html(content,part,url):
    soup=BeautifulSoup(content,'html.parser')
    for t in soup(['script','style','header','footer','nav','noscript']):t.decompose()
    text=soup.get_text('\n',strip=True)
    lines=[normalize(x) for x in text.splitlines() if normalize(x)]
    big=re.sub(r'\s+',' ',text)
    title_el=soup.find('h1')
    title=normalize(title_el.get_text(' ',strip=True)) if title_el else ''
    if not title or title.lower() in ('search','products','access denied','not found'):
        raise LookupErrorPublic('The official page did not return a recognisable product title.')
    if part not in big and part not in url:
        raise LookupErrorPublic('The product part number could not be verified on the official page.')
    # Strong identification: URL contains the exact part number as a path component or slug prefix.
    path=urlparse(url).path
    if not re.search(r'/(?:'+re.escape(part)+r')(?:\b|[-_/])',path,re.I):
        # search pages are not treated as verified products
        raise LookupErrorPublic('The result was not an exact product page for this part number.')
    rrpm=re.search(r'RRP\s*£\s*([\d,]+(?:\.\d{2})?)',big,re.I)
    rrp=('£'+rrpm.group(1)+' excluding VAT') if rrpm else None
    features=select_bullets(soup)
    # Find product description: longest useful paragraph before spec table, not SEO navigation.
    paras=[normalize(x.get_text(' ',strip=True)) for x in soup.find_all('p')]
    paras=[x for x in paras if 80<len(x)<1100 and not re.search(r'(cookies|privacy policy|terms and conditions)',x,re.I)]
    desc=paras[0] if paras else (features[0] if features else '')
    specs={}
    for tr in soup.find_all('tr'):
        cells=tr.find_all(['th','td'])
        if len(cells)>=2:
            k,v=[normalize(x.get_text(' ',strip=True)) for x in cells[:2]]
            if 1<len(k)<65 and 1<len(v)<110: specs[k]=v
    # Site uses paired div text for properties, so check textual labelled values as fallback.
    known=['Brand','Type','Material','Length','Diameter (mm)','Number of pieces','Standards','Voltage','Wattage','Power plug','Run time','Magnetic','Battery capacity','Weight','Packaged Width (mm)','Packaged Height (mm)','Packaged Depth (mm)','Drive','Head Dia','Display']
    for i,line in enumerate(lines[:-1]):
        if line in known and line not in specs and 1<len(lines[i+1])<90:specs[line]=lines[i+1]
    image_urls=[]
    for meta in soup.find_all('meta'):
        if meta.get('property') in ('og:image','twitter:image') or meta.get('name')=='twitter:image':
            src=meta.get('content',''); u=urljoin(url,src)
            if authorized_url(u): image_urls.append(u)
    for image in soup.find_all('img'):
        src=image.get('src') or image.get('data-src') or ''
        u=urljoin(url,src)
        if authorized_url(u) and (part in src or 'XLarge' in src):image_urls.append(u)
    if not features and not specs: raise LookupErrorPublic('The product page contains insufficient technical information.')
    return dict(part=part,title=title,description=desc,features=features,specs=specs,price=rrp,source=url,image_candidates=list(dict.fromkeys(image_urls)),source_type='Official Laser/Tool Connection product page')

def parse_pis_pdf(pdfbytes,part,url):
    d=fitz.open(stream=pdfbytes,filetype='pdf')
    if d.page_count<1:raise LookupErrorPublic('The official information sheet is empty.')
    page=d[0]
    txt=page.get_text('text',sort=True)
    lines=[normalize(line) for line in txt.splitlines() if normalize(line)]
    # PDF often starts with LASER then part no, then name, possibly preceding boilerplate.
    exact=[i for i,l in enumerate(lines[:40]) if l==part]
    if not exact: raise LookupErrorPublic('The official product information sheet does not match the requested part number.')
    i=exact[0]
    title=''
    for l in lines[i+1:i+8]:
        if l.lower().startswith(('additional information','distributed by','the tool connection')):break
        if len(l)>7: title=l;break
    if not title: raise LookupErrorPublic('Product name could not be extracted from the information sheet.')
    add=next((j for j,l in enumerate(lines) if l.lower().startswith('additional information')),len(lines))
    desc=' '.join(x for x in lines[i+2:add] if len(x)>8)[:1250]
    features=[]; curr=''
    after=lines[add+1:]
    for l in after:
        if re.search(r'(distributed by|tool connection ltd|www\.toolconnection|telephone|©|\bCV47\b)',l,re.I): break
        if l.startswith(('•','-','●')):
            if curr:features.append(normalize(curr))
            curr=l.lstrip('•-● ').strip()
        elif curr and len(l)>8:curr+=' '+l
    if curr:features.append(normalize(curr))
    features=[x for x in features if 10<len(x)<650][:9]
    if not features:
        # bullet glyph may appear as separate blocks; fallback to feature-like lines
        features=[x for x in after[:20] if len(x)>25 and not re.search(r'distributed by|tool connection',x,re.I)][:7]
    specs={}
    patterns=[('Dimensions',r'(?:dimensions\s*:\s*)(\d+\s*[×xX]\s*\d+\s*[×xX]\s*\d+\s*mm)'),
              ('Power',r'\b(\d+\s*W)\b'),('Length',r'\b(\d+\s*mm)\s*(?:long|length)\b'),
              ('Brightness',r'\b(\d{2,5}\s*lumens?)\b'),('Battery',r'\b(\d{3,6}\s*mAh)\b'),
              ('Voltage',r'\b(\d+(?:\.\d+)?\s*V)\b')]
    for k,pat in patterns:
        m=re.search(pat,txt,re.I)
        if m:specs[k]=normalize(m.group(1))
    photos=[]
    for j in range(min(d.page_count,2)):
        pg=d[j]
        for entry in pg.get_images(full=True):
            xref=entry[0]
            try:
                image=d.extract_image(xref)
                im=Image.open(io.BytesIO(image['image']))
                if min(im.size)>=80 and max(im.size)>=350 and im.width*im.height>=50000:
                    rects=pg.get_image_rects(xref)
                    metric=(min(im.size)*max(im.size),min((r.y0 for r in rects),default=999))
                    photos.append((metric,im.convert('RGB')))
            except Exception:pass
    photos.sort(key=lambda t:(-t[0][0],t[0][1]))
    chosen=None
    for _,im in photos:
        out=io.BytesIO();im.thumbnail((2100,2100));im.save(out,format='PNG');chosen=out.getvalue();break
    result=dict(part=part,title=title,description=desc,features=features,specs=specs,price=None,source=url,source_type='Official Laser product information sheet',image_candidates=[])
    d.close()
    return result,chosen

def valid_image(blob):
    try:
        im=Image.open(io.BytesIO(blob));im.load()
        return min(im.size)>=80 and max(im.size)>=300 and im.width*im.height>=50000 and im.width*im.height<=30_000_000
    except Exception:return False

def lookup(part,session=requests,force=False):
    part=sku_clean(part)
    now=time.time()
    if not force and part in CACHE and now-CACHE[part][0]<3600:return CACHE[part][1],CACHE[part][2]
    errors=[];product=None;image_bytes=None
    # First try the official one-number deep link. This can redirect to a canonical slug.
    for url in [f'https://www.lasertools.co.uk/product/{part}',f'https://lasertools.toolconnection.co.uk/product/{part}']:
        try:
            r=official_get(url,session)
            if 'pdf' in r.headers.get('Content-Type','').lower() or r.content.startswith(b'%PDF'):
                product,image_bytes=parse_pis_pdf(r.content,part,r.url)
            else:product=parse_html(r.content,part,r.url)
            break
        except Exception as e:errors.append(str(e)[:190])
    # Product Information Sheet gives reliable part-number lookup even when page routing changes.
    if product is None:
        for url in [f'https://www.lasertools.co.uk/pis/{part}_PIS.pdf',f'https://lasertools.co.uk/pis/{part}_PIS.pdf']:
            try:
                r=official_get(url,session,content_types=['pdf'])
                product,image_bytes=parse_pis_pdf(r.content,part,r.url)
                break
            except Exception as e:errors.append(str(e)[:190])
    if not product:
        raise LookupErrorPublic('Could not retrieve a verified official product record for this part number. The manufacturer website may be blocking requests or may not have published an information sheet. No data has been fabricated.')
    if image_bytes is None:
        candidates=product.get('image_candidates',[])+[
          f'https://lasertools.toolconnection.co.uk/items/XLarge/{part}.jpg',
          f'https://www.lasertools.co.uk/items/XLarge/{part}.jpg']
        for url in dict.fromkeys(candidates):
            try:
                r=official_get(url,session)
                if valid_image(r.content):image_bytes=r.content;break
            except Exception:pass
    if not image_bytes:
        # fallback to official PDF image only, even when page metadata lacks a photo
        try:
            url=f'https://www.lasertools.co.uk/pis/{part}_PIS.pdf'
            r=official_get(url,session,content_types=['pdf'])
            _,image_bytes=parse_pis_pdf(r.content,part,r.url)
        except Exception:pass
    product['photo_verified']=bool(image_bytes)
    product['source_checked']=datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')
    product['lookup_status']='Live official website/PDF' # no cache when generated
    product['warnings']=[]
    if not image_bytes:product['warnings'].append('No verified product photo available. Upload an approved photo to create image-based posters.')
    if product['price'] is None:product['warnings'].append('No verified RRP found. Price will be omitted.')
    CACHE[part]=(now,product,image_bytes)
    return product,image_bytes

def safe_override(original,updates):
    out={**original}
    for key in ('title','description'):
        if isinstance(updates.get(key),str):out[key]=updates[key].strip()[:1300]
    for key in ('features',):
        if isinstance(updates.get(key),list):out[key]=[str(x).strip()[:350] for x in updates[key] if str(x).strip()][:9]
    if isinstance(updates.get('specs'),dict):out['specs']={str(k)[:55]:str(v)[:110] for k,v in list(updates['specs'].items())[:15]}
    return out

@app.get('/')
def home():return render_template('index.html')

@app.get('/api/health')
def health():return jsonify(ok=True,service='Laser Product Studio',lookup='official page + PDF fallback')

@app.get('/api/lookup/<part>')
def product_lookup(part):
    try:
        product,image=lookup(part)
        return jsonify(product=product,photo_url=f'/api/photo/{part}' if image else None)
    except LookupErrorPublic as e:return jsonify(error=str(e)),404
    except requests.RequestException:return jsonify(error='Official Laser website could not be reached. Please retry.'),502
    except Exception:
        app.logger.exception('Unexpected lookup error')
        return jsonify(error='Product lookup failed unexpectedly.'),500

@app.get('/api/photo/<part>')
def photo(part):
    try:
        _,image=lookup(part)
        if not image:return jsonify(error='No verified image found'),404
        im=Image.open(io.BytesIO(image));out=io.BytesIO();im.convert('RGB').save(out,'PNG');out.seek(0)
        return send_file(out,mimetype='image/png',download_name=f'LASER_{part}.png')
    except LookupErrorPublic:return jsonify(error='Photo unavailable'),404

@app.post('/api/generate/<part>')
def generate(part):
    try:
        product,img=lookup(part)
        body=request.get_json(silent=True) or {}
        if not body.get('confirmed'):
            return jsonify(error='Please confirm you reviewed the official product facts before generating external marketing drafts.'),400
        product=safe_override(product,body.get('edits') or {})
        if not img:return jsonify(error='No verified official product photograph available; marketing posters will not be generated with a fabricated photo.'),422
        assets=create_posters(product,img)
        tech=create_fact_sheet_pdf(product,img)
        txt=create_marketing_copy(product)
        with io.BytesIO() as zbuf:
            with zipfile.ZipFile(zbuf,'w',zipfile.ZIP_DEFLATED) as z:
                for name,png in assets.items():z.writestr(f'LASER_{part}_{name}.png',png)
                z.writestr(f'LASER_{part}_Technical_Sheet.pdf',tech)
                z.writestr(f'LASER_{part}_Marketing_Copy.txt',txt)
                z.writestr(f'LASER_{part}_Source_Record.json',json.dumps(product,indent=2))
            zbuf.seek(0)
            return send_file(io.BytesIO(zbuf.getvalue()),mimetype='application/zip',download_name=f'LASER_{part}_Marketing_Pack.zip',as_attachment=True)
    except LookupErrorPublic as e:return jsonify(error=str(e)),404
    except Exception:
        app.logger.exception('generation error')
        return jsonify(error='Unable to generate the marketing pack.'),500

@app.get('/api/poster/<part>/<style>')
def preview(part,style):
    if style not in ('Hero','Technical','Applications','Social'):return jsonify(error='Poster format not found'),404
    try:
        p,img=lookup(part)
        if not img:return jsonify(error='Verified product image missing'),422
        assets=create_posters(p,img)
        return send_file(io.BytesIO(assets[style]),mimetype='image/png',download_name=f'LASER_{part}_{style}.png')
    except LookupErrorPublic as e:return jsonify(error=str(e)),404

if __name__=='__main__':
    app.run(debug=True,host='127.0.0.1',port=5000)
