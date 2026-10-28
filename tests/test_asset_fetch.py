"""CC0 asset fetch from Poly Haven. Offline tests use a fake opener with canned API JSON + bytes;
one live smoke test (network) downloads a real 1k HDRI and is skipped when offline."""
import json
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import asset_fetch
from tools.asset_fetch import PolyHaven, fetch


def _online() -> bool:
    try:
        socket.create_connection(("api.polyhaven.com", 443), timeout=4).close()
        return True
    except OSError:
        return False


# ── a fake Poly Haven ──────────────────────────────────────────────────────
GLTF_URL = "https://dl.polyhaven.org/Barrel_01_1k.gltf"
BIN_URL = "https://dl.polyhaven.org/Barrel_01.bin"
TEX_URL = "https://dl.polyhaven.org/Barrel_01_diff_1k.jpg"
HDR_URL = "https://dl.polyhaven.org/sky_1k.hdr"

_ASSETS = {
    "Barrel_01": {"tags": ["barrel", "explosive"], "categories": ["industrial"]},
    "wooden_table_02": {"tags": ["table", "wood", "furniture"], "categories": ["furniture"]},
}
_HDRIS = {"sunset_sky": {"tags": ["sunset", "sky"], "categories": ["sunset"]}}


def fake_opener(url: str) -> bytes:
    if url.endswith("/assets?type=models"):
        return json.dumps(_ASSETS).encode()
    if url.endswith("/assets?type=hdris"):
        return json.dumps(_HDRIS).encode()
    if url.endswith("/files/Barrel_01"):
        return json.dumps({"gltf": {"1k": {"gltf": {
            "url": GLTF_URL, "md5": "", "include": {
                "Barrel_01.bin": {"url": BIN_URL, "md5": ""},
                "textures/diff.jpg": {"url": TEX_URL, "md5": ""}}}}}}).encode()
    if url.endswith("/files/sunset_sky"):
        return json.dumps({"hdri": {"1k": {"hdr": {"url": HDR_URL, "md5": ""}}}}).encode()
    # file downloads → fake bytes
    return b"BINARY:" + url.rsplit("/", 1)[-1].encode()


def test_search_matches_and_ranks():
    ph = PolyHaven(opener=fake_opener)
    hits = ph.search("barrel", "models")
    assert hits and hits[0]["id"] == "Barrel_01"
    assert ph.search("table", "models")[0]["id"] == "wooden_table_02"


def test_resolve_model_collects_gltf_and_includes():
    ph = PolyHaven(opener=fake_opener)
    plan = ph.resolve("Barrel_01", "models", "1k")
    rels = {f.rel_path for f in plan.all_files}
    assert plan.main.rel_path == "Barrel_01_1k.gltf"
    assert "Barrel_01.bin" in rels and "textures/diff.jpg" in rels     # dependencies included


def test_download_writes_all_files_preserving_paths(tmp_path):
    ph = PolyHaven(opener=fake_opener)
    plan = ph.resolve("Barrel_01", "models", "1k")
    res = ph.download(plan, str(tmp_path))
    assert res["status"] == "success" and res["count"] == 3
    folder = tmp_path / "Barrel_01"
    assert (folder / "Barrel_01_1k.gltf").exists()
    assert (folder / "textures" / "diff.jpg").exists()               # nested include path kept
    assert res["main"].endswith("Barrel_01_1k.gltf")


def test_checksum_mismatch_aborts(tmp_path):
    def bad_opener(url):
        if url.endswith("/files/Barrel_01"):
            return json.dumps({"gltf": {"1k": {"gltf": {
                "url": GLTF_URL, "md5": "deadbeef", "include": {}}}}}).encode()
        return b"not-the-expected-bytes"
    ph = PolyHaven(opener=bad_opener)
    plan = ph.resolve("Barrel_01", "models", "1k")
    res = ph.download(plan, str(tmp_path))
    assert res["status"] == "error" and "hecksum" in res["message"]


def test_fetch_hdri_end_to_end(tmp_path):
    res = fetch("sunset", "hdris", "1k", dest_root=str(tmp_path), opener=fake_opener)
    assert res["status"] == "success" and res["asset_id"] == "sunset_sky"
    assert res["main"].endswith(".hdr")


def test_fetch_reports_no_match(tmp_path):
    res = fetch("dragon_statue_xyz", "models", "1k", dest_root=str(tmp_path), opener=fake_opener)
    assert res["status"] == "not_found"


@pytest.mark.skipif(not _online(), reason="offline")
def test_live_download_small_hdri(tmp_path):
    res = fetch("kloppenheim", "hdris", "1k", dest_root=str(tmp_path))
    assert res["status"] == "success"
    assert os.path.getsize(res["main"]) > 10_000        # a real .hdr file, not an error page
