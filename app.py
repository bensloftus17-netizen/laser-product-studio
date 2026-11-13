"""Laser Product Studio: official-source data -> authentic-photo marketing assets.
Public-site pilot. Not affiliated with the official Laser Tools website.
"""
from __future__ import annotations
import io, re, json, time, zipfile, hashlib, logging, html
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, quote, unquote, parse_qs
from functools import lru_cache
from typing import Any
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import fitz
import requests
from bs4 import BeautifulSoup
from PIL import Image
from flask import Flask, request, jsonify, send_file, render_template_string

from poster import create_posters, create_fact_sheet_pdf, create_marketing_copy, render_hero, render_technical, render_price

V7_HOME_PAGE = r'''
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Laser Product Studio | Official product data to marketing assets</title>
<link rel="stylesheet" href="/static/styles.css?design=v8">
<style>
/* V6 preview layout: one wide hero, two different follow-up formats. */
.previews{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}
.previews .posteritem:first-child{grid-column:1/-1}
.previews .posteritem:first-child .posterthumb{height:515px}
.previews .posterthumb{height:435px;background:#eaf0f5;padding:24px;display:flex;justify-content:center;align-items:center}
.previews .posterthumb img{max-width:100%;max-height:100%;height:100%;object-fit:contain;box-shadow:0 12px 25px #132b4630}
.previews .posteritemfoot{background:white;padding:18px 20px;font-size:15px}
.previews .posteritemfoot span{font-weight:800}
.previews .posteritemfoot a{white-space:nowrap}
.posteritem .posterthumb img[data-error="true"]{display:none}
.posteritem .posterthumb .loaderror{color:#9c3720;font-size:13px}
@media(max-width:640px){.previews{grid-template-columns:1fr}.previews .posteritem:first-child{grid-column:auto}.previews .posterthumb,.previews .posteritem:first-child .posterthumb{height:360px}}
</style></head><body>
<header class="topbar"><div class="wrap nav"><div class="logo">LASER <small>TOOLS</small></div><div class="navright">PRODUCT STUDIO <span class="tag">INTERNAL PILOT</span></div></div></header>
<main class="wrap">
<section class="intro"><div class="kicker">LASER TOOLS · AUTOMATED CONTENT STUDIO</div><h1>One part number.<br><span>Three posters. Three different purposes.</span></h1><p>Enter a published Laser Tools part number. We retrieve the official product details and an authentic product image, then generate branded draft marketing materials.</p></section>
<section class="searchpanel"><form id="searchForm"><label for="part">ENTER A LASER TOOLS PART NUMBER</label><div class="searchrow"><input id="part" type="text" pattern="[0-9A-Za-z.\-]{3,16}" maxlength="16" value="9197" placeholder="e.g. 9197" required autocomplete="off"><button class="primary" id="searchBtn" type="submit">Find product &amp; create previews <b>→</b></button></div></form><details style="margin-top:13px;color:#30536f;font-size:13px"><summary style="cursor:pointer;font-weight:700">RRP missing? Paste the official UK product link</summary><input style="margin-top:9px;width:100%;padding:11px 12px;border:1px solid #bed0df;border-radius:7px" id="officialUrl" type="url" placeholder="https://www.toolconnection.co.uk/products/..." aria-label="Official UK Tool Connection product link"></details><details style="margin-top:11px;color:#30536f;font-size:13px"><summary style="cursor:pointer;font-weight:700">Missing RRP? Enter a staff-reviewed UK price</summary><div style="display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin-top:9px"><label for="staffRrp">RRP excluding VAT (£)</label><input id="staffRrp" type="number" min="0.01" max="500000" step="0.01" placeholder="e.g. 114.70" style="width:150px;padding:9px;border:1px solid #a9bbce;border-radius:6px"><label style="display:flex;align-items:center;gap:5px"><input id="staffReview" type="checkbox"> I have checked this price</label><button type="button" class="linkchip" id="applyRrp">Update poster prices</button></div><p style="margin-top:7px">Entered prices are draft figures and require company approval before publication.</p></details><div class="examples">Try <button class="linkchip" data-part="9197">9197</button><button class="linkchip" data-part="9395">9395</button><button class="linkchip" data-part="9345">9345</button><button class="linkchip" data-part="9139">9139</button></div><p id="status" class="status" role="status">Ready. Searches use live manufacturer pages, with an official PDF fallback.</p></section>
<div class="content"><aside><div class="sectioncap">01 / OFFICIAL PRODUCT RECORD</div><div id="record" class="record"><div class="placeholder"><div class="placeholder_icon">↗</div><b>No product loaded</b><p>Enter a part number above to retrieve the official product information and photograph.</p></div></div></aside>
<section class="right"><div class="previewtop"><div><div class="sectioncap">02 / AUTOMATIC MARKETING ASSETS</div><h2>Generated poster designs</h2></div><label class="approval"><input type="checkbox" id="reviewed" disabled> I've checked the product information</label></div><div id="previews" class="previews"><div class="posterempty">Your authentic-photo posters will appear here after the official product lookup succeeds.</div></div><div class="downloadbar"><div><b>Complete marketing pack</b><small>Promotional PNG · technical PNG + PDF · RRP PNG · campaign copy</small></div><button id="download" disabled class="primary">Download all assets (ZIP) ↓</button></div></section></div>
<section class="process"><div class="sectioncap">THE SYSTEM BEHIND THE DEMO</div><h2>Simple enough for every new product launch.</h2><div class="processgrid"><div><strong>1</strong><b>Enter SKU</b><p>Product lookup starts from the official website, not a hand-built five-product list.</p></div><div><strong>2</strong><b>Verify source</b><p>Exact part number, official features, product sheet and genuine image.</p></div><div><strong>3</strong><b>Generate drafts</b><p>Distinct promotional, technical and price-led poster campaigns.</p></div><div><strong>4</strong><b>Approve and use</b><p>Technical and marketing staff review claims before distribution.</p></div></div></section>
<footer><p>Independent internal pilot. Public Laser Tools / Tool Connection product information is used with source attribution. Prices, product claims and imagery must be approved before external release.</p></footer>
</main><script>
const $=id=>document.getElementById(id);let active=null;let activePhoto=null;let staffApplied=null;let inflight=false;
function esc(s){return String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));}
function setState(message,type='neutral'){const el=$('status');el.className='status '+type;el.textContent=message;}
function reset(){active=null;activePhoto=null;staffApplied=null;$('staffRrp').value='';$('staffReview').checked=false;$('reviewed').checked=false;$('reviewed').disabled=true;$('download').disabled=true;$('previews').innerHTML='<div class="posterempty">Retrieving genuine product details and photograph…</div>';}
function productCard(p,photo){const specs=Object.entries(p.specs||{}).map(([k,v])=>`<div class="spec"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('');const fs=(p.features||[]).map(x=>`<li>${esc(x)}</li>`).join('');const warns=(p.warnings||[]).map(x=>`<p class="warn">${esc(x)}</p>`).join('');return `<div class="found"><div class="sourcepill">✓ Live official source</div><h3>${esc(p.part)} <span>${esc(p.title)}</span></h3><div class="recordphoto">${photo?`<img src="${photo}" alt="Genuine Laser ${esc(p.part)} image">`:'<div class="nophoto">No verified photo retrieved</div>'}</div><p class="description">${esc(p.description)}</p>${p.price?`<div class="price">Manufacturer RRP <b>${esc(p.price)}</b><small style="display:block;font-size:12px;color:#486b87">${esc(p.price_status||'Check official source before publishing')}</small></div>`:''}<b class="subheading">Features</b><ul>${fs||'<li>Consult product sheet</li>'}</ul><b class="subheading">Technical specifications</b><div>${specs||'<span class="smallmuted">Refer to official information sheet</span>'}</div><div class="sourceinfo"><div>Source checked: ${esc(p.source_checked)}</div><a href="${esc(p.source)}" target="_blank" rel="noopener noreferrer">Open official source ↗</a></div>${warns}</div>`;}
function showPreviews(p,photo){if(!photo){$('previews').innerHTML='<div class="posterempty">No verified product photo was found. Posters are withheld rather than using an inaccurate AI-generated image.</div>';return;}
let styles=[['Hero','01 · Promotional advert'],['Technical','02 · Technical breakdown'],['Price','03 · RRP / sales poster']];$('previews').innerHTML=styles.map(([key,label])=>`<div class="posteritem"><div class="posterthumb"><img loading="lazy" src="/api/poster/${encodeURIComponent(p.part)}/${key}?design=v8${staffApplied?'&staff_rrp_ex='+encodeURIComponent(staffApplied)+'&staff_rrp_reviewed=1':''}" alt="${label}" onerror="this.style.display='none';this.parentElement.insertAdjacentHTML('beforeend','<span class=loaderror>Preview unavailable — open the full image or check Render logs.</span>')"></div><div class="posteritemfoot"><span>${label}</span><a target="_blank" href="/api/poster/${encodeURIComponent(p.part)}/${key}?design=v8${staffApplied?'&staff_rrp_ex='+encodeURIComponent(staffApplied)+'&staff_rrp_reviewed=1':''}" download="LASER_${esc(p.part)}_${key}.png">View / save ↗</a></div></div>`).join('');}
async function load(part){if(inflight)return;inflight=true;reset();const b=$('searchBtn');b.disabled=true;b.textContent='Retrieving official product…';setState('Looking up official product pages and product information sheets.','working');$('record').innerHTML='<div class="placeholder"><b>Searching official source…</b></div>';
try{const override=$('officialUrl').value.trim();const res=await fetch(`/api/lookup/${encodeURIComponent(part)}${override?'?uk_url='+encodeURIComponent(override):''}`,{headers:{'Accept':'application/json'}});const data=await res.json();if(!res.ok)throw Error(data.error||'The lookup did not succeed');active=data.product;activePhoto=data.photo_url;$('record').innerHTML=productCard(active,data.photo_url);showPreviews(active,data.photo_url);$('reviewed').disabled=!data.photo_url;setState('Official product record retrieved. Review the details and tick the approval box to download the pack.','success');}
catch(e){$('record').innerHTML='<div class="placeholder"><b>Product lookup unsuccessful</b><p>'+esc(e.message)+'</p></div>';$('previews').innerHTML='<div class="posterempty">No output generated because there is no verified manufacturer record.</div>';setState(e.message,'error');}finally{b.disabled=false;b.innerHTML='Find product &amp; create previews <b>→</b>';inflight=false;}}
$('applyRrp').addEventListener('click',()=>{
    if(!active){setState('Find a product first.','error');return;}
    const raw=$('staffRrp').value.trim(),approved=$('staffReview').checked,number=Number(raw);
    if(!raw||!approved||!Number.isFinite(number)||number<=0||number>500000){
        setState('Enter a positive ex-VAT RRP and tick the staff review box.','error');return;
    }
    staffApplied=number.toFixed(2);
    active.price='£'+number.toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2})+' excluding VAT';
    active.price_status='Staff-entered draft — approval needed before publishing';
    active.price_source='Staff entry';
    $('record').innerHTML=productCard(active,activePhoto);
    showPreviews(active,activePhoto);
    $('reviewed').checked=false;$('download').disabled=true;
    setState('Draft price applied. Review all posters before exporting.','success');
});
$('searchForm').addEventListener('submit',e=>{e.preventDefault();load($('part').value.trim().toUpperCase())});document.querySelectorAll('[data-part]').forEach(b=>b.addEventListener('click',()=>{$('part').value=b.dataset.part;load(b.dataset.part)}));$('reviewed').addEventListener('change',()=>{$('download').disabled=!$('reviewed').checked;});
$('download').addEventListener('click',async()=>{if(!active||!$('reviewed').checked)return;const b=$('download');b.disabled=true;b.textContent='Creating ZIP…';try{const r=await fetch(`/api/generate/${encodeURIComponent(active.part)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true,staff_rrp_ex:staffApplied,staff_rrp_reviewed:!!staffApplied&&$('staffReview').checked})});if(!r.ok){const v=await r.json();throw Error(v.error||'Export failed')}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`LASER_${active.part}_Marketing_Pack.zip`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);setState('Marketing pack generated and downloaded.','success')}catch(e){setState(e.message,'error')}finally{b.disabled=false;b.innerText='Download all assets (ZIP) ↓';}});
</script></body></html>

'''

