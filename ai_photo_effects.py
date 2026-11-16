"""Faithful manufacturer packshot cut-outs and controlled workshop backdrops.

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


@lru_cache(maxsize=10)
def _cutout_png(blob: bytes) -> tuple[bytes, bool]:
    """Cache safe cutout result so rendering three designs doesn't repeat matting."""
    original = ImageOps.exif_transpose(Image.open(io.BytesIO(blob)))
    original.load()
    if original.width * original.height > 4_000_000:
        original.thumbnail((1450, 1450), RESAMPLE)
    rgba = original.convert("RGBA")
    orig_a = rgba.getchannel("A")
    if orig_a.getextrema()[0] < 250:
        bbox = orig_a.getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), True

    rgb = rgba.convert("RGB")
    channels = rgb.split()
    min_chan = ImageChops.darker(ImageChops.darker(channels[0], channels[1]), channels[2])
    max_chan = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    neutral = ImageChops.subtract(max_chan, min_chan).point(lambda v: 255 if v <= 38 else 0)
    bright = min_chan.point(lambda v: 255 if v >= 217 else 0)
    candidates = ImageChops.multiply(neutral, bright)
    w, h = candidates.size
    seeds = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1),
             (w//2, 0), (w//2, h-1), (0, h//2), (w-1, h//2)]
    # Flood only eligible pixels connected to the photo edge; white parts
    # inside the actual tool (plastic reservoirs, white labels) remain opaque.
    if not any(candidates.getpixel(pt) == 255 for pt in seeds):
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), False
    for seed in seeds:
        if candidates.getpixel(seed) == 255:
            ImageDraw.floodfill(candidates, seed, 128, thresh=0)
    alpha = candidates.point(lambda p: 0 if p == 128 else 255)
    # Reduce bright antialiasing fringe without resynthesising the tool.
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.7))
    bounds = alpha.getbbox()
    if not bounds:
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), False
    foreground = ImageChops.darker(alpha, orig_a)
    # Reject aggressive cutouts; preserve originals if isolation is uncertain.
    coverage = foreground.histogram()
    opaque_fraction = sum(coverage[185:]) / (w*h)
    if not .012 < opaque_fraction < .91:
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        return buf.getvalue(), False
    rgba.putalpha(foreground)
    pad = max(4, int(min(w, h) * .015))
    rgba = rgba.crop((max(0, bounds[0]-pad), max(0, bounds[1]-pad),
                      min(w, bounds[2]+pad), min(h, bounds[3]+pad)))
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
    # Never show a white photographic slab on coloured graphics without framing.
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
                            fill="#FFFFFF",outline="#D7E5EF",width=3)

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
    base.alpha_composite(layer,(x0,y0))
    return isolated
