"""Optional live generative-AI creative concepts, with source-grounded poster artwork."""
import os, json, re, secrets, time
import requests
from ai_promo_renderer import FAMILIES

def propose(product, creative_brief="", only_family=None, tone="trade"):
    """Generate three ideas normally, or ONE new concept for a selected design."""
    if only_family is not None and only_family not in FAMILIES:
        raise ValueError("Unknown promotional family.")
    if tone not in ("trade","technical","premium","sales"):
        tone="trade"
    key=os.environ.get("GEMINI_API_KEY","").strip()
    if not key:
        raise RuntimeError("Gemini AI is not configured. Add GEMINI_API_KEY to Render Environment. The regular poster builder still works.")
    features=[str(x).strip()[:175] for x in (product.get("features") or []) if str(x).strip()][:12]
    specs=[{"label":str(k)[:65],"value":str(v)[:110]} for k,v in (product.get("specs") or {}).items()][:12]
    context={"part":product.get("part"),"title":product.get("title"),"description":str(product.get("description",""))[:1100],"features":features,"specs":specs,"category":product.get("marketing_direction",{}).get("category_label",""),"verified_price":str(product.get("price") or "Price on request")[:60]}
    system=("You are a senior UK automotive trade marketing copywriter. Generate THREE completely DIFFERENT, "
            "short, attention-grabbing PROMOTIONAL advertisement concepts for the actual Laser Tools product in the supplied official data. "
            "All three are SALES POSTERS, NEVER technical specification sheets, blueprint diagrams or educational posters. "
            "Posters already display original product photography, exact part number, official product name and the verified RRP "
            "(or PRICE ON REQUEST where no official UK price is available). "
            "Concept 1 is a colourful BOLD RETAIL PROMOTION with a standout circular price burst. "
            "Concept 2 is a CLEAN PREMIUM PRODUCT PROMOTION with elegant typography and a boxed RRP. "
            "Concept 3 is an ENERGETIC TRADE COUNTER PROMOTION with dramatic angular shapes and a wide price banner. "
            "Write concise, natural UK trade headlines with the TOOL TYPE as the main subject: "
            "e.g. 'Ball Joint Separator for JLR' rather than 'JLR Ball Joint Separation', "
            "'Glow Plug Removal Kit' rather than 'Conquer Sheared Glow Plugs'. "
            "Prefer the manufacturer's own tool noun (puller, separator, charger, "
            "socket set, bleeder, tester) and a verified application when useful. "
            "Keep each headline 2-7 useful words, ideally under 42 characters. "
            "Use direct factual language, without exclamation marks or invented benefits. "
            "Examples of style only: 'Ford EcoBlue Crankshaft Pulley Removal', '72-Tooth Ratchet Set', "
            "'Brake Bleeding for Workshop Service'. Only use those examples if they apply to this product. "
            "NEVER use cheesy slogans or empty excitement, including conquer, upgrade your, unlock, elevate, "
            "precision engineering for, game changer, ultimate, unleash, revolutionise, power through, "
            "master your, game-changing, built to dominate or take control. Prefer factual, useful headlines. "
            "Return concise short sublines and pick 2 or 3 genuine manufacturer feature bullets for each concept. "
            "Only use claims that are directly supported by the official manufacturer description, features or specs provided. "
            "No fabricated vehicle fitment, performance, discount, price reductions, capacity, comparative claims, or invented tools. "
            "Never say SALE, OFF, SAVING, DISCOUNT or LIMITED OFFER unless the source explicitly supports it. "
            "Stay professional, use normal UK English spelling. "
            "Respond with a JSON object with a 'concepts' array of exactly 3 objects in this exact order, each having: "
            "name (max 30 chars), headline (max 48 chars), subline (max 82 chars), "
            "angle (max 120 chars, a marketing explanation), feature_ids (2 or 3 integer indices into the supplied features array). "
            "All three headlines and angles must be meaningfully different. Do not request more input from the user.")
    if only_family is not None:
        kind={"retail":"bold retail promotion","premium":"clean premium retail advert",
              "trade":"dramatic trade counter promotion"}[only_family]
        system=("You are a UK automotive tools advertising copywriter. Generate exactly ONE NEW, "
                "distinct marketing concept for the following verified Laser Tools product. "
                "This must be a "+kind+". This is for a SALES POSTER, not a spec sheet. "
                "Use a "+tone+" writing tone. Never use exaggerated slogans such as conquer, "
                "unlock, elevate, ultimate, upgrade your, precision engineering for, "
                "game changer, revolutionise, unleash, dominate or master your. "
                "Lead with the actual tool noun (e.g. separator, puller, charger), "
            "then its verified workshop application. Keep headlines to 2-7 words. "
            "No generic brand slogans, no exclamation marks. "
                "Write a fresh, specific headline of no more than 48 characters that differs "
                "from the existing product name, a subline no more than 82 characters, "
                "an angle no more than 120 characters and select 1-3 real product features. "
                "Use ONLY supplied manufacturer information. Never invent technical facts, "
                "fitment, discounts, price, savings, warranty or accessories. "
                "Return ONLY JSON: a dict with a 'concepts' array containing exactly one "
                "object with name, headline, subline, angle and feature_ids indices.")
    model=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite").strip()
    # Restrict model configuration to identifier characters, never arbitrary URLs.
    if not re.fullmatch(r"[a-zA-Z0-9._-]{3,80}",model):
        raise RuntimeError("Invalid GEMINI_MODEL configuration.")
    url="https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent"
    payload={
        "systemInstruction":{"parts":[{"text":system}]},
        "contents":[{"role":"user","parts":[{"text":json.dumps(context,ensure_ascii=False)}]}],
        "generationConfig":{"temperature":1.0,"responseMimeType":"application/json",
                            "maxOutputTokens":2200}
    }
    try:
        # Retry only brief Gemini server failures (500/502/503/504).
        # Do not retry quota (429), authentication or missing model errors.
        for attempt in range(3):
            response=requests.post(url,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=payload,timeout=24)
            if getattr(response,"status_code",200) in (500,502,503,504) and attempt<2:
                time.sleep(1.5*(attempt+1))
                continue
            response.raise_for_status()
            break
        body=response.json()
        candidates=body.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no poster ideas. Please retry.")
        parts=candidates[0].get("content",{}).get("parts",[])
        generated="".join(part.get("text","") for part in parts if isinstance(part,dict))
        raw=json.loads(generated)
    except requests.HTTPError as exc:
        status=exc.response.status_code if exc.response is not None else 0
        if status in (400,401,403):
            message="Google Gemini rejected the request or API key. Check GEMINI_API_KEY and free-tier access in Google AI Studio."
        elif status==429:
            message="Gemini free-tier rate limit reached. Try again later; do not enable paid billing."
        elif status==404:
            message="Gemini model unavailable for this Google project. The default is gemini-3.5-flash-lite; check GEMINI_MODEL or your AI Studio project access."
        elif status>=500:
            message="Google Gemini is temporarily unavailable. Retry later."
        else:
            message="Gemini API request failed (HTTP "+str(status)+"). Check your Google AI Studio API key."
        raise RuntimeError(message) from exc
    except requests.Timeout as exc:
        raise RuntimeError("Google Gemini timed out. Try again.") from exc
    except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
        raise RuntimeError("Could not connect to or read the Gemini response. Please retry.") from exc
    # Gemini's JSON mode can return either the requested {"concepts": [...]}
    # object or the bare [...] array. Both represent valid generative output.
    if isinstance(raw,list):
        concepts=raw
    elif isinstance(raw,dict):
        concepts=raw.get("concepts",[])
        # Some model responses nest the array under an object with "items".
        if isinstance(concepts,dict):
            concepts=concepts.get("items",[])
    else:
        concepts=[]
    # Single-design regeneration is a cheaper ONE-concept Gemini request.
    if only_family is not None and isinstance(raw,dict) and not concepts and "headline" in raw:
        concepts=[raw]
    expected=1 if only_family is not None else 3
    if not isinstance(concepts,list) or len(concepts)!=expected:
        raise RuntimeError("Gemini returned an unexpected poster format. Click Generate with AI to retry.")
    cleaned=[]
    for i,c in enumerate(concepts):
        family_index=FAMILIES.index(only_family) if only_family is not None else i
        if not isinstance(c,dict):
            raise RuntimeError("Gemini returned invalid marketing concepts. Try generating again.")
        ids=c.get("feature_ids",[])
        if not isinstance(ids,list):ids=[]
        selected=[]
        for x in ids:
            if type(x) is int and 0<=x<len(features) and features[x] not in selected:
                selected.append(features[x])
            if len(selected)>=3:break
        # Include verified features where Gemini omitted evidence references.
        for item in features:
            if len(selected)>=3:break
            if item not in selected:selected.append(item)
        def safe(field,maxlen):
            return " ".join(str(c.get(field,"")).split())[:maxlen]
        cleaned.append({"id":family_index,
            "name":safe("name",30) or ("Promotional Option "+str(family_index+1)),
            "headline":professional_headline(safe("headline",48),product,features),
            "subline":safe("subline",82) or str(product.get("title",""))[:82],
            "angle":safe("angle",120),
            "family":FAMILIES[family_index],
            "variant":secrets.randbelow(3),  # fresh colour/shapes each press
            "features":selected,
            "part":str(product.get("part","")),
            "title":str(product.get("title",""))[:125]})
    return cleaned


