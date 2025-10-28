using System;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;

namespace YourApp
{
    public partial class Primary_Image_Generation : Window
    {
        private string currentPrompt;

        public Primary_Image_Generation()
        {
            InitializeComponent();

            GenerateButton.Click += GenerateButton_Click;
            SaveButton.Click += SaveButton_Click;

            currentPrompt = string.Empty;
        }
        private void ChatInput_GotFocus(object sender, RoutedEventArgs e)
        {
            if (ChatInput.Text == "Type Prompt Here...")
            {
                ChatInput.Text = "";
                ChatInput.Foreground = Brushes.Black;
            }
        }

        private void ChatInput_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(ChatInput.Text))
            {
                ChatInput.Text = "Type Prompt Here...";
                ChatInput.Foreground = Brushes.Gray;
            }
        }

        private void GenerateButton_Click(object sender, RoutedEventArgs e)
        {
            currentPrompt = ChatInput.Text.Trim();

            if (string.IsNullOrEmpty(currentPrompt))
            {
                MessageBox.Show("Please enter a prompt first.");
                return;
            }

            MessageBox.Show($"Generating image for: {currentPrompt}");

            // 临时示例图片
            string imageUrl = "https://placekitten.com/600/400";

            try
            {
                GeneratedImage.Source = new BitmapImage(new Uri(imageUrl));
                MessageBox.Show("Image generated successfully!");
            }
            catch
            {
                MessageBox.Show("Failed to load image.");
            }
        }

        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            if (GeneratedImage.Source == null)
            {
                MessageBox.Show("No image to save.");
                return;
            }

            SaveFileDialog dlg = new SaveFileDialog
            {
                Filter = "PNG Image|*.png|JPEG Image|*.jpg",
                FileName = "GeneratedImage"
            };

            if (dlg.ShowDialog() == true)
            {
                try
                {
                    BitmapSource bitmapSource = GeneratedImage.Source as BitmapSource;
                    if (bitmapSource != null)
                    {
                        using (var stream = new System.IO.FileStream(dlg.FileName, System.IO.FileMode.Create))
                        {
                            BitmapEncoder encoder;
                            if (dlg.FilterIndex == 1)
                                encoder = new PngBitmapEncoder();
                            else
                                encoder = new JpegBitmapEncoder();

                            encoder.Frames.Add(BitmapFrame.Create(bitmapSource));
                            encoder.Save(stream);
                        }
                        MessageBox.Show("Image saved successfully!");
                    }
                }
                catch
                {
                    MessageBox.Show("Failed to save image.");
                }
            }
        }
    }
}
