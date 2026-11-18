# Laser Tools catalogue taxonomy → marketing strategy

## What is implemented

The Laser Product Studio includes the **Tool Connection Laser Tools website category
hierarchy** as recorded from the official menu at
https://www.toolconnection.co.uk/laser/products on **18 November 2026**.

Each top category, department and subcategory inherits a defined marketing
lens, suggested buying audience, appropriate channel pair and feature priorities.
The full matrix can be browsed on the website under
**Browse Laser Tools categories & preferred marketing strategies**, or obtained
as JSON at GET /api/catalogue/taxonomy.

The site has more granular product-detail URL folders than the main navigation
(e.g. Cars & Vans / Transmission / Wheel Bearings / Gen2 Wheel Bearing Kits).
These additional folder levels are preserved when they appear in a real
manufacturer product URL; they are explicitly distinguished from matching
the menu snapshot.

### Examples

| Manufacturer category path | Marketing lens | Primary channels |
|---|---|---|
| Cars & Vans → Engine Timing Tools → Peugeot | Verified vehicle/engine application | Email, website |
| Cars & Vans → Transmission → Wheel Bearings | Verified vehicle/engine application | Email, website |
| General Hand Tools → Socketry → Socket Sets | Kit contents and verified sizes | Social, email |
| General Hand Tools → Pliers & Grips → Circlip Pliers | Verified tool functionality | Social, email |
| General Hand Tools → Torque Control → Digital Torque | Torque range and verified precision | Email, website |
| Workshop → Equipment → Hydraulic Press | Verified equipment capacity | Email, website |
| Hybrid/Electric Vehicles → Insulated Tools → Socketry | Verified HV/protection specifications | Email, website |
| Workshop → Inspection - Lighting → Workshop Lamps | Verified lighting specifications | Social, email |
| Workshop → Fluid & Grease → Fluid Extractors | Fluid service and capacity | Email, social |
| Bicycles → Chain | Documented bicycle maintenance | Social, email |
| Assorted Boxes → General Fasteners → Nuts | Verified pack sizes/materials | Website, social |

**Important:** These categories come from the source menu/URL; audiences,
channels, positioning and marketing lenses are **our recommendations**, not
statements of proven demand or the manufacturer's endorsement. Product claims
must be manufacturer-verified and company-approved.

## How part numbers are mapped

1. Enter a part number in Laser Product Studio.
2. The site locates and fetches the exact official manufacturer product page.
3. The verified Tool Connection product URL supplies the catalogue category
   and subcategory. For example, 6200 maps to:
   Cars & Vans → Engine Timing Tools → Peugeot.
4. A company-provided URL index can save repeated searching. Every entry is
   validated against the exact SKU and official website host.
5. When no verified category URL is available, the existing product-title
   classifier remains a **labelled fallback**. The program never claims that
   its guess is the manufacturer's official category.
6. Validated Gemini strategy choices may refine the audience/focus/channels,
   but must be selected from the verified options for that specific category.
   Actual manufacturer specs/photos/fitment cannot be invented.

## Current catalogue coverage

At the time of this change, **10 previously checked pilot product URLs**
are included in data/catalogue_index.json (including 6200, 9395, 9372,
9364, 9365, 9197, 8324, 4832, 8899 and 9024).

This **does not mean every Laser Tools product has been imported**. The
manufacturer publishes a large range and the website navigation does not
provide a complete accessible SKU export through our current tools. The
category rules cover the recorded hierarchy; exact part numbers are mapped
automatically when their product URLs are available.

## Import all parts from an approved company product export

Ask HR for guidance on an internal **Laser Tools product export containing
part number and public Tool Connection product URL**. No customer or
confidential sales data is needed.

The CSV should have at least these columns:

```csv
part_number,product_url
6200,https://www.toolconnection.co.uk/products/cars-vans/engine-timing-tools/peugeot/6200-engine-timing-kit-for-psa-vauxhall-opel-1-0-1-2
```

Then, in the repository:

```bash
python import_catalogue.py laser_products.csv --report catalogue_import_audit.json
python -m unittest test_official_taxonomy.py
```

The command merges validated entries with the existing index, rejects
mismatched or non-official URLs, reports unresolved rows, and **never claims
a complete catalogue** just because an import succeeded. The importer does
not scrape the manufacturer's website. Review the results, then commit the
updated data/catalogue_index.json file.

If the export lacks official product URLs, those part numbers need a
separate authorised lookup/verification process; they are not silently
assigned to a guessed category.

## Why this is useful to Tool Connection

The AI marketing system can now make better-differentiated decisions at
the actual category/subcategory level without your sales-project teammates
having to manually describe the tool for every campaign. It can be expanded
to new lines as official URLs become available, and category-to-marketing
decisions can be reviewed by Technical and Sales before use.
