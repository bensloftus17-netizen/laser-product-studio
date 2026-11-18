"""Laser Product Studio: official-source data -> authentic-photo marketing assets.
Public-site pilot. Not affiliated with the official Laser Tools website.
"""
from __future__ import annotations
import io, re, json, time, zipfile, hashlib, logging, html, base64, secrets, threading
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
from english_numeric_specs import (translate_known_numeric_labels,
                                   normalise_numeric_spec_row, RAW_GERMAN_TECH)
DetectorFactory.seed = 0
from flask import Flask, request, jsonify, send_file, render_template_string

from poster import create_posters, create_fact_sheet_pdf, create_marketing_copy, render_hero, render_technical, render_price, technical_layout_mode
from brand_assets import BRAND_LABELS, get_brand_image
from marketing_intelligence import strategy_for
from official_taxonomy import (apply_official_taxonomy, taxonomy_snapshot,
                               catalogue_url_for_part)
from ai_concepts import propose as propose_ai_concepts, suggest_headlines as suggest_ai_headlines
from ai_promo_renderer import render_promo as render_ai_promo, FAMILIES as AI_PROMO_FAMILIES
from promo_scene_library import find_scene, classify_product, scene_reference as stock_scene_reference
from promo_art_direction import normalise_art_direction, editor_preferences, scene_treatment
from promo_selling_points import focus_concept
from promo_copy import compose_promotional_copy, normalise_copy_direction
from campaign_hub import build_campaign
from copy_rewriter import rewrite_copy

