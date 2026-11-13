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
from PIL import Image, ImageOps
from langdetect import detect_langs, DetectorFactory, LangDetectException
DetectorFactory.seed = 0
from flask import Flask, request, jsonify, send_file, render_template_string

from poster import create_posters, create_fact_sheet_pdf, create_marketing_copy, render_hero, render_technical, render_price, technical_layout_mode
from brand_assets import BRAND_LABELS, get_brand_image

V7_HOME_PAGE = r'''
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Laser Product Studio | Official product data to marketing assets</title>
<link rel="stylesheet" href="/static/styles.css?design=v18">
</head><body>
<header class="topbar"><div class="wrap nav">
<div class="brand-lockup"><div class="logo">LASER<small>TOOLS</small></div><span class="brand-rule"></span><div class="brand-name">Product Studio<small>Professional marketing, simplified</small></div></div>
<nav class="navright"><a href="#builder">Create posters</a><a href="#how">How it works</a><span class="tag">DEMO · REVIEW REQUIRED</span></nav></div></header>
<main><section class="hero"><div class="wrap hero-inner">
<div class="hero-copy"><div class="hero-kicker">LASER TOOLS · PRODUCT MARKETING STUDIO</div><h1>Create professional<br><span>product posters.</span></h1><p>One part number. Three professional marketing designs. Genuine product photography and manufacturer information, ready for your review.</p><div class="hero-qualities"><span>Official product imagery</span><span>Three poster styles</span><span>Download-ready drafts</span></div></div>
<div class="hero-art" aria-hidden="true"><div class="art-sheet art-left"><b>LASER TOOLS</b><strong>TECHNICAL<br>INFORMATION</strong><i></i><i></i></div><div class="art-sheet art-right"><b>LASER TOOLS</b><strong>UK RRP</strong><em>£</em></div><div class="art-sheet art-center"><b>LASER TOOLS</b><strong>PRODUCT<br>SPOTLIGHT</strong><div class="art-circle"></div><small>ENGINEERED FOR THE JOB</small></div></div>
</div></section>
<div class="wrap app-shell" id="builder">
<div class="steps-panel"><div class="steps-heading"><b>Three simple steps</b><span>From product lookup to marketing materials</span></div><ol class="steps" aria-label="Poster creation steps"><li class="step active" data-step="1" aria-current="step"><span class="step-num">1</span><div><b>Find your product</b><small>Enter a part number</small></div></li><li class="step" data-step="2"><span class="step-num">2</span><div><b>Review the details</b><small>Check imagery and RRP</small></div></li><li class="step" data-step="3"><span class="step-num">3</span><div><b>Download the posters</b><small>Three ready-to-review drafts</small></div></li></ol></div>
<section class="searchpanel"><div class="lookup-heading"><div><div class="sectioncap">STEP 01 / PRODUCT LOOKUP</div><h2>Find a Laser Tools product</h2><p>Enter a part number to retrieve the official record and create three poster designs.</p></div><span class="lookup-chip">Quick product search</span></div>
<form id="searchForm"><label class="inputlabel" for="part">LASER TOOLS PART NUMBER</label><div class="searchrow"><input id="part" type="text" pattern="[0-9A-Za-z.\-]{3,16}" maxlength="16" value="9395" placeholder="e.g. 9395" required autocomplete="off"><button class="primary" id="searchBtn" type="submit">Find product &amp; create posters <b>→</b></button></div></form>
<div class="examples"><span>Try an example:</span><button class="linkchip" type="button" data-part="9364">9364 · Ratchet set</button><button class="linkchip" type="button" data-part="9395">9395 · Bearing kit</button><button class="linkchip" type="button" data-part="9365">9365 · 4pc set</button><button class="linkchip" type="button" data-part="8324">8324 · Hub spreader</button></div>
<div class="distributor-config">
 <div class="distributor-label"><label for="distributorBrand">Customer / distributor branding <span>(optional)</span></label><small>Show a customer's logo alongside Laser Tools on all three posters.</small></div>
 <div class="distributor-controls">
  <select id="distributorBrand" name="distributor_brand" aria-label="Customer or distributor branding">
   <option value="none" selected>None — Laser Tools only</option>
   <option value="gsf">GSF Car Parts</option>
   <option value="euro">Euro Car Parts</option>
   <option value="mpd">Motor Parts Direct</option>
  </select>
  <div id="distributorPreview" class="distributor-logo-preview" aria-live="polite"><span>LASER TOOLS ONLY</span></div>
 </div>
 <small class="brand-disclaimer">Demo customer logos. Obtain approval to use each company's brand before publishing externally.</small>
</div>
<details class="advanced-options"><summary>Need to enter a price or official product URL? <span>Advanced options</span></summary><div class="advanced-content">
<div class="advanced-field"><label for="officialUrl">Official UK product URL (optional)</label><input id="officialUrl" type="url" placeholder="https://www.toolconnection.co.uk/products/..."><small>Use this when a product is difficult to find.</small></div>
<div class="advanced-field"><label for="staffRrp">Staff-reviewed UK RRP</label><div class="price-entry"><input id="staffRrp" type="number" min="0.01" max="500000" step="0.01" placeholder="e.g. 114.70"><select id="staffRrpBasis" aria-label="VAT status"><option value="ex">Ex VAT</option><option value="inc">Inc VAT</option></select></div><label class="check-label"><input id="staffReview" type="checkbox"> I've checked this price</label><button type="button" class="secondary" id="applyRrp">Update poster prices</button><small>Staff-entered prices are drafts and need company approval.</small></div>
</div></details><p id="status" class="status" role="status" aria-live="polite">Ready to find a Laser Tools product.</p></section>
<div class="content"><aside class="record-panel"><div class="panel-heading"><span class="panel-step">02</span><div><div class="sectioncap">OFFICIAL PRODUCT RECORD</div><h2>Review product details</h2><p>Check the information before sharing.</p></div></div><div id="record" class="record"><div class="placeholder"><div class="placeholder_icon">⌕</div><b>Search for a product</b><p>Official details and photography appear here.</p></div></div></aside>
<section class="right"><div class="previewtop"><div class="panel-heading"><span class="panel-step">03</span><div><div class="sectioncap">YOUR MARKETING ASSETS</div><h2>Generated poster designs</h2><p>Three designs for three different sales uses.</p></div></div><span class="formats-chip">3 FORMATS</span></div>
<div id="previews" class="previews"><div class="posterempty"><b>Your posters will appear here</b><p>Enter a part number to create three branded previews.</p></div></div>
<div class="reviewstrip"><label class="approval"><input type="checkbox" id="reviewed" disabled><span>I've checked the product information and posters</span></label><small>Company review required before publication.</small></div>
<div class="downloadbar"><div><b>Download your marketing pack</b><small>3 PNG posters · technical PDF · marketing copy · source information</small></div><button id="download" disabled class="primary">Download all assets (ZIP) ↓</button></div></section></div>
<section id="how" class="how"><div class="how-intro"><div class="sectioncap">MADE FOR REPS &amp; DISTRIBUTORS</div><h2>Simple from start to finish</h2><p>A faster way to prepare product marketing drafts using genuine manufacturer information.</p></div><div class="how-grid"><div><span class="how-icon">01</span><b>Find</b><p>Retrieve a genuine Laser Tools product image and official details.</p></div><div><span class="how-icon">02</span><b>Review</b><p>Check specifications, applications and UK pricing.</p></div><div><span class="how-icon">03</span><b>Download</b><p>Save promotional, technical and sales poster drafts.</p></div></div></section>
<footer><p>Independent internal pilot. Public Laser Tools / Tool Connection information is used with source attribution. Prices, product claims, artwork and imagery require approval before external release.</p></footer>
</div></main>
<script>
const $=id=>document.getElementById(id);let active=null;let activePhoto=null;let staffApplied=null;let staffBasis='ex';let inflight=false;
function esc(s){return String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));}
function setState(message,type='neutral'){const el=$('status');el.className='status '+type;el.textContent=message;}
function selectedDistributor(){return $('distributorBrand').value;}
function updateDistributorPreview(){
 const id=selectedDistributor(),target=$('distributorPreview');
 const labels={gsf:'GSF Car Parts',euro:'Euro Car Parts',mpd:'Motor Parts Direct'};
 target.innerHTML=id==='none'?'<span>LASER TOOLS ONLY</span>':
   '<img src="/api/distributor-logo/'+encodeURIComponent(id)+'" alt="'+esc(labels[id]||'Distributor')+' logo">';
 target.setAttribute('aria-label',id==='none'?'No customer branding':(labels[id]||'Selected customer logo'));
 if(active){
   $('reviewed').checked=false;$('download').disabled=true;
   setProgress(2);showPreviews(active,activePhoto);
   setState(id==='none'?'Laser Tools-only posters selected. Review the previews.':
     (labels[id]+' branding applied to all three poster previews. Review before downloading.'),'success');
 }
}
function reset(){setProgress(1);active=null;activePhoto=null;staffApplied=null;$('staffRrp').value='';$('staffRrpBasis').value='ex';$('staffReview').checked=false;$('reviewed').checked=false;$('reviewed').disabled=true;$('download').disabled=true;$('previews').innerHTML='<div class="posterempty">Retrieving genuine product details and photograph…</div>';}
function setProgress(stage){document.querySelectorAll('.step[data-step]').forEach(el=>{const n=Number(el.dataset.step);el.classList.toggle('active',n===stage);el.classList.toggle('complete',n<stage);if(n===stage)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');});}
function productCard(p,photo){const fs=(p.features||[]).filter(x=>x.length<180);const specs=Object.entries(p.specs||{}).slice(0,8).map(([k,v])=>'<div class="spec"><span>'+esc(k)+'</span><b>'+esc(v)+'</b></div>').join('');const warns=(p.warnings||[]).map(x=>'<p class="warn">'+esc(x)+'</p>').join('');const full=String(p.description||'');const desc=full.length>250?full.slice(0,244).replace(/\s+\S*$/,'')+'…':full;const staff=String(p.price_source||'').startsWith('Staff entry');return '<div class="found"><div class="sourcepill">✓ Official manufacturer record</div><h3><span class="sku-label">PART NO. '+esc(p.part)+'</span>'+esc(p.title)+'</h3><div class="recordphoto">'+(photo?'<img src="'+esc(photo)+'" alt="Official Laser Tools product image">':'<div class="nophoto">No verified photograph</div>')+'</div><div class="price"><span>'+(p.price?(staff?'Staff-reviewed draft RRP':'Manufacturer UK RRP'):'PRICE')+'</span><b>'+esc(p.price||'On request')+'</b><small>'+esc(p.price_status||(p.price?'Confirm before publishing':'No verified RRP available'))+'</small></div><div class="record-summary"><h4>Product overview</h4><p>'+esc(desc)+'</p></div>'+(fs.length?'<div class="key-list"><h4>Key features</h4><ul>'+fs.slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>':'')+'<details class="record-details"><summary>View all product information</summary><div class="record-full"><h4>Full description</h4><p>'+esc(full)+'</p><h4>Features</h4><ul>'+fs.slice(0,8).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul><h4>Specifications</h4>'+(specs||'No further verified specifications')+'</div></details><div class="sourceinfo"><div>Source checked: '+esc(p.source_checked||'Not available')+'</div><a href="'+esc(p.source||'#')+'" target="_blank" rel="noopener noreferrer">Official product page ↗</a></div>'+warns+'</div>';}
function showPreviews(p,photo){if(!photo){$('previews').innerHTML='<div class="posterempty">No verified image was found. Posters are withheld rather than inventing a tool photograph.</div>';return;}const layouts=String(p.technical_layout||'').toLowerCase();const styles=[['Hero','01','Promotional advert','Attention-grabbing product campaign'],['Technical','02','Technical information',layouts?layouts+' detail layout':'Product breakdown'],['Price','03','RRP / sales poster','Price-led customer sales material']];$('previews').innerHTML=styles.map(([key,num,title,desc])=>{const url='/api/poster/'+encodeURIComponent(p.part)+'/'+key+'?design=v18&distributor_brand='+encodeURIComponent(selectedDistributor())+(staffApplied?'&staff_rrp_ex='+encodeURIComponent(staffApplied)+'&staff_rrp_reviewed=1&staff_rrp_basis='+encodeURIComponent(staffBasis):'');return '<article class="posteritem"><div class="poster-cardheading">'+num+' / '+title+'</div><div class="posterthumb"><img loading="lazy" src="'+url+'" alt="'+esc(title)+' preview" onerror="this.onerror=null;this.style.display=\'none\';this.parentElement.insertAdjacentHTML(\'beforeend\',\'<span class=loaderror>Preview unavailable. Open full size to retry.</span>\')"></div><div class="posteritemfoot"><div><b>'+title+'</b><small>'+esc(desc)+'</small></div><a target="_blank" rel="noopener noreferrer" href="'+url+'">View full size ↗</a></div></article>';}).join('');}
async function load(part){if(inflight)return;inflight=true;reset();const b=$('searchBtn');b.disabled=true;b.textContent='Retrieving official product…';setState('Looking up official product pages and product information sheets.','working');$('record').innerHTML='<div class="placeholder"><b>Searching official source…</b></div>';
try{const override=$('officialUrl').value.trim();const res=await fetch(`/api/lookup/${encodeURIComponent(part)}${override?'?uk_url='+encodeURIComponent(override):''}`,{headers:{'Accept':'application/json'}});const data=await res.json();if(!res.ok)throw Error(data.error||'The lookup did not succeed');active=data.product;activePhoto=data.photo_url;setProgress(2);$('record').innerHTML=productCard(active,data.photo_url);showPreviews(active,data.photo_url);$('reviewed').disabled=!data.photo_url;setState('Official product record retrieved. Review the details and tick the approval box to download the pack.','success');}
catch(e){$('record').innerHTML='<div class="placeholder"><b>Product lookup unsuccessful</b><p>'+esc(e.message)+'</p></div>';$('previews').innerHTML='<div class="posterempty">No output generated because there is no verified manufacturer record.</div>';setState(e.message,'error');}finally{b.disabled=false;b.innerHTML='Find product &amp; create posters <b>→</b>';inflight=false;}}
$('applyRrp').addEventListener('click',()=>{
    if(!active){setState('Find a product first.','error');return;}
    const raw=$('staffRrp').value.trim(),approved=$('staffReview').checked,number=Number(raw);
    if(!raw||!approved||!Number.isFinite(number)||number<=0||number>500000){
        setState('Enter a positive UK RRP and tick the staff review box.','error');return;
    }
    staffApplied=number.toFixed(2);staffBasis=$('staffRrpBasis').value;
    active.price='£'+number.toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2})+(staffBasis==='inc'?' including VAT':' excluding VAT');
    active.price_status='Staff-entered draft — approval needed before publishing';
    active.price_source='Staff entry';
    $('record').innerHTML=productCard(active,activePhoto);
    showPreviews(active,activePhoto);
    $('reviewed').checked=false;$('download').disabled=true;
    setState('Draft price applied. Review all posters before exporting.','success');
});
$('distributorBrand').addEventListener('change',updateDistributorPreview);
$('searchForm').addEventListener('submit',e=>{e.preventDefault();load($('part').value.trim().toUpperCase())});document.querySelectorAll('[data-part]').forEach(b=>b.addEventListener('click',()=>{$('part').value=b.dataset.part;load(b.dataset.part)}));$('reviewed').addEventListener('change',()=>{$('download').disabled=!$('reviewed').checked;setProgress($('reviewed').checked?3:2);});
$('download').addEventListener('click',async()=>{if(!active||!$('reviewed').checked)return;const b=$('download');b.disabled=true;b.textContent='Creating ZIP…';try{const r=await fetch(`/api/generate/${encodeURIComponent(active.part)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true,distributor_brand:selectedDistributor(),staff_rrp_ex:staffApplied,staff_rrp_reviewed:!!staffApplied&&$('staffReview').checked,staff_rrp_basis:staffBasis})});if(!r.ok){const v=await r.json();throw Error(v.error||'Export failed')}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`LASER_${active.part}_Marketing_Pack.zip`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);setState('Marketing pack generated and downloaded.','success')}catch(e){setState(e.message,'error')}finally{b.disabled=false;b.innerText='Download all assets (ZIP) ↓';}});
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

def official_get(url,session=requests, content_types=None, timeout=12):
    if not authorized_url(url): raise LookupErrorPublic('Source URL is not on an approved Laser/Tool Connection domain.')
    r=session.get(url,headers=HEADERS,timeout=timeout,allow_redirects=True)
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
    '8899':'https://www.toolconnection.co.uk/products/cars-vans/steering-suspension/general-ball-joints/scissor/8899-ball-joint-separator-for-jlr',
    '9024':'https://www.toolconnection.co.uk/products/workshop/air-tools-accessories/air-tools/impact-wrenches/9024-air-impact-wrench-1-d-with-6-anvil',
    '9364':'https://www.toolconnection.co.uk/products/general-hand-tools/socketry/general-ratchets/mixed-sets/9364-ratchet-set-with-comfort-handle-3pc-50th-anniversary',
    '9365':'https://www.toolconnection.co.uk/products/general-hand-tools/socketry/general-ratchets/mixed-sets/9365-stainless-steel-high-quality-ratchet-set-4pc-50th-anniversary',
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
    '8899': ('£144.16 excluding VAT', OFFICIAL_UK_PRODUCTS['8899']),
    '9024': ('£510.35 excluding VAT', OFFICIAL_UK_PRODUCTS['9024']),
    '9364': ('£101.48 excluding VAT', OFFICIAL_UK_PRODUCTS['9364']),
    '9365': ('£178.00 excluding VAT', OFFICIAL_UK_PRODUCTS['9365']),
}

# Official UK reference text, used only when live extraction yields no English details.
# This is a dated product-specific fallback, not a replacement for live data.
VERIFIED_UK_FACTS = {
    '9364': {
        'features': [
            'Three comfort-handle ratchets with 1/4-inch, 3/8-inch and 1/2-inch square drives.',
            'Chrome Vanadium construction with flat-sided handles designed to reduce pressure points.',
            'Each ratchet has a 72-tooth mechanism for controlled movement.',
            'Supplied in a toolbox-ready EVA foam tray.',
            'Part of the Laser Tools 50th anniversary range, with a special 50-year warranty subject to terms.',
        ],
        'specs': {
            'Number of pieces': '3',
            'Drive': '1/4-inch, 3/8-inch, 1/2-inch',
            'No. of teeth': '72',
            'Material': 'Chrome Vanadium',
            'Length': '145mm, 200mm, 240mm',
            'Storage': 'EVA foam tray',
        },
        'source': OFFICIAL_UK_PRODUCTS['9364'],
        'verified_on': '13 Nov 2026',
    },
    '9365': {
        'features': [
            'Four stainless-steel fine-tooth ratchets in a toolbox-ready EVA foam tray.',
            'Includes 1/4-inch hex bit, 1/4-inch, 3/8-inch and 1/2-inch square-drive ratchets.',
            'The small 1/4-inch and bit ratchets have 60-tooth mechanisms; larger ratchets have 72 teeth.',
            'Stainless-steel construction helps resist rust and corrosion.',
            'Part of the Laser Tools 50th anniversary range, with a special 50-year warranty subject to terms.',
        ],
        'specs': {
            'Number of pieces': '4',
            'Material': 'Stainless steel',
            'Drive': '1/4-inch hex, 1/4-inch, 3/8-inch, 1/2-inch',
            'No. of teeth': '60, 72',
            'Storage': 'EVA foam tray',
        },
        'source': OFFICIAL_UK_PRODUCTS['9365'],
        'verified_on': '13 Nov 2026',
    },
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
    '9024': {
        'features': [
            '1-inch drive air impact wrench with an extended 6-inch anvil for recessed wheel nuts.',
            'Maximum torque 2170Nm; nut-busting torque 3526Nm.',
            'Working torque 1763Nm at 5 seconds; loosening torque 3526Nm at 25 seconds.',
            'Noise level 98.5dB; air consumption 7cfm; length 520mm.',
            'Magnesium alloy and composite body, twin-hammer mechanism and side exhaust.',
            'Air inlet 3/8-inch BSPT; working air pressure 90psi.',
        ],
        'specs': {
            'Drive': '1-inch square drive',
            'Anvil': '6-inch extended',
            'Maximum torque': '2170Nm',
            'Nut-busting torque': '3526Nm',
            'Working pressure': '90psi',
            'Air consumption': '7cfm',
            'Noise level': '98.5dB',
            'Length': '520mm',
        },
        'source': OFFICIAL_UK_PRODUCTS['9024'],
        'verified_on': '13 Nov 2026',
    },
    '8899': {
        'features': [
            'Heavy-duty scissor-type ball joint separator for listed Land Rover and Jaguar applications.',
            'Suitable for Land Rover Discovery V (L462), Range Rover IV (L405) and Range Rover Sport II (L494).',
            'Inner opening 31mm; outer opening 52mm; upper jaw 215mm; lower jaw 220mm.',
            'Manufactured from heat-treated 45 carbon steel.',
            'Equivalent to JLR OEM 204-793A; follow the manufacturer instructions and grease guidance.',
        ],
        'specs': {
            'Type': 'Scissor',
            'Material': 'Heat-treated carbon steel',
            'Jaw width': '31mm',
            'Depth': '52mm',
            'Length': '220mm',
            'Equivalent OEM': 'JLR 204-793A',
            'Vehicle manufacturer': 'Land Rover, Range Rover',
        },
        'source': OFFICIAL_UK_PRODUCTS['8899'],
        'verified_on': '13 Nov 2026',
    },
}

# High-confidence French technical phrases which a simple stop-word count misses,
# e.g. "En acier au carbone 45 traité thermiquement" from the 8899 PDF.
FRENCH_STRONG = re.compile(
    r'\b(?:en\s+acier|acier\s+au\s+carbone|trait[ée]s?\s+thermiquement|'
    r'm[âa]choire|[ée]cartement|[ée]crou|[ée]carter|[ée]cart[ée]|'
    r's[ée]parateur\s+de|rotule|[ée]quivalent\s+[àa]|conform[ée]ment|'
    r'toujours\s+lubrifier|les\s+applications|utilis[ée]\s+pour|'
    r'de\s+mani[èe]re|mise\s+en\s+place|ressort|d[ée]montage|'
    r'avec\s+un|pour\s+une|sur\s+les|pour\s+le|l[’\\x27]utilisation|'
    r'les\s+v[ée]hicules|outil\s+de)\b',
    re.I
)
FRENCH_TECH_TERMS = re.compile(r'\b(?:méthode|syphonage|siphonnage|unidirectionnelle|réservoir|système|purge|purger|pressurisation|pression|dépose|repose|moyeu|lorsque|pourra|destiné|vissage|suffisante|particulier|nécessitant|remplissage|permettant)\b',re.I)

FOREIGN_MARKERS = re.compile(r"\b(?:les|des|une|pour|avec|sans|afin|lors|sur|roulement|véhicules|comprend|comprennent|utilisation|également|assurer|remarque|utiliser|atelier|montage|pression|permettre|adapté|nécessaire|pièces|dépose|repose|cette|conçu|références|nettoyer|veiller|éviter|outil|lesquels|auxquels|cette|ceci|du|le|la|et)\b", re.I)

# Foreign-language markers are not a replacement for language detection:
# the official PDFs sometimes contain Dutch, French and German content.
DUTCH_TECH=re.compile(
    r'\b(?:slagmoersleutel|buitenmantel|slagmoersleutels|wielmoeren|'
    r'losdraaimoment|luchtdruk|luchtverbruik|geluidsniveau|'
    r'magnesiumlegering|tweevoudige|schroefdraad|uitgerust|'
    r'verlengde|onderhoudswerkzaamheden|luchtgereedschap|'
    r'voertuigreparatie|werklast|gebruiksvriendelijk)\b',re.I)
DUTCH_WORDS=re.compile(
    r'\b(?:met|een|het|voor|van|deze|zijn|door|zoals|'
    r'wordt|kunnen|zonder|gebruik|gemonteerd|hierdoor|'
    r'verwijderen|tijdens|aanbrengen|snelheid|'
    r'gewicht|maximumkoppel|aandrijving|onderdeel|'
    r'werkplaats|wagen|luchtinlaat|dubbel|'
    r'bevat|werkdruk|geschikt)\b',re.I)
GERMAN_TECH=re.compile(
    r'\b(?:Drehmoment|Druckluft|Schlagschrauber|Werkzeugstahl|'
    r'geeignet\s+für|Fahrzeuge|Verwendung|Ausführung|'
    r'Kugellager|Montagewerkzeug)\b',re.I)
SPANISH_TECH=re.compile(
    r'\b(?:herramienta|vehículos|rodamiento|para\s+la|'
    r'presión\s+de|aplicaciones|fabricado|incluye)\b',re.I)
FOREIGN_FUNCTION_WORDS=re.compile(
    r'\b(?:de|het|een|voor|met|van|deze|zonder|'
    r'pour|avec|une|les|des|dans|sur|'
    r'und|mit|für|der|die|das|zum|'
    r'para|con|los|las|una|del)\b',re.I)



# Additional Dutch vocabulary in actual supplier records (including 4554).
DUTCH_PRODUCTS = re.compile(
    r'\b(?:snijbekken|taphouders?|verstelbare|tappen|snijplaten|'
    r'snijgereedschap|tapsleutel|geleverd|gemonteerde|gemaakt|'
    r'gelegeerd|staal|kunststof|behuizing|opbergen|stevige|'
    r'veilig|verschillende|maten|elk|ieder|dubbele|snijder|'
    r'bewaardoos|meegeleverd|draadreparatie|schroefdraad|'
    r'werkstuk|bestaat|inclusief|bereik|om\s+te)\b', re.I
)
DUTCH_PATTERNS = re.compile(
    r'\b(?:van\s+elk|geleverd\s+in|gemaakt\s+van|'
    r'voor\s+het|om\s+te|met\s+een|in\s+een|'
    r'elk\s+en|en\s+snijbekken)\b', re.I
)
ENGLISH_SAFETY_WORDS = re.compile(
    r'\b(?:for|with|includes?|supplied|designed|suitable|'
    r'manufactured|allows?|provides?|features?|professional|'
    r'removal|installation|workshop|capacity|adjustable|'
    r'rechargeable|applications?|vehicles?|steel|tool|'
    r'repairs?|press|bearing|joint|set|wrench|drive)\b', re.I
)

def is_non_english(text):
    """Conservatively reject non-English marketing copy, never translate specs.

    Exact model names, isolated measurements and brief technical labels are kept
    because statistical language identification is unreliable on short strings.
    """
    phrase=normalize(text)
    if not phrase:return False
    if (FRENCH_STRONG.search(phrase) or FRENCH_TECH_TERMS.search(phrase)
        or DUTCH_TECH.search(phrase) or GERMAN_TECH.search(phrase)
        or SPANISH_TECH.search(phrase)):
        return True
    if DUTCH_PATTERNS.search(phrase):return True
    dutch_hits=len(DUTCH_PRODUCTS.findall(phrase))+len(DUTCH_WORDS.findall(phrase))
    if len(DUTCH_PRODUCTS.findall(phrase))>=1 and dutch_hits>=2:return True
    if dutch_hits>=3:return True
    french_words=FOREIGN_MARKERS.findall(phrase)
    if len(french_words)>=2:return True
    if len(french_words)>=1 and re.search(r'[àâçéèêëîïôùûüÿœæ]',phrase,re.I):return True
    alphabet=re.findall(r'[A-Za-zÀ-ÿ]+',phrase)
    if len(alphabet)<5:return False
    try:
        likely=detect_langs(phrase)
        if likely and likely[0].lang in ('nl','fr','de','es','it','pt','pl'):
            threshold=.76 if len(alphabet)>=8 else .88
            # Never reject fluent English just because a statistical model
            # misclassified specialist workshop jargon or measurements.
            # Require actual foreign function words or multiple Dutch terms.
            if likely[0].prob>=threshold and (
                (FOREIGN_FUNCTION_WORDS.search(phrase)
                 and not ENGLISH_SAFETY_WORDS.search(phrase))
                or dutch_hits>=2
            ):return True
    except LangDetectException:
        pass
    return False


def is_french(text):
    """Compatibility wrapper: now rejects other languages too."""
    return is_non_english(text)


def english_only_features(features):
    output=[]
    seen=set()
    for feature in features or []:
        phrase=normalize(feature)
        key=phrase.casefold().strip(' .')
        if (not phrase or key in seen or is_non_english(phrase)
            or re.search(r'\b(?:N\.B\.|REMARQUE)\s*:',phrase,re.I)):
            continue
        seen.add(key)
        output.append(phrase)
    return output


def english_only_specs(specs):
    return {k:v for k,v in (specs or {}).items()
            if not is_non_english(str(k)+' '+str(v))}


def english_description(text):
    """Do not let translated PDF sentences leak into poster-purpose copy."""
    original=normalize(text)
    if not original:return ''
    parts=re.split(r'(?<=[.!?])\s+(?=[A-Za-zÀ-ÿ])',original)
    good=[part for part in parts if part and not is_non_english(part)]
    if not good:return ''
    return normalize(' '.join(good))[:900]


def normalise_product_language(product):
    """Last line of defence for the record and every generated artwork format."""
    result=dict(product)
    if is_non_english(result.get('title','')):
        raise LookupErrorPublic('Official English product name unavailable for this part number.')
    # Keep source audit text while filtering customer-facing facts.
    if 'source_raw_features' not in result:
        result['source_raw_features']=[str(v) for v in result.get('features',[])]
    result['features']=english_only_features(result.get('features',[]))
    result['specs']=english_only_specs(result.get('specs',{}))
    result['description']=english_description(result.get('description',''))
    if not result['description']:
        result['description']=(result['features'][0] if result['features']
                               else 'Refer to the official English manufacturer product information.')
    return result


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
    paras=[x for x in paras if 80<len(x)<1100 and not is_non_english(x) and not re.search(r'(cookies|privacy policy|terms and conditions)',x,re.I)]
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
    """Exact part-number studio JPEGs from approved Laser Tools domains."""
    return [
        f'https://www.lasertools.co.uk/items/large/{part}.jpg',
        f'https://lasertools.toolconnection.co.uk/items/large/{part}.jpg',
        f'https://www.lasertools.co.uk/items/XLarge/{part}.jpg',
        f'https://lasertools.toolconnection.co.uk/items/XLarge/{part}.jpg',
    ]

def manufacturer_gallery_urls(part,session=requests):
    """Discover product photographs from the manufacturer's real gallery."""
    urls=[]
    for page in [f'https://www.lasertools.co.uk/Product/{part}',
                 f'https://lasertools.toolconnection.co.uk/Product/{part}']:
        try:
            response=official_get(page,session,timeout=6)
            soup=BeautifulSoup(response.content,'html.parser')
            for node in soup.find_all(['a','img','source']):
                for key in ('href','src','data-src','data-large','data-original','data-zoom-image','srcset'):
                    raw=(node.get(key) or '').split(',')[0].strip().split(' ')[0]
                    if not raw:continue
                    url=urljoin(response.url,html.unescape(raw))
                    if not authorized_url(url):continue
                    basename=urlparse(url).path.rsplit('/',1)[-1]
                    regex=re.escape(part)+r'(?:[_-][^/]*)?\.(?:jpe?g|png|webp)$'
                    if re.match(regex,basename,re.I):urls.append(url)
            if urls:break
        except Exception:pass
    return list(dict.fromkeys(urls))

def pdf_render_photo(pdfbytes):
    """Render composite product photo from PIS PDF to avoid broken stencil/mask xrefs."""
    doc=fitz.open(stream=pdfbytes,filetype='pdf')
    try:
        if doc.page_count<1:return None
        page=doc[0]
        areas=[]
        for block in page.get_text('dict').get('blocks',[]):
            if block.get('type')!=1:continue
            rect=fitz.Rect(block['bbox'])
            if rect.width>=65 and rect.height>=65 and rect.y0<page.rect.height*.77:
                areas.append(rect)
        for item in page.get_images(full=True):
            try:
                for rect in page.get_image_rects(item[0]):
                    if rect.width>=65 and rect.height>=65 and rect.y0<page.rect.height*.77:
                        areas.append(rect)
            except Exception:pass
        areas.sort(key=lambda r:r.width*r.height,reverse=True)
        checked=set()
        for rect in areas[:12]:
            key=(round(rect.x0/10),round(rect.y0/10),round(rect.width/10),round(rect.height/10))
            if key in checked:continue
            checked.add(key)
            clip=fitz.Rect(max(0,rect.x0-12),max(0,rect.y0-12),
                           min(page.rect.width,rect.x1+12),min(page.rect.height,rect.y1+12))
            data=page.get_pixmap(matrix=fitz.Matrix(2.3,2.3),clip=clip,alpha=False).tobytes('png')
            if valid_image(data):return data
        return None
    finally:doc.close()


def lookup(part,session=requests,force=False,uk_url=None):
    part=sku_clean(part)
    if uk_url:
        uk_url=uk_url.strip()
        if not (authorized_url(uk_url) and urlparse(uk_url).hostname in ('www.toolconnection.co.uk','toolconnection.co.uk')
                and re.search(r'/products/.*/'+re.escape(part)+r'(?:-|$)',urlparse(uk_url).path,re.I)):
            raise LookupErrorPublic('Please paste the official UK Tool Connection product page URL for this exact part number.')
    now=time.time()
    if not force and not uk_url and part in CACHE:
        age_limit=3600 if CACHE[part][2] else 60
        if now-CACHE[part][0]<age_limit:return CACHE[part][1],CACHE[part][2]
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
    product=normalise_product_language(product)
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
    # Recheck the record after verified English fallbacks.
    product=normalise_product_language(product)
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
    # Product images: prefer genuine manufacturer studio gallery, not broken PDF xrefs.
    pdf_image=image_bytes if image_bytes and valid_image(image_bytes) else None
    image_bytes=None
    gallery=manufacturer_gallery_urls(part,session)
    studio=[url for url in gallery if not re.search(r'in.?situ',url,re.I)]
    candidates=preferred_manufacturer_photos(part)+studio
    candidates += [
        url for url in product.get('image_candidates',[])
        if re.search(r'/'+re.escape(part)+r'(?:[_./-]|$)',urlparse(url).path,re.I)
    ]
    product['photo_source']=None
    for photo_url in dict.fromkeys(candidates):
        try:
            response=official_get(photo_url,session,timeout=6)
            if valid_image(response.content):
                image_bytes=response.content
                product['photo_source']=response.url
                break
        except Exception:pass
    # PDFs may embed a black mask and a colour image as separate xrefs. Rendering
    # the visible page rectangle merges them, unlike extracting the xref directly.
    if image_bytes is None:
        for pdf_url in (f'https://www.lasertools.co.uk/pis/{part}_PIS.pdf',
                        f'https://lasertools.toolconnection.co.uk/pis/{part}_PIS.pdf'):
            try:
                pdf_response=official_get(pdf_url,session,content_types=['pdf'],timeout=8)
                composite=pdf_render_photo(pdf_response.content)
                if composite:
                    image_bytes=composite
                    product['photo_source']=pdf_url+'#rendered'
                    break
            except Exception:pass
    if image_bytes is None and pdf_image:
        image_bytes=pdf_image
        product['photo_source']='Image extracted from official product information sheet'
    # A separate *real* in-use photo gives the promotional advert a unique look.
    APPLICATION_IMAGE_CACHE.pop(part,None)
    product['application_photo_source']=None
    in_use=[url for url in gallery if re.search(r'in.?situ',url,re.I)]
    if not in_use:
        in_use=[
            f'https://www.lasertools.co.uk/items/large/{part}_InSitu.jpg',
            f'https://www.lasertools.co.uk/items/large/{part}_Insitu_1.jpg',
            f'https://www.lasertools.co.uk/items/large/{part}_InSitu_A.jpg',
        ]
    for photo_url in in_use[:3]:
        try:
            response=official_get(photo_url,session,timeout=6)
            if valid_image(response.content):
                APPLICATION_IMAGE_CACHE[part]=response.content
                product['application_photo_source']=response.url
                break
        except Exception:pass
    # Some products offer only an application photo. It is still a real,
    # part-specific manufacturer photograph, and preferable to no poster at all.
    if image_bytes is None and part in APPLICATION_IMAGE_CACHE:
        image_bytes=APPLICATION_IMAGE_CACHE[part]
        product['photo_source']=product['application_photo_source']
    product['photo_verified']=bool(image_bytes)
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

def with_reviewed_price(product,raw,approved=False,basis='ex'):
    """Accept a staff-reviewed UK RRP (ex- or inc-VAT) with honest provenance."""
    if raw is None or str(raw).strip()=='':return product
    if not approved:
        raise LookupErrorPublic('Tick the staff price review box before using an entered RRP.')
    if basis not in ('ex','inc'):
        raise LookupErrorPublic('Select whether the entered RRP includes or excludes VAT.')
    try:
        amount=Decimal(str(raw).strip()).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError):
        raise LookupErrorPublic('Enter a valid UK RRP amount.')
    if not amount.is_finite() or amount<=0 or amount>Decimal('500000'):
        raise LookupErrorPublic('Enter a positive UK RRP (maximum £500,000).')
    result={**product}
    description='including VAT' if basis=='inc' else 'excluding VAT'
    result['price']=f'£{amount:,.2f} {description}'
    result['price_status']='Staff-entered draft RRP — independently approve before publication'
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
    if request.path=='/' or request.path.startswith('/api/poster/') or request.path.startswith('/api/photo/'):
        response.headers['Cache-Control']='no-store, max-age=0'
    return response

@app.get('/api/health')
def health():return jsonify(ok=True,service='Laser Product Studio',design='v17-guided-premium-studio-safe-text',lookup='official page + PDF fallback')

@app.get('/api/lookup/<part>')
def product_lookup(part):
    try:
        product,image=lookup(part,uk_url=request.args.get('uk_url') or None)
        public_record={**product,'technical_layout':technical_layout_mode(product)}
        return jsonify(product=public_record,photo_url=f'/api/photo/{part}?design=v16' if image else None)
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
        product=normalise_product_language(safe_override(product,body.get('edits') or {}))
        product=with_reviewed_price(product,body.get('staff_rrp_ex'),body.get('staff_rrp_reviewed') is True,body.get('staff_rrp_basis','ex'))
        if not img:return jsonify(error='No verified official product photograph available; marketing posters will not be generated with a fabricated photo.'),422
        assets=create_posters(product,img,APPLICATION_IMAGE_CACHE.get(part))
        tech=create_fact_sheet_pdf(product,img,APPLICATION_IMAGE_CACHE.get(part))
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
        p=with_reviewed_price(p,request.args.get('staff_rrp_ex'),request.args.get('staff_rrp_reviewed')=='1',request.args.get('staff_rrp_basis','ex'))
        if not img:return jsonify(error='Verified product image missing'),422
        renderer={'Hero':render_hero,'Technical':render_technical,'Price':render_price}[style]
        artwork=renderer(p,img,APPLICATION_IMAGE_CACHE.get(part)) if style in ('Hero','Technical') else renderer(p,img)
        return send_file(io.BytesIO(artwork),mimetype='image/png',download_name=f'LASER_{part}_{style}.png')
    except LookupErrorPublic as e:return jsonify(error=str(e)),404

if __name__=='__main__':
    app.run(debug=True,host='127.0.0.1',port=5000)
