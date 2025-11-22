using EasyArtistry.MiddleLayer;
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;
using System.Windows;
using System.Windows.Media;

namespace WpfApp1
{
    public partial class Primary_Image_Generation : Window
    {
        private static readonly HttpClient HttpClient = new();
        private readonly string _stderrLogPath;
        private readonly object _stderrLock = new();
        private EaClient? _client;
        private string? _lastImagePayload;
        public Primary_Image_Generation()
        {
            InitializeComponent();
            var projectRoot = ResolveProjectRoot();
            var python = ResolvePythonExecutable(projectRoot);
            var workerPy = ResolveWorkerScript(projectRoot);
            var stderrLog = Path.Combine(projectRoot, "backend-stderr.log");
            try
            {
                File.WriteAllText(stderrLog, string.Empty);
            }
            catch
            {
                // ignore if file locked
            }
            _stderrLogPath = stderrLog;

            try
            {
                _client = new EaClient(python.Executable, workerPy, projectRoot, python.ExtraArgs);
                _client.OnError += (msg) =>
                {
                    AppendBackendLog(msg);
                    Debug.WriteLine($"[Python STDERR] {msg}");
                };
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to start backend: {ex.Message}");
            }
        }

        // Input box got focus
        private void ChatInput_GotFocus(object sender, RoutedEventArgs e)
        {
            if (ChatInput.Text == "Type Prompt Here...")
            {
                ChatInput.Text = "";
                ChatInput.Foreground = Brushes.Black;
            }
        }

