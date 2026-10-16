using System.IO;
using System.Text.Json;

namespace QwenAnimeLauncher.Models;

public sealed class AppSettings
{
    public string VideoFile { get; set; } = @"Resources\splash.mp4";

    public string TargetQwenPath { get; set; } =
        @"C:\Users\Z\AppData\Local\Programs\QianwenApp\qianwen.exe";

    public string TargetQwenArguments { get; set; } = "--launch-from=startmenu";

    public string TargetQwenWorkingDirectory { get; set; } =
        @"C:\Users\Z\AppData\Local\Programs\QianwenApp";

    public int MonitorIndex { get; set; } = 0;

    public double PlayDurationSeconds { get; set; } = 7.0;

    public double GraceSeconds { get; set; } = 15.0;

    public int PauseBeforeLaunchMs { get; set; } = 0;

    public bool MuteAudio { get; set; } = true;

    public bool EnableVlcLog { get; set; } = false;

    public bool LoopVideo { get; set; } = false;

    public bool AllowEscToSkip { get; set; } = true;

    public bool ShowCursor { get; set; } = false;

    // ---- layered (transparent character) mode ----------------------------------
    public string RenderMode { get; set; } = "video";   // "video" or "layered"

    public string CharacterFramesDir { get; set; } = @"Resources\character";

    public string FramePattern { get; set; } = "frame_";   // file name prefix, e.g. frame_

    public string FrameExtension { get; set; } = ".png";

    public int FramePadding { get; set; } = 5;             // digits in the number, e.g. 00000

    public int FrameStartIndex { get; set; } = 0;

    public int CharacterFrameCount { get; set; } = 0;      // 0 = auto-detect from disk

    public int FrameRate { get; set; } = 30;

    public double CharacterScale { get; set; } = 1.0;

    public double CharacterOffsetX { get; set; } = 0;

    public double CharacterOffsetY { get; set; } = 0;

    public string Title { get; set; } = "Qwen";

    public string Subtitle { get; set; } = "AI  ·  Wisdom  ·  Future";

    public bool EnableParticles { get; set; } = true;

    public string ResolveVideoPath(string baseDirectory) =>
        Path.IsPathRooted(VideoFile)
            ? VideoFile
            : Path.Combine(baseDirectory, VideoFile);

    public string ResolveFramesDir(string baseDirectory) =>
        Path.IsPathRooted(CharacterFramesDir)
            ? CharacterFramesDir
            : Path.Combine(baseDirectory, CharacterFramesDir);

    public static AppSettings LoadOrDefaults(string baseDirectory)
    {
        try
        {
            string path = Path.Combine(baseDirectory, "Config", "settings.json");
            if (File.Exists(path))
            {
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                    ReadCommentHandling = JsonCommentHandling.Skip,
                    AllowTrailingCommas = true,
                };
                string json = File.ReadAllText(path);
                var settings = JsonSerializer.Deserialize<AppSettings>(json, options);
                if (settings is not null)
                {
                    return settings;
                }
            }
        }
        catch (Exception ex)
        {
            Log($"Failed to read settings.json, using defaults: {ex.Message}");
        }

        return new AppSettings();
    }

    internal static void Log(string message)
    {
        try
        {
            string path = Path.Combine(AppContext.BaseDirectory, "launcher.log");
            File.AppendAllText(path, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}{Environment.NewLine}");
        }
        catch
        {
            // logging must never throw
        }
    }
}