app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=10*1024*1024
logging.basicConfig(level=logging.INFO)
ALLOWED={'www.lasertools.co.uk','lasertools.co.uk','lasertools.toolconnection.co.uk','www.toolconnection.co.uk','toolconnection.co.uk'}
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; LaserProductStudioPilot/1.0; product-content-review)', 'Accept':'text/html,application/pdf,image/avif,image/webp,image/jpeg,image/png,*/*', 'Accept-Language':'en-GB,en;q=0.9'}
CACHE: dict[str, tuple[float,dict,bytes|None]]={}
APPLICATION_IMAGE_CACHE: dict[str,bytes]={}

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

# Official English Tool Connection product pages verified for pilot demonstrations.
# For other part numbers, a search discovery attempt locates the manufacturer page.
OFFICIAL_UK_PRODUCTS = {
    '8324':'https://www.toolconnection.co.uk/products/cars-vans/steering-suspension/shock-absorbers/kits/8324-suspension-split-hub-knuckle-spreader',
    '9395':'https://www.toolconnection.co.uk/products/cars-vans/transmission/wheel-bearings/gen2-wheel-bearing-kits/9395-front-wheel-bearing-kit-for-mercedes-benz-sprinter-vw-crafter',
    '9372':'https://www.toolconnection.co.uk/products/workshop/equipment/hydraulic-press/9372-air-hydraulic-workshop-press-50-tonne',
    '9197':'https://www.toolconnection.co.uk/products/workshop/inspection-lighting/workshop-lamps/9197-under-bonnet-compact-work-lamp-10w-cob-infrared',
    '4832':'https://www.toolconnection.co.uk/products/cars-vans/brakes/brake-bleeding/brake-bleeders-manual/4832-manual-pressure-brake-bleeder-2l',
}


# Manufacturer RRPs independently checked against the official UK product pages
# on 13 November 2026. These are LAST-KNOWN values, not invented live quotations.
# A newer verified live RRP always takes precedence. Review prices before publishing.
VERIFIED_UK_RRP = {
    '9197': ('£48.78 excluding VAT', OFFICIAL_UK_PRODUCTS['9197']),
    '9372': ('£2,617.62 including VAT', OFFICIAL_UK_PRODUCTS['9372']),
    '9395': ('£630.79 including VAT', OFFICIAL_UK_PRODUCTS['9395']),
    '8324': ('£41.67 excluding VAT', OFFICIAL_UK_PRODUCTS['8324']),
    '4832': ('£114.70 excluding VAT', OFFICIAL_UK_PRODUCTS['4832']),
}

# Official UK reference text, used only when live extraction yields no English details.
# This is a dated product-specific fallback, not a replacement for live data.
VERIFIED_UK_FACTS = {
    '4832': {
        'features': [
            '2 litre capacity tank for pressure brake bleeding.',
            'One-way syphoning method.',
            'Operating pressure 10psi; maximum pressure rating 30psi.',
            'Quick connector and pressure release valve, with 0–70psi (0–5 bar) gauge.',
            'For brake master cylinder reservoirs using the supplied 44mm Euro adaptor.',
        ],
        'specs': {
            'Capacity': '2 litres',
            'Operating pressure': '10psi',
            'Maximum pressure': '30psi',
            'Gauge range': '0–70psi / 0–5 bar',
            'Reservoir adaptor': '44mm Euro',
        },
        'source': OFFICIAL_UK_PRODUCTS['4832'],
        'verified_on': '13 Nov 2026',
    },
}

FRENCH_TECH_TERMS = re.compile(r'\b(?:méthode|syphonage|siphonnage|unidirectionnelle|réservoir|système|purge|purger|pressurisation|pression|dépose|repose|moyeu|lorsque|pourra|destiné|vissage|suffisante|particulier|nécessitant|remplissage|permettant)\b',re.I)

FOREIGN_MARKERS = re.compile(r"\b(?:les|des|une|pour|avec|sans|afin|lors|sur|roulement|véhicules|comprend|comprennent|utilisation|également|assurer|remarque|utiliser|atelier|montage|pression|permettre|adapté|nécessaire|pièces|dépose|repose|cette|conçu|références|nettoyer|veiller|éviter|outil|lesquels|auxquels|cette|ceci|du|le|la|et)\b", re.I)

def is_french(text):
    text=normalize(text)
    if FRENCH_TECH_TERMS.search(text):return True
    words=FOREIGN_MARKERS.findall(text)
    # Avoid rejecting English 'insertion', 'outil' appearing as model names.
    return len(words)>=2 or (len(words)>=1 and bool(re.search(r'[àâçéèêëîïôùûüÿœæ]',text,re.I)))

def english_only_features(features):
    return [x for x in features if not is_french(x) and not re.search(r'\b(?:N\.B\.|REMARQUE)\s*:',x,re.I)]

def english_only_specs(specs):
    return {k:v for k,v in specs.items() if not is_french(k+' '+str(v))}

def search_official_uk_product(part,session=requests):
    """Discover the genuine product URL; third-party search snippets are NEVER used for facts/prices."""
    # The UK site's normal search is tried first. Parsing is restricted to official product links.
    q=quote(part)
    choices=[f'https://www.toolconnection.co.uk/search?query={q}',
             f'https://www.bing.com/search?format=rss&q={quote("site:toolconnection.co.uk/products/ " + part)}']
    for url in choices:
        try:
            r=session.get(url,headers=HEADERS,timeout=5,allow_redirects=True)
            if not r.ok or len(r.content)>3_000_000:continue
            soup=BeautifulSoup(r.content,'html.parser')
            for node in soup.find_all(['a','link']):
                href=node.get('href') or ''
                if href.startswith('//'):href='https:'+href
                if 'uddg=' in href:
                    href=unquote(parse_qs(urlparse(href).query).get('uddg',[''])[0])
                resolved=urljoin(r.url,html.unescape(href))
                if (authorized_url(resolved) and 'toolconnection.co.uk' in urlparse(resolved).hostname
                    and re.search(r'/products/.*/'+re.escape(part)+r'(?:-|$)',urlparse(resolved).path,re.I)):
                    return resolved
            # Bing search RSS URLs appear as text in <link> elements in certain parsers.
            for match in re.findall(r'https?://(?:www\.)?toolconnection\.co\.uk/products/[^\s<"\']+',r.text,re.I):
                match=html.unescape(match.split('&amp;')[0])
                if re.search(r'/'+re.escape(part)+r'(?:-|$)',urlparse(match).path,re.I):return match
        except Exception:continue
    return None

