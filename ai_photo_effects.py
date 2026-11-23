"""Faithful manufacturer packshot cut-outs, including enclosed white-background gaps.

No AI-drawn/reconstructed product imagery, no model calls and no new paid API.
Near-white *edge-connected* photo background is removed, while internal white
product components are preserved. Ambiguous photographs fall back to a frame.
"""
from __future__ import annotations

import hashlib
import io
import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

RESAMPLE = Image.Resampling.LANCZOS
DEFAULT_SIZE = 1250


def _clear_enclosed_paper(rgba: Image.Image) -> Image.Image:
    """Final rescue pass for large paper-white gaps *inside* dark metal tools.

    Edge flood can leave a white parallelogram between scissor arms. Segment
    only large elongated, bright-neutral components, ignoring small white logo
    lettering and rounded white reservoirs. This works even with PNG alpha.
    Never create product pixels; only reduce alpha of confidence-matched paper.
    """
    rgba=rgba.convert("RGBA")
    rgb=rgba.convert("RGB")
    w,h=rgba.size
    if min(w,h)<80:
        return rgba
    channels=rgb.split()
    lo=ImageChops.darker(ImageChops.darker(channels[0],channels[1]),channels[2])
    hi=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
    pale=ImageChops.multiply(
        lo.point(lambda v:255 if v>=219 else 0),
        ImageChops.subtract(hi,lo).point(lambda v:255 if v<=43 else 0))
    alpha=rgba.getchannel("A")
    pale=ImageChops.multiply(pale,alpha.point(lambda v:255 if v>210 else 0))
    # Remove tiny disconnected logo glyphs/noise from component search, while
    # retaining long broad holes through separators, pullers and ratchet sets.
    core=pale.filter(ImageFilter.MinFilter(3))
    eligible=Image.new("L",(w,h),0)
    min_area=max(180,int(w*h*.0035))
    max_area=int(w*h*.25)
    for _ in range(80):
        raw=core.tobytes()
        index=raw.find(b"\xff")
        if index<0:break
        seed=(index%w,index//w)
        ImageDraw.floodfill(core,seed,128,thresh=0)
        component_core=core.point(lambda v:255 if v==128 else 0)
        core.paste(0,mask=component_core)
        bb=component_core.getbbox()
        if not bb:continue
        bw,bh=bb[2]-bb[0],bb[3]-bb[1]
        ratio=max(bw,bh)/max(1,min(bw,bh))
        # Real 8899 is an enclosed WHITE PARALLELOGRAM. Its bounding box
        # is nearly square (aspect ~1.29) despite the diagonal metal jaws.
        # Permit such an opening only if it is a sizeable, uniform area.
        large_paper=(bw*bh>w*h*.06 and ratio>1.12)
        if bw*bh<min_area or (ratio<1.4 and not large_paper):
            continue
        if bw < w*.09 or bh < h*.025:
            continue
        # Grow to include anti-aliased grey/off-white pixels at the boundary.
        work=pale.copy()
        ImageDraw.floodfill(work,seed,128,thresh=0)
        region=work.point(lambda v:255 if v==128 else 0)
        area=region.histogram()[255]
        if not min_area<=area<=max_area:
            continue
        bbox=region.getbbox()
        if not bbox:continue
        # Must be enclosed, not ordinary white photo background.
        if bbox[0]<=2 or bbox[1]<=2 or bbox[2]>=w-2 or bbox[3]>=h-2:
            continue
        from PIL import ImageStat
        statistics=ImageStat.Stat(rgb,mask=region)
        means,spread=statistics.mean,statistics.stddev
        if large_paper:
            # The real 8899 white opening is almost pure neutral paper
            # (RGB ~254, std <4); an actual white moulded component has
            # shading, texture and substantially higher local variation.
            if area<w*h*.02 or min(means)<248 or max(spread)>9:
                continue
        elif min(means)<237 or max(means)-min(means)>23 or max(spread)>16:
            continue
        eligible=ImageChops.lighter(eligible,region)
    if eligible.getbbox() is None:
        return rgba
    # A pixel-thin dilate erases baked-in JPEG white edges. Slight antialias
    # softens the mask without changing opaque steel or LASER typography.
    eligible=eligible.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.GaussianBlur(.6))
    alpha=ImageChops.subtract(alpha,eligible)
    rgba.putalpha(alpha)
    return rgba


