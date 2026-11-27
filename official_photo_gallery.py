"""V77: genuine, distinct official gallery photographs for campaign artwork.

The HTML parser only accepts SKU-linked images on approved manufacturer pages.
Images must pass the existing no-white-halo/legibility preflight. Perceptual
hashing prevents identical product shots in different file sizes from being
mistaken for new angles. Additional full-resolution manufacturer bytes live on
private temporary disk, NOT in Render Free's 512 MiB Python heap.
"""
from __future__ import annotations

import hashlib
import html
import io
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from PIL import Image, ImageOps


_ROOT = Path(tempfile.mkdtemp(prefix="laser-official-gallery-"))
_GALLERIES = {}
_MAX_IMAGE_BYTES = 5_000_000
_MAX_IMAGES = 4


def _exact_sku(text, part):
    """Require a complete part number, not a substring of another SKU."""
    return bool(re.search(r"(?<![A-Za-z0-9])"+re.escape(part)+
                          r"(?![A-Za-z0-9])", str(text or ""), re.I))


def gallery_urls_from_html(content, page_url, part, approved):
    """Discover full-size and lazy gallery images on the *exact* Laser SKU page.

    Read image-bearing JSON-LD before stripping scripts. Only accept URLs from
    approved manufacturer domains whose filename or product image metadata
    identifies the requested part. Data-URI, SVG, logo, unrelated products,
    off-domain, and guessed image URLs are excluded.
    """
    soup=BeautifulSoup(
        content.decode("utf-8","replace") if isinstance(content,bytes)
        else str(content or ""), "html.parser")
    found=[]
    def add(raw,context="",resolution=0):
        if not isinstance(raw,str):
            return
        raw=html.unescape(raw.strip())
        if not raw or raw.startswith(("data:","blob:","#")):
            return
        url=urljoin(page_url,raw)
        p=urlparse(url)
        if (p.scheme!="https" or not approved(url)
                or re.search(r"\.(svg|gif|ico)(?:$|[?#])",p.path,re.I)):
            return
        basename=p.path.rsplit("/",1)[-1]
        if not _exact_sku(basename,part):
            # Product gallery images without the part number in their URL
            # are admitted ONLY when this exact SKU is in its own alt/title/
            # image caption, rather than a generic navigation element.
            if not _exact_sku(context,part):
                return
        lower=(basename+" "+str(context)).lower()
        if re.search(r"\b(logo|brandmark|header|footer|icon|sprite|placeholder)\b",lower):
            return
        found.append((url,int(resolution or 0)))
    for tag in soup.select('script[type="application/ld+json"]')[:15]:
        try:
            import json
            payload=json.loads(tag.string or tag.get_text() or "{}")
        except (ValueError,TypeError):
            continue
        def walk(obj, depth=0):
            if depth>5:return
            if isinstance(obj,list):
                for item in obj[:25]:walk(item,depth+1)
            elif isinstance(obj,dict):
                kind=str(obj.get("@type","")).lower()
                if "product" in kind:
                    name=str(obj.get("name") or "")
                    sku=str(obj.get("sku") or obj.get("mpn") or "")
                    if (_exact_sku(sku,part) or _exact_sku(name,part) or
                            _exact_sku(urlparse(page_url).path,part)):
                        img=obj.get("image",[])
                        for item in img if isinstance(img,list) else [img]:
                            if isinstance(item,str):add(item,sku or name,1600)
                            elif isinstance(item,dict):
                                add(item.get("contentUrl") or item.get("url"),
                                    sku or name,1600)
                for value in obj.values():
                    if isinstance(value,(dict,list)):
                        walk(value,depth+1)
        walk(payload)
    for node in soup.find_all(["a","img","source","meta"]):
        container=node.find_parent(
            attrs={"class":re.compile(
                r"(gallery|product[-_ ]?(?:image|photo|media)|carousel|slider|thumb)",re.I)})
        context=" ".join(str(node.get(key) or "")
                         for key in ("alt","title","data-product-id","data-sku"))
        if container:
            context+=" "+str(container.get("data-product-id") or
                             container.get("data-sku") or "")
        if node.name=="meta":
            if (node.get("property") or node.get("name") or "").lower() in (
                "og:image","twitter:image"):
                add(node.get("content"),context,1200)
            continue
        for key in ("data-original","data-zoom-image","data-full",
                    "data-large","data-src","data-lazy-src","href","src"):
            value=node.get(key)
            if isinstance(value,str):
                add(value,context,1200 if key in
                    ("data-original","data-zoom-image","data-full","data-large") else 0)
        for key in ("srcset","data-srcset"):
            value=node.get(key) or ""
            for item in value.split(","):
                fields=item.strip().split()
                if not fields:continue
                resolution=0
                if len(fields)>1:
                    try:
                        if fields[-1].endswith("w"):
                            resolution=int(fields[-1][:-1])
                        elif fields[-1].endswith("x"):
                            resolution=int(float(fields[-1][:-1])*1000)
                    except ValueError:pass
                add(fields[0],context,resolution)
    # The SAME URL can appear in both gallery and JSON-LD; retain best size.
    ranked={}
    for url,priority in found:
        ranked[url]=max(ranked.get(url,0),priority)
    return [url for url,_ in sorted(ranked.items(),key=lambda v:-v[1])][:24]


