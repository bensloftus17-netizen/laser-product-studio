"""Optional visual-art director critique of finished, *actual* poster pixels.

The verdict is advisory when Gemini is unavailable, but explicit visual faults
block an AI campaign unless a local variant can be re-rendered and rechecked.
This critic sees images, not simply a layout description. No OCR is required,
no picture is generated or edited by the model and no arbitrary model claims
reach the end-user.
"""
from __future__ import annotations

import base64
import io
import os
import re

from PIL import Image

from campaign_distinctness import POSTERS

ISSUE_CODES=(
    "white_box","white_halo","blurry_product","cutoff_text",
    "unreadable_copy","tiny_product","poor_contrast","clutter",
    "duplicate_layout","unrelated_background",
)
BLOCKING=set(ISSUE_CODES)


def _small_jpeg(blob):
    picture=Image.open(io.BytesIO(blob)).convert("RGB")
    # 420 x 525 previews make small but legible poster copy look clipped.
    # Review enough real pixels to distinguish cropped lettering from
    # down-sampling artefacts, without sending the native 1200 x 1500 files.
    picture.thumbnail((760,950),Image.Resampling.LANCZOS)
    data=io.BytesIO()
    picture.save(data,"JPEG",quality=80,optimize=True)
    return base64.b64encode(data.getvalue()).decode("ascii")


def review_finished_artworks(images):
    """Review a batch in one bounded multimodal call, or report not reviewed.

    Prompts and filenames are trusted server text, not sourced from the model.
    Vision-based aesthetic review is imperfect and is never represented as an
    objective guarantee of professional design.
    """
    key=os.environ.get("GEMINI_API_KEY","").strip()
    model=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite").strip()
    if not key or not re.fullmatch(r"[a-zA-Z0-9._-]{3,80}",model):
        return {"method":"automated-geometry-only","reviewed":False,
                "issues":{},"warning":"AI visual critic unavailable; geometry and asset QA still enforced"}
    from ai_concepts import _gemini_json
    parts=[{"text":(
        "You are an independent senior UK automotive advertising art director. "
        "You will see three actual rendered Laser Tools poster images in order: "
        "poster_technical, poster_price, poster_smart. "
        "Flag only concrete visible design defects: obvious white photo rectangles, "
        "white edge halos around tools, blurry/pixelated tools, cut-off text, "
        "unreadable text, tiny hero products, extremely weak contrast, "
        "cluttered hierarchy, repetitive visual arrangement or totally unrelated "
        "real photographic context. A product may genuinely contain white or "
        "silver parts; do not reject legitimate light-coloured components. "
        "Do not verify technical facts or try to redraw any tool. "
        "Return JSON object with 'issues' mapping each of those exact poster "
        "IDs to an array of applicable issue code strings from: "
        + ", ".join(ISSUE_CODES) + ". "
        "Use empty lists for good posters. Be conservative: only flag defects "
        "actually visible. No prose, no instructions, no URLs."
    )}]
    for role in POSTERS:
        parts.append({"text":role})
        parts.append({"inlineData":{
            "mimeType":"image/jpeg","data":_small_jpeg(images[role])}})
    payload={
        "contents":[{"role":"user","parts":parts}],
        "generationConfig":{"responseMimeType":"application/json",
                            "temperature":0.1,"maxOutputTokens":650},
    }
    try:
        raw=_gemini_json(payload,key,model)
        submitted=raw.get("issues",{}) if isinstance(raw,dict) else {}
        if not isinstance(submitted,dict):
            raise ValueError("Unusable critic response")
        findings={}
        for role in POSTERS:
            codes=submitted.get(role,[])
            if not isinstance(codes,list):
                raise ValueError("Incorrect critic issue list")
            findings[role]=[code for code in codes if isinstance(code,str)
                            and code in BLOCKING][:6]
        return {"method":"gemini-visual-critic","reviewed":True,
                "issues":findings,"warning":None}
    except (RuntimeError,ValueError,KeyError,TypeError,OSError) as exc:
        return {"method":"automated-geometry-only","reviewed":False,
                "issues":{},"warning":"AI visual critic could not complete: "+
                                     type(exc).__name__+
                                     ". Image geometry and source QA were still checked."}


def reconcile_with_measured_geometry(visual, quality_reports):
    """Do not let a fallible image model overrule objective font/hero metrics.

    Text clipping is checked at render time against the actual glyph bbox,
    safe areas and collisions. Product prominence is checked with the
    placed, genuine cutout's actual bounds. A model sometimes confuses a
    narrow tool with a tiny one, or misreads dense legal/footer text as
    clipping. Resolve ONLY those two measurable claims, and ONLY when the
    corresponding deterministic inspection is present and passing.

    White-box, white-halo, blur, clutter, unrelated backgrounds, duplicate
    compositions and other visual observations are NEVER silently cleared.
    """
    if not visual.get("reviewed"):
        return visual
    issues=visual.get("issues")
    if not isinstance(issues,dict):
        return visual
    preserved={}
    disputed={}
    for role in POSTERS:
        reported=issues.get(role) or []
        report=(quality_reports or {}).get(role) or {}
        remaining=[]
        contradicted=[]
        for issue in reported:
            if (issue=="cutoff_text"
                    and report.get("passed") is True
                    and report.get("text_bounds_verified") is True):
                contradicted.append(issue)
            elif (issue=="tiny_product"
                  and report.get("passed") is True
                  and report.get("product_bounds_verified") is True
                  and isinstance(report.get("product_visible_fraction"),(float,int))
                  and report["product_visible_fraction"] >= .08):
                contradicted.append(issue)
            else:
                remaining.append(issue)
        preserved[role]=remaining
        if contradicted:
            disputed[role]=contradicted
    outcome=dict(visual)
    outcome["issues"]=preserved
    outcome["geometry_disagreements"]=disputed
    if disputed:
        message=("Visual model disagreed with measurable font/product placement "
                 "checks; those two issue types were resolved by independently "
                 "recorded geometry. All other quality gates remain active. "
                 "Review final artwork before publishing.")
        outcome["warning"]="; ".join(filter(None,(visual.get("warning"),message)))
    return outcome
