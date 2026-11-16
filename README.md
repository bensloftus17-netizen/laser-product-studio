# Laser Product Studio

Free-tier Render web app. Enter a Laser Tools part number; the app looks up official product data from lasertools.co.uk / Tool Connection, validates source/part number, uses official product images, and generates 4 PNG marketing graphics, a technical PDF and a ZIP.

**Limitations:** The actual live lookup must be tested from the deployed Render service. Some product pages may block automated access, and not every part has an official PIS or retrievable image. Do not publish unreviewed marketing claims. The app is a prototype, not affiliated with the public Laser Tools website.

**Deploy:** Create a GitHub repository and upload the contents of this folder to the repository root (keep the `static` and `templates` directories). In Render, create a Web Service pointing to that repository with plan Free, Python runtime, build command `pip install -r requirements.txt`, start command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 95`. An equivalent `render.yaml` Blueprint is included. Then open your new HTTPS website and test part number `9197`.


## Product-aware marketing (V19)

The studio now recognises product families from the **official English manufacturer record** and adapts the promotional photo composition, technical-sheet detail and verified selling-point priorities. The customer-facing product record explains the detected category and its marketing angle.

- **Ratchet / socket sets** emphasise genuine set contents, sizes, storage and a clean kit photograph.
- **Hydraulic workshop presses** emphasise documented force, controls and workshop use, with an industrial equipment-led composition.
- **Bearing / suspension, lighting, air/power tools, diagnostics, bodyshop, servicing, threading, accessories and general hand tools** each have their own category rules.

The strategy is **transparent rule-based art direction**, not an actual image-generation or LLM integration. It never changes the original product photograph or invents technical claims.

See [MARKETING_ART_DIRECTION.md](MARKETING_ART_DIRECTION.md) for the full category framework and [marketing_intelligence.py](marketing_intelligence.py) for the implementation. The 26 regression tests in [test_studio.py](test_studio.py) include category classification, evidence-based selling points, adaptive technical layouts and co-branded marketing exports.



## Optional generative AI poster concepts (V20)

The original product lookup, three default poster previews, manufacturer photo, RRP review,
distributor branding and ZIP export remain unchanged. After a successful lookup, click
**Generate with AI** to obtain three additional visual poster recommendations with
downloadable PNG previews (spotlight, split-layout and technical-layout).

This is a **real model-backed feature**, not a random template picker: the language model
studies the verified product title, manufacturer description, specifications, and features
to create different creative positioning, headlines and selected evidence-based selling points.
The rendering stage preserves the **authentic manufacturer product image** and places
typography in deliberately bounded layout zones. AI recommendations are new draft images
and do not replace the original three export formats.

### Enable the AI on Render

1. Open the Render web service for this repository.
2. Add environment variable `OPENAI_API_KEY` as a **secret** (never put a key in GitHub,
   browser JavaScript or a source file).
3. Optional: set `OPENAI_MODEL` (default `gpt-4.1-mini`).
4. Redeploy the service, load a product, then click **Generate with AI**.

When the key is missing or AI is unreachable, the AI panel shows a clear error and
the existing poster builder continues working. The server passes only official public
product details to the configured API; no browser-side credentials are exposed.
The API may incur usage charges, and Render's free-tier request timeout can affect
slow model responses. Staff must verify every AI-written headline, subline and
marketing assertion before external use. Suggested wording is not an approved
manufacturer claim and no actual model training or long-term learning is implied.

