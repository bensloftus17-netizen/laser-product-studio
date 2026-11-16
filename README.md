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



## Optional generative AI poster concepts (Gemini free-tier)

The original product lookup, three default poster previews, distributor branding, price review
and ZIP export are unchanged. **Generate with AI** uses Google's Gemini API to propose three
product-aware advertising concepts, with authentic manufacturer imagery and downloadable PNGs. Gemini directs nine distinct design families: cinematic, retail, diagonal, industrial, editorial, minimal, feature, blueprint and data. Each generation must select one impact campaign, one editorial advert and one technical concept; the model chooses which layouts fit the product. The real product packshot may be isolated from a plain white background and enlarged, but is never AI-redrawn.

### Free setup (Google AI Studio)

1. Open https://aistudio.google.com/apikey and create a Gemini API key using a project eligible for the free tier.
2. In Render > laser-product-studio > Environment add `GEMINI_API_KEY` and paste the secret API key into its value. Never add the key to GitHub.
3. Save and deploy. Optionally configure `GEMINI_MODEL`, default `gemini-3.5-flash-lite`.
4. Load product 9395, click **Generate with AI**, and review all generated claims before publication.

This implementation makes real model calls, but **does not train its own model** or learn
persistently from previous requests. The visual rendering remains controlled to avoid
inventing physical tools. Google's free tier has usage limits and may use submitted content
to improve its products. The AI call transmits only the public official manufacturer record
to Google, not private internal sales data. Free-tier availability is conditional on your
project/region/model and Google's current terms. Do not enable paid billing if you want zero
API charges. The old `OPENAI_API_KEY` is no longer used and can be deleted from Render.

Note (Nov 2026): Google restricts Gemini 2.5 access for newly created API projects. New projects should use `gemini-3.5-flash-lite` (the default in this repo), provided it is available to your free-tier project. If `GEMINI_MODEL` was manually set to an older model on Render, update or remove that override.


### One-click promotional AI (November 2026)

The **Generate with AI** button requires no prompt or choices. Once a product is loaded,
Gemini chooses marketing headlines and verified selling points from the official manufacturer
record, and the site ALWAYS renders three distinct sales advertisements:

1. **Bold retail promo** — vibrant Laser blue, angular shapes and a circular RRP burst.
2. **Clean premium promo** — light editorial spacing, genuine product photo and refined RRP plaque.
3. **High-impact trade promo** — industrial dark backgrounds, asymmetrical composition, angular
   shapes and a wide price banner.

Each design has three colour variations, chosen anew on every generation. All three include
the authentic product photograph, verified part number/title, manufacturer facts and
the **actual UK RRP with correct VAT descriptor** where known; missing prices say
**PRICE ON REQUEST**. Staff-entered RRP only applies after the existing review control
has been explicitly approved, and is labelled draft. The renderer does not calculate or invent
prices, discounts or product specifications. Brand review remains required before publication.

These new posters are rendered by `ai_promo_renderer.py`. The original manual poster
builder and its three export formats remain unchanged. Promos are separate downloadable PNGs.
The generative model is the free-tier text model (not a paid image synthesis API). The
optional creative direction field was intentionally removed to make generation truly one-click.
Tests live in `test_ai_promos.py`.
