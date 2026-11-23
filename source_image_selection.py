"""Rank genuine, exact-SKU manufacturer images without settling for thumbnails.

This helper never edits, enlarges or invents source imagery. Each candidate
is fetched exclusively through the app's approved-domain official_get()
callback, which verifies redirects, file size and response status.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor


def collect_official_photo_options(urls, fetch, valid, rank, *,
                                   max_checks=15, workers=3,
                                   min_distinct_good=1, distinct_signature=None):
    """Inspect bounded batches, continuing past low-quality images.

    Stop only when an actual source passes the strict preflight at a preferred
    650+ minimum side. A 300px thumbnail must not cause an early exit merely
    because it is a genuine part-number catalogue image.

    Return (options, attempted_urls) with stable input ordering.
    """
    paths=list(dict.fromkeys(
        x for x in urls if isinstance(x,str) and x.startswith("https://")
    ))[:max_checks]
    found=[]
    checked=[]
    good_signatures=[]
    def inspect(url):
        try:
            response=fetch(url)
            blob=response.content
            if not valid(blob):
                return None
            score,report=rank(blob)
            return (score,blob,response.url,report)
        except Exception:
            # A 404 or blocked high-resolution endpoint is normal; keep
            # trying manufacturer gallery variants instead of giving up.
            return None
    for start in range(0,len(paths),workers):
        batch=paths[start:start+workers]
        with ThreadPoolExecutor(max_workers=min(workers,len(batch))) as pool:
            results=list(pool.map(inspect,batch))
        checked.extend(batch)
        found.extend(result for result in results if result)
        for item in results:
            if not item or not item[3].get("passed"):
                continue
            if min(item[3].get("size") or (0,0))<650:
                continue
            try:
                signature=(distinct_signature(item[1])
                           if distinct_signature else item[2])
            except (OSError,ValueError):
                continue
            if isinstance(signature,int):
                if any((signature^older).bit_count()<=5
                       for older in good_signatures):
                    continue
            elif signature in good_signatures:
                continue
            good_signatures.append(signature)
        if len(good_signatures)>=max(1,min_distinct_good):
            break
    return found,checked


def best_manufacturer_photo(options):
    """Prefer a passing *actual* source over all failed thumbnails.

    Ranking of multiple passing sources still rewards sharper, larger
    manufacturer photos. A poor source may remain available for the product
    preview, but it is not approved for poster generation.
    """
    if not options:
        return None
    return max(options,key=lambda item:(
        bool(item[3].get("passed")),item[0],
        min(item[3].get("size") or [0,0])
    ))


def source_photo_audit(options,checked,selected):
    report=(selected[3] if selected else {})
    return {
        "method":"ranked-official-image-sources-with-pdf-rescue",
        "source_urls_checked":len(checked),
        "valid_images_checked":len(options),
        "quality_passed":bool(report.get("passed")),
        "dimensions":report.get("size"),
        "quality_issues":list(report.get("issues") or []),
        "quality_warnings":list(report.get("warnings") or []),
        "source_url":selected[2] if selected else None,
        "pdf_rescue_used":bool(selected and "#pdf-photo-" in selected[2]),
        "generated_or_upscaled":False,
    }
