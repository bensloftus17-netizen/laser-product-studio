"""Private, short-lived disk backing for completed, source-verified campaigns.

Render's 512 MiB web instance must not retain four complete campaign ZIPs,
nine original PNGs, decoded photograph sources and editor contexts in RAM.
Only already-approved bytes reach this store. A secret bearer token is still
required by every public route; files live outside the Flask static directory.
Container-local storage is ephemeral across redeploys, as before.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import MutableMapping
from pathlib import Path

KEY = re.compile(r"^[a-z][a-z0-9_]{1,40}$", re.ASCII)


def _atomic_file(path: Path, payload: bytes):
    fd, name=tempfile.mkstemp(prefix=".write-",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(payload)
        os.replace(name,path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class DiskImages(MutableMapping):
    def __init__(self,folder: Path, keys):
        self.folder=folder
        self.keys_order=list(keys)

    def _path(self,key):
        if not isinstance(key,str) or not KEY.fullmatch(key) or key not in self.keys_order:
            raise KeyError(key)
        return self.folder/(key+".png")

    def __getitem__(self,key):
        return self._path(key).read_bytes()

    def __setitem__(self,key,payload):
        if not isinstance(key,str) or not KEY.fullmatch(key):
            raise ValueError("Invalid approved artwork identifier")
        if not isinstance(payload,bytes) or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Only checked PNGs may be saved")
        if key not in self.keys_order:
            self.keys_order.append(key)
        _atomic_file(self._path(key),payload)

    def __delitem__(self,key):
        self._path(key).unlink()
        self.keys_order.remove(key)

    def __iter__(self):
        return iter(tuple(self.keys_order))

    def __len__(self):
        return len(self.keys_order)


class StoredCampaign(MutableMapping):
    """Dict-compatible on-demand bundle for editing and authenticated download."""

    def __init__(self, folder: Path, manifest, image_names):
        self.folder=folder
        self._manifest=manifest
        self._images=DiskImages(folder/"images",image_names)

    @property
    def archive_path(self):
        return self.folder/"campaign.zip"

    def __getitem__(self,key):
        if key=="manifest":
            return self._manifest
        if key=="images":
            return self._images
        if key=="archive":
            return self.archive_path.read_bytes()
        if key=="editor_context":
            return self._read_editor()
        raise KeyError(key)

    def __setitem__(self,key,value):
        if key=="manifest":
            self._manifest=value
            return
        if key=="archive" and isinstance(value,bytes):
            _atomic_file(self.archive_path,value)
            return
        raise KeyError(key)

    def __delitem__(self,key):
        raise KeyError("Required campaign fields cannot be removed")

    def __iter__(self):
        return iter(("manifest","images","archive","editor_context"))

    def __len__(self):
        return 4

    def _read_editor(self):
        path=self.folder/"editor.json"
        if not path.exists():
            return None
        ctx=json.loads(path.read_text(encoding="utf-8"))
        photo=self.folder/"product_photo.bin"
        ctx["genuine_photo"]=photo.read_bytes() if photo.exists() else None
        scene_files=ctx.pop("scene_files",[])
        ctx["scenes"]=[
            (self.folder/name).read_bytes() if name else None
            for name in scene_files]
        return ctx

    def save_editor(self,ctx):
        """Persist newly revised factual concepts after successful poster edit."""
        if not ctx:
            return
        scene_files=[]
        for n,payload in enumerate(ctx.get("scenes",[])):
            if isinstance(payload,bytes):
                name="scene_%s.bin"%n
                _atomic_file(self.folder/name,payload)
                scene_files.append(name)
            else:
                scene_files.append(None)
        photo=ctx.get("genuine_photo")
        if isinstance(photo,bytes):
            _atomic_file(self.folder/"product_photo.bin",photo)
        data={
            "product":ctx.get("product") or {},
            "concepts":ctx.get("concepts") or [],
            "distributor":ctx.get("distributor"),
            "scene_files":scene_files,
        }
        _atomic_file(self.folder/"editor.json",json.dumps(
            data,ensure_ascii=False,default=str).encode("utf-8"))

    def delete(self):
        shutil.rmtree(self.folder,ignore_errors=True)


def store_campaign(bundle,*,root=None):
    """Spill an approved campaign to disk, without keeping duplicate bytes.

    Never replace an in-memory approved pack until every required file has
    been written successfully. Invalid or missing PNGs fail closed.
    """
    directory=Path(tempfile.mkdtemp(prefix="laser-studio-pack-",dir=root))
    try:
        (directory/"images").mkdir()
        images=bundle["images"]
        stored=StoredCampaign(directory,bundle["manifest"],[])
        for key in images:
            stored["images"][key]=images[key]
        archive=bundle["archive"]
        if not isinstance(archive,bytes) or not archive.startswith(b"PK"):
            raise ValueError("Approved campaign ZIP is missing or invalid")
        _atomic_file(stored.archive_path,archive)
        stored.save_editor(bundle.get("editor_context"))
        return stored
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise
