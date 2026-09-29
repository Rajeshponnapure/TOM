"""TOM's memory layer with the REAL hindsight-client talking to a local fake Hindsight server.

The older tests use an in-memory stand-in, which cannot show threading problems: the real client
binds its HTTP session to one thread's event loop, and TOM calls it from several threads.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("hindsight_client")

from tools.hindsight_memory import HindsightMemory


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        self.server.requests.append((self.path, body))
        if self.path.endswith("/memories"):
            if self.server.reject_retains:
                return self._send(500, {"detail": "storage unavailable"})
            return self._send(200, {"success": True, "bank_id": "b", "items_count": len(body.get("items", [])),
                                    "async": bool(body.get("async"))})
        if self.path.endswith("/recall"):
            return self._send(200, {"results": [{"id": "1", "text": "PDFs go in Invoices", "type": "world",
                                                 "tags": ["preference"]}]})
        self._send(200, {})

    do_PUT = do_POST

    def do_GET(self):
        self._send(200, {})


@pytest.fixture
def hindsight(tmp_path, monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Fake)
    server.requests, server.reject_retains = [], False
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("HINDSIGHT_BASE_URL", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setenv("TOM_MEMORY_STATE_DIR", str(tmp_path / "mem"))
    monkeypatch.setenv("HINDSIGHT_TIMEOUT_SECONDS", "8")
    monkeypatch.setenv("HINDSIGHT_ENABLED", "1")
    server.memory = HindsightMemory()
    assert server.memory.available, server.memory.last_error
    yield server
    server.shutdown()
    server.server_close()


def stored(server):
    return [b for p, b in server.requests if p.endswith("/memories")]


def test_a_background_retain_after_a_recall_reaches_hindsight(hindsight):
    mem = hindsight.memory
    assert mem.recall("PDFs")                                  # first use binds the client (main thread)
    assert mem.retain("task outcome", tags=["task"], session_id="s1")   # then the background worker thread
    mem.flush()
    assert mem.stats["failed"] == 0, mem.last_error
    assert mem.stats["retained"] == 1 and mem.pending_count() == 0
    assert len(stored(hindsight)) == 1


def test_calls_from_many_threads_all_succeed(hindsight):
    mem = hindsight.memory

    def work(i):
        if i % 2:
            return mem.retain(f"fact {i}", tags=["task"], wait=True)
        return bool(mem.recall("PDFs"))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(work, range(24)))
    assert all(results), (mem.last_error, mem.stats)
    assert mem.stats["failed"] == 0 and mem.stats["retained"] == 12 and mem.pending_count() == 0


def test_recall_from_asyncio_worker_threads_and_retain_can_interleave(hindsight):
    import asyncio
    mem = hindsight.memory

    async def main():
        hits = await asyncio.gather(*[mem.arecall("PDFs") for _ in range(5)])
        mem.retain("after recalls", tags=["preference"], index_now=True)
        return hits
    hits = asyncio.run(main())
    mem.flush()
    assert all(h and h[0].text == "PDFs go in Invoices" for h in hits)
    assert mem.stats["retained"] == 1 and mem.stats["failed"] == 0, mem.last_error


def test_failed_retains_are_queued_reported_and_sent_after_recovery(hindsight):
    mem = hindsight.memory
    hindsight.reject_retains = True
    assert mem.retain("keep this", tags=["preference"], wait=True) is False
    assert mem.pending_count() == 1 and "storage unavailable" in mem.last_error
    line = mem.status_line()
    assert "1 memory is waiting to be saved" in line and "HTTP 500" in line and "storage unavailable" in line
    assert "ONLINE" not in line                                       # a failing store must not look healthy
    hindsight.reject_retains = False
    assert mem.flush_pending() == 1
    assert mem.pending_count() == 0 and mem.stats["retained"] == 1


def test_queued_memories_are_sent_automatically_when_tom_starts(hindsight, tmp_path, monkeypatch):
    mem = hindsight.memory
    hindsight.reject_retains = True
    mem.retain("saved while Hindsight was down", tags=["preference"], wait=True)
    assert mem.pending_count() == 1
    hindsight.reject_retains = False
    restarted = HindsightMemory()                                      # next launch of TOM
    deadline = time.time() + 10
    while restarted.pending_count() and time.time() < deadline:
        time.sleep(0.1)
    assert restarted.pending_count() == 0 and len(stored(hindsight)) >= 2


# ── whole agent: what TOM tells the user must match what Hindsight really did ──
import asyncio


@pytest.fixture
def agent_with_hindsight(hindsight, tmp_path, monkeypatch):
    from tools import hindsight_memory
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOM_LLM_PROVIDER", "ollama")
    hindsight_memory.set_memory(hindsight.memory)
    from agent import TomAgent
    tom = TomAgent()
    assert tom.memory is hindsight.memory
    tom.approval_manager.provider = lambda req: True

    async def no_llm(command):
        return tom.nlp_parser.parse(command)
    monkeypatch.setattr(tom, "understand_command", no_llm)
    yield tom
    hindsight_memory.set_memory(None)


def test_a_correction_is_really_stored_and_only_then_reported_as_saved(agent_with_hindsight, hindsight):
    result = asyncio.run(agent_with_hindsight.execute_task("No — PDFs always go in Invoices, not Documents."))
    assert "Saved to long-term memory" in result["message"] and "NOT saved" not in result["message"]
    texts = [i["content"] for body in stored(hindsight) for i in body["items"]]
    assert any("PDFs always go in Invoices" in t for t in texts), texts
    assert hindsight.memory.stats["retained"] >= 1 and hindsight.memory.pending_count() == 0


def test_when_hindsight_refuses_the_reply_says_so_instead_of_claiming_success(agent_with_hindsight, hindsight):
    hindsight.reject_retains = True
    result = asyncio.run(agent_with_hindsight.execute_task("No — PDFs always go in Invoices, not Documents."))
    message = result["message"]
    assert "NOT saved to Hindsight yet" in message and "storage unavailable" in message
    assert "Saved to long-term memory" not in message
    assert hindsight.memory.pending_count() >= 1
    hindsight.reject_retains = False
    assert hindsight.memory.flush_pending() >= 1 and hindsight.memory.pending_count() == 0


def test_task_outcomes_are_stored_too(agent_with_hindsight, hindsight):
    asyncio.run(agent_with_hindsight.execute_task("hi tom"))
    hindsight.memory.flush()
    texts = [i["content"] for body in stored(hindsight) for i in body["items"]]
    assert any(t.startswith('The user asked TOM: "hi tom"') for t in texts), texts
