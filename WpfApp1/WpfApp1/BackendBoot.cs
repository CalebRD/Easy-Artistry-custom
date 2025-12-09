using EasyArtistry.MiddleLayer;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;

namespace YourApp
{
    public static class BackendBoot
    {
        private const string StderrFileName = "backend-stderr.log";

        // Holds the final Python command + optional extra arguments (e.g., "conda run ...")
        private readonly record struct PythonLaunchInfo(string Executable, string? ExtraArgs);

        /// <summary>
        /// Creates and configures an EaClient, resolving project root, Python executable,
        /// worker.py path, and wiring stderr logging.
        /// </summary>
        public static EaClient CreateClient()
        {
            var projectRoot = ResolveProjectRoot();
            var python = ResolvePythonExecutable(projectRoot);
            var workerPy = ResolveWorkerScript(projectRoot);
            var stderrLog = Path.Combine(projectRoot, StderrFileName);

            try
            {
                File.WriteAllText(stderrLog, string.Empty);
            }
            catch
            {
                // ignore if file locked
            }

            var client = new EaClient(python.Executable, workerPy, projectRoot, python.ExtraArgs);

            client.OnError += (msg) =>
            {
                try
                {
                    File.AppendAllText(stderrLog, msg + Environment.NewLine);
                }
                catch
                {
                    // ignore logging failures
                }
                Debug.WriteLine($"[Python STDERR] {msg}");
            };

            return client;
        }

        /// <summary>
        /// Tries to locate the project root folder:
        /// 1) EASY_ARTISTRY_ROOT env var, or
        /// 2) walking up from BaseDirectory until it finds middle_layer + backend, or
        /// 3) falls back to BaseDirectory.
        /// </summary>
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

        /// <summary>
        /// Locates worker.py:
        /// 1) EASY_ARTISTRY_WORKER env var, or
        /// 2) middle_layer/worker.py inside project root.
        /// Throws if not found.
        /// </summary>
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

        /// <summary>
        /// Resolves which Python to use in the following priority:
        /// config file, EASY_ARTISTRY_PYTHON, conda env/prefix, embedded python/,
        /// python on PATH, Windows py launcher, then generic "python"/"python3".
        /// </summary>
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

        /// <summary>
        /// Uses "where python" (Windows) or "which python3" (Unix) to locate Python on PATH.
        /// </summary>
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

        /// <summary>
        /// Loads simple key=value config from .pythonPath in project root into a dictionary.
        /// Lines starting with # or // are ignored.
        /// </summary>
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

        /// <summary>
        /// Tries to build a PythonLaunchInfo from conda settings:
        /// priority: config conda_prefix, config conda_env, env EASY_ARTISTRY_CONDA_PREFIX/CONDA_PREFIX,
        /// then EASY_ARTISTRY_CONDA_ENV/CONDA_DEFAULT_ENV with "conda run".
        /// </summary>
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

        /// <summary>
        /// Given a conda prefix folder, tries to resolve the python executable inside it.
        /// </summary>
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

        /// <summary>
        /// Builds a PythonLaunchInfo that uses "conda run -n envName python"
        /// by locating the conda executable and composing the arguments.
        /// </summary>
        private static bool TryLaunchCondaEnv(string envName, string? configuredCondaPath, out PythonLaunchInfo info)
        {
            info = default;
            if (!TryFindCondaExecutable(configuredPath: configuredCondaPath, out var condaPath))
            {
                return false;
            }

            var args = $"run --no-capture-output -n \"{envName}\" python";
            info = new PythonLaunchInfo(condaPath, args);
            return true;
        }

        /// <summary>
        /// On Windows, tries to use the "py.exe" launcher with "-3" (latest Python 3).
        /// </summary>
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

        /// <summary>
        /// Locates the "conda" executable:
        /// 1) optional configured path, or
        /// 2) "where conda" / "which conda" on PATH.
        /// </summary>
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
    }
}