V7_HOME_PAGE = r'''
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Laser Product Studio | Official product data to marketing assets</title>
<link rel="stylesheet" href="/static/styles.css?design=v44-creative-editor">
</head><body>
<svg xmlns="http://www.w3.org/2000/svg" class="hub-icon-sprite" aria-hidden="true" focusable="false">
 <symbol id="hub-home" viewBox="0 0 24 24"><path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7"/></symbol>
 <symbol id="hub-campaign" viewBox="0 0 24 24"><path d="M3 10 17 5v14L3 14zM7 15l2 6h3l-2-7M20 8v8"/></symbol>
 <symbol id="hub-saved" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h5l3 3h6a2 2 0 0 1 2 2v10H3zM12 11l1.2 2.4 2.8.4-2 2 .5 2.7-2.5-1.5-2.5 1.5.5-2.7-2-2 2.8-.4z"/></symbol>
 <symbol id="hub-image" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.4"/><path d="m3 18 5-5 4 4 3-3 6 6"/></symbol>
 <symbol id="hub-stack" viewBox="0 0 24 24"><path d="m12 3 9 5-9 5-9-5zM3 12l9 5 9-5M3 16l9 5 9-5"/></symbol>
 <symbol id="hub-spark" viewBox="0 0 24 24"><path d="m12 2 2.3 7.7L22 12l-7.7 2.3L12 22l-2.3-7.7L2 12l7.7-2.3z"/></symbol>
 <symbol id="hub-chart" viewBox="0 0 24 24"><path d="M3 20V11h4v9M10 20V5h4v15M17 20v-8h4v8M2 20h20"/></symbol>
 <symbol id="hub-copy" viewBox="0 0 24 24"><path d="M8 4h11a2 2 0 0 1 2 2v14H8zM3 8h3M3 12h3M3 16h3"/></symbol>
 <symbol id="hub-download" viewBox="0 0 24 24"><path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/></symbol>
</svg>
<header class="studio-topbar">
 <a class="studio-brand" href="#builder" aria-label="Laser Tools Marketing Hub home">
  <span class="studio-mark">LASER<span>TOOLS</span></span>
  <span class="studio-brand-accent" aria-hidden="true"></span>
  <span class="studio-brand-title">Laser Product Studio<small>Marketing Hub for Laser Tools products</small></span>
 </a>
 <nav class="studio-top-links" aria-label="Primary navigation">
  <a href="#builder" class="active"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-home"></use></svg> Home</a><a href="#studioWorkspace"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-campaign"></use></svg> Campaigns</a><a href="#assetWorkspace"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-image"></use></svg> Assets</a>
  <a href="#savedPromotions"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-saved"></use></svg> Saved Promotions</a>
  <span title="Reports are planned for a future release"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-chart"></use></svg> Reports <small>Soon</small></span>
 </nav>
 <span class="studio-pilot-tag">INTERNAL PILOT · REVIEW REQUIRED</span>
</header>
<aside class="studio-sidebar" aria-label="Workspace navigation">
 <div class="sidebar-label">MARKETING WORKSPACE</div>
 <nav class="sidebar-menu">
  <a class="active" href="#builder"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-home"></use></svg> Dashboard</a>
  <a href="#builder"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-campaign"></use></svg> Create Campaign</a>
  <a href="#savedPromotions"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-saved"></use></svg> Saved Promotions <small>Soon</small></a>
  
  <a href="#assetWorkspace"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-image"></use></svg> Asset Library</a>
  
  <span class="sidebar-future" title="Reports are a planned feature"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-chart"></use></svg> Reports <small>Soon</small></span>
 </nav>
 <div class="sidebar-section"><b>CAMPAIGN WORKFLOW</b><p>Enter a part number, generate assets, review your copy and download a complete draft pack.</p></div>
 <div class="sidebar-bottom">Laser Product Studio <span>Internal pilot · v1</span></div>
</aside>
<main class="studio-main">
<div class="wrap app-shell" id="builder">
<div class="steps-panel" hidden><div class="steps-heading"><b>Three simple steps</b><span>From product lookup to marketing materials</span></div><ol class="steps" aria-label="Poster creation steps"><li class="step active" data-step="1" aria-current="step"><span class="step-num">1</span><div><b>Find your product</b><small>Enter a part number</small></div></li><li class="step" data-step="2"><span class="step-num">2</span><div><b>Review the details</b><small>Check imagery and RRP</small></div></li><li class="step" data-step="3"><span class="step-num">3</span><div><b>Download the posters</b><small>Three ready-to-review drafts</small></div></li></ol></div>
<section class="searchpanel"><div class="lookup-heading"><div><div class="sectioncap">ONE-CLICK PRODUCT MARKETING</div><h2>Build a Unique Product Campaign</h2><p>Enter a part number. AI plans three different, product-specific posters, real workshop imagery, story suggestions and editable copy.</p></div><span class="lookup-chip">OFFICIAL SOURCE CONTENT</span></div>
<form id="searchForm"><label class="inputlabel" for="part">LASER TOOLS PART NUMBER</label><div class="searchrow"><input id="part" type="text" pattern="[0-9A-Za-z.\-]{3,16}" maxlength="16" value="9395" placeholder="e.g. 9395" required autocomplete="off"><button class="campaign-start" id="campaignBtn" type="button">✦ Build Campaign</button></div></form>
<div class="studio-hero-art" aria-hidden="true"><img id="heroProductPhoto" src="/api/photo/9395" alt="" onerror="this.hidden=true"></div>
<p id="campaignStatus" class="campaign-feedback" role="status" aria-live="polite">Enter a part number to begin. Generated marketing requires review before publication.</p>
<div id="campaignRecovery" class="campaign-mobile-recovery" hidden>
 <span id="campaignRecoveryText">Your last campaign may still be available.</span>
 <button type="button" id="campaignResume">Reopen campaign</button>
</div>
<details id="campaignSettings" class="campaign-settings">
 <summary>Distributor branding, product lookup and pricing settings <span>Optional</span></summary>
 <div class="campaign-settings-content">
<div class="examples"><span>Try an example:</span><button class="linkchip" type="button" data-part="9364">9364 · Ratchet set</button><button class="linkchip" type="button" data-part="9395">9395 · Bearing kit</button><button class="linkchip" type="button" data-part="9365">9365 · 4pc set</button><button class="linkchip" type="button" data-part="9372">9372 · 50t press</button><button class="linkchip" type="button" data-part="8324">8324 · Hub spreader</button></div>
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
</div></details>
<button class="studio-preview-trigger secondary" id="searchBtn" type="button" hidden>Look up manufacturer details</button>
 </div>
</details>
<p id="status" class="status" role="status" aria-live="polite">Ready to find a Laser Tools product.</p></section>

<section class="studio-quickbar" aria-label="Campaign formats and quick actions">
 <div class="quickbar-item"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-campaign"></use></svg><b>3</b><small>Technical · Price · Product-selected</small></div>
 <div class="quickbar-item"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-image"></use></svg><b>9</b><small>Core artwork files</small></div>
 <div class="quickbar-item"><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-download"></use></svg><b>1</b><small>Complete ZIP download</small></div>
 <div class="quickbar-actions"><strong>QUICK ACTIONS</strong>
  <a href="#assetWorkspace">View campaign assets</a><a href="#copyWorkspace">Edit campaign copy</a>
 </div>
</section>
<section class="studio-workspace" id="studioWorkspace" aria-label="Campaign workspace">
 <section class="asset-workspace" id="assetWorkspace" aria-label="Campaign asset previews">
  <div class="workspace-heading"><div><h2><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-image"></use></svg> Campaign Asset Preview</h2><p id="assetWorkspaceStatus">Three unique posters, Instagram Story and banners will appear after Build Campaign.</p></div><span class="workspace-secondary-note">One campaign builder</span></div>
 </section>
 <section class="copy-workspace" id="copyWorkspace" aria-label="Marketing copy editor">
  <div class="workspace-heading"><div><h2><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-copy"></use></svg> Copy Editor</h2><p>Choose a channel, refine wording and copy it in one place.</p></div></div>
  <div id="copyEmpty" class="studio-empty-copy"><span aria-hidden="true">✎</span><b>Marketing copy ready when you are</b><p>Generate a campaign to preview social, LinkedIn, email and web copy here.</p></div>
 </section>
</section>
<section class="saved-promotions" id="savedPromotions" aria-label="Saved promotions future feature">
 <div class="saved-heading"><div><h2><svg class="hub-icon" aria-hidden="true" focusable="false"><use href="#hub-saved"></use></svg> Saved Promotions Library <span>Coming soon</span></h2><p>Save, reopen, duplicate and organise promotions in a future release.</p></div></div>
 <div class="saved-not-yet"><span aria-hidden="true">☆</span><div><b>Saved campaigns are not enabled yet</b><p>Your finished campaigns can be downloaded as ZIP files today. A searchable library will be added later — no campaigns are being stored by this demo.</p></div></div>
</section>
<details class="taxonomy-explorer" id="taxonomyExplorer">
 <summary>Browse Laser Tools categories &amp; preferred marketing strategies
 <small>Official website hierarchy · product-aware marketing plans</small></summary>
 <div class="taxonomy-explorer-content">
  <label for="taxonomySearch">Find a category or subcategory</label>
  <input id="taxonomySearch" type="search" placeholder="e.g. Engine Timing, Socket Sets, Battery Tools" autocomplete="off">
  <p id="taxonomyCoverage" class="taxonomy-coverage">Full part-number catalogue import not yet completed.</p>
  <p id="taxonomyCount" role="status" aria-live="polite">Open this section to load the category directory.</p>
  <div id="taxonomyMatches"></div>
  <p class="taxonomy-accuracy">Category names are a dated snapshot of the official Laser navigation. A part number is only shown as website-classified when its exact official product URL confirms that path. Suggested audiences and channels need sales-team review.</p>
 </div>
</details>
<details class="studio-deep-tools" id="productStudio" hidden aria-hidden="true">
 <summary>Legacy product poster tools (not part of unified campaign flow)</summary>
 <div id="productRecordSlot" class="record-dock"></div>
 <div id="advancedStudioSlot" class="advanced-dock"></div>
</details>
<div class="content"><aside class="record-panel"><div class="panel-heading"><span class="panel-step">02</span><div><div class="sectioncap">OFFICIAL PRODUCT RECORD</div><h2>Review product details</h2><p>Check the information before sharing.</p></div></div><div id="record" class="record"><div class="placeholder"><div class="placeholder_icon">⌕</div><b>Search for a product</b><p>Official details and photography appear here.</p></div></div></aside>
<section class="right"><div class="previewtop"><div class="panel-heading"><span class="panel-step">03</span><div><div class="sectioncap">YOUR MARKETING ASSETS</div><h2>Campaign posters</h2><p>Three different roles, layouts and verified selling points for this specific tool.</p></div></div><span class="formats-chip">3 FORMATS</span></div>
<div id="previews" class="previews"><div class="posterempty"><b>Your posters will appear here</b><p>Enter a part number to create three branded previews.</p></div></div>
<section class="campaign-dashboard" id="campaignResults" hidden aria-label="Complete marketing campaign">
<div class="campaign-results-heading"><div><span class="sectioncap">ONE-CLICK CAMPAIGN / READY TO REVIEW</span><h3 id="campaignTitle">Your campaign pack</h3><p id="campaignSummary">Review all copy, image rights and prices before publishing.</p><p id="campaignQuality" class="campaign-quality" aria-live="polite"></p></div><div class="campaign-download-choice">
 <button type="button" id="campaignShareSocial" class="asset-share-button share-primary" data-share-url="" data-share-filename="">↗ Share social graphic</button>
 <small class="share-app-targets">WhatsApp · Instagram · Facebook</small>
 <a id="campaignDownload" class="campaign-download" href="#" download>Download complete ZIP ↓</a>
 <button type="button" id="campaignShareZip" class="asset-share-button" data-share-url="" data-share-filename="">↗ Share complete ZIP</button>
 <small>Nothing downloads automatically. Sharing is optional too.</small>
 </div></div>
<section class="marketing-strategy-panel" id="marketingStrategyPanel" hidden aria-label="Product-specific AI marketing strategy">
 <div class="marketing-strategy-heading"><div><span class="sectioncap">PRODUCT-SPECIFIC MARKETING INTELLIGENCE</span><h4>Recommended marketing approach</h4></div><span id="strategyMethod" class="strategy-method"></span></div>
 <div class="marketing-strategy-grid">
  <div class="strategy-field"><small id="strategyCategoryLabel">Product category</small><b id="strategyCategory"></b><span class="strategy-category-source" id="strategyCategorySource"></span></div>
  <div class="strategy-field"><small>Suggested target audience</small><b id="strategyAudience"></b></div>
  <div class="strategy-field"><small>Recommended sales angle</small><b id="strategyFocus"></b></div>
  <div class="strategy-field"><small>Recommended channels</small><b id="strategyChannels"></b></div>
 </div>
 <div class="marketing-proof"><small>Category-specific marketing strategy</small><p id="strategyLens"></p><small>Why this is recommended</small><p id="strategyReason"></p><small>Verified manufacturer selling point</small><p id="strategyProof"></p></div>
 <p class="strategy-warning">Audience and channel recommendations are marketing hypotheses, not verified prospects. The team must approve the approach and all manufacturer claims before publication.</p>
</section>
<div class="campaign-angle-cards" id="campaignAngles"></div>
<div class="campaign-role-note">These posters serve different purposes: technical/application, price promotion and a third category-specific marketing angle. The actual Laser Tools product photo is always genuine.</div>
<h4>Three posters · Story · Social · Banners</h4><p id="campaignAssetCount" class="campaign-count" role="status" aria-live="polite"></p><p class="share-lead">Share an image directly from the website — no need to save it to Files first. Your phone's share sheet lets you choose an installed app.</p><div class="campaign-asset-grid" id="campaignAssets"></div><p class="share-help">Tap <b>Share to apps</b> and select WhatsApp, Instagram, Facebook or another compatible option in your phone's share sheet. App availability and supported formats vary. Suggested captions are in the Copy Editor.</p>

<section class="campaign-poster-editor" id="campaignPosterEditor" hidden aria-label="Edit selected poster">
 <div class="poster-edit-heading"><div><span class="sectioncap">EDIT VERIFIED CAMPAIGN POSTER</span><h4 id="posterEditTitle">Edit one poster</h4><p>Manufacturer photo, part number and verified price remain locked.</p></div><button type="button" id="posterEditClose" class="ai-secondary">Close</button></div>
 <div class="poster-edit-controls">
  <label for="posterEditHeadline">Headline (official product name)<input id="posterEditHeadline" maxlength="120" autocomplete="off"></label>
  <label for="posterEditFeature">Manufacturer-verified featured fact<select id="posterEditFeature"></select></label>
  <label for="posterEditVariant">Layout variation<select id="posterEditVariant"><option value="0">Layout 1</option><option value="1">Layout 2</option><option value="2">Layout 3</option></select></label>
 </div>
 <p class="poster-edit-disclaimer">Use an exact excerpt of the official title and select a genuine manufacturer fact. This updates only the chosen poster and its version in the downloadable ZIP. Existing Copy Editor drafts are unchanged.</p>
 <div class="poster-edit-actions"><button type="button" class="primary" id="posterEditSave">Update this poster</button><span id="posterEditStatus" role="status" aria-live="polite"></span></div>
</section>
<section class="campaign-social-ideas" id="campaignSocialIdeas" hidden aria-label="Instagram Story and social suggestions">
 <h4>Instagram Story &amp; sharing suggestions</h4>
 <p>Use the suggested story sequence alongside the individual shareable graphics. All wording needs review.</p>
 <div id="storySuggestions" class="story-suggestion-cards"></div>
 <div id="campaignSocialTip" class="campaign-social-tip"></div>
 </section>
<p class="campaign-legal">DRAFT ONLY · Check current RRP, VAT, claims, applications, customer logo permissions and company approval before any external use.</p>
</section>
<section id="unifiedCopyStudio" class="campaign-copy-studio" hidden aria-label="Single marketing copy editor">
<div class="ai-copy-heading"><div><span id="copyStudioOrigin" class="sectioncap">CAMPAIGN COPY / READY-TO-EDIT DRAFTS</span><h3>Choose your marketing text</h3><p>Select a campaign angle and marketing channel to see the full suggested wording. Edit the draft, then copy the text you want to use.</p></div></div>
<div id="campaignCopyAngles" class="ai-copy-design-tabs" role="group" aria-label="Campaign selling angle"></div>
<div id="campaignCopyChannels" class="ai-copy-channels" role="group" aria-label="Marketing content type">
 <button type="button" data-campaign-channel="social_caption">Social caption</button>
 <button type="button" data-campaign-channel="linkedin_post">LinkedIn post</button>
 <button type="button" data-campaign-channel="email_body">Product email</button>
 <button type="button" data-campaign-channel="hashtags">Hashtags</button>
 <button type="button" data-campaign-channel="website_listing">Website listing</button>
 <button type="button" data-campaign-channel="short_message">Short promo</button>
</div>
<label id="campaignCopyLabel" class="ai-copy-label" for="campaignCopyText">Social caption</label>
<textarea id="campaignCopyText" rows="9" spellcheck="true" aria-label="Editable campaign copy text"></textarea>

<div class="rewrite-tools" aria-label="Improve suggested marketing copy">
 <div class="rewrite-tools-title"><b>✦ Improve this wording</b><span>AI-assisted · Verified product information only</span></div>
 <div class="rewrite-options" id="rewriteOptions" role="group" aria-label="Copy rewrite styles">
  <button type="button" data-rewrite-mode="shorter">Make shorter</button>
  <button type="button" data-rewrite-mode="professional">More professional</button>
  <button type="button" data-rewrite-mode="persuasive">More persuasive</button>
  <button type="button" data-rewrite-mode="technical">More technical</button>
  <button type="button" data-rewrite-mode="facebook">Rewrite for Facebook</button>
 </div>
 <div id="rewritePreview" class="rewrite-preview" hidden>
  <div class="rewrite-preview-heading"><b>Suggested rewrite</b><small id="rewriteMethod">Review before applying</small></div>
  <textarea id="rewritePreviewText" rows="6" readonly aria-label="Suggested rewrite preview"></textarea>
  <div class="rewrite-preview-actions">
   <button type="button" class="rewrite-apply" id="rewriteApply">Apply to text editor</button>
   <button type="button" class="rewrite-discard" id="rewriteDiscard">Keep original</button>
  </div>
 </div>
 <div class="rewrite-bottom"><button type="button" id="rewriteUndo" class="rewrite-undo" hidden>↶ Undo last rewrite</button>
 <span id="rewriteStatus" role="status" aria-live="polite">Choose a style to preview a safer, more polished version.</span></div>
</div>
<div class="ai-copy-actions"><button type="button" id="campaignCopyCurrent" class="ai-secondary">Copy this text</button>
<button type="button" id="campaignCopyAll" class="ai-secondary">Copy all campaign wording</button>
<button type="button" id="campaignCopyReset" class="ai-secondary">Reset this draft</button>
<span id="campaignCopyStatus" role="status" aria-live="polite"></span></div>
<p id="copyStudioNote" class="ai-copy-disclaimer">Your edits are kept when changing tabs. Review all wording before publishing.</p>
</section>
<section class="ai-explore" id="aiExplore" hidden aria-hidden="true"><div class="ai-explore-top"><div><span class="sectioncap">OPTIONAL / GENERATIVE AI</span><h3>Three AI promotional designs</h3><p>One click makes three photographic promotional campaigns matched to the actual tool: battery chargers with car-battery service scenes, engine tools with engine workshops, and more. Real manufacturer product photos, licensed background photography and verified prices. No prompts needed.</p></div><button type="button" class="primary" id="generateAI" disabled>✦ Generate with AI</button></div><div id="aiIdeas" class="ai-ideas" aria-live="polite"></div>
</section><section id="aiEditor" class="ai-editor" hidden aria-label="Edit selected AI promotional poster">
<div class="ai-editor-heading"><div><span class="sectioncap">DESIGN EDITOR / SELECTED POSTER</span><h3 id="aiEditorTitle">Edit AI poster</h3><p>Personalise this poster without affecting the other two. The genuine product photo and verified RRP stay locked.</p></div><button type="button" id="aiEditorClose" class="ai-close">Close editor ✕</button></div>
<div class="ai-editor-main"><div class="ai-editor-visual"><img id="aiEditorPreview" alt="Live selected AI poster artwork preview" src=""><a id="aiEditorDownload" download="Laser_AI_edited_poster.png" href="#">Download edited PNG ↓</a><button type="button" id="aiEditorShare" class="asset-share-button share-primary">↗ Share edited image to apps</button><small>Your edits update this poster in the gallery. Download to keep a copy.</small></div>
<form id="aiEditorForm" class="ai-editor-controls">
 <label for="aiEditHeadline">Promotional headline</label><input id="aiEditHeadline" type="text" minlength="1" maxlength="48" required placeholder="e.g. Ford EcoBlue Crankshaft Pulley Removal">
 <div class="ai-two-cols"><div><label for="aiEditTone">Headline tone</label><select id="aiEditTone"><option value="trade">UK trade / workshop</option><option value="technical">Technical / application</option><option value="premium">Premium / understated</option><option value="sales">Product benefits</option></select></div><div><label for="aiEditHeadlineSize">Headline size</label><select id="aiEditHeadlineSize"><option value="small">Compact</option><option value="normal" selected>Balanced</option><option value="large">Large</option></select></div></div>
 <div class="ai-headline-buttons"><button type="button" id="aiGenerateOneHeadline" class="ai-secondary">✦ New headline only</button><button type="button" id="aiSuggestHeadlines" class="ai-secondary">✦ Suggest 3 headlines</button></div><div id="aiHeadlineChoices" class="ai-headline-choices" aria-live="polite"></div>
 <label class="ai-inline-check"><input id="aiEditShowSubline" type="checkbox"> Show supporting subheading</label><label for="aiEditSubline">Supporting subheading</label><input id="aiEditSubline" type="text" maxlength="82" placeholder="Optional short supporting line">
 <label for="aiEditPalette">Colour palette</label><select id="aiEditPalette"><option value="0">Style A</option><option value="1">Style B</option><option value="2">Style C</option></select>
 <div class="ai-colour-row"><div><label for="aiEditAccent">Accent colour</label><input id="aiEditAccent" type="color" value="#FFC82E"></div><div><label for="aiEditBgColour">Background colour</label><input id="aiEditBgColour" type="color" value="#056DB9"></div></div>
 <small class="ai-hint">Background tones are adjusted for readable Laser Tools branding.</small>
 <label for="aiEditBackground">Background / context</label><select id="aiEditBackground"><option value="clean">Clean brand background</option><option value="grid">Technical grid</option><option value="rings">Circular graphics</option><option value="context">Automatic real photo for this tool</option><option value="workshop">Real vehicle workshop photo</option><option value="bench">Real toolbench photo</option><option value="engine">Real engine-service photo</option></select>
 <div class="ai-two-cols"><div><label for="aiEditIntensity">Background strength <output id="aiEditIntensityValue">50</output>%</label><input type="range" id="aiEditIntensity" min="0" max="100" value="50"></div><div><label for="aiEditShapes">Graphic shapes</label><select id="aiEditShapes"><option value="0">None</option><option value="1">Subtle</option><option value="2" selected>Balanced</option><option value="3">Bold</option></select></div></div>
 <label for="aiEditSceneFile">Optional genuine workshop background photo</label><input type="file" id="aiEditSceneFile" accept="image/png,image/jpeg,image/webp"><button type="button" id="aiSceneRemove" class="ai-text-button">Remove uploaded background</button><small id="aiSceneNote" class="ai-hint">Upload an approved photo (max 2 MB), or use the curated genuine workshop images. Background stock photography does not demonstrate the specific tool.</small>
 <label for="aiEditDisplay">Product photo treatment</label><select id="aiEditDisplay"><option value="shadow">Clean cutout + soft shadow</option><option value="cutout">Cutout only</option><option value="glow">Cutout + subtle glow</option><option value="panel">Framed official photo</option></select>
 <div class="ai-three-sliders"><div><label for="aiEditScale">Product scale <output id="aiEditScaleValue">100</output>%</label><input id="aiEditScale" type="range" min="70" max="160" step="5" value="100"></div><div><label for="aiEditX">Horizontal <output id="aiEditXValue">0</output></label><input id="aiEditX" type="range" min="-100" max="100" step="10" value="0"></div><div><label for="aiEditY">Vertical <output id="aiEditYValue">0</output></label><input id="aiEditY" type="range" min="-100" max="100" step="10" value="0"></div></div>
 <label for="aiEditPriceStyle">RRP badge style</label><select id="aiEditPriceStyle"><option value="bubble">Circular price bubble</option><option value="plaque">Premium outlined plaque</option><option value="banner">Bold price banner</option><option value="tag">Angled price tag</option><option value="sticker">Promotional starburst sticker</option><option value="corner">Folded corner ticket</option><option value="panel">Large split-colour price panel</option></select>
 <label for="aiEditPricePosition">RRP placement</label><select id="aiEditPricePosition"><option value="standard">Original position</option><option value="opposite">Opposite side / alignment</option></select>
 <div class="ai-lock"><strong>Locked for accuracy</strong><span>Official tool photo · Part number · Product title · Verified RRP and VAT · Product features</span></div>
 <p id="aiEditStatus" class="ai-edit-status" aria-live="polite">Choose settings and apply your changes.</p>
 <button type="submit" id="aiEditApply" class="primary">Apply changes to this poster</button>
 <button type="button" id="aiEditRegenerate" class="ai-regenerate">✦ Regenerate this design</button>
 <small class="ai-hint">Regenerate asks Gemini for fresh product-specific wording in your selected tone. Manual layout changes do not call Gemini. The manufacturer photo and verified RRP cannot be replaced or altered here.</small>
</form></div></section><dialog class="ai-lightbox" id="aiPosterPreview" aria-label="Full-size AI promotional poster"><div class="ai-lightbox-top"><strong id="aiPosterTitle">AI promotional poster</strong><button type="button" id="aiPosterClose" aria-label="Close poster preview">Close ✕</button></div><img id="aiPosterImage" alt="Full-size AI poster preview" src=""></dialog><div class="reviewstrip"><label class="approval"><input type="checkbox" id="reviewed" disabled><span>I've checked the product information and posters</span></label><small>Company review required before publication.</small></div>
<div class="downloadbar"><div><b>Download your marketing pack</b><small>3 PNG posters · technical PDF · marketing copy · source information</small></div><div class="legacy-export-actions"><button id="download" disabled class="primary">Download all assets (ZIP) ↓</button><button type="button" id="legacyShareZip" class="asset-share-button" disabled>↗ Share prepared ZIP</button></div></div></section></div>
<section id="how" class="how"><div class="how-intro"><div class="sectioncap">MADE FOR REPS &amp; DISTRIBUTORS</div><h2>Simple from start to finish</h2><p>A faster way to prepare product marketing drafts using genuine manufacturer information.</p></div><div class="how-grid"><div><span class="how-icon">01</span><b>Find</b><p>Retrieve a genuine Laser Tools product image and official details.</p></div><div><span class="how-icon">02</span><b>Review</b><p>Check specifications, applications and UK pricing.</p></div><div><span class="how-icon">03</span><b>Download</b><p>Save promotional, technical and sales poster drafts.</p></div></div></section>
<footer><p>Independent internal pilot. Public Laser Tools / Tool Connection information is used with source attribution. Prices, product claims, artwork and imagery require approval before external release.</p></footer>
</div></main>
<div id="shareNotice" class="share-notice" role="status" aria-live="polite" hidden><span id="shareNoticeText"></span><button type="button" id="shareNoticeClose" aria-label="Dismiss sharing message">×</button></div>
<script>
const $=id=>document.getElementById(id);let campaignData=null;let active=null;let activePhoto=null;let staffApplied=null;let staffBasis='ex';let inflight=false;let aiConcepts=[],aiOriginals=[],currentAiEditor=-1,aiEditing=false;
function esc(s){return String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));}


// Native iOS/Android sharing. Image/ZIP blobs are prepared *before* the tap:
// Safari's Web Share API needs the user gesture to reach navigator.share()
// synchronously, not after waiting for a network fetch.
const preparedShareFiles=new WeakMap();
let legacyShareFile=null;
let shareNoticeTimer=null;
function canNativeShareFiles(){
 return typeof File==='function'&&typeof navigator.share==='function';
}
function showShareNotice(message){
 const notice=$('shareNotice');
 $('shareNoticeText').textContent=message;
 notice.hidden=false;
 if(shareNoticeTimer)clearTimeout(shareNoticeTimer);
 shareNoticeTimer=setTimeout(()=>{notice.hidden=true;},11000);
}
$('shareNoticeClose').addEventListener('click',()=>{$('shareNotice').hidden=true;});
function shareNativeFile(file){
 if(!file||!canNativeShareFiles()){
  showShareNotice('This browser cannot share files directly. Use Download PNG/ZIP, then share the saved file from Photos or Files.');
  return;
 }
 let shareable=true;
 if(typeof navigator.canShare==='function'){
  try{shareable=navigator.canShare({files:[file]});}catch(error){shareable=false;}
 }
 if(!shareable){
  showShareNotice(file.type==='application/zip'
   ?'Your phone does not support sharing ZIP files directly. Try an individual image or download the ZIP instead.'
   :'This browser will not send this image to other apps. Open the website in Safari or Chrome and use Share to apps there.');
  return;
 }
 // CRITICAL: call share() right in this tap handler, without awaits.
 try{
  const pending=navigator.share({files:[file]});
  Promise.resolve(pending).then(()=>showShareNotice('Share sheet completed. Check the receiving app before posting.'))
   .catch(error=>{
    if(error?.name==='AbortError')return;
    showShareNotice('The image could not be shared with that app. Download the PNG and share it from Photos instead.');
   });
 }catch(error){
  showShareNotice('Your browser could not open the share sheet. Download the file and share it from Photos or Files.');
 }
}
function fileFromPngDataUrl(dataUrl,filename){
 if(typeof dataUrl!=='string'||!dataUrl.startsWith('data:image/png;base64,')||typeof File!=='function')return null;
 const encoded=dataUrl.slice(dataUrl.indexOf(',')+1),binary=atob(encoded),bytes=new Uint8Array(binary.length);
 for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
 return new File([bytes],filename,{type:'image/png'});
}
function shareDataImage(dataUrl,filename){
 try{shareNativeFile(fileFromPngDataUrl(dataUrl,filename));}
 catch(error){showShareNotice('Could not prepare this image. Please use Download PNG.');}
}
function prepareShareButton(button){
 if(!button||!button.dataset.shareUrl||button.dataset.shareLoading==='1')return;
 if(!canNativeShareFiles()){
  button.disabled=false;
  button.title='Your browser may require you to download the file first';
  return;
 }
 const url=button.dataset.shareUrl,name=button.dataset.shareFilename||'LASER_Artwork.png';
 preparedShareFiles.delete(button);
 const kind=name.toLowerCase().endsWith('.zip')?'application/zip':'image/png';
 const originalLabel=button.textContent;
 button.disabled=true;button.textContent='Preparing share…';
 button.dataset.shareLoading='1';
 fetch(url,{credentials:'same-origin',cache:'no-store'}).then(response=>{
  if(!response.ok)throw Error('File no longer available');
  return response.blob();
 }).then(blob=>{
  if(button.dataset.shareUrl!==url)return;
  const file=new File([blob],name,{type:kind});
  // Cache for a direct tap. Never wait for fetch inside the share tap.
  // Some WebKit builds expose share() without canShare(); share() itself
  // will report unsupported file types, so keep download as the fallback.
  preparedShareFiles.set(button,file);
  button.disabled=false;button.textContent=originalLabel;
 }).catch(error=>{
  if(button.dataset.shareUrl!==url)return;
  button.disabled=false;button.textContent=originalLabel;
  button.title='Share preview unavailable — use the download link';
 }).finally(()=>{if(button.dataset.shareUrl===url)delete button.dataset.shareLoading;});
}
function prepareShareButtons(root){
 // On mobile, eagerly fetching a 5 MB ZIP plus every PNG for sharing can
 // exhaust Safari memory just as its artwork gallery is being displayed.
 // Preload ONLY after the user requests that individual share file.
 if(root)root.querySelectorAll('button[data-share-url]').forEach(button=>{
  button.disabled=false;
  button.title='Tap once to prepare this file; tap again to open the share sheet';
 });
}
document.addEventListener('click',event=>{
 const button=event.target.closest('button[data-share-url]');
 if(!button||button.disabled)return;
 const file=preparedShareFiles.get(button);
 if(file){shareNativeFile(file);return;}
 if(!canNativeShareFiles()){
  showShareNotice('This browser does not support sharing images directly. Open Laser Product Studio in Safari or Chrome to use the phone share sheet.');
  return;
 }
 showShareNotice('Preparing this image for sharing. Tap Share to apps again when preparation finishes — no download required.');
 // A failed preload can be retried without navigating away.
 if(button.dataset.shareLoading!=='1')prepareShareButton(button);
});
$('legacyShareZip').addEventListener('click',()=>{
 if(legacyShareFile)shareNativeFile(legacyShareFile);
});


let taxonomyExplorerRows=null;
function flattenTaxonomy(data){
 const result=[];
 (data.categories||[]).forEach(root=>{
  result.push({path:root.name,marketing:root.marketing});
  (root.departments||[]).forEach(group=>{
   const groupPath=root.name+' › '+group.name;
   result.push({path:groupPath,marketing:group.marketing});
   (group.subcategories||[]).forEach(leaf=>{
    result.push({path:groupPath+' › '+leaf.name,marketing:leaf.marketing});
   });
  });
 });
 return result;
}
function renderTaxonomyExplorer(){
 if(!taxonomyExplorerRows)return;
 const query=$('taxonomySearch').value.toLowerCase().trim();
 const matching=taxonomyExplorerRows.filter(item=>
  item.path.toLowerCase().includes(query)||(item.marketing?.label||'').toLowerCase().includes(query));
 $('taxonomyCount').textContent='Showing '+Math.min(40,matching.length)+' of '+matching.length+
  ' matching category paths. Refine the search to find a specific subcategory.';
 $('taxonomyMatches').innerHTML=matching.slice(0,40).map(item=>
  '<div class="taxonomy-result"><b>'+esc(item.path)+'</b><span>'+esc(item.marketing?.label||'Verified product marketing')+
  ' · '+esc((item.marketing?.channels||[]).join(' + '))+'</span></div>').join('')||
  '<p class="taxonomy-no-results">No category matches that search.</p>';
}
$('taxonomySearch').addEventListener('input',renderTaxonomyExplorer);
$('taxonomyExplorer').addEventListener('toggle',async()=>{
 if(!$('taxonomyExplorer').open||taxonomyExplorerRows)return;
 $('taxonomyCount').textContent='Loading official category directory…';
 try{
  const response=await fetch('/api/catalogue/taxonomy',{headers:{Accept:'application/json'}});
  const data=await readApiJson(response);
  taxonomyExplorerRows=flattenTaxonomy(data);
  $('taxonomyCoverage').textContent=(data.part_numbers_indexed||0)+
   ' official part-number URLs indexed so far; the full catalogue still needs an approved product export.';
  renderTaxonomyExplorer();
 }catch(error){$('taxonomyCount').textContent='Category directory unavailable. Refresh and try again.';}
});

function installMarketingHubLayout(){
 // Relocate existing functional controls into the approved dashboard structure.
 // IDs and event handlers remain unchanged; no duplicate editors or poster APIs.
 const assets=$('assetWorkspace'),copy=$('copyWorkspace');
 assets.appendChild($('previews'));
 assets.appendChild($('campaignResults'));
 copy.appendChild($('unifiedCopyStudio'));
 const record=document.querySelector('.record-panel');
 const advanced=document.querySelector('.right');
 $('productRecordSlot').appendChild(record);
 $('advancedStudioSlot').appendChild(advanced);
 const previewDialog=$('aiPosterPreview');
 if(previewDialog)document.body.appendChild(previewDialog);
 const old=document.querySelector('.content');
 if(old)old.hidden=true;
}
installMarketingHubLayout();
function refreshWorkspaceHeading(product){
 $('assetWorkspaceStatus').textContent=product
  ?'Part '+String(product.part||'')+' · '+String(product.title||'')+' — review all artwork before publishing.'
  :'Enter a product part number above to prepare the campaign assets.';
 if(product&&product.part){
  const image=$('heroProductPhoto');
  image.hidden=false;
  image.src='/api/photo/'+encodeURIComponent(product.part);
 }
}
function showCopyEmpty(){
 $('copyEmpty').hidden=!$('unifiedCopyStudio').hidden;
}
document.querySelectorAll('[data-open-studio]').forEach(control=>control.addEventListener('click',()=>{
 $('productStudio').open=true;
 $('productStudio').scrollIntoView({behavior:'smooth',block:'start'});
}));
document.querySelectorAll('[data-open-ai]').forEach(control=>control.addEventListener('click',()=>{
 $('productStudio').open=true;
 $('aiExplore').scrollIntoView({behavior:'smooth',block:'start'});
}));

function setState(message,type='neutral'){const el=$('status');el.className='status '+type;el.textContent=message;}
function selectedDistributor(){return $('distributorBrand').value;}
function clearCampaign(){campaignData=null;$('campaignResults').hidden=true;$('previews').hidden=false;if(copyStudioData?.origin==='campaign'){copyStudioData=null;rewriteNonce++;pendingCopyRewrite=null;rewriteUndoHistory={};$('unifiedCopyStudio').hidden=true;}showCopyEmpty();$('campaignStatus').textContent='Enter a part number to begin. Generated marketing requires review before publication.';}
function updateDistributorPreview(){
 legacyShareFile=null;$('legacyShareZip').disabled=true;
 const id=selectedDistributor(),target=$('distributorPreview');
 const labels={gsf:'GSF Car Parts',euro:'Euro Car Parts',mpd:'Motor Parts Direct'};
 target.innerHTML=id==='none'?'<span>LASER TOOLS ONLY</span>':
   '<img src="/api/distributor-logo/'+encodeURIComponent(id)+'" alt="'+esc(labels[id]||'Distributor')+' logo">';
 target.setAttribute('aria-label',id==='none'?'No customer branding':(labels[id]||'Selected customer logo'));
 if(active){
   $('reviewed').checked=false;$('download').disabled=true;
   setProgress(2);showPreviews(active,activePhoto);clearAiDesigns();clearCampaign();
   setState(id==='none'?'Laser Tools-only posters selected. Review the previews.':
     (labels[id]+' branding applied to all three poster previews. Review before downloading.'),'success');
 }
}
function reset(){legacyShareFile=null;$('legacyShareZip').disabled=true;$('generateAI').disabled=true;clearAiDesigns();clearCampaign();refreshWorkspaceHeading(null);setProgress(1);active=null;activePhoto=null;staffApplied=null;$('staffRrp').value='';$('staffRrpBasis').value='ex';$('staffReview').checked=false;$('reviewed').checked=false;$('reviewed').disabled=true;$('download').disabled=true;$('previews').innerHTML='<div class="posterempty">Retrieving genuine product details and photograph…</div>';}
function setProgress(stage){document.querySelectorAll('.step[data-step]').forEach(el=>{const n=Number(el.dataset.step);el.classList.toggle('active',n===stage);el.classList.toggle('complete',n<stage);if(n===stage)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');});}
function productCard(p,photo){const fs=(p.features||[]).filter(x=>x.length<180);const specs=Object.entries(p.specs||{}).slice(0,8).map(([k,v])=>'<div class="spec"><span>'+esc(k)+'</span><b>'+esc(v)+'</b></div>').join('');const warns=(p.warnings||[]).map(x=>'<p class="warn">'+esc(x)+'</p>').join('');const full=String(p.description||'');const desc=full.length>250?full.slice(0,244).replace(/\s+\S*$/,'')+'…':full;const staff=String(p.price_source||'').startsWith('Staff entry');return '<div class="found"><div class="sourcepill">✓ Official manufacturer record</div><h3><span class="sku-label">PART NO. '+esc(p.part)+'</span>'+esc(p.title)+'</h3><div class="recordphoto">'+(photo?'<img src="'+esc(photo)+'" alt="Official Laser Tools product image">':'<div class="nophoto">No verified photograph</div>')+'</div><div class="price"><span>'+(p.price?(staff?'Staff-reviewed draft RRP':'Manufacturer UK RRP'):'PRICE')+'</span><b>'+esc(p.price||'On request')+'</b><small>'+esc(p.price_status||(p.price?'Confirm before publishing':'No verified RRP available'))+'</small></div><div class="marketing-direction" id="product-marketing-direction"><div class="marketing-direction-title"><span class="marketing-direction-icon">✦</span><span>PRODUCT-AWARE MARKETING</span></div><div class="marketing-family"><b>'+esc(((p.marketing_direction||{}).site_category_path||[]).length
 ?(p.marketing_direction.site_category_path.join(' › '))
 :((p.marketing_direction||{}).category_label||'Category not confirmed'))+'</b><span class="marketing-mode">'+esc((p.marketing_direction||{}).visual_style||'workshop_essential')+'</span></div><div class="marketing-angle">'+esc((p.marketing_direction||{}).marketing_angle||'Verified product features and benefits')+'</div><div class="marketing-support">Automatically selects marketing priorities from the official product record. Review before publishing.</div></div><div class="record-summary"><h4>Product overview</h4><p>'+esc(desc)+'</p></div>'+(fs.length?'<div class="key-list"><h4>Key features</h4><ul>'+fs.slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>':'')+'<details class="record-details"><summary>View all product information</summary><div class="record-full"><h4>Full description</h4><p>'+esc(full)+'</p><h4>Features</h4><ul>'+fs.slice(0,8).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul><h4>Specifications</h4>'+(specs||'No further verified specifications')+'</div></details><div class="sourceinfo"><div>Source checked: '+esc(p.source_checked||'Not available')+'</div><a href="'+esc(p.source||'#')+'" target="_blank" rel="noopener noreferrer">Official product page ↗</a></div>'+warns+'</div>';}
function showPreviews(p,photo){if(!photo){$('previews').innerHTML='<div class="posterempty">No verified image was found. Posters are withheld rather than inventing a tool photograph.</div>';return;}const layouts=String(p.technical_layout||'').toLowerCase();const marketing=p.marketing_direction||{};const styles=[['Hero','01','Promotional advert',marketing.marketing_angle||'Product-led campaign'],['Technical','02','Technical information',layouts?layouts+' detail layout':'Product breakdown'],['Price','03','RRP / sales poster','Price-led customer sales material']];$('previews').innerHTML=styles.map(([key,num,title,desc])=>{const url='/api/poster/'+encodeURIComponent(p.part)+'/'+key+'?design=v19&distributor_brand='+encodeURIComponent(selectedDistributor())+(staffApplied?'&staff_rrp_ex='+encodeURIComponent(staffApplied)+'&staff_rrp_reviewed=1&staff_rrp_basis='+encodeURIComponent(staffBasis):'');return '<article class="posteritem"><div class="poster-cardheading">'+num+' / '+title+'</div><div class="posterthumb"><img loading="lazy" src="'+url+'" alt="'+esc(title)+' preview" onerror="this.onerror=null;this.style.display=\'none\';this.parentElement.insertAdjacentHTML(\'beforeend\',\'<span class=loaderror>Preview unavailable. Open full size to retry.</span>\')"></div><div class="posteritemfoot"><div><b>'+title+'</b><small>'+esc(desc)+'</small></div><div class="asset-links"><a target="_blank" rel="noopener noreferrer" href="'+url+'">View full size ↗</a><a download="LASER_'+esc(p.part)+'_'+key+'.png" href="'+url+'">Download PNG</a><button type="button" class="asset-share-button share-primary" data-share-url="'+esc(url)+'" data-share-filename="LASER_'+esc(p.part)+'_'+key+'.png">↗ Share to apps</button></div></div></article>';}).join('');prepareShareButtons($('previews'));}
// Render's free-hosting wake/deploy screen is HTML, NOT our product JSON.
// Never show a raw "Unexpected token <" error. GET lookups can safely retry;
// AI POST requests are not replayed because they may invoke a model.
async function readApiJson(response){
 const type=(response.headers.get('content-type')||'').toLowerCase();
 if(!type.includes('json')){
  const error=new Error(response.status===404?
   'Product lookup service was not found. Refresh the website and try again.':
   'The website server is starting up or temporarily unavailable. Please try again.');
  error.retryable=[200,429,500,502,503,504].includes(response.status);
  throw error;
 }
 let data;
 try{data=await response.json();}
 catch(parseError){
  const error=new Error('The server sent an incomplete response. Please retry.');
  error.retryable=true;throw error;
 }
 if(!response.ok){
  const error=new Error(data&&typeof data.error==='string'?data.error:'The server could not complete the request.');
  error.retryable=[429,502,503,504].includes(response.status);
  throw error;
 }
 return data;
}
async function lookupWithWakeRetry(url){
 // Exponential-ish delay while Render finishes starting. No duplicate Gemini
 // requests; only the safe GET lookup is automatically retried.
 const pauses=[1500,3000,5000,7000];
 for(let attempt=0;attempt<=pauses.length;attempt++){
  try{
   const response=await fetch(url,{headers:{'Accept':'application/json'},cache:'no-store'});
   return await readApiJson(response);
  }catch(error){
   if(!error.retryable&&!(error instanceof TypeError))throw error;
   if(attempt===pauses.length)
    throw new Error('The website is still starting. Select Find product again shortly.');
   setState('Render is waking up. Retrying product lookup ('+(attempt+1)+'/'+pauses.length+')…','working');
   await new Promise(resolve=>setTimeout(resolve,pauses[attempt]));
  }
 }
}
async function load(part){if(inflight)return;inflight=true;reset();const b=$('searchBtn');b.disabled=true;b.textContent='Retrieving official product…';setState('Looking up official product pages and product information sheets.','working');$('record').innerHTML='<div class="placeholder"><b>Searching official source…</b></div>';
try{const override=$('officialUrl').value.trim();const data=await lookupWithWakeRetry(`/api/lookup/${encodeURIComponent(part)}${override?'?uk_url='+encodeURIComponent(override):''}`);active=data.product;activePhoto=data.photo_url;refreshWorkspaceHeading(active);$('generateAI').disabled=!data.photo_url;setProgress(2);$('record').innerHTML=productCard(active,data.photo_url);showPreviews(active,data.photo_url);$('reviewed').disabled=!data.photo_url;setState('Official product record retrieved. Review the details and tick the approval box to download the pack.','success');}
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
    clearAiDesigns();clearCampaign();
    $('reviewed').checked=false;$('download').disabled=true;
    setState('Draft price applied. Review all posters before exporting.','success');
});
const aiFamilyNames=['Bold Retail Promo','Clean Premium Promo','Trade Campaign Promo'];

function renderAiMarketingCopy(){
 // Reuse the very same editor as the full-campaign route.
 // Switching data sources never leaves two copy panels on the page.
 if(!aiConcepts.some(c=>c.marketing_copy)){
  if(copyStudioData?.origin==='ai'){
   copyStudioData=null;$('unifiedCopyStudio').hidden=true;
  }
  return;
 }
 const wasAi=copyStudioData?.origin==='ai';
 copyStudioData={
  origin:'ai',
  copy:aiConcepts.map((c,i)=>({...c.marketing_copy,campaign_angle:aiFamilyNames[i]}))
 };
 if(!wasAi){
  campaignCopyIndex=0;campaignCopyChannel='social_caption';
  campaignCopyEdits={};rewriteUndoHistory={};
 }
 renderCampaignCopyStudio();
 $('unifiedCopyStudio').hidden=false;
 showCopyEmpty();
}

let aiScenePhotos=[null,null,null];
const aiAccentPresets=[['#FFC82E','#FF9D3D','#C5EB58'],['#B28D52','#0D95CD','#418C9B'],['#FFAA32','#25C4EC','#D2E96B']];
const aiBackgroundPresets=[['#056DB9','#0A65AF','#175CB0'],['#FCFBF8','#FBFDFF','#F9FBFC'],['#0E263C','#061E39','#202D3A']];
const aiPaletteNames=[['Laser blue / yellow','Blue / orange','Royal blue / lime'],['Ivory / gold','White / cyan','Stone / teal'],['Navy / orange','Blue / cyan','Charcoal / lime']];

function clearAiDesigns(){
 aiConcepts=[];aiOriginals=[];currentAiEditor=-1;aiScenePhotos=[null,null,null];
 if(copyStudioData?.origin==='ai'){copyStudioData=null;rewriteNonce++;pendingCopyRewrite=null;rewriteUndoHistory={};$('unifiedCopyStudio').hidden=true;showCopyEmpty();}
 $('aiIdeas').innerHTML='';
 $('aiEditor').hidden=true;
}
function renderAiGallery(){
 $('aiIdeas').innerHTML=aiConcepts.map((c,i)=>'<article class="ai-idea"><img loading="lazy" src="'+c.preview+'" alt="'+esc(c.name)+' poster preview"><div class="ai-copy"><span class="ai-index">AI PROMO '+String(i+1).padStart(2,'0')+'</span><h4>'+esc(aiFamilyNames[i])+'</h4><p><b>'+esc(c.headline)+'</b></p><p>'+esc(c.angle)+'</p>'+(c.quality?.status?'<p class="ai-qa-note">Design check: '+esc(c.quality.status==='passed'?'Passed':c.quality.status==='review'?'Manual review advised':'Rejected')+(c.quality.auto_corrected?' · Layout automatically adjusted':'')+(c.quality.warnings?.length?' · '+esc(c.quality.warnings[0]):'')+'</p>':'')+(c.scene?.source&&c.scene.source!=='No external photograph used'?'<p class="ai-photo-credit">Background: '+esc(c.scene.description||c.scene.source)+(c.scene.page_url? ' · <a href="'+esc(c.scene.page_url)+'" target="_blank" rel="noopener noreferrer">Photo source</a>':'')+'</p>':'')+'<div class="ai-card-actions"><button type="button" class="ai-edit-trigger" data-ai-edit="'+i+'">✎ Edit this poster</button><button type="button" class="ai-zoom" data-ai-zoom="'+i+'">View full size ⤢</button><a href="'+c.preview+'" download="LASER_'+esc(active?.part||c.part)+'_AI_'+(i+1)+'.png">Download PNG ↓</a><button type="button" class="asset-share-button share-primary" data-ai-share="'+i+'">↗ Share to apps</button><button type="button" data-ai-copy="'+i+'">Captions &amp; email</button></div></div></article>').join('');
 renderAiMarketingCopy();
}
function setAiPaletteOptions(index){
 const selector=$('aiEditPalette');
 selector.innerHTML=aiPaletteNames[index].map((n,i)=>'<option value="'+i+'">'+esc(n)+'</option>').join('');
}
function refreshAiPaletteColours(){
 const i=currentAiEditor,p=Number($('aiEditPalette').value);
 if(i<0||p<0||p>2)return;
 $('aiEditAccent').value=aiAccentPresets[i][p].toLowerCase();
 $('aiEditBgColour').value=aiBackgroundPresets[i][p].toLowerCase();
}
function openAiEditor(index){
 if(!Number.isInteger(index)||index<0||index>=aiConcepts.length||!active)return;
 currentAiEditor=index;
 const c=aiConcepts[index],e=c.editor||{},variant=Number.isInteger(c.variant)?c.variant:0;
 $('aiEditorTitle').textContent=aiFamilyNames[index]+' · Part '+active.part;
 $('aiEditorPreview').src=c.preview;
 $('aiEditorDownload').href=c.preview;
 $('aiEditorDownload').download='LASER_'+active.part+'_AI_edited_'+(index+1)+'.png';
 $('aiEditHeadline').value=c.headline||'';
 $('aiEditSubline').value=e.subline||c.subline||'';
 $('aiEditTone').value=e.tone||'trade';
 $('aiEditHeadlineSize').value=e.headline_size||'normal';
 $('aiEditShowSubline').checked=!!e.show_subline;
 $('aiEditDisplay').value=e.display_mode||'shadow';
 $('aiEditPriceStyle').value=e.price_style||['bubble','plaque','banner'][index];
 $('aiEditIntensity').value=String(e.background_intensity??50);
 $('aiEditShapes').value=String(e.shape_intensity??2);
 $('aiEditScale').value=String(e.product_scale??100);
 $('aiEditX').value=String(e.product_x??0);
 $('aiEditY').value=String(e.product_y??0);
 for(const [input,label] of [['aiEditIntensity','aiEditIntensityValue'],['aiEditScale','aiEditScaleValue'],['aiEditX','aiEditXValue'],['aiEditY','aiEditYValue']])$(label).value=$(input).value;
 $('aiHeadlineChoices').innerHTML='';
 $('aiEditSceneFile').value='';
 $('aiSceneNote').textContent=aiScenePhotos[index]?'Approved workshop photo uploaded for this design.':'Upload an approved workshop photo if you want a specific scene. Otherwise an official manufacturer application photo is used where available (or an illustrative backdrop). Max 2 MB.';
 setAiPaletteOptions(index);
 $('aiEditPalette').value=String(variant);
 refreshAiPaletteColours();
 $('aiEditAccent').value=e.accent||$('aiEditAccent').value;
 $('aiEditBgColour').value=e.background_colour||$('aiEditBgColour').value;
 $('aiEditBackground').value=e.background||(index===2?'context':'clean');
 $('aiEditPricePosition').value=e.price_position||'standard';
 $('aiEditStatus').textContent='Edit this design and apply changes. No new AI request is needed.';
 $('aiEditor').hidden=false;
 $('aiEditor').scrollIntoView({behavior:'smooth',block:'start'});
}
function closeAiEditor(){
 $('aiEditor').hidden=true;currentAiEditor=-1;
}
async function saveAiEdit(regenerate=false){
 const idx=currentAiEditor,productPart=active?.part;
 if(idx<0||!productPart||aiEditing||!aiConcepts[idx])return;
 const headline=$('aiEditHeadline').value.trim();
 if(!regenerate&&!headline){$('aiEditStatus').textContent='Please enter a headline.';return;}
 const edits={headline:headline,subline:$('aiEditSubline').value.trim(),
  palette:Number($('aiEditPalette').value),background:$('aiEditBackground').value,
  price_position:$('aiEditPricePosition').value,accent:$('aiEditAccent').value,
  background_colour:$('aiEditBgColour').value,display_mode:$('aiEditDisplay').value,
  price_style:$('aiEditPriceStyle').value,headline_size:$('aiEditHeadlineSize').value,
  tone:$('aiEditTone').value,show_subline:$('aiEditShowSubline').checked,
  background_intensity:Number($('aiEditIntensity').value),
  shape_intensity:Number($('aiEditShapes').value),
  product_scale:Number($('aiEditScale').value),
  product_x:Number($('aiEditX').value),product_y:Number($('aiEditY').value),
  scene_data:aiScenePhotos[idx]||''};
 const original=aiConcepts[idx],{preview,...concept}=original;
 aiEditing=true;
 const applyButton=$('aiEditApply'),regenButton=$('aiEditRegenerate');
 applyButton.disabled=true;regenButton.disabled=true;
 $('aiEditStatus').textContent=regenerate?'Gemini is creating fresh copy for this poster only…':'Updating this poster with your settings…';
 try{
  const response=await fetch('/api/ai/edit/'+encodeURIComponent(productPart),{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({index:idx,concept,edits,regenerate,
    distributor_brand:selectedDistributor(),staff_rrp_ex:staffApplied,
    staff_rrp_reviewed:!!staffApplied&&$('staffReview').checked,staff_rrp_basis:staffBasis})});
  const data=await readApiJson(response);
  if(!active||active.part!==productPart||currentAiEditor!==idx)return;
  aiConcepts[idx]=data.concept;
  if(copyStudioData?.origin==='ai'){
   Object.keys(campaignCopyEdits).filter(key=>key.startsWith(String(idx)+':')).forEach(key=>delete campaignCopyEdits[key]);
  }
  renderAiGallery();
  $('aiEditorPreview').src=data.concept.preview;
  $('aiEditorDownload').href=data.concept.preview;
  $('aiEditHeadline').value=data.concept.headline;
  $('aiEditStatus').textContent=regenerate?'New AI copy applied to this poster. The other two are unchanged.':'Changes saved to this poster in the gallery. Download the PNG to keep it.';
  setState('AI poster '+(idx+1)+' updated. Please review the artwork before sharing.','success');
 }catch(err){$('aiEditStatus').textContent=err.message;setState(err.message,'error');}
 finally{aiEditing=false;applyButton.disabled=false;regenButton.disabled=false;}
}
for(const [input,label] of [['aiEditIntensity','aiEditIntensityValue'],['aiEditScale','aiEditScaleValue'],['aiEditX','aiEditXValue'],['aiEditY','aiEditYValue']]){
 $(input).addEventListener('input',()=>{$(label).value=$(input).value;});
}
$('aiEditSceneFile').addEventListener('change',event=>{
 const file=event.target.files?.[0],idx=currentAiEditor;
 if(!file||idx<0)return;
 if(file.size>2000000||!['image/png','image/jpeg','image/webp'].includes(file.type)){
  $('aiSceneNote').textContent='Choose a PNG, JPEG or WebP image no larger than 2 MB.';
  event.target.value='';return;
 }
 const reader=new FileReader();
 reader.onload=()=>{
  if(currentAiEditor!==idx)return;
  aiScenePhotos[idx]=String(reader.result);
  $('aiEditBackground').value='context';
  $('aiSceneNote').textContent='Approved workshop photo selected. Click Apply changes to use it behind the real product.';
 };
 reader.onerror=()=>{$('aiSceneNote').textContent='Could not read that workshop photo.';};
 reader.readAsDataURL(file);
});
$('aiSceneRemove').addEventListener('click',()=>{
 if(currentAiEditor<0)return;
 aiScenePhotos[currentAiEditor]=null;
 $('aiEditSceneFile').value='';
 $('aiSceneNote').textContent='Workshop photo removed. Automatic real contextual photography is available.';
});
$('aiHeadlineChoices').addEventListener('click',event=>{
 const btn=event.target.closest('button[data-headline]');
 if(btn){$('aiEditHeadline').value=btn.dataset.headline;$('aiEditStatus').textContent='Headline selected. Click Apply changes to update your poster.';}
});
async function generateHeadlineOptions(single=false){
 const idx=currentAiEditor,part=active?.part;
 if(idx<0||!part||aiEditing)return;
 const button=$(single?'aiGenerateOneHeadline':'aiSuggestHeadlines');button.disabled=true;
 $('aiHeadlineChoices').textContent='Finding three professional headline options…';
 try{
  const res=await fetch('/api/ai/headlines/'+encodeURIComponent(part),{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({index:idx,tone:$('aiEditTone').value})});
  const data=await readApiJson(res);
  if(currentAiEditor!==idx||active?.part!==part)return;
  if(single){
   $('aiEditHeadline').value=data.headlines[0]||'';
   $('aiHeadlineChoices').textContent='New trade headline ready. Apply changes to use it.';
  }else{
   $('aiHeadlineChoices').innerHTML=data.headlines.map((h,i)=>
    '<button type="button" data-headline="'+esc(h)+'">'+(i+1)+'. '+esc(h)+'</button>').join('');
  }
 }catch(error){$('aiHeadlineChoices').textContent=error.message;}
 finally{button.disabled=false;}
}
$('aiGenerateOneHeadline').addEventListener('click',()=>generateHeadlineOptions(true));
$('aiSuggestHeadlines').addEventListener('click',()=>generateHeadlineOptions(false));
$('aiEditPalette').addEventListener('change',refreshAiPaletteColours);
$('aiEditorForm').addEventListener('submit',event=>{event.preventDefault();saveAiEdit(false);});
$('aiEditRegenerate').addEventListener('click',()=>saveAiEdit(true));
$('aiEditorClose').addEventListener('click',closeAiEditor);

$('generateAI').addEventListener('click',async()=>{
 if(!active||!activePhoto)return;
 const button=$('generateAI'),productPart=active.part;
 button.disabled=true;button.textContent='Creating 3 promotional designs…';
 clearAiDesigns();
 $('aiIdeas').innerHTML='<p class="ai-loading">Generating three different price-led marketing posters automatically…</p>';
 try{
   const res=await fetch('/api/ai/concepts/'+encodeURIComponent(productPart),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({distributor_brand:selectedDistributor(),staff_rrp_ex:staffApplied,staff_rrp_reviewed:!!staffApplied&&$('staffReview').checked,staff_rrp_basis:staffBasis})});
   const data=await readApiJson(res);
   if(!active||active.part!==productPart)return;
   aiConcepts=data.concepts;
   aiOriginals=data.concepts.map(c=>({...c}));
   renderAiGallery();
   setState('Three AI promotional posters generated. Check the verified RRP and copy before sharing.','success');
 }catch(err){
   if(!active||active.part!==productPart)return;
   const message=String(err.message||'Unable to generate AI posters.');
   const temporary=/HTTP 50[0234]|temporarily unavailable|timed out|timeout|incomplete response/i.test(message);
   const heading=temporary?'Gemini is unavailable right now':'AI generation could not be completed';
   const explanation=temporary
    ?'Google temporarily rejected the AI request. Your product lookup and standard marketing tools are still available.'
    :'Check the error below. If the AI service cannot generate posters, you can still create a complete source-verified campaign.';
   $('aiIdeas').innerHTML='<div class="ai-recovery" role="alert"><strong>'+esc(heading)+
      '</strong><p>'+esc(explanation)+'</p><p class="ai-recovery-reason">'+esc(message)+
      '</p><div class="ai-recovery-actions"><button type="button" class="ai-secondary" data-ai-retry="1">Retry AI posters</button>'+
      '<button type="button" class="ai-secondary" data-ai-fallback="1">Generate full campaign instead</button></div>'+
      '<small>The alternative campaign uses verified manufacturer facts and is labelled as a template fallback if Gemini is unavailable.</small></div>';
   setState(message,'error');
 }
 finally{button.disabled=!activePhoto;button.textContent='✦ Generate with AI';}
});
$('aiIdeas').addEventListener('click',event=>{
 const retry=event.target.closest('button[data-ai-retry]');
 if(retry){$('generateAI').click();return;}
 const fallback=event.target.closest('button[data-ai-fallback]');
 if(fallback){$('campaignBtn').click();return;}
 const shareBtn=event.target.closest('button[data-ai-share]');
 if(shareBtn){
  const index=Number(shareBtn.dataset.aiShare),concept=aiConcepts[index];
  if(concept?.preview)shareDataImage(concept.preview,'LASER_'+(active?.part||concept.part)+'_AI_'+(index+1)+'.png');
  return;
 }
 const copyBtn=event.target.closest('button[data-ai-copy]');
 if(copyBtn){
  renderAiMarketingCopy();
  campaignCopyIndex=Number(copyBtn.dataset.aiCopy);campaignCopyChannel='social_caption';
  renderCampaignCopyStudio();
  $('unifiedCopyStudio').scrollIntoView({behavior:'smooth',block:'start'});
  return;
 }
 const editBtn=event.target.closest('button[data-ai-edit]');
 if(editBtn){openAiEditor(Number(editBtn.dataset.aiEdit));return;}
 const btn=event.target.closest('button[data-ai-zoom]');
 if(!btn)return;
 const card=btn.closest('.ai-idea'),poster=card?.querySelector('img');
 if(!poster)return;
 $('aiPosterImage').src=poster.src;
 $('aiPosterTitle').textContent=card.querySelector('h4')?.textContent||'AI promotional poster';
 const dialog=$('aiPosterPreview');if(!dialog.open)dialog.showModal();
});
$('aiEditorShare').addEventListener('click',()=>{
 const source=$('aiEditorPreview').src;
 if(source)shareDataImage(source,$('aiEditorDownload').download||'LASER_AI_edited_poster.png');
});
$('aiPosterClose').addEventListener('click',()=>$('aiPosterPreview').close());
$('aiPosterPreview').addEventListener('click',e=>{if(e.target.id==='aiPosterPreview')e.target.close();});

function campaignAssetUrl(id){return '/api/campaign/assets/'+encodeURIComponent(campaignData.token)+'/'+encodeURIComponent(id);}
function renderCampaignGallery(data){
 const m=data.manifest||{};
 if(!Array.isArray(m.images)||m.images.filter(item=>item.id!=='source_qr').length<9){
  throw new Error('The campaign response is incomplete. No missing artwork will be shown as finished.');
 }
 const artworkCount=m.images.filter(item=>item.id!=='source_qr').length;
 $('campaignAssetCount').textContent='All '+artworkCount+' campaign artwork files are ready. Scroll down to view every format; tap a graphic to open it.';
 const names={poster_technical:'01 / Application & Technical',poster_price:'02 / Price Promotion',poster_smart:'03 / Product-Selected',
 social_square:'Facebook / Instagram Square',social_story:'Instagram Story (9:16)',website_banner:'Website Banner',
 email_header:'Email Header',linkedin_graphic:'LinkedIn Graphic',landscape_ad:'Landscape Advert',source_qr:'Official Product QR'};
 $('campaignAssets').innerHTML=m.images.map((asset,index)=>
  '<article class="campaign-asset" data-asset-card="'+esc(asset.id)+'"><a href="'+campaignAssetUrl(asset.id)+'" target="_blank" rel="noopener noreferrer" aria-label="Open '+esc(names[asset.id]||asset.id)+'"><img loading="'+(index<3?'eager':'lazy')+'" decoding="async" src="'+campaignAssetUrl(asset.id)+'" alt="'+esc(names[asset.id]||asset.id)+'"></a><small class="campaign-asset-load" data-load-state>Loading preview…</small><button class="campaign-asset-retry" type="button" data-retry-asset="'+esc(asset.id)+'" hidden>Retry image</button><b>'+esc(names[asset.id]||asset.id)+'</b><small>'+esc(asset.path)+'</small>'+
  '<div class="campaign-asset-actions"><a class="campaign-save-image" href="'+campaignAssetUrl(asset.id)+'?download=1" download="LASER_'+esc(m.part)+'_'+esc(asset.id)+'.png">Download PNG</a>'+
  '<button type="button" class="asset-share-button share-primary" data-share-url="'+campaignAssetUrl(asset.id)+'" data-share-filename="LASER_'+esc(m.part)+'_'+esc(asset.id)+'.png">↗ Share to apps</button>'+
  (['poster_technical','poster_price','poster_smart'].includes(asset.id)?'<button type="button" class="campaign-edit-button" data-edit-poster="'+esc(asset.id)+'">✎ Edit poster</button>':'')+'</div></article>').join('');

 $('previews').hidden=true;
 $('campaignResults').hidden=false;
}
$('campaignAssets').addEventListener('load',event=>{
 if(event.target.tagName!=='IMG')return;
 const card=event.target.closest('.campaign-asset');
 const status=card&&card.querySelector('[data-load-state]');
 if(status)status.textContent='Preview loaded';
},true);
$('campaignAssets').addEventListener('error',event=>{
 if(event.target.tagName!=='IMG')return;
 const card=event.target.closest('.campaign-asset');
 if(!card)return;
 const state=card.querySelector('[data-load-state]');
 const retry=card.querySelector('[data-retry-asset]');
 if(state)state.textContent='Preview did not load. The full ZIP may still be available.';
 if(retry)retry.hidden=false;
},true);
$('campaignAssets').addEventListener('click',event=>{
 const control=event.target.closest('[data-retry-asset]');
 if(!control)return;
 const card=control.closest('.campaign-asset');
 const img=card&&card.querySelector('img');
 if(!img)return;
 control.hidden=true;
 const state=card.querySelector('[data-load-state]');
 if(state)state.textContent='Retrying preview…';
 const base=img.src.split('?')[0];
 img.src=base+'?retry='+Date.now();
});

function showCampaign(data){
 campaignData=data;
 renderCampaignGallery(data);
 const m=data.manifest;
 $('campaignTitle').textContent='LASER '+m.part+' · '+m.title;
 const freeform=m.creative_plan&&m.creative_plan.render_engine==='ai-authored-freeform-layout';
 $('campaignSummary').textContent=(freeform
     ?'AI-designed original compositions using genuine manufacturer photos and verified facts. '
     :(m.generation_method==='gemini-assisted'
        ?'Gemini suggested concepts, but the safe legacy layout renderer was used. '
        :'Verified-source fallback campaign using standard layouts (Gemini unavailable). '))
     +m.files.length+' files in the ZIP. All materials still require approval.';
 const checked=Object.values(m.artwork_quality||{});
 const alerts=checked.flatMap(item=>item.warnings||[]);
 $('campaignQuality').textContent=checked.length
   ?checked.filter(item=>item.passed).length+' / '+checked.length+
    ' posters passed automated layout checks · '+checked.reduce((n,item)=>n+(item.candidates_checked||0),0)+
    ' candidate designs reviewed.'+(alerts.length?' Photo review: '+[...new Set(alerts)].join('; ')+'.':'')
   :'Automated poster checks unavailable — review every image before sharing.';
 if(freeform){
   const vision=m.creative_critic||{};
   $('campaignQuality').textContent+=' · '+(vision.reviewed
      ?'Independent AI review of finished posters completed.'
      :'AI visual review unavailable; deterministic QA applied.');
 }
 const formatChecks=m.format_artwork_quality||{};
 const nativeKinds=['social_square','social_story','website_banner','email_header','linkedin_graphic','landscape_ad'];
 const originalCount=nativeKinds.filter(k=>formatChecks[k]?.render_engine==='ai-original-format-canvas').length;
 if(nativeKinds.every(k=>formatChecks[k])){
    $('campaignQuality').textContent+=' · '+originalCount+'/6 marketing formats have their own AI-designed layouts.'+
      (originalCount<4?' Formats using the older renderer still require manual design review.':'');
 }
 const strategy=m.marketing_strategy;
 $('marketingStrategyPanel').hidden=!strategy;
 if(strategy){
  $('strategyMethod').textContent=strategy.method_label||'Product-aware recommendation';
  $('strategyCategory').textContent=strategy.category_label||'Uncategorised';
  const official=Array.isArray(strategy.official_category_path)&&strategy.official_category_path.length>0;
  $('strategyCategoryLabel').textContent=official?'Official Tool Connection category':'Suggested product category';
  $('strategyCategorySource').textContent=official
    ?'Verified from the manufacturer product URL'
    :'Inferred from the product title/description — verify the official category';
  $('strategyLens').textContent=(strategy.marketing_lens||{}).label||'Product-aware verified features';
  $('strategyAudience').textContent=strategy.target_audience||'Sales review required';
  $('strategyFocus').textContent=strategy.primary_focus_label||'Review required';
  $('strategyChannels').textContent=(strategy.recommended_channels||[]).map(c=>c.label).join(' + ');
  $('strategyReason').textContent=strategy.reason||'Requires review';
  $('strategyProof').textContent=strategy.proof_point||'No verified manufacturer feature available';
 }
 $('campaignDownload').href='/api/campaign/download/'+encodeURIComponent(data.token);
 $('campaignDownload').setAttribute('download','LASER_'+m.part+'_Complete_Campaign.zip');
 delete $('campaignShareZip').dataset.shareLoading;
 preparedShareFiles.delete($('campaignShareZip'));
 $('campaignShareZip').dataset.shareUrl=$('campaignDownload').href;
 $('campaignShareZip').dataset.shareFilename='LASER_'+m.part+'_Complete_Campaign.zip';
 prepareShareButtons($('campaignResults'));
 // The most shareable graphic is the square social image; show an obvious
 // Share action above the gallery, not only under individual download links.
 const socialAsset=m.images.find(item=>item.id==='social_square');
 const socialButton=$('campaignShareSocial');
 preparedShareFiles.delete(socialButton);
 delete socialButton.dataset.shareLoading;
 socialButton.dataset.shareUrl=socialAsset?campaignAssetUrl('social_square'):'';
 socialButton.dataset.shareFilename='LASER_'+m.part+'_Social.png';
 socialButton.hidden=!socialAsset;
 if(socialAsset)prepareShareButtons($('campaignResults'));
 $('campaignAngles').innerHTML=m.angles.map((angle,index)=>
  '<div class="campaign-angle'+(angle.role==='product_selected'?' strategy-recommended':'')+'"><span>0'+(index+1)+' / '+esc(angle.name.toUpperCase())+
  (angle.role==='product_selected'?' · PRODUCT-SELECTED':'')+'</span><b>'+esc(angle.headline)+'</b><small>Layout: '+esc(angle.layout||'product-specific')+'</small><p>'+esc(angle.selling_point)+'</p></div>').join('');
 prepareShareButtons($('campaignResults'));
 const social=m.social_suggestions||{};
 const frames=Array.isArray(social.instagram_story)?social.instagram_story:[];
 $('campaignSocialIdeas').hidden=!frames.length;
 $('storySuggestions').innerHTML=frames.map(item=>
  '<div class="story-suggestion"><b>STORY '+esc(item.slide)+' · '+esc(item.suggestion)+'</b><p>'+esc(item.text)+'</p></div>').join('');
 $('campaignSocialTip').textContent='WhatsApp suggestion: '+(social.whatsapp||'Review product details before ordering.')+
  ' · Captions and other channel text can be edited in the single Copy Editor.';
 copyStudioData={origin:'campaign',copy:m.copy};
 campaignCopyIndex=0;campaignCopyChannel='social_caption';campaignCopyEdits={};rewriteUndoHistory={};
 renderCampaignCopyStudio();
 $('unifiedCopyStudio').hidden=false;
 showCopyEmpty();
 $('previews').hidden=true;
 $('campaignResults').hidden=false;
 $('studioWorkspace').scrollIntoView({behavior:'smooth',block:'start'});
}

let copyStudioData=null,campaignCopyIndex=0,campaignCopyChannel='social_caption',campaignCopyEdits={};
let pendingCopyRewrite=null,rewriteNonce=0,rewriteBusy=false,rewriteUndoHistory={};
const campaignChannelLabels={
 social_caption:'Social caption',linkedin_post:'LinkedIn post',email_body:'Product email',
 hashtags:'Hashtags',website_listing:'Website listing',short_message:'Short promo'
};
function campaignDraft(index,channel){
 const key=String(index)+':'+channel;
 if(Object.prototype.hasOwnProperty.call(campaignCopyEdits,key))return campaignCopyEdits[key];
 const copy=copyStudioData?.copy?.[index]||{};
 if(channel==='email_body')return 'Subject: '+(copy.email_subject||'')+'\n\n'+(copy.email_body||'');
 if(channel==='hashtags')return Array.isArray(copy.hashtags)?copy.hashtags.join(' '):'';
 return copy[channel]||'';
}
function renderCampaignCopyStudio(){
 if(!copyStudioData)return;
 resetRewriteSuggestion();
 const copies=copyStudioData.copy||[];
 campaignCopyIndex=Math.min(Math.max(0,campaignCopyIndex),Math.max(0,copies.length-1));
 $('campaignCopyAngles').innerHTML=copies.map((copy,index)=>
  '<button type="button" data-campaign-angle="'+index+'" class="'+(index===campaignCopyIndex?'selected':'')+
  '" aria-pressed="'+String(index===campaignCopyIndex)+'">'+esc(copy.campaign_angle||'Campaign '+(index+1))+'</button>').join('');
 document.querySelectorAll('#campaignCopyChannels button').forEach(button=>{
  // Original AI poster concepts only supply the original four copy channels.
  button.hidden=copyStudioData.origin==='ai'&&['website_listing','short_message'].includes(button.dataset.campaignChannel);
  const active=button.dataset.campaignChannel===campaignCopyChannel;
  button.classList.toggle('selected',active);button.setAttribute('aria-pressed',String(active));
 });
 const name=copies[campaignCopyIndex]?.campaign_angle||'Campaign';
 $('campaignCopyLabel').textContent=name+' · '+campaignChannelLabels[campaignCopyChannel];
 $('copyStudioOrigin').textContent=copyStudioData.origin==='ai'?'AI POSTER COPY / READY-TO-EDIT DRAFTS':'CAMPAIGN COPY / READY-TO-EDIT DRAFTS';
 $('copyStudioNote').textContent=copyStudioData.origin==='ai'
  ?'Wording is taken from the selected AI posters. Your edits remain while switching tabs. Review everything before publishing.'
  :'Your edits remain while switching tabs and copying. The ZIP still includes the original drafts. Review everything before publishing.';
 $('campaignCopyText').value=campaignDraft(campaignCopyIndex,campaignCopyChannel);
 $('campaignCopyStatus').textContent='';
 const available=campaignCopyChannel!=='hashtags';
 $('rewriteOptions').hidden=!available;
 $('rewriteStatus').textContent=available
  ?'Choose a style to preview a new draft. Review product claims before publishing.'
  :'Hashtags are generated from verified categories and cannot be rewritten.';
 $('rewriteUndo').hidden=!available||!Object.prototype.hasOwnProperty.call(rewriteUndoHistory,rewriteKey());
}
$('campaignCopyAngles').addEventListener('click',event=>{
 const button=event.target.closest('button[data-campaign-angle]');
 if(!button||!copyStudioData)return;
 campaignCopyIndex=Number(button.dataset.campaignAngle);renderCampaignCopyStudio();
});
$('campaignCopyChannels').addEventListener('click',event=>{
 const button=event.target.closest('button[data-campaign-channel]');
 if(!button||!copyStudioData)return;
 campaignCopyChannel=button.dataset.campaignChannel;renderCampaignCopyStudio();
});
$('campaignCopyText').addEventListener('input',()=>{
 if(!copyStudioData)return;
 campaignCopyEdits[String(campaignCopyIndex)+':'+campaignCopyChannel]=$('campaignCopyText').value;
 resetRewriteSuggestion();
 delete rewriteUndoHistory[rewriteKey()];$('rewriteUndo').hidden=true;
 $('campaignCopyStatus').textContent=copyStudioData.origin==='campaign'?'Edited locally — ZIP still contains original wording.':'Edited draft saved in this page.';
});
async function copySelectedCampaignText(value){
 if(navigator.clipboard&&navigator.clipboard.writeText){
  await navigator.clipboard.writeText(value);return true;
 }
 const field=$('campaignCopyText'),prior=field.value;
 field.value=value;field.focus();field.select();
 const copied=document.execCommand('copy');field.value=prior;return copied;
}

function rewriteKey(){
 return String(campaignCopyIndex)+':'+campaignCopyChannel;
}
function resetRewriteSuggestion(){
 rewriteNonce++;
 pendingCopyRewrite=null;
 $('rewritePreview').hidden=true;
 if(!rewriteBusy)$('rewriteOptions').querySelectorAll('button').forEach(button=>button.disabled=false);
}
function showRewriteBusy(isBusy){
 rewriteBusy=isBusy;
 $('rewriteOptions').querySelectorAll('button').forEach(button=>button.disabled=isBusy);
}
$('rewriteOptions').addEventListener('click',async event=>{
 const button=event.target.closest('button[data-rewrite-mode]');
 if(!button||rewriteBusy||!copyStudioData||!active||campaignCopyChannel==='hashtags')return;
 const oldText=$('campaignCopyText').value;
 if(!oldText.trim()){$('rewriteStatus').textContent='Add some copy before requesting a rewrite.';return;}
 const currentData=copyStudioData,key=rewriteKey(),part=active.part;
 const mode=button.dataset.rewriteMode;
 resetRewriteSuggestion();
 const requestId=rewriteNonce;
 showRewriteBusy(true);
 $('rewriteStatus').textContent='Preparing source-checked wording…';
 const rawPrice=$('staffRrp').value.trim(),reviewedPrice=$('staffReview').checked;
 if(rawPrice&&!reviewedPrice){
  showRewriteBusy(false);
  $('rewriteStatus').textContent='Review the staff-entered price before requesting a rewrite.';
  return;
 }
 try{
  const response=await fetch('/api/copy/rewrite/'+encodeURIComponent(part),{
   method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},
   body:JSON.stringify({mode,channel:campaignCopyChannel,angle:campaignCopyIndex,
    current_text:oldText,official_url:$('officialUrl').value.trim()||null,
    staff_rrp_ex:rawPrice||staffApplied,
    staff_rrp_reviewed:!!(rawPrice||staffApplied)&&(rawPrice?reviewedPrice:$('staffReview').checked),
    staff_rrp_basis:rawPrice?$('staffRrpBasis').value:staffBasis})
  });
  const result=await readApiJson(response);
  if(requestId!==rewriteNonce||copyStudioData!==currentData||rewriteKey()!==key||active?.part!==part)return;
  pendingCopyRewrite={key,text:result.text,original:oldText,source:currentData};
  $('rewritePreviewText').value=result.text;
  $('rewriteMethod').textContent=result.method==='gemini-assisted'
    ?'Gemini-assisted · Official verified facts'
    :'Verified-source rewrite · AI unavailable';
  $('rewritePreview').hidden=false;
  $('rewriteStatus').textContent=(result.warning?result.warning+' ':'')+
   'Compare with your draft, then apply or keep the original.';
 }catch(error){
  if(requestId===rewriteNonce)$('rewriteStatus').textContent=error.message||'Unable to rewrite this draft.';
 }finally{
  showRewriteBusy(false);
 }
});
$('rewriteApply').addEventListener('click',()=>{
 const proposed=pendingCopyRewrite;
 if(!proposed||!copyStudioData||proposed.source!==copyStudioData||proposed.key!==rewriteKey())return;
 rewriteUndoHistory[proposed.key]=proposed.original;
 campaignCopyEdits[proposed.key]=proposed.text;
 $('campaignCopyText').value=proposed.text;
 resetRewriteSuggestion();
 $('rewriteUndo').hidden=false;
 $('rewriteStatus').textContent='Rewrite applied to this draft. Copy it when ready; the ZIP still contains the original text.';
 $('campaignCopyStatus').textContent='Rewrite applied locally — review before publishing.';
});
$('rewriteDiscard').addEventListener('click',()=>{
 resetRewriteSuggestion();$('rewriteStatus').textContent='Original wording kept.';
});
$('rewriteUndo').addEventListener('click',()=>{
 if(!copyStudioData||!Object.prototype.hasOwnProperty.call(rewriteUndoHistory,rewriteKey()))return;
 const previous=rewriteUndoHistory[rewriteKey()];
 delete rewriteUndoHistory[rewriteKey()];
 campaignCopyEdits[rewriteKey()]=previous;
 $('campaignCopyText').value=previous;
 resetRewriteSuggestion();$('rewriteUndo').hidden=true;
 $('rewriteStatus').textContent='Previous wording restored.';
});

$('campaignCopyCurrent').addEventListener('click',async()=>{
 if(!copyStudioData)return;
 try{
  const success=await copySelectedCampaignText(campaignDraft(campaignCopyIndex,campaignCopyChannel));
  $('campaignCopyStatus').textContent=success?'Text copied.':'Select and copy the text manually.';
 }catch(e){$('campaignCopyStatus').textContent='Clipboard unavailable. Select the text and copy it manually.';}
});
$('campaignCopyAll').addEventListener('click',async()=>{
 if(!copyStudioData)return;
 const channels=copyStudioData.origin==='ai'
  ?['social_caption','linkedin_post','email_body','hashtags']:Object.keys(campaignChannelLabels);
 const text=(copyStudioData.copy||[]).map((copy,index)=>
  (copy.campaign_angle||'Campaign '+(index+1))+'\n'+channels.map(channel=>
   campaignChannelLabels[channel]+'\n'+campaignDraft(index,channel)).join('\n\n')).join('\n\n-------------------------\n\n');
 try{
  const success=await copySelectedCampaignText(text);
  $('campaignCopyStatus').textContent=success?'All campaign wording copied.':'Select and copy the text manually.';
 }catch(e){$('campaignCopyStatus').textContent='Clipboard unavailable. Copy each section individually.';}
});
$('campaignCopyReset').addEventListener('click',()=>{
 if(!copyStudioData)return;
 delete campaignCopyEdits[String(campaignCopyIndex)+':'+campaignCopyChannel];
 delete rewriteUndoHistory[rewriteKey()];
 renderCampaignCopyStudio();$('campaignCopyStatus').textContent='Original suggested wording restored.';
});
$('campaignBtn').addEventListener('click',async()=>{
 if(inflight)return;
 const part=$('part').value.trim().toUpperCase(),button=$('campaignBtn');
 if(!/^[0-9A-Za-z.-]{3,16}$/.test(part)){$('campaignStatus').textContent='Enter a valid Laser Tools part number.';return;}
 const rawPrice=$('staffRrp').value.trim();
 // Capture staff review before lookup: load() resets inputs during first search.
 const reviewedPrice=$('staffReview').checked,reviewedBasis=$('staffRrpBasis').value;
 if(rawPrice&&!reviewedPrice){$('campaignStatus').textContent='Check the staff RRP box before using your entered price.';return;}
 button.disabled=true;button.textContent='Building full campaign…';
 clearCampaign();
 try{
   if(!active||active.part!==part){$('campaignStatus').textContent='Retrieving verified product details…';await load(part);}
   if(rawPrice&&!$('staffRrp').value){$('staffRrp').value=rawPrice;$('staffReview').checked=reviewedPrice;$('staffRrpBasis').value=reviewedBasis;}
   if(!active||active.part!==part||!activePhoto)throw Error('Verified manufacturer product details and original photography are required.');
   $('campaignStatus').textContent='Understanding the tool, selecting three different poster layouts, sourcing approved application imagery and writing channel copy…';
   const response=await fetch('/api/campaign/'+encodeURIComponent(part),{
     method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},
     body:JSON.stringify({official_url:$('officialUrl').value.trim()||null,
       distributor_brand:selectedDistributor(),
       staff_rrp_ex:rawPrice||staffApplied,
       staff_rrp_reviewed:!!(rawPrice||staffApplied)&&(rawPrice?reviewedPrice:$('staffReview').checked),
       staff_rrp_basis:rawPrice?reviewedBasis:staffBasis})
   });
   const data=await readApiJson(response);
   showCampaign(data);
   $('campaignStatus').textContent='Campaign ready to review. Nothing has downloaded — use Download complete ZIP or choose individual PNGs if you want to save them. The links expire after 15 minutes.';
 }catch(error){$('campaignStatus').textContent=error.message;setState(error.message,'error');}
 finally{button.disabled=false;button.textContent='✦ Build Campaign';}
});

$('distributorBrand').addEventListener('change',updateDistributorPreview);
['staffRrp','staffRrpBasis','staffReview','officialUrl'].forEach(id=>$(id).addEventListener('change',clearCampaign));
$('searchForm').addEventListener('submit',e=>{e.preventDefault();$('campaignBtn').click()});$('searchBtn').addEventListener('click',()=>load($('part').value.trim().toUpperCase()));document.querySelectorAll('[data-part]').forEach(b=>b.addEventListener('click',()=>{$('part').value=b.dataset.part;load(b.dataset.part)}));$('reviewed').addEventListener('change',()=>{$('download').disabled=!$('reviewed').checked;setProgress($('reviewed').checked?3:2);});
$('download').addEventListener('click',async()=>{if(!active||!$('reviewed').checked)return;const b=$('download');b.disabled=true;b.textContent='Creating ZIP…';try{const r=await fetch(`/api/generate/${encodeURIComponent(active.part)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true,distributor_brand:selectedDistributor(),staff_rrp_ex:staffApplied,staff_rrp_reviewed:!!staffApplied&&$('staffReview').checked,staff_rrp_basis:staffBasis})});if(!r.ok){const v=await r.json();throw Error(v.error||'Export failed')}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');const packName=`LASER_${active.part}_Marketing_Pack.zip`;legacyShareFile=new File([blob],packName,{type:'application/zip'});$('legacyShareZip').disabled=false;a.href=url;a.download=packName;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);setState('Marketing pack generated and downloaded.','success')}catch(e){setState(e.message,'error')}finally{b.disabled=false;b.innerText='Download all assets (ZIP) ↓';}});
</script><script src="/static/campaign_poster_edit.js?v=44"></script></body></html>

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
    r'Kugellager|Montagewerkzeug|Auswechselbar\w*|Wechselbar\w*|'
    r'Schlüsselköpfe|Schluesselkoepfe|Maulschlüssel|'
    r'Schraubenschlüssel|Steckschlüssel|Schlüsselweite\w*|'
    r'Schlüsselgröße\w*|Drehmomentschlüssel|Aufsätze)\b',re.I)
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
        or RAW_GERMAN_TECH.search(phrase)
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
        phrase=translate_known_numeric_labels(normalize(feature))
        key=phrase.casefold().strip(' .')
        if (not phrase or key in seen or is_non_english(phrase)
            or re.search(r'\b(?:N\.B\.|REMARQUE)\s*:',phrase,re.I)):
            continue
        seen.add(key)
        output.append(phrase)
    return output


def english_only_specs(specs):
    """Preserve English specs; translate only numeric labels with exact units."""
    english={}
    for key,value in (specs or {}).items():
        safe_key,safe_value=normalise_numeric_spec_row(key,value)
        if (safe_key and safe_value
            and not is_non_english(safe_key+" "+safe_value)):
            english[safe_key]=safe_value
    return english


def english_description(text):
    """Do not let translated PDF sentences leak into poster-purpose copy."""
    original=normalize(text)
    if not original:return ''
    parts=re.split(r'(?<=[.!?])\s+(?=[A-Za-zÀ-ÿ])',original)
    good=[]
    for part in parts:
        translated=translate_known_numeric_labels(part)
        if translated and not is_non_english(translated):
            good.append(translated)
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
    # Start with the highest-resolution official master when available.
    return [
        f'https://www.lasertools.co.uk/items/XLarge/{part}.jpg',
        f'https://lasertools.toolconnection.co.uk/items/XLarge/{part}.jpg',
        f'https://www.lasertools.co.uk/items/large/{part}.jpg',
        f'https://lasertools.toolconnection.co.uk/items/large/{part}.jpg',
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
    indexed_url = OFFICIAL_UK_PRODUCTS.get(part) or catalogue_url_for_part(part)
    if indexed_url:
        uk_candidates.append(indexed_url)
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
                # Product information sheets may mix English headings with
                # short German specification lines. Normalise those verified
                # numeric labels before checking/choosing the source, rather
                # than rejecting the entire official product record.
                candidate=normalise_product_language(candidate)
                if is_french(candidate['title']+' '+candidate['description']):
                    errors.append('Manufacturer page not in English');continue
                if not candidate.get('features') and not candidate.get('specs'):
                    errors.append('Manufacturer page has no verified English facts');continue
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
                sheet=normalise_product_language(sheet)
                if is_french(sheet['title']+' '+sheet['description']):continue
                if not sheet.get('features') and not sheet.get('specs'):continue
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
    # Source authenticity is checked by official_get; quality selection does
    # not invent, upscale or redraw tools. Do not settle for a bad thumbnail
    # merely because it was the first URL in the supplier gallery.
    from asset_quality import manufacturer_image_rank
    photo_options=[]
    attempts=0
    for photo_url in dict.fromkeys(candidates):
        if attempts>=6:break
        attempts+=1
        try:
            response=official_get(photo_url,session,timeout=6)
            if not valid_image(response.content):continue
            try:
                score,report=manufacturer_image_rank(response.content)
            except (ValueError,OSError,TypeError):
                score,report=0,{"passed":False,"issues":["Cannot assess photo quality"],
                                "size":[0,0],"edge_strength":0}
            photo_options.append((score,response.content,response.url,report))
            # A sharp, clean, sufficiently detailed official master is good
            # enough; additional network calls would only delay campaigns.
            if report.get("passed") and min(report.get("size",[0,0]))>=650 \
                    and score>=135:
                break
            if len(photo_options)>=3:break
        except Exception:pass
    if photo_options:
        best=max(photo_options,key=lambda item:item[0])
        image_bytes=best[1]
        product['photo_source']=best[2]
        product['photo_quality_selection']={
            "method":"ranked-official-image-sources",
            "candidates_checked":len(photo_options),
            "quality_passed":bool(best[3].get("passed")),
            "dimensions":best[3].get("size"),
        }
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
    product=apply_official_taxonomy(product)
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


def selected_distributor(value):
    """Accept only the three user-supplied demo marks."""
    code=str(value or 'none').strip().lower()
    if code not in BRAND_LABELS:
        raise ValueError('Unknown customer branding. Select a listed distributor or None.')
    return None if code=='none' else code


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
    if request.path=='/' or request.path.startswith('/api/poster/') or request.path.startswith('/api/photo/') or request.path.startswith('/api/distributor-logo/'):
        response.headers['Cache-Control']='no-store, max-age=0'
    return response

@app.get('/api/health')
def health():return jsonify(ok=True,service='Laser Product Studio',design='v19-product-aware-marketing-direction',lookup='official page + PDF fallback')

@app.get('/api/catalogue/taxonomy')
def catalogue_taxonomy():
    """Complete published category tree, NOT a claim to have imported every SKU."""
    response=jsonify(taxonomy_snapshot())
    response.headers['Cache-Control']='public, max-age=3600'
    return response


@app.get('/api/distributor-logo/<brand>')
def distributor_logo(brand):
    try:
        code=selected_distributor(brand)
        if code is None:return jsonify(error='No distributor logo selected'),404
        image=get_brand_image(code)
        if image is None:return jsonify(error='Distributor logo unavailable'),404
        output=io.BytesIO()
        image.save(output,format='PNG')
        output.seek(0)
        return send_file(output,mimetype='image/png',download_name=code+'_logo.png')
    except ValueError:
        return jsonify(error='Unknown distributor'),404


@app.get('/api/lookup/<part>')
def product_lookup(part):
    try:
        product,image=lookup(part,uk_url=request.args.get('uk_url') or None)
        # Raw foreign supplier phrases are retained only for internal audit;
        # never expose them to the website or downloadable campaign record.
        public_record={**{key:value for key,value in product.items()
                          if key!="source_raw_features"},
                       'technical_layout':technical_layout_mode(product),
                       'marketing_direction':strategy_for(product)}
        return jsonify(product=public_record,photo_url=f'/api/photo/{part}?design=v19' if image else None)
    except LookupErrorPublic as e:return jsonify(error=str(e)),404
    except requests.RequestException:return jsonify(error='Official Laser website could not be reached. Please retry.'),502
    except Exception:
        app.logger.exception('Unexpected lookup error')
        return jsonify(error='Product lookup failed unexpectedly.'),500

@app.post('/api/ai/concepts/<part>')
def ai_recommendations(part):
    """Genuine model generation only; never label deterministic fallback as AI."""
    try:
        product,image=lookup(part)
        if not image:
            return jsonify(error='A verified product photograph is required for AI poster recommendations.'),422
        ai_body=request.get_json(silent=True) or {}
        distributor=selected_distributor(ai_body.get('distributor_brand','none'))
        product=with_reviewed_price(product,ai_body.get('staff_rrp_ex'),ai_body.get('staff_rrp_reviewed') is True,ai_body.get('staff_rrp_basis','ex'))
        product['marketing_direction']=strategy_for(product)
        concepts=propose_ai_concepts(product)
        official_scene=(APPLICATION_IMAGE_CACHE.get(part)
                       if product.get('application_photo_source') and
                       product.get('application_photo_source')!=product.get('photo_source')
                       else None)
        image_variation=int.from_bytes(hashlib.sha256(str(part).encode("utf-8")).digest()[:2],"big")
        for i,concept in enumerate(concepts):
            # Enforce three different *verified* marketing purposes even when
            # Gemini repeats the same feature or a mocked model omits focus.
            concept=focus_concept(product,concept,i)
            concepts[i]=concept
            art=normalise_art_direction(concept.get('art_direction'),
                                        concept.get('family'),concept.get('variant',i))
            concept['art_direction']=art
            concept['variant']=art['layout_variant']
            # Pick a genuine scene automatically by what this specific tool
            # does: battery charger -> battery with cables, brakes -> actual
            # brake service, diagnostics -> scanner, etc. Prefer verified
            # manufacturer in-situ imagery for the trade campaign.
            scene,reference=find_scene(
                product,variation=i+image_variation,official_photo=official_scene,
                prefer_official=(i==2),family=concept.get('family'))
            quality={}
            treatment=scene_treatment(reference,art)
            options={'background':'context','_scene_bytes':scene,'show_subline':True,
                     '_scene_style':treatment,'_quality_report':quality,
                     **editor_preferences(art)}
            poster=render_ai_promo(concept,image,product,distributor,editor=options)
            concept['preview']='data:image/png;base64,'+base64.b64encode(poster).decode('ascii')
            if quality:
                concept['quality']=quality
                if quality.get('auto_corrected'):
                    corrected=int(quality.get('layout_variant',concept['variant']))
                    concept['variant']=corrected
                    art['layout_variant']=corrected
                    # The editor opens exactly the auto-repaired artwork.
                    art.update(quality.get('effective_editor') or {})
            # Keep the image source visible to staff for licence and accuracy
            # review, but never embed large binary data in a JSON concept.
            concept['scene']={k:reference.get(k) for k in (
                'category','description','source','page_url','license_url',
                'scene_type','family','crop')}
            concept['editor']={'background':'context','show_subline':True,
                               'palette':art['layout_variant'],
                               **editor_preferences(art)}
            concept['marketing_copy']=compose_promotional_copy(product,concept)
        return jsonify(concepts=concepts,source=product.get('source'),review_required=True)
    except RuntimeError as e:return jsonify(error=str(e)),503
    except ValueError as e:return jsonify(error=str(e)),400
    except LookupErrorPublic as e:return jsonify(error=str(e)),404
    except Exception:
        app.logger.exception('AI concept generation failed')
        return jsonify(error='Unable to generate AI poster ideas. Please retry.'),500


@app.post('/api/copy/rewrite/<part>')
def rewrite_marketing_copy(part):
    """One reviewed copy suggestion. Never accepts user/model factual claims."""
    try:
        body=request.get_json(silent=True)
        if not isinstance(body,dict):
            return jsonify(error='Invalid rewrite request.'),400
        mode=body.get('mode')
        channel=body.get('channel')
        angle=body.get('angle')
        current_text=body.get('current_text')
        # Validate before manufacturer lookup or any optional Gemini call.
        if mode not in ('shorter','professional','persuasive','technical','facebook'):
            return jsonify(error='Choose one of the five rewrite options.'),400
        if channel not in ('social_caption','linkedin_post','email_body','website_listing','short_message'):
            return jsonify(error='Select social, LinkedIn, email, web or short-promo copy.'),400
        if type(angle) is not int or angle not in (0,1,2):
            return jsonify(error='Choose a valid campaign direction.'),400
        if not isinstance(current_text,str) or not current_text.strip() or len(current_text)>5000:
            return jsonify(error='Select a draft of no more than 5,000 characters.'),400
        product,_=lookup(part,uk_url=body.get('official_url') or None)
        product=with_reviewed_price(
            product,body.get('staff_rrp_ex'),
            body.get('staff_rrp_reviewed') is True,
            body.get('staff_rrp_basis','ex'))
        rewritten=rewrite_copy(
            product,mode=mode,channel=channel,current_text=current_text,angle=angle)
        response=jsonify(rewritten)
        response.headers['Cache-Control']='no-store, private'
        return response
    except LookupErrorPublic as exc:return jsonify(error=str(exc)),400
    except ValueError as exc:return jsonify(error=str(exc)),400
    except requests.RequestException:
        return jsonify(error='Official manufacturer source could not be reached. Please retry.'),502
    except Exception:
        app.logger.exception('Marketing copy rewrite failed')
        return jsonify(error='Unable to rewrite this copy. Please retry.'),500


@app.post('/api/ai/headlines/<part>')
def ai_headline_options(part):
    """Generate three copy-only factual headline options for one selected promo."""
    try:
        body=request.get_json(silent=True) or {}
        if not isinstance(body,dict):
            return jsonify(error='Invalid request.'),400
        idx=body.get('index')
        tone=body.get('tone','trade')
        if type(idx) is not int or idx not in (0,1,2) or tone not in ('trade','technical','premium','sales'):
            return jsonify(error='Choose a valid design and writing tone.'),400
        product,image=lookup(part)
        if not image:return jsonify(error='Official product image unavailable.'),422
        product['marketing_direction']=strategy_for(product)
        options=suggest_ai_headlines(product,AI_PROMO_FAMILIES[idx],tone=tone)
        return jsonify(headlines=options,review_required=True)
    except RuntimeError as exc:return jsonify(error=str(exc)),503
    except LookupErrorPublic as exc:return jsonify(error=str(exc)),404
    except ValueError as exc:return jsonify(error=str(exc)),400
    except Exception:
        app.logger.exception('Headline suggestions failed')
        return jsonify(error='Could not generate headline suggestions.'),500


@app.post('/api/ai/edit/<part>')
def edit_ai_promo(part):
    """Edit one generated AI poster without changing original manufacturer facts.

    The browser sends only selected concept text and presentation controls.
    Product photo, part number, title, features and RRP are re-validated from
    official source on EVERY render; clients cannot provide arbitrary images
    or change the displayed price through this editor.
    """
    try:
        body=request.get_json(silent=True)
        if not isinstance(body,dict):
            return jsonify(error='Invalid editor request.'),400
        idx=body.get('index')
        if type(idx) is not int or idx not in (0,1,2):
            return jsonify(error='Choose one of the three promotional posters.'),400
        family=AI_PROMO_FAMILIES[idx]
        supplied=body.get('concept')
        edits=body.get('edits',{})
        if not isinstance(supplied,dict) or not isinstance(edits,dict):
            return jsonify(error='Invalid poster editor data.'),400
        product,image=lookup(part)
        if not image:
            return jsonify(error='Official product photography is required.'),422
        if str(supplied.get('part',''))!=str(product.get('part','')) or supplied.get('family')!=family:
            return jsonify(error='Poster does not match this product or design.'),400
        product=with_reviewed_price(product,body.get('staff_rrp_ex'),
                                   body.get('staff_rrp_reviewed') is True,
                                   body.get('staff_rrp_basis','ex'))
        brand=selected_distributor(body.get('distributor_brand','none'))

        # Price, product title, product image and factual feature bullets are
        # never supplied by or mutable from this editor.
        known_features=[str(x).strip()[:175] for x in product.get('features',[]) if str(x).strip()]
        selected=[x for x in supplied.get('features',[]) if
                  isinstance(x,str) and x in known_features] if isinstance(supplied.get('features'),list) else []
        selected=list(dict.fromkeys(selected))[:3]
        if not selected:
            selected=known_features[:2]
        def phrase(value,limit):
            return ' '.join(str(value or '').split())[:limit]
        if body.get('regenerate') is True:
            generated=propose_ai_concepts(product,only_family=family,
                                          tone=edits.get('tone','trade'))[0]
            headline=phrase(generated.get('headline'),48)
            subline=phrase(generated.get('subline'),82)
            name=phrase(generated.get('name'),30)
            angle=phrase(generated.get('angle'),120)
            selected=[x for x in generated.get('features',[]) if x in known_features][:3] or selected
        else:
            headline=phrase(edits.get('headline'),48)
            if not headline:
                return jsonify(error='Enter a headline before applying your changes.'),400
            subline=phrase(edits.get('subline',supplied.get('subline')),82)
            name=phrase(supplied.get('name'),30)
            angle=phrase(supplied.get('angle'),120)
        raw_palette=edits.get('palette',supplied.get('variant',0))
        if type(raw_palette) is not int or not 0<=raw_palette<=2:
            return jsonify(error='Select a valid colour palette.'),400
        background=edits.get('background','clean')
        position=edits.get('price_position','standard')
        if background not in ('clean','grid','rings','context','workshop','bench','engine') or position not in ('standard','opposite'):
            return jsonify(error='Unsupported background or price position.'),400
        display_mode=edits.get('display_mode','shadow')
        price_style=edits.get('price_style',('bubble','plaque','banner')[idx])
        headline_size=edits.get('headline_size','normal')
        tone=edits.get('tone','trade')
        if display_mode not in ('panel','cutout','shadow','glow') or price_style not in ('bubble','plaque','banner','tag','sticker','corner','panel'):
            return jsonify(error='Unsupported product or price appearance.'),400
        if headline_size not in ('small','normal','large') or tone not in ('trade','technical','premium','sales'):
            return jsonify(error='Unsupported headline style or tone.'),400
        transforms={}
        for key,low,high,default in [
                ('product_scale',70,160,100),('product_x',-100,100,0),
                ('product_y',-100,100,0),('shape_intensity',0,3,2),
                ('background_intensity',0,100,50)]:
            value=edits.get(key,default)
            if type(value) is not int or not low<=value<=high:
                return jsonify(error='Invalid position, zoom or background intensity.'),400
            transforms[key]=value
        if type(edits.get('show_subline',False)) is not bool:
            return jsonify(error='Invalid subheading setting.'),400
        scene_bytes=None
        scene_data=edits.get('scene_data','')
        if scene_data:
            if not isinstance(scene_data,str) or len(scene_data)>2_900_000:
                return jsonify(error='Workshop image is too large (maximum 2 MB).'),400
            match=re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)',scene_data)
            if not match:
                return jsonify(error='Upload a valid PNG, JPEG or WebP workshop photo.'),400
            try:
                scene_bytes=base64.b64decode(match.group(2),validate=True)
                if len(scene_bytes)>2_000_000:
                    return jsonify(error='Workshop image is too large (maximum 2 MB).'),400
                sample=Image.open(io.BytesIO(scene_bytes))
                if sample.format not in ('JPEG','PNG','WEBP') or sample.width*sample.height>12_000_000:
                    return jsonify(error='The workshop image must be under 12 megapixels.'),400
                sample.verify()
            except (ValueError,OSError,base64.binascii.Error):
                return jsonify(error='Workshop photo could not be read.'),400
        accent=edits.get('accent','')
        bg_colour=edits.get('background_colour','')
        if not isinstance(accent,str) or not isinstance(bg_colour,str):
            return jsonify(error='Invalid colour settings.'),400
        for value in (accent,bg_colour):
            if value and not re.fullmatch(r'#[0-9a-fA-F]{6}',value):
                return jsonify(error='Choose valid colours.'),400
        options={'background':background,'price_position':position,
                 'accent':accent,'background_colour':bg_colour,
                 'display_mode':display_mode,'price_style':price_style,
                 'headline_size':headline_size,'show_subline':edits.get('show_subline',False),
                 'tone':tone,**transforms}
        scene_reference=None
        if scene_bytes is None and background in ('context','workshop','bench','engine'):
            official=(APPLICATION_IMAGE_CACHE.get(part) if
                product.get('application_photo_source') and
                product.get('application_photo_source')!=product.get('photo_source')
                else None)
            selection={"workshop":"workshop","bench":"hand_tools",
                       "engine":"engine"}.get(background)
            seed=int.from_bytes(hashlib.sha256(str(part).encode("utf-8")).digest()[:2],"big")
            scene_bytes,scene_reference=find_scene(
                product,variation=idx+seed,official_photo=official,
                prefer_official=(idx==2 and background=="context" and bool(official)),
                category_override=selection,family=family)
        if scene_reference is None:
            scene_reference=stock_scene_reference(
                classify_product(product),idx,family=family)
        source_art=normalise_art_direction(supplied.get('art_direction'),
                                           family,raw_palette)
        source_art['layout_variant']=raw_palette
        render_options={**options,'_scene_bytes':scene_bytes,
                        '_scene_style':scene_treatment(scene_reference,source_art)}
        focus_info=focus_concept(product,{'family':family},idx)
        concept={'id':idx,'part':str(product.get('part','')),
                 'title':str(product.get('title',''))[:125], 'family':family,
                 'name':name or ('Promotional Option '+str(idx+1)),
                 'headline':headline or str(product.get('title','Laser Tools'))[:48],
                 'subline':subline,'angle':angle,'features':selected,
                 'focus':focus_info['focus'],'focus_label':focus_info['focus_label'],
                 'selling_point':focus_info['selling_point'],
                 'variant':raw_palette,'art_direction':source_art,
                 'editor':{**options,'palette':raw_palette}}
        quality={}
        render_options['_quality_report']=quality
        rendered=render_ai_promo(concept,image,product,brand,editor=render_options)
        concept['preview']='data:image/png;base64,'+base64.b64encode(rendered).decode('ascii')
        if quality:
            concept['quality']=quality
            if quality.get('auto_corrected'):
                corrected=int(quality.get('layout_variant',raw_palette))
                concept['variant']=corrected
                concept['editor']['palette']=corrected
                concept['editor'].update(quality.get('effective_editor') or {})
                concept['art_direction']['layout_variant']=corrected
        if scene_reference:
            concept['scene']={k:scene_reference.get(k) for k in (
                'category','description','source','page_url','license_url',
                'scene_type','family','crop')}
        elif scene_bytes:
            concept['scene']={'category':classify_product(product),
                              'description':'Approved uploaded context photo',
                              'source':'Staff-provided photo (confirm usage rights)',
                              'page_url':'','license_url':None}
        concept['copy_direction']=normalise_copy_direction(
            supplied.get('copy_direction'))
        concept['marketing_copy']=compose_promotional_copy(product,concept)
        return jsonify(concept=concept,review_required=True)
    except RuntimeError as exc:
        return jsonify(error=str(exc)),503
    except LookupErrorPublic as exc:
        return jsonify(error=str(exc)),404
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    except Exception:
        app.logger.exception('AI poster edit failed')
        return jsonify(error='Unable to update the poster. Please retry.'),500



# Temporary single-worker pack storage. Random tokens prevent unrelated visitors
# from downloading other distributor drafts; expiry bounds memory on free Render.
CAMPAIGN_PACKS = {}
CAMPAIGN_PACK_LOCK = threading.Lock()
CAMPAIGN_PACK_TTL = 15 * 60


def _get_campaign_pack(token):
    if not re.fullmatch(r'[A-Za-z0-9_-]{24,64}', token):
        return None
    with CAMPAIGN_PACK_LOCK:
        now = time.time()
        for key in list(CAMPAIGN_PACKS):
            if CAMPAIGN_PACKS[key]['expires'] < now:
                CAMPAIGN_PACKS.pop(key, None)
        entry = CAMPAIGN_PACKS.get(token)
        return entry['bundle'] if entry and entry['expires'] >= now else None


@app.post('/api/campaign/<part>')
def one_click_campaign(part):
    """One click creates a full campaign, previews and a complete ZIP.

    Generate draft material only; no automatic social posts or publishing.
    The browser cannot replace verified product photos, technical claims or RRP.
    """
    try:
        part = sku_clean(part)
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify(error='Invalid campaign settings.'), 400
        product, image = lookup(part, uk_url=body.get('official_url') or None)
        if not image:
            return jsonify(error='A genuine official product photograph is required.'), 422
        product = with_reviewed_price(
            product, body.get('staff_rrp_ex'), body.get('staff_rrp_reviewed') is True,
            body.get('staff_rrp_basis', 'ex')
        )
        distributor = selected_distributor(body.get('distributor_brand', 'none'))
        official_context = (
            APPLICATION_IMAGE_CACHE.get(part)
            if product.get('application_photo_source')
            and product.get('application_photo_source') != product.get('photo_source')
            else None
        )
        bundle = build_campaign(product, image, distributor,
                                application_photo=official_context)
        token = secrets.token_urlsafe(24)
        with CAMPAIGN_PACK_LOCK:
            now = time.time()
            for key in list(CAMPAIGN_PACKS):
                if CAMPAIGN_PACKS[key]['expires'] < now:
                    CAMPAIGN_PACKS.pop(key, None)
            while len(CAMPAIGN_PACKS) >= 4:
                CAMPAIGN_PACKS.pop(next(iter(CAMPAIGN_PACKS)))
            CAMPAIGN_PACKS[token] = {'expires': now + CAMPAIGN_PACK_TTL, 'bundle': bundle}
        response = jsonify(token=token, manifest=bundle['manifest'])
        response.headers['Cache-Control'] = 'no-store, private'
        return response
    except LookupErrorPublic as exc:
        return jsonify(error=str(exc)), 400
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        app.logger.exception('Campaign rendering failed')
        return jsonify(error='Campaign could not be completed: ' + str(exc)), 503
    except Exception:
        app.logger.exception('One-click campaign error')
        return jsonify(error='Unable to build the marketing campaign. Please check the application logs.'), 500


@app.post('/api/campaign/edit/<token>/<asset_id>')
def edit_campaign_asset(token, asset_id):
    """Revise exactly one source-verified poster; preserve all other assets."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{24,64}', token):
        return jsonify(error='Invalid or expired campaign link.'), 404
    body=request.get_json(silent=True)
    if not isinstance(body,dict):
        return jsonify(error='Invalid poster edits.'),400
    try:
        from poster_live_edit import edit_campaign_poster
        with CAMPAIGN_PACK_LOCK:
            entry=CAMPAIGN_PACKS.get(token)
            if not entry or entry['expires'] < time.time():
                return jsonify(error='Campaign expired. Please build a new campaign.'),404
            result=edit_campaign_poster(entry['bundle'],asset_id,body)
        response=jsonify(result)
        response.headers['Cache-Control']='no-store, private'
        return response
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    except RuntimeError as exc:
        return jsonify(error='Poster failed quality review: '+str(exc)),422
    except Exception:
        app.logger.exception('Single campaign poster edit failed')
        return jsonify(error='Could not update this poster. Original campaign is unchanged.'),500


@app.get('/api/campaign/manifest/<token>')
def resume_campaign_manifest(token):
    """Recover already completed mobile campaign after Safari tab suspension.

    This only reads an existing short-lived in-memory draft, never repeats
    the Gemini request or creates new artwork. Possession of the same
    unguessable campaign token already grants its existing PNG/ZIP downloads.
    """
    if not re.fullmatch(r'[A-Za-z0-9_-]{24,64}', token):
        return jsonify(error='Invalid or expired campaign link.'), 404
    bundle = _get_campaign_pack(token)
    if bundle is None:
        return jsonify(error='This campaign has expired. Generate a new one.'), 404
    response = jsonify(token=token, manifest=bundle['manifest'])
    response.headers['Cache-Control']='private, no-store, max-age=0'
    return response


@app.get('/api/campaign/download/<token>')
def download_campaign(token):
    bundle = _get_campaign_pack(token)
    if bundle is None:
        return jsonify(error='Campaign link expired. Generate the campaign again.'), 404
    part = re.sub(r'[^A-Za-z0-9_-]', '', str(bundle['manifest'].get('part') or 'Product'))
    response = send_file(io.BytesIO(bundle['archive']), mimetype='application/zip',
                         as_attachment=True,
                         download_name='LASER_' + part + '_Complete_Campaign.zip')
    response.headers['Cache-Control'] = 'no-store, private'
    return response


@app.get('/api/campaign/assets/<token>/<asset_id>')
def preview_campaign_asset(token, asset_id):
    bundle = _get_campaign_pack(token)
    if bundle is None:
        return jsonify(error='Campaign preview expired. Generate it again.'), 404
    asset = bundle['images'].get(asset_id)
    if asset is None:
        return jsonify(error='Campaign asset not found.'), 404
    download_requested = request.args.get('download') == '1'
    response = send_file(
        io.BytesIO(asset), mimetype='image/png',
        as_attachment=download_requested,
        download_name='LASER_' + re.sub(r'[^A-Za-z0-9_-]', '',
            str(bundle['manifest'].get('part') or 'Product')) + '_' + asset_id + '.png'
    )
    response.headers['Cache-Control'] = 'no-store, private'
    return response

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
        distributor=selected_distributor(body.get('distributor_brand','none'))
        product['distributor_brand']=BRAND_LABELS[distributor] if distributor else None
        if distributor:product['brand_use_notice']='Customer logo for draft use only. Obtain brand owner approval before external publication.'
        product['marketing_direction']=strategy_for(product)
        product['technical_layout']=technical_layout_mode(product)
        if not img:return jsonify(error='No verified official product photograph available; marketing posters will not be generated with a fabricated photo.'),422
        assets=create_posters(product,img,APPLICATION_IMAGE_CACHE.get(part),distributor)
        tech=create_fact_sheet_pdf(product,img,APPLICATION_IMAGE_CACHE.get(part),distributor)
        txt=create_marketing_copy(product)
        with io.BytesIO() as zbuf:
            with zipfile.ZipFile(zbuf,'w',zipfile.ZIP_DEFLATED) as z:
                for name,png in assets.items():z.writestr(f'LASER_{part}_{name}.png',png)
                z.writestr(f'LASER_{part}_Technical_Sheet.pdf',tech)
                z.writestr(f'LASER_{part}_Marketing_Copy.txt',txt)
                z.writestr(f'LASER_{part}_Source_Record.json',json.dumps(product,indent=2))
            zbuf.seek(0)
            return send_file(io.BytesIO(zbuf.getvalue()),mimetype='application/zip',download_name=f'LASER_{part}_Marketing_Pack.zip',as_attachment=True)
    except ValueError as e:return jsonify(error=str(e)),400
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
        distributor=selected_distributor(request.args.get('distributor_brand','none'))
        if not img:return jsonify(error='Verified product image missing'),422
        renderer={'Hero':render_hero,'Technical':render_technical,'Price':render_price}[style]
        artwork=renderer(p,img,APPLICATION_IMAGE_CACHE.get(part),distributor) if style in ('Hero','Technical') else renderer(p,img,distributor)
        return send_file(io.BytesIO(artwork),mimetype='image/png',download_name=f'LASER_{part}_{style}.png')
    except ValueError as e:return jsonify(error=str(e)),400
    except LookupErrorPublic as e:return jsonify(error=str(e)),404

if __name__=='__main__':
    app.run(debug=True,host='127.0.0.1',port=5000)
