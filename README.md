## V69 — One workshop promo template, genuinely different supporting artwork

The user-supplied blank workshop/workbench reference is reserved exclusively
for **Poster 02 / Price Promotion** (the default Workshop Showcase choice).
A genuine Laser product photo is placed into the large hero space; factual
information panels are populated from verified product descriptions, and the
price panel uses verified RRP/VAT or the truthful PRICE ON REQUEST label.
The image is a dynamic layout reference, not a flattened image with empty boxes.

- **Poster 01:** blue-and-white structured technical product sheet;
  never uses the workshop sales layout.
- **Poster 02:** approved workshop scene, workbench, source-authentic product,
  functional information panels and commercial price treatment.
- **Poster 03:** AI-selected benefit/product spotlight with its own layout
  family; neither technical nor workshop references may overwrite it.
- **Six additional native formats:** keep the approved parent *selling angle*,
  but each gets an independent creative family and distinct visual treatment.
  Valid original AI choices are honoured unless they repeat a family/treatment
  already used in the same campaign. Verified fallback renders use the same
  independent art directions rather than duplicating the parent poster.
- The campaign validates the three poster render-engine roles before
  generating social formats, and saves the chosen role/family/treatment in
  the manifest for design review.
- The pre-existing genuine manufacturer imagery, original product pixels,
  English-only source checks, verified pricing, and visual/geometry QC remain
  enforced. No draft is automatically published.

Tests: `python -m unittest -v test_role_separation_v69.py
test_reference_templates_v67.py test_reference_critic_v68.py`.
GitHub Actions workflow: `.github/workflows/poster-regression.yml`.
A full live 9-artwork campaign still requires verification before an important
demo; a successful Render deployment only confirms the app starts.

---

## V67 — Reference-led technical and promotional poster roles

The two user-supplied reference screenshots are now **reusable dynamic layouts**,
not embedded raster screenshots or invented pictures of Laser tools.

- **Poster 01 — Technical / Application** uses the blue and white
  manufacturer-style product sheet from reference two: prominent LASER header
  and part number, product title, genuine large hero photo, source-backed
  application line when available, and a complete-facts Additional
  Information section. It never silently truncates a manufacturer claim.
- **Poster 02 — Price Promotion** uses reference three's automotive-workshop
  and steel-workbench visual style: LASER header, substantial genuine product,
  labelled feature panels (always populated), a KIT CONTENTS panel **only when
  explicitly backed by manufacturer features**, honest UK RRP/VAT label or
  PRICE ON REQUEST, and a black/blue LASER footer. External workshop scene
  photos must still come from the existing approved real-source library.
- **Poster 03 — Product-Selected** remains the independently art-directed,
  AI-led role; it must not clone the information sheet or the price design.
- Both reference roles stay reference-led whether Gemini succeeds or not.
  Their composition is also protected during AI visual-review repair and
  verified-safe recovery. Variant selection may adjust source photo staging,
  but will not change the role-specific layout.
- Original manufacturer source pixels, approved price/VAT provenance,
  distributor logo permissions, English-only source checks, candidate ranking,
  full independent visual QA, nine native artwork files and ZIP workflow
  are all retained. Any asset that still fails an actual quality gate is not
  silently approved or published.
- Campaign Manifest and the UI now label which fixed reference renderer
  actually produced the technical and promotional posters.

Regression tests: `python -m unittest -v test_reference_templates_v67.py`.
Additional smoke testing has used simulated product records for parts 9395,
6728 and 4554 (both reference layouts). Full live nine-asset generation,
manufacturer source availability and aesthetic approval still need hands-on
verification, particularly on the 512 MiB Render Free service.

---

## V65 — Memory-stable full-quality campaigns on a 512 MiB Render worker

Render confirmed `oomKilled: 512Mi` at **10:19 and 10:49 UTC on 20 November
2026**, after image-generation work. This is server RAM exhaustion, not
a browser cache issue. Clearing the build cache/restarting is temporary.

V65 reduces peak and retained memory while preserving the genuine
manufacturer photo, native 1200×1500 posters, native Story/banner pixels,
three original promotional approaches, verified RRP/VAT labels, and all
deterministic + independent artwork QA gates.

- **Private disk-backed completed packs:** approved ZIPs, nine PNGs and
  source-backed poster-editor photos are written to private container-local
  temporary storage. Only small manifest/metadata objects stay in RAM.
  Download endpoints stream files by path; resume, editable posters and
  individual assets keep their bearer-token permissions. Expired/evicted
  packs remove their private files. Storage is ephemeral on deploy/restart,
  just like earlier in-process packs; not a permanent saved-promotion system.
- **One expensive rendering operation at a time** across desktop requests,
  progressive mobile jobs and individual poster edits. A simultaneous
  second request receives HTTP 429 / Retry-After rather than doubling peak
  1200×1500 RGBA canvas memory and causing another OOM.
- **Bounded authentic source caches:** two heavy decoded/PNG cutouts (rather
  than 10–12), and three recent official manufacturer/photo lookups. Clear
  decoded image caches and collect garbage after each success or failure.
- **In-place compositing on fresh artboards:** avoid repeat multi-megabyte
  RGBA overlays for all three posters, six campaign formats and the
  Workshop Showcase reference template. This must have pixel-identical
  output to the original renderer, not reduced-resolution output.
- **No huge QA pixel arrays:** white-halo analysis streams pixels rather
  than building a list of hundreds of thousands of tuples. It no longer
  modifies the cached genuine manufacturer image by thumbnailing it for
  inspection; photo detail is preserved.
- **Bounded source-image checks:** two high-quality manufacturer-image
  inspections in parallel, rather than four simultaneous large cutouts.

The complete existing art review, source constraints and nine-asset
download format remain in force. V65 automated regressions cover
private-pack roundtrip/expiry, PNG and ZIP downloads, editor state,
concurrency blocking, pixel-identical overlays, unmodified source
photo quality, and cache limits. On a 512 MiB host even isolated very
large image sources may exceed memory; Render usage should be monitored
with real campaign attempts before claiming a universal guarantee.

## V64 — Workshop Showcase promo poster (user-provided reference)

The **Price Promotion** poster now has a selectable, reusable on-site design
based on the supplied portrait Laser Tools workshop poster. Unlike displaying
a placeholder image, this is an actual dynamic Pillow renderer that inserts
each official Laser part's genuine manufacturer photograph, product name,
validated UK RRP/VAT status and source-backed selling facts into a recognisable
professional automotive-workshop composition.

**Reference-inspired layout**: Laser header/part-number lockup, dark workshop
context, generous hero-tool space on a metallic bench, three modular
technical/feature panels, a kit-contents panel **only when the product source
explicitly lists contents** (otherwise 'Product details'), a bold blue
UK-price enquiry graphic, and a Laser footer with a draft-review notice.

**AI still directs designs**: the existing generative creative direction
determines the secondary colour treatment, workshop photographic focus,
graphic accents, product scale and one of three candidate variants. The
composition follows the reference but isn't an uneditable repeated JPEG.
The other two posters retain their separate technical/application and
third-angle AI composition choices; all six native marketing formats still
have independent AI direction and quality checks.

