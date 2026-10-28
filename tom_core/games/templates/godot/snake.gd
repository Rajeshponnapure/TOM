# Snake — eat the food, grow, don't hit the walls or yourself. Arrow keys / WASD. Made by TOM.
extends "res://tom_base.gd"

const DIRS := {"up": Vector2i(0, -1), "down": Vector2i(0, 1), "left": Vector2i(-1, 0), "right": Vector2i(1, 0)}

var cols := 24
var rows := 17
var cell := 32
var x0 := 0
var y0 := 0
var move_every := 7
var body: Array = []
var heading := Vector2i(1, 0)
var turns: Array = []
var tick := 0
var food := Vector2i(-1, -1)


func reset() -> void:
	cols = int(game.get("cols", 24))
	rows = int(game.get("rows", 17))
	cell = min(w / cols, (h - HUD) / rows)
	x0 = (w - cell * cols) / 2
	y0 = HUD + (h - HUD - cell * rows) / 2
	move_every = max(1, int(game.get("move_every", 7)))
	var c := Vector2i(cols / 2, rows / 2)
	body = [c, c - Vector2i(1, 0), c - Vector2i(2, 0)]
	heading = Vector2i(1, 0)
	turns = []
	tick = 0
	place_food()


func place_food() -> void:
	var free: Array = []
	for x in cols:
		for y in rows:
			if not body.has(Vector2i(x, y)):
				free.append(Vector2i(x, y))
	food = free[rng.randi_range(0, free.size() - 1)] if free.size() > 0 else Vector2i(-1, -1)


func step() -> void:
	for name in DIRS:
		var d: Vector2i = DIRS[name]
		if tapped(name) or (is_held(name) and turns.is_empty()):
			var last: Vector2i = turns.back() if not turns.is_empty() else heading
			if d != last and d != -last and turns.size() < 2:
				turns.append(d)
	tick += 1
	if tick % move_every != 0:
		return
	if not turns.is_empty():
		heading = turns.pop_front()
	var head: Vector2i = body[0] + heading
	var grow := head == food
	var rest: Array = body.duplicate() if grow else body.slice(0, body.size() - 1)
	if head.x < 0 or head.y < 0 or head.x >= cols or head.y >= rows or rest.has(head):
		end_round()
		return
	body = [head] + rest
	if grow:
		score += 1
		place_food()
		if food == Vector2i(-1, -1):
			end_round()


func cell_rect(p: Vector2i) -> Rect2:
	return Rect2(x0 + p.x * cell + 1, y0 + p.y * cell + 1, cell - 2, cell - 2)


func paint() -> void:
	draw_rect(Rect2(x0 - 3, y0 - 3, cell * cols + 6, cell * rows + 6), col("accent"), false, 3.0)
	if food != Vector2i(-1, -1):
		draw_rect(cell_rect(food), col("target"))
	for i in body.size():
		draw_rect(cell_rect(body[i]), col("player") if i == 0 else col("player_accent"))