def _signature(blob):
    with Image.open(io.BytesIO(blob)) as original:
        if original.format in ("JPEG","MPO"):
            original.draft("RGB",(128,128))
        preview=ImageOps.exif_transpose(original).convert("L").resize(
            (9,8),Image.Resampling.BILINEAR)
        values=list(preview.getdata())
        # Difference hash distinguishes alternate views but dedupes source
        # resolution/encoding variations. No visual changes are written.
        bits=0
        for y in range(8):
            for x in range(8):
                bits=(bits<<1)|(1 if values[y*9+x]>values[y*9+x+1] else 0)
        return bits


def _laid_out_photo(url):
    name = urlparse(url).path.rsplit("/", 1)[-1].lower()
    return bool(re.search(r"(?:exploded|lay[ _-]?out|laid[ _-]?out|contents?)",name))


def distinct_gallery(options, primary, *, max_images=_MAX_IMAGES):
    """Keep only genuinely different, QA-approved manufacturer hero images."""
    selected=[]
    if primary:
        selected.append(primary)
    for item in sorted(options,key=lambda x:(not _laid_out_photo(x[2]),-x[0])):
        if item is primary or not isinstance(item,(list,tuple)) or len(item)<4:
            continue
        if not item[3].get("passed") or item[3].get("possible_source_crop"):
            continue
        selected.append(item)
    seen_hash=set()
    seen_visual=[]
    distinct=[]
    for score,blob,url,report in selected:
        if not isinstance(blob,bytes) or len(blob)>_MAX_IMAGE_BYTES:
            continue
        digest=hashlib.sha256(blob).hexdigest()
        if digest in seen_hash:continue
        try:
            visual=_signature(blob)
        except (OSError,ValueError):
            continue
        if any((visual^old).bit_count()<=5 for old in seen_visual):
            continue
        seen_hash.add(digest)
        seen_visual.append(visual)
        basename=urlparse(url).path.lower()
        kind=("application" if re.search(r"in.?situ|workshop|application",basename)
              else "laid-out contents" if _laid_out_photo(url)
              else "contents" if re.search(r"contents?|kit",basename)
              else "detail" if re.search(r"close.?up|detail",basename)
              else "alternate" if distinct else "packshot")
        distinct.append({
            "blob":blob,"source_url":url,"type":kind,
            "sha256":digest,
            "size":list(report.get("size") or []),
            "passed":True,
        })
        if len(distinct)>=max_images:break
    return distinct


def store_gallery(part, records):
    """Atomically retain at most four approved photos on *private* disk."""
    if not re.fullmatch(r"[A-Za-z0-9.-]{3,16}",str(part or "")):
        raise ValueError("Unsafe manufacturer part number")
    discard_gallery(part)
    directory=Path(tempfile.mkdtemp(prefix="sku-",dir=_ROOT))
    metadata=[]
    try:
        for index,entry in enumerate(records[:_MAX_IMAGES]):
            blob=entry["blob"]
            if not isinstance(blob,bytes) or len(blob)>_MAX_IMAGE_BYTES:
                continue
            dest=directory/("photo-"+str(index)+".bin")
            tmp=directory/("tmp-"+str(index)+".bin")
            tmp.write_bytes(blob)
            os.replace(tmp,dest)
            metadata.append({
                "type":entry["type"],
                "source_url":entry["source_url"],
                "sha256":entry["sha256"],
                "size":entry["size"],
                "passed":True,
                "_path":str(dest),
            })
        _GALLERIES[part]=directory
        # Public metadata never reveals a private temporary filesystem path.
        return [{k:v for k,v in item.items() if k!="_path"} for item in metadata]
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise


def load_gallery(part):
    """Read only bounded original pixels when a campaign is actually built."""
    directory=_GALLERIES.get(part)
    if not directory or not directory.is_dir():return []
    loaded=[]
    for file in sorted(directory.glob("photo-*.bin"))[:_MAX_IMAGES]:
        try:
            if file.stat().st_size>_MAX_IMAGE_BYTES:continue
            blob=file.read_bytes()
            if blob:loaded.append(blob)
        except OSError:pass
    return loaded


def discard_gallery(part):
    directory=_GALLERIES.pop(part,None)
    if directory:
        shutil.rmtree(directory,ignore_errors=True)