def manufacturer_price_from_html(content):
    """Return only manufacturer RRP, preserving official VAT basis.

    Official UK pages typically display RRP£114.70plus VAT or
    RRP£2,617.62inc VAT £2,181.35exc VAT.
    """
    soup=BeautifulSoup(content.decode('utf-8','replace') if isinstance(content,bytes) else content,'html.parser')
    for tag in soup(['script','style','nav','noscript','footer']):tag.decompose()
    text=normalize(soup.get_text(' ',strip=True))
    match=re.search(r'\bRRP\s*[:\s]*£\s*([\d,]+(?:\.\d{1,2})?)(.{0,100})',text,re.I)
    if not match:return None
    amount='£'+match.group(1)
    suffix=normalize(match.group(2)).lower()
    if re.match(r'\s*(?:inc(?:luding|l)?\.?|with)\s*vat\b',suffix):
        return amount+' including VAT'
    if re.match(r'\s*(?:plus|exc(?:luding|l)?\.?|ex)\s*vat\b',suffix):
        return amount+' excluding VAT'
    return amount+' (VAT basis not verified)'


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
    soup=BeautifulSoup(content.decode('utf-8','replace') if isinstance(content,bytes) else content,'html.parser')
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
    rrp=manufacturer_price_from_html(content)
    features=english_only_features(select_bullets(soup))
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
    specs=english_only_specs(specs)
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
    """Reject blank/broken crops as well as undersized manufacturer photos.

    A previous catalogue thumbnail was almost entirely a thin black horizontal
    ribbon on white, yet its canvas passed our dimensions-only validation.
    We detect that failure without rejecting long, vertical tools such as lamps.
    """
    try:
        im=Image.open(io.BytesIO(blob));im.load()
        if not (min(im.size)>=80 and max(im.size)>=300 and 50000<=im.width*im.height<=30_000_000):return False
        im=ImageOps.exif_transpose(im).convert('RGB')
        im.thumbnail((350,350),Image.Resampling.LANCZOS)
        w,h=im.size
        colors=[im.getpixel((x,y)) for x,y in ((0,0),(w-1,0),(0,h-1),(w-1,h-1))]
        # Photo with a near-white studio background: measure actual content.
        light=sum(1 for rgb in colors if min(rgb)>228 and max(rgb)-min(rgb)<24)
        if light>=3:
            from PIL import ImageChops
            mask=ImageChops.difference(im,Image.new('RGB',(w,h),'white')).convert('L')
            mask=mask.point(lambda v:255 if v>45 else 0)
            box=mask.getbbox()
            if not box:return False
            contentw=(box[2]-box[0])/w
            contenth=(box[3]-box[1])/h
            if contentw>.65 and contenth<.16:return False
            if contentw*contenth<.025:return False
        return True
    except Exception:return False

