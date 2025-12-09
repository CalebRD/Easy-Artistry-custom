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
        // Shared HttpClient for downloading images over HTTP(S).
        private static readonly HttpClient HttpClient = new();

        /// <summary>
        /// Converts a generic image payload into a BitmapImage.
        /// Supports:
        /// 1) base64 (optionally "data:*;base64,..."),
        /// 2) HTTP/HTTPS URLs,
        /// 3) file:// URIs,
        /// 4) direct file paths.
        /// Throws if the payload type is not recognized.
        /// </summary>
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

        /// <summary>
        /// Saves an image payload to disk by:
        /// 1) If base64: pops up SaveFileDialog and encodes as PNG/JPEG.
        /// 2) If HTTP(S) URL: opens it in the default browser.
        /// 3) If file/URI path: lets user choose a target path and copies the file.
        /// Throws if it cannot determine a way to save the payload.
        /// </summary>
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

        /// <summary>
        /// Tries to interpret the payload as a base64-encoded image.
        /// Returns true on success and outputs a BitmapImage.
        /// </summary>
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

        /// <summary>
        /// Builds a BitmapImage from a raw byte[] and freezes it for WPF usage.
        /// </summary>
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
