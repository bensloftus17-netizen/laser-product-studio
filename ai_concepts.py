"""Optional live generative-AI creative concepts, with source-grounded poster artwork."""
import os, json, re, secrets, time
import requests
from ai_promo_renderer import FAMILIES
from promo_art_direction import normalise_art_direction
from promo_copy import normalise_copy_direction
from promo_selling_points import focus_concept
from campaign_strategy import strategy_options
from campaign_director import third_angle_options
from creative_director import creative_instruction

def _gemini_json(payload, key, model):
    """Read Gemini JSON with bounded retries and actionable, non-secret errors.

    HTTP 200 does not guarantee that the model finished writing the JSON.
    Gemini may end with MAX_TOKENS or produce empty/truncated candidate text.
    """
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
    for attempt in range(2):
        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=payload,
                timeout=28,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status in (500, 502, 503, 504) and attempt == 0:
                time.sleep(1.5)
                continue
            if status in (400, 401, 403):
                message = ("Google Gemini rejected the request or API key (HTTP "
                           + str(status) + "). Check GEMINI_API_KEY, GEMINI_MODEL "
                           "and model access in Google AI Studio.")
            elif status == 429:
                message = ("Gemini API quota or rate limit reached (HTTP 429). "
                           "Check your free-tier limits in Google AI Studio.")
            elif status == 404:
                message = ("Gemini model unavailable (HTTP 404). Check GEMINI_MODEL "
                           "and model access for your API key in Google AI Studio.")
            elif status >= 500:
                message = ("Google Gemini is temporarily unavailable (HTTP "
                           + str(status) + "). Try again shortly.")
            else:
                message = "Gemini API request failed (HTTP " + str(status) + ")."
            raise RuntimeError(message) from exc
        except requests.Timeout as exc:
            if attempt == 0:
                continue
            raise RuntimeError("Gemini timed out twice. Retry later or check Render logs.") from exc
        except requests.ConnectionError as exc:
            if attempt == 0:
                continue
            raise RuntimeError("The server could not reach Google's Gemini API. Check Render networking and DNS.") from exc
        except requests.RequestException as exc:
            raise RuntimeError("The Gemini API request failed. Check Render logs for network errors.") from exc

        try:
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("Expected a Gemini response object")
            candidates = body.get("candidates") or []
            candidate = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
            reason = candidate.get("finishReason", "")
            if reason == "MAX_TOKENS":
                if attempt == 0:
                    continue
                raise RuntimeError(
                    "Gemini stopped before finishing its JSON response (MAX_TOKENS). "
                    "Try again or increase the output limit."
                )
            if reason and reason not in ("STOP", "FINISH_REASON_UNSPECIFIED"):
                raise RuntimeError("Gemini could not finish the response ("
                                   + str(reason)[:40] + "). Check model access and input policy.")
            parts = candidate.get("content", {}).get("parts", [])
            generated = "".join(
                part.get("text", "") for part in parts
                if isinstance(part, dict) and isinstance(part.get("text", ""), str)
            )
            if not generated.strip():
                raise ValueError("Gemini returned no JSON text")
            return json.loads(generated)
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            if attempt == 0:
                continue
            raise RuntimeError(
                "Gemini returned incomplete or invalid JSON twice. "
                "Check GEMINI_MODEL and the Render logs if the problem persists."
            ) from exc
    raise RuntimeError("Gemini did not return a usable response.")


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
    if only_family is None:
        # Gives the existing single Gemini request constrained marketing choices
        # in addition to the poster designs. No second API call or extra outage risk.
        context["strategy_options"]=strategy_options(product)
        context["third_angle_options"]=third_angle_options(product)
    system=("You are a senior UK automotive trade marketing copywriter. Generate THREE completely DIFFERENT, "
            "short, attention-grabbing PROMOTIONAL advertisement concepts for the actual Laser Tools product in the supplied official data. "
            "All three are SALES POSTERS, NEVER technical specification sheets, blueprint diagrams or educational posters. "
            "Posters already display original product photography, exact part number, official product name and the verified RRP "
            "(or PRICE ON REQUEST where no official UK price is available). "
            "Concept 1 is a colourful BOLD RETAIL PROMOTION focused on the source-confirmed UK RRP "
            "(or price on request), without suggesting an unsupported discount. "
            "Concept 2 is a CLEAN PREMIUM PRODUCT PROMOTION focused on one real practical "
            "benefit in the manufacturer's verified features, with elegant typography. "
            "Concept 3 is a TRADE WORKSHOP PROMOTION focused on the tool's confirmed "
            "vehicle fitments and workshop applications. If there is no verified "
            "vehicle compatibility, focus on the source-backed task, not a guessed vehicle. "
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
            "All three headlines and angles must be meaningfully different. "
            "For each concept ALSO return art_direction: an object recommending the visual arrangement. "
            "Use only these fields: layout_variant (integer 0,1,2 selecting three structurally distinct layouts "
            "within the poster's family), price_style (bubble/plaque/banner/tag/sticker/corner/panel), "
            "price_position (standard/opposite), accent (one of #F6D343 #F9A842 #13B5EC #D9E75B "
            "#40C1E8 #F1E9D8 #E8F4F4 #FFCB5B #FFFFFF), "
            "product_scale (integer 85..125), product_x and product_y (integers -30..30), "
            "headline_size (small/normal/large), graphic_motif (none/speed-lines/circles/"
            "industrial-grid/diagonal-bars), photo_focus (left/centre/right), "
            "background_mood (bright/balanced/dramatic). "
            "Select layouts and product photo treatment that suit THIS ACTUAL product. "
            "Each of the three art directions must differ in composition, colour and graphic motifs. "
            "The real product photograph, verified RRP and source claims remain fixed. "
            "For each concept ALSO include copy_direction: a compact object with three "
            "fields, tone (direct/practical/professional), hook (product/application/feature), "
            "and cta (details/enquire/specifications). Choose different copy styles for "
            "Retail, Premium and Trade. The app will use these choices to compose a short "
            "social caption, a LinkedIn post, a customer email and relevant hashtags using "
            "only the supplied verified facts. Never write unsupported marketing claims. "
            "For the unified campaign, choose the BEST THIRD POSTER ANGLE for this "
            "specific tool category. The main Build Campaign action always makes "
            "(1) a technical/application poster and (2) a price-led sales poster. "
            "The third must add a DIFFERENT category-relevant point, never simply "
            "repeat the technical or price poster. Choose only one value from "
            "third_angle_options, and include it as marketing_strategy.third_angle. "
            "Do not claim the model trained on sales performance: explain choices "
            "only from manufacturer-supplied product information. "
            "Also return a top-level 'marketing_strategy' object (not inside a concept), "
            "with audience_id (one of strategy_options.audiences IDs), "
            "primary_focus (one of strategy_options.focus_options), "
            "channels (exactly two distinct IDs from strategy_options.channel_options), "
            "and proof_index (integer index into strategy_options.proof_options). "
            "The audience is a marketing hypothesis, not a verified customer or fitment. "
            "Select a suitable audience, selling angle, factual proof and communications "
            "channels for THIS product. Do not invent extra prospects, proof or conclusions. "
            "The application validates your choices and writes all justifications from "
            "approved source-based information. "
            "Do not request more input from the user.")
    if only_family is None:
        system += " " + creative_instruction()
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
                "object with name, headline, subline, angle, feature_ids indices "
                "and art_direction using the same constrained keys as the ordinary "
                "three-poster response: layout_variant 0..2, price_style bubble/plaque/"
                "banner/tag/sticker/corner/panel, price_position standard/opposite, "
                "accent (an approved Laser blue/yellow/cyan hex), product_scale 85..125, "
                "product_x/y -30..30, headline_size small/normal/large, "
                "graphic_motif none/speed-lines/circles/industrial-grid/diagonal-bars, "
                "photo_focus left/centre/right and background_mood bright/balanced/dramatic. "
                "Also return copy_direction with tone direct/practical/professional, "
                "hook product/application/feature and cta details/enquire/specifications.")
    model=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite").strip()
    # Restrict model configuration to identifier characters, never arbitrary URLs.
    if not re.fullmatch(r"[a-zA-Z0-9._-]{3,80}",model):
        raise RuntimeError("Invalid GEMINI_MODEL configuration.")
    payload={
        "systemInstruction":{"parts":[{"text":system}]},
        "contents":[{"role":"user","parts":[{"text":json.dumps(context,ensure_ascii=False)}]}],
        # 2,200 tokens could exhaust the allowance before Gemini completes
        # three multi-field concepts, including model thinking tokens.
        "generationConfig":{"temperature":0.65,"responseMimeType":"application/json",
                            "maxOutputTokens":2500 if only_family else 8500}
    }
    raw = _gemini_json(payload, key, model)
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
        variant=secrets.randbelow(3)
        direction=normalise_art_direction(c.get("art_direction"),FAMILIES[family_index],variant)
        cleaned.append(focus_concept(product,{"id":family_index,
            "name":safe("name",30) or ("Promotional Option "+str(family_index+1)),
            "headline":professional_headline(safe("headline",48),product,features),
            "subline":safe("subline",82) or str(product.get("title",""))[:82],
            "angle":safe("angle",120),
            "family":FAMILIES[family_index],
            "variant":direction["layout_variant"],
            "art_direction":direction,
            "creative_canvas":c.get("creative_canvas") if isinstance(c.get("creative_canvas"),dict) else None,
            "copy_direction":normalise_copy_direction(c.get("copy_direction")),
            "features":selected,
            "part":str(product.get("part","")),
            "title":str(product.get("title",""))[:125]},family_index))
    # Attach the strictly enumerated choice to the first concept. The
    # campaign builder validates IDs again against the manufacturer record.
    # Existing AI poster callers remain compatible with the concept list.
    if only_family is None and isinstance(raw,dict) and isinstance(raw.get("marketing_strategy"),dict):
        cleaned[0]["ai_strategy_choice"]=raw["marketing_strategy"]
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
    payload={"systemInstruction":{"parts":[{"text":system}]},
             "contents":[{"role":"user","parts":[{"text":json.dumps(context,ensure_ascii=False)}]}],
             "generationConfig":{"responseMimeType":"application/json","temperature":0.65,
                                 "maxOutputTokens":1600}}
    parsed = _gemini_json(payload, key, model)
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
