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

    def path_for(self,key):
        """Only accept identifiers from the approved campaign's image index."""
        return self._path(key)

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
            _atomic_file(self.folder/"manifest.json",json.dumps(value,ensure_ascii=False,default=str).encode("utf-8"))
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

    def gallery_path(self,index):
        """Validated path for one short-lived source image, never a public URL."""
        if type(index) is not int or index<0 or index>=4:
            raise ValueError("Invalid manufacturer photo index")
        choices=self._manifest.get("poster_photo_choices") or []
        if index>=len(choices):
            raise ValueError("Photo is not in the source-verified campaign")
        path=self.folder/("gallery_"+str(index)+".bin")
        if not path.is_file() or path.stat().st_size>5_000_000:
            raise ValueError("Verified manufacturer photo unavailable")
        return path

    def gallery_photo(self,index):
        """Read only the selected compressed photo, never the entire gallery."""
        return self.gallery_path(index).read_bytes()

    def _read_editor(self):
        path=self.folder/"editor.json"
        if not path.exists():
            return None
        ctx=json.loads(path.read_text(encoding="utf-8"))
        photo=self.folder/"product_photo.bin"
        ctx["genuine_photo"]=photo.read_bytes() if photo.exists() else None
        photo_files=ctx.pop("role_photo_files",{})
        ctx["role_photos"]={
            key:(self.folder/name).read_bytes()
            for key,name in photo_files.items()
            if key in ("poster_technical","poster_price","poster_smart")
            and re.fullmatch(r"role_(?:poster_technical|poster_price|poster_smart)\.bin",str(name))
            and (self.folder/name).is_file()}
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
        # Initial campaign stores four compressed original photos on disk;
        # later single-poster edits only load/update one, so keep originals
        # without readback or reserialising their bytes in editor.json.
        for index,payload in enumerate((ctx.get("gallery_photos") or [])[:4]):
            if isinstance(payload,bytes) and 0<len(payload)<=5_000_000:
                _atomic_file(self.folder/("gallery_"+str(index)+".bin"),payload)
        photo_files={}
        for role,payload in (ctx.get("role_photos") or {}).items():
            if role not in ("poster_technical","poster_price","poster_smart"):
                continue
            if isinstance(payload,bytes):
                name="role_"+role+".bin"
                _atomic_file(self.folder/name,payload)
                photo_files[role]=name
        data={
            "product":ctx.get("product") or {},
            "concepts":ctx.get("concepts") or [],
            "distributor":ctx.get("distributor"),
            "scene_files":scene_files,
            "role_photo_files":photo_files,
        }
        _atomic_file(self.folder/"editor.json",json.dumps(
            data,ensure_ascii=False,default=str).encode("utf-8"))

    def delete(self):
        shutil.rmtree(self.folder,ignore_errors=True)


def store_campaign(bundle,*,root=None,token=None):
    """Spill an approved campaign to disk, without keeping duplicate bytes.

    Never replace an in-memory approved pack until every required file has
    been written successfully. Invalid or missing PNGs fail closed.
    """
    if token is not None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{24,64}",token):
            raise ValueError("Invalid campaign token")
        base=Path(root)
        base.mkdir(mode=0o700,parents=True,exist_ok=True)
        directory=base/token
        directory.mkdir(mode=0o700)
    else:
        directory=Path(tempfile.mkdtemp(prefix="laser-studio-pack-",dir=root))
    try:
        (directory/"images").mkdir()
        images=bundle["images"]
        stored=StoredCampaign(directory,bundle["manifest"],[])
        for key in images:
            stored["images"][key]=images[key]
        if "archive_path" in bundle:
            source=Path(bundle["archive_path"])
            # The only producer is the internal ZIP builder. Move the source
            # atomically within private /tmp; no second ZIP bytes allocation.
            with source.open("rb") as stream:
                if stream.read(2)!=b"PK":
                    raise ValueError("Approved campaign ZIP is invalid")
            os.replace(source,stored.archive_path)
        else:
            archive=bundle["archive"]
            if not isinstance(archive,bytes) or not archive.startswith(b"PK"):
                raise ValueError("Approved campaign ZIP is missing or invalid")
            _atomic_file(stored.archive_path,archive)
        stored.save_editor(bundle.get("editor_context"))
        stored["manifest"]=bundle["manifest"]
        return stored
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise


def reopen_campaign(root,token):
    """Recover private disk-backed packs without loading image or ZIP bytes."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{24,64}",token):
        return None
    folder=Path(root)/token
    try:
        manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        names=[p.stem for p in (folder/"images").glob("*.png") if KEY.fullmatch(p.stem)]
        if not names or not (folder/"campaign.zip").is_file():
            return None
        return StoredCampaign(folder,manifest,names)
    except (OSError,ValueError):
        return None
