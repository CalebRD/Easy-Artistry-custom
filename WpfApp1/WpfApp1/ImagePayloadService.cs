using System;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;
using Microsoft.Win32;

namespace YourApp
{
    public static class ImagePayloadService
    {
        private static readonly HttpClient HttpClient = new();

        public static async Task<BitmapImage> LoadBitmapFromPayloadAsync(string payload)
        {
            if (string.IsNullOrWhiteSpace(payload))
            {
                throw new InvalidOperationException("Image payload is empty.");
            }

            payload = payload.Trim();
            if (payload.StartsWith("data:", StringComparison.OrdinalIgnoreCase))
            {
                var comma = payload.IndexOf(',');
                if (comma >= 0)
                {
                    payload = payload[(comma + 1)..];
                }
            }

            // Try base64 first
            if (TryLoadBase64(payload, out var bitmap))
            {
                return bitmap;
            }

            if (Uri.TryCreate(payload, UriKind.Absolute, out var uri))
            {
                if (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps)
                {
                    var bytes = await HttpClient.GetByteArrayAsync(uri).ConfigureAwait(false);
                    return LoadBitmapFromBytes(bytes);
                }

                if (uri.Scheme == Uri.UriSchemeFile)
                {
                    var localPath = uri.LocalPath;
                    var bytes = await File.ReadAllBytesAsync(localPath).ConfigureAwait(false);
                    return LoadBitmapFromBytes(bytes);
                }
            }

            if (File.Exists(payload))
            {
                var bytes = await File.ReadAllBytesAsync(payload).ConfigureAwait(false);
                return LoadBitmapFromBytes(bytes);
            }

            throw new InvalidOperationException("Unrecognized image payload: " + payload);
        }

        public static void SaveImagePayload(string payload)
        {
            payload = payload.Trim();
            if (payload.StartsWith("data:", StringComparison.OrdinalIgnoreCase))
            {
                var comma = payload.IndexOf(',');
                if (comma >= 0)
                {
                    payload = payload[(comma + 1)..];
                }
            }

            if (TryLoadBase64(payload, out var bmp))
            {
                var dlg = new SaveFileDialog
                {
                    Filter = "PNG Image (*.png)|*.png|JPEG Image (*.jpg)|*.jpg|All Files (*.*)|*.*",
                    FileName = "generated.png"
                };

                if (dlg.ShowDialog() == true)
                {
                    BitmapEncoder encoder = dlg.FilterIndex == 2 ? new JpegBitmapEncoder() : new PngBitmapEncoder();
                    encoder.Frames.Add(BitmapFrame.Create(bmp));
                    using var fs = new FileStream(dlg.FileName, FileMode.Create, FileAccess.Write);
                    encoder.Save(fs);
                }
                return;
            }

            if (Uri.TryCreate(payload, UriKind.Absolute, out var uri))
            {
                if (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps)
                {
                    System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                    {
                        FileName = uri.ToString(),
                        UseShellExecute = true
                    });
                    return;
                }

                if (uri.Scheme == Uri.UriSchemeFile)
                {
                    payload = uri.LocalPath;
                }
            }

            if (File.Exists(payload))
            {
                var dlg = new SaveFileDialog
                {
                    Filter = "Image Files|*.png;*.jpg;*.jpeg;*.webp;*.bmp|All Files|*.*",
                    FileName = Path.GetFileName(payload)
                };

                if (dlg.ShowDialog() == true)
                {
                    File.Copy(payload, dlg.FileName, overwrite: true);
                }
                return;
            }

            throw new InvalidOperationException("Unable to determine how to save payload.");
        }

        private static bool TryLoadBase64(string payload, out BitmapImage bitmap)
        {
            bitmap = null!;
            try
            {
                var sanitized = new string(payload.Where(c => !char.IsWhiteSpace(c)).ToArray());
                var bytes = Convert.FromBase64String(sanitized);
                bitmap = LoadBitmapFromBytes(bytes);
                return true;
            }
            catch (FormatException)
            {
                return false;
            }
        }

        private static BitmapImage LoadBitmapFromBytes(byte[] bytes)
        {
            using var ms = new MemoryStream(bytes);
            var bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            ms.Position = 0;
            bitmap.StreamSource = ms;
            bitmap.EndInit();
            bitmap.Freeze();
            return bitmap;
        }
    }
}