In Dashboard > **Distributor branding, product lookup and pricing settings**
choose:
- `Workshop Showcase — your reference, with AI variations` (default).
- `AI Original — unrestricted brand-safe composition`.

This selection affects **only poster 02 (Price Promotion)** in one-click
campaigns, with the exact choice recorded under `manifest.promo_template`.
The selected renderer works when Gemini succeeds and when the source-safe
fallback is necessary. It is visible on the price-poster asset card and
included in the normal nine-PNG ZIP.

**Safety**: the reference is a *layout*, never a source for product facts.
No invented kit contents, vehicle applications, pricing, VAT or AI-redrawn
product. Missing RRP displays 'Price on request'. Unsupported product
photos, cutout failures and clipping still fail the original source/visual
QA rather than slipping into a completed public campaign. All artwork
remains a draft requiring staff review.

## V63 — Source-photo selection rescue (Laser 4554)

The 4554 screenshot showed the exact genuine Laser tap-and-die set but
**0/9 artwork** due to `Source product image is too small for professional
poster artwork`. The existing selector could stop after just three
technically valid but undersized catalogue photos, and would only inspect the
real official PIS PDF if it found **no** image at all. As a result, a genuine
low-resolution thumbnail was prematurely chosen, then the freeform poster
quality gate correctly rejected it.

V63 fixes **image selection** rather than bypassing the quality gate:

- Review up to **12 approved exact-part official photo URLs** in bounded,
  concurrent batches. Stop early only for an actually passing 650px+ source,
  not a merely valid thumbnail. The chosen photograph must pass the existing
  text-free source-image preflight (dimensions, real visible edge detail,
  authentic cutout, white-halo and clarity checks).
- Parse every manufacturer gallery `srcset` entry, `data-original`, zoom,
  full and large photo URL. A 1200w authentic source is checked before a 320w
  version. Never fetch a domain outside the approved Laser Tools domains.
- When the best manufacturer JPEG still **fails**, examine the genuinely
  embedded image in the exact-SKU official PIS PDF. Compare with the verified
  original photo using the exact same quality test and keep the best **actual
  manufacturer source**. No AI-redraw, pixel extrapolation or artificial
  enlargement is used to fake a passing image.
- Preserve detailed photo-selection diagnostics (`photo_source`,
  `quality_passed`, actual pixel dimensions, source URL, number of
  candidates checked, PDF rescue status and failure issues). Low-quality
  images can remain in the dashboard for context, but **will not be released
  as professional poster art** if no acceptable original can be located.
- Keep language, UK RRP, genuine-product, artwork-quality, competition and
  three-concept checks intact.

A strict regression simulates part **4554** with *three undersized original
photos followed by a full-size original*, and a second case where only
the verified official PDF embeds a sufficiently large genuine image. The
whole nine-asset marketing pack continues to use the existing approval gate
after image selection; if a source genuinely has no acceptable pixels, the
site remains clear that a better manufacturer master is required.

## V62 — Dutch source-language leak prevented (Laser 7845)

A UK campaign for Laser 7845 showed untranslated Dutch:
`Vierkante doorsnede van 16 mm, gebogen kop van 25°.`

**Verified primary source:** The official English Tool Connection product listing
at `https://www.toolconnection.co.uk/products/general-hand-tools/striking-tools/pry-bars/heavy-duty/7845-pry-bar-900mm`
explicitly gives a `16mm square section 25° angled head`. V62 prioritises
that official UK page by exact part number.

For a cached PDF or a temporarily unavailable UK page, the same very
specific, source-preserving Dutch **numeric measurement pattern** is
translated to `16 mm square section; 25° angled head.` (the two source
numbers and their units are not altered). Unsupported Dutch technical or
promotional sentences are **rejected**, never creatively translated into
new features or selling points. The high-confidence Dutch vocabulary
detector now covers short descriptions such as `vierkante doorsnede` and
`gebogen kop` even when statistical language identification fails.

The last-line normalisation remains in initial campaign generation,
copy previews, the five newer copy goals (including Check English & facts),
PDF-source fallback, and server-side product-data parsing. No pricing,
customer logos, product imagery or quality gates were changed.

**Important:** Existing saved copy is not rewritten without the user's
consent. After deploying V62, regenerate 7845 or press Check English &
facts in the editor, inspect the source-backed suggestion and Apply.

Regressions test the exact Dutch sentence, untranslatable Dutch claims,
independent French/German translation, genuine English manufacturer URL,
all three initial angles and every rewrite/channel combination, as well
as absence of false positives on normal English workshop descriptions.

## V61 — British-English Marketing Copy Studio (part 7823)

The copy editor no longer presents overlapping "more professional / more
persuasive / more technical / rewrite for Facebook" buttons alongside social
and LinkedIn channel selectors. It now separates **three independent choices**:

1. **Selling angle:** the three source-verified application, price and benefit
   campaign directions from the full campaign;
2. **Publishing channel:** social, LinkedIn, email and website, with short
   messages and hashtags in a collapsible "Other formats" section;
3. **Writing goal:** Short & sharp, Stronger opening, Lead with evidence,
   Invite enquiries. Optional "Writing for" selects workshop technicians,
   trade stockists/distributors or retail customers. A separate **Check
   English & facts** action regenerates stale/bilingual copy from the official
   source instead of blindly translating user-created marketing claims.

The initial channel drafts are also differentiated by purpose: price/product
enquiry, manufacturer-backed benefit and workshop application. Rewrites are
draft previews: apply/discard/undo remains, original ZIP is unchanged.

**7823 French language regression:** The exact screenshot fragment
`Longueur : 120 mm, profondeur interne : 93 mm.` now converts to
`Length: 120 mm. Internal depth: 93 mm.` only when complete known numeric
labels and their literal source numbers/units match. Supported French numeric
spec rows are translated the same way. Any unknown/non-numeric French
marketing claim is rejected instead of guessed or silently promoted.
Original raw source text remains audit-only; it is not used as marketing
copy.

The AI planning model is still allowed to choose only enumerated structure,
hook/CTA and verified source fact indices. It cannot supply arbitrary prices,
product claims or vehicle fitments. Legacy API rewrite modes remain supported
for older clients, but they are removed from the new UI to avoid redundancy.
The campaign angles are correctly mapped (application/technical, price-led,
product-specific) when rewriting.

All work requires manual review and company approval before publication.
Existing campaign images, competitor research, customer branding, price/VAT
logic, and poster-quality safeguards remain unchanged.

## V60 — AI has more visual freedom across ALL nine assets

The 9197 screenshot showed nine complete marketing assets still dominated by
the same dark navy backdrop. V60 corrects the rendering layer rather than
just asking the model for more creativity.

- **AI-owned design choices:** the existing single Gemini planning call can
  now choose creative_palette, visual_treatment, text_treatment and
  hero_treatment for each original poster and each native-format artboard.
  Supported looks include laser blue, safety yellow, cyan, silver slate,
  graphite orange, electric violet and workshop teal; cinematic photography,
  high-impact geometry, editorial/split composition, minimalist composition
  and technical infographic treatments. These choices alter **actual
  large-scale artwork pixels** rather than simply renaming style metadata.
