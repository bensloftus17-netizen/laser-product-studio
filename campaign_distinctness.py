"""Independent checks that three campaign artworks really look different."""
from __future__ import annotations
import io
from itertools import combinations
from PIL import Image, ImageChops, ImageStat

POSTERS=("poster_technical","poster_price","poster_smart")


def _small(blob):
    image=Image.open(io.BytesIO(blob)).convert("RGB")
    return image.resize((96,120),Image.Resampling.BILINEAR)


def _difference_hash(blob):
    """64-bit difference hash from completed poster pixels (not model labels)."""
    grey=Image.open(io.BytesIO(blob)).convert("L").resize(
        (9,8),Image.Resampling.LANCZOS)
    samples=list(grey.getdata())
    bits=0
    for row in range(8):
        for col in range(8):
            bits=(bits<<1)|(1 if samples[row*9+col]>samples[row*9+col+1] else 0)
    return bits


def check_distinctness(images,concepts):
    issues=[]
    comparisons=[]
    if len(concepts)!=3:
        return {"passed":False,"issues":["Expected three campaign directions"],
                "pairs":[]}
    # Check the model's actual authored geometry, marketing proof, visual
    # families, not merely named styles or one changed background stripe.
    from creative_families import copy_diversity,layout_diversity
    if all(c.get("creative_direction") for c in concepts):
        issues.extend(copy_diversity(concepts))
    briefs=[c.get("creative_canvas") for c in concepts]
    if all(isinstance(b,dict) and b.get("creative_family") for b in briefs):
        issues.extend(layout_diversity(briefs))
    if all(isinstance(b,dict) for b in briefs):
        from creative_director import distinct_briefs
        if not distinct_briefs(briefs):
            issues.append("AI supplied repeated creative compositions")
    for left,right in combinations(POSTERS,2):
        if left not in images or right not in images:
            issues.append("Missing poster for visual distinctness check")
            continue
        try:
            a,b=_small(images[left]),_small(images[right])
            delta=ImageChops.difference(a,b)
            difference=round(sum(ImageStat.Stat(delta).mean)/3/255,4)
            hash_distance=(_difference_hash(images[left]) ^
                           _difference_hash(images[right])).bit_count()
        except (ValueError,OSError):
            issues.append("Unreadable campaign artwork during distinctness check")
            continue
        comparisons.append({"left":left,"right":right,"difference":difference,
                            "perceptual_hash_distance":hash_distance})
        # A minor accent stripe may raise raw RGB difference while both ads
        # still have the same visual structure. Require enough perceptual
        # difference too, but never reject visibly different originals merely
        # because both retain the same genuine manufacturer tool.
        if difference<.028 or (difference<.075 and hash_distance<=5):
            issues.append(left+" and "+right+" look like duplicate artworks")
    return {"passed":not issues,"issues":issues,"pairs":comparisons}