_CHEESY=re.compile(r"\b(conquer|unlock|elevate|unleash|revolutionis[ez]|dominate|ultimate|game[\s-]?chang(?:er|ing)|master\s+your|upgrade\s+your|precision\s+engineering\s+for|take\s+control|power\s+through|discover\s+the|next\s+level|built\s+to\s+dominate)\b",re.I)
_TOOL_NOUNS=("separator","puller","extractor","charger","bleeder","ratchet",
             "socket","wrench","spanner","tester","scanner","press","inductor",
             "adapter","adaptor","removal","tool","kit","set","pliers","cutter")


def professional_headline(raw, product, features=()):
    """Reject hype and misleading noun-free headlines; use verified product title."""
    title=" ".join(str(product.get("title") or "Laser Tools Product").split())
    # Omit redundant manufacturer label, not product facts.
    clean_title=re.sub(r"^(?:Laser\s+Tools?\s+)", "", title, flags=re.I).strip()
    candidate=" ".join(str(raw or "").replace("!","").split())[:48].rstrip(" -,")
    if not candidate or _CHEESY.search(candidate):
        return clean_title[:48].rstrip(" -,")
    title_lower=clean_title.lower()
    text=candidate.lower()
    # A specific tool name beats a vaguely phrased vehicle list or action.
    # Only require nouns that appear in the actual manufacturer title.
    strong_nouns=[w for w in _TOOL_NOUNS if re.search(r"\b"+re.escape(w)+r"s?\b",title_lower)]
    specific=[w for w in strong_nouns if w not in ("kit","set","tool","removal")]
    must_include=specific if specific else strong_nouns
    matched=any(re.search(r"\b"+re.escape(w)+r"s?\b",text) for w in must_include)
    # Puller tools can truthfully be marketed by their removal application.
    if "puller" in specific and re.search(r"\bremov(?:al|e|ing)\b",text):
        matched=True
    if must_include and not matched:
        return clean_title[:48].rstrip(" -,")
    if len(candidate.split())>9:
        return clean_title[:48].rstrip(" -,")
    return candidate


