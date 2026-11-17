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


### V3 — cutout-first posters, contextual backgrounds and advanced editor (November 2026)

The one-click AI button still creates **exactly three sales posters**: Retail, Premium, and Trade. They use the original Laser Tools packshot with a **safe edge-connected background removal pass**, not an AI-generated replacement product. White parts of the tool that are enclosed by its outline are preserved. If isolation is unreliable, the original manufacturer photograph is retained inside a tidy frame rather than mangled.

The Trade layout uses a separate **genuine official manufacturer in-situ photo** as an out-of-focus background whenever the official product record supplies one. Otherwise it uses a clearly illustrative workshop, toolbench or engine-bay background. Illustrations are not actual demonstrations or evidence of fitment. Editors may optionally supply an authorised JPEG/PNG/WebP image (up to 2 MB); this picture is used **only behind** the original manufacturer product photograph, not in place of it. Background photos are not stored server-side; editor settings live only in the current browser session.

Added editing controls:
- Product: cutout, soft shadow, glow, or framed original; scale 70–160%; horizontal and vertical offsets.
- Graphic styling: colour palettes, custom colour accents, clean/grid/rings or contextual backgrounds, background strength and graphic-shape intensity.
- RRP: circle, plaque, wide banner, angled tag; two safe placement options. Price/VAT always remains the verified figure.
- Typography: headline size, optional editable supporting line, and UK trade/technical/premium/sales tone.
- Copy: **Suggest 3 trade-ready headlines** makes one Gemini free-tier call, and selecting a suggestion simply fills the editor field. **Regenerate this design** asks Gemini for only one revised marketing concept in the chosen tone.
- Copy generation specifically rejects generic hype (e.g. "conquer", "game-changing", "upgrade your") and prioritises verifiable applications and product functions.

Original manual posters, official-image sourcing, distributor branding, price review, and ZIP export have not changed. Editor updates need no Gemini calls unless you explicitly ask for new copy. Full tests in test_ai_v3.py verify cutouts, photo-source accuracy, context images, safe price locks, new editor choices and browser JavaScript syntax.


### V4 — photographic promotional campaigns by product type (November 2026)

**Generate with AI** still uses a single click and outputs **three visibly different sales advertisements**: bold retail, editorial/premium and trade/workshop. The previous boxy graphics have been replaced with full-size photographic backgrounds, large manufacturer-photo product cutouts, dark translucent brand panels, realistic layering, strong readable headlines and bold UK RRP/price-on-request treatments. The original manual poster builder is untouched.

**Context is selected automatically from the actual product**, with simple auditable rules rather than generative hallucination:
- Battery chargers, maintainers and jump-starters → *genuine photographs of a vehicle battery with connected jumper leads*, with the actual manufacturer charger/kit photo prominent in the foreground.
- Diagnostics and scanners → vehicle diagnostic workstation/technician.
- Brake service tools → brake discs, calipers and brake maintenance.
- Suspension/hubs/bearings → under-car/suspension workshop setting.
- Engine pullers, glow-plug and timing tools → genuine engine-repair photography.
- Ratchets/sockets/spanners → real toolbench/workshop photography.
- Hydraulic workshop presses → industrial press/workshop setting.
- Welders → real vehicle welding/repair photography.
- Other tools → credible general vehicle service workshop photography.

Category selection is deterministic and reviewable in promo_scene_library.py. Different part numbers and design families select different photographs/photographic crops from the matching category, plus different poster hierarchies and genuine product packshots. The app **does not claim the photographed stock scene shows the exact tool in use**. An official Laser Tools in-situ application image is preferred for the trade campaign when available, since it is more product-specific than stock imagery. All original tool pixels and verified price/VAT data remain untouched.

**Photo rights & reliability:** Curated genuine photos are from [Pexels](https://www.pexels.com/license/), which licenses images for commercial marketing, with use restrictions (including no implied personal/brand endorsement). The preview cards show which scene was chosen and link to its source. Stock image downloads are strictly restricted to hard-coded verified Pexels photo IDs and cached in process. If a background is unavailable, the system uses a clean navy photographic-style graphic rather than drawing a fake charger/vehicle/tool application. Backgrounds may be replaced with an authorised staff-supplied photo in the existing editor. User uploads are not stored on the server.

No extra API subscription has been introduced: Gemini free tier remains for copy direction; real photos and all poster layout rendering use requests and Pillow. New code: ai_cinematic.py, promo_scene_library.py; tests: test_scene_library.py. External-photo calls are disabled only in CI via DISABLE_STOCK_PHOTOS=1, not in the live site.

### V6 — product-aware photography and nine rotating creative layouts (November 2026)

**Step 1 — Real workshop background direction** (promo_scene_library.py, app.py, ai_cinematic.py)

- The tool's manufacturer title is classified before its longer description, protecting charger/battery tools from incorrect engine context.
- Curated commercial-use photography now has category-specific scene pools. It uses factual contexts such as battery with leads, car brakes, suspension, engine repair and workshop maintenance, rather than inventing a photo of the tool in use.
- Retail, Premium and Trade each get different crop focus, image brightness, desaturation and blur; part numbers independently rotate among the approved photographs.
- Official Laser Tools in-situ photos are preferred for the Trade direction when available.
- Image URLs come only from fixed approved Pexels photo IDs and are downloaded with file-size limits, timeouts and in-process caching. Staff can review the linked photo source. When no photo is available, a clean brand backdrop is used.
- The manufacturer tool photograph and reviewed UK RRP are not altered or regenerated.

**Step 2 — Three different sub-layouts in each creative family** (ai_variant_layouts.py, ai_cinematic.py)

- Retail A: bright price-led campaign with circular RRP and central product. Retail B: strong diagonal split and price on left. Retail C: large real context photo with white headline ribbon and angular price tag.
- Premium A: clean light editorial. Premium B: photo-gallery band and spacious headline. Premium C: full-height workshop picture on the left with a dedicated white information column.
- Trade A: full-bleed workshop advert. Trade B: navy industrial split with photo on the right. Trade C: dramatic diagonal photograph and high-contrast headline ribbon.
- Each Generate with AI press still produces three separate adverts, one from each family. Sub-layout variation changes between generations and part numbers; the original poster editor retains headline, colour, price and product placement controls.
- Rendering uses genuine source photographs and locally produced graphics. No paid image generation is required.

**Regression tests:** test_scene_variants.py exercises family-aware crop metadata, safe approved-photo selection, all nine 1200-by-1500 PNG layouts, their visual differences and editor compatibility. GitHub Actions runs it alongside the existing tests.
