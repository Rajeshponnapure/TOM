"""Fetch real, free-to-use 3D assets from the internet — models, HDRIs and PBR textures from Poly
Haven, which is entirely CC0 (public domain, no key, usable in commercial work).

This is what lets TOM build a scene with professional assets instead of only primitives: search for
"barrel" or "wooden table", download the glTF (with its .bin and textures) or an HDRI, and hand the
file paths to Blender to import. Downloads are ordinary web fetches that land in the owner's
workspace, like a web search that saves its result; nothing is sent anywhere.

Sketchfab (a far larger library) needs an API token and its own per-model licence check, so it is a
separate, opt-in path gated behind a key (tom_core.secrets "sketchfab") — not wired here yet.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

API = "https://api.polyhaven.com"
_UA = {"User-Agent": "TOM-agent/1.0 (+https://polyhaven.com)"}
OpenerT = Callable[[str], bytes]


def _default_opener(url: str) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:        # nosec - fixed CC0 asset host
        return resp.read()


@dataclass
class AssetFile:
    url: str
    rel_path: str                     # where it goes relative to the asset folder
    md5: str = ""


@dataclass
class DownloadPlan:
    asset_id: str
    type: str                         # models | hdris | textures
    resolution: str
    main: AssetFile
    includes: List[AssetFile] = field(default_factory=list)

    @property
    def all_files(self) -> List[AssetFile]:
        return [self.main] + self.includes


class PolyHaven:
    def __init__(self, opener: Optional[OpenerT] = None):
        self._open = opener or _default_opener

    def _json(self, path: str) -> object:
        return json.loads(self._open(f"{API}{path}").decode("utf-8"))

    def search(self, query: str, asset_type: str = "models", limit: int = 12) -> List[Dict[str, str]]:
        """CC0 assets whose id/name/tags match `query`. asset_type: models | hdris | textures."""
        data = self._json(f"/assets?type={asset_type}")
        if not isinstance(data, dict):
            return []
        q = (query or "").lower().strip()
        terms = [t for t in q.split() if t]
        hits = []
        for aid, meta in data.items():
            hay = (aid + " " + " ".join(meta.get("tags", []) or []) + " " +
                   " ".join(meta.get("categories", []) or [])).lower()
            if not terms or all(t in hay for t in terms):
                hits.append({"id": aid, "name": aid.replace("_", " "),
                             "type": asset_type, "categories": ", ".join(meta.get("categories", []) or [])})
        # exact / prefix matches first
        hits.sort(key=lambda h: (q not in h["id"].lower(), not h["id"].lower().startswith(terms[0] if terms else "")))
        return hits[:limit]

    def resolve(self, asset_id: str, asset_type: str = "models", resolution: str = "1k") -> DownloadPlan:
        """Build the download plan: the main file plus every dependency (glTF .bin + textures)."""
        files = self._json(f"/files/{asset_id}")
        if not isinstance(files, dict):
            raise ValueError(f"No files for '{asset_id}'.")
        if asset_type == "hdris":
            tree = files.get("hdri", {})
            res = tree.get(resolution) or next(iter(tree.values()), {})
            entry = res.get("hdr") or next(iter(res.values()), {})
            if not entry.get("url"):
                raise ValueError(f"No HDRI download for '{asset_id}'.")
            return DownloadPlan(asset_id, "hdris", resolution,
                                AssetFile(entry["url"], f"{asset_id}_{resolution}.hdr", entry.get("md5", "")))
        if asset_type == "textures":
            # grab the diffuse/albedo map as the representative file
            for mapname in ("Diffuse", "Albedo", "Color", "col"):
                tree = files.get(mapname, {})
                res = tree.get(resolution) or next(iter(tree.values()), {})
                entry = res.get("jpg") or res.get("png") or next(iter(res.values()), {}) if isinstance(res, dict) else {}
                if isinstance(entry, dict) and entry.get("url"):
                    ext = os.path.splitext(entry["url"])[1] or ".jpg"
                    return DownloadPlan(asset_id, "textures", resolution,
                                        AssetFile(entry["url"], f"{asset_id}_{mapname}_{resolution}{ext}",
                                                  entry.get("md5", "")))
            raise ValueError(f"No texture map for '{asset_id}'.")
        # models: glTF with includes
        gltf = files.get("gltf", {})
        res = gltf.get(resolution) or next(iter(gltf.values()), {})
        entry = res.get("gltf") if isinstance(res, dict) else None
        if not entry or not entry.get("url"):
            raise ValueError(f"No glTF model for '{asset_id}'.")
        main = AssetFile(entry["url"], f"{asset_id}_{resolution}.gltf", entry.get("md5", ""))
        includes = [AssetFile(v["url"], rel, v.get("md5", ""))
                    for rel, v in (entry.get("include", {}) or {}).items() if v.get("url")]
        return DownloadPlan(asset_id, "models", resolution, main, includes)

    def download(self, plan: DownloadPlan, dest_root: str) -> Dict[str, object]:
        """Download every file in the plan into dest_root/<asset_id>/, preserving relative paths."""
        folder = os.path.join(dest_root, plan.asset_id)
        os.makedirs(folder, exist_ok=True)
        written: List[str] = []
        for f in plan.all_files:
            path = os.path.join(folder, f.rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(path) or folder, exist_ok=True)
            data = self._open(f.url)
            if f.md5:
                got = hashlib.md5(data).hexdigest()   # nosec - integrity check only, not security
                if got != f.md5:
                    return {"status": "error", "message": f"Checksum mismatch for {f.rel_path} "
                            f"(expected {f.md5}, got {got}); download aborted."}
            with open(path, "wb") as fh:
                fh.write(data)
            written.append(path)
        main_path = os.path.join(folder, plan.main.rel_path.replace("/", os.sep))
        return {"status": "success", "folder": folder, "main": main_path, "files": written,
                "count": len(written),
                "message": f"Downloaded {plan.asset_id} ({plan.type}, {plan.resolution}, CC0) — "
                           f"{len(written)} file(s) to {folder}"}


def fetch(query: str, asset_type: str = "models", resolution: str = "1k",
          dest_root: str = "", opener: Optional[OpenerT] = None) -> Dict[str, object]:
    """Search, pick the best match, download it. Returns the result with `main` = the file to import."""
    ph = PolyHaven(opener=opener)
    try:
        hits = ph.search(query, asset_type)
    except Exception as exc:
        return {"status": "error", "message": f"Couldn't reach Poly Haven: {exc}"}
    if not hits:
        return {"status": "not_found",
                "message": f"No CC0 {asset_type} on Poly Haven matched \"{query}\". Try another word "
                           "(their library is curated, so it won't have everything)."}
    if not dest_root:
        from tools.project_paths import workspace_root
        dest_root = os.path.join(str(workspace_root()), "assets")
    try:
        plan = ph.resolve(hits[0]["id"], asset_type, resolution)
        res = ph.download(plan, dest_root)
    except Exception as exc:
        return {"status": "error", "message": f"Download failed for {hits[0]['id']}: {exc}"}
    res["asset_id"] = hits[0]["id"]
    res["alternatives"] = [h["id"] for h in hits[1:6]]
    return res
