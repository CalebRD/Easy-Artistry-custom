using EasyArtistry.MiddleLayer;
using System;
using System.Windows;
using System.Windows.Media;

namespace YourApp
{
    /// <summary>
    /// Main window for primary image generation: handles UI events and talks to the backend client.
    /// </summary>
    public partial class Primary_Image_Generation : Window
    {
        // Client used to communicate with the Python backend.
        private EaClient? _client;

        // Stores the most recent image payload returned from the backend.
        private string? _lastImagePayload;

        /// <summary>
        /// Initializes the window and tries to create the backend client.
        /// </summary>
        public Primary_Image_Generation()
        {
            InitializeComponent();

            try
            {
                _client = BackendBoot.CreateClient();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to start backend: {ex.Message}");
            }
        }

        /// <summary>
        /// Clears the placeholder text when the prompt textbox gains focus.
        /// </summary>
        private void ChatInput_GotFocus(object sender, RoutedEventArgs e)
        {
            if (ChatInput.Text == "Type Prompt Here...")
            {
                ChatInput.Text = "";
                ChatInput.Foreground = Brushes.Black;
            }
        }

        /// <summary>
        /// Restores the placeholder text if the prompt textbox loses focus and is empty.
        /// </summary>
        private void ChatInput_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(ChatInput.Text))
            {
                ChatInput.Text = "Type Prompt Here...";
                ChatInput.Foreground = Brushes.Gray;
            }
        }

        /// <summary>
        /// Handles the Generate button click:
        /// validates prompt, sends request to backend, and displays the resulting image.
        /// </summary>
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
                    _lastImagePayload = images[0];
                    var bitmap = await ImagePayloadService.LoadBitmapFromPayloadAsync(_lastImagePayload);
                    GeneratedImage.Source = bitmap;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error generating image:\n" + ex.Message);
            }
            finally
            {
                GenerateButton.IsEnabled = true;
                GenerateButton.Content = "Generate";
            }
        }

        /// <summary>
        /// Handles the Save button click:
        /// saves the last generated image payload using ImagePayloadService.
        /// </summary>
        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_lastImagePayload))
            {
                MessageBox.Show("No image to save yet.");
                return;
            }

            try
            {
                ImagePayloadService.SaveImagePayload(_lastImagePayload);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to save image:\n" + ex.Message);
            }
        }

        /// <summary>
        /// Ensures the backend client is shut down and disposed when the window is closed.
        /// </summary>
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
