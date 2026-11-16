"""Optional live generative-AI creative concepts, with source-grounded poster artwork."""
import io, os, json, re, base64, hashlib
import requests
from PIL import Image, ImageDraw, ImageOps
from ai_creative_engine import render_concept, STYLE_GROUPS

def propose(product, creative_brief=""):
    key=os.environ.get("GEMINI_API_KEY","").strip()
    if not key:
        raise RuntimeError("Gemini AI is not configured. Add GEMINI_API_KEY to Render Environment. The regular poster builder still works.")
    features=[str(x).strip()[:175] for x in (product.get("features") or []) if str(x).strip()][:12]
    specs=[{"label":str(k)[:65],"value":str(v)[:110]} for k,v in (product.get("specs") or {}).items()][:12]
    context={"part":product.get("part"),"title":product.get("title"),"description":str(product.get("description",""))[:1100],"features":features,"specs":specs,"category":product.get("marketing_direction",{}).get("category_label",""),"creative_request":str(creative_brief or "")[:230]}
    system=("You are the lead visual and copy art director for a premium UK automotive tool brand. "
            "Your task is to propose three visually DIVERGENT high-end advertising posters for the product described in the supplied manufacturer record. "
            "It must WOW a room full of professional tool reps, not look like three variations of a generic brochure. "
            "You choose real, substantially different visual design directions that the print compositor can render. "
            "Concept 1 is a BIG, HIGH-IMPACT CAMPAIGN for retail: choose visual_style cinematic, retail, diagonal or industrial. "
            "Concept 2 is an ELEGANT EDITORIAL PRODUCT AD telling a different factual customer story: choose visual_style editorial, minimal or feature. "
            "Concept 3 is a BOLD TECHNICIAN-LED SPECIFICATION CAMPAIGN: choose visual_style blueprint or data. "
            "Vary message hierarchy, visual weight, colour use, product photograph scale, whitespace and text treatment between concepts. "
            "The model must generate different HEADLINES and supporting explanations, not repeat the full catalogue title on all three. "
            "Think like an advertising agency: concise, memorable and clear, with individual artistic intent. "
            "The tool category matters: ratchet sets - true drive sizes and kit pieces; hydraulic presses - verified capacity; "
            "specialist bearing tools - confirmed vehicle applications and functionality; diagnostics - verified technical features. "
            "The manufacturer record is the only approved source of factual assertions. Never invent fitments, material, force, torque, speed, "
            "performance advantages, ergonomics, warranty, discounts or specifications. Avoid vague superlatives or unsupported benefits. "
            "Use original product imagery ONLY, placed by the renderer, not redrawn. "
            "A user creative_request may guide visual tone, but can never override fact accuracy, product photo or Laser Tools branding. "
            "Return ONLY a JSON object with key concepts: exactly 3 objects IN ORDER. "
            "Each object has name (max 35 chars), headline (max 46 chars, preferably 2-6 words), "
            "subline (max 78 chars, preferably 7-12 words), visual_style (one of the allowed choices for its concept), "
            "angle (max 135 chars, explain the distinct commercial idea), "
            "feature_ids (array of 1-2 integer 0-based indices into the EXACT features list). "
            "Do not use similar headlines, crop the photo, or suggest images not supplied. "
            "Never say the product is better than competitors without evidence.")
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
    concepts=raw.get("concepts",[])
    if not isinstance(concepts,list) or len(concepts)!=3:raise RuntimeError("AI returned an invalid set of concepts. Please retry.")
    cleaned=[]
    for i,c in enumerate(concepts):
        if not isinstance(c,dict):raise RuntimeError("AI concept response was invalid.")
        ids=c.get("feature_ids",[])
        if not isinstance(ids,list):ids=[]
        selected=[]
        for x in ids:
            if type(x) is int and 0<=x<len(features) and features[x] not in selected:
                selected.append(features[x])
            if len(selected)>=2:break
        def safe(field,maxlen):
            return re.sub(r"[\\r\\n\\t]+"," ",str(c.get(field,""))).strip()[:maxlen]
        chosen=safe("visual_style",25).lower()
        if chosen not in STYLE_GROUPS[i]:
            # Gemini has creative freedom within each dramatically different
            # family. Gracefully handle an out-of-schema creative suggestion.
            seed=(str(product.get("part",""))+safe("headline",46)+str(i)).encode("utf-8")
            chosen=STYLE_GROUPS[i][int(hashlib.sha256(seed).hexdigest()[:8],16)%len(STYLE_GROUPS[i])]
        cleaned.append({"id":i,
            "name":safe("name",35) or ("Concept "+str(i+1)),
            "headline":safe("headline",46) or str(product.get("title","Laser Tools"))[:46],
            "subline":safe("subline",78) or str(product.get("title",""))[:78],
            "angle":safe("angle",135),
            "visual_style":chosen, "features":selected,
            "part":str(product.get("part","")), "title":str(product.get("title",""))[:125]})
    return cleaned
