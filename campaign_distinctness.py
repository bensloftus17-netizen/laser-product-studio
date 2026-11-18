"""Independent checks that three campaign artworks really look different."""
from __future__ import annotations
import io
from itertools import combinations
from PIL import Image, ImageChops, ImageStat

POSTERS=("poster_technical","poster_price","poster_smart")


def _small(blob):
    image=Image.open(io.BytesIO(blob)).convert("RGB")
    return image.resize((96,120),Image.Resampling.BILINEAR)


def check_distinctness(images,concepts):
    issues=[]
    comparisons=[]
    if len(concepts)!=3:
        return {"passed":False,"issues":["Expected three campaign directions"],
                "pairs":[]}
    # The model's different layouts must have different actual headline/product
    # geometry, not merely renamed styles or a changed background colour.
    briefs=[c.get("creative_canvas") for c in concepts]
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
        except (ValueError,OSError):
            issues.append("Unreadable campaign artwork during distinctness check")
            continue
        comparisons.append({"left":left,"right":right,"difference":difference})
        if difference<.028:
            issues.append(left+" and "+right+" look like duplicate artworks")
    return {"passed":not issues,"issues":issues,"pairs":comparisons}
