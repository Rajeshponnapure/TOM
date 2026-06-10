"""Pure-logic tests for the unified EngineRouter (no heavy deps needed)."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.engine_router import EngineRouter, _extract_kv_list, _extract_kv_num

ROUTE = {
    "ml regression linear X=[[1],[2]] y=[2,4]": "ml",
    "train a regression model on my dataset": "ml",
    "generate esp32 dht11 mqtt firmware code": "iot",
    "create a verilog counter with width=16": "vlsi",
    "move mouse to 500 300": "hardware",
    "scaffold a pygame platformer called myquest": "gamedev",
    "blender create a terrain": "blender",
    "give me the daily briefing": "news",
    "check dependency conflicts": "deps",
    "update tom": "autoupdate",
    "execute autonomous task: tidy downloads": "autonomous",
    "deploy multi-agent task: write a report": "orchestrator",
    "analyze emotion text: I feel great": "voiceplus",
}
NO_ROUTE = [
    "send an email to bob", "create a word document about cars",
    "open chrome", "what's the weather like today",
    "classify my emails please", "create an excel spreadsheet for budget",
    "search the web for laptops", "whatsapp mom saying hi",
    "write code for a web scraper", "analyze the data in sales.csv",
    "create a website for my bakery", "make a powerpoint about space",
]

def test_routes_detected():
    r = EngineRouter()
    for cmd, key in ROUTE.items():
        assert r.detect(cmd.lower()) == key, f"{cmd!r} should route to {key}"

def test_normal_commands_not_hijacked():
    r = EngineRouter()
    for cmd in NO_ROUTE:
        assert r.detect(cmd.lower()) is None, f"{cmd!r} must NOT route to an engine"

def test_kv_extraction():
    assert _extract_kv_list("X=[[1],[2]] y=[1,2]", "X") == [[1], [2]]
    assert _extract_kv_list("y=[1,2]", "y") == [1, 2]
    assert _extract_kv_list("y=[bad", "y") is None
    assert _extract_kv_num("width=16", "width", 8) == 16
    assert _extract_kv_num("nothing", "width", 8) == 8

def test_unmatched_execute_is_unhandled():
    r = EngineRouter()
    res = asyncio.get_event_loop().run_until_complete(r.execute("hello there"))
    assert res["status"] == "unhandled"
