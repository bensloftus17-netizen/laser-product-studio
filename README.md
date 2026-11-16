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
product-aware advertising concepts, with authentic manufacturer imagery and downloadable PNGs. Gemini writes three different marketing concepts; the site renders them inside three professionally art-directed Laser Tools sales-poster families (Retail, Premium and Trade). There are three palette variations per family, so repeated generations can change the colours while keeping the brand consistent. The real product packshot may be isolated from a plain white background and enlarged, but is never AI-redrawn.

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

### Promotional design refresh — November 2026

The three styles were rebuilt to match the new Laser-style reference concept. Retail uses a bold navy/blue angular header, large official photo frame and circular RRP bubble; Premium uses a bright editorial hierarchy, large product hero and clean outlined price plaque; Trade uses a charcoal workshop theme, diagonal shapes, side-by-side text/product framing and a prominent wide RRP ribbon. A single click still produces **exactly three different promotional designs**, with no user prompt required. Text is fitted to measured spaces and long copy safely abbreviated when necessary. The full-size **View large preview** action is available for each design before downloading. Rendered photos are placed unchanged (apart from cropping outer white whitespace and resizing) and all RRPs come from the official/staff-reviewed product record.

Temporary Gemini 500/502/503/504 service errors are retried up to two more times automatically; API quota, authentication and model-access errors are not retried. This uses the existing free API tier and does not require extra infrastructure or paid image generation.

### AI poster editor — November 2026

After using **Generate with AI**, select **Edit this poster** on any of the three options.
The new editor works on that design only; the other two previews remain untouched.

* Edit the short promotional headline (up to 48 characters).
* Pick one of three brand-safe colour palettes, or select custom accent and background colours.
* Choose clean artwork, a geometric grid, or circular background graphics.
* Move the UK RRP bubble/plaque to the opposite side (or reverse the price banner's alignment on trade adverts).
* Click **Apply changes to this poster** to redraw locally on the Python server using Pillow; this does **not** invoke or charge the Gemini model.
* Click **Regenerate this design** to ask Gemini for one fresh marketing concept for this specific poster, retaining the selected palette, background, price placement and manufacturer's original photography.
* The edited card in the three-poster gallery is updated and can be downloaded as a full-resolution PNG. Changes live in the current browser session; **download** to keep your work (persistent project history is not yet available).

The server always obtains the official product photograph, true part number, official product title and verified RRP independently from the product lookup; it never accepts those values or uploaded images from editor settings. Manufacturer feature bullets are validated against the original record, and any staff-entered prices still require explicit price review. Original marketing-pack generation remains unchanged. Editor API: `POST /api/ai/edit/<part>`. Editor tests: `test_ai_editor.py`.
