# Laser Product Studio — Product-Aware Marketing Framework (V19)

## What this upgrade does

Laser Product Studio now recognises the **type of tool** from its official manufacturer product record, prioritises category-relevant *verified* selling points and selects an art direction **before generating** promotional, technical and RRP designs. It also shows the category and intended selling angle to the person creating the posters.

This version uses transparent **deterministic classification and scoring**, not a paid generative language or image API. It is an **art-direction engine / foundation for future AI marketing planning**, not an assertion that machine-learning artwork is being generated. The core goal is to reduce repeated manual decisions and allow reps to create more effective drafts quickly.

### Source-of-truth rules

- Product names, applications, numbers, prices, accessories and specifications must come from the **verified English manufacturer record**, not an advertising idea.
- Category headlines are **generic promotional framing**, not invented specifications. Avoid unsupported claims like "the strongest", "best", or guaranteed savings.
- Features are **reordered**, not fabricated; priority words rank real manufacturer sentences.
- Keep the exact product photograph; graphics, geometric framing, contrast and background treatments may differ by product category. Do not redraw the actual tool.
- If information is sparse, show fewer facts larger, not a fake technical specification table.
- Prices are retrieved from the UK listing or explicitly reviewed staff input; VAT must be clear. No unverified figures.
- Distributor logo selections (GSF, Euro Car Parts, MPD) remain optional; use only with the required brand approvals.
- A human must approve all customer-facing marketing drafts.

## Product categories and their campaign directions

| Category | What makes the tool sell | Promotional visual direction | Technical information priority | RRP / sales emphasis |
| --- | --- | --- | --- | --- |
| **Socket & ratchet sets** | Verified piece count, drive sizes, completeness, tooth count, storage | Neat **full kit** photograph; clean organised showroom-style backdrop | Set contents, verified drives, ratchet details, storage. **Light** layout | Set description + selected included features |
| **Hydraulic & workshop presses** | Verified tonne capacity, pressure, controls, working area, workshop tasks | Industrial **full-height** product presence, stronger steel-blue geometry | Capacity, force, controls, dimensions and safe usage. Dense only where enough facts exist | Capacity and price clear without tiny text |
| **Bearing & suspension** | Vehicle applications, problem/solution, safe removal/fitting methods, kit contents | Workshop-specific graphic angle; genuine in-use image when provided | Applications, adapters, fitting technique, technical sizes; detailed layout with sufficient source facts | Application compatibility and benefits |
| **Lighting & inspection** | Brightness, run time, mounting, battery, visibility, adjustable heads | Brighter **spotlight rings** behind the real lamp | Lumens/W, run time, recharge, mounting features | Lighting benefit and price |
| **Air & power tools** | Verified torque, drive size, speed, air pressure, ergonomics | Dynamic **performance/grid** accents behind the exact tool photo | Torque, pressure, drive, weight/noise only when published | Torque/drive features and cost |
| **Diagnostic & electrical** | Confirmed functions, ranges, accuracy, compatibility | Precise technical **grid** graphics, no invented screen content | Measurement ranges, power requirements, testing functions | Functions and price |
| **Bodyshop & repair** | Repair use, materials and task-specific benefits | Distinct **repair workflow** graphic diagonals; genuine product only | Supported materials and repair tasks | Suitable use and RRP |
| **Workshop servicing** | Fluid capacity, one-person use where verified, service process | Neat service-themed **framed** tool image | Capacity, pressure, adapter information | Practical purpose and price |
| **Threading & cutting** | Piece count, included taps/dies, ranges, storage, materials | **Organised kit** and complete contents view | Set sizes and verified contents. Usually light | Piece count, included tools and price |
| **Accessories & consumables** | Pack quantity, size, compatible tools, consumable purpose | Clean component photography and layout | Quantity, dimensions, compatibility | Pack size, SKU, price |
| **General hand tools** | Drive, length, material, grip, workshop use | Clean **single-tool** photo and restrained outlines | Only genuine characteristics; light layout | Value proposition from real features |

Implementations and specific keyword/feature priorities are in **`marketing_intelligence.py`**.

## How the pipeline works

