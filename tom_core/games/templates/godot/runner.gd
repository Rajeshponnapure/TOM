# Endless runner — jump over the obstacles; it speeds up as you go. Space / Up to jump. Made by TOM.
extends "res://tom_base.gd"

const GROUND := 80

var speed := 6.0
var jump := -15.5
var gravity := 0.8
var floor_y := 520
var player := Rect2(110, 472, 34, 48)
var vy := 0.0
var obstacles: Array = []          # [x, w, h, scored]
var gap := 60


func reset() -> void:
	speed = float(game.get("speed", 6.0))
	jump = float(game.get("jump", -15.5))
	gravity = float(game.get("gravity", 0.8))
	floor_y = h - GROUND
	player = Rect2(110, floor_y - 48, 34, 48)
	vy = 0.0
	obstacles = []
	gap = 60


func step() -> void:
	var on_ground := player.end.y >= floor_y
	if on_ground and (is_held("action") or is_held("up")):
		vy = jump
	vy += gravity
	player.position.y = min(player.position.y + vy, floor_y - player.size.y)
	if player.position.y >= floor_y - player.size.y:
		vy = 0.0
	gap -= 1
	if gap <= 0:
		obstacles.append([float(w), rng.randi_range(22, 40), rng.randi_range(30, 66), false])
		gap = rng.randi_range(55, 110) + int(120 / max(1.0, speed / 6.0))
	for ob in obstacles:
		ob[0] -= speed
		if not ob[3] and ob[0] + ob[1] < player.position.x:
			ob[3] = true
			score += 1
			speed = min(14.0, speed + 0.08)
	obstacles = obstacles.filter(func(o): return o[0] > -60)
	for ob in obstacles:
		if player.intersects(Rect2(int(ob[0]), floor_y - ob[2], ob[1], ob[2])):
			end_round()
			return


func paint() -> void:
	draw_rect(Rect2(0, floor_y, w, GROUND), col("ground"))
	for ob in obstacles:
		draw_rect(Rect2(int(ob[0]), floor_y - ob[2], ob[1], ob[2]), col("hazard"))
	draw_rect(Rect2(int(player.position.x), int(player.position.y), player.size.x, player.size.y), col("player"))
