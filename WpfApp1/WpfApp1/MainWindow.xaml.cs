using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography.X509Certificates;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using EA_Utils;



namespace WpfApp1
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
                    EA_utils.DisplayChatMessage(ChatPanel, "Changing prompt to: " + userMessage, Brushes.White);

                    ChatInput.Clear();

                }

                e.Handled = true; // Prevent beep sound on Enter
            }
        }

        private void GenerateButton_Click(object sender, RoutedEventArgs e)
        {
            // TODO: Trigger image generation
            if (string.IsNullOrEmpty(currentPrompt))
            {
                EA_utils.DisplayChatMessage(ChatPanel, "Please enter a prompt first", Brushes.White); ;
            }
            else
            {

                EA_utils.DisplayChatMessage(ChatPanel, "Generating image for: " + currentPrompt, Brushes.White); ;

                string imageUrl = GenerateImage(currentPrompt);
                if (!string.IsNullOrEmpty(imageUrl))
                {
                    // Display the generated image
                    GeneratedImage.Source = new System.Windows.Media.Imaging.BitmapImage(new Uri(imageUrl));
                    EA_utils.DisplayChatMessage(ChatPanel, "Image generated successfully!", Brushes.White);
                }
                else
                {
                    EA_utils.DisplayChatMessage(ChatPanel, "failed to generate image.", Brushes.White);
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


            // Run the script
            var args = new List<string> { userInput };
            return EA_utils.RunPythonScript(scriptPath, args);
            
        }

    }
}
