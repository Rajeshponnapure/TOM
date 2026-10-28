// Runtime shared by every Unity game TOM makes: config, input, game-over/restart, HUD, stats.
// Same contract as TOM's pygame and Godot runtimes: frame-based logic in Update(), colours by role from
// StreamingAssets/config.json, everything drawn with IMGUI in the same 800x600 layout, and a headless
// self-test (MyGame.exe -batchmode -nographics -logFile - --selftest=600) that plays with a random bot
// and logs one line "TOM_SELFTEST {json}" before quitting.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

[Serializable] public class TomColors { public int[] background, player, player_accent, target, hazard, ground, accent, text; }
[Serializable] public class TomSettings { public int cols, rows, move_every; public float speed, jump, gravity; }
[Serializable] public class TomConfig
{
    public string title = "Game";
    public string genre = "snake";
    public int width = 800, height = 600, fps = 60;
    public TomColors colors;
    public TomSettings game;
}
[Serializable] public class TomStats { public int score, best, rounds, frames; public bool over; public string title; public double updated; }

public abstract class TomGame : MonoBehaviour
{
    protected const int HUD = 44;
    static readonly string[] Moves = { "up", "down", "left", "right", "action" };

    protected TomConfig cfg;
    protected int W = 800, H = 600;
    protected System.Random rng;
    protected int score, best, rounds = 1, frame;
    protected bool over;

    int selftest;
    System.Random bot;
    readonly List<string> botHeld = new List<string>();
    int botLeft;
    HashSet<string> held = new HashSet<string>(), prev = new HashSet<string>();
    readonly HashSet<string> taps = new HashSet<string>();
    float lastSave;
    Texture2D white;
    GUIStyle small, big;
    float sx = 1f, sy = 1f;

    void Start()
    {
        cfg = JsonUtility.FromJson<TomConfig>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath, "config.json")));
        W = cfg.width;
        H = cfg.height;
        if (cfg.game == null) cfg.game = new TomSettings();
        foreach (var arg in Environment.GetCommandLineArgs())
            if (arg.StartsWith("--selftest=")) selftest = int.Parse(arg.Substring("--selftest=".Length));
        rng = new System.Random(selftest > 0 ? 7 : Environment.TickCount);
        if (selftest > 0) bot = new System.Random(7);
        QualitySettings.vSyncCount = 0;
        Application.targetFrameRate = selftest > 0 ? -1 : cfg.fps;
        Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);
        var cam = Camera.main;
        if (cam != null) cam.backgroundColor = Col(cfg.colors.background);
        white = Texture2D.whiteTexture;
        ResetRound();
    }

    protected static Color Col(int[] c) { return new Color32((byte)c[0], (byte)c[1], (byte)c[2], 255); }
    protected static float Or(float value, float fallback) { return value != 0f ? value : fallback; }

    void Poll()
    {
        prev = held;
        held = new HashSet<string>();
        taps.Clear();
        if (bot != null)
        {
            if (botLeft <= 0)
            {
                botLeft = bot.Next(4, 19);
                botHeld.Clear();
                if (over) botHeld.Add("restart");
                else for (int i = bot.Next(0, 3); i > 0; i--) botHeld.Add(Moves[bot.Next(0, Moves.Length)]);
            }
            botLeft--;
            foreach (var a in botHeld) held.Add(a);
            return;
        }
        Read("up", KeyCode.UpArrow, KeyCode.W);
        Read("down", KeyCode.DownArrow, KeyCode.S);
        Read("left", KeyCode.LeftArrow, KeyCode.A);
        Read("right", KeyCode.RightArrow, KeyCode.D);
        Read("action", KeyCode.Space, KeyCode.Space);
        Read("restart", KeyCode.R, KeyCode.Return);
    }

    void Read(string action, KeyCode a, KeyCode b)
    {
        if (Input.GetKey(a) || Input.GetKey(b)) held.Add(action);
        if (Input.GetKeyDown(a) || Input.GetKeyDown(b)) taps.Add(action);
    }

    protected bool Held(string a) { return held.Contains(a); }
    protected bool Tapped(string a) { return taps.Contains(a) || (held.Contains(a) && !prev.Contains(a)); }

    void Update()
    {
        Poll();
        if (bot == null && Input.GetKeyDown(KeyCode.Escape)) { WriteStats(); Application.Quit(); return; }
        frame++;
        if (over)
        {
            if (Tapped("restart") || Tapped("action")) { rounds++; score = 0; over = false; ResetRound(); }
        }
        else
        {
            Step();
            best = Math.Max(best, score);
        }
        if (Time.realtimeSinceStartup - lastSave > 2f) { WriteStats(); lastSave = Time.realtimeSinceStartup; }
        if (selftest > 0 && frame >= selftest)
        {
            Debug.Log("TOM_SELFTEST " + JsonUtility.ToJson(Stats()));
            Application.Quit();
        }
    }

    protected void End()
    {
        over = true;
        best = Math.Max(best, score);
        WriteStats();
    }

    TomStats Stats()
    {
        return new TomStats { score = score, best = best, rounds = rounds, frames = frame, over = over, title = cfg.title,
                              updated = (DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalSeconds };
    }

    void WriteStats()
    {
        try { File.WriteAllText(Path.Combine(Path.GetDirectoryName(Application.dataPath), "stats.json"), JsonUtility.ToJson(Stats())); }
        catch (Exception) { }
    }

    protected void Box(float x, float y, float w, float h, int[] color)
    {
        GUI.color = Col(color);
        GUI.DrawTexture(new Rect(x * sx, y * sy, w * sx, h * sy), white);
    }

    void OnGUI()
    {
        if (cfg == null || Event.current.type != EventType.Repaint) return;
        sx = Screen.width / (float)W;
        sy = Screen.height / (float)H;
        Box(0, 0, W, H, cfg.colors.background);
        Paint();
        if (small == null)
        {
            small = new GUIStyle(GUI.skin.label) { fontSize = 22 };
            big = new GUIStyle(GUI.skin.label) { fontSize = 56, alignment = TextAnchor.MiddleCenter, fontStyle = FontStyle.Bold };
        }
        small.fontSize = Mathf.RoundToInt(22 * sy);
        big.fontSize = Mathf.RoundToInt(56 * sy);
        small.normal.textColor = big.normal.textColor = Col(cfg.colors.text);
        GUI.color = Color.white;
        GUI.Label(new Rect(12 * sx, 8 * sy, 400 * sx, 30 * sy), "Score " + score + "   Best " + best, small);
        if (over)
        {
            GUI.Label(new Rect(0, (H / 2 - 50) * sy, W * sx, 70 * sy), "Game over", big);
            var hint = new GUIStyle(small) { alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0, (H / 2 + 20) * sy, W * sx, 30 * sy), "Press R, Enter or Space to play again", hint);
        }
    }

    protected abstract void ResetRound();
    protected abstract void Step();
    protected abstract void Paint();
}
