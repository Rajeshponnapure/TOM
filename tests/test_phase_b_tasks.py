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

def test_fileops_undo_latest_organization(tmp_path, monkeypatch):
    from tools import file_ops
    monkeypatch.setattr(file_ops, "JOURNAL_PATH", tmp_path / "journal.json")
    ops = file_ops.FileOps()
    for name in ["a.pdf", "b.jpg"]:
        (tmp_path / name).write_text("x")
    organize = ops.plan_organize_by_type(str(tmp_path))
    completed = ops.execute_plan(organize)
    ops.record_organization(organize, completed)
    undo = ops.plan_undo_last_organization(str(tmp_path))
    assert undo["status"] == "plan" and len(undo["moves"]) == 2
    restored = ops.execute_undo_plan(undo)
    assert restored["moved"] == 2
    assert sorted(path.name for path in tmp_path.iterdir()) == ["a.pdf", "b.jpg", "journal.json"]

def test_fileops_moves_only_requested_pdfs(tmp_path):
    from tools.file_ops import FileOps
    for name in ["report.pdf", "photo.jpg", "notes.txt"]:
        (tmp_path / name).write_text("x")
    plan = FileOps().plan_move_by_extension(str(tmp_path), ".pdf", "pdfs")
    assert plan["summary"] == {"pdfs": 1}
    FileOps().execute_plan(plan)
    assert (tmp_path / "pdfs" / "report.pdf").is_file()
    assert (tmp_path / "photo.jpg").is_file()
    assert (tmp_path / "notes.txt").is_file()

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
    assert r.detect("revert what you have done to my downloads") == "fileops"
    assert r.detect("revert what you have done just now") == "fileops"
    assert r.detect("scrape the tables from https://x.com/p") == "webrecipes"
    assert r.detect("run shell: echo hi") == "coderun"
    assert r.detect("schedule: daily briefing every 24 hours") == "schedule"
    assert r.detect("give me the daily briefing") == "news"
    assert r.detect("schedule a meeting with bob") is None
    assert r.detect("i organized my thoughts about it") is None

def test_nlp_marks_explicit_file_commands_as_tasks():
    from tools.nlp_parser import CommandParser
    parsed = CommandParser().parse("revert what you have done just now in my downloads")
    assert parsed["intent"] == "file_operation"
    assert parsed["execution_mode"] == "task"


def test_nlp_keeps_a_greeting_as_chat_and_exposes_linguistic_analysis():
    from tools.nlp_parser import CommandParser, deep_analyze
    parsed = CommandParser().parse("Hi TOM, how are you today?")
    assert parsed["intent"] == "chat"
    assert parsed["execution_mode"] == "chat"
    analysis = deep_analyze("Move the PDF files from Downloads into PDFs.")
    assert analysis["available"] is True
    assert analysis["action"] == "move"
    assert analysis["target"] == "the PDF files"


def test_regression_correction_wording_reaches_the_file_engine():
    """Wording from the user's own screenshots stays a real, verifiable task."""
    from tools import memory_rules
    from tools.engine_router import EngineRouter
    text = "no, you didn't revert the changes"
    assert memory_rules.is_correction(text)             # kept, so TOM learns from it
    assert memory_rules.is_preference_statement(text)
    assert not memory_rules.is_pure_preference(text)    # ...and still acts on it now
    assert EngineRouter().detect(text) == "fileops"     # never answered as plain chat


def test_engine_success_is_verified_against_the_filesystem(tmp_path):
    from tools.engine_router import EngineRouter
    moved = tmp_path / "pdfs"
    moved.mkdir()
    target = moved / "a.pdf"
    target.write_text("x")
    result = {"status": "success", "message": "Done: 1 file(s) processed",
              "completed_moves": [[str(tmp_path / "a.pdf"), str(target)]]}
    verification = EngineRouter().verify("fileops", "move the pdfs", result)
    assert verification["checked"] is True and verification["ok"] is True
    assert "confirmed on disk" in verification["evidence"]


def test_unconfirmed_engine_success_is_never_reported_as_done(tmp_path):
    from tools.engine_router import EngineRouter
    router = EngineRouter()
    downgraded = router._apply_verification(
        "documents", "write report.pdf",
        {"status": "success", "message": "Wrote report.pdf",
         "path": str(tmp_path / "report.pdf")})
    assert downgraded["status"] == "error"
    assert downgraded["message"].startswith("I could not confirm")
    assert downgraded["verification"]["checked"] is True

    # An engine that declares no artifact keeps its own structured status, and
    # the fact that nothing could be re-checked is recorded, not faked.
    unverifiable = router._apply_verification(
        "ml", "train a model",
        {"status": "success", "message": "accuracy 0.9", "output": "accuracy 0.9"})
    assert unverifiable["status"] == "success"
    assert unverifiable["verification"]["checked"] is False
