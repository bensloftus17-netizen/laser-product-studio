"""Lightweight 512 MiB Render worker memory admission and diagnostics.

Prevent new high-memory jobs while the container is near its actual cgroup
memory limit. No background tasks, large in-memory metrics buffers or
expensive monitoring threads. Never changes image pixels or the quality gate.
"""
from __future__ import annotations

import gc
import logging
from pathlib import Path

LOG = logging.getLogger(__name__)
MIB = 1024*1024
# Leave enough headroom for decoded source photos, PIL temporary canvases,
# OpenSSL/HTTP buffers and other gunicorn threads on Render Free.
CAMPAIGN_HEADROOM = 165*MIB
RESEARCH_HEADROOM = 105*MIB
UNKNOWN_LIMIT = 512*MIB


def _int_file(path):
    try:
        raw=Path(path).read_text(encoding="ascii").strip()
        if raw.isdigit():
            return int(raw)
    except (OSError, ValueError):
        return None
    return None


def _reclaimable_file_cache():
    """Linux can reclaim inactive file-cache pages under memory pressure.

    File-backed progressive PNG previews are intentionally stored on disk.
    Those pages should not be mistaken for live Pillow RGB canvases.
    """
    try:
        for line in Path("/sys/fs/cgroup/memory.stat").read_text(
                encoding="ascii").splitlines():
            if line.startswith("inactive_file "):
                return max(0,int(line.split()[1]))
    except (OSError,ValueError,IndexError):
        pass
    return 0


def current_memory():
    """Read container allocation rather than RSS from only one worker.

    cgroup memory.current captures Python, the gunicorn master, kernel page
    cache and other threads, unlike resource.getrusage() of the worker alone.
    An unknown limit is reported as None instead of inventing capacity.
    """
    limit=_int_file("/sys/fs/cgroup/memory.max")
    used=_int_file("/sys/fs/cgroup/memory.current")
    if used is None:
        used=_int_file("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if limit is None:
        limit=_int_file("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if limit and limit>1_000_000_000_000:
        limit=None
    if used is None:
        try:
            for line in Path("/proc/self/status").read_text(
                    encoding="ascii").splitlines():
                if line.startswith("VmRSS:"):
                    used=int(line.split()[1])*1024
                    break
        except (OSError, ValueError, IndexError):
            pass
    return {"used_bytes":used, "limit_bytes":limit,
            "reclaimable_bytes":_reclaimable_file_cache()}


def try_release_heap():
    """Release dead PIL objects and libc free heaps before heavy work.

    Linux glibc often retains freed image/HTML buffers in anonymous mmap
    arenas. malloc_trim can return unused pages without lowering print
    resolution or clearing live user campaigns. Non-glibc environments safely
    skip the optional trim.
    """
    gc.collect()
    try:
        import ctypes
        libc=ctypes.CDLL(None)
        trim=getattr(libc,"malloc_trim",None)
        if trim:
            trim(0)
    except (OSError, AttributeError, TypeError, ValueError):
        pass


def can_start_heavy(kind):
    """Admission control; never interpret unavailable measurements as failure.

    Preserve fast cached reads and previews. A busy response allows the
    browser to retry rather than losing the whole worker to an OOM kill.
    """
    required=CAMPAIGN_HEADROOM if kind=="campaign" else RESEARCH_HEADROOM
    try_release_heap()
    metrics=current_memory()
    used,limit=metrics["used_bytes"],metrics["limit_bytes"]
    if used is None or limit is None:
        return True
    reclaimable=min(used,max(0,metrics.get("reclaimable_bytes") or 0))
    working_set=used-reclaimable
    safe=working_set+required < limit
    if not safe:
        LOG.warning("Render memory pressure; refusing new %s task: cgroup=%d MiB active=%d MiB limit=%d MiB required_headroom=%d MiB",
                    kind, used//MIB,working_set//MIB,limit//MIB,required//MIB)
    return safe
