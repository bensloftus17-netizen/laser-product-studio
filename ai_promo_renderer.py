"""One-click Gemini promo posters: three DISTINCT price-led, brand-safe advertising styles.

All posters use genuine manufacturer product photos, verified product price,
a current Laser Tools part number and verified feature text. Gemini provides
headline and marketing angle, not prices or physical tools.
"""
from __future__ import annotations
import io
import re
from PIL import Image, ImageDraw
from ai_creative_engine import W,H,_txt,_product,_brand_logo,WHITE,NAVY,INK,LINE,SLATE
from poster import font

PALE="#F4F8FC"
BLUE="#036CB9"
CYAN="#23B4EA"
RRP_RE=re.compile(r"£\s*(\d[\d,]*(?:\.\d{1,2})?)")

# The three visual families NEVER use the same structure, price treatment or palette.
RETAIL_PALETTES=(
    {"bg":"#076BC0","deep":"#06396F","accent":"#FFCC32","label":"#061F38"},
    {"bg":"#0B6099","deep":"#102A53","accent":"#F99B29","label":"#102A53"},
    {"bg":"#153D92","deep":"#091D48","accent":"#BDE653","label":"#091D48"},
)
PREMIUM_PALETTES=(
    {"paper":"#FBFAF5","pale":"#EEEDE5","accent":"#B58A3E","deep":"#153450"},
    {"paper":"#FAFCFE","pale":"#E8F2F8","accent":"#139BD3","deep":"#133651"},
    {"paper":"#F7F8FB","pale":"#E9EFF6","accent":"#408C98","deep":"#132C51"},
)
TRADE_PALETTES=(
    {"dark":"#142633","deep":"#081B2B","accent":"#FFAD28","side":"#1B648F"},
    {"dark":"#092B45","deep":"#06192E","accent":"#25C7EE","side":"#075C98"},
    {"dark":"#252D36","deep":"#101B29","accent":"#D8EA60","side":"#1A6689"},
)
FAMILIES=("retail","premium","trade")


def verified_price(product):
    """Read only the verified/staff-reviewed price, never estimate or convert VAT."""
    raw=str(product.get("price") or "").strip()
    m=RRP_RE.search(raw)
    if not m:
        return {"amount":None,"label":"PRICE ON REQUEST","vat":"",
                "provenance":"No verified RRP available"}
    amount="£"+m.group(1)
    lower=raw.lower()
    if "including vat" in lower or "inc vat" in lower:
        vat="INC VAT"
    elif "excluding vat" in lower or "ex vat" in lower:
        vat="EX VAT"
    else:
        vat="VAT STATUS TO CONFIRM"
    reviewed=str(product.get("price_source") or "").lower().startswith("staff entry")
    return {"amount":amount,"label":"UK RRP" if not reviewed else "DRAFT UK RRP",
            "vat":vat,"provenance":"STAFF PRICE — APPROVAL REQUIRED" if reviewed else
            "CONFIRM CURRENT RRP BEFORE RELEASE"}


def _laser(d,x,y,dark=False,size=85):
    color=NAVY if dark else WHITE
    d.text((x,y),"LASER",font=font(size,"bold"),fill=color)
    d.text((x+3,y+size-4),"TOOLS",font=font(19,"bold"),fill=BLUE if dark else CYAN)


def _part(d,product,rect,fill=WHITE):
    _txt(d,"PART NO. "+str(product.get("part","")),rect,(37,32,27),fill,"bold",1)


def _footer(d,price,light=False):
    textcolor=SLATE if light else "#B6D0E1"
    d.line((54,H-92,W-54,H-92),fill=LINE if light else "#3C5C75",width=2)
    _txt(d,"DRAFT • PRODUCT & PRICE REVIEW REQUIRED",(56,H-74,W-55,H-30),
         (17,15),textcolor,"bold",1)


def _info(d,concept,rects,color,size=(28,25,22,19)):
    items=concept.get("features") or []
    for idx,rect in enumerate(rects):
        if idx>=len(items):break
        x,y,x2,y2=rect
        d.ellipse((x,y+12,x+13,y+25),fill=color)
        _txt(d,items[idx],(x+24,y,x2,y2),size,color,"regular",3)


def _circle_price(d,price,box,accent,textcolor,offset=0):
    x0,y0,x1,y1=box
    d.ellipse((x0+18,y0+18,x1+19,y1+19),fill="#12344B")
    d.ellipse((x0,y0,x1,y1),fill=accent)
    _txt(d,price["label"],(x0+27,y0+62,x1-27,y0+103),(24,21),textcolor,"bold",1,align="center")
    _txt(d,price["amount"] or "PRICE ON",(x0+18,y0+133,x1-18,y0+235),
         (64,57,49,42,36),textcolor,"bold",2,align="center")
    if price["amount"]:
        _txt(d,price["vat"],(x0+24,y0+246,x1-24,y0+300),
             (23,20),textcolor,"bold",1,align="center")
    else:
        _txt(d,"REQUEST",(x0+24,y0+220,x1-24,y0+290),(41,37),textcolor,"bold",1,align="center")


