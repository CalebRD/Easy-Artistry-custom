using EasyArtistry.MiddleLayer;
using System.IO;
using System.Windows.Media.Imaging;
using System.Windows;
using System.Windows.Media;

namespace YourApp
{
    public partial class Primary_Image_Generation : Window
    {
        private EaClient _client;
        public Primary_Image_Generation()
        {
            InitializeComponent();
            string pythonExe = @"C:\Users\Zheng Zhu\.conda\envs\easyart\python.exe";
            var workerPy = @"C:\D\programming\RPI_CSCI\EasyArtistry\Easy-Artistry-custom\middle_layer\worker.py";
            MessageBox.Show(workerPy, "Debug: workerPy");
            try
            {
                _client = new EaClient(pythonExe, workerPy);
                _client.OnError += (msg) =>
                {
                    Console.Error.WriteLine($"[Python STDERR] {msg}");
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

            string prompt = ChatInput.Text;
            GenerateButton.IsEnabled = false;
            GenerateButton.Content = "Generating...";

            try
            {
                var images = await _client.GenerateAsync(prompt, size: "512x512", n: 1);
                if (images.Count > 0)
                {
                    string base64 = images[0];
                    BitmapImage bitmap = new BitmapImage();
                    bitmap.BeginInit();
                    bitmap.StreamSource = new MemoryStream(Convert.FromBase64String(base64));
                    bitmap.CacheOption = BitmapCacheOption.OnLoad;
                    bitmap.EndInit();
                    bitmap.Freeze();

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
            // Save image method here
            MessageBox.Show("Save image clicked.");
        }
    }
}
