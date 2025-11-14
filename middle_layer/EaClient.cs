using System.Diagnostics;
using System.Text.Json;
using System.Collections.Concurrent;
using System.Windows;

namespace EasyArtistry.MiddleLayer;

public sealed class EaClient : IDisposable
{
    public event Action<string>? OnError;
    private readonly Process _proc;
    private readonly StreamWriter _stdin;
    private readonly Task _reader;
    private readonly Task _stderrReader;
    private readonly ConcurrentDictionary<string, TaskCompletionSource<JsonElement>> _pending = new();

    public EaClient(string pythonExe, string workerPy, string? workingDir = null)
    {
        var psi = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = $"-u \"{workerPy}\"",  // -u: unbuffered, ensures real-time communication
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

        // Asynchronously read each line of JSON returned by the worker
        _reader = Task.Run(async () =>
        {
            using var sr = _proc.StandardOutput;
            string? line;
            while ((line = await sr.ReadLineAsync()) != null)
            {
                JsonDocument doc;
                try
                {
                    doc = JsonDocument.Parse(line);
                }
                catch
                {
                    // Non-protocol line, ignore (should not happen in theory)
                    continue;
                }

                var root = doc.RootElement;
                if (!root.TryGetProperty("id", out var idProp)) continue;
                var id = idProp.GetString();
                if (string.IsNullOrEmpty(id)) continue;

                if (_pending.TryRemove(id!, out var tcs))
                {
                    tcs.TrySetResult(root);
                }
            }
        });

        // Forward worker stderr to the parent console for easier debugging
        // _stderrReader = Task.Run(async () =>
        // {
        //     using var sr = _proc.StandardError;
        //     string? line;
        //     while ((line = await sr.ReadLineAsync()) != null)
        //     {
        //         OnError?.Invoke(line);
        //     }
        // });
        _stderrReader = Task.Run(async () =>
        {
            using var sr = _proc.StandardError;
            string? line;
            while ((line = await sr.ReadLineAsync()) != null)
            {
                Console.Error.WriteLine($"[Python STDERR] {line}");
            }
        });
    }

    // Core call: send a {id, method, params} and wait for the corresponding response
    private async Task<JsonElement> CallAsync(string method, object @params, CancellationToken ct = default)
    {
        var id = Guid.NewGuid().ToString("N");
        var tcs = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        _pending[id] = tcs;

        var payload = JsonSerializer.Serialize(
            new { id, method, @params },
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }
        );

        await _stdin.WriteLineAsync(payload);
        await _stdin.FlushAsync();

        using var reg = ct.Register(() =>
        {
            if (_pending.TryRemove(id, out var t))
            {
                t.TrySetCanceled(ct);
            }
        });

        return await tcs.Task.ConfigureAwait(false);
    }

    private static void ThrowIfError(JsonElement root)
    {
        if (root.TryGetProperty("error", out var e))
        {
            string? msg = null;
            if (e.ValueKind == JsonValueKind.Object)
            {
                if (e.TryGetProperty("message", out var m))
                    msg = m.GetString();
            }
            msg ??= "backend error";
            throw new InvalidOperationException(msg);
        }
    }

    // ================= Publicly available methods =================

    /// <summary>
    /// Generate image (calls backend_main.generate_image_from_prompt)
    /// </summary>
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
        var root = await CallAsync("images.generate", new
        {
            prompt,
            size,
            n,
            model,
            preset,
            negative_prompt = negativePrompt,
            sd_params = sdOverrides ?? new { }
        }, ct);

        ThrowIfError(root);

        var result = root.GetProperty("result");
        var list = new List<string>();
        foreach (var x in result.EnumerateArray())
        {
            var s = x.GetString();
            if (!string.IsNullOrEmpty(s))
                list.Add(s!);
        }
        return list;
    }

    /// <summary>
    /// Start the local stable-diffusion-webui service (local_sd.start_server)
    /// </summary>
    public async Task StartLocalServerAsync(
        string? modelPath = null,
        CancellationToken ct = default)
    {
        var root = await CallAsync(
            "local_sd.start",
            modelPath is null ? new { } : new { model_path = modelPath },
            ct
        );
        ThrowIfError(root);
        // Usually we don't care about the result, but it can be read from root.GetProperty("result") if needed
    }

    /// <summary>
    /// Shutdown the local stable-diffusion-webui service (local_sd.shutdown_server)
    /// </summary>
    public async Task ShutdownLocalServerAsync(CancellationToken ct = default)
    {
        var root = await CallAsync("local_sd.shutdown", new { }, ct);
        ThrowIfError(root);
    }

    /// <summary>
    /// Switch local model (wraps local_sd._switch_model)
    /// </summary>
    public async Task SwitchLocalModelAsync(
        string modelName,
        int timeoutSeconds = 90,
        CancellationToken ct = default)
    {
        var root = await CallAsync(
            "local_sd.switch_model",
            new { model_name = modelName, timeout = timeoutSeconds },
            ct
        );
        ThrowIfError(root);
    }

    /// <summary>
    /// Generic call: for experimenting with new methods or plugins without changing the DLL.
    /// </summary>
    public Task<JsonElement> CallRawAsync(string method, object @params, CancellationToken ct = default)
        => CallAsync(method, @params, ct);

    public void Dispose()
    {
        try
        {
            if (!_proc.HasExited)
                _proc.Kill(true);
        }
        catch
        {
            // ignore
        }
        try
        {
            _reader.Wait(1000);
        }
        catch
        {
            // ignore
        }

        try
        {
            _stderrReader.Wait(1000);
        }
        catch
        {
            // ignore
        }

        _proc.Dispose();
    }
}
