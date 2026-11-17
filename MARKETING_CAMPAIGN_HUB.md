# Laser Tools — One-Click Distributor Marketing Campaign Hub

**Status:** Working MVP integrated into the existing Laser Product Studio. The legacy poster
builder, poster editor and original ZIP download remain available.

## Goal

A distributor or Laser Tools representative enters **one part number** and presses
**Generate Complete Campaign**. The system retrieves verified manufacturer data
and the *genuine* product photograph, selects three distinct marketing purposes,
renders native channel artwork, writes copy and delivers one downloadable ZIP.
It does **not** automatically post, email, schedule or publish content.

## Customer journey / page map

1. **Marketing Hub landing / product entry**
   - Part number (required).
   - Distributor logo (optional; presently three approved demo selections only).
   - Staff-entered RRP + VAT basis and manual review checkbox (optional).
   - Official UK product URL for that exact part number (optional).
   - One prominent **Generate Complete Campaign** action.
   - Existing **Find product & create posters** remains available.
2. **Progress**
   - Load official record, original manufacturer photo and product-aware category.
   - Select **price**, **benefit** and **application** angles.
   - Generate assets, validate source-based content and package ZIP.
   - If Gemini is unavailable: use labelled evidence-based copy/layout logic.
3. **Campaign overview**
   - Part number, product title, three verified marketing angles, warning/review notes.
   - Downloadable preview gallery of all channel graphics.
   - The original selectable copy-preview experience: choose **Price-led / Benefit-led / Application-led**, then **Social / LinkedIn / Email / Hashtags / Website / Short promo** to display the full suggested text in one editable field.
   - **Copy this text**, **Copy all campaign wording** and **Reset this draft** controls; browser edits persist while switching tabs but are not included in the downloaded original ZIP.
   - **Optional downloads only:** generating a campaign displays the asset gallery and copy editor; it does **not** open a ZIP on mobile or desktop. Tap **Download complete ZIP** if you want the pack, or **Download PNG** on an individual artwork.
   - **Optional native sharing:** Use **Share PNG** beside a campaign graphic to open the iPhone/Android share sheet for installed compatible apps, such as WhatsApp or Instagram where supported. **Share complete ZIP** is also available on devices that support the ZIP file type, though social apps may reject ZIP archives. An explicit Download option remains alongside every Share control.
   - The share file is prepared in memory after an asset appears, with no automatic file download or share action. The final native share sheet opens **only on your tap**. Other browsers show guidance to download and share from Photos/Files. Marketing captions stay in the copy editor for review/copying.
4. **External publication**
   - Human review of every graphic, claim, image right, fitment, RRP/VAT and
     distributor logo permission is mandatory. No auto-publication in MVP.

## Output contract — generated in one request

| Group | Assets |
| --- | --- |
| Posters | Price-led, benefit-led and application-led 1200×1500 PNG advertisements |
| Social | Facebook/Instagram 1080×1080 and Story 1080×1920 PNG |
| Web and email | Website 1600×600 and email header 1200×420 PNG |
| Written copy | Price/benefit/application variants of social caption, LinkedIn post, customer email subject/body, hashtags, SEO-friendly product listing blurb and short WhatsApp-style message |
| Sales info | Source record JSON, campaign manifest JSON, copy JSON/TXT, PDF campaign summary, official-source QR if safe URL available |
| Delivery | One ZIP with review notes; clickable previews and copy actions inside the hub |

The seven main artwork files are native to their aspect ratio; **no arbitrary poster
cropping**. Original manufacturer product photo pixels are preserved. The original
poster renderer also runs automatic typography / layout quality checks.

### Sample ZIP structure

```text
LASER_9395_Complete_Campaign.zip
├── 01_Posters/
│   ├── Price-led.png
│   ├── Benefit-led.png
│   └── Application-led.png
├── 02_Social/
│   ├── Facebook_Instagram_Square.png
│   └── Instagram_Facebook_Story.png
├── 03_Web_Email/
│   ├── Website_Banner.png
│   └── Email_Header.png
├── 04_Copy/
│   ├── All_Channels.txt
│   └── All_Channels.json
├── 05_Product_Info/
│   ├── Official_Product_QR.png (only when source URL is approved)
│   ├── Source_Record.json
│   ├── Campaign_Summary.pdf
│   └── READ_FIRST.txt
└── Campaign_Manifest.json
```

