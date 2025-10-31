using System.Windows;
using System.Windows.Media;

namespace YourApp
{
    public partial class Primary_Image_Generation : Window
    {
        public Primary_Image_Generation()
        {
            InitializeComponent();
            // this.SizeChanged += (s, e) =>
            // {
            //     if (e.WidthChanged)
            //     {
            //         this.Height = this.Width * 700.0 / 1000.0;
            //     }
            // };
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
        private void GenerateButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(ChatInput.Text) || ChatInput.Text == "Type Prompt Here...")
            {
                MessageBox.Show("Please enter a prompt first.");
                return;
            }

            // Backend API here
            MessageBox.Show($"Generating image with prompt:\n{ChatInput.Text}");
        }

        // Save Button
        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            // Save image method here
            MessageBox.Show("Save image clicked.");
        }
    }
}
