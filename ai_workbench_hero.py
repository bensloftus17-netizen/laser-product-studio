"""One bounded, source-guided AI illustration for the price poster."""
import base64
import io
import json
import os
import re
import time

import requests
from PIL import Image, ImageOps

MARKER = b"STUDIO_AI_WORKBENCH\0"
SIZE = (1200, 603)
MAX_RESPONSE = 5 * 1024 * 1024


def is_workbench_hero(scene):
    return isinstance(scene, bytes) and scene.startswith(MARKER)


def _reference(blob):
    with Image.open(io.BytesIO(blob)) as image:
        image.draft("RGB", (800, 800))
        if image.width * image.height > 12_000_000:
            raise ValueError("Workbench reference exceeds the safe decode budget")
        image.thumbnail((1000, 1000))
        stream = io.BytesIO()
        ImageOps.exif_transpose(image).convert("RGB").save(stream, "JPEG", quality=88)
    return _image_part(stream.getvalue())


def _image_part(blob):
    return {"inlineData": {"mimeType": "image/jpeg",
                           "data": base64.b64encode(blob).decode("ascii")}}


def generate_workbench_hero(product, photo, workshop, *, alternate=None):
    """Return a reviewed illustration, or None for the official-photo fallback."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key or os.environ.get("STUDIO_AI_WORKBENCH", "").lower() != "true":
        return None
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    reviewer = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not all(re.fullmatch(r"[\w.-]{3,80}", value) for value in (model, reviewer)):
        return None
    try:
        source = [_reference(photo)]
        if alternate and alternate != photo:
            source.append(_reference(alternate))
        title = str(product.get("title", ""))[:180]
        parts = [{"text": (
            "Create only the wide photographic hero image for a trade advert. "
            "The first image(s) are official views of the exact tool. The last image "
            "is the reference workshop. Use its blue cabinets and steel workbench. "
            "Show a photorealistic elevated three-quarter view of the exact tool "
            "resting on the steel. For a kit, remove the storage tray from the scene "
            "and lay the supplied pieces separately across the table with natural contact "
            "shadows. For a single tool, leave it assembled. Preserve exact count, "
            "shapes, visible thickness, proportions, materials and handle design. "
            "Never add tools, accessories or parts. Keep the complete spread well inside "
            "the central 85% of the frame. No headings, borders, prices or added text. "
            f"Reference product: {title}."
        )}, *source, _reference(workshop)]
        payload = {"contents": [{"parts": parts}], "generationConfig": {
            "responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}}
        endpoint = ("https://generativelanguage.googleapis.com/v1beta/models/"
                    + model + ":generateContent")
        deadline = time.monotonic() + 50
        data = bytearray()
        with requests.post(endpoint, headers={"x-goog-api-key": key},
                           json=payload, timeout=(5, 45), stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=65536):
                if len(data) + len(chunk) > MAX_RESPONSE or time.monotonic() > deadline:
                    return None
                data.extend(chunk)
        outputs = json.loads(data)["candidates"][0]["content"]["parts"]
        raw = next(p["inlineData"]["data"] for p in outputs if p.get("inlineData"))
        with Image.open(io.BytesIO(base64.b64decode(raw, validate=True))) as image:
            if image.width * image.height > 4_000_000 or image.width < 800:
                return None
            if not 1.6 <= image.width / image.height <= 2.3:
                return None
            hero = ImageOps.fit(image.convert("RGB"),SIZE,Image.Resampling.LANCZOS)
        stream = io.BytesIO()
        hero.save(stream, "JPEG", quality=90)
        jpeg = stream.getvalue()
        from ai_concepts import _gemini_json
        check = _gemini_json({"contents":[{"parts":[{"text":(
            "Compare the last image, a proposed marketing illustration, with the "
            "earlier official photos of the same tool. Return JSON with a boolean "
            "matches. Set it true only if every pictured tool is the same design "
            "and the kit has the same tool/component count, proportions, thickness, "
            "handles and heads. A removed storage tray is fine. Reject clipped items, "
            "tools floating above the bench, invented details or any uncertainty."
        )},*source,_image_part(jpeg)]}],"generationConfig":{
            "responseMimeType":"application/json","maxOutputTokens":80}}, key, reviewer)
        return MARKER+jpeg if isinstance(check,dict) and check.get("matches") is True else None
    except (requests.RequestException, RuntimeError, ValueError, TypeError,
            OSError, KeyError, StopIteration, IndexError):
        return None