def _retail(concept,photo,product,price,variation):
    """Loud but usable RETAIL advert: angular stripes, oversized circular RRP bubble."""
    p=RETAIL_PALETTES[variation%len(RETAIL_PALETTES)]
    base=Image.new("RGBA",(W,H),p["bg"])
    d=ImageDraw.Draw(base)
    d.polygon([(0,0),(W,0),(W,395),(0,565)],fill=p["deep"])
    d.polygon([(0,565),(W,386),(W,600),(0,795)],fill=WHITE)
    d.polygon([(0,1240),(W,1030),(W,1500),(0,1500)],fill=p["deep"])
    d.polygon([(910,0),(W,0),(W,400),(1050,419)],fill=p["accent"])
    _laser(d,59,38)
    _part(d,product,(60,170,655,223),WHITE)
    _txt(d,concept.get("headline"),(56,246,1050,466),
         (86,78,69,61,53,47,41),WHITE,"bold",3)
    _txt(d,product.get("title"),(57,526,1110,631),
         (36,32,29,25,22),p["deep"],"bold",3)
    # Large photograph takes central stage; price is an independent bold circle.
    # Reserve a separate zone for the circular price burst so it cannot
    # obscure the real tool photo (especially long socket/ratchet sets).
    _product(base,photo,(34,668,786,1152),shadow=True)
    d=ImageDraw.Draw(base)
    _circle_price(d,price,(792,835,1164,1207),p["accent"],p["label"])
    _info(d,concept,[(61,1284,1100,1333),(61,1338,1100,1393)],
          WHITE,(25,22,19))
    _footer(d,price)
    return base


def _premium(concept,photo,product,price,variation):
    """Upscale PREMIUM print advert: ivory white space, huge genuine product, tidy price plaque."""
    p=PREMIUM_PALETTES[variation%len(PREMIUM_PALETTES)]
    base=Image.new("RGBA",(W,H),p["paper"])
    d=ImageDraw.Draw(base)
    d.rectangle((0,0,W,18),fill=p["deep"])
    d.rectangle((0,1054,W,H),fill=p["pale"])
    d.rectangle((60,214,1134,220),fill=p["accent"])
    _laser(d,59,42,dark=True,size=88)
    _txt(d,"PRODUCT SPOTLIGHT",(60,164,1000,212),(24,21),p["accent"],"bold",1)
    _txt(d,concept.get("headline"),(57,263,1135,461),
         (91,81,72,64,57,49),p["deep"],"bold",3)
    _part(d,product,(61,478,780,532),p["accent"])
    # Almost full-width clean product photo; right-angle layout not seen in retail.
    _product(base,photo,(52,560,1140,1040),shadow=True)
    d=ImageDraw.Draw(base)
    _txt(d,product.get("title"),(58,1091,700,1231),
         (40,36,32,28,25),p["deep"],"bold",4)
    _info(d,concept,[(61,1270,705,1320),(61,1330,705,1384)],
          p["deep"],(23,21,18))
    # White bordered price PLAQUE rather than retail circle.
    d.rounded_rectangle((740,1116,1143,1387),radius=23,fill=WHITE,outline=p["accent"],width=5)
    _txt(d,price["label"],(775,1144,1118,1188),(25,22),p["accent"],"bold",1)
    _txt(d,price["amount"] or "PRICE ON REQUEST",(763,1211,1118,1309),
         (65,57,49,40,33),p["deep"],"bold",2)
    if price["amount"]:
        _txt(d,price["vat"],(776,1324,1117,1361),(23,20),p["deep"],"regular",1)
    _footer(d,price,light=True)
    return base


def _trade(concept,photo,product,price,variation):
    """Dark TRADE promo: asymmetric split, orange/cyan graphics, wide RRP banner."""
    p=TRADE_PALETTES[variation%len(TRADE_PALETTES)]
    base=Image.new("RGBA",(W,H),p["dark"])
    d=ImageDraw.Draw(base)
    d.polygon([(505,0),(W,0),(W,1160),(665,1180)],fill=p["side"])
    d.polygon([(845,0),(W,0),(W,1150),(1000,1142)],fill=p["deep"])
    for k in range(4):
        off=k*122
        d.line((680+off,470,385+off,1170),fill="#287DA8",width=4)
    d.polygon([(0,1175),(1200,1100),(1200,1500),(0,1500)],fill=p["deep"])
    d.polygon([(0,1175),(1200,1100),(1200,1131),(0,1205)],fill=p["accent"])
    _laser(d,58,39)
    _part(d,product,(60,174,740,228),p["accent"])
    # Narrow left copy; tall giant packshot on right in contrasting graphic field.
    _txt(d,concept.get("headline"),(59,295,530,685),
         (66,59,52,46,41,36,31),WHITE,"bold",6)
    d.rectangle((60,730,425,740),fill=p["accent"])
    _txt(d,product.get("title"),(59,784,497,989),
         (32,29,26,23,21),WHITE,"bold",5)
    _product(base,photo,(500,295,1180,1120),shadow=True)
    d=ImageDraw.Draw(base)
    _txt(d,price["label"],(61,1232,700,1288),(29,26),p["accent"],"bold",1)
    _txt(d,price["amount"] or "PRICE ON REQUEST",(53,1290,910,1402),
         (99,87,77,64,51),WHITE,"bold",2)
    if price["amount"]:
        _txt(d,price["vat"],(910,1340,1150,1400),(26,23,20),WHITE,"bold",1,align="right")
    _footer(d,price)
    return base


RENDERERS={"retail":_retail,"premium":_premium,"trade":_trade}


def render_promo(concept,photo,product,distributor=None):
    """Create one of three meaningfully different full-size promotional designs."""
    family=concept.get("family","retail")
    if family not in RENDERERS:
        raise ValueError("Unknown promotional design family.")
    price=verified_price(product)
    variant=int(concept.get("variant",0))%3
    canvas=RENDERERS[family](concept,photo,product,price,variant)
    _brand_logo(canvas,distributor)
    output=io.BytesIO()
    canvas.convert("RGB").save(output,format="PNG",optimize=True)
    return output.getvalue()
