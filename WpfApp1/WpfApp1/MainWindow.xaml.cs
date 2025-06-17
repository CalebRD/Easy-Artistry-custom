using System.Diagnostics;
using System.IO;
using System.Security.Cryptography.X509Certificates;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;



namespace YourApp 
{

    public partial class MainWindow : Window
    {
        private string currentPrompt;


        public MainWindow()
        {
            InitializeComponent();
            this.KeyDown += Window_KeyDown; // Attach the event handler
            currentPrompt = string.Empty;
        }

        private void Window_KeyDown(object sender, KeyEventArgs e)
        {
            // Handle global key events if needed
        }

        private void ChatInput_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                string userMessage = ChatInput.Text.Trim();
                if (!string.IsNullOrEmpty(userMessage))
                {
                    currentPrompt = userMessage; // Update current prompt
                    // Add message to chat
                    ChatPanel.Children.Add(new TextBlock
                    {
                        Text = "Current prompt changed to " + userMessage,
                        Foreground = Brushes.White,
                        Margin = new Thickness(0, 5, 0, 5),
                        TextWrapping = TextWrapping.Wrap
                    });

                    ChatInput.Clear();

                    // TODO: Send to AI agent
                }

                e.Handled = true; // Prevent beep sound on Enter
            }
        }

        private void GenerateButton_Click(object sender, RoutedEventArgs e)
        {
            // TODO: Trigger image generation
            if (string.IsNullOrEmpty(currentPrompt))
            {
                ChatPanel.Children.Add(new TextBlock
                {
                    Text = "Please Enter a Prompt First.",
                    Foreground = Brushes.White,
                    Margin = new Thickness(0, 5, 0, 5),
                    TextWrapping = TextWrapping.Wrap
                });
            }
            else
            {

                ChatPanel.Children.Add(new TextBlock
                {
                    Text = "Generating image for: " + currentPrompt,
                    Foreground = Brushes.White,
                    Margin = new Thickness(0, 5, 0, 5),
                    TextWrapping = TextWrapping.Wrap
                });

                string imageUrl = GenerateImage(currentPrompt);
                if (!string.IsNullOrEmpty(imageUrl))
                {
                    // Display the generated image
                    GeneratedImage.Source = new System.Windows.Media.Imaging.BitmapImage(new Uri(imageUrl));
                    ChatPanel.Children.Add(new TextBlock
                    {
                        Text = "Image generated successfully!",
                        Foreground = Brushes.White,
                        Margin = new Thickness(0, 5, 0, 5),
                        TextWrapping = TextWrapping.Wrap
                    });
                }
                else
                {
                    ChatPanel.Children.Add(new TextBlock
                    {
                        Text = "Failed to generate image.",
                        Foreground = Brushes.Red,
                        Margin = new Thickness(0, 5, 0, 5),
                        TextWrapping = TextWrapping.Wrap
                    });
                }
            }
        }

        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            // TODO: Save the image in GeneratedImage.Source
        }

        private string GenerateImage(string userInput)
        {

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;

            // Go up 4 levels from bin\Debug\net8.0-windows\ to C:\ (where main.py lives)
            string scriptPath = Path.Combine(baseDir, @"..\..\..\..\..\main.py");
            scriptPath = Path.GetFullPath(scriptPath); // Normalize the path

            var psi = new ProcessStartInfo
            {
                FileName = "python", // Run Python
                Arguments = $"\"main.py\" \"{userInput}\"",
                RedirectStandardOutput = true, // Capture output (i.e., the image URL)
                UseShellExecute = false, // Needed to redirect output
                CreateNoWindow = true, // Hide the Python terminal window
                WorkingDirectory = Path.GetDirectoryName(scriptPath) // Your Python file folder
            };

            using (var process = Process.Start(psi)) // Start the process
            {
                if (process == null)
                {
                    MessageBox.Show("Failed to start Python process.");
                    return string.Empty;
                }
                string result = process.StandardOutput.ReadToEnd(); // Read printed URL
                process.WaitForExit(); // Wait for Python to finish
                return result.Trim(); // Clean up result
            }
        }

    }
}
