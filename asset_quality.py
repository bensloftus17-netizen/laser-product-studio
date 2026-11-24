"""Conservative source-image preflight for freeform AI-designed posters.

Never upscale a fuzzy thumbnail or paint missing edges. Reject unsafe white
packshots instead of compositing their white rectangle onto artwork.
"""
from __future__ import annotations

import io

from PIL import Image, ImageFilter, ImageOps, ImageStat
from campaign_art_quality import inspected_product


def _foreground_reaches_frame(image):
    """Flag a continuous tool edge on studio packshots or transparent cutouts."""
    w,h=image.size
    corners=[image.getpixel(point) for point in ((0,0),(w-1,0),(0,h-1),(w-1,h-1))]
    transparent=any(pixel[3]<32 for pixel in corners)
    if not transparent and not all(min(pixel[:3])>=240 for pixel in corners):
        return False
    for axis,length,edges in ((0,w,(0,h-1)),(1,h,(0,w-1))):
        for edge in edges:
            run=0
            for offset in range(length):
                pixel=image.getpixel((offset,edge) if axis==0 else (edge,offset))
                foreground=pixel[3]>=224 if transparent else min(pixel[:3])<215
                run=run+1 if foreground else 0
                if run>=max(6,round(length*.02)):
                    return True
    return False


def inspect_asset(blob):
    issues=[]
    warnings=[]
    try:
        with Image.open(io.BytesIO(blob)) as raw:
            w,h=raw.size
            # QA only inspects structure at 420px. Never decode 30MP into
            # several full-resolution RGB images to calculate an edge score.
            if raw.format in ("JPEG", "MPO"):
                raw.draft("RGB", (900, 900))
            raw.thumbnail((900,900),Image.Resampling.LANCZOS)
            image=ImageOps.exif_transpose(raw).convert("RGBA")
            image.load()
    except (ValueError, OSError, TypeError):
        return {"passed":False,"issues":["Unreadable manufacturer product photo"],
                "warnings":[],"size":[0,0],"edge_strength":0}
    # Materially smaller photos lose tool detail on a 1200x1500 poster.
    if min(w,h)<400 or w*h<210_000:
        issues.append("Source product image is too small for professional poster artwork")
    elif min(w,h)<650:
        warnings.append("Source photo is below ideal print resolution; review at full size")
    possible_source_crop=_foreground_reaches_frame(image)
    if possible_source_crop:
        warnings.append("A component reaches the manufacturer image edge; check for source cropping")
    thumbnail=image
    thumbnail.thumbnail((420,420),Image.Resampling.LANCZOS)
    edges=thumbnail.convert("L").filter(ImageFilter.FIND_EDGES)
    strength=round(ImageStat.Stat(edges).stddev[0],2)
    if strength<11:
        issues.append("Source product photo has insufficient visible edge detail")
    info=inspected_product(blob)
    if info.get("needs_manual_cutout"):
        issues.append("Cannot safely remove source white background; request a clean original")
    elif not info.get("isolated"):
        # Actual workshop/application images can legitimately be rectangular;
        # they should be used as contextual backgrounds, NOT fake cutout heroes.
        issues.append("No reliable isolated product photo for freeform hero artwork")
    else:
        # Never mutate the cached source cutout: thumbnail() shrank its
        # pixels for every later poster. Inspect a temporary copy instead,
        # and stream pixels rather than retaining huge Python lists/tuples.
        cut=info["rgba"].copy()
        # A halo is particularly visible when nearly all semi-transparent
        # edge pixels are paper-white. Inspect only feathered alpha boundaries,
        # avoiding opaque white metal and plastic parts.
        cut.thumbnail((600,600),Image.Resampling.LANCZOS)
        fringe_count=0
        white_fringe_count=0
        for pixel in cut.getdata():
            if 20<=pixel[3]<=210:
                fringe_count+=1
                if min(pixel[:3])>244 and max(pixel[:3])-min(pixel[:3])<12:
                    white_fringe_count+=1
        cut.close()
        if fringe_count>=40:
            paper=white_fringe_count/fringe_count
            if paper>.65:
                issues.append("Product cutout has visible white fringe around its edges")
            elif paper>.38:
                warnings.append("Cutout may have pale fringe; review around the tool")
    return {
        "passed":not issues,
        "issues":issues,
        "warnings":warnings,
        "size":[w,h],
        "edge_strength":strength,
        "isolated":bool(info.get("isolated")),
        "possible_source_crop":possible_source_crop,
        "manufacturer_pixels_untouched":True,
    }


def require_good_asset(blob):
    result=inspect_asset(blob)
    if not result["passed"]:
        raise ValueError("Product image rejected before poster generation: "+
                         "; ".join(result["issues"]))
    return result



def manufacturer_image_rank(blob):
    """Rank only genuine manufacturer photos already checked for the exact SKU.

    Returns score and public-safe diagnostics. A rejected photo cannot outrank
    a passing one merely by being large or colourful. No AI image editing.
    """
    report=inspect_asset(blob)
    w,h=report["size"]
    score=(100 if report["passed"] else 0)
    score+=min(35,min(w,h)/30)
    score+=min(18,report["edge_strength"]/2)
    score-=12*len(report["warnings"])
    return round(score,2),report
