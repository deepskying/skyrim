using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace MainMenuBrowser
{
    internal static class BrowserTests
    {
        private static int checks;
        private static void Check(bool value, string name) { checks++; if (!value) throw new Exception(name); }
        private static void Fails(Action action, string name)
        {
            bool failed = false; try { action(); } catch { failed = true; } Check(failed, name);
        }
        private static void Fixture(string directory, string name, bool review)
        {
            Directory.CreateDirectory(Path.Combine(directory, "Data"));
            File.WriteAllText(Path.Combine(directory, "Data", "fixture.txt"), "source bytes " + name, Encoding.UTF8);
            File.WriteAllText(Path.Combine(directory, "theme.json"), new JavaScriptSerializer().Serialize(new {
                name = name, enabled = !review, issues = review ? new[] { "缺少模型" } : new string[0],
                previews = new[] { new { path = "preview.jpg", dimensions = new[] { 1920, 1080 } } }
            }), Encoding.UTF8);
            if (review) File.WriteAllText(Path.Combine(directory, "disabled.txt"), "review");
            using (var bitmap = new Bitmap(320, 180))
            using (var g = Graphics.FromImage(bitmap))
            {
                g.Clear(review ? Color.SlateBlue : Color.SteelBlue);
                g.FillEllipse(Brushes.DarkSlateGray, 70, 30, 170, 170);
                bitmap.Save(Path.Combine(directory, "preview.jpg"), ImageFormat.Jpeg);
            }
        }
        public static int Run(string output)
        {
            output = Path.GetFullPath(output); Directory.CreateDirectory(output);
            var fixture = Path.Combine(output, "fixture-" + Guid.NewGuid().ToString("N"));
            var root = Path.Combine(fixture, "backgrounds"); Directory.CreateDirectory(root);
            try
            {
                Fixture(Path.Combine(root, "001_第一"), "第一套", false);
                Fixture(Path.Combine(root, "002_第二"), "第二套", false);
                Fixture(Path.Combine(root, "_待确认", "003_待确认"), "待确认图片", true);
                Fixture(Path.Combine(root, "_example"), "隐藏示例", true);
                var original = Path.Combine(fixture, "original-source.txt"); File.WriteAllText(original, "untouched");
                var library = new Library(root); var themes = library.Scan();
                Check(themes.Count == 3, "Scan excludes example");
                Check(themes.All(t => t.Previews.Count == 1 && t.Dimensions.Contains("1920")), "Preview metadata parsed");
                Check(themes.Single(t => t.State == "待确认").Notes == "缺少模型", "Issue metadata parsed");
                var first = themes.Single(t => t.Name == "第一套");
                using (var image = BrowserForm.ReadImage(first.Previews[0]))
                {
                    var removed = library.Remove(first);
                    Check(!Directory.Exists(first.Directory), "Move theme out of random pool while image loaded");
                    Check(library.Scan().Count(t => t.State == "已删除") == 1, "Trash discoverable");
                    library = new Library(root); var fromDisk = library.Scan().Single(t => t.Removed != null);
                    Check(fromDisk.Name == "第一套", "Trash survives restart with metadata");
                    Directory.CreateDirectory(first.Directory); File.WriteAllText(Path.Combine(first.Directory, "keep.txt"), "new");
                    Fails(delegate { library.Restore(fromDisk.Removed); }, "Restore does not overwrite new directory");
                    Check(File.ReadAllText(Path.Combine(first.Directory, "keep.txt")) == "new", "Collision contents preserved");
                    File.Delete(Path.Combine(first.Directory, "keep.txt")); Directory.Delete(first.Directory);
                    library.Restore(fromDisk.Removed);
                    Check(File.ReadAllText(Path.Combine(first.Directory, "Data", "fixture.txt"), Encoding.UTF8) == "source bytes 第一套", "Exact bytes restored");
                    Check(library.Scan().Count(t => t.Removed != null) == 0, "Restored entries absent from trash");
                }
                var pending = library.Scan().Single(t => t.State == "待确认");
                var pendingRecord = library.Remove(pending); library.Restore(pendingRecord);
                Check(File.Exists(Path.Combine(pending.Directory, "disabled.txt")), "Restore preserves disabled marker and review location");
                Check(File.ReadAllText(original) == "untouched", "Original source untouched");
                Fails(delegate { library.ThemePath("..\\outside"); }, "Reject path traversal");
                Fails(delegate { library.ThemePath("theme\\Data"); }, "Reject nested non-theme target");
                Fails(delegate { library.ThemePath("_example"); }, "Protect template");
                Fails(delegate { library.Remove(new Theme { Id = first.Id, Directory = fixture, Name = "wrong" }); }, "Reject stale/forged source path");
                Fails(delegate { library.Restore(new RemovedEntry { id = "..", original = first.Id }); }, "Reject forged trash record id");
                var entry = library.Remove(library.Scan().Single(t => t.Name == "第一套"));
                var entryFile = Path.Combine(library.Trash, entry.id, "entry.json");
                File.WriteAllText(entryFile, new JavaScriptSerializer().Serialize(new RemovedEntry { id = entry.id, original = "..\\outside", name = "bad" }), Encoding.UTF8);
                Check(library.Scan().All(t => t.Removed == null) && library.Warnings.Count == 1, "Corrupt record surfaced without escape");
                File.WriteAllText(entryFile, new JavaScriptSerializer().Serialize(entry), Encoding.UTF8); library.Restore(entry);
                using (var form = new BrowserForm(root))
                {
                    form.Show(); Application.DoEvents(); form.CheckUi(); Application.DoEvents();
                    form.SaveWindowPreview(Path.Combine(output, "fixture-window.png")); form.Close();
                    Check(library.Scan().Count(t => t.Removed == null) == 3, "UI delete, undo, search and filters preserve fixture after tests");
                }
                checks += LoadingTests.Run(fixture);
                File.WriteAllText(Path.Combine(output, "result.txt"), "PASS: " + checks + " checks; file operations, loading publication and UI integration.", Encoding.UTF8);
                return 0;
            }
            catch (Exception error)
            {
                File.WriteAllText(Path.Combine(output, "test-body-error.txt"), error.ToString(), Encoding.UTF8);
                throw;
            }
            finally
            {
                var absolute = Path.GetFullPath(fixture);
                if (Path.GetDirectoryName(absolute) != output || !Path.GetFileName(absolute).StartsWith("fixture-"))
                    throw new IOException("Refusing unexpected test cleanup path");
                if (Directory.Exists(absolute)) Directory.Delete(absolute, true);
            }
        }
    }
}