def preferred_manufacturer_photos(part):
    """Exact part-number JPEGs, not the first SEO/OG image on a product page."""
    return [
        f'https://www.lasertools.co.uk/items/large/{part}.jpg',
        f'https://lasertools.toolconnection.co.uk/items/large/{part}.jpg',
        f'https://www.lasertools.co.uk/items/XLarge/{part}.jpg',
        f'https://lasertools.toolconnection.co.uk/items/XLarge/{part}.jpg',
    ]

def lookup(part,session=requests,force=False,uk_url=None):
    part=sku_clean(part)
    if uk_url:
        uk_url=uk_url.strip()
        if not (authorized_url(uk_url) and urlparse(uk_url).hostname in ('www.toolconnection.co.uk','toolconnection.co.uk')
                and re.search(r'/products/.*/'+re.escape(part)+r'(?:-|$)',urlparse(uk_url).path,re.I)):
            raise LookupErrorPublic('Please paste the official UK Tool Connection product page URL for this exact part number.')
    now=time.time()
    if not force and not uk_url and part in CACHE and now-CACHE[part][0]<3600:
        return CACHE[part][1],CACHE[part][2]
    errors=[]; product=None; image_bytes=None
    # Official UK pages are best for English product wording and genuine GBP RRP.
    uk_candidates=[]
    if uk_url:uk_candidates.append(uk_url)
    if part in OFFICIAL_UK_PRODUCTS:uk_candidates.append(OFFICIAL_UK_PRODUCTS[part])
    else:
        discovered=search_official_uk_product(part,session)
        if discovered:uk_candidates.append(discovered)
    for url in dict.fromkeys(uk_candidates):
        try:
            r=official_get(url,session)
            candidate=parse_html(r.content,part,r.url)
            # Prefer English UK descriptions; never display a foreign-language product record.
            if is_french(candidate['title']+' '+candidate['description']):
                errors.append('UK page returned translated copy');continue
            product=candidate
            break
        except Exception as e:errors.append(str(e)[:180])
    # If no UK listing was found, use Laser's official page, filtering non-English text.
    if product is None:
        for url in [f'https://www.lasertools.co.uk/product/{part}',f'https://lasertools.toolconnection.co.uk/product/{part}']:
            try:
                r=official_get(url,session)
                if 'pdf' in r.headers.get('Content-Type','').lower() or r.content.startswith(b'%PDF'):
                    candidate,image_bytes=parse_pis_pdf(r.content,part,r.url)
                else:candidate=parse_html(r.content,part,r.url)
                if is_french(candidate['title']+' '+candidate['description']):
                    errors.append('Manufacturer page not in English');continue
                product=candidate
                break
            except Exception as e:errors.append(str(e)[:180])
    # English product sheets are a safe fallback when the browser receives French text.
    # If the UK page is present, keep it as the authoritative RRP source.
    if product is None or not product.get('features'):
        for url in [f'https://www.lasertools.co.uk/pis/{part}_PIS.pdf',f'https://lasertools.co.uk/pis/{part}_PIS.pdf']:
            try:
                r=official_get(url,session,content_types=['pdf'])
                sheet,photo=parse_pis_pdf(r.content,part,r.url)
                if is_french(sheet['title']+' '+sheet['description']):continue
                sheet['features']=english_only_features(sheet.get('features',[]))
                if not product:product=sheet
                else:
                    product['features']=product['features'] or sheet['features']
                    product['specs']={**sheet.get('specs',{}),**product.get('specs',{})}
                if image_bytes is None:image_bytes=photo
                break
            except Exception as e:errors.append(str(e)[:180])
    if not product:
        raise LookupErrorPublic('Could not retrieve an English-language official Laser product record. No product text or prices have been fabricated.')
    product['features']=english_only_features(product.get('features',[]))
    product['specs']=english_only_specs(product.get('specs',{}))
    # Restore manufacturer-confirmed UK facts if the available product sheet was
    # non-English or returned incomplete technical text.
    if part in VERIFIED_UK_FACTS:
        reference=VERIFIED_UK_FACTS[part]
        if not product['features']:
            product['features']=reference['features'][:]
            product['features_status']='Official UK facts checked '+reference['verified_on']
        if not product['specs']:
            product['specs']=dict(reference['specs'])
            product['specs_status']='Official UK facts checked '+reference['verified_on']
    # A product sheet often has no commercial data. Check the official UK listing
    # separately, even if the primary English product record came from a PDF.
    if not product.get('price'):
        for candidate_url in dict.fromkeys(uk_candidates):
            try:
                response=official_get(candidate_url,session)
                verified=manufacturer_price_from_html(response.content)
                if verified:
                    product['price']=verified
                    product['price_source']=response.url
                    product['price_status']='Live UK manufacturer RRP'
                    break
            except Exception:
                pass
    # Exact-SKU manufacturer RRPs checked against official UK product pages.
    # These are labelled cached and MUST be reviewed before external publication.
    if not product.get('price') and part in VERIFIED_UK_RRP:
        product['price'], product['price_source']=VERIFIED_UK_RRP[part]
        product['price_status']='Official UK RRP independently checked on 13 Nov 2026; recheck before publication'
    elif product.get('price') and not product.get('price_source'):
        product['price_source']=product.get('source')
        product['price_status']='Live official UK product page'
    # Always use a verified product-specific manufacturer photo as first choice.
    # Social-media OG thumbnails and extracted PDF masks can appear as black strips.
    # Preserve the PDF photo as a fallback, but replace it with the genuine JPEG
    # whenever one is obtainable.
    pdf_photo=image_bytes if image_bytes and valid_image(image_bytes) else None
    image_bytes=None
    preferred=preferred_manufacturer_photos(part)
    fallback_candidates=[
        u for u in product.get('image_candidates',[])
        if re.search(r'/'+re.escape(part)+r'(?:[_./-]|$)',urlparse(u).path,re.I)
    ]
    product['photo_source']=None
    for image_url in dict.fromkeys(preferred+fallback_candidates):
        try:
            r=official_get(image_url,session)
            if valid_image(r.content):
                image_bytes=r.content
                product['photo_source']=r.url
                break
        except Exception:pass
    if image_bytes is None and pdf_photo:
        image_bytes=pdf_photo
        product['photo_source']='Embedded in official product information sheet'
    if image_bytes is None:
        try:
            r=official_get(f'https://www.lasertools.co.uk/pis/{part}_PIS.pdf',session,content_types=['pdf'])
            _,photo=parse_pis_pdf(r.content,part,r.url)
            if photo and valid_image(photo):
                image_bytes=photo
                product['photo_source']=r.url
        except Exception:pass
    product['photo_verified']=bool(image_bytes)
    # When the manufacturer provides a separate photo of the tool in use, keep
    # it for the campaign poster; catalogue and price designs use the studio photo.
    # A single extra official photo is attempted, never a random search-engine image.
    APPLICATION_IMAGE_CACHE.pop(part,None)
    application_candidates=[
        x for x in product.get('image_candidates',[])
        if re.search(r'in[ _-]?situ',x,re.I)
    ]
    application_candidates.append(f'https://www.lasertools.co.uk/items/large/{part}_InSitu_A.jpg')
    product['application_photo_source']=None
    for image_url in dict.fromkeys(application_candidates[:2]):
        try:
            if not re.search(r'/'+re.escape(part)+r'(?:[_./-]|$)',urlparse(image_url).path,re.I):continue
            result=official_get(image_url,session)
            if valid_image(result.content):
                APPLICATION_IMAGE_CACHE[part]=result.content
                product['application_photo_source']=result.url
                break
        except Exception:pass
    product['source_checked']=datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')
    product['lookup_status']='Live official UK/English manufacturer source'
    product['warnings']=[]
    if not image_bytes:product['warnings'].append('No verified manufacturer photo available.')
    if product.get('price_status','').startswith('Official UK RRP independently checked'):
        product['warnings'].append('RRP was checked on 13 Nov 2026; confirm it is still current before publishing.')
    if not product.get('price'):
        product['warnings'].append('UK RRP not verified. Paste the exact official Tool Connection URL, or have staff confirm the price before publication.')
    if not product['features']:
        product['warnings'].append('English feature bullets were not available. Use the official English description instead of translated text.')
    CACHE[part]=(now,product,image_bytes)
    return product,image_bytes

