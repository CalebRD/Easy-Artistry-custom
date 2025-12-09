using EasyArtistry.MiddleLayer;
using System;
using System.Windows;
using System.Windows.Media;

namespace YourApp
{
    public partial class Primary_Image_Generation : Window
    {
        private EaClient? _client;
        private string? _lastImagePayload;

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
                ImagePayloadService.SaveImagePayload(_lastImagePayload);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to save image:\n" + ex.Message);
            }
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