- **Different poster concepts:** technical/application, price-led and
  third-angle each receives its own composition, coloured typography details,
  price treatment and genuine hero-photo presentation. Repeated model colours
  are visibly diversified without moving the model's protected text/photo
  zones. The modification remains auditable.
- **Different social + website art:** native square, Story, website banner,
  email header, LinkedIn graphic and landscape advert each receives its own
  AI-authored palette and composition when provided. If a model repeats the
  same colour on three or more assets, the renderer selects a safe different
  palette. Default native-format colours are deliberately varied.
- **Different fallbacks:** a text-zone failure or temporarily unavailable
  Gemini can no longer cause all six formats to look like the original navy
  format. The separate legacy fallback renders the same approved genuine
  Laser photo under its own colourful backdrop and contrast-safe text panels,
  always labelled as a fallback.
- **Immutable essentials:** verified manufacturer product pixels, protected
  Laser logo/footer, customer branding, source-locked facts, English-only
  copy, UK RRP/VAT treatment and all pre-existing cutout, placement, text
  bounds, quality and visual review gates remain in force.
- **Audit:** the completed asset gallery shows real palette/visual choice,
  while the Campaign Manifest records one creative palette per asset.
  No arbitrary model CSS, external photo URLs or invented hardware/claims
  are accepted as art instructions.

These are still **drafts requiring human review**. Tests establish actual
pixel changes and the preservation of source/photo/copy constraints, not
an aesthetic guarantee for every part or an independently verified production
Render deployment.

## V58 — Competitor Finder: genuine photos, direct product links and broader coverage

Previously the comparison table had no `image_url` fields, and the backend
searched three restrictive phrases with only eight source-page checks. This
could leave almost any non-endoscope Laser part with zero visible alternatives.

V58:
- Extracts product photos from verified retailer/manufacturer `Product`
  JSON-LD and declared `og:image`/Twitter product hero metadata; trusted
  Google Shopping thumbnails are supported when the optional Shopping
  service is configured. A photo is NEVER synthesised or inferred from a
  product title. If unavailable or blocked by the merchant, the UI says so.
- Adds clickable photos, **View competitor product** links, explicit search
  lead labels, photo provenance, direct product URLs and image URLs in CSV.
- Broadens manufacturer terminology for bearing kits, LED under-bonnet lights,
  ratchets, hydraulic presses, split hub spreaders, torque-spanner tools,
  injector test tools, and further derived official-title types. Terms are
  SEARCH/MATCH HINTS, never interchangeability certifications.
- Supplements the optional UK Shopping feed with five varied web queries,
  public RSS and a second HTML search fallback; checks up to 18 distinct
  live approved product pages concurrently. Curated **manufacturer page
  pointers**, publicly verified in November 2026, cover several common
  tool families. Seeds must be fetched and validated live before display.
- Never invents a missing competitor part number, technical fitment,
  image, GBP price or VAT basis. Product images have an HTTPS host allowlist,
  no arbitrary browser/proxy fetch, and a safe broken-photo placeholder.
  Search-only index leads display no guessed photo/price/SKU.

**Coverage depends on the runtime environment.** Without `SERPAPI_KEY`,
the app uses public keyless search + trusted brand pointers. Public search
and retailer websites sometimes block server requests; configuring
`SERPAPI_KEY` in your Render environment (never in frontend/GitHub code)
enables structured UK Shopping results and more reliable picture listings,
but still does not guarantee competitors for every Laser SKU.

Tests include real source-markup extraction with mocked merchant pages and
eight varied Laser-style part numbers. These prove search-path coverage, not
that the publicly hosted site currently lists any particular alternative.
Check all live prices and manufacturer applications before publishing.

## V57 — Actual visual differentiation, not nine resized clones

V57 addresses the 9/9 campaign screenshot that showed essentially the same
navy design across every format. AI-authored layout coordinates previously
reached Pillow, but the brand renderer flattened the artwork to a uniform
colour/hierarchy, while unapproved native artboards fell back to a common
generic style.

**Three deliberately different sales narratives** remain mandatory:
technical/application, price-led promotion, and a source-backed category-specific
third benefit. A single Gemini concept request can select one of six branded
creative families per poster: `engineering_grid`, `commercial_burst`,
`premium_spotlight`, `workshop_motion`, `editorial_split`, or
`toolkit_coverage`. Each produces genuinely different background architecture
and product framing, behind the **unchanged official manufacturer photograph**.

The server validates all creative choices. It checks for repeated family
choices, repairs collisions with a **labelled** safe style correction that
preserves the original Gemini geometry, requires factual proof, and prefers
different source-supported promotional headlines. Model slogans unsupported
by the exact manufacturer record are discarded. Technical, price, benefit,
headline/proof and hero emphasis are explicitly represented.

**The other six canvases inherit different parent angles**, while the AI can
still choose individual format-specific geometry and backgrounds:
- Social square and Story: normally price-led
- Website and landscape banners: normally third-angle/product
- Email and LinkedIn: normally technical/application

Format inheritance can change within a safe enumerated mapping, but all
three parent marketing roles remain present. Even when an AI format cannot
pass text/photo QA, the separately labelled verified-native recovery
now uses its own inherited family and source-verified headline, rather than
repeating the same generic blue artwork.

**Quality and audit:** Campaign poster QA tests actual text fitting, verified
genuine photo pixels, source-backed claims, RRP/VAT, distinct composition
families, layout variance, pixel difference and perceptual image hash.
Native-format text remains bound to the model's safe zones and receives
contrast protection behind bold designs. A failed quality check cannot
be hidden behind the word `AI`, nor can an unapproved graphic enter a ZIP.
The gallery surfaces family, parent role, headline strategy, proof strategy
and whether an asset used a fallback renderer.

Nothing here constitutes automatic approval for publication; verify all
application/price statements, distributer branding and artwork before
sharing. Local tests check deterministic render behaviour, not aesthetic
quality on every possible real tool SKU or the current Render deployment.

## V55 — Demo reliability: Instagram Story text recovery and distinct AI art direction

The production LASER 9469 job returned 5/9 assets and rejected `social_story`
with `Verified copy does not fit AI-designed text zone`. A full campaign
must not abort simply because the AI chose an impossibly small text box.

- AI still controls freeform coordinates, background, scene, colours, style and
  shapes for every poster and native social/banner format; actual manufacturer
  photos, product facts and RRP stay source-locked.
- Native graphics try the two original candidates at normal quality. **Only
  if both fail** are two additional layouts rendered with genuinely smaller,
  measured typography, and an alternative **complete, exact** source-backed
  headline/feature where it physically fits. No ellipsised technical claims.
- If the AI's chosen Story/square/banner geometry remains unusable, use the
  existing independently drawn native format with the original verified
  product cutout and check its true dimensions, source-image quality, white
  background coverage and contrast. Declare its render engine
  `verified-native-recovery` in the manifest, not AI-original.
- Never stop before separately approving posters just because an independent
  native format cannot be repaired. Individual approved PNGs remain accessible
  on partial failure. The ZIP only appears when **all nine** are complete.
- Give the three AI poster roles more distinguishable visual language:
  technical precision rails, energetic price-led sweeps, and a premium
  product spotlight. Each is layered behind the AI's actual freeform zones
  and never alters the tool photograph.