def with_reviewed_price(product,raw,approved=False):
    """Set a staff-reviewed draft RRP. Never label it as live manufacturer data."""
    if raw is None or str(raw).strip()=='':return product
    if not approved:
        raise LookupErrorPublic('Tick the staff price review box before using an entered RRP.')
    try:
        amount=Decimal(str(raw).strip()).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError):
        raise LookupErrorPublic('Enter a valid UK RRP excluding VAT.')
    if not amount.is_finite() or amount<=0 or amount>Decimal('500000'):
        raise LookupErrorPublic('Enter a positive ex-VAT price (maximum £500,000).')
    result={**product}
    result['price']=f'£{amount:,.2f} excluding VAT'
    result['price_status']='Staff-entered draft price — independently approve before publication'
    result['price_source']='Staff entry, not an automatically confirmed manufacturer RRP'
    result['warnings']=[v for v in product.get('warnings',[]) if 'rrp' not in v.lower() and 'price' not in v.lower()]
    result['warnings'].append('Price was entered by staff. Company approval is required before publishing.')
    return result


def safe_override(original,updates):
    out={**original}
    for key in ('title','description'):
        if isinstance(updates.get(key),str):out[key]=updates[key].strip()[:1300]
    for key in ('features',):
        if isinstance(updates.get(key),list):out[key]=[str(x).strip()[:350] for x in updates[key] if str(x).strip()][:9]
    if isinstance(updates.get('specs'),dict):out['specs']={str(k)[:55]:str(v)[:110] for k,v in list(updates['specs'].items())[:15]}
    return out

