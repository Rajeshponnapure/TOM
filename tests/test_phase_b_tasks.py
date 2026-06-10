"""Phase B contracts: file ops, web recipes, runner extensions, scheduling."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_fileops_plan_execute_roundtrip(tmp_path):
    from tools.file_ops import FileOps
    for n in ["a.pdf", "b.jpg", "c.mp3"]:
        (tmp_path / n).write_text("x")
    ops = FileOps()
    plan = ops.plan_organize_by_type(str(tmp_path))
    assert plan["status"] == "plan" and len(plan["moves"]) == 3
    res = ops.execute_plan(plan)
    assert res["moved"] == 3
    assert sorted(os.listdir(tmp_path)) == ["Audio", "Documents", "Images"]

def test_fileops_rename_and_zip(tmp_path):
    from tools.file_ops import FileOps
    (tmp_path / "IMG_1.txt").write_text("x")
    (tmp_path / "IMG_2.txt").write_text("x")
    ops = FileOps()
    plan = ops.plan_bulk_rename(str(tmp_path), "IMG_", "Pic_")
    assert plan["summary"]["renames"] == 2
    ops.execute_plan(plan)
    assert sorted(os.listdir(tmp_path)) == ["Pic_1.txt", "Pic_2.txt"]
    z = ops.zip_folder(str(tmp_path))
    assert z["status"] == "success" and z["files"] == 2

def test_table_parsing_offline():
    from tools.web_recipes import parse_tables_html
    html = "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"
    t = parse_tables_html(html)
    assert t == [[["A"], ["1"]]]

def test_shell_denylist_blocks_destructive():
    from tools.code_runner import CodeRunner
    cr = CodeRunner()
    assert cr.run_shell("shutdown /s")["status"] == "blocked"
    assert cr.run_shell("rm -rf / --no-preserve-root")["status"] == "blocked"
    assert "SAFE" in cr.run_shell("echo SAFE")["message"]

def test_schedule_parser():
    from tools.engine_router import parse_schedule_command as p
    assert p("schedule: check inbox every 2 hours") == ("check inbox", 2.0)
    assert p("daily briefing every morning")[1] == 24.0
    assert p("ping every 30 minutes")[1] == 0.5
    assert p("nothing here") == (None, None)

def test_new_routes_and_no_hijack():
    from tools.engine_router import EngineRouter
    r = EngineRouter()
    assert r.detect("organize my downloads folder by type") == "fileops"
    assert r.detect("scrape the tables from https://x.com/p") == "webrecipes"
    assert r.detect("run shell: echo hi") == "coderun"
    assert r.detect("schedule: daily briefing every 24 hours") == "schedule"
    assert r.detect("give me the daily briefing") == "news"
    assert r.detect("schedule a meeting with bob") is None
    assert r.detect("i organized my thoughts about it") is None
