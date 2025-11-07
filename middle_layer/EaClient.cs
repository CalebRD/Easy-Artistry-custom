using System.Diagnostics;
using System.Text.Json;
using System.Collections.Concurrent;

namespace EasyArtistry.MiddleLayer;

public sealed class EaClient : IDisposable
{
    private readonly Process _proc;
    private readonly StreamWriter _stdin;
    private readonly Task _reader;
    private readonly ConcurrentDictionary<string, TaskCompletionSource<JsonElement>> _pending = new();

    public EaClient(string pythonExe, string workerPy, string? workingDir = null)
    {
        var psi = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = $"-u \"{workerPy}\"",  // -u 关闭缓冲，确保实时通讯
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            WorkingDirectory = workingDir ?? Path.GetDirectoryName(workerPy)!
        };

        _proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _proc.Start();

        _stdin = _proc.StandardInput;

        // 异步读取响应 & 事件
        _reader = Task.Run(async () =>
        {
            using var sr = _proc.StandardOutput;
            string? line;
            while ((line = await sr.ReadLineAsync()) != null)
            {
                JsonDocument doc;
                try { doc = JsonDocument.Parse(line); }
                catch { continue; } // 非协议行（理论上不会出现）
                var root = doc.RootElement;
                if (!root.TryGetProperty("id", out var idProp)) continue;
                var id = idProp.GetString()!;
                if (_pending.TryRemove(id, out var tcs))
                    tcs.TrySetResult(root);
            }
        });
    }

    private async Task<JsonElement> CallAsync(string method, object @params, CancellationToken ct = default)
    {
        var id = Guid.NewGuid().ToString("N");
        var tcs = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        _pending[id] = tcs;

        var payload = JsonSerializer.Serialize(new { id, method, @params },
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });

        await _stdin.WriteLineAsync(payload);
        await _stdin.FlushAsync();

        using var reg = ct.Register(() =>
        {
            if (_pending.TryRemove(id, out var t)) t.TrySetCanceled(ct);
        });

        return await tcs.Task.ConfigureAwait(false);
    }

    // 强类型方法：生成图片（映射到 backend_main.generate_image_from_prompt）
    public async Task<IReadOnlyList<string>> GenerateAsync(
        string prompt,
        string size = "1024x1024",
        int n = 1,
        string model = "stable-diffusion",
        string preset = "balanced",
        string negativePrompt = "bad quality",
        object? sdOverrides = null,
        CancellationToken ct = default)
    {
        var res = await CallAsync("images.generate", new
        {
            prompt,
            size,
            n,
            model,
            preset,
            negative_prompt = negativePrompt,
            sd_params = sdOverrides ?? new { }
        }, ct);

        if (res.TryGetProperty("error", out var e))
        {
            var msg = e.TryGetProperty("message", out var m) ? m.GetString() : "error";
            throw new InvalidOperationException(msg);
        }

        var list = new List<string>();
        foreach (var x in res.GetProperty("result").EnumerateArray())
            list.Add(x.GetString() ?? "");
        return list;
    }

    // 兜底：便于后续快速接新方法（无需升级 DLL）
    public Task<JsonElement> CallRawAsync(string method, object @params, CancellationToken ct = default)
        => CallAsync(method, @params, ct);

    public void Dispose()
    {
        try { if (!_proc.HasExited) _proc.Kill(true); } catch { }
        _proc.Dispose();
    }
}
