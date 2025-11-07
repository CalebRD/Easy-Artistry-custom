using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using EasyArtistry.MiddleLayer;

namespace EasyArtistry.Frontend;

internal static class Program
{
    /// <summary>
    /// 中文说明：此测试入口支持两种模式方便排查：
    /// 1. 默认走“api”模式，直接调用云端 Stable Diffusion；
    /// 2. 输入“local”即可测试本地 Stable Diffusion WebUI，流程为启动→切换模型→生成→关闭；
    /// 3. 两种模式都会读取命令行输入的正向提示词，未输入则采用示例。
    /// 这样既能在本地环境未就绪时验证云端链路，也能在日后回归本地测试。
    /// </summary>
    private static async Task Main()
    {
        var projectRoot = ResolveProjectRoot();
        var pythonExe = ResolvePythonExecutable();
        var workerPath = Path.Combine(projectRoot, "middle_layer", "worker.py");

        if (!File.Exists(workerPath))
        {
            Console.WriteLine($"无法在路径 {workerPath} 找到 worker.py，请确认目录结构是否正确。");
            return;
        }

        Console.WriteLine($"使用 Python: {pythonExe}");
        Console.WriteLine($"使用 Worker: {workerPath}");

        using var client = new EaClient(pythonExe, workerPath, projectRoot);

        const string apiDefaultPrompt = "highly detailed illustration of a silver-haired girl in a classroom, soft sunlight, anime style, best quality";
        const string localDefaultPrompt = "1girl, solo, silver hair, blue eyes, school uniform, beige blazer, white shirt, red ribbon bow, black pleated skirt, thighhighs, sitting on classroom chair, gentle blush, soft sunlight, masterpiece";
        const string apiNegativePrompt = "low quality, blurry, bad anatomy, watermark, signature";
        const string localNegativePrompt = "(worst quality, low quality, lowres, bad anatomy, bad hands, extra limbs, missing fingers, signature, watermark)";

        Console.Write("选择测试模式 (api/local，回车默认 api)：");
        var modeInput = Console.ReadLine();
        var useLocal = string.Equals(modeInput?.Trim(), "local", StringComparison.OrdinalIgnoreCase);

        var defaultPrompt = useLocal ? localDefaultPrompt : apiDefaultPrompt;
        Console.Write("请输入正向提示词 (留空使用默认示例)：");
        var promptInput = Console.ReadLine();
        var positivePrompt = string.IsNullOrWhiteSpace(promptInput) ? defaultPrompt : promptInput;
        var negativePrompt = useLocal ? localNegativePrompt : apiNegativePrompt;

    var startedLocal = false;

        try
        {
            if (useLocal)
            {
                Console.WriteLine("========== 1. 启动本地 Stable Diffusion WebUI ==========");
                await client.StartLocalServerAsync();
                startedLocal = true;
                Console.WriteLine("服务启动成功或已在运行。");

                const string modelName = "sd_xl_base_1.0.safetensors";
                Console.WriteLine("\n========== 2. 切换模型 ==========");
                Console.WriteLine($"准备切换至模型: {modelName}");
                await client.SwitchLocalModelAsync(modelName);
                Console.WriteLine("模型切换完成。");

                Console.WriteLine("\n========== 3. 生成图片 (本地) ==========");
                var sdOverrides = new
                {
                    steps = 26,
                    sampler_name = "DPM++ 3M SDE",
                    cfg_scale = 6.8,
                    enable_hr = true,
                    hr_scale = 1.6,
                    hr_upscaler = "R-ESRGAN 4x+ Anime6B",
                    denoising_strength = 0.30,
                    hr_second_pass_steps = 14
                };

                var images = await client.GenerateAsync(
                    prompt: positivePrompt,
                    size: "640x896",
                    n: 1,
                    model: "local",
                    preset: "high",
                    negativePrompt: negativePrompt,
                    sdOverrides: sdOverrides
                );

                ReportImages(images, useLocal);
            }
            else
            {
                Console.WriteLine("========== 1. 调用云端 Stable Diffusion API ==========");

                var images = await client.GenerateAsync(
                    prompt: positivePrompt,
                    size: "1024x1024",
                    n: 1,
                    model: "stable-diffusion",
                    preset: "balanced",
                    negativePrompt: negativePrompt,
                    sdOverrides: null
                );

                ReportImages(images, useLocal);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("测试过程中出现异常：");
            Console.WriteLine(ex);
        }
        finally
        {
            if (startedLocal)
            {
                Console.WriteLine("\n========== 4. 关闭本地 SD 服务 ==========");
                try
                {
                    await client.ShutdownLocalServerAsync();
                    Console.WriteLine("服务已关闭。");
                }
                catch (Exception shutdownEx)
                {
                    Console.WriteLine("关闭服务时出现异常：");
                    Console.WriteLine(shutdownEx);
                }
            }

            Console.WriteLine("\n测试结束。");
        }
    }

    private static void ReportImages(IReadOnlyList<string> images, bool isLocal)
    {
        if (images.Count > 0)
        {
            Console.WriteLine(isLocal
                ? "生成成功，返回的图片路径如下："
                : "生成成功，返回的图片地址如下：");
            foreach (var path in images)
            {
                Console.WriteLine(path);
                OpenImageIfPossible(path);
            }
        }
        else
        {
            Console.WriteLine("生成失败，未收到任何输出。");
        }
    }

    private static string ResolveProjectRoot()
    {
        // 优先使用环境变量，便于自定义；否则向上回溯直至找到 backend/middle_layer 目录
        var env = Environment.GetEnvironmentVariable("EASY_ARTISTRY_ROOT");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
        {
            return Path.GetFullPath(env);
        }

        var current = Path.GetFullPath(AppContext.BaseDirectory);
        while (!string.IsNullOrEmpty(current))
        {
            var backendPath = Path.Combine(current, "backend");
            var middleLayerPath = Path.Combine(current, "middle_layer");
            if (Directory.Exists(backendPath) && Directory.Exists(middleLayerPath))
            {
                return current;
            }

            var parent = Directory.GetParent(current);
            if (parent is null)
            {
                break;
            }
            current = parent.FullName;
        }

        return Directory.GetCurrentDirectory();
    }

    private static string ResolvePythonExecutable()
    {
        // 如果设置了环境变量则直接使用
        var env = Environment.GetEnvironmentVariable("EASY_ARTISTRY_PYTHON");
        if (!string.IsNullOrWhiteSpace(env))
        {
            return env;
        }

        // Windows 按常见顺序猜测 python 可执行文件
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            return "python.exe";
        }

        // Unix-like 环境默认 python3
        return "python3";
    }

    private static void OpenImageIfPossible(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return;
        }

        if (Uri.TryCreate(path, UriKind.Absolute, out var uri) &&
            (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps))
        {
            try
            {
                var psi = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = uri.ToString(),
                    UseShellExecute = true
                };
                System.Diagnostics.Process.Start(psi);
            }
            catch (Exception openEx)
            {
                Console.WriteLine($"尝试打开图片链接失败：{openEx.Message}");
            }
            return;
        }

        if (!File.Exists(path))
        {
            return;
        }

        try
        {
            var fullPath = Path.GetFullPath(path);
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                var psi = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = fullPath,
                    UseShellExecute = true
                };
                System.Diagnostics.Process.Start(psi);
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            {
                System.Diagnostics.Process.Start("open", fullPath);
            }
            else
            {
                System.Diagnostics.Process.Start("xdg-open", fullPath);
            }
        }
        catch (Exception openEx)
        {
            Console.WriteLine($"尝试打开图片失败：{openEx.Message}");
        }
    }
}
