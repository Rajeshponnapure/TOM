# Flappy — flap through the gaps between the pillars. Space / Up to flap. Made by TOM.
extends "res://tom_base.gd"

const GROUND := 40

var gravity := 0.42
var flap := -7.4
var gap := 175
var speed := 3.2
var spacing := 270
var bird := Rect2(200, 260, 30, 24)
var vy := 0.0
var pipes: Array = []              # [x, gap_top, scored]
var next_x := 840.0


func reset() -> void:
	gravity = float(game.get("gravity", 0.42))
	flap = float(game.get("flap", -7.4))
	gap = int(game.get("gap", 175))
	speed = float(game.get("speed", 3.2))
	spacing = int(game.get("spacing", 270))
	bird = Rect2(w / 4, h / 2 - 40, 30, 24)
	vy = flap
	pipes = []
	next_x = float(w + 40)


func pipe_rects() -> Array:
	var out: Array = []
	for p in pipes:
		out.append(Rect2(int(p[0]), 0, 70, p[1]))
		out.append(Rect2(int(p[0]), p[1] + gap, 70, h - GROUND - p[1] - gap))
	return out


func step() -> void:
	if tapped("action") or tapped("up"):
		vy = flap
	vy = min(vy + gravity, 10.0)
	bird.position.y += vy
	if bird.position.y < HUD:
		bird.position.y = HUD
		vy = 0.0
	next_x -= speed
	if next_x <= w:
		pipes.append([next_x, rng.randi_range(90, h - GROUND - gap - 40), false])
		next_x += spacing
	for p in pipes:
		p[0] -= speed
		if not p[2] and p[0] + 70 < bird.position.x:
			p[2] = true
			score += 1
	pipes = pipes.filter(func(p): return p[0] > -80)
	var b := Rect2(bird.position.x, int(bird.position.y), bird.size.x, bird.size.y)
	if b.end.y >= h - GROUND:
		end_round()
		return
	for r in pipe_rects():
		if b.intersects(r):
			end_round()
			return


func paint() -> void:
	for r in pipe_rects():
		draw_rect(r, col("hazard"))
	draw_rect(Rect2(0, h - GROUND, w, GROUND), col("ground"))
	draw_rect(Rect2(bird.position.x, int(bird.position.y), bird.size.x, bird.size.y), col("player"))
