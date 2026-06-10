"""Phase A reliability contracts: preflight, universal-fallback gating, crash guard."""
import sys, os, threading, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_preflight_pure_and_actionable():
    from tools.preflight import check, check_all, fix_hint, CHECKS
    res = check_all()
    assert set(res) == set(CHECKS)
    for r in res.values():
        assert isinstance(r["ok"], bool)
        if not r["ok"]:
            assert r["missing"], "failed check must say what's missing"
    # always-available capabilities must pass anywhere
    for cid in ("vlsi", "iot", "gamedev", "code_run"):
        assert check(cid)["ok"] is True

def test_universal_gating_conservative():
    from tools.task_heuristics import should_attempt_universal as s
    assert s("task", "organize all my photos into folders by year", enabled=True)
    assert not s("chat", "how are you today", enabled=True)
    assert not s("question", "what is the capital of france", enabled=True)
    assert not s("task", "do it", enabled=True)              # too short
    assert not s("task", "organize my files now please", enabled=False)  # kill switch

def test_crash_guard_writes_reports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib
    import tools.crash_guard as cg
    importlib.reload(cg)  # rebind _LOG_DIR to tmp cwd
    p = cg.write_crash("unit", RuntimeError, RuntimeError("x"), None)
    assert p and os.path.isfile(p)
    cg.install("unit")
    def boom():
        raise RuntimeError("thread boom")
    t = threading.Thread(target=boom); t.start(); t.join(); time.sleep(0.2)
    crashes = [f for f in os.listdir(tmp_path / "tom_logs") if f.startswith("crash_")]
    assert len(crashes) >= 2
