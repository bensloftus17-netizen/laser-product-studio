"""Optional live generative-AI creative concepts, with source-grounded poster artwork."""
import io, os, json, re, base64
import requests
from PIL import Image, ImageDraw, ImageOps
from poster import font, lines, paragraph

LAYOUTS=("spotlight","split","technical")
def propose(product):
    key=os.environ.get("OPENAI_API_KEY","").strip()
    if not key:
        raise RuntimeError("AI is not configured. Add OPENAI_API_KEY to Render environment variables; the original poster builder still works.")
    features=[str(x).strip()[:175] for x in (product.get("features") or []) if str(x).strip()][:12]
    specs=[{"label":str(k)[:65],"value":str(v)[:110]} for k,v in (product.get("specs") or {}).items()][:12]
    context={"part":product.get("part"),"title":product.get("title"),"description":str(product.get("description",""))[:1100],"features":features,"specs":specs,"category":product.get("marketing_direction",{}).get("category_label","")}
    system=("You are a B2B UK automotive workshop marketing art director for Laser Tools. "
            "Develop exactly THREE genuinely different poster concepts with creative positioning appropriate to the actual product. "
            "Use only the supplied manufacturer record; never invent specifications, vehicle fitment, performance, savings, superiority or prices. "
            "The actual tool photo is provided separately and MUST remain unmodified. "
            "Return ONLY a JSON object with key concepts: array of exactly three objects. "
            "Each concept has: name (max 35 chars), headline (max 65 chars), subline (max 100 chars), "
            "layout (one of spotlight, split, technical), angle (max 140 chars), "
            "feature_ids (array of up to three integer indices into the supplied features array). "
            "Make each visual composition different: spotlight, split, technical used once each. "
            "No unsupported factual assertions in the headlines or sublines. Avoid invented adjectives about performance.")
    payload={"model":os.environ.get("OPENAI_MODEL","gpt-4.1-mini"),"temperature":0.85,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(context,ensure_ascii=False)}],"max_tokens":1100}
    try:
        response=requests.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},json=payload,timeout=38)
        response.raise_for_status()
        raw=json.loads(response.json()["choices"][0]["message"]["content"])
    except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
        raise RuntimeError("The generative AI service could not create recommendations. Check API access and retry.") from exc
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

def render_concept(concept, image_bytes, distributor=None):
    """Non-generative precise print rendering: the tool image itself is never AI-redrawn."""
    from brand_assets import get_brand_image
    W,H=960,1200
    navy="#0C2846";blue="#0874BD";cyan="#29B6EC";white="#FFFFFF";pale="#F1F6FB"
    im=Image.new("RGB",(W,H),white);d=ImageDraw.Draw(im)
    layout=concept["layout"]
    if layout=="spotlight":
        d.rectangle((0,0,W,355),fill=navy);d.rectangle((0,340,W,355),fill=cyan)
        d.rectangle((0,355,W,975),fill=pale)
    elif layout=="split":
        d.rectangle((0,0,W,H),fill=pale);d.polygon([(0,0),(960,0),(960,700),(460,700)],fill=navy)
        d.rectangle((0,0,20,H),fill=cyan)
    else:
        d.rectangle((0,0,W,H),fill=white);d.rectangle((0,0,W,175),fill=navy)
        d.rectangle((0,175,W,185),fill=cyan)
        d.rectangle((50,420,910,920),fill=pale)
    def write(x,y,s,size,fill,maxwidth,maxlines=2,kind="bold"):
        rows=lines(d,s,maxwidth,size,kind,max_lines=maxlines)
        for line in rows:
            d.text((x,y),line,font=font(size,kind),fill=fill);y+=int(size*1.23)
        return y
    label_y=45 if layout!="technical" else 39
    d.text((58,label_y),"LASER",font=font(77,"bold"),fill=white if layout!="split" else white)
    d.text((59,label_y+81),"TOOLS  /  PRODUCT PROMOTION",font=font(18,"bold"),fill=cyan)
    # Place real manufacturer image within its own opaque white image frame.
    source=Image.open(io.BytesIO(image_bytes)).convert("RGB")
    source.thumbnail((760,510),Image.Resampling.LANCZOS)
    if layout=="split":frame=(300,345,920,880)
    elif layout=="technical":frame=(75,445,885,905)
    else:frame=(85,400,875,900)
    x0,y0,x1,y1=frame
    d.rounded_rectangle(frame,radius=22,fill=white,outline="#D7E3EC",width=3)
    src=Image.open(io.BytesIO(image_bytes));src=ImageOps.exif_transpose(src)
    if src.mode=="RGBA":
        rgba=src.copy();rgba.thumbnail((x1-x0-50,y1-y0-45),Image.Resampling.LANCZOS)
        px=x0+(x1-x0-rgba.width)//2;py=y0+(y1-y0-rgba.height)//2
        im.paste(rgba,(px,py),rgba)
    else:
        pic=ImageOps.contain(src.convert("RGB"),(x1-x0-44,y1-y0-40),Image.Resampling.LANCZOS)
        im.paste(pic,(x0+(x1-x0-pic.width)//2,y0+(y1-y0-pic.height)//2))
    d=ImageDraw.Draw(im)
    if layout=="spotlight":
        write(57,190,concept["headline"],52,white,840,2)
        write(57,311,concept["subline"],24,white,830,1,"regular")
    elif layout=="split":
        d.rounded_rectangle((46,195,745,340),radius=12,fill=white)
        write(68,215,concept["headline"],43,navy,650,2)
        write(48,895,concept["subline"],25,navy,850,2,"regular")
    else:
        write(56,218,concept["headline"],53,navy,850,2)
        write(57,366,concept["subline"],24,blue,845,2,"regular")
    lower=975 if layout!="split" else 970
    d.rectangle((0,lower,W,H),fill=navy)
    d.text((55,lower+23),"PART NO. "+concept["part"],font=font(25,"bold"),fill=cyan)
    fy=lower+69
    for feature in concept["features"][:2]:
        fy=write(55,fy,"• "+feature,20,white,840,2,"regular")+7
        if fy>H-65:break
    d.text((56,H-39),"DRAFT — VERIFY PRODUCT CLAIMS BEFORE PUBLICATION",font=font(15,"bold"),fill="#A8C5DC")
    if distributor:
        logo=get_brand_image(distributor)
        if logo:
            logo.thumbnail((190,84))
            if logo.mode=="RGBA":im.paste(logo,(W-logo.width-30,25),logo)
            else:im.paste(logo,(W-logo.width-30,25))
    out=io.BytesIO();im.save(out,format="PNG",optimize=True)
    return out.getvalue()