def suggest_headlines(product, family, tone="trade", count=3):
    """Ask the configured Gemini free-tier model for three alternative factual titles."""
    if family not in FAMILIES:raise ValueError("Unknown promotional family")
    if tone not in ("trade","technical","premium","sales"):tone="trade"
    if count!=3:raise ValueError("Exactly three headline options required")
    key=os.environ.get("GEMINI_API_KEY","").strip()
    if not key:raise RuntimeError("Gemini AI is not configured.")
    model=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite").strip()
    if not re.fullmatch(r"[a-zA-Z0-9._-]{3,80}",model):
        raise RuntimeError("Invalid GEMINI_MODEL configuration.")
    features=[str(x).strip()[:165] for x in (product.get("features") or []) if str(x).strip()][:9]
    context={"title":product.get("title"),"part":product.get("part"),
             "description":str(product.get("description",""))[:700],"features":features,
             "family":family,"tone":tone}
    system=("Write exactly THREE distinct factual UK automotive trade poster headlines. "
            "Name the real tool type explicitly; do not make vehicle names the entire title. "
            "Keep each title under about 7 words and use a practical workshop tone. "
            "Return JSON as {\"headlines\":[\"...\",\"...\",\"...\"]}, no other fields. "
            "Each max 48 chars. Tone: "+tone+". Prefer a verified tool action, feature, "
            "application or vehicle fitment. The three must use different wording. "
            "No fabricated claims, prices, discounts or unsupported fits. "
            "NEVER say conquer, unlock, elevate, unleash, upgrade your, ultimate, "
            "game changer, precision engineering for, revolutionise, or dominate. "
            "Not poetry, not slogans: real product marketing for UK mechanics.")
    url="https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent"
    payload={"systemInstruction":{"parts":[{"text":system}]},
             "contents":[{"role":"user","parts":[{"text":json.dumps(context,ensure_ascii=False)}]}],
             "generationConfig":{"responseMimeType":"application/json","temperature":.8,
                                 "maxOutputTokens":500}}
    try:
        for attempt in range(3):
            response=requests.post(url,headers={"x-goog-api-key":key,
                                   "Content-Type":"application/json"},json=payload,timeout=24)
            if getattr(response,"status_code",200) in (500,502,503,504) and attempt<2:
                time.sleep(1.5*(attempt+1));continue
            response.raise_for_status()
            break
        response_body=response.json()
        chunks=response_body.get("candidates",[])[0].get("content",{}).get("parts",[])
        parsed=json.loads("".join(v.get("text","") for v in chunks))
    except (requests.RequestException,IndexError,ValueError,KeyError) as exc:
        raise RuntimeError("Gemini headline suggestions are unavailable. Retry later.") from exc
    raw=parsed.get("headlines") if isinstance(parsed,dict) else parsed
    if not isinstance(raw,list):
        raise RuntimeError("Gemini did not return headline choices.")
    options=[]
    for item in raw:
        if not isinstance(item,str):continue
        title=professional_headline(item,product,features)
        if title.lower() not in [v.lower() for v in options]:
            options.append(title)
    if len(options)<3:
        for part in [str(product.get("title",""))]+features:
            title=" ".join(part.split())[:48].rstrip()
            if title and title.lower() not in [v.lower() for v in options]:
                options.append(title)
            if len(options)>=3:break
    return options[:3]
