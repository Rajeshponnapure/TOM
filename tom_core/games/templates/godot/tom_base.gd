# Runtime shared by every Godot game TOM makes (Godot 4): config, input, game-over/restart, HUD.
# Same contract as the pygame runtime: frame-based logic, colours by role from config.json, and a
# headless self-test  (godot --headless --path <game> -- --selftest=600)  that plays with a random bot
# and prints one line  TOM_SELFTEST {json}  before quitting.
extends Node2D

const HUD := 44
const ACTIONS := ["up", "down", "left", "right", "action", "restart"]

var cfg: Dictionary = {}
var game: Dictionary = {}
var colors: Dictionary = {}
var rng := RandomNumberGenerator.new()
var w := 800
var h := 600
var score := 0
var best := 0
var rounds := 1
var over := false
var frame := 0
var selftest := 0
var font: Font

var held: Dictionary = {}
var prev_held: Dictionary = {}
var taps: Dictionary = {}
var bot_held: Array = []
var bot_left := 0


func _ready() -> void:
	var f := FileAccess.open("res://config.json", FileAccess.READ)
	cfg = JSON.parse_string(f.get_as_text())
	game = cfg.get("game", {})
	w = int(cfg["width"])
	h = int(cfg["height"])
	for role in cfg["colors"]:
		var c: Array = cfg["colors"][role]
		colors[role] = Color8(int(c[0]), int(c[1]), int(c[2]))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--selftest="):
			selftest = int(arg.split("=")[1])
	if selftest > 0:
		rng.seed = 7
	else:
		rng.randomize()
		Engine.max_fps = int(cfg.get("fps", 60))
	font = ThemeDB.fallback_font
	reset()


func action_for(key: int) -> String:
	match key:
		KEY_UP, KEY_W:
			return "up"
		KEY_DOWN, KEY_S:
			return "down"
		KEY_LEFT, KEY_A:
			return "left"
		KEY_RIGHT, KEY_D:
			return "right"
		KEY_SPACE:
			return "action"
		KEY_R, KEY_ENTER:
			return "restart"
		KEY_ESCAPE:
			return "quit"
	return ""


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var a := action_for(event.physical_keycode if event.physical_keycode != 0 else event.keycode)
		if a != "":
			taps[a] = true


func poll() -> void:
	prev_held = held
	held = {}
	if selftest > 0:
		if bot_left <= 0:
			bot_left = rng.randi_range(4, 18)
			bot_held = []
			if over:
				bot_held = ["restart"]
			else:
				for i in rng.randi_range(0, 2):
					bot_held.append(["up", "down", "left", "right", "action"][rng.randi_range(0, 4)])
		bot_left -= 1
		for a in bot_held:
			held[a] = true
		return
	var keys := {"up": [KEY_UP, KEY_W], "down": [KEY_DOWN, KEY_S], "left": [KEY_LEFT, KEY_A],
		"right": [KEY_RIGHT, KEY_D], "action": [KEY_SPACE], "restart": [KEY_R, KEY_ENTER]}
	for a in keys:
		for k in keys[a]:
			if Input.is_physical_key_pressed(k) or Input.is_key_pressed(k):
				held[a] = true


func is_held(a: String) -> bool:
	return held.has(a)


func tapped(a: String) -> bool:
	return taps.has(a) or (held.has(a) and not prev_held.has(a))


func col(role: String) -> Color:
	return colors[role]


func end_round() -> void:
	over = true
	best = max(best, score)


func _process(_delta: float) -> void:
	poll()
	if taps.has("quit"):
		get_tree().quit()
		return
	frame += 1
	if over:
		if tapped("restart") or tapped("action"):
			rounds += 1
			score = 0
			over = false
			reset()
	else:
		step()
		best = max(best, score)
	taps.clear()
	queue_redraw()
	if selftest > 0 and frame >= selftest:
		var stats := {"score": score, "best": best, "rounds": rounds, "over": over, "frames": frame,
			"title": cfg.get("title", "")}
		print("TOM_SELFTEST " + JSON.stringify(stats))
		get_tree().quit()


func _draw() -> void:
	draw_rect(Rect2(0, 0, w, h), col("background"))
	paint()
	draw_string(font, Vector2(12, 30), "Score %d   Best %d" % [score, best], HORIZONTAL_ALIGNMENT_LEFT, -1, 22, col("text"))
	if over:
		draw_string(font, Vector2(0, h / 2 - 10), "Game over", HORIZONTAL_ALIGNMENT_CENTER, w, 52, col("text"))
		draw_string(font, Vector2(0, h / 2 + 30), "Press R, Enter or Space to play again", HORIZONTAL_ALIGNMENT_CENTER, w, 22, col("text"))


# ── overridden by each game ──────────────────────────────────────────────
func reset() -> void:
	pass


func step() -> void:
	pass


func paint() -> void:
	pass
