"""Do a task inside a game: "build a house in minecraft", "find a village in minecraft", "in Green Hell
find water".

Minecraft (the Bedrock edition — what runs in BlueStacks, on Windows and consoles) is driven through its
own chat commands, the exact and checkable way to act in it: /fill and /setblock build a structure
block by block next to the player, /locate finds a structure or biome and answers with coordinates, /tp
goes there. TOM opens chat, types each command into the game window, then reads the game's reply on
screen (Tesseract) — "no permission" means cheats are off in that world, and TOM says so instead of
claiming it built anything.

Any other game: the task becomes the goal for the vision explorer (tools.game_autopilot) — real input,
honest report, no pretend success.

Input only ever goes to the game's own window (it pauses if anything else is in front), and the
whole run is approved once, on the exact list of commands.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── what the owner asked for ───────────────────────────────────────────────
_TASK = re.compile(
    r"^(?:(?:please|can you|could you|tom)\s+)*(?:in|inside|on)\s+(?P<game1>[^,]+?)\s*,\s*(?P<task1>.+)$"
    r"|^(?:(?:please|can you|could you|tom)\s+)*(?:in|inside|on)\s+(?P<game3>[\w' :-]+?)[, ]+\s*(?P<task3>.+)$"
    r"|^(?:(?:please|can you|could you|tom)\s+)*(?P<task2>(?:build|make|create|find|locate|search for|look for|"
    r"get|give me|collect|go to|teleport|set|make it|change|craft|explore|survive|fight|kill|mine|dig)\b.+?)"
    r"\s+(?:in|inside|on)\s+(?:my\s+|the\s+)?(?P<game2>[\w' :-]+?)(?:\s+game)?[.!?]*$", re.IGNORECASE)


def parse(text: str) -> Optional[Tuple[str, str]]:
    """(game, task) for an in-game task request, else None."""
    m = _TASK.match((text or "").strip())
    if not m:
        return None
    game = next((m.group(g) for g in ("game1", "game3", "game2") if m.group(g)), "").strip()
    task = next((m.group(t) for t in ("task1", "task3", "task2") if m.group(t)), "").strip().rstrip(".!?")
    if not game or not task or len(game) > 40:
        return None
    return game, task


def is_minecraft(game: str) -> bool:
    return bool(re.search(r"\bminecraft\b|\bmcpe\b", game or "", re.IGNORECASE))


# ── Minecraft: tasks → commands ────────────────────────────────────────────
MATERIALS = {
    "wood": "oak_planks", "wooden": "oak_planks", "oak": "oak_planks", "stone": "stone", "cobblestone": "cobblestone",
    "brick": "brick_block", "bricks": "brick_block", "glass": "glass", "gold": "gold_block", "golden": "gold_block",
    "diamond": "diamond_block", "iron": "iron_block", "sandstone": "sandstone", "quartz": "quartz_block",
    "obsidian": "obsidian", "concrete": "white_concrete", "stone brick": "stonebrick", "stone bricks": "stonebrick",
}
STRUCTURES = {
    "village": "village", "villages": "village", "stronghold": "stronghold", "end portal": "stronghold",
    "temple": "desert_pyramid", "desert temple": "desert_pyramid", "pyramid": "desert_pyramid",
    "jungle temple": "jungle_temple", "shipwreck": "shipwreck", "ocean monument": "monument",
    "monument": "monument", "mansion": "mansion", "woodland mansion": "mansion", "outpost": "pillager_outpost",
    "pillager outpost": "pillager_outpost", "ruined portal": "ruined_portal", "mineshaft": "mineshaft",
    "buried treasure": "buried_treasure", "treasure": "buried_treasure", "igloo": "igloo",
    "witch hut": "swamp_hut", "fortress": "fortress", "nether fortress": "fortress", "bastion": "bastion_remnant",
    "ancient city": "ancient_city", "trail ruins": "trail_ruins", "trial chamber": "trial_chambers",
    "ocean ruins": "ruins",
}
BIOMES = ("desert", "jungle", "ocean", "plains", "forest", "taiga", "savanna", "swamp", "mesa", "badlands",
          "mushroom", "ice", "snow", "beach", "river", "cherry", "mountain", "birch", "dark forest", "bamboo")
ITEMS = {"diamond": "diamond", "diamonds": "diamond", "iron": "iron_ingot", "gold": "gold_ingot", "emerald": "emerald",
         "emeralds": "emerald", "sword": "diamond_sword", "pickaxe": "diamond_pickaxe", "axe": "diamond_axe",
         "food": "cooked_beef", "steak": "cooked_beef", "bread": "bread", "torch": "torch", "torches": "torch",
         "elytra": "elytra", "bow": "bow", "arrows": "arrow", "armor": "diamond_chestplate", "shield": "shield",
         "wood": "oak_log", "logs": "oak_log", "tnt": "tnt", "ender pearl": "ender_pearl", "boat": "oak_boat"}


@dataclass
class Plan:
    game: str
    task: str
    commands: List[str] = field(default_factory=list)
    summary: str = ""
    expect: str = ""                    # what a successful reply looks like ("locate", "fill", …)
    needs_cheats: bool = True


def _material(task: str, default: str) -> str:
    t = task.lower()
    for word in sorted(MATERIALS, key=len, reverse=True):
        if re.search(rf"\b{word}\b", t):
            return MATERIALS[word]
    return default


def _size(task: str, default: int, lo: int = 3, hi: int = 31) -> int:
    m = re.search(r"\b(\d{1,2})\s*(?:x\s*\d{1,2}\s*)?(?:blocks?|wide|tall|high|long|by)?\b", task)
    if m:
        return max(lo, min(hi, int(m.group(1))))
    if re.search(r"\b(big|large|huge|giant|tall)\b", task, re.I):
        return min(hi, default * 2)
    if re.search(r"\b(small|tiny|little)\b", task, re.I):
        return max(lo, default // 2 + 1)
    return default


def minecraft_plan(task: str) -> Optional[Plan]:
    """Bedrock commands for a task, all relative to the player (~), built just in front (+x/+z)."""
    t = task.lower().strip()
    if re.search(r"\b(build|make|create|construct)\b", t):
        if re.search(r"\b(house|home|hut|cabin|shelter|base)\b", t):
            n = _size(t, 7, 5, 15)
            wall = _material(t, "oak_planks")
            x0, x1, z0, z1, h = 2, 2 + n - 1, 2, 2 + n - 1, 4
            mid = (z0 + z1) // 2
            cmds = [f"/fill ~{x0} ~-1 ~{z0} ~{x1} ~-1 ~{z1} cobblestone",
                    f"/fill ~{x0} ~ ~{z0} ~{x1} ~{h} ~{z1} {wall} hollow",
                    f"/fill ~{x0} ~{h + 1} ~{z0} ~{x1} ~{h + 1} ~{z1} stonebrick",
                    f"/fill ~{x0} ~ ~{mid} ~{x0} ~1 ~{mid} air",
                    f"/fill ~{x1} ~2 ~{mid - 1} ~{x1} ~2 ~{mid + 1} glass",
                    f"/setblock ~{(x0 + x1) // 2} ~2 ~{z0} glass",
                    f"/setblock ~{(x0 + x1) // 2} ~2 ~{z1} glass",
                    f"/setblock ~{x0 + 1} ~ ~{z0 + 1} crafting_table",
                    f"/setblock ~{x0 + 2} ~ ~{z0 + 1} furnace",
                    f"/setblock ~{x1 - 1} ~2 ~{mid} torch"]
            return Plan("Minecraft", task, cmds, f"a {n}x{n} {wall.replace('_', ' ')} house with a door, windows, "
                                                  "a crafting table and a furnace, right next to you", "fill")
        if re.search(r"\btower\b", t):
            n, h = 5, _size(t, 16, 6, 60)
            m = _material(t, "stonebrick")
            return Plan("Minecraft", task, [f"/fill ~2 ~ ~2 ~{2 + n - 1} ~{h} ~{2 + n - 1} {m} hollow",
                                            f"/fill ~2 ~ ~4 ~2 ~1 ~4 air",
                                            f"/fill ~3 ~ ~3 ~3 ~{h - 1} ~3 ladder"],
                        f"a {h}-block {m.replace('_', ' ')} tower beside you", "fill")
        if re.search(r"\bwall\b", t):
            n = _size(t, 15, 3, 60)
            m = _material(t, "cobblestone")
            return Plan("Minecraft", task, [f"/fill ~2 ~ ~-{n // 2} ~2 ~3 ~{n // 2} {m}"],
                        f"a {n}-block {m.replace('_', ' ')} wall in front of you", "fill")
        if re.search(r"\bbridge\b", t):
            n = _size(t, 20, 5, 60)
            m = _material(t, "oak_planks")
            return Plan("Minecraft", task, [f"/fill ~1 ~-1 ~-1 ~{n} ~-1 ~1 {m}",
                                            f"/fill ~1 ~ ~-2 ~{n} ~ ~-2 oak_fence", f"/fill ~1 ~ ~2 ~{n} ~ ~2 oak_fence"],
                        f"a {n}-block bridge ahead of you", "fill")
        if re.search(r"\b(pool|pond)\b", t):
            n = _size(t, 7, 3, 20)
            return Plan("Minecraft", task, [f"/fill ~2 ~-4 ~2 ~{n + 3} ~-1 ~{n + 3} stone",
                                            f"/fill ~3 ~-3 ~3 ~{n + 2} ~-1 ~{n + 2} water"],
                        f"a {n}x{n} pool next to you", "fill")
        if re.search(r"\bpyramid\b", t):
            n = _size(t, 11, 5, 31) | 1
            m = _material(t, "sandstone")
            cmds = [f"/fill ~{2 + i} ~{i} ~{2 + i} ~{2 + n - 1 - i} ~{i} ~{2 + n - 1 - i} {m}" for i in range((n + 1) // 2)]
            return Plan("Minecraft", task, cmds, f"a {m.replace('_', ' ')} pyramid {n} blocks wide", "fill")
        if re.search(r"\b(platform|floor|island)\b", t):
            n = _size(t, 9, 3, 40)
            m = _material(t, "stone")
            return Plan("Minecraft", task, [f"/fill ~-{n // 2} ~-1 ~-{n // 2} ~{n // 2} ~-1 ~{n // 2} {m}"],
                        f"a {n}x{n} platform under you", "fill")
        # no structure named ("make it day", "make it creative"): fall through to the other intents below
    if re.search(r"\b(find|locate|search for|look for|where is|go to|take me to|teleport to)\b", t):
        go = bool(re.search(r"\b(go to|take me|teleport|travel)\b", t))
        for word in sorted(STRUCTURES, key=len, reverse=True):
            if re.search(rf"\b{word}\b", t):
                return Plan("Minecraft", task, [f"/locate structure {STRUCTURES[word]}"],
                            f"the nearest {word}" + (" and take you there" if go else ""), "locate:go" if go else "locate")
        for biome in BIOMES:
            if re.search(rf"\b{biome}\b", t):
                return Plan("Minecraft", task, [f"/locate biome {biome.replace(' ', '_')}"],
                            f"the nearest {biome} biome" + (" and take you there" if go else ""), "locate:go" if go else "locate")
        return None
    m = re.search(r"\b(?:give me|get me|get|i need|collect)\s+(?:some\s+|a\s+|an\s+)?(\d+\s+)?([a-z ]+?)$", t)
    if m:
        name = m.group(2).strip()
        item = ITEMS.get(name) or ITEMS.get(name.rstrip("s"))
        if item:
            count = int(m.group(1)) if m.group(1) else (1 if item in ("elytra", "diamond_sword", "diamond_pickaxe",
                                                                       "diamond_axe", "shield", "bow", "oak_boat",
                                                                       "diamond_chestplate") else 32)
            return Plan("Minecraft", task, [f"/give @s {item} {min(count, 64)}"], f"{count} {name}", "give")
    if re.search(r"\b(day|daytime|morning|sunrise)\b", t):
        return Plan("Minecraft", task, ["/time set day"], "daytime", "time")
    if re.search(r"\b(night|midnight)\b", t):
        return Plan("Minecraft", task, ["/time set night"], "night", "time")
    if re.search(r"\b(clear weather|stop (?:the )?rain|sunny)\b", t):
        return Plan("Minecraft", task, ["/weather clear"], "clear weather", "weather")
    if re.search(r"\bcreative\b", t):
        return Plan("Minecraft", task, ["/gamemode creative"], "creative mode", "gamemode")
    if re.search(r"\bsurvival\b", t):
        return Plan("Minecraft", task, ["/gamemode survival"], "survival mode", "gamemode")
    return None


# ── reading the game's answer ──────────────────────────────────────────────
_LOCATED = re.compile(r"(?:nearest|closest)\s+([\w ]+?)\s+is\s+at\s+\[?\s*(-?\d+)\s*,\s*\(?(-?\d+|y\?|~)\)?\s*,\s*(-?\d+)",
                      re.IGNORECASE)
_DENIED = re.compile(r"cheats?\s+(?:are\s+)?(?:not|disabled)|do(?:es)?\s+not\s+have\s+permission|"
                     r"you do not have permission|unknown command|syntax error|not allowed|unknown block|"
                     r"cannot place|too many blocks|not loaded|outside (?:of )?the world|invalid", re.IGNORECASE)


def read_reply(text: str) -> Dict[str, Any]:
    """What the game said back after a command (OCR text of its chat)."""
    t = " ".join((text or "").split())
    m = _LOCATED.search(t)
    if m:
        y = m.group(3)
        return {"ok": True, "kind": "located", "what": m.group(1).strip(), "x": int(m.group(2)),
                "y": int(y) if y.lstrip("-").isdigit() else None, "z": int(m.group(4))}
    d = _DENIED.search(t)
    if d:
        return {"ok": False, "kind": "denied", "said": d.group(0)}
    if re.search(r"\b(\d+)\s+blocks?\s+(?:filled|placed)|block placed|gave\b|set the time|changed the weather|"
                 r"game mode", t, re.IGNORECASE):
        return {"ok": True, "kind": "done"}
    return {"ok": None, "kind": "unclear"}


# ── typing into a game window ──────────────────────────────────────────────
def type_text(text: str, send_vk: Optional[Callable[[int, bool], None]] = None, gap: float = 0.012) -> None:
    """Type ASCII text as real key presses (VkKeyScan → scan code, Shift when needed). Games and
    emulators that ignore pasted/unicode text still read these."""
    import ctypes
    from tools.game_autopilot import _send_scancode
    user32 = ctypes.windll.user32
    shift = 0x2A

    def key(vk_scan: int, down: bool) -> None:
        if send_vk is not None:
            send_vk(vk_scan, down)
        else:
            _send_scancode(vk_scan, down)

    caps = bool(user32.GetKeyState(0x14) & 1)          # Caps Lock on: letters come out flipped otherwise
    for ch in text:
        res = user32.VkKeyScanW(ord(ch))
        if res == -1:
            continue
        vk, mods = res & 0xFF, (res >> 8) & 0xFF
        scan = user32.MapVirtualKeyW(vk, 0)
        need_shift = bool(mods & 1) != (caps and ch.isalpha())
        if need_shift:
            key(shift, True)
        key(scan, True)
        key(scan, False)
        if need_shift:
            key(shift, False)
        time.sleep(gap)


class MinecraftDriver:
    """Opens chat in the focused Minecraft window, types one command, presses Enter, reads the reply.
    Everything OS-facing is injectable so tests need no game."""

    def __init__(self, hwnd: int, ocr: Optional[Callable[[], str]] = None, typer: Optional[Callable[[str], None]] = None,
                 press: Optional[Callable[[str], bool]] = None, foreground: Optional[Callable[[], bool]] = None):
        from tools import game_autopilot as ga
        self.hwnd = hwnd
        self.typer = typer or type_text
        self.press = press or (lambda k: ga.press_action(k, 0.05))
        self.foreground = foreground or (lambda: ga.is_foreground(hwnd))
        self.ocr = ocr or self._ocr_window

    def _ocr_window(self) -> str:
        from tom_core.screen_control import ScreenControl
        try:
            return " ".join(line.text for line in ScreenControl().read())
        except Exception:
            return ""

    def _typed(self, command: str) -> Optional[bool]:
        """Is the command visible in the chat box? None when the screen can't be read (no OCR).
        One blank frame (OCR catching a redraw) is retried before the screen counts as unreadable."""
        text = self.ocr()
        if not text.strip():
            time.sleep(0.25)
            text = self.ocr()
        if not text.strip():
            return None
        probe = command.lstrip("/").split()[0].lower()       # fill, locate, give ...
        return probe in text.lower()

    def run(self, command: str, settle: float = 1.2) -> Dict[str, Any]:
        """Open chat, type, check it is really in the chat box, Enter. If T did not open chat, try the
        other way in (the / key, which opens chat with the slash already typed)."""
        ways = (("t", command), ("/", command[1:] if command.startswith("/") else command))
        for opener, text in ways:
            if not self.foreground():
                return {"ok": False, "kind": "not_focused", "command": command}
            self.typer(opener)
            time.sleep(0.6)
            if not self.foreground():
                return {"ok": False, "kind": "not_focused", "command": command}
            self.typer(text)
            time.sleep(0.3)
            seen = self._typed(command)
            if seen:
                break
            if seen is False or opener == "t":           # not in the chat box (or no way to tell):
                self.press("ESC")                         # close it and try the other way in
                time.sleep(0.4)
                continue
            break                                         # last way in, unreadable: send it and read the reply
        else:
            return {"ok": False, "kind": "chat_failed", "command": command}
        self.press("ENTER")
        time.sleep(settle)
        reply = read_reply(self.ocr())
        reply["command"] = command
        return reply


def run_minecraft(plan: Plan, driver: "MinecraftDriver") -> Dict[str, Any]:
    """Run each command; stop at the first refusal. Follow a /locate with /tp when asked to go there."""
    replies: List[Dict[str, Any]] = []
    for cmd in plan.commands:
        r = driver.run(cmd)
        replies.append(r)
        if r["kind"] in ("denied", "not_focused", "chat_failed"):
            break
    found = next((r for r in replies if r["kind"] == "located"), None)
    if found and plan.expect == "locate:go":
        y = "~" if found["y"] is None else str(found["y"])
        replies.append(driver.run(f"/tp @s {found['x']} {y} {found['z']}"))
    denied = next((r for r in replies if r["kind"] == "denied"), None)
    unfocused = next((r for r in replies if r["kind"] == "not_focused"), None)
    if unfocused:
        return {"status": "error", "replies": replies, "message": (
            "Minecraft lost focus (another window came to the front), so I stopped typing. Nothing was typed "
            "anywhere else.")}
    if any(r["kind"] == "chat_failed" for r in replies):
        return {"status": "error", "replies": replies, "fallback": "play", "message": (
            "I couldn't open Minecraft's chat (tried the T key and the / key), so no command was entered.")}
    if denied:
        return {"status": "error", "replies": replies, "fallback": "play", "message": (
            f"Minecraft refused \"{denied['command']}\" (\"{denied['said']}\"). Commands need cheats turned on for "
            "this world: pause → Settings → Game → Activate Cheats. Then ask me again.")}
    if plan.expect.startswith("locate"):
        if not found:
            return {"status": "unverified", "replies": replies, "message": (
                f"I typed {plan.commands[0]} but couldn't read Minecraft's answer on screen, so I can't tell you "
                "where it is — look at the chat.")}
        where = f"x {found['x']}, z {found['z']}" + (f" (y {found['y']})" if found["y"] is not None else "")
        went = " and teleported you there" if plan.expect == "locate:go" else ""
        return {"status": "success", "replies": replies, "location": found,
                "message": f"Found {plan.summary.replace(' and take you there', '')} at {where}{went}."}
    confirmed = any(r["kind"] == "done" for r in replies)
    return {"status": "success" if confirmed else "unverified", "replies": replies, "verified": confirmed,
            "message": (f"Built {plan.summary} ({len(plan.commands)} commands)." if confirmed and plan.expect == "fill"
                        else f"Done: {plan.summary}." if confirmed else
                        f"I typed {len(replies)} command(s) for {plan.summary}, but couldn't read Minecraft's "
                        "confirmation on screen — have a look in the game.")}
