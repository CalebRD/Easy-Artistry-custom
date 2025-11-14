using System.Diagnostics;
using System.IO;
using System.Security.Cryptography.X509Certificates;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace EA_Utils
{
    public static class EA_utils
    {
        public static void DisplayChatMessage(Panel chatPanel, string message, Brush foreground)
        {
            chatPanel.Children.Add(new TextBlock
            {
                Text = message,
                Foreground = foreground,
                Margin = new Thickness(0, 5, 0, 5),
                TextWrapping = TextWrapping.Wrap
            });
        }

        public static string RunPythonScript(string path, List<string> args)
        {
            // format the arguments
            string tempArgs = $"\"main.py\"";
            for (int i = 0; i < args.Count(); i++)
            {
                tempArgs += $" \"{args[i]}\"";
            }


            var psi = new ProcessStartInfo
            {
                FileName = "python", // Run Python
                Arguments = tempArgs,
                RedirectStandardOutput = true, // Capture output (i.e., the image URL)
                RedirectStandardError = true,
                UseShellExecute = false, // Needed to redirect output
                CreateNoWindow = true, // Hide the Python terminal window
                WorkingDirectory = Path.GetDirectoryName(path) // Your Python file folder
            };

            using (var process = Process.Start(psi)) // Start the process
            {
                if (process == null)
                {
                    MessageBox.Show("Failed to start Python process.");
                    return string.Empty;
                }
                string errors = process.StandardError.ReadToEnd();
                string result = process.StandardOutput.ReadToEnd(); // Read printed URL
                process.WaitForExit(); // Wait for Python to finish

                if (errors != "")
                {
                    MessageBox.Show(errors);
                }

                return result.Trim(); // Clean up result
            }
        }
    }
}