@lru_cache(maxsize=2)
def _cutout_png(blob: bytes) -> tuple[bytes, bool]:
    """Cache safe cutout result so rendering three designs doesn't repeat matting."""
    with Image.open(io.BytesIO(blob)) as source:
        # JPEG draft reduces decoding allocation before EXIF correction.
        # Every retained pixel is from the actual official product image.
        if source.format in ("JPEG", "MPO"):
            source.draft("RGB", (1800, 1800))
        if source.width * source.height > 4_000_000:
            source.thumbnail((1450, 1450), RESAMPLE)
        original = ImageOps.exif_transpose(source)
        original.load()
    rgba = original.convert("RGBA")
    orig_a = rgba.getchannel("A")
    if orig_a.getextrema()[0] < 250:
        bbox = orig_a.getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
        buf = io.BytesIO()
        rgba=_clear_enclosed_paper(rgba)
        rgba.save(buf, format="PNG")
        return buf.getvalue(), True

    rgb = rgba.convert("RGB")
    channels = rgb.split()
    minimum = ImageChops.darker(ImageChops.darker(channels[0], channels[1]), channels[2])
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])

    # Packshot photography is rarely pure white. Off-white/grey compression
    # artefacts create the objectionable bright rectangle around the tool.
    # A pixel qualifies as background only if it is BOTH light and neutral.
    neutral = ImageChops.subtract(maximum, minimum).point(
        lambda value: 255 if value <= 56 else 0)
    light = minimum.point(lambda value: 255 if value >= 199 else 0)
    candidates = ImageChops.multiply(neutral, light)
    w, h = candidates.size

    # Starting at multiple border locations removes *only* background
    # connected to the photographic edge. Internal white plastic, badges,
    # light-grey steel and enclosed gaps remain original product pixels.
    seeds = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1),
             (w//2, 0), (w//2, h-1), (0, h//2), (w-1, h//2)]
    if not any(candidates.getpixel(pt) == 255 for pt in seeds):
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), False
    for seed in seeds:
        if candidates.getpixel(seed) == 255:
            ImageDraw.floodfill(candidates, seed, 128, thresh=0)

    # A U-shaped tool can surround a large patch of white photograph.
    # Flooding ONLY from the outer edge leaves that area as a bright white
    # rectangle suspended inside the metal jaws. Find the isolated, nearly
    # uniform white *background holes* without touching real tool pixels.
    #
    # Conservative safeguards: substantial area, very neutral/light pixels,
    # colour matching the photo's border, and a limited region count.
    # Small white LASER lettering and internal highlights stay untouched.
    exterior = candidates.point(lambda p: 255 if p == 128 else 0)
    interior_candidates = candidates.point(lambda p: 255 if p == 255 else 0)
    bright_core = ImageChops.multiply(
        interior_candidates,
        ImageChops.multiply(
            minimum.point(lambda p: 255 if p >= 226 else 0),
            ImageChops.subtract(maximum, minimum).point(
                lambda p: 255 if p <= 30 else 0)))
    bright_core = bright_core.filter(ImageFilter.MinFilter(5))
    border_colours = [rgb.getpixel(pt) for pt in
                      ((0, 0), (w-1, 0), (0, h-1), (w-1, h-1))]
    reference = tuple(sorted(c[i] for c in border_colours)[2] for i in range(3))
    minimum_area = max(200, int(w*h*.0025))
    maximum_area = int(w*h*.23)
    for _ in range(96):
        raw = bright_core.tobytes()
        seed_offset = raw.find(b"\xff")
        if seed_offset < 0:
            break
        seed = (seed_offset % w, seed_offset // w)
        ImageDraw.floodfill(bright_core, seed, 128, thresh=0)
        core_component = bright_core.point(lambda p: 255 if p == 128 else 0)
        bright_core.paste(0, mask=core_component)
        bbox = core_component.getbbox()
        if not bbox or (bbox[2]-bbox[0])*(bbox[3]-bbox[1]) < minimum_area:
            continue

        # Expand from the bright central pixels only into the matching
        # isolated white region; it must not connect with the outer border.
        region_work = interior_candidates.copy()
        ImageDraw.floodfill(region_work, seed, 128, thresh=0)
        region = region_work.point(lambda p: 255 if p == 128 else 0)
        region_area = region.histogram()[255]
        if not minimum_area <= region_area <= maximum_area:
            continue
        # Genuine white reservoir caps, round ceramic components, and pale
        # moulded parts are often enclosed by dark metal. A tool-frame gap
        # generally forms an elongated slit, not a rounded white component.
        # Reject roughly square/circular regions rather than erasing them.
        region_box = region.getbbox()
        if not region_box:
            continue
        region_w = region_box[2] - region_box[0]
        region_h = region_box[3] - region_box[1]
        elongation = max(region_w, region_h) / max(1, min(region_w, region_h))
        if elongation < 1.37:
            continue
        # Include even mildly grey/compressed edges if most of the candidate
        # region matches the original paper-white photo background.
        high_confidence = ImageChops.multiply(region,
                                             minimum.point(lambda p: 255 if p >= 223 else 0))
        if high_confidence.histogram()[255] < region_area*.73:
            continue
        from PIL import ImageStat
        mean = ImageStat.Stat(rgb, mask=region).mean
        if any(abs(mean[i]-reference[i]) > 37 for i in range(3)):
            continue
        exterior = ImageChops.lighter(exterior, region)
        interior_candidates = ImageChops.subtract(interior_candidates, region)

    # Feather the exterior AND the verified interior background holes.
    # The actual white metal/labels stay opaque and keep their source pixels.
    connected_background = exterior
    # Feather the merged exterior background and interior white gaps as one
    # mask; do not overwrite it with the original edge-only flood result.
    expanded_background = connected_background.filter(ImageFilter.MaxFilter(3))
    alpha = ImageOps.invert(expanded_background).filter(
        ImageFilter.GaussianBlur(.55))
    foreground = ImageChops.darker(alpha, orig_a)
    bounds = foreground.getbbox()
    if not bounds:
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), False

    histogram = foreground.histogram()
    opaque_fraction = sum(histogram[185:]) / (w*h)
    # If an ordinary workshop photograph is misclassified as a white
    # packshot, never silently erase large portions of it.
    if not .012 < opaque_fraction < .92:
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), False

    # JPEG pixels on the boundary have white baked into their RGB channels.
    # For only semi-transparent boundary pixels borrow the darker local RGB
    # values, preventing a glowing white fringe against dark workshop photos.
    # Pixels inside the product are not recoloured at all.
    fringe = foreground.point(lambda p: 255 if 6 < p < 249 else 0)
    if fringe.getbbox():
        decontaminated = rgb.filter(ImageFilter.MinFilter(3))
        rgb = Image.composite(decontaminated, rgb, fringe)
    rgba = rgb.convert("RGBA")
    rgba.putalpha(foreground)
    pad = max(5, int(min(w, h) * .016))
    rgba = rgba.crop((max(0, bounds[0]-pad), max(0, bounds[1]-pad),
                      min(w, bounds[2]+pad), min(h, bounds[3]+pad)))
    rgba=_clear_enclosed_paper(rgba)
    buf = io.BytesIO()
    rgba.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), True


