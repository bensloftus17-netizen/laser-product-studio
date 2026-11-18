"""Import Tool Connection part-number -> official URL exports into the studio.

Usage:
    python import_catalogue.py products.csv
    python import_catalogue.py products.csv --output data/catalogue_index.json

Accepted CSV column pairs:
    part_number,product_url
    part_no,url
    sku,official_url

Rows are never assigned a category from title keyword guesses. Every accepted
URL must be on the Tool Connection website and contain that exact part number;
its full category path is checked against the recorded site hierarchy.
Unresolvable rows are reported, not assigned to 'General Hand Tools'.
The existing checked pilot products remain in the index unless replaced.
No network scraping or customer/contact details are involved.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from official_taxonomy import INDEX_FILE, category_from_product_url


def _norm_header(value):
    return "".join(ch for ch in (value or "").casefold() if ch.isalnum())


PART_HEADERS = {"partnumber", "partno", "part", "partcode", "productcode", "sku", "itemnumber", "itemcode"}
URL_HEADERS = {"producturl", "officialurl", "manufacturerurl", "url", "productlink", "weblink"}


def _headers(fieldnames):
    names = {_norm_header(name): name for name in (fieldnames or [])}
    part = next((names[k] for k in PART_HEADERS if k in names), None)
    url = next((names[k] for k in URL_HEADERS if k in names), None)
    if not part or not url:
        raise ValueError(
            "CSV needs a part number column (e.g. part_number) and "
            "a Tool Connection product URL column (e.g. product_url)."
        )
    return part, url


def load_existing(path: Path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("products"), dict):
        raise ValueError("Existing catalogue index has an invalid format.")
    result = {}
    for part, url in data["products"].items():
        if isinstance(url, str) and category_from_product_url(url, str(part)):
            result[str(part)] = url
    return result


def import_catalogue_csv(input_path, output_path=INDEX_FILE, *, preserve_existing=True):
    """Return an audit summary; do not claim to have captured all live SKUs."""
    source, destination = Path(input_path), Path(output_path)
    accepted = load_existing(destination) if preserve_existing else {}
    stats = Counter()
    unresolved = []
    imported_categories = Counter()

    with source.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = csv.DictReader(fh)
        part_field, url_field = _headers(rows.fieldnames)
        for row_num, row in enumerate(rows, start=2):
            stats["rows_seen"] += 1
            part = str(row.get(part_field) or "").strip()
            url = str(row.get(url_field) or "").strip()
            match = category_from_product_url(url, part)
            if not part or not match:
                stats["unresolved"] += 1
                unresolved.append({"csv_row": row_num, "part": part,
                                   "issue": "Missing or non-matching official product URL/category path"})
                continue
            if part in accepted:
                if accepted[part] != url:
                    stats["conflicts"] += 1
                    unresolved.append({"csv_row": row_num, "part": part,
                                       "issue": "Conflicting URL; existing indexed URL retained"})
                else:
                    stats["already_indexed"] += 1
                continue
            accepted[part] = url
            stats["new_parts"] += 1
            imported_categories[match["breadcrumb"]] += 1

    if not stats["rows_seen"]:
        raise ValueError("CSV contains no product rows.")
    if not accepted:
        raise ValueError("No valid official manufacturer product URLs were found.")
    output: dict[str, Any] = {
        "source": "Tool Connection product URL CSV import",
        "catalogue_complete": False,
        "requires_source_review": True,
        "products": dict(sorted(accepted.items(), key=lambda item: item[0])),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    stats["total_indexed"] = len(accepted)
    return {
        "input_csv": source.name,
        "output_index": str(destination),
        "summary": dict(stats),
        "new_category_counts": dict(imported_categories),
        "unresolved_rows": unresolved,
        "important": (
            "Indexed URLs have been validated structurally, not fetched live. "
            "Individual product pages are checked by the application when used. "
            "The catalogue is not certified complete."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", help="A company product URL CSV export")
    parser.add_argument("--output", default=str(INDEX_FILE),
                        help="JSON destination for accepted part-number URLs")
    parser.add_argument("--replace-index", action="store_true",
                        help="Replace rather than preserve existing checked URLs")
    parser.add_argument("--report", help="Optional separate JSON audit report")
    args = parser.parse_args()
    report = import_catalogue_csv(
        args.csv_file, args.output, preserve_existing=not args.replace_index
    )
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
