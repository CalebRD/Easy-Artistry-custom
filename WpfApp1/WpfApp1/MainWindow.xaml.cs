using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace YourApp
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            this.KeyDown += Window_KeyDown; // Attach the event handler
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
                    // Add message to chat
                    ChatPanel.Children.Add(new TextBlock
                    {
                        Text = "User: " + userMessage,
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
        }

        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            // TODO: Save the image in GeneratedImage.Source
        }
    }
}