        // Input box lost focus
        private void ChatInput_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(ChatInput.Text))
            {
                ChatInput.Text = "Type Prompt Here...";
                ChatInput.Foreground = Brushes.Gray;
            }
        }

        // Generate Button
        private async void GenerateButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(ChatInput.Text) || ChatInput.Text == "Type Prompt Here...")
            {
                MessageBox.Show("Please enter a prompt first.");
                return;
            }

            if (_client is null)
            {
                MessageBox.Show("Backend client is not available.");
                return;
            }

            string prompt = ChatInput.Text;
            GenerateButton.IsEnabled = false;
            GenerateButton.Content = "Generating...";
            AppendBackendLog($"[UI] prompt={prompt}");

            try
            {
                var images = await _client.GenerateAsync(
                    prompt: prompt,
                    size: "768x768",
                    n: 1,
                    model: "local",
                    preset: "balanced",
                    negativePrompt: "bad quality",
                    sdOverrides: new { }
                );
                if (images.Count > 0)
                {
                    var payload = images[0];
                    _lastImagePayload = payload;
                    var bitmap = await LoadBitmapFromPayloadAsync(payload);
                    GeneratedImage.Source = bitmap;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error generating image:\n" + ex.Message);
            }
            finally
            {
                AppendBackendLog("[UI] generation complete");
                GenerateButton.IsEnabled = true;
                GenerateButton.Content = "Generate";
            }
        }
        // private void GenerateButton_Click(object sender, RoutedEventArgs e)
        // {
        //     if (string.IsNullOrWhiteSpace(ChatInput.Text) || ChatInput.Text == "Type Prompt Here...")
        //     {
        //         MessageBox.Show("Please enter a prompt first.");
        //         return;
        //     }

        //     // Backend API here
        //     MessageBox.Show($"Generating image with prompt:\n{ChatInput.Text}");
        // }

        // Save Button
        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_lastImagePayload))
            {
                MessageBox.Show("No image to save yet.");
                return;
            }

            try
            {
                SaveImagePayload(_lastImagePayload);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to save image:\n" + ex.Message);
            }
        }

        private static string ResolveProjectRoot()
        {
            var env = Environment.GetEnvironmentVariable("EASY_ARTISTRY_ROOT");
            if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            {
                return Path.GetFullPath(env);
            }

            var current = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
            while (current != null)
            {
                var middleLayer = Path.Combine(current.FullName, "middle_layer");
                var backend = Path.Combine(current.FullName, "backend");
                if (Directory.Exists(middleLayer) && Directory.Exists(backend))
                {
                    return current.FullName;
                }
                current = current.Parent;
            }

            return AppDomain.CurrentDomain.BaseDirectory;
        }

        private static string ResolveWorkerScript(string projectRoot)
        {
            var env = Environment.GetEnvironmentVariable("EASY_ARTISTRY_WORKER");
            if (!string.IsNullOrWhiteSpace(env) && File.Exists(env))
            {
                return env;
            }

            var candidate = Path.Combine(projectRoot, "middle_layer", "worker.py");
            if (File.Exists(candidate))
            {
                return candidate;
            }

            throw new FileNotFoundException("Could not locate worker.py", candidate);
        }

        private readonly record struct PythonLaunchInfo(string Executable, string? ExtraArgs);

        private static PythonLaunchInfo ResolvePythonExecutable(string projectRoot)
        {
            var cfg = LoadPythonConfig(projectRoot);
            if (cfg.TryGetValue("python", out var cfgPython) && File.Exists(cfgPython))
            {
                return new PythonLaunchInfo(cfgPython, null);
            }

            var env = Environment.GetEnvironmentVariable("EASY_ARTISTRY_PYTHON");
            if (!string.IsNullOrWhiteSpace(env) && File.Exists(env))
            {
                return new PythonLaunchInfo(env, null);
            }

            if (TryCondaEnvironment(cfg, out var condaInfo))
            {
                return condaInfo;
            }

            var embedded = Path.Combine(projectRoot, "python", "python.exe");
            if (File.Exists(embedded))
            {
                return new PythonLaunchInfo(embedded, null);
            }

            if (TryFindPythonOnPath(out var located))
            {
                return new PythonLaunchInfo(located, null);
            }

            if (TryPythonLauncher(out var launcher))
            {
                return launcher;
            }

            // Fallback to generic command; system PATH must contain a suitable interpreter.
            return Environment.OSVersion.Platform == PlatformID.Win32NT
                ? new PythonLaunchInfo("python.exe", null)
                : new PythonLaunchInfo("python3", null);
        }

        private static bool TryFindPythonOnPath(out string pythonPath)
        {
            pythonPath = string.Empty;

            try
            {
                var isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
                var psi = new ProcessStartInfo
                {
                    FileName = isWindows ? "where" : "which",
                    Arguments = isWindows ? "python" : "python3",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using var proc = Process.Start(psi);
                if (proc == null)
                {
                    return false;
                }

                var firstLine = proc.StandardOutput.ReadLine();
                proc.WaitForExit(2000);

                if (!string.IsNullOrWhiteSpace(firstLine) && File.Exists(firstLine))
                {
                    pythonPath = firstLine.Trim();
                    return true;
                }
            }
            catch
            {
                // ignore and fall back to default
            }

            return false;
        }

        private static IReadOnlyDictionary<string, string> LoadPythonConfig(string projectRoot)
        {
            var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var path = Path.Combine(projectRoot, ".pythonPath");
            if (!File.Exists(path))
            {
                return map;
            }

            foreach (var rawLine in File.ReadAllLines(path))
            {
                var line = rawLine.Trim();
                if (string.IsNullOrEmpty(line) || line.StartsWith("#") || line.StartsWith("//"))
                {
                    continue;
                }

                var idx = line.IndexOf('=');
                if (idx <= 0)
                {
                    continue;
                }

                var key = line[..idx].Trim();
                var value = line[(idx + 1)..].Trim();
                if (!string.IsNullOrEmpty(key) && !string.IsNullOrEmpty(value) && !map.ContainsKey(key))
                {
                    map[key] = value;
                }
            }

            return map;
        }

        private static bool TryCondaEnvironment(IReadOnlyDictionary<string, string> cfg, out PythonLaunchInfo info)
        {
            info = default;

            if (cfg.TryGetValue("conda_prefix", out var cfgPrefix) && TryResolveCondaPrefix(cfgPrefix, out info))
            {
                return true;
            }

            if (cfg.TryGetValue("conda_env", out var cfgEnv))
            {
                var configuredCondaPath = cfg.TryGetValue("conda_path", out var cp) ? cp : null;
                if (TryLaunchCondaEnv(cfgEnv, configuredCondaPath, out info))
                {
                    return true;
                }
            }

            // Prefer explicit prefix path if provided
            var prefix = Environment.GetEnvironmentVariable("EASY_ARTISTRY_CONDA_PREFIX")
                         ?? Environment.GetEnvironmentVariable("CONDA_PREFIX");
            if (!string.IsNullOrWhiteSpace(prefix) && TryResolveCondaPrefix(prefix!, out info))
            {
                return true;
            }

            var envName = Environment.GetEnvironmentVariable("EASY_ARTISTRY_CONDA_ENV")
                         ?? Environment.GetEnvironmentVariable("CONDA_DEFAULT_ENV");
            if (string.IsNullOrWhiteSpace(envName))
            {
                return false;
            }

            if (!TryLaunchCondaEnv(envName!, cfg.TryGetValue("conda_path", out var pathOverride) ? pathOverride : null, out info))
            {
                return false;
            }

            return true;
        }

        private static bool TryResolveCondaPrefix(string prefix, out PythonLaunchInfo info)
        {
            info = default;
            try
            {
                string python;
                if (Environment.OSVersion.Platform == PlatformID.Win32NT)
                {
                    python = Path.Combine(prefix, "python.exe");
                }
                else
                {
                    python = Path.Combine(prefix, "bin", "python");
                }

                if (File.Exists(python))
                {
                    info = new PythonLaunchInfo(python, null);
                    return true;
                }
            }
            catch
            {
                // ignore
            }

            return false;
        }

        private static bool TryLaunchCondaEnv(string envName, string? configuredCondaPath, out PythonLaunchInfo info)
        {
            info = default;
            if (!TryFindCondaExecutable(configuredCondaPath, out var condaPath))
            {
                return false;
            }

            var args = $"run --no-capture-output -n \"{envName}\" python";
            info = new PythonLaunchInfo(condaPath, args);
            return true;
        }

        private static bool TryPythonLauncher(out PythonLaunchInfo info)
        {
            info = default;
            try
            {
                var isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
                if (!isWindows)
                {
                    return false;
                }

                var psi = new ProcessStartInfo
                {
                    FileName = "py.exe",
                    Arguments = "-3 --version",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using var proc = Process.Start(psi);
                if (proc == null)
                {
                    return false;
                }

                proc.WaitForExit(2000);
                if (proc.ExitCode == 0)
                {
                    info = new PythonLaunchInfo("py.exe", "-3");
                    return true;
                }
            }
            catch
            {
                // ignore
            }

            return false;
        }

        private static bool TryFindCondaExecutable(string? configuredPath, out string condaPath)
        {
            condaPath = string.Empty;
            if (!string.IsNullOrWhiteSpace(configuredPath) && File.Exists(configuredPath))
            {
                condaPath = configuredPath;
                return true;
            }

            try
            {
                var isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
                var psi = new ProcessStartInfo
                {
                    FileName = isWindows ? "where" : "which",
                    Arguments = "conda",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using var proc = Process.Start(psi);
                if (proc == null)
                {
                    return false;
                }

                var firstLine = proc.StandardOutput.ReadLine();
                proc.WaitForExit(2000);

                if (!string.IsNullOrWhiteSpace(firstLine) && File.Exists(firstLine))
                {
                    condaPath = firstLine.Trim();
                    return true;
                }
            }
            catch
            {
                // ignore
            }

            return false;
        }

        private static async Task<BitmapImage> LoadBitmapFromPayloadAsync(string payload)
        {
            if (string.IsNullOrWhiteSpace(payload))
            {
                throw new InvalidOperationException("Image payload is empty.");
            }

            payload = payload.Trim();
            if (payload.StartsWith("data:", StringComparison.OrdinalIgnoreCase))
            {
                var comma = payload.IndexOf(',');
                if (comma >= 0)
                {
                    payload = payload[(comma + 1)..];
                }
            }

            // Try base64 first
            if (TryLoadBase64(payload, out var bitmap))
            {
                return bitmap;
            }

            if (Uri.TryCreate(payload, UriKind.Absolute, out var uri))
            {
                if (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps)
                {
                    var bytes = await HttpClient.GetByteArrayAsync(uri).ConfigureAwait(false);
                    return LoadBitmapFromBytes(bytes);
                }

                if (uri.Scheme == Uri.UriSchemeFile)
                {
                    var localPath = uri.LocalPath;
                    if (File.Exists(localPath))
                    {
                        return await LoadBitmapFromFileAsync(localPath).ConfigureAwait(false);
                    }
                }
            }

            if (File.Exists(payload))
            {
                return await LoadBitmapFromFileAsync(payload).ConfigureAwait(false);
            }

            throw new InvalidOperationException("Unrecognized image payload: " + payload);
        }

        private static async Task<BitmapImage> LoadBitmapFromFileAsync(string path)
        {
            await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.StreamSource = stream;
            bitmap.EndInit();
            bitmap.Freeze();
            return bitmap;
        }

        private static bool TryLoadBase64(string payload, out BitmapImage bitmap)
        {
            bitmap = null!;
            try
            {
                var sanitized = new string(payload.Where(c => !char.IsWhiteSpace(c)).ToArray());
                var bytes = Convert.FromBase64String(sanitized);
                bitmap = LoadBitmapFromBytes(bytes);
                return true;
            }
            catch (FormatException)
            {
                return false;
            }
        }

        private static BitmapImage LoadBitmapFromBytes(byte[] bytes)
        {
            using var ms = new MemoryStream(bytes);
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            ms.Position = 0;
            bitmap.StreamSource = ms;
            bitmap.EndInit();
            bitmap.Freeze();
            return bitmap;
        }
        
        private void AppendBackendLog(string message)
        {
            if (string.IsNullOrWhiteSpace(_stderrLogPath))
            {
                return;
            }

            try
            {
                lock (_stderrLock)
                {
                    File.AppendAllText(_stderrLogPath, message + Environment.NewLine);
                }
            }
            catch
            {
                // ignore logging failures
            }
        }

        private static void SaveImagePayload(string payload)
        {
            payload = payload.Trim();
            if (payload.StartsWith("data:", StringComparison.OrdinalIgnoreCase))
            {
                var comma = payload.IndexOf(',');
                if (comma >= 0)
                {
                    payload = payload[(comma + 1)..];
                }
            }

            if (TryLoadBase64(payload, out var bmp))
            {
                var dlg = new Microsoft.Win32.SaveFileDialog
                {
                    Filter = "PNG Image (*.png)|*.png|JPEG Image (*.jpg)|*.jpg|All Files (*.*)|*.*",
                    FileName = "generated.png"
                };

                if (dlg.ShowDialog() == true)
                {
                    BitmapEncoder encoder = dlg.FilterIndex == 2 ? new JpegBitmapEncoder() : new PngBitmapEncoder();
                    encoder.Frames.Add(BitmapFrame.Create(bmp));
                    using var fs = new FileStream(dlg.FileName, FileMode.Create, FileAccess.Write);
                    encoder.Save(fs);
                }
                return;
            }

            if (Uri.TryCreate(payload, UriKind.Absolute, out var uri))
            {
                if (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps)
                {
                    System.Diagnostics.Process.Start(new ProcessStartInfo
                    {
                        FileName = uri.ToString(),
                        UseShellExecute = true
                    });
                    return;
                }

                if (uri.Scheme == Uri.UriSchemeFile)
                {
                    payload = uri.LocalPath;
                }
            }

            if (File.Exists(payload))
            {
                var dlg = new Microsoft.Win32.SaveFileDialog
                {
                    Filter = "Image Files|*.png;*.jpg;*.jpeg;*.webp;*.bmp|All Files|*.*",
                    FileName = Path.GetFileName(payload)
                };

                if (dlg.ShowDialog() == true)
                {
                    File.Copy(payload, dlg.FileName, overwrite: true);
                }
                return;
            }

            throw new InvalidOperationException("Unable to determine how to save payload.");
        }

        protected override async void OnClosed(EventArgs e)
        {
            base.OnClosed(e);

            if (_client is not null)
            {
                try
                {
                    await _client.ShutdownLocalServerAsync();
                }
                catch
                {
                    // swallow shutdown errors so closing window never throws
                }

                _client.Dispose();
                _client = null;
            }
        }
    }
}
