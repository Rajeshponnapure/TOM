// The games themselves (Unity versions of TOM's snake and runner — same rules and layout as pygame/Godot).
using System.Collections.Generic;
using UnityEngine;

public class SnakeGame : TomGame
{
    static readonly Dictionary<string, Vector2Int> Dirs = new Dictionary<string, Vector2Int> {
        { "up", new Vector2Int(0, -1) }, { "down", new Vector2Int(0, 1) },
        { "left", new Vector2Int(-1, 0) }, { "right", new Vector2Int(1, 0) } };

    int cols, rows, cell, x0, y0, moveEvery, tick;
    List<Vector2Int> body = new List<Vector2Int>();
    readonly List<Vector2Int> turns = new List<Vector2Int>();
    Vector2Int heading, food;
    bool hasFood;

    protected override void ResetRound()
    {
        cols = cfg.game.cols > 0 ? cfg.game.cols : 24;
        rows = cfg.game.rows > 0 ? cfg.game.rows : 17;
        cell = Mathf.Min(W / cols, (H - HUD) / rows);
        x0 = (W - cell * cols) / 2;
        y0 = HUD + (H - HUD - cell * rows) / 2;
        moveEvery = Mathf.Max(1, cfg.game.move_every > 0 ? cfg.game.move_every : 7);
        var c = new Vector2Int(cols / 2, rows / 2);
        body = new List<Vector2Int> { c, c - new Vector2Int(1, 0), c - new Vector2Int(2, 0) };
        heading = new Vector2Int(1, 0);
        turns.Clear();
        tick = 0;
        PlaceFood();
    }

    void PlaceFood()
    {
        var free = new List<Vector2Int>();
        for (int x = 0; x < cols; x++)
            for (int y = 0; y < rows; y++)
                if (!body.Contains(new Vector2Int(x, y))) free.Add(new Vector2Int(x, y));
        hasFood = free.Count > 0;
        if (hasFood) food = free[rng.Next(free.Count)];
    }

    protected override void Step()
    {
        foreach (var kv in Dirs)
        {
            if (Tapped(kv.Key) || (Held(kv.Key) && turns.Count == 0))
            {
                var last = turns.Count > 0 ? turns[turns.Count - 1] : heading;
                if (kv.Value != last && kv.Value != -last && turns.Count < 2) turns.Add(kv.Value);
            }
        }
        tick++;
        if (tick % moveEvery != 0) return;
        if (turns.Count > 0) { heading = turns[0]; turns.RemoveAt(0); }
        var head = body[0] + heading;
        bool grow = hasFood && head == food;
        var rest = new List<Vector2Int>(body);
        if (!grow) rest.RemoveAt(rest.Count - 1);
        if (head.x < 0 || head.y < 0 || head.x >= cols || head.y >= rows || rest.Contains(head)) { End(); return; }
        rest.Insert(0, head);
        body = rest;
        if (grow)
        {
            score++;
            PlaceFood();
            if (!hasFood) End();
        }
    }

    void Cell(Vector2Int p, int[] color) { Box(x0 + p.x * cell + 1, y0 + p.y * cell + 1, cell - 2, cell - 2, color); }

    protected override void Paint()
    {
        int bw = cell * cols + 6, bh = cell * rows + 6;
        Box(x0 - 3, y0 - 3, bw, 3, cfg.colors.accent);
        Box(x0 - 3, y0 - 3 + bh - 3, bw, 3, cfg.colors.accent);
        Box(x0 - 3, y0 - 3, 3, bh, cfg.colors.accent);
        Box(x0 - 3 + bw - 3, y0 - 3, 3, bh, cfg.colors.accent);
        if (hasFood) Cell(food, cfg.colors.target);
        for (int i = 0; i < body.Count; i++) Cell(body[i], i == 0 ? cfg.colors.player : cfg.colors.player_accent);
    }
}

public class RunnerGame : TomGame
{
    const int Ground = 80;
    float speed, jump, gravity, y, vy;
    int floorY, gap;
    Rect player;
    readonly List<float[]> obstacles = new List<float[]>();   // x, w, h, scored

    protected override void ResetRound()
    {
        speed = Or(cfg.game.speed, 6f);
        jump = Or(cfg.game.jump, -15.5f);
        gravity = Or(cfg.game.gravity, 0.8f);
        floorY = H - Ground;
        player = new Rect(110, floorY - 48, 34, 48);
        y = player.y;
        vy = 0f;
        obstacles.Clear();
        gap = 60;
    }

    protected override void Step()
    {
        bool onGround = player.yMax >= floorY;
        if (onGround && (Held("action") || Held("up"))) vy = jump;
        vy += gravity;
        y = Mathf.Min(y + vy, floorY - player.height);
        if (y >= floorY - player.height) vy = 0f;
        player.y = (int)y;
        gap--;
        if (gap <= 0)
        {
            obstacles.Add(new float[] { W, rng.Next(22, 41), rng.Next(30, 67), 0f });
            gap = rng.Next(55, 111) + (int)(120f / Mathf.Max(1f, speed / 6f));
        }
        foreach (var ob in obstacles)
        {
            ob[0] -= speed;
            if (ob[3] == 0f && ob[0] + ob[1] < player.x) { ob[3] = 1f; score++; speed = Mathf.Min(14f, speed + 0.08f); }
        }
        obstacles.RemoveAll(o => o[0] <= -60);
        foreach (var ob in obstacles)
            if (player.Overlaps(new Rect((int)ob[0], floorY - ob[2], ob[1], ob[2]))) { End(); return; }
    }

    protected override void Paint()
    {
        Box(0, floorY, W, Ground, cfg.colors.ground);
        foreach (var ob in obstacles) Box((int)ob[0], floorY - ob[2], ob[1], ob[2], cfg.colors.hazard);
        Box(player.x, player.y, player.width, player.height, cfg.colors.player);
    }
}