- Regression tests include the long-copy Story failure and end-to-end 9/9
  approved pack, honest fallback labelling, rejected recovery security, no
  trapped poster assets, measured typography and branded role distinction.

**For a demo**: after the latest deploy, hard-refresh, enter part 9469, build
the campaign, and save the ZIP as an offline backup. Do not claim that local
automated regression tests guarantee the live model or the hosting instance
will complete; review the returned designs and source facts before presenting
them as final collateral.

## V54 — Fix the real cut-off-text failures and protect independent campaign assets

A live report showed that the AI visual critic repeatedly rejected the third
product poster for `cutoff_text`. Previous repair attempts changed only
background lighting and photo scale, *not any words or text boundaries*.

- The poster renderer now checks the **actual painted glyph extents** before
  drawing each line, including ascenders/descenders and text-zone limits, and
  refuses a line that does not fit.
- When independent review flags clipped or unreadable copy, repair levels
  now **really reflow the copy**: typography gets progressively safer, the text
  is inset from zone edges, and the final review footer is farther from the
  poster's lower boundary. The factual copy is preserved verbatim.
- A persistently rejected AI artboard can be replaced for the affected role
  only by the existing, independently quality-tested alternative renderer.
  It still has to pass geometric asset checks, an actual independent image
  review, and the three-poster distinctness gate. This recovery is
  **explicitly labelled** `Verified-safe recovery` in the manifest and
  angle report, never misrepresented as a model-authored artboard.
- The six native social, story, website, email and landscape graphics are now
  rendered with their **own** quality checks before the poster batch's final
  visual critique. A failing poster can no longer hold back independently
  approved native assets. A complete ZIP remains unavailable unless all nine
  checks pass. No partial failure is called a complete campaign.
- Real manufacturer pixels, verified part numbers/facts, actual RRP/VAT labels,
  mandatory English text, no invented context photos, and human approval
  remain essential. Known source-image defects still block approval.
- Regression tests cover actual rendered text movement (not just mock retry
  counts), bounds checking, safe alternative approval, six approved files
  surviving an unrecoverable poster, and zero unapproved poster releases.

No guarantee is made that Gemini's subjective image critic will always
approve every product. Server-side user-facing reasons remain specific.

## V52 — Interface cleanup and more reliable completed campaigns

This fixes two observed problems. The earlier hero image used absolute
positioning and could cover the competitor panel and status text on desktop;
a real campaign also generated successfully but its image requests later
returned HTTP 404 after its short-lived in-memory files expired or a new
Render instance replaced the old one.

### Layout
- On wide desktops the hero text, product search, competitor research,
  progress, recovery and pricing settings stay **inside a dedicated 72%
  content column**, separated from the real manufacturer photograph's
  28% display column. The background photograph never sits over actual
  controls or comparison results.
- At narrower desktop/tablet/mobile widths the hero photograph is hidden
  and all content gets the full available width.
- Poster cards, marketing angle headlines, copy controls, navigation,
  search buttons and table cells now wrap naturally. Artwork still uses
  `object-fit: contain` and is never cropped to solve a UI issue.
- Responsive layouts remain single-column on small phones, with accessible
  focus outlines and working horizontal scroll inside genuine data tables.
- CSS asset revision is bumped so Safari fetches new styles.

### Campaign reliability without sacrificing quality
- Real completed campaign pack tokens now stay valid up to **45 minutes**
  instead of 15, subject to free hosting instance restarts; active job
  progress records remain for up to 55 minutes. Storage remains strictly
  bounded to four in-memory complete packs.
- As quality-approved PNGs arrive, the current browser tab saves copies
  using standard Blob URLs and substitutes them for expiring remote links
  in preview, open, download and share actions. On successful completion,
  all remaining PNGs (including the optional source QR) are also fetched
  even if off-screen, avoiding failures on later lazy scroll.
- The **complete ZIP** is fetched only after all artwork checks have passed.
  Its actual ZIP signature is validated and a temporary browser-tab copy
  is offered through the same Download ZIP button. No automatic download,
  fabricated images, early ZIP, reduced-resolution render or QA bypass.
- Intermittent GET progress-poll failures (network errors, retryable server
  responses) now retry with visible feedback while the *existing* job
  continues. Repeated failures preserve the Reopen Campaign option.
- Repeated Build clicks for an already-running part recover that job
  rather than launching a duplicate; a busy server responds with
  transparent, bounded start retries instead of an unexplained failure.
  Users can still deliberately generate a fresh campaign after the
  previous job is complete.
- Expired, unavailable server artwork now carries a clear explanatory
  message instead of silently displaying broken image cards.

**Limitations**: Render's free instance memory is not persistent across
deployments, restarts or devices. Temporary local Blob copies last only
while the current tab remains open. Always download the complete ZIP for
permanent retention. A truly durable shared campaign library requires
a persistent database/object store, which this update does not claim to
provide.

Regression tests: `python -m unittest -v
test_interface_reliability_v52.py`, plus the entire existing campaign,
quality, English, VAT, mobile, competitor and dashboard JS checks.

## V51 — Universal competitor search for every official Laser part number

The previous competitor finder recognised only a small hardcoded list of
tool categories. An official Laser product outside that list failed before
searching. The new flow **accepts any valid official Laser product record**:
it first applies known high-confidence category/alias rules, otherwise
derives a bounded product-type **search hint from the official UK product
title**, and performs broad brand-neutral searches. No fabricated category,
model or competitor is presented as manufacturer fact.

- Every recognised part with a valid official product page now enters the
  search pipeline; an unfamiliar category returns source-backed results,
  explicitly unverified search leads, or an honest empty result with
  warnings—not an unsupported-type HTTP 422 error.
- Search terms are adapted to the individual product. For title-derived
  categories, the search looks for generic UK workshop products,
  alternatives and trade distributors instead of requiring a specific
  predefined competitor brand. Existing specialist camera, bearing and
  vehicle coverage is preserved.
- Existing HTTPS source-host protections remain. Known-brand matching still
  works; **additional manufacturers** can be reported from a verified
  product's structured `brand` field or an authorised Shopping listing,
  without adding them to the source-code brand list. An unverified brand is
  explicitly labelled rather than invented.
- Product titles are conservatively matched by distinctive, shared tool
  nouns and exclude irrelevant replacement accessories. For previously
  unknown categories, the result is labelled **Related product — verify
  technical equivalence**; matching text is NEVER evidence of identical
  fitment, capacities, drive sizes or kit contents.
- Search engine indexed links on approved retailer/manufacturer HTTPS
  hosts may appear when the actual page cannot be inspected; these are
  labelled **Search lead — verify manufacturer page** and always have no
  verified part number or price. The UI and CSV distinguish such leads from
  source-checked product results, so quality standards remain intact.
- Verified GBP prices, seller, VAT basis, listing condition and links remain
  separate from Laser's genuine manufacturer RRP. Missing or unavailable
  prices are never inferred, and no imaginary physical tool photos appear.
- Tests span wheel-bearing kits, endoscopes, ratchet sets, under-bonnet
  lamps, split-hub spreaders, test kits, extractors, compressors, crimpers,
  specialist calibration targets and unknown product families. They
  explicitly verify no unsupported-category errors, unrelated-tool
  rejection, cross-brand product metadata and empty-result handling.

