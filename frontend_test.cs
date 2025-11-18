// WinForms example
using System;
using System.Windows.Forms;

class Program
{
    static void Main()
    {
        Application.Run(new MainWindow());
    }
}

class MainWindow : Form
{
    public MainWindow()
    {
        Text = "My App";
        Button button = new Button() { Text = "Click Me" };
        button.Click += (sender, e) => MessageBox.Show("Clicked!");
        Controls.Add(button);
    }
}
