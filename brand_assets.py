"""Bundled authentic distributor logos supplied by the user for demo co-branding.

Logos are cropped for framing but never redrawn. All uses require brand approval.
""" 
import base64
import io
from PIL import Image

BRAND_LABELS = {
    "none": "Laser Tools only",
    "gsf": "GSF Car Parts",
    "euro": "Euro Car Parts",
    "mpd": "Motor Parts Direct",
}

# Encoded image bytes, no network access or stock photo substitution.
_BRAND_DATA = {
    "gsf": """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""",
    "euro": "",
    "mpd": "",
}


def get_brand_image(code):
    key=str(code or "").strip().lower()
    if key not in BRAND_LABELS or key == "none":
        return None
    raw=_BRAND_DATA.get(key)
    if not raw:
        return None
    with Image.open(io.BytesIO(base64.b64decode(raw))) as img:
        return img.convert("RGB").copy()
