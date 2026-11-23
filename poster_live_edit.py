"""Edit one completed poster without regenerating three AI campaigns.

Only official product-title excerpts and manufacturer-verified feature IDs
are accepted. Price, VAT, applications and source product photo are locked.
The campaign's ZIP and PDF are updated to match the edited PNG.
"""
from __future__ import annotations

import io
import json
import re
from copy import deepcopy
from zipfile import ZipFile, ZIP_DEFLATED

from campaign_art_quality import choose_best
from campaign_role_posters import technical_poster,smart_poster
from product_evidence_ranker import verified_candidates
from poster_quality import capture

ASSETS={"poster_technical":(0,"technical_application"),
        "poster_price":(1,"price_promo"),
        "poster_smart":(2,"product_selected")}


def verified_title_excerpt(official_title,headline):
    """Permits shortening the exact manufacturer title, not creating claims."""
    official=" ".join(str(official_title or "").split())
    proposed=" ".join(str(headline or "").split())
    if not proposed or len(proposed)>120:
        raise ValueError("Use a short, non-empty excerpt of the official product name (up to 120 characters).")
    found=re.search(r"(?<!\w)"+re.escape(proposed)+r"(?!\w)",official,re.I)
    if not found:
        raise ValueError("The headline must be copied from the verified manufacturer product name. Use the Copy Editor for draft marketing wording.")
    return found.group(0)


def edit_campaign_poster(bundle,asset_id,body):
    """Replace exactly one verified poster and its ZIP entry atomically."""
    if asset_id not in ASSETS:
        raise ValueError("Only the three campaign posters can be edited.")
    if not isinstance(body,dict):
        raise ValueError("Invalid poster edit.")
    source=bundle.get("editor_context")
    if not source:
        raise ValueError("This campaign cannot be edited. Generate a new campaign.")
    product=source["product"]
    # Preserve the genuine manufacturer angle chosen for this poster, rather
    # than quietly switching back to the primary packshot after an edit.
    photo=(source.get("role_photos") or {}).get(asset_id) or source["genuine_photo"]
    distributor=source["distributor"]
    idx,role=ASSETS[asset_id]
    current=source["concepts"][idx]
    headline=verified_title_excerpt(
        product.get("title"),body.get("headline",current.get("headline")))
    features=verified_candidates(product)[:24]
    feature_index=body.get("feature_index")
    if type(feature_index) is not int or feature_index<(-1) or feature_index>=len(features):
        raise ValueError("Choose a feature from the official manufacturer record.")
    fact=features[feature_index] if feature_index>=0 else ""
    layout=body.get("layout_variant")
    if type(layout) is not int or layout not in (0,1,2):
        raise ValueError("Choose one of the three validated poster compositions.")
    updated=deepcopy(current)
    updated["headline"]=headline
    updated["selling_point"]=fact
    updated["subline"]=fact or headline
    updated["variant"]=layout
    updated["features"]=(
        [fact]+[item for item in features if item!=fact][:2]
        if fact and role=="technical_application" else
        [fact] if fact and role=="product_selected" else []
    )
    scene=source["scenes"][idx]
    if updated.get("creative_canvas"):
        # Preserve an AI-authored composition when a single poster is edited.
        # Switching to the old templates would silently discard the creative
        # director's actual design decisions.
        from flexible_canvas import render_creative_canvas
        def render(variant):
            with capture() as geometry:
                png=render_creative_canvas(
                    product,photo,updated,scene,distributor,variant=variant)
            return png,{
                "truncated":any(t["truncated"] for t in geometry.texts),
                "out_of_bounds":any(
                    t["box"][0]<0 or t["box"][1]<0 or
                    t["box"][2]>1200 or t["box"][3]>1500
                    for t in geometry.texts),
                "missing_headline":not any(
                    t.get("role")=="headline" for t in geometry.texts),
                "product_visible_fraction":max(
                    (p.get("visible_fraction",0) for p in geometry.products),
                    default=None),
            }
    elif role=="price_promo":
        from ai_promo_renderer import render_promo
        art=updated.get("visual_plan") or {}
        controls=art.get("art_direction") or {}
        def render(variant):
            detail={}
            png=render_promo(updated,photo,product,distributor,editor={
                "background":"context","_scene_bytes":scene,
                "_scene_style":{"crop":(.45,.52),"darkness":.29,
                                "blur":2.2,"colour":.84},
                "show_subline":False,
                "price_style":art.get("price_style","panel"),
                "accent":art.get("accent","#F6D343"),
                "product_scale":controls.get("product_scale",105),
                "product_x":controls.get("product_x",0),
                "product_y":controls.get("product_y",0),
                "headline_size":controls.get("headline_size","normal"),
                "_quality_report":detail})
            return png,{"truncated":False,"out_of_bounds":False,
                        "overlaps":bool(detail.get("issues"))}
    else:
        renderer=technical_poster if idx==0 else smart_poster
        def render(variant):
            with capture() as geometry:
                png=renderer(product,photo,updated,scene,distributor)
            return png,{
                "truncated":any(t["truncated"] for t in geometry.texts),
                "out_of_bounds":any(
                    t["box"][0]<0 or t["box"][1]<0 or
                    t["box"][2]>1200 or t["box"][3]>1500
                    for t in geometry.texts),
                "missing_headline":not any(
                    t.get("role")=="headline" for t in geometry.texts),
                "product_visible_fraction":max((
                    p.get("visible_fraction",0) for p in geometry.products),
                    default=None),
            }

    new_image,quality=choose_best(render,role,photo,variants=(layout,))
    # Work on new objects and only update the in-memory pack after rendering
    # succeeds and the ZIP/PDF are both valid.
    manifest=deepcopy(bundle["manifest"])
    angle=manifest["angles"][idx]
    angle["headline"]=headline
    angle["selling_point"]=fact
    angle["layout_variant"]=layout
    manifest["artwork_quality"][asset_id]=quality
    manifest["poster_revision"]=int(manifest.get("poster_revision",0))+1
    edits=manifest.setdefault("poster_edits",[])
    edits.append({"asset_id":asset_id,"headline_source":"manufacturer title excerpt",
                  "feature_source":"manufacturer feature" if fact else "no feature selected",
                  "review_required":True})
    if len(edits)>15:del edits[:-15]
    source_concepts=list(source["concepts"])
    source_concepts[idx]=updated
    from campaign_hub import _summary_pdf,FOLDERS
    summary=_summary_pdf(product,source_concepts,manifest)
    new_data={
        FOLDERS[asset_id]:new_image,
        "Campaign_Manifest.json":json.dumps(manifest,indent=2,ensure_ascii=False),
        "05_Product_Info/Campaign_Summary.pdf":summary,
    }
    archive=io.BytesIO()
    with ZipFile(io.BytesIO(bundle["archive"]),"r") as old, \
         ZipFile(archive,"w",compression=ZIP_DEFLATED) as new:
        for name in old.namelist():
            new.writestr(name,new_data.pop(name,old.read(name)))
        for name,data in new_data.items():
            new.writestr(name,data)
    # Commit only once every artifact is ready.
    bundle["images"][asset_id]=new_image
    bundle["manifest"]=manifest
    bundle["archive"]=archive.getvalue()
    source["concepts"]=source_concepts
    if hasattr(bundle,"save_editor"):
        # Source-backed variations must persist when the pack lives on disk.
        # Subsequent edits use the current verified concepts, not old defaults.
        bundle.save_editor(source)
    return {"manifest":manifest,"asset_id":asset_id,
            "revision":manifest["poster_revision"],"quality":quality}