**Important limitation:** This guarantees a *search attempt*, not a
directly interchangeable alternative or a published UK price for every SKU.
Free web search is inherently best-effort. Add optional `SERPAPI_KEY`
for more reliable UK shopping price coverage; absent source evidence is
reported honestly. Individual technical equivalence still needs human
review before publication. No existing poster generation or visual QA
checks have been changed.

Regression tests: `python -m unittest -v test_competitor_finder_v51.py`
plus all prior CI tests.

## V50 — Inspection camera competitor discovery and source-backed pricing

Fixes the specific **Laser 9195 Portable Endoscope Camera** failure.
Previously the strict tool type table did not recognise **endoscope** or
**borescope**, so research stopped with HTTP 422 before searching.

The finder now groups inspected endoscopes, borescopes, videoscopes,
snake cameras and visual inspection devices into the **inspection camera**
tool category, while retaining conservative category matching and rejecting
unrelated diagnostic scanners, chargers and tool accessories.

**Snap-on added:** both Snap-on UK and Snap-on Store product URLs are allowed,
alongside verified UK Sealey and Draper stockists. Search queries use useful
synonyms and Snap-on/Sealey/Draper models; audited manufacturer and seller URLs
are fetched as real source pages even when the free RSS provider is down.
No seeded item or price is returned without source-page evidence.

Verified source-backed examples for inspection-camera discovery include
Snap-on BK7000 (UK dealer price may not be published); used Snap-on BK5500
marketplace listings (explicitly marked used); Sealey VS8118 video
borescope and Draper 92578. UK retailer prices are accepted from correctly
linked GBP Product structured data or a tightly limited, visible current
offer ("Our Price", "Guest Price", "or Best Offer") on approved shops.
Historic RRPs, shipping charges, other currencies and unverified
Snap-on dealer quotes are never used as actual live prices.

The UI and comparison CSV display **listing condition**. Users can see
if a Snap-on figure is a used marketplace asking price rather than a
new-tool RRP. Broadly comparable inspection cameras are *not* claimed to
have identical swivel or dual-lens functions: validate head articulation,
probe diameter, screen, image quality and supplied accessories.

Tests: `python -m unittest -v test_competitor_finder_v50.py`,
plus the existing V49 competitor and entire poster/QA/mobile suites.

## V49 — AI Competitor Finder: source-linked UK alternatives and prices

The product search bar now has **Find Competitors & UK Prices**. Staff enter a Laser part number to open an independent comparison panel, preserving every existing poster and campaign feature.

- Retrieves the genuine official UK Laser record first; only its product title, type and named vehicle applications inform matching.
- Default keyless discovery searches Bing's public RSS results and checks actual external product pages on a strict HTTPS UK retailer/manufacturer allowlist. Competing product names, brand/part numbers and GBP offers come from retailer Product/Offer structured data, not generated text.
- Optional SERPAPI_KEY in the Render server environment enables extra Google Shopping UK listings and advertised GBP prices. The key is never exposed to visitors. Price source is always displayed and is never mislabelled as the competitor manufacturer's RRP.
- Common competitor manufacturers include Sealey, Draper, BGS, Gedore, Sykes-Pickavant, Schaeffler/FAG, KS Tools, etc. Laser-branded and unrelated tools are excluded.
- Match statuses are explicitly qualified: likely equivalent (verify technical details), potential alternative (application coverage differs), similar tool (specifications or fitment unconfirmed). Never claims certified interchangeability.
- Existing GEMINI_API_KEY can optionally run a **conservative downgrade-only match review** on the externally verified candidate titles. The AI cannot upgrade a match, invent a competitor, create a new price, invent technical advantages, or replace the photo.
- Verified UK price, seller, source link, part number where available, check time and VAT basis are reported. VAT is marked unknown unless independently established. Unavailable prices are never guessed or converted from foreign currencies.
- Refresh prices bypasses a 20-minute in-memory cache. Export comparison CSV makes an Excel-compatible list with source links, timestamps, qualifications and spreadsheet-formula injection protection.
- No pricing provider or accessible sources? The page shows explicit no-verification warnings rather than fake competitor results. Bing RSS is an unversioned, keyless public feed and may be blocked or change without notice; structured shopping providers need valid accounts.
- Only approved HTTPS destinations can be fetched; redirects and non-GBP prices are rejected. No scraping or AI modification of manufacturer photography. Human staff must compare vehicle generations, kit contents, capacities and VAT basis before any customer claim.

Server routes: GET /api/competitors/<part>, GET /api/competitors/<part>?refresh=1 and GET /api/competitors/<part>/export.csv.

Regression test: python -m unittest -v test_competitor_finder_v49.py. Full GitHub Actions suite also covers existing artwork QA, original product images, mobile progressive loading, English-only copy and exports.

## V48 — genuine progressive campaign generation (no quality shortcuts)

Full campaigns now **appear one artwork at a time**, on both desktop and mobile.
Each job returns immediately with an unguessable bearer ID. The frontend
shows nine separate queued/rendering/quality-checking/ready/failed cards,
polls its job and reveals each real finished PNG as soon as the original
quality controls approve it. Ready images can be opened or downloaded before
the full campaign is complete. A complete ZIP is only available when all nine
graphics and the manifest/review files have been generated successfully.

**Quality is unchanged:** the three original posters are withheld until
the existing batch distinctness and AI visual-critic review passes. A poster
rejected for clipping, white borders, blur, illegible text or duplication is
never streamed as ready. Subsequent square/Story/website/email/LinkedIn/
landscape artwork is emitted after that format's normal approved render and
quality selection; failed assets are recorded individually. A failed format
does **not** erase prior quality-approved images, but it **does** block the
full ZIP. This is progressive delivery, not a faster lower-fidelity mode.

Server: `build_campaign(..., progress=callback)` emits trusted stage and
validated PNG events; the existing synchronous API continues to produce
identical archives. The bounded background job stores temporary bytes only
until its normal complete pack is available, then releases duplicate RAM.
`GET /api/campaign/jobs/<job_id>` reports only statuses and counts.
`GET /api/campaign/job-assets/<job_id>/<asset_id>` serves only approved
PNG bytes to the bearer token, with optional `?download=1`. No partial ZIP,
product artwork URL injection or unapproved renders are exposed.

The browser uses the same resumable jobs for mobile and desktop. It maintains
nine persistent cards without reloading existing PNGs on every poll and makes
clear which assets have not passed review. Existing 15-minute retention and
worker-restart limitations still apply; Redis/Postgres would be needed for
durable, cross-worker recovery. No extra image quality sacrifices, source
modifications or skipped visual checks are introduced.

Tests: `python -m unittest -v test_progressive_campaign_v48.py`, plus the
existing entire CI suite and Node JavaScript syntax checks.

## V47 — mobile full-campaign reliability, Safari recovery, and accurate previews

The iPhone Safari live log showed that a complete campaign API request returned
HTTP 200, but its browser never requested the finished asset images. The first
three standalone poster previews were visibly available, causing confusion
about whether the entire campaign had been generated.