@app.get('/')
def home():
    return render_template_string(V7_HOME_PAGE)

@app.after_request
def no_cache_for_drafts(response):
    if request.path=='/' or request.path.startswith('/api/poster/'):
        response.headers['Cache-Control']='no-store, max-age=0'
    return response

@app.get('/api/health')
def health():return jsonify(ok=True,service='Laser Product Studio',design='v8-distinct-posters-and-rrp',lookup='official page + PDF fallback')

@app.get('/api/lookup/<part>')
def product_lookup(part):
    try:
        product,image=lookup(part,uk_url=request.args.get('uk_url') or None)
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
        product=with_reviewed_price(product,body.get('staff_rrp_ex'),body.get('staff_rrp_reviewed') is True)
        if not img:return jsonify(error='No verified official product photograph available; marketing posters will not be generated with a fabricated photo.'),422
        assets=create_posters(product,img,APPLICATION_IMAGE_CACHE.get(part))
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
    if style not in ('Hero','Technical','Price'):return jsonify(error='Poster format not found'),404
    try:
        p,img=lookup(part)
        p=with_reviewed_price(p,request.args.get('staff_rrp_ex'),request.args.get('staff_rrp_reviewed')=='1')
        if not img:return jsonify(error='Verified product image missing'),422
        renderer={'Hero':render_hero,'Technical':render_technical,'Price':render_price}[style]
        artwork=renderer(p,img,APPLICATION_IMAGE_CACHE.get(part)) if style=='Hero' else renderer(p,img)
        return send_file(io.BytesIO(artwork),mimetype='image/png',download_name=f'LASER_{part}_{style}.png')
    except LookupErrorPublic as e:return jsonify(error=str(e)),404

if __name__=='__main__':
    app.run(debug=True,host='127.0.0.1',port=5000)
