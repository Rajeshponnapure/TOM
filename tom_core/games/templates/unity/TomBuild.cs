// Editor build script TOM runs in batch mode:
//   Unity.exe -batchmode -nographics -quit -projectPath <game> -executeMethod TomBuild.Build -logFile build.log
// It makes the scene in code (camera + the game component), applies the window settings and builds a
// Windows player into Build/. Exit code 0 only when the build succeeded.
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class TomBuild
{
    public static void Build()
    {
        var cfg = JsonUtility.FromJson<TomConfig>(File.ReadAllText("Assets/StreamingAssets/config.json"));
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var camera = new GameObject("Main Camera");
        camera.tag = "MainCamera";
        var cam = camera.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.orthographic = true;
        var game = new GameObject("Game");
        if (cfg.genre == "runner") game.AddComponent<RunnerGame>();
        else game.AddComponent<SnakeGame>();
        Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene, "Assets/Scenes/Main.unity");

        PlayerSettings.productName = cfg.title;
        PlayerSettings.companyName = "TOM";
        PlayerSettings.defaultScreenWidth = cfg.width;
        PlayerSettings.defaultScreenHeight = cfg.height;
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.resizableWindow = false;
        PlayerSettings.runInBackground = true;

        var exe = string.Join("_", cfg.title.Split(Path.GetInvalidFileNameChars())).Replace(' ', '_');
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Scenes/Main.unity" },
            locationPathName = "Build/" + exe + ".exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,
        });
        Debug.Log("TOM_BUILD " + report.summary.result + " " + report.summary.outputPath);
        EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
    }
}