**Fixes**:
- The dashboard previously forced `.asset-workspace .previews` to
  `display:grid`, overriding the HTML `hidden` attribute. When a complete
  campaign appears, those three *basic* previews now actually disappear.
- Quick previews are labelled **preview only**, with a prominent **Build All 9
  Graphics** button. The complete pack clearly counts all nine graphics and
  distinguishes image loading/retry from generation.
- iPhone / Android / narrow viewport users start a background rendering job,
  get a short-lived job token immediately, and poll for completion. A long
  Safari POST no longer has to remain open throughout image generation.
- A short-lived session-only recovery record lets staff reopen an interrupted
  campaign or an in-progress job using the Reopen Campaign control. The server
  serves the existing pack instead of running Gemini again; expiry and
  unguessable token checks are enforced. No permanent user data is retained.
- The gallery is rendered *before* the optional copy editor and sharing
  controls, so accessory UI errors are less likely to leave just the
  quick previews visible. On mobile, the gallery is single-column with clear
  progress and retry feedback for individual image loads.
- Share files are fetched on demand only after tapping the share action.
  Eagerly preloading the campaign ZIP and every individual PNG on iPhone could
  increase browser memory pressure enough to interrupt displaying the gallery.
- Existing synchronous desktop / API route remains compatible and unchanged
  in response format. When a source photo or poster fails QA, the app still
  reports the failure rather than claiming that the missing artwork exists.

The mobile asynchronous job service is bounded to two active jobs per single
Render worker and uses short-lived in-memory state; worker restarts may
invalidate an unfinished or saved job. Full persistence requires a database.

Regression tests: `python -m unittest -v test_mobile_campaign_v47.py`.

## V46 — original AI artwork for every campaign format

The single `Build Campaign` request now asks Gemini to develop **six additional
independent creative canvases**, instead of deriving them from the three
1200×1500 posters: **1080×1080 Instagram/Facebook square**, **1080×1920
Instagram/Facebook Story**, **1600×600 website banner**, **1200×420 email
header**, **1200×627 LinkedIn graphic** and **1600×900 landscape advert**. The six native canvases are planned for their own reading and
attention patterns, including mobile Story UI-safe areas and concise
horizontal banner compositions.

`format_creative.py` validates the model's free-position headline, source
product, optional manufacturer proof, and optional verified price zones, plus
up to eight decorative vector shapes. It also accepts a role for the
official product headline, an exact verified-feature index and a choice
among existing approved context scenes. All text and product pixels are
inserted by the server; the model cannot pass arbitrary slogans, photos,
vehicle fitments, URLs, customer logos, prices or publication claims.

Each format is rendered **at its final native pixel dimensions**, never
cropped or resized from a poster. The actual manufacturer tool is isolated
conservatively and composited untouched onto a non-white design. Two
variations are checked for clipping, hero prominence, white-background
contamination, image integrity and contrast; both failing rejects the
AI artwork rather than quietly exporting unsafe output. Unavailable or
invalid AI canvases use the existing clearly labelled verified-layout
fallback. The ZIP manifest now includes separate `ai_format_canvases`,
`format_artwork_quality`, and per-format engine status. The dashboard
shows the number of genuine AI-original formats, rather than claiming all
formats were AI-directed when they were not.

Existing freeform poster creativity, genuine image QA, copy safeguards,
approval notices, editor and download paths remain in place.
Regression tests: `python -m unittest -v test_ai_formats_v46.py`.

## V45 — freeform AI creative director, genuine-image gates and visual review

**Build Campaign** now asks Gemini, in its existing campaign concept request, to
invent the **actual 1200×1500 compositions** of all three poster roles. The model
chooses each headline, genuine product, proof and price zone using arbitrary
0–1000 artboard coordinates; mood, background, photo focus, accents and motif
are also model-directed. A new Pillow renderer (`flexible_canvas.py`) builds
those model-authored placements without switching to the old family templates.

The renderer itself **never accepts model-created product imagery or claims**:
it uses the exact official tool photo, server-verified price, approved real
workshop contexts and manufacturer feature strings. Branding and publication
disclaimer occupy fixed safe areas. Every AI text zone must be large enough,
stay within margin bounds and avoid collisions. If unsafe model geometry is
returned, the existing documented legacy composition fallback is used and
explicitly marked rather than falsely called AI-directed.

New source-photo preflight (`asset_quality.py`) rejects undersized / blurry
product originals, unreliable white-background isolation and severe cutout
fringes. Poster quality checks now evaluate real rendered coordinates,
headline fit, product prominence, excessive white backgrounds and contrast.
The new `creative_qa.py` can send a downsampled batch of the *three completed
posters* to Gemini vision for an independent, bounded visual critique; serious
defects trigger rejection, and repairable issues get one visual variation
re-render and one further review. When the critic is unavailable, its absence
is disclosed: only deterministic QA is claimed. Campaign-level distinctness
checks inspect composition signatures and rendered pixel difference before
delivery. Bad artwork is rejected, never silently exported as successful.

The ZIP manifest now contains creative-engine origin, input asset quality,
independent visual review status and three-poster distinctness report. This
version does not train on design taste or guarantee independent brand approval;
every campaign remains a review-required draft.

Run: `python -m unittest -v test_ai_creative_director_v45.py`

## V44 — product-specific creative decisions and direct poster editing

Five improvements build on the existing one-click campaign without creating a
second poster generator:

1. **AI creative direction that actually reaches the artwork.** The one
   Gemini concepts request can supply bounded layout variant, photographic
   focus, brightness mood, graphic motif, product scale and accent. The
   campaign maps the legacy retail/premium/trade proposals to the new
   technical/price/product-selected roles, validates every setting against
   approved choices, and gives the preferred composition a small priority
   **only if it passes objective QA**. When Gemini is unavailable, category
   and part-number-specific art direction is used transparently.
2. **Better real photographic context.** Multi-function workshop lamps use a
   curated automotive workshop/under-bonnet photo pool instead of generic
   engine/laboratory scenes. Verified manufacturer application photographs
   take priority for technical and product-selected posters when available.
   The system scores category match and rejects out-of-category context.
   Context photos are illustrative, not evidence of this exact product in use.
3. **Stricter visual QA.** Candidate checks now include source cutout safety,
   visible product size, presence of a headline, text-box geometry, clipping,
   excessive white canvas, contrast and scene relevance. Unsafe candidates
   are rejected. For acceptable candidates, quality selection can favour
   Gemini's chosen composition when scores are close.
4. **Function-first evidence.** `product_evidence_ranker.py` ranks only
   manufacturer-verbatim features by role and category. For work lamp 9476,
   the verified fan/lighting functions outrank dimensions and weight; timing
   kits foreground timing jobs, ratchets their actual drive/contents and
   presses their confirmed capacity. Unsupported benefits never enter copy.
5. **Edit one poster, not the whole campaign.** Each of three images has an
   Edit poster control. Users can shorten the headline *only as a contiguous
   excerpt of the verified manufacturer's product name*, select from genuine
   product feature entries, and choose a preapproved layout. The tool
   re-renders that single image and updates its preview, PDF summary and ZIP
   **without calling Gemini again**. Price, VAT, applications and product
   photo are locked. Copy Editor drafts and other posters remain unchanged.
   This editor is intentionally available only during the existing 15-minute
   campaign session.