def manufacturer_cutout(blob: bytes) -> tuple[Image.Image, bool]:
    result, isolated = _cutout_png(blob)
    return Image.open(io.BytesIO(result)).convert("RGBA"), isolated


def scene_category(product: dict) -> str:
    """Visual context only. Do not assert fitment or present as product in use."""
    text = (str(product.get("title", "")) + " " + str(product.get("description", ""))).lower()
    if any(word in text for word in ("pulley", "crankshaft", "engine", "camshaft",
                                     "injector", "timing", "turbo")):
        return "engine"
    if any(word in text for word in ("ratchet", "socket", "spanner", "wrench",
                                     "hex key", "bit set")):
        return "bench"
    return "workshop"


def illustrative_scene(size: tuple[int, int], kind: str = "workshop") -> Image.Image:
    """Soft-focus, explicitly illustrative workshop scenery; never fake a real demo."""
    w, h = size
    sw, sh = max(90, w//2), max(90, h//2)
    canvas = Image.new("RGB", (sw, sh), "#172d40")
    d = ImageDraw.Draw(canvas, "RGB")
    rng = random.Random(kind)
    for y in range(sh):
        t = y/max(sh-1, 1)
        c = (int(20+24*t), int(40+24*t), int(52+16*t))
        d.line((0, y, sw, y), fill=c)
    if kind == "bench":
        for x in range(0, sw, max(25, sw//6)):
            d.rounded_rectangle((x+8, sh*.17, x+sw*.10, sh*.62),
                                radius=3, fill="#364b57")
            d.rectangle((x+14, sh*.28, x+sw*.10-8, sh*.33), fill="#536879")
        d.polygon([(0, sh*.63), (sw, sh*.56), (sw, sh), (0, sh)], fill="#4c5257")
        for i in range(10):
            x = rng.randrange(sw)
            y = rng.randrange(int(sh*.69), max(int(sh*.69)+1, sh-4))
            d.ellipse((x, y, x+8, y+3), fill="#8b969b")
        d.line((0, sh*.65, sw, sh*.57), fill="#9eafb4", width=4)
    elif kind == "engine":
        d.rounded_rectangle((sw*.09, sh*.17, sw*.91, sh*.80),
                            radius=max(8,sw//16), fill="#42535c")
        for i in range(6):
            x = sw*(.17+i*.11)
            d.rounded_rectangle((x, sh*.28, x+sw*.08, sh*.7),
                                radius=7, fill="#61737b")
        d.ellipse((sw*.26,sh*.42,sw*.54,sh*.73), fill="#202f37",
                  outline="#83939b", width=5)
        for i in range(5):
            y = sh*(.20+i*.12)
            d.line((sw*.14,y,sw*.87,y+sh*.09),fill="#33444f",width=8)
    else:
        for i in range(6):
            x=sw*(.08+i*.16)
            d.rectangle((x,sh*.13,x+sw*.09,sh*.77), fill="#435965")
            d.line((x,sh*.20,x+sw*.12,sh*.20),fill="#6b7b85",width=3)
        d.rectangle((0,sh*.72,sw,sh),fill="#56636a")
        d.rectangle((sw*.21,sh*.42,sw*.46,sh*.74),fill="#265778")
        d.rectangle((sw*.21,sh*.47,sw*.46,sh*.50),fill="#4d87a1")
        d.rectangle((sw*.21,sh*.58,sw*.46,sh*.61),fill="#4d87a1")
        d.line((0,sh*.77,sw,sh*.71),fill="#94a6a9",width=5)
    # Out-of-focus light pools and garage ambience, not a claimed demonstration.
    for i in range(4):
        cx = rng.randint(0,sw)
        cy = rng.randint(0,max(1,int(sh*.3)))
        radius = rng.randint(7,max(9,sw//13))
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill="#9aa8ab")
    canvas=canvas.filter(ImageFilter.GaussianBlur(max(5,round(sw/50))))
    return ImageOps.fit(canvas,(w,h),method=RESAMPLE)


def photo_backdrop(size: tuple[int,int], kind: str, uploaded: bytes | None = None,
                   intensity: int = 50) -> Image.Image:
    if uploaded:
        photo=Image.open(io.BytesIO(uploaded))
        photo.load()
        canvas=ImageOps.fit(ImageOps.exif_transpose(photo).convert("RGB"),size,method=RESAMPLE)
        canvas=canvas.filter(ImageFilter.GaussianBlur(5))
    else:
        canvas=illustrative_scene(size,kind)
    canvas=ImageEnhance.Color(canvas).enhance(.67)
    canvas=ImageEnhance.Brightness(canvas).enhance(.76)
    overlay=Image.new("RGB",size,"#0D2C46")
    return Image.blend(canvas,overlay,max(.12,min(.60, (100-intensity)/180)))


def compose_product(base: Image.Image, blob: bytes, box: tuple[int,int,int,int],
                    editor: dict | None = None, product: dict | None = None,
                    uploaded_scene: bytes | None = None):
    """Place true product pixels on coloured or illustrative workshop art.

    User transforms only resize and position original photo; no product redraw.
    """
    editor = editor or {}
    product = product or {}
    x0,y0,x1,y1=[int(v) for v in box]
    w,h=x1-x0,y1-y0
    mode=editor.get("display_mode","shadow")
    background=editor.get("background","clean")
    if mode not in ("cutout","shadow","glow","panel"):
        mode="shadow"
    cutout, isolated=manufacturer_cutout(blob)
    # If the photographic edges are too ambiguous to isolate safely, keep
    # the original genuine tool photograph instead of inventing its outline.
    # The fallback mount is dark, NEVER an extra white rectangle.
    if not isolated:
        mode="panel"
    layer=Image.new("RGBA",(w,h),(0,0,0,0))
    ctx=background
    if ctx in ("context","workshop","bench","engine") or uploaded_scene:
        scene=scene_category(product) if ctx=="context" else ctx
        if scene not in ("workshop","bench","engine"):
            scene="workshop"
        tint=photo_backdrop((w,h),scene,uploaded_scene,
                            int(editor.get("background_intensity",50)))
        layer.alpha_composite(tint.convert("RGBA"))
        # Very gentle border makes illustrative photographic regions intentional.
        ImageDraw.Draw(layer).rounded_rectangle((2,2,w-3,h-3),radius=24,
                                                     outline=(225,237,245,85),width=2)
    elif mode=="panel":
        d=ImageDraw.Draw(layer)
        d.rounded_rectangle((8,8,w-10,h-10),radius=24,
                            fill=(12,33,53,228),outline=(108,149,176,200),width=3)

    zoom=max(70,min(160,int(editor.get("product_scale",100))))/100
    avail_w,avail_h=w-32,h-30
    ratio=min(avail_w/max(1,cutout.width),avail_h/max(1,cutout.height))*zoom
    dims=(max(1,round(cutout.width*ratio)),max(1,round(cutout.height*ratio)))
    if cutout.size!=dims:
        cutout=cutout.resize(dims,RESAMPLE)
    xp=max(-100,min(100,int(editor.get("product_x",0))))
    yp=max(-100,min(100,int(editor.get("product_y",0))))
    cx=(w-cutout.width)//2 + int(xp*w*.003)
    cy=(h-cutout.height)//2 + int(yp*h*.003)
    mask=Image.new("L",(w,h),0)
    mask.paste(cutout.getchannel("A"),(cx,cy))
    if mode in ("shadow","glow"):
        if mode=="shadow":
            blur=mask.filter(ImageFilter.GaussianBlur(14))
            shadow=Image.new("L",(w,h),0)
            shadow.paste(blur,(8,11))
            shadow=shadow.point(lambda p:int(p*.45))
            colour=(8,22,36)
        else:
            shadow=mask.filter(ImageFilter.GaussianBlur(30)).point(lambda p:int(p*.50))
            colour=(75,178,233)
        glow=Image.new("RGBA",(w,h),colour+(0,))
        glow.putalpha(shadow)
        layer.alpha_composite(glow)
    # When the editor zooms beyond 100%, preserve the real tool pixels
    # inside the selected hero region without causing negative-offset PIL errors.
    left=max(0,cx);top=max(0,cy)
    right=min(w,cx+cutout.width);bottom=min(h,cy+cutout.height)
    if right>left and bottom>top:
        crop=cutout.crop((left-cx,top-cy,right-cx,bottom-cy))
        layer.alpha_composite(crop,(left,top))
    # Capture actual alpha visibility, not just the nominal editor rectangle.
    # Source tool pixels remain untouched and are never re-generated.
    from PIL import ImageStat
    from poster_quality import record_product
    total_alpha=ImageStat.Stat(cutout.getchannel("A")).sum[0]
    visible_alpha=ImageStat.Stat(mask).sum[0]
    record_product((x0,y0,x1,y1),
                   visible_alpha/max(total_alpha,1),isolated)
    base.alpha_composite(layer,(x0,y0))
    return isolated
