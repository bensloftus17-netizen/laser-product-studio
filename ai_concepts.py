"""Optional live generative-AI creative concepts, with source-grounded poster artwork."""
import io, os, json, re, base64
import requests
from PIL import Image, ImageDraw, ImageOps
from ai_design import render_concept  # distinct editorial, product hero, technical layouts

LAYOUTS=("spotlight","split","technical")
def propose(product):
    key=os.environ.get("GEMINI_API_KEY","").strip()
    if not key:
        raise RuntimeError("Gemini AI is not configured. Add GEMINI_API_KEY to Render Environment. The regular poster builder still works.")
    features=[str(x).strip()[:175] for x in (product.get("features") or []) if str(x).strip()][:12]
    specs=[{"label":str(k)[:65],"value":str(v)[:110]} for k,v in (product.get("specs") or {}).items()][:12]
    context={"part":product.get("part"),"title":product.get("title"),"description":str(product.get("description",""))[:1100],"features":features,"specs":specs,"category":product.get("marketing_direction",{}).get("category_label","")}
    system=("You are the creative director at a real automotive workshop tools advertising agency. "
            "Create three visually and commercially DIFFERENT campaign concepts grounded strictly in the supplied manufacturer information. "
            "Not three rewritten versions of the same product name. These are concepts for professional Laser Tools retail advertising. "
            "1: a BOLD PRODUCT SPOTLIGHT: very short, punchy, non-generic headline; product is the hero; use layout spotlight. "
            "2: an APPLICATION STORY: what job / compatible vehicle / practical use makes the product relevant, ONLY if the manufacturer source confirms it; layout split. "
            "3: a SPECIFICATION / PRODUCT DETAIL story: accurate, concrete, technician-facing angle, no unverified figures; layout technical. "
            "Consider the product family: sockets are sold for kit contents and sizes; presses for verified capacity; "
            "specialist service tools for stated application and fitments. "
            "Use factual product details ONLY from manufacturer evidence. Do not claim quality superiority, speed, savings, suitability, "
            "mechanisms, capabilities, or performance not directly established in the evidence. "
            "All ads use original manufacturer product photography separately. "
            "Return ONLY JSON object with key concepts: exactly 3 objects in the above order. "
            "Each: name (short unique internal concept title, max 30 characters), headline (max 52 characters, useful at poster size), "
            "subline (max 96 characters, short and grounded), layout (spotlight/split/technical in order), "
            "angle (why the creative direction sells this specific product, max 140 characters), "
            "feature_ids (up to 2 different zero-based indices into the exact supplied features array). "
            "Prefer genuinely varied visual hierarchy, message and feature selection. "
            "Do not use a near-identical headline twice. Not every headline needs to repeat the full product name.")
    model=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite").strip()
    # Restrict model configuration to identifier characters, never arbitrary URLs.
    if not re.fullmatch(r"[a-zA-Z0-9._-]{3,80}",model):
        raise RuntimeError("Invalid GEMINI_MODEL configuration.")
    url="https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent"
    payload={
        "systemInstruction":{"parts":[{"text":system}]},
        "contents":[{"role":"user","parts":[{"text":json.dumps(context,ensure_ascii=False)}]}],
        "generationConfig":{"temperature":0.85,"responseMimeType":"application/json",
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
        selected=[features[x] for x in ids[:3] if type(x) is int and 0<=x<len(features)]
        def safe(field,maxlen):
            return re.sub(r"[\r\n\t]+"," ",str(c.get(field,""))).strip()[:maxlen]
        cleaned.append({"id":i,"name":safe("name",35) or ("Concept "+str(i+1)),
            "headline":safe("headline",65) or str(product.get("title","Laser Tools"))[:65],
            "subline":safe("subline",100) or str(product.get("title",""))[:100],
            "angle":safe("angle",140),
            "layout":LAYOUTS[i], "features":selected,
            "part":str(product.get("part","")), "title":str(product.get("title",""))[:125]})
    return cleaned

