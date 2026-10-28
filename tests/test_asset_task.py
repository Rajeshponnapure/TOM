"""The agent's 3D flow: parse subjects, fetch each from Poly Haven, assemble in Blender — fetch and
Blender are stubbed so no network or Blender run in the suite. Routing is checked too."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import agent as agent_mod
from tools.command_router import CommandRouter


@pytest.mark.parametrize("cmd,models,hdri,scene", [
    ("download a 3d model of a barrel", ["barrel"], "", False),
    ("find a 3d asset of a wooden table", ["wooden table"], "", False),
    ("build a blender scene with a barrel and a wooden table under a sunset sky",
     ["barrel", "wooden table"], "sunset sky", True),
    ("create a 3d scene with a chair lit by a studio hdri", ["chair"], "studio hdri", True),
])
def test_parse_3d(cmd, models, hdri, scene):
    m, h, s = agent_mod.TomAgent._parse_3d(cmd)
    assert m == models
    assert (hdri in h or h in hdri or h == hdri)
    assert s == scene


def test_routing_to_asset_task():
    r = CommandRouter()
    for c in ["download a 3d model of a barrel", "build a blender scene with a barrel",
              "create a 3d scene with a chair and a sunset sky", "find a 3d asset of a car"]:
        assert r.route(c).handler == "execute_asset_task", c


def test_download_only_fetches_and_reports(monkeypatch, tmp_path):
    t = object.__new__(agent_mod.TomAgent)
    calls = []
    def fake_fetch(subject, atype, res):
        calls.append((subject, atype))
        folder = os.path.join(tmp_path, subject.replace(" ", "_"))
        os.makedirs(folder, exist_ok=True)
        main = os.path.join(folder, "m.gltf")
        open(main, "w").close()
        return {"status": "success", "asset_id": subject.replace(" ", "_"), "main": main}
    import tools.asset_fetch as af
    monkeypatch.setattr(af, "fetch", fake_fetch)
    out = asyncio.run(agent_mod.TomAgent.execute_asset_task(t, "download a 3d model of a barrel", {}))
    assert out["status"] == "success" and calls == [("barrel", "models")]
    assert out["paths"] and out["paths"][0].endswith("m.gltf")


def test_scene_fetches_models_and_hdri_then_assembles(monkeypatch, tmp_path):
    t = object.__new__(agent_mod.TomAgent)
    def fake_fetch(subject, atype, res):
        return {"status": "success", "asset_id": subject.replace(" ", "_"),
                "main": os.path.join(str(tmp_path), f"{atype}.bin")}
    import tools.asset_fetch as af
    monkeypatch.setattr(af, "fetch", fake_fetch)

    assembled = {}
    class FakeBlender:
        def is_available(self): return True
        def assemble_scene(self, mains, hdri, task):
            assembled["mains"] = list(mains)
            assembled["hdri"] = hdri
            return {"status": "success", "message": "Blender scene saved", "path": "scene.blend"}
    import tools.blender_control as bcmod
    monkeypatch.setattr(bcmod, "BlenderControl", FakeBlender)

    out = asyncio.run(agent_mod.TomAgent.execute_asset_task(
        t, "build a blender scene with a barrel and a wooden table under a sunset sky", {}))
    assert out["status"] == "success"
    assert len(assembled["mains"]) == 2 and assembled["hdri"].endswith("hdris.bin")
    assert "Blender scene saved" in out["message"]


def test_scene_without_blender_still_reports_downloads(monkeypatch, tmp_path):
    t = object.__new__(agent_mod.TomAgent)
    import tools.asset_fetch as af
    monkeypatch.setattr(af, "fetch", lambda s, a, r: {"status": "success", "asset_id": s, "main": "x.gltf"})
    class NoBlender:
        def is_available(self): return False
    import tools.blender_control as bcmod
    monkeypatch.setattr(bcmod, "BlenderControl", NoBlender)
    out = asyncio.run(agent_mod.TomAgent.execute_asset_task(t, "build a 3d scene with a barrel", {}))
    assert out["status"] == "success" and "Blender isn't installed" in out["message"]


def test_nothing_found_is_honest(monkeypatch):
    t = object.__new__(agent_mod.TomAgent)
    import tools.asset_fetch as af
    monkeypatch.setattr(af, "fetch", lambda s, a, r: {"status": "not_found", "message": "no match"})
    out = asyncio.run(agent_mod.TomAgent.execute_asset_task(t, "download a 3d model of a dragon", {}))
    assert out["status"] == "error" and "couldn't fetch" in out["message"].lower()