1. **Lookup** — retrieve official UK Laser / Tool Connection source details, RRP and the genuine product photograph.
2. **Validate** — clean the record, filter non-English sentences, deduplicate and reject unsupported numerical claims.
3. **Classify** — match a specific product name against ordered tool-category rules. Only use description fallback if title is genuinely ambiguous.
4. **Plan the marketing** — calculate:
   - `category` and `category_label`
   - `evidence` (product title / manufacturer description / general fallback)
   - `marketing_angle` and category-safe campaign `headline`
   - `hero_focus` and `visual_style`
   - ranked manufacturer `selling_points` and `technical_priority`
   - preferred technical density.
5. **Render** — the **promotional poster** uses a product-family graphic background, category-aware photographic framing, a verified selling line and ranked fact strip. The **technical poster** adapts light/medium/dense based on product category *and actual source content*. The **RRP poster** displays a category cue, verified points and price.
6. **Review** — show the detected category and angle in the website alongside the official product record; user checks content and price.
7. **Export** — three PNGs, the technical PDF, marketing-copy text and JSON source record. Include the chosen marketing direction in the source record.

## Visual examples for the MD

**9364 — Three-piece ratchet set:** Category `socket_ratchet`, set/size/storage selling points. Clean organised product photo, light technical layout, no unsupported torque values.

**9372 — 50-tonne air-hydraulic workshop press:** Category `workshop_press`, verified tonnage, control and capacity priority. Larger vertical machine photograph, dark industrial backdrop, technical data prioritised when available.

**9395 — Front wheel bearing kit for Sprinter & Crafter:** Category `bearing_suspension`, applications, workshop problem being solved, kit functionality. Specialist technical layout if manufacturer facts are sufficiently detailed.

**9197 — Under-bonnet work lamp:** Category `lighting_inspection`, visibility, magnetic mounting and published run time where verified. Spotlight graphics, tall product framing.

**9024 — Air impact wrench:** Category `air_power`, verified torque and air/power parameters. Performance-style composition with the real product photo.

## Critical classification safeguards

- Use the **product name first**: 9395 may use a standard workshop press but is *not* itself a workshop press.
- A socket kit must not be tagged as a power tool just because it includes impact sockets.
- When a new product is unrecognised, use a safe "General hand tools" fallback and show this as lower-certainty classification.
- Do not infer "50 tonnes" from a photo or from other products. This claim must appear in that product's official title, specifications or features.
- Prioritise real manufacturer feature sentences by category. Do not invent a feature to fill a three-cell poster strip.
- If a specialist tool has too few verified facts, **choose medium technical density instead of forced dense panels**.
- Never show raw foreign-language feature lists or truncated measurements in a customer-facing design.

## How we will evaluate the improvement

For each of 9364, 9372, 9395, 9197, 9024 and an unknown part number with a valid official source, check:

- The recognised category makes sense and the matched evidence is understandable.
- The three campaign formats remain visibly different, and the promotional composition differs meaningfully between a ratchet set and a workshop press.
- The dominant selling points are actually relevant to the category, with source support.
- Image placement adapts to wide kit photos versus tall machines.
- No cropped price/headline, text overlap, non-English fragments, fabricated components or fake specifications.
- Laser-only and distributor-branded versions both export successfully as PNG/PDF/ZIP.
- A person can understand the value of the result without editing every single poster.

## Next step: a genuine generative AI art director (optional future phase)

After this rules-based baseline passes user testing, an LLM service could:
- propose several *different* audience-specific campaign concepts from the validated English source record,
- score the strongest factual benefits,
- propose optional workshop background treatments without altering original products,
- suggest copy variations and review warnings.

**However, the model must return strict, structured fields and trace every product claim back to the official record.** Generated marketing text should be validated before renderer use. AI background generation must be an optional, separate layer with the *original product imagery composited unchanged*. Do not describe V19 as an actual LLM integration.

## Project files

- `marketing_intelligence.py` — category definitions, classification, claim ranking and art-direction plan.
- `poster.py` — three category-aware artwork renderers with preserved official product photography.
- `app.py` — product lookup, category/marketing-angle display, previews and reviewed ZIP exports.
- `test_studio.py` — CI regression tests for product families, layout selection and genuine-source messaging.
