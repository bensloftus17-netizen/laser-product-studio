"""Safety-first aesthetic QA for the one-click Laser campaign builder.

No OCR, no hallucinated product pixels and no generative edits to a real tool.
QA is a measurable ranking/rejection stage: aspect ratio, whitespace, photo
integrity, legibility/space, duplicates and source-backed text. It cannot
measure professional taste, so results remain marked DRAFT/REVIEW REQUIRED.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from PIL import Image, ImageChops, ImageOps, ImageStat

from ai_photo_effects import manufacturer_cutout
from poster_quality import white_paper_warning

EXPECTED=(1200,1500)
_ROLES={"technical_application","price_promo","product_selected"}


@lru_cache(maxsize=12)
def inspected_product(blob:bytes):
    """Use the existing manufacturer extraction, *never* redraw the tool.

    Border-white parts cannot be confidently distinguished from the source
    photo background in every case. In that case retain the genuine source,
    explicitly flag the risk and use a bounded non-white photographic frame.
    """
    cut,isolated=manufacturer_cutout(blob)
    original=ImageOps.exif_transpose(Image.open(io.BytesIO(blob)))
    original.load()
    if original.width*original.height>6_000_000:
        original.thumbnail((1800,1800),Image.Resampling.LANCZOS)
    if isolated:
        alpha=cut.getchannel("A")
        bbox=alpha.getbbox()
        if bbox:cut=cut.crop(bbox)
        coverage=round(ImageStat.Stat(alpha).mean[0]/255,4)
    else:
        cut=original.convert("RGBA")
        coverage=1.0
    issue=white_paper_warning(blob)
    return {
        "isolated":bool(isolated),
        "rgba":cut,
        "foreground_coverage":coverage,
        "source_warning":issue,
        "needs_manual_cutout":bool(not isolated and issue),
    }


def _is_nearwhite(pixel):
    r,g,b=pixel[:3]
    return min(r,g,b)>=242 and max(r,g,b)-min(r,g,b)<18


def visual_review(data:bytes,role:str,*,source_info=None,text_status=None):
    """Small-pixel audit; score creative variants and reject obvious mistakes.

    The white-area check is deliberately *not* an exclusion of naturally
    silver/white components; it inspects the composed canvas as a whole.
    """
    reasons=[]
    warnings=[]
    if role not in _ROLES:reasons.append("Unexpected poster role")
    try:
        image=Image.open(io.BytesIO(data))
        image.load()
    except (OSError,ValueError):
        return {"passed":False,"score":0,"issues":["Unreadable image"],
                "warnings":[],"white_fraction":1.0}
    if image.size!=EXPECTED:reasons.append("Wrong poster dimensions")
    sample=image.convert("RGB").resize((100,125),Image.Resampling.BILINEAR)
    pixels=list(sample.getdata())
    white_fraction=sum(1 for p in pixels if _is_nearwhite(p))/max(1,len(pixels))
    if white_fraction>.43:
        reasons.append("Oversized white or near-white canvas area")
    elif white_fraction>.31:
        warnings.append("High white-area ratio, review product compositing")
    stats=ImageStat.Stat(sample)
    colour_range=sum(stats.stddev)/3
    if colour_range<18:reasons.append("Artwork lacks visual contrast")
    elif colour_range<31:warnings.append("Low visual contrast")
    if source_info:
        if source_info.get("needs_manual_cutout"):
            reasons.append("White-background product photo cannot be isolated safely; provide a clean manufacturer cutout")
        elif source_info.get("source_warning"):
            warnings.append(source_info["source_warning"])
    status=text_status or {}
    if status.get("truncated"):
        reasons.append("Text does not fit its design area")
    if status.get("out_of_bounds"):
        reasons.append("Text is outside safe margins")
    if status.get("overlaps"):
        reasons.append("Headline or selling point overlaps")
    if (status.get("product_visible_fraction") is not None and
            status["product_visible_fraction"]<.028):
        reasons.append("Product is too small or visually insignificant")
    if status.get("missing_headline"):
        reasons.append("Promotional headline is missing")
    # High score rewards breathing room and photographic contrast without
    # claiming a human/AI style judgement is mathematically verifiable.
    score=100-int(max(0,white_fraction-.11)*88)
    score-=max(0,round((37-colour_range)*.6))
    score-=12*len(reasons)+4*len(warnings)
    return {
        "passed":not reasons,
        "score":max(0,min(100,score)),
        "issues":list(dict.fromkeys(reasons)),
        "warnings":list(dict.fromkeys(warnings)),
        "white_fraction":round(white_fraction,4),
        "contrast":round(colour_range,2),
        "criteria":["dimensions","large_white_areas","scene_contrast",
                    "text_safe_area","headline_presence","product_hero_area",
                    "manufacturer_cutout_confidence"],
    }


def choose_best(render,role,source_blob,variants=(0,1,2),
                *,preferred_variant=None,scene_relevance=None):
    """Render three different safe candidate compositions and select best.

    Best-of-N is about real layout/photography treatment; each candidate
    keeps the original manufacturer product. We never accept an invalid
    file merely because it scores relatively highly among other bad ones.
    """
    info=inspected_product(source_blob)
    reports=[]
    winning=None
    for variant in variants:
        try:
            payload,geometry=render(variant)
            audit=visual_review(payload,role,source_info=info,text_status=geometry)
            # Prefer Gemini's bounded art direction when scores are close,
            # never to override clipping, cutout or other failed QA.
            if (audit["passed"] and type(preferred_variant) is int
                    and variant==preferred_variant):
                audit["score"]=min(100,audit["score"]+3)
            if scene_relevance and scene_relevance.get("warning"):
                audit["warnings"].append(scene_relevance["warning"])
        except Exception as exc:
            audit={"passed":False,"score":0,"issues":["Render failed: "+type(exc).__name__],
                   "warnings":[]}
            payload=None
        audit["variation"]=variant
        reports.append(audit)
        if payload and audit["passed"] and (
            winning is None or audit["score"]>winning[1]["score"]
        ):
            winning=(payload,audit)
    if winning is None:
        failed=list(dict.fromkeys(
            issue for audit in reports for issue in audit.get("issues",[])))
        raise ValueError("Campaign artwork rejected by quality checks: "+
                         "; ".join(failed[:4]))
    result=dict(winning[1])
    result["candidates_checked"]=len(reports)
    result["rejected_candidates"]=sum(not x["passed"] for x in reports)
    result["alternatives"]= [
        {"variation":x["variation"],"score":x["score"],"passed":x["passed"]}
        for x in reports
    ]
    return winning[0],result


def campaign_consistency(concepts):
    """Check marketing-role diversity and verified-source feature repetition."""
    seen_roles=[x.get("campaign_role") for x in concepts]
    if seen_roles!=["technical_application","price_promo","product_selected"]:
        return ["Campaign must contain technical, price and selected third angle"]
    families=[x.get("family") for x in concepts]
    issues=[]
    if len(set(families))!=3:
        issues.append("Campaign has repeating composition families")
    smart=concepts[2].get("third_angle")
    if smart in ("price_promo","technical_application"):
        issues.append("The third poster repeats another purpose")
    proofs=[re.sub(r"\s+"," ",str(x.get("selling_point") or "")).strip().casefold()
            for x in concepts]
    if len([x for x in proofs if x])>1 and len(set(x for x in proofs if x))==1:
        issues.append("All three posters repeat the same selling point")
    return issues



def photo_relevance(product,selected_category,reference):
    """Give users a traceable relevance decision, not a false photo claim.

    References can only come from the curated stock library or official
    manufacturer application pictures. No arbitrary Gemini URL is trusted.
    Unknown or mismatched stock contexts are rejected upstream, because an
    unrelated laboratory/office is worse than a clean branded background.
    """
    source=str((reference or {}).get("source") or "")
    actual=(reference or {}).get("category")
    if source=="No external photograph used":
        return {"score":0,"supported":True,"warning":"No suitable real workshop photograph; branded background used"}
    if source=="Official manufacturer application photo":
        return {"score":100,"supported":True,"warning":None}
    if source=="Pexels free commercial-use photo" and actual==selected_category:
        return {"score":80,"supported":True,"warning":None}
    return {"score":0,"supported":False,
            "warning":"Photo context did not match this product category"}