All outputs still require technical/company approval. This is product-aware
AI-assisted decision support, not an autonomously trained advertising model,
and automatic visual QA cannot substitute for a human design review.
Regression tests: `python -m unittest test_creative_editor_v44.py`.

# Laser Product Studio

## Premium product-specific campaign artwork and automatic QA (V42)

The one-click campaign now generates multiple **genuine** artwork candidates
per role (technical, price promotion and product-selected) and selects the
best passing variant using objective image and geometry checks.

- **No giant white product cards:** Technical and product-selected posters
  now composite original manufacturer tool pixels onto polished, dark,
  category-relevant workshop art. Square social images, Stories and
  web/email banners use the same manufacturer cutout engine instead of
  pasting an unprocessed white product photo.
- **Cutout quality:** Uses the existing conservative manufacturer_cutout
  engine (connected-white background removal, antialiasing and halo
  cleanup, white product components preserved). If a white-background
  photograph cannot be isolated with confidence, the campaign is blocked
  from publication rather than inventing product pixels or exporting a
  misleading white rectangle. Supply a cleaner official photograph.
- **More restrained price posters:** Short manufacturer-sourced headlines,
  one prominent real product image, verified price, reduced/repeated
  copy and multiple balanced price treatments. Never invent an RRP.
- **Role- and product-aware layouts:** Technical layouts differ from price
  promotions and the smart third creative, while candidate layouts vary
  by manufacturer product category and part number.
- **Real workshop context:** The three posters use category-specific
  photos from the existing real/licensed context library, with source
  and licence attribution preserved in the campaign manifest.
- **Automatic QA:** Reject invalid dimensions, large near-white dead
  areas, flat/low-contrast posters, overflowing text, unsafe cutouts
  and duplicate campaign roles/facts. Three candidates per role are
  scored and the strongest acceptable one is included in the pack.
  The dashboard shows the QA outcome, warnings and candidate count.
  QA is an objective guardrail, not a guarantee of professional design
  or automatic verification of any fact/vehicle application.

The genuine manufacturer photo, reviewed price data, source citations,
single copy editor, stories, individual social sharing and optional ZIP
download are retained. Human approval is still required before external
use. Tests: `python -m unittest test_campaign_visual_quality.py`.

## One Build Campaign: three different posters (V41)

The public website exposes ONE campaign generator, Build Campaign. The
separate standard and AI poster generators are hidden from the normal
workflow. Legacy endpoints remain for compatibility.

Each verified part number yields:
- Application / Technical: source-verified purpose, use and specifications,
  genuine manufacturer photography, different editorial layout, not a large
  retail price tag.
- Price Promotion: bold promotional layout, real tool imagery, staff-reviewed
  price or honest price-on-request, distinct background and headline priority.
- Product-Selected: a different editorial layout emphasising a category-based
  third angle, such as timing-kit contents, bearing service, press capacity,
  lighting performance or EV electrical ratings.

The director plans different role, image, layout, palette, feature and focus
for each part number. It reads verified product facts and official category
data, not invented fitment. Gemini may select the third creative direction
from bounded product-relevant options during the existing concept request;
if unavailable, a labelled category-specific fallback is used.

When available, each poster can use a different real licensed contextual
workshop photograph or an official manufacturer application photo. The
actual product photograph is not AI-redrawn. If real context is unavailable,
the app uses a safe designed background rather than fake tool photographs.

The single campaign includes a social square, Instagram/Facebook Story,
website and email banners, three Instagram Story suggestions, one existing
copy editor with AI rewrite actions, individual downloads/native sharing,
and an optional ZIP with source/photo attribution and the campaign strategy.
No automatic downloads or publishing.

This is a product-aware AI-assisted planner, NOT an autonomously trained
sales model. All outputs require review.

Tests: python -m unittest test_unified_campaign.py

## Official category to marketing strategy mapping (V40)

The recorded Tool Connection Laser Tools website navigation hierarchy is
mapped to product-specific marketing strategies. Valid manufacturer product
URLs supply exact categories and subcategories ahead of title guesses.
A collapsible website category browser and GET /api/catalogue/taxonomy show
the category-strategy mapping.

Ten checked official product URLs are indexed initially. The application
classifies any other product when it locates its actual official product URL.
An authorised company part-number/product-URL CSV can populate the full
index via import_catalogue.py. See CATALOGUE_STRATEGY.md for sources,
matching rules, the CSV format, evidence checks and coverage limits.

## Engine timing tool recognition (part 6200)

The official Engine Timing Kit 6200 is classified as **Engine timing & locking
tools**, not generic hand tools. Title matching also covers camshaft locking,
crankshaft holding, cambelt tool kits and timing belt/chain locking products.

For this category, marketing strategy recommends relevant engine/timing repair
workshops and specialist distributors, prioritising documented applications,
timing operations and tool kit contents. Accessory cross-references such as
"see Laser Part No. 7595" are retained in the original manufacturer data but
excluded from primary poster selling points and Gemini's allowed evidence
choices. Technical specs, engine fitment and campaign claims remain sourced
and require review. Regression tests use the official 6200 product wording.

## Product-specific AI marketing strategy (V39)

The campaign builder now produces an explainable strategy, not just generic
promotional posters. It identifies the tool category from the official
manufacturer record, suggests possible audiences, chooses a lead marketing
angle, recommends channels and identifies a verbatim manufacturer proof point.
A specialist bearing kit can prioritise verified vehicle applications and
trade email; a ratchet set can prioritise documented set contents and social
marketing; a workshop press can prioritise confirmed capacity and technical
product listings.

The existing single Gemini concepts request can additionally choose among
strictly supplied audience IDs, sales angles, channel choices and manufacturer
feature indexes. campaign_strategy.py validates all selections before use.
Unverified claims, customer leads, fitment and prices cannot be introduced by
the AI plan. When Gemini fails or returns unsupported choices, the application
labels the product-aware rules fallback. No extra Gemini call is needed.

The new Recommended marketing approach panel explains who might buy the tool,
which channels may work best, why the recommended selling angle makes sense,
and which manufacturer evidence supports it. The recommended campaign angle
is highlighted and the selected proof is used in social/website/email graphics.
The strategy is included in Campaign_Manifest.json, the campaign PDF and the
Marketing_Strategy.txt export.

IMPORTANT: Suggested audiences are unqualified marketing hypotheses for the
trainee sales team to validate, not verified customer leads or order forecasts.
Technical and company approval remains required before publication.

Tests: python -m unittest test_campaign_strategy.py

## AI-assisted rewrite buttons (V34)

The single shared marketing copy editor now includes five quick rewrite styles:
**Make shorter**, **More professional**, **More persuasive**, **More technical**,
and **Rewrite for Facebook**.

Select an existing campaign direction and a written channel (Social, LinkedIn,
Email, Website or Short promo). Click a style to show a separate preview.
**Apply to text editor** replaces only the selected local draft. **Keep original**
discards the suggestion; **Undo last rewrite** restores the previous wording.
Edits survive tab switching until the user generates a new campaign or resets
the draft. Hashtags remain source-generated and cannot be rewritten.

