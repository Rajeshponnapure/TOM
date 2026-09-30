"""filesystem and database were documented (this module's own docstring, and the README's
"Built-in MCP connectors" list) as built-in MCP connectors, but neither was ever registered --
calling either always failed with "No connector 'filesystem'/'database'". These lock in that
both are now real, working connectors registered by MCPManager.with_defaults().
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

import pytest

from tools.mcp_manager import MCPManager


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mgr():
    return MCPManager.with_defaults()


def test_all_eleven_documented_connectors_are_registered(mgr):
    names = {c["name"] for c in mgr.list_connectors()}
    documented = {"github", "gmail", "slack", "notion", "whatsapp", "instagram",
                  "calendar", "weather", "websearch", "filesystem", "database"}
    assert documented <= names, f"missing: {documented - names}"


def test_filesystem_write_read_list_round_trip(mgr, tmp_path):
    target = str(tmp_path / "note.txt")
    r1 = run(mgr.call("filesystem", "write_file", {"path": target, "content": "hello"}))
    assert r1["status"] == "success", r1

    r2 = run(mgr.call("filesystem", "read_file", {"path": target}))
    assert r2["status"] == "success" and r2["data"]["content"] == "hello", r2

    r3 = run(mgr.call("filesystem", "list_directory", {"path": str(tmp_path)}))
    assert r3["status"] == "success"
    assert any(e["name"] == "note.txt" for e in r3["data"])


def test_filesystem_refuses_a_protected_system_path(mgr):
    r = run(mgr.call("filesystem", "read_file", {"path": r"C:\Windows\System32\config\SAM"}))
    assert r["status"] == "error"
    assert "protected" in r["message"].lower()


def test_database_sqlite_create_insert_select_round_trip(mgr, tmp_path):
    conn_str = f"sqlite:///{tmp_path / 'test.db'}"
    r1 = run(mgr.call("database", "query", {
        "connection_string": conn_str, "sql": "CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT)"}))
    assert r1["status"] == "success", r1

    r2 = run(mgr.call("database", "query", {
        "connection_string": conn_str, "sql": "INSERT INTO people (name) VALUES (?)", "params": ["Alice"]}))
    assert r2["status"] == "success" and "1 row" in r2["message"], r2

    r3 = run(mgr.call("database", "query", {
        "connection_string": conn_str, "sql": "SELECT * FROM people"}))
    assert r3["status"] == "success"
    assert r3["data"] == [{"id": 1, "name": "Alice"}]


def test_database_requires_connection_string_and_sql(mgr, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    r1 = run(mgr.call("database", "query", {"sql": "SELECT 1"}))
    assert r1["status"] == "error" and "connection_string" in r1["message"]

    r2 = run(mgr.call("database", "query", {"connection_string": "sqlite:///x.db"}))
    assert r2["status"] == "error" and "sql" in r2["message"]
