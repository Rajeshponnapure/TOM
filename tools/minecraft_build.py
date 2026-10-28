"""Blueprints TOM builds in Minecraft (Bedrock) with commands — exact, block by block, next to the player.

"build a modern 3 floor duplex house with all facilities" → `blueprint(request)` → a list of `Part`s, each
one /fill or /setblock command with a plain description ("kitchen: cooker, sink and fridge"). Coordinates
are relative to where the player stands (~), and the whole build sits in front of them (+x, +z), so it
works anywhere in any world. Every /fill stays under Bedrock's 32 768-block limit.

The modern house: white concrete shell with grey floor bands, full-height glass on the front and sides,
a front balcony with glass railings, stairs between floors, light strips in every ceiling, and rooms —
ground: living room (sofa, TV, coffee table), kitchen (counters, cooker, smoker, sink, fridge), dining;
upper floors: bedrooms (beds, wardrobes, bedside lamps), bathroom (tub, shower, sink), study (bookshelves,
desk), home theatre; plus a rooftop terrace, a back-garden pool, a lawn and a path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

MAX_FILL = 32768


@dataclass(frozen=True)
class Part:
    command: str
    what: str


def _volume(cmd: str) -> int:
    nums = [int(n or 0) for n in re.findall(r"~(-?\d*)", cmd)[:6]]
    if len(nums) < 6:
        return 1
    x1, y1, z1, x2, y2, z2 = nums
    return (abs(x2 - x1) + 1) * (abs(y2 - y1) + 1) * (abs(z2 - z1) + 1)


def fill(x1, y1, z1, x2, y2, z2, block: str, mode: str = "") -> str:
    return f"/fill ~{x1} ~{y1} ~{z1} ~{x2} ~{y2} ~{z2} {block}" + (f" {mode}" if mode else "")


def setblock(x, y, z, block: str) -> str:
    return f"/setblock ~{x} ~{y} ~{z} {block}"


def floors_in(request: str, default: int = 2) -> int:
    r = (request or "").lower()
    words = {"one": 1, "single": 1, "two": 2, "double": 2, "three": 3, "triple": 3, "four": 4}
    m = re.search(r"\b(\d)\s*[- ]?\s*(?:floor|stor(?:e)?y|storey|level)s?\b", r)
    if m:
        return max(1, min(4, int(m.group(1))))
    m = re.search(r"\b(one|single|two|double|three|triple|four)[- ]?(?:floor|stor(?:e)?y|storey|level)s?\b", r)
    if m:
        return words[m.group(1)]
    if "duplex" in r:
        return 2
    return default


def modern_house(floors: int = 3) -> List[Part]:
    """A modern house, `floors` storeys of 5 blocks, 20 x 16 footprint, at x 4..23, z 4..19."""
    X0, X1, Z0, Z1 = 4, 23, 4, 19
    top = 5 * floors                                     # roof slab height
    p: List[Part] = []
    add = lambda cmd, what: p.append(Part(cmd, what))   # noqa: E731

    # site: clear trees/terrain, level the ground, lawn
    add(fill(-3, 0, -3, 30, 24, 30, "air"), "clear the building site")
    add(fill(-3, -1, -3, 30, -1, 30, "grass_block"), "level lawn")
    add(fill(-3, -3, -3, 30, -2, 30, "dirt", "replace air"), "fill holes under the lawn")
    # shell: one hollow box for all storeys, then floor slabs
    add(fill(X0, 0, Z0, X1, top, Z1, "white_concrete", "hollow"), f"{floors}-storey white concrete shell")
    add(fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, "smooth_quartz"), "ground-floor quartz floor")
    for f in range(1, floors):
        y = 5 * f
        add(fill(X0 + 1, y, Z0 + 1, X1 - 1, y, Z1 - 1, "smooth_quartz"), f"floor {f + 1} slab")
        add(fill(X0, y, Z0, X1, y, Z1, "gray_concrete", "outline"), f"grey band at floor {f + 1}")
    add(fill(X0 - 1, top, Z0 - 1, X1 + 1, top, Z1 + 1, "gray_concrete"), "flat roof with an overhang")
    # glass: big front windows, side and back windows on every floor
    for f in range(floors):
        y = 5 * f
        add(fill(X0 + 2, y + 1, Z0, X1 - 2, y + 3, Z0, "glass"), f"front glass wall, floor {f + 1}")
        add(fill(X0, y + 2, Z0 + 3, X0, y + 3, Z1 - 3, "glass"), f"left windows, floor {f + 1}")
        add(fill(X1, y + 2, Z0 + 3, X1, y + 3, Z1 - 3, "glass"), f"right windows, floor {f + 1}")
        add(fill(X0 + 3, y + 2, Z1, X1 - 3, y + 3, Z1, "glass"), f"back windows, floor {f + 1}")
        add(fill(X0 + 3, y + 4, Z0 + 3, X1 - 3, y + 4, Z0 + 3, "sea_lantern"), f"ceiling light strip, floor {f + 1}")
        add(fill(X0 + 3, y + 4, Z1 - 3, X1 - 3, y + 4, Z1 - 3, "sea_lantern"), f"second light strip, floor {f + 1}")
    # entrance: opening, canopy, path
    add(fill(12, 1, Z0, 15, 3, Z0, "air"), "front entrance")
    add(fill(11, 4, Z0 - 3, 16, 4, Z0 - 1, "gray_concrete"), "entrance canopy")
    add(fill(12, -1, -3, 15, -1, Z0 - 1, "smooth_stone"), "front path")
    add(setblock(11, 1, Z0 - 1, "lantern"), "entrance lamp")
    add(setblock(16, 1, Z0 - 1, "lantern"), "entrance lamp")
    # stairs between floors (along +x at the back, with a hole in the slab above)
    for f in range(floors - 1):
        y = 5 * f
        for i in range(4):
            add(fill(X0 + 12 + i, y + 1 + i, Z1 - 3, X0 + 12 + i, y + 1 + i, Z1 - 2,
                     'quartz_stairs ["weirdo_direction"=0]'), f"stairs floor {f + 1}→{f + 2}, step {i + 1}")
        add(fill(X0 + 12, y + 5, Z1 - 3, X0 + 16, y + 5, Z1 - 2, "air"), f"stairwell opening to floor {f + 2}")
    # balcony on the front of floor 2
    if floors >= 2:
        add(fill(X0 + 2, 5, Z0 - 3, X1 - 2, 5, Z0 - 1, "gray_concrete"), "front balcony")
        add(fill(X0 + 2, 6, Z0 - 3, X1 - 2, 6, Z0 - 3, "glass_pane"), "balcony glass railing")
        add(fill(10, 6, Z0, 17, 7, Z0, "air"), "balcony door")

    # ── ground floor: living room, kitchen, dining ──
    add(fill(X0 + 1, 1, Z0 + 9, X0 + 9, 4, Z0 + 9, "light_gray_concrete"), "wall between living room and kitchen")
    add(fill(X0 + 4, 1, Z0 + 9, X0 + 6, 3, Z0 + 9, "air"), "doorway to the kitchen")
    add(fill(X0 + 2, 1, Z0 + 2, X0 + 2, 1, Z0 + 7, "gray_wool"), "sofa (long side)")
    add(fill(X0 + 3, 1, Z0 + 7, X0 + 5, 1, Z0 + 7, "gray_wool"), "sofa (short side)")
    add(fill(X0 + 4, 1, Z0 + 3, X0 + 5, 1, Z0 + 5, "dark_oak_planks"), "coffee table")
    add(fill(X0 + 8, 1, Z0 + 3, X0 + 9, 1, Z0 + 5, "white_carpet"), "living-room rug")
    add(fill(X0 + 1, 2, Z0 + 3, X0 + 1, 3, Z0 + 5, "black_concrete"), "wall TV")
    add(fill(X0 + 1, 1, Z0 + 10, X0 + 1, 1, Z1 - 1, "smooth_quartz"), "kitchen counter")
    add(setblock(X0 + 1, 1, Z0 + 11, "smoker"), "kitchen smoker")
    add(setblock(X0 + 1, 1, Z0 + 12, "furnace"), "kitchen cooker")
    add(setblock(X0 + 1, 1, Z0 + 13, "cauldron"), "kitchen sink")
    add(fill(X0 + 1, 1, Z0 + 14, X0 + 1, 2, Z0 + 14, "iron_block"), "fridge")
    add(fill(X0 + 1, 3, Z0 + 10, X0 + 1, 3, Z1 - 1, "barrel"), "kitchen wall cabinets")
    add(fill(X0 + 4, 1, Z0 + 11, X0 + 6, 1, Z0 + 13, "smooth_quartz"), "kitchen island")
    add(setblock(X0 + 5, 1, Z0 + 12, "crafting_table"), "worktop on the island")
    add(fill(X0 + 11, 1, Z0 + 11, X0 + 14, 1, Z0 + 12, "spruce_planks"), "dining table")
    add(fill(X0 + 11, 1, Z0 + 10, X0 + 14, 1, Z0 + 10, "spruce_stairs"), "dining chairs")
    add(setblock(X0 + 12, 2, Z0 + 11, "flower_pot"), "table centrepiece")

    # ── floor 2: master bedroom, bathroom, study ──
    if floors >= 2:
        y = 5
        add(fill(X0 + 10, y + 1, Z0 + 1, X0 + 10, y + 4, Z1 - 4, "light_gray_concrete"), "wall: bedroom | bathroom")
        add(fill(X0 + 10, y + 1, Z0 + 5, X0 + 10, y + 3, Z0 + 6, "air"), "bedroom door")
        add(setblock(X0 + 3, y + 1, Z0 + 4, 'bed ["direction"=0,"head_piece_bit"=false]'), "master bed (foot)")
        add(setblock(X0 + 3, y + 1, Z0 + 5, 'bed ["direction"=0,"head_piece_bit"=true]'), "master bed (head)")
        add(setblock(X0 + 4, y + 1, Z0 + 4, 'bed ["direction"=0,"head_piece_bit"=false]'), "master bed (second half)")
        add(setblock(X0 + 4, y + 1, Z0 + 5, 'bed ["direction"=0,"head_piece_bit"=true]'), "master bed (second half)")
        add(fill(X0 + 2, y + 1, Z0 + 6, X0 + 5, y + 1, Z0 + 6, "dark_oak_planks"), "headboard")
        add(setblock(X0 + 2, y + 2, Z0 + 6, "lantern"), "bedside lamp")
        add(setblock(X0 + 5, y + 2, Z0 + 6, "lantern"), "bedside lamp")
        add(fill(X0 + 1, y + 1, Z0 + 8, X0 + 1, y + 3, Z0 + 10, "barrel"), "wardrobe")
        add(setblock(X0 + 8, y + 1, Z0 + 2, "chest"), "storage chest")
        add(fill(X0 + 2, y + 1, Z0 + 2, X0 + 7, y + 1, Z0 + 3, "light_blue_carpet"), "bedroom carpet")
        add(fill(X0 + 12, y + 1, Z0 + 1, X1 - 1, y + 1, Z0 + 6, "smooth_quartz"), "bathroom floor")
        add(fill(X0 + 13, y + 1, Z0 + 2, X0 + 15, y + 1, Z0 + 3, "cauldron"), "bath tub")
        add(fill(X1 - 3, y + 1, Z0 + 4, X1 - 1, y + 3, Z0 + 6, "glass", "hollow"), "glass shower")
        add(setblock(X1 - 2, y + 4, Z0 + 5, "sea_lantern"), "shower light")
        add(setblock(X0 + 12, y + 1, Z0 + 6, "cauldron"), "bathroom sink")
        add(fill(X0 + 11, y + 1, Z0 + 7, X1 - 1, y + 4, Z0 + 7, "light_gray_concrete"), "wall: bathroom | study")
        add(fill(X0 + 15, y + 1, Z0 + 7, X0 + 16, y + 3, Z0 + 7, "air"), "study door")
        add(fill(X1 - 1, y + 1, Z0 + 8, X1 - 1, y + 3, Z0 + 12, "bookshelf"), "study bookshelves")
        add(fill(X0 + 13, y + 1, Z0 + 10, X0 + 15, y + 1, Z0 + 10, "dark_oak_planks"), "study desk")
        add(setblock(X0 + 14, y + 2, Z0 + 10, "lectern"), "reading stand")

    # ── floor 3: second bedroom, home theatre ──
    if floors >= 3:
        y = 10
        add(fill(X0 + 10, y + 1, Z0 + 1, X0 + 10, y + 4, Z1 - 4, "light_gray_concrete"), "wall: bedroom 2 | theatre")
        add(fill(X0 + 10, y + 1, Z0 + 5, X0 + 10, y + 3, Z0 + 6, "air"), "door")
        add(setblock(X0 + 3, y + 1, Z0 + 4, 'bed ["direction"=0,"head_piece_bit"=false]'), "bed 2 (foot)")
        add(setblock(X0 + 3, y + 1, Z0 + 5, 'bed ["direction"=0,"head_piece_bit"=true]'), "bed 2 (head)")
        add(fill(X0 + 1, y + 1, Z0 + 8, X0 + 1, y + 3, Z0 + 9, "barrel"), "wardrobe 2")
        add(setblock(X0 + 6, y + 1, Z0 + 2, "lantern"), "desk lamp")
        add(fill(X0 + 2, y + 1, Z0 + 2, X0 + 7, y + 1, Z0 + 3, "pink_carpet"), "bedroom 2 carpet")
        add(fill(X0 + 11, y + 1, Z0 + 1, X1 - 1, y + 1, Z1 - 4, "black_carpet"), "theatre carpet")
        add(fill(X1 - 1, y + 2, Z0 + 3, X1 - 1, y + 4, Z0 + 8, "black_concrete"), "cinema screen")
        add(fill(X0 + 13, y + 1, Z0 + 4, X0 + 13, y + 1, Z0 + 8, "red_wool"), "theatre seats, row 1")
        add(fill(X0 + 15, y + 1, Z0 + 4, X0 + 15, y + 1, Z0 + 8, "red_wool"), "theatre seats, row 2")
        add(setblock(X0 + 12, y + 1, Z0 + 10, "jukebox"), "sound system")

    # roof terrace, pool, garden
    add(fill(X0, top + 1, Z0, X1, top + 1, Z1, "glass_pane", "outline"), "rooftop terrace railing")
    add(fill(X0 + 2, top + 1, Z0 + 2, X0 + 6, top + 1, Z0 + 4, "spruce_planks"), "rooftop deck")
    add(setblock(X0 + 4, top + 2, Z0 + 3, "lantern"), "rooftop light")
    add(fill(6, -4, 22, 21, -1, 28, "smooth_quartz"), "pool basin")
    add(fill(7, -3, 23, 20, -1, 27, "water"), "swimming pool")
    add(fill(6, -1, 20, 21, -1, 21, "smooth_stone"), "pool deck")
    add(fill(-2, 0, 6, -2, 0, 17, "oak_leaves"), "garden hedge")
    for x, z in ((0, 8), (0, 12), (0, 16), (27, 8), (27, 14)):
        add(setblock(x, 0, z, "poppy"), "garden flowers")
    add(setblock(0, 0, 2, "lantern"), "garden light")
    return p


def view_command(floors: int = 3) -> str:
    """Move the player back and up to look at the finished build (last: it changes where ~ is)."""
    return f"/tp @s ~-10 ~{4 + 2 * floors} ~-12 facing ~14 ~{2 * floors} ~12"


def blueprint(request: str) -> Optional[List[Part]]:
    r = (request or "").lower()
    if re.search(r"\b(house|home|villa|duplex|mansion|bungalow|apartment|building)\b", r):
        return modern_house(floors_in(r, default=3 if "duplex" in r and re.search(r"\b3|three", r) else 2))
    return None


def check(parts: List[Part]) -> List[str]:
    """Problems with a blueprint before anything is typed (too-large fills)."""
    return [f"{pt.what}: {pt.command} is {_volume(pt.command)} blocks (limit {MAX_FILL})"
            for pt in parts if pt.command.startswith("/fill") and _volume(pt.command) > MAX_FILL]