The endpoint POST /api/copy/rewrite/<part> independently retrieves the
manufacturer product record and optional staff-reviewed RRP. Gemini, when
configured and reachable, selects only permitted presentation choices and
indexes into confirmed manufacturer features: the final copy is assembled
server-side from those approved factual elements. The existing draft is a
style reference only, never evidence for a product claim.

When Gemini is unavailable, the interface explicitly shows that it used
verified-source copy templates rather than claiming an AI generation.
A rewrite never silently overwrites the draft. Company review remains
mandatory. Edits in the browser do not yet change the original ZIP export.

Run: python -m unittest test_copy_rewriter.py

## Marketing Hub dashboard (V33)

The home page now follows the approved navy-and-yellow dashboard mock-up:
- Branded top navigation, compact left sidebar and a campaign-first hero search.
- **Generate Campaign** uses the original verified product lookup and complete ZIP builder.
- Honest quick facts (**3** campaign angles, **7** core graphics, **1** complete ZIP),
  with no invented user accounts, campaign totals, or saved records.
- Side-by-side campaign asset previews and **one** shared channel-specific copy editor.
- **Saved Promotions Library** is visible as **Coming soon**, not functional storage.
  Download the ZIP for any campaign you want to keep in the meantime.
- Original manual posters, detailed manufacturer record, reviewed-price controls and
  optional AI poster editor remain available through **Product Studio & advanced poster tools**.
- Responsive desktop, laptop, tablet and mobile layouts.

No backend migration, database or publishing permission is required by this UI update.
The hero sample photo is served through the genuine manufacturer-photo endpoint; it
is not generated or modified using AI.

## One-click distributor marketing campaigns

The landing page now includes a prominent **Generate Complete Campaign** action.
Enter a part number (for example `9395`) to create, in one request:

- 3 distinct price-, benefit- and application-led promotional posters using the
  genuine manufacturer product photo and verified specifications.
- Native Facebook/Instagram square graphic, vertical story, website banner and
  email header.
- Social caption, LinkedIn post, customer email, hashtags, website listing copy
  and a short customer message — with 3 source-grounded campaign directions.
- PDF summary, source record and official-product-page QR (when a trusted source
  URL exists) in a **single complete ZIP**.
- On-page graphic previews and copy buttons, with a repeat-download link.

Gemini chooses concepts when configured and accessible. If the AI API is unavailable,
the app **still builds an honest source-verified fallback campaign** instead of
failing the whole action. All assets are **drafts requiring company review**; the
app never sends or publishes anything automatically. Session preview/download links
expire after 15 minutes on the current single-worker Render free service.

See [MARKETING_CAMPAIGN_HUB.md](MARKETING_CAMPAIGN_HUB.md) for the UI map, outputs,
architecture, approval checklist and next development phases.


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

### V7 — five promotional-design upgrades (November 2026)

This update implements the five requested improvements **in order**, without adding a paid image-generation service. Existing manual posters, original manufacturer packshots, staff-approved distributor branding and verified UK price/VAT records remain authoritative.

1. **Automatic poster checks** (`poster_quality.py`): Records real text and image geometry during rendering rather than attempting OCR. Detects truncated headlines, cropped tool photographs, overlapping headline/price areas, missing RRP/VAT labels, incorrect poster sizes and suspicious unresolved white backgrounds. Automatically retries with safer tool scale/position or alternative composition; refuses designs which still fail mandatory geometry checks. Displays a design-check status on each AI poster, including manual-review warnings and any automatic adjustment. The visual editor retains the corrected layout and product placement.

2. **Gemini-directed layouts** (`promo_art_direction.py`, `ai_concepts.py`): One model call now suggests a validated layout variant, real-photo focal point and lighting mood, graphic motif, product scale/offset, accent, headline size and RRP treatment. These suggestions are restricted to approved choices and bounded numeric ranges. The renderer uses nine structurally different layouts (three each for Retail, Premium and Trade), then adds restrained shapes **behind** source photography and product content. Gemini cannot supply new product pixels, arbitrary image URLs or a replacement price.

3. **Better real background matching** (`promo_scene_library.py`): Added a separate wheel-hub/bearing category and verified car hub/wheel-service photography, improved authentic battery-charging and vehicle-diagnostic photo choices and automatic same-category stock-photo fallback when one source is unavailable. The original Laser Tools application photo still takes priority for Trade when present. Stock pictures are illustrative context and do **not** claim to demonstrate the precise Laser tool. Relevant photo sources remain reviewable.

4. **Different selling points for each poster** (`promo_selling_points.py`): Retail leads with the source-confirmed UK RRP (or PRICE ON REQUEST), Premium with a documented product benefit, and Trade with manufacturer-confirmed vehicle applications or workshop tasks. All featured proof points are selected verbatim from verified manufacturer features; if fitment evidence is missing, the software does not invent it. Campaign focus is shown in the output.

5. **More expressive RRP graphics** (`ai_cinematic.py`, `app.py`): In addition to the previous price bubble, white plaque, angular tag and banner, added a promotional starburst sticker, folded corner ticket and large split-colour price panel. Every style uses the exact verified price and VAT wording, supports PRICE ON REQUEST and remains adjustable through the editor. No fabricated reductions, discounts or VAT conversions.

Tests include `test_poster_quality.py`, `test_ai_art_direction.py`, `test_promo_upgrades.py` and the existing original-product-image / 8899 photo / browser checks; they run in GitHub Actions on each commit.

**Human approval is still required before external publication.** Automated QA finds specific detectable layout problems, not every possible visual-design or compliance issue. Only official product claims and approved/licensed photography should be used.


### V8 — AI promotional captions and customer marketing copy (November 2026)

**Generate with AI** now automatically supplies **four marketing formats for each of the three chosen poster concepts**:
- Short social media caption, focused on that poster's Retail (price), Premium (benefit), or Trade (application) angle
- LinkedIn post in UK trade language, with short relevant hashtags
- Product email with a copy-ready subject, short body and editable signature placeholder
- Relevant hashtags based on the verified tool category and confirmed vehicle mentions

A **Campaign Content** panel appears beneath the AI poster gallery. Users can switch between the three posters and four channel tabs, edit each draft independently, copy a single format or all four formats at once. Each poster card has a **Captions & email** shortcut. Edited posters regenerate their associated marketing copy from the official manufacturer record; drafts are never published automatically.

Gemini supplies the copy style, hook and CTA via the **same free-tier request already made for the three poster concepts**. The final channel copy is composed from the source manufacturer title, part number, verified manufacturer feature/application statements and reviewed price/VAT status. The app does not accept invented claims, discounts, unverified vehicle fitment, customer quotes, or arbitrary URLs from the model. Draft staff-entered RRPs remain clearly marked as draft; missing RRPs become **Price on request**, not a guessed price.

New modules: \`promo_copy.py\`; updated \`ai_concepts.py\`, \`app.py\` and \`static/styles.css\`. Regression tests in \`test_promo_copy.py\` cover all four channels, different campaign focuses, manufacturer/price tampering, missing VAT/price, safe brand hashtags, AI endpoint integration, editor regeneration and browser syntax.

**All generated copy is a draft requiring human review before sending or publication.** No posting/email-sending integrations or extra paid APIs have been added.
