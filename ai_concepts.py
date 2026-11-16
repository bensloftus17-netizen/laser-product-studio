"""Optional live generative-AI creative concepts, with source-grounded poster artwork."""
import os, json, re, secrets
import requests
from ai_promo_renderer import FAMILIES

def propose(product, creative_brief=""):
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
            "Write creative, concise, different headlines that do not simply repeat the catalogue title. "
            "Return concise short sublines and pick 2 or 3 genuine manufacturer feature bullets for each concept. "
            "Only use claims that are directly supported by the official manufacturer description, features or specs provided. "
            "No fabricated vehicle fitment, performance, discount, price reductions, capacity, comparative claims, or invented tools. "
            "Never say SALE, OFF, SAVING, DISCOUNT or LIMITED OFFER unless the source explicitly supports it. "
            "Stay professional, use normal UK English spelling. "
            "Respond with a JSON object with a 'concepts' array of exactly 3 objects in this exact order, each having: "
            "name (max 30 chars), headline (max 48 chars), subline (max 82 chars), "
            "angle (max 120 chars, a marketing explanation), feature_ids (2 or 3 integer indices into the supplied features array). "
            "All three headlines and angles must be meaningfully different. Do not request more input from the user.")
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
        response=requests.post(url,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=payload,timeout=45)
        response.raise_for_status()
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
    if not isinstance(concepts,list) or len(concepts)!=3:
        raise RuntimeError("Gemini returned an unexpected poster format. Click Generate with AI to retry.")
    cleaned=[]
    for i,c in enumerate(concepts):
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
        cleaned.append({"id":i,
            "name":safe("name",30) or ("Promotional Option "+str(i+1)),
            "headline":safe("headline",48) or str(product.get("title","Laser Tools"))[:48],
            "subline":safe("subline",82) or str(product.get("title",""))[:82],
            "angle":safe("angle",120),
            "family":FAMILIES[i],
            "variant":secrets.randbelow(3),  # fresh colour/shapes each press
            "features":selected,
            "part":str(product.get("part","")),
            "title":str(product.get("title",""))[:125]})
    return cleaned