## Marketing intelligence

- **Price-led:** Official/staff-reviewed UK RRP, the price's VAT status
  and a genuine manufacturer feature. No unsupported discounts or savings.
- **Benefit-led:** A source-backed workshop benefit or tool specification.
- **Application-led:** Manufacturer-confirmed vehicle/application text. If not
  available, describe the workshop task only; don't invent fitment.
- For a socket set, choose verified drive sizes, set contents and supplied
  accessories. For a workshop press, use confirmed capacities/operation only.
  For a bearing kit, use confirmed vehicle/application details only.
- Gemini can select headline/art direction; technical evidence, image, price,
  source and approved product facts are **never** generated by Gemini.
- Without a working Gemini API key, the source-grounded fallback still
  produces a complete usable draft pack and reports the fallback honestly.

## Technical architecture

- `campaign_hub.py`: independent campaign builder and archive construction.
- `app.py`: single-click UI, preview/copy dashboard and three API endpoints.
- `static/styles.css`: responsive campaign UI.
- `promo_copy.py`, `promo_selling_points.py`, `ai_promo_renderer.py`:
  existing source-verified copy, three marketing focuses and quality-gated ads.
- `requirements.txt`: QR support.
- `test_campaign_hub.py`: no-network integration/format/safety tests.

### API

- `POST /api/campaign/<part>` with optional JSON
  `official_url`, `distributor_brand`, `staff_rrp_ex`,
  `staff_rrp_reviewed`, `staff_rrp_basis`.
  Returns an opaque pack token plus the manifest and copy/asset references.
- `GET /api/campaign/assets/<token>/<asset_id>` returns an original PNG.
- `GET /api/campaign/download/<token>` returns the complete ZIP.

**MVP session model:** Tokens are unguessable and expire after 15 minutes.
The current single-worker Render service holds up to four recent bundles in
memory. Restarting a free-tier service clears those tokens; **download your ZIP**.
No customer accounts, permanent library, background jobs or off-site data
storage yet. Adding multi-worker/background processing will require shared
storage and a job queue before public rollout.

## Safety / approval boundaries

- Manufacturer source data is re-validated in the backend, not accepted
  as arbitrary browser-submitted descriptions or product photographs.
- Only the approved source hosts may be encoded in a generated QR.
- No invented MSRP/RRP, discount, product compatibility, stock or performance
  claims; omitted RRP is displayed as **PRICE ON REQUEST**.
- Staff-entered RRP is labelled draft and only accepted after staff review.
- Customer logos are demonstration assets pending written brand approval.
- User interface and ZIP both say **DRAFT / COMPANY REVIEW REQUIRED**.
- The tool does not send customer data to the model; only manufacturer source
  information is used for model-selected marketing direction.

## MVP QA acceptance checklist

1. Part 9395 produces the complete ZIP and preview gallery from one button.
2. 9364 (socket set) and 9372 (press) use source-specific selling points.
3. All seven core images have native dimensions and no clipped prices/headlines.
4. Each poster has a distinct **price/benefit/application** focus.
5. Unavailable RRP is never guessed; price is on request.
6. Invalid product images, customer logos and staff prices are rejected.
7. The model/API may fail but the **complete labelled fallback pack** still builds.
8. Non-UK source URLs never generate QR links.
9. Existing ordinary posters and AI editor still work.
10. Copy and PNGs always have explicit publication-review warnings.

## Next phases — not yet implemented

1. Distributor account profiles with approved logo/brand palette,
   website/contact CTA, allowed territories and permissions.
2. Saved campaigns, reusable templates, approval stages and campaign history.
3. Optional authorised product-demo-video uploads and short video exports
   (never create imaginary product demonstrations).
4. Approved distributor product-link QR and offer codes.
5. Bulk part-number campaigns, scheduled social publishing through authorised
   provider connections and campaign performance reporting.
