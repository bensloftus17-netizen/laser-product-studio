"""Six alternative, substantially different automotive advertising compositions.

Each original Retail/Premium/Trade family now has three layout structures,
not three recolourings of the same geometry. All use source product pixels,
manufacturer facts, reviewed RRP and real/licensed context photos only.
"""
from __future__ import annotations

from PIL import Image, ImageDraw


def render_variant(family, variant, concept, photo, product, price, editor, scene):
    # Imported at call time to avoid importing ai_cinematic while it is still
    # defining the dispatch table that calls this module.
    if family=="retail":
        return (_retail_split if variant==1 else _retail_typographic)(
            concept,photo,product,price,editor,scene)
    if family=="premium":
        return (_premium_gallery if variant==1 else _premium_column)(
            concept,photo,product,price,editor,scene)
    return (_trade_industrial if variant==1 else _trade_diagonal)(
        concept,photo,product,price,editor,scene)


def _shared():
    from ai_cinematic import (
        _photo_stage,_scene_base,_brand,_headline,_rrp,_product,
        _fit,_features,_footer,_readable_ink,_accent,COLOURS)
    return (_photo_stage,_scene_base,_brand,_headline,_rrp,_product,
            _fit,_features,_footer,_readable_ink,_accent,COLOURS)


def _retail_split(concept,photo,product,price,editor,scene):
    """Variant B: saturated diagonal split, giant product and low-left price."""
    (stage,_,brand,headline,rrp,hero,fit,features,footer,ink,accent,palette)=_shared()
    p=palette["retail"][1];gold=accent(editor,p["accent"])
    canvas=Image.new("RGBA",(1200,1500),"#0569B0")
    canvas.alpha_composite(stage(scene,(430,190,1200,1230),.22,2.4,
                                editor.get("_scene_style")),(430,190))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,0),(660,0),(497,1270),(0,1330)],fill=(3,43,93,249))
    d.polygon([(650,0),(713,0),(528,1270),(472,1270)],fill=gold)
    d.polygon([(0,1270),(1200,1170),(1200,1500),(0,1500)],fill=(3,30,59,248))
    d.polygon([(0,1261),(1200,1161),(1200,1183),(0,1282)],fill=gold)
    hero(canvas,photo,product,(390,390,1182,1192),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    brand(d,p["primary"],product.get("part",""),family="retail")
    fit(d,concept.get("focus_label","TRADE PROMOTION"),(55,302,522,361),(33,29,25),gold,"bold",1)
    headline(d,concept,(55,385,512,750),(80,69,59,50,43),
             "#FFFFFF",5,editor)
    if editor.get("show_subline"):
        fit(d,concept.get("subline"),(62,789,479,888),
            (28,24,21),"#E9F7FF","regular",3)
    features(d,concept,[(62,931,481,1086)],gold)
    style=editor.get("price_style","bubble")
    box=(55,1115,410,1470) if editor.get("price_position")!="opposite" else (745,1115,1100,1470)
    if style!="bubble":
        box=(55,1260,618,1442) if editor.get("price_position")!="opposite" else (602,1260,1165,1442)
    d=ImageDraw.Draw(canvas)
    rrp(d,price,box,style,gold,ink(gold,p["ink"]))
    footer(d)
    return canvas


def _retail_typographic(concept,photo,product,price,editor,scene):
    """Variant C: bright magazine-style poster with huge application photo."""
    (stage,_,brand,headline,rrp,hero,fit,features,footer,ink,accent,palette)=_shared()
    p=palette["retail"][2];gold=accent(editor,p["accent"])
    canvas=Image.new("RGBA",(1200,1500),"#F3F8FB")
    # Photo belongs to a tall left-hand block; cutout hero floats across both.
    canvas.alpha_composite(stage(scene,(0,410,785,1218),.24,3.1,
                                editor.get("_scene_style")),(0,410))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,248),fill=(2,48,93,255))
    d.polygon([(0,256),(1200,244),(1200,264),(0,276)],fill=gold)
    d.rectangle((785,410,1200,1218),fill=(225,239,247,255))
    d.polygon([(0,1218),(1200,1178),(1200,1500),(0,1500)],fill=(2,43,84,255))
    d.polygon([(0,1211),(1200,1172),(1200,1195),(0,1236)],fill=gold)
    hero(canvas,photo,product,(73,468,1100,1200),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    brand(d,p["primary"],product.get("part",""),family="retail")
    fit(d,concept.get("focus_label","PRODUCT PROMOTION"),(674,91,1145,156),
        (31,27,23),gold,"bold",1,"right")
    # A single striking headline across the open light section.
    d.rounded_rectangle((45,285,1153,416),radius=13,fill=(255,255,255,248))
    headline(d,concept,(72,304,1130,397),
             (78,68,60,52,44),"#06395F",2,editor)
    if editor.get("show_subline"):
        fit(d,concept.get("subline"),(53,1233,736,1303),
            (30,26,23),"#F2F7FB","regular",2)
    features(d,concept,[(54,1339,733,1422)],gold)
    style=editor.get("price_style","tag")
    box=(754,1239,1158,1437) if editor.get("price_position")!="opposite" else (53,1239,458,1437)
    d=ImageDraw.Draw(canvas)
    rrp(d,price,box,style,gold,ink(gold,p["ink"]))
    footer(d)
    return canvas


def _premium_gallery(concept,photo,product,price,editor,scene):
    """Variant B: ivory minimal catalogue ad with horizontal workshop photograph."""
    (stage,_,brand,headline,rrp,hero,fit,features,footer,ink,accent,palette)=_shared()
    p=palette["premium"][1];blue=accent(editor,p["primary"])
    paper="#FAFAF7"
    canvas=Image.new("RGBA",(1200,1500),paper)
    canvas.alpha_composite(stage(scene,(0,260,1200,788),.36,4.0,
                                editor.get("_scene_style")),(0,260))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,14),fill=blue)
    d.rectangle((0,786,1200,810),fill=blue)
    # Floating manufacturer product bridges the photo and clean white paper.
    hero(canvas,photo,product,(130,382,1080,1084),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    from ai_promo_renderer import _laser
    _laser(d,55,43,dark=True)
    fit(d,concept.get("focus_label","PRODUCT SPOTLIGHT"),(730,88,1150,141),
        (28,25,21),blue,"bold",1,"right")
    fit(d,"PART  "+str(product.get("part","")),(57,180,440,237),
        (38,33,29),blue,"bold",1)
    # Dedicated spacious typography: no navies or angled retail price block.
    headline(d,concept,(57,1079,1141,1231),
             (81,72,63,55,47),"#0C3454",3,editor)
    if editor.get("show_subline"):
        fit(d,concept.get("subline"),(59,1246,644,1303),
            (30,26,23),"#496C84","regular",2)
    features(d,concept,[(61,1354,651,1424)],blue,"#0B3958")
    style=editor.get("price_style","plaque")
    box=(695,1262,1147,1428) if editor.get("price_position")!="opposite" else (55,1262,507,1428)
    d=ImageDraw.Draw(canvas)
    rrp(d,price,box,style,blue,ink(blue,p["ink"]))
    footer(d,light=True)
    return canvas


def _premium_column(concept,photo,product,price,editor,scene):
    """Variant C: cream brochure, photo in left column, clean copy on right."""
    (stage,_,_,headline,rrp,hero,fit,features,footer,ink,accent,palette)=_shared()
    p=palette["premium"][2];blue=accent(editor,p["primary"])
    canvas=Image.new("RGBA",(1200,1500),"#F8FAF8")
    canvas.alpha_composite(stage(scene,(0,0,620,1460),.35,4.0,
                                editor.get("_scene_style")),(0,0))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((615,0,636,1500),fill=blue)
    d.rectangle((636,0,1200,1500),fill="#F8FAF8")
    d.rectangle((656,55,1160,70),fill=blue)
    hero(canvas,photo,product,(28,394,662,1190),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    from ai_promo_renderer import _laser
    _laser(d,685,104,dark=True)
    fit(d,"PART  "+str(product.get("part","")),(687,292,1129,345),
        (36,32,27),blue,"bold",1)
    headline(d,concept,(685,400,1160,793),
             (70,61,53,46,39),"#092F4D",5,editor)
    if editor.get("show_subline"):
        fit(d,concept.get("subline"),(688,845,1150,941),
            (29,26,22),"#54738B","regular",3)
    features(d,concept,[(686,1015,1154,1152)],blue,"#0A3554")
    # Uninterrupted price panel in the clean editorial column.
    style=editor.get("price_style","plaque")
    box=(686,1210,1163,1431) if editor.get("price_position")!="opposite" else (44,1210,519,1431)
    d=ImageDraw.Draw(canvas)
    rrp(d,price,box,style,blue,ink(blue,p["ink"]))
    footer(d,light=True)
    return canvas


def _trade_industrial(concept,photo,product,price,editor,scene):
    """Variant B: navy technical copy column and large real photo on right."""
    (stage,_,brand,headline,rrp,hero,fit,features,footer,ink,accent,palette)=_shared()
    p=palette["trade"][1];cyan=accent(editor,p["accent"])
    canvas=Image.new("RGBA",(1200,1500),"#051D34")
    canvas.alpha_composite(stage(scene,(510,205,1200,1220),.48,2.8,
                                editor.get("_scene_style")),(510,205))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.rectangle((0,0,1200,204),fill=(2,19,36,255))
    d.polygon([(0,205),(568,205),(524,1230),(0,1260)],fill=(2,24,43,249))
    d.polygon([(557,205),(575,205),(541,1230),(523,1230)],fill=cyan)
    d.rectangle((0,1222,1200,1500),fill=(2,21,39,250))
    d.rectangle((0,1212,1200,1235),fill=cyan)
    hero(canvas,photo,product,(445,350,1167,1225),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    brand(d,p["primary"],product.get("part",""),family="trade")
    fit(d,concept.get("focus_label","APPLICATION / SERVICE"),(52,298,523,359),
        (31,27,24),cyan,"bold",1)
    headline(d,concept,(54,410,510,835),
             (77,68,59,51,43), "#FFFFFF",5,editor)
    if editor.get("show_subline"):
        fit(d,concept.get("subline"),(57,851,510,954),
            (27,24,21),"#D0E4EF","regular",3)
    features(d,concept,[(57,997,505,1130)],cyan)
    style=editor.get("price_style","banner")
    box=(509,1252,1153,1431) if editor.get("price_position")!="opposite" else (53,1252,700,1431)
    d=ImageDraw.Draw(canvas)
    rrp(d,price,box,style,cyan,ink(cyan,p["ink"]))
    footer(d)
    return canvas


def _trade_diagonal(concept,photo,product,price,editor,scene):
    """Variant C: full-photo diagonal campaign, large white headline ribbon."""
    (stage,base,brand,headline,rrp,hero,fit,features,footer,ink,accent,palette)=_shared()
    p=palette["trade"][2];lime=accent(editor,p["accent"])
    canvas=base(scene,"trade",product,2,editor.get("_scene_style"))
    d=ImageDraw.Draw(canvas,"RGBA")
    d.polygon([(0,0),(1200,0),(1200,225),(0,276)],fill=(3,21,38,244))
    d.polygon([(0,270),(1200,217),(1200,244),(0,298)],fill=lime)
    d.polygon([(0,1062),(1200,951),(1200,1500),(0,1500)],fill=(3,21,38,246))
    d.polygon([(0,1055),(1200,942),(1200,967),(0,1079)],fill=lime)
    hero(canvas,photo,product,(132,268,1166,1104),editor)
    d=ImageDraw.Draw(canvas,"RGBA")
    brand(d,p["primary"],product.get("part",""),family="trade")
    fit(d,concept.get("focus_label","AUTOMOTIVE WORKSHOP"),(706,94,1144,153),
        (30,27,23),lime,"bold",1,"right")
    # Reverses the usual dark text block: white diagonal headline card.
    d.polygon([(0,1063),(1072,971),(1136,1140),(0,1249)],fill=(248,251,252,248))
    headline(d,concept,(65,1067,1021,1191),
             (79,70,61,54,46),"#092C4B",2,editor)
    if editor.get("show_subline"):
        fit(d,concept.get("subline"),(62,1281,741,1338),
            (30,26,23),"#E2ECF5","regular",2)
    features(d,concept,[(65,1370,740,1439)],lime)
    style=editor.get("price_style","tag")
    box=(746,1234,1153,1431) if editor.get("price_position")!="opposite" else (55,1234,461,1431)
    d=ImageDraw.Draw(canvas)
    rrp(d,price,box,style,lime,ink(lime,p["ink"]))
    footer(d)
    return canvas
