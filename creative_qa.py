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
        "real photographic context. A shared LASER header, the same genuine "
        "product photo, and consistent brand colours do not by themselves make "
        "two deliberately different technical and promotional layouts duplicates. "
        "Only flag duplicate_layout when two actual whole-poster compositions "
        "have almost identical placements and visual hierarchy. "
        "A product may genuinely contain white or "
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


def _independent_reference_distinctness(role, quality_reports, distinctness):
    """Check objective evidence before disputing a *fixed template* duplicate.

    Only two approved reference layouts qualify. This must not hide duplicates
    in flexible AI artwork. All of the role's pairwise comparisons must have
    independently strong colour/structure differences, not merely a coloured
    line or a changed LASER logo. The standard campaign duplicate gate remains.
    """
    references={
        "poster_technical":"laser-technical-reference",
        "poster_price":"laser-workshop-promo-reference",
    }
    required=references.get(role)
    report=(quality_reports or {}).get(role) or {}
    if not required or report.get("render_engine")!=required:
        return False
    if report.get("passed") is not True:
        return False
    if not isinstance(distinctness,dict) or distinctness.get("passed") is not True:
        return False
    comparisons=distinctness.get("pairs")
    if not isinstance(comparisons,list):
        return False
    relevant=[p for p in comparisons if isinstance(p,dict) and
              role in (p.get("left"),p.get("right"))]
    if len(relevant)!=2:
        return False
    for pair in relevant:
        diff=pair.get("difference")
        hamming=pair.get("perceptual_hash_distance")
        if not isinstance(diff,(float,int)) or not isinstance(hamming,int):
            return False
        # A slight palette/accent change is not sufficient evidence. Require
        # a substantial pixel difference AND independent perceptual contrast,
        # or very large pixel differences across the whole composition.
        if not (diff>=.09 and (hamming>=8 or diff>=.18)):
            return False
    return True


def reconcile_with_measured_geometry(visual, quality_reports, distinctness=None):
    """Reconcile subjective model defects with independently measured output.

    Existing measured glyph and product bounds remain authoritative. V68 also
    checks the *finished pixels* of a fixed technical/workshop template before
    accepting a model's duplicate_layout finding. Other visual issues always
    remain blocking. Weak/absent pairwise evidence never clears duplication.
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
            elif (issue=="duplicate_layout"
                  and _independent_reference_distinctness(
                      role,quality_reports,distinctness)):
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
        message=("Visual model findings disagreed with independently checked "
                 "text, product bounds or strong pairwise pixel differences "
                 "of locked reference templates. Disagreements are recorded "
                 "for human review; source, layout, image and duplication "
                 "quality gates remain active. Review before publishing.")
        outcome["warning"]="; ".join(filter(None,(visual.get("warning"),message)))
    return outcome
