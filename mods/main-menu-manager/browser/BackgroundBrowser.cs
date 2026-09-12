using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace MainMenuBrowser
{
    public sealed class FlatButton : Button
    {
        protected override void OnPaint(PaintEventArgs e)
        {
            using (var brush = new SolidBrush(BackColor)) e.Graphics.FillRectangle(brush, ClientRectangle);
            TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle,
                Enabled ? ForeColor : Color.FromArgb(126, 146, 168),
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine | TextFormatFlags.NoPadding);
            if (Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(e.Graphics, Rectangle.Inflate(ClientRectangle, -4, -4));
        }
    }
    public sealed class RemovedEntry
    {
        public string id { get; set; }
        public string original { get; set; }
        public string name { get; set; }
        public string deletedUtc { get; set; }
    }

    public sealed class Theme
    {
        public string Id, Directory, Name, State, Notes, Dimensions;
        public long Bytes;
        public List<string> Previews = new List<string>();
        public RemovedEntry Removed;
    }

    public sealed class Library
    {
        public readonly string Root, Trash;
        public readonly bool IsLoading;
        public List<string> Warnings = new List<string>();
        private readonly JavaScriptSerializer json = new JavaScriptSerializer { MaxJsonLength = 8 * 1024 * 1024 };

        public Library(string root)
        {
            Root = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar);
            IsLoading = String.Equals(Path.GetFileName(Root), "loading-backgrounds", StringComparison.OrdinalIgnoreCase);
            Trash = Path.Combine(Path.GetDirectoryName(Root), IsLoading ? "deleted-loading-backgrounds" : "deleted-backgrounds");
            NoLinks(Root); NoLinks(Trash);
            if (!System.IO.Directory.Exists(Root)) throw new DirectoryNotFoundException("找不到背景库：" + Root);
        }

        public static void NoLinks(string path)
        {
            for (var current = Path.GetFullPath(path); !String.IsNullOrEmpty(current); current = Path.GetDirectoryName(current))
            {
                if ((System.IO.Directory.Exists(current) || File.Exists(current)) &&
                    (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("不操作目录链接：" + current);
            }
        }

        public static bool IsInside(string root, string path)
        {
            return Path.GetFullPath(path).StartsWith(Path.GetFullPath(root).TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase);
        }

        private static string ValidRelative(string value)
        {
            if (String.IsNullOrWhiteSpace(value) || Path.IsPathRooted(value)) throw new IOException("背景路径无效。");
            var parts = value.Replace('/', '\\').Split('\\');
            if (parts.Any(p => String.IsNullOrEmpty(p) || p == "." || p == ".." || p.EndsWith(".") || p.EndsWith(" ") || p.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0))
                throw new IOException("背景路径包含无效字符。");
            if (parts.Length != 1 && !(parts.Length == 2 && parts[0] == "_待确认"))
                throw new IOException("只操作背景库中的独立主题目录。");
            if (parts[parts.Length - 1].StartsWith("_") || parts[parts.Length - 1].StartsWith("."))
                throw new IOException("不操作系统或示例目录。");
            return String.Join("\\", parts);
        }

        public string ThemePath(string relative)
        {
            var path = Path.GetFullPath(Path.Combine(Root, ValidRelative(relative)));
            if (!IsInside(Root, path)) throw new IOException("背景目录超出资源库。");
            NoLinks(path);
            return path;
        }

        private string EntryPath(string id)
        {
            Guid parsed;
            if (!Guid.TryParseExact(id, "N", out parsed)) throw new IOException("删除记录编号无效。");
            var path = Path.Combine(Trash, id);
            if (!IsInside(Trash, path)) throw new IOException("删除记录路径无效。");
            NoLinks(path);
            return path;
        }

        private static void TreeHasNoLinks(string root)
        {
            NoLinks(root);
            foreach (var file in System.IO.Directory.EnumerateFileSystemEntries(root))
            {
                var attributes = File.GetAttributes(file);
                if ((attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("主题包含目录或文件链接，已跳过：" + file);
                if ((attributes & FileAttributes.Directory) != 0) TreeHasNoLinks(file);
            }
        }

        private Dictionary<string, object> Metadata(string path)
        {
            NoLinks(path);
            if (!File.Exists(path)) return new Dictionary<string, object>();
            if (new FileInfo(path).Length > 8 * 1024 * 1024) throw new IOException("元数据文件过大。");
            return json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path, Encoding.UTF8)) ?? new Dictionary<string, object>();
        }
        private static string Text(Dictionary<string, object> data, string field, string fallback)
        {
            object value;
            return data.TryGetValue(field, out value) && value != null ? Convert.ToString(value, CultureInfo.InvariantCulture) : fallback;
        }
        private static object[] Values(object value)
        {
            var sequence = value as System.Collections.IEnumerable;
            return sequence == null || value is string ? null : sequence.Cast<object>().ToArray();
        }

        private Theme ReadTheme(string path, string id, RemovedEntry removed)
        {
            NoLinks(path);
            var data = Metadata(Path.Combine(path, "theme.json"));
            var theme = new Theme { Id = id, Directory = path, Name = Text(data, "name", removed == null ? Path.GetFileName(path) : removed.name), Removed = removed };
            object value;
            bool enabled = !data.TryGetValue("enabled", out value) || !(value is bool) || (bool)value;
            var issues = data.TryGetValue("issues", out value) ? Values(value) : null;
            theme.Notes = issues == null ? "" : String.Join("；", issues.Select(v => Convert.ToString(v)).ToArray());
            theme.State = removed != null ? "已删除" : (id.StartsWith("_待确认\\", StringComparison.Ordinal) || !String.IsNullOrEmpty(theme.Notes)) ? "待确认" :
                (!enabled || File.Exists(Path.Combine(path, "disabled.txt"))) ? "已停用" : "可用";
            var previewItems = data.TryGetValue("previews", out value) ? Values(value) : null;
            if (previewItems != null)
            {
                foreach (var item in previewItems)
                {
                    var preview = item as Dictionary<string, object>;
                    if (preview == null) continue;
                    var relative = Text(preview, "path", "");
                    if (Path.GetFileName(relative) != relative || String.IsNullOrEmpty(relative)) continue;
                    var previewPath = Path.Combine(path, relative);
                    NoLinks(previewPath);
                    if (File.Exists(previewPath)) theme.Previews.Add(previewPath);
                    var dimensions = preview.TryGetValue("dimensions", out value) ? Values(value) : null;
                    if (dimensions != null && dimensions.Length == 2 && String.IsNullOrEmpty(theme.Dimensions))
                        theme.Dimensions = "原始纹理 " + dimensions[0] + " × " + dimensions[1];
                }
            }
            if (theme.Previews.Count == 0)
            {
                foreach (var name in new[] { "preview.jpg", "preview.png", "preview.jpeg" })
                {
                    var file = Path.Combine(path, name); NoLinks(file);
                    if (File.Exists(file)) { theme.Previews.Add(file); break; }
                }
            }
            var manifest = Metadata(Path.Combine(path, "source-manifest.json"));
            long bytes;
            if (Int64.TryParse(Text(manifest, "bytes", "0"), out bytes)) theme.Bytes = bytes;
            return theme;
        }

        public List<Theme> Scan()
        {
            Warnings.Clear();
            var result = new List<Theme>();
            NoLinks(Root); NoLinks(Trash);
            var paths = System.IO.Directory.GetDirectories(Root).Where(p => !Path.GetFileName(p).StartsWith("_") && !Path.GetFileName(p).StartsWith(".")).ToList();
            var review = Path.Combine(Root, "_待确认"); NoLinks(review);
            if (System.IO.Directory.Exists(review)) paths.AddRange(System.IO.Directory.GetDirectories(review));
            foreach (var path in paths)
            {
                if (!File.Exists(Path.Combine(path, "theme.json")) && !System.IO.Directory.Exists(Path.Combine(path, "Data"))) continue;
                try
                {
                    string id = path.Substring(Root.Length + 1);
                    ThemePath(id);
                    result.Add(ReadTheme(path, id, null));
                }
                catch (Exception error) { Warnings.Add(Path.GetFileName(path) + "：" + error.Message); }
            }
            if (System.IO.Directory.Exists(Trash))
            {
                foreach (var directory in System.IO.Directory.GetDirectories(Trash))
                {
                    try
                    {
                        var entryRoot = EntryPath(Path.GetFileName(directory));
                        var file = Path.Combine(entryRoot, "entry.json"); NoLinks(file);
                        var content = Path.Combine(entryRoot, "theme"); NoLinks(content);
                        if (!System.IO.Directory.Exists(content)) continue; // Restored or interrupted before move.
                        var entry = json.Deserialize<RemovedEntry>(File.ReadAllText(file, Encoding.UTF8));
                        if (entry == null || entry.id != Path.GetFileName(directory)) throw new IOException("删除记录损坏。");
                        ThemePath(entry.original);
                        var theme = ReadTheme(content, entry.original, entry);
                        if (String.IsNullOrEmpty(theme.Name)) theme.Name = entry.name;
                        result.Add(theme);
                    }
                    catch (Exception error) { Warnings.Add("已删除：" + Path.GetFileName(directory) + "：" + error.Message); }
                }
            }
            return result.OrderBy(t => t.Id, StringComparer.OrdinalIgnoreCase).ToList();
        }

        private static void RequireGameClosed()
        {
            if (Process.GetProcessesByName("SkyrimSE").Length != 0)
                throw new IOException("请先退出 Skyrim，再删除或恢复背景。预览仍可正常使用。");
        }

        public RemovedEntry Remove(Theme theme)
        {
            RequireGameClosed();
            if (theme.Removed != null) throw new IOException("这套背景已经在“已删除”中。");
            var source = ThemePath(theme.Id);
            if (!String.Equals(Path.GetFullPath(theme.Directory), source, StringComparison.OrdinalIgnoreCase)) throw new IOException("背景位置发生变化，请刷新。");
            if (!System.IO.Directory.Exists(source)) throw new IOException("背景已被移走，请刷新。");
            if (!File.Exists(Path.Combine(source, "theme.json")) && !System.IO.Directory.Exists(Path.Combine(source, "Data")))
                throw new IOException("目录不再是有效的背景主题。");
            TreeHasNoLinks(source);
            var record = new RemovedEntry { id = Guid.NewGuid().ToString("N"), original = ValidRelative(theme.Id), name = theme.Name, deletedUtc = DateTime.UtcNow.ToString("o") };
            var entry = EntryPath(record.id);
            System.IO.Directory.CreateDirectory(entry);
            var destination = Path.Combine(entry, "theme");
            // Write recovery information before the atomic same-volume move.
            File.WriteAllText(Path.Combine(entry, "entry.json"), json.Serialize(record), new UTF8Encoding(false));
            if (!IsInside(Root, source) || !IsInside(Trash, destination)) throw new IOException("移动路径校验失败。");
            System.IO.Directory.Move(source, destination);
            try { if (IsLoading) LoadingLibrary.Publish(this); }
            catch { System.IO.Directory.Move(destination, source); throw; }
            return record;
        }

        public void Restore(RemovedEntry record)
        {
            RequireGameClosed();
            var entry = EntryPath(record.id);
            var saved = json.Deserialize<RemovedEntry>(File.ReadAllText(Path.Combine(entry, "entry.json"), Encoding.UTF8));
            if (saved == null || saved.id != record.id || saved.original != record.original) throw new IOException("删除记录不一致，请刷新。");
            var source = Path.Combine(entry, "theme");
            var destination = ThemePath(saved.original);
            if (!IsInside(Trash, source) || !IsInside(Root, destination)) throw new IOException("恢复路径校验失败。");
            if (System.IO.Directory.Exists(destination) || File.Exists(destination)) throw new IOException("原位置已有同名目录，未覆盖：" + saved.original);
            TreeHasNoLinks(source);
            System.IO.Directory.CreateDirectory(Path.GetDirectoryName(destination));
            System.IO.Directory.Move(source, destination);
            try { if (IsLoading) LoadingLibrary.Publish(this); }
            catch { System.IO.Directory.Move(destination, source); throw; }
            // Leave the tiny entry record as history. Scan ignores restored entries.
        }
    }

    public sealed class BrowserForm : Form
    {
        private Library library;
        private readonly string managerRoot;
        private readonly Label libraryTitle = new Label();
        private Button mainLibraryButton, loadingLibraryButton;
        private readonly TextBox search = new TextBox();
        private readonly Button category = new FlatButton();
        private string filterName = "全部背景";
        private readonly ListView grid = new ListView();
        private readonly ImageList icons = new ImageList();
        private readonly List<Image> thumbnails = new List<Image>();
        private readonly PictureBox picture = new PictureBox();
        private readonly Label title = new Label(), detail = new Label(), status = new Label(), counts = new Label(), empty = new Label();
        private readonly Button remove = new FlatButton(), restore = new FlatButton(), undo = new FlatButton(), open = new FlatButton(), zoom = new FlatButton();
        private List<Theme> themes = new List<Theme>();
        private List<RemovedEntry> lastRemoved = new List<RemovedEntry>();
        private Theme current;
        private int frame;
        private bool updating;
        private Color background = Color.FromArgb(18, 24, 33), panel = Color.FromArgb(27, 37, 50), ink = Color.FromArgb(234, 240, 247);

        public BrowserForm(string root)
        {
            library = new Library(root);
            managerRoot = Path.GetDirectoryName(library.Root);
            Text = "开屏背景管理器";
            AutoScaleMode = AutoScaleMode.Dpi;
            Font = new Font("Microsoft YaHei UI", 10f);
            BackColor = background; ForeColor = ink;
            var area = Screen.PrimaryScreen.WorkingArea;
            ClientSize = new Size(Math.Min(1380, area.Width - 80), Math.Min(880, area.Height - 100));
            MinimumSize = new Size(1020, 660);
            StartPosition = FormStartPosition.CenterScreen;
            KeyPreview = true;

            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(20), RowCount = 4, ColumnCount = 1, BackColor = background };
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 68));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 35));
            Controls.Add(layout);
            var heading = new Panel { Dock = DockStyle.Fill };
            libraryTitle.Text = library.IsLoading ? "加载背景" : "主菜单背景";
            libraryTitle.Font = new Font(Font.FontFamily, 23f, FontStyle.Bold); libraryTitle.AutoSize = true; libraryTitle.Location = new Point(0, 0);
            heading.Controls.Add(libraryTitle);
            var mainLibrary = MakeButton("主菜单背景", 115, false); mainLibrary.Location = new Point(285, 7);
            var loadingLibrary = MakeButton("加载背景", 115, true); loadingLibrary.Location = new Point(408, 7);
            mainLibraryButton = mainLibrary; loadingLibraryButton = loadingLibrary;
            mainLibrary.BackColor = library.IsLoading ? panel : Color.FromArgb(46, 85, 130);
            loadingLibrary.BackColor = library.IsLoading ? Color.FromArgb(46, 85, 130) : panel;
            var applyLoading = MakeButton("同步加载库", 120, false); applyLoading.Location = new Point(540, 7);
            mainLibrary.Click += delegate { SwitchLibrary("backgrounds"); };
            loadingLibrary.Click += delegate { SwitchLibrary("loading-backgrounds"); };
            applyLoading.Click += delegate {
                try { var loading = new Library(Path.Combine(managerRoot, "loading-backgrounds"));
                    int count = LoadingLibrary.Publish(loading); Reload("已同步 " + count + " 张加载背景，下次启动游戏生效。"); }
                catch (Exception error) { status.Text = "同步失败：" + error.Message; }
            };
            heading.Controls.AddRange(new Control[] { mainLibrary, loadingLibrary, applyLoading });
            counts.Location = new Point(3, 43); counts.AutoSize = true; counts.ForeColor = Color.FromArgb(157, 176, 198); heading.Controls.Add(counts);
            layout.Controls.Add(heading, 0, 0);

            var toolbar = new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false, Padding = new Padding(0, 4, 0, 0) };
            var searchLabel = new Label { Text = "搜索", Width = 44, Height = 34, TextAlign = ContentAlignment.MiddleLeft, Margin = new Padding(0) };
            search.Width = 241; search.BackColor = panel; search.ForeColor = ink; search.BorderStyle = BorderStyle.FixedSingle; search.Margin = new Padding(0, 3, 10, 0);
            new ToolTip().SetToolTip(search, "搜索背景名称或目录编号");
            SetupButton(category, "全部背景 ▾", 115, panel);
            var categories = new ContextMenuStrip();
            foreach (var name in new[] { "全部背景", "可用", "待确认", "已停用", "已删除" })
            {
                var choice = name;
                categories.Items.Add(name, null, delegate { SetFilter(choice); });
            }
            category.Click += delegate { categories.Show(category, new Point(0, category.Height)); };
            var refresh = MakeButton("刷新", 75, false);
            SetupButton(remove, "删除选中", 105, Color.FromArgb(133, 53, 64));
            SetupButton(restore, "恢复选中", 105, Color.FromArgb(41, 107, 91));
            SetupButton(undo, "撤销删除", 105, panel); undo.Enabled = false;
            toolbar.Controls.AddRange(new Control[] { searchLabel, search, category, refresh, remove, restore, undo });
            layout.Controls.Add(toolbar, 0, 1);

            var split = new SplitContainer { Size = new Size(ClientSize.Width - 40, ClientSize.Height - 195), Dock = DockStyle.Fill, BackColor = background, SplitterWidth = 10, Panel1MinSize = 360, Panel2MinSize = 490 };
            layout.Controls.Add(split, 0, 2);
            split.SplitterDistance = Math.Max(360, Math.Min(550, ClientSize.Width * 43 / 100));
            icons.ImageSize = new Size(166, 112); icons.ColorDepth = ColorDepth.Depth32Bit;
            grid.Dock = DockStyle.Fill; grid.View = View.LargeIcon; grid.LargeImageList = icons;
            grid.MultiSelect = true; grid.HideSelection = false; grid.BackColor = panel; grid.ForeColor = ink;
            grid.BorderStyle = BorderStyle.None; grid.ShowItemToolTips = true; grid.Font = new Font(Font.FontFamily, 9f);
            split.Panel1.Controls.Add(grid);

            var previewLayout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4, Padding = new Padding(15), BackColor = panel };
            previewLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 62));
            previewLayout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            previewLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 85));
            previewLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 43));
            split.Panel2.Controls.Add(previewLayout);
            title.Dock = DockStyle.Fill; title.Font = new Font(Font.FontFamily, 15f, FontStyle.Bold); title.AutoEllipsis = true;
            previewLayout.Controls.Add(title, 0, 0);
            var pictureHost = new Panel { Dock = DockStyle.Fill, BackColor = Color.FromArgb(10, 14, 20) };
            picture.Dock = DockStyle.Fill; picture.SizeMode = PictureBoxSizeMode.Zoom; picture.BackColor = pictureHost.BackColor;
            empty.Dock = DockStyle.Fill; empty.TextAlign = ContentAlignment.MiddleCenter; empty.Text = "选择一套背景，开始预览"; empty.ForeColor = Color.FromArgb(130, 148, 169);
            pictureHost.Controls.Add(picture); pictureHost.Controls.Add(empty);
            previewLayout.Controls.Add(pictureHost, 0, 1);
            detail.Dock = DockStyle.Fill; detail.Padding = new Padding(0, 10, 0, 0); detail.AutoEllipsis = true; detail.ForeColor = Color.FromArgb(165, 184, 204);
            previewLayout.Controls.Add(detail, 0, 2);
            var actions = new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false, Padding = new Padding(0, 3, 0, 0) };
            var previous = MakeButton("上一套", 66, false); var next = MakeButton("下一套", 66, false);
            SetupButton(zoom, "放大查看", 86, Color.FromArgb(46, 85, 130));
            SetupButton(open, "打开目录", 86, panel);
            var nextFrame = MakeButton("其他图片", 86, false);
            actions.Controls.AddRange(new Control[] { previous, next, zoom, open, nextFrame });
            previewLayout.Controls.Add(actions, 0, 3);
            status.Dock = DockStyle.Fill; status.TextAlign = ContentAlignment.MiddleLeft; status.AutoEllipsis = true; status.ForeColor = Color.FromArgb(158, 178, 199);
            layout.Controls.Add(status, 0, 3);

            search.TextChanged += delegate { Filter(); };
            refresh.Click += delegate { Reload("已刷新背景库。"); };
            grid.SelectedIndexChanged += delegate { if (!updating) ShowSelection(); };
            grid.DoubleClick += delegate { Zoom(); };
            remove.Click += delegate { RemoveSelected(); };
            restore.Click += delegate { RestoreSelected(); };
            undo.Click += delegate { Undo(); };
            previous.Click += delegate { Step(-1); }; next.Click += delegate { Step(1); };
            zoom.Click += delegate { Zoom(); };
            open.Click += delegate { if (current != null) Process.Start(new ProcessStartInfo(current.Directory) { UseShellExecute = true }); };
            nextFrame.Click += delegate { if (current != null && current.Previews.Count > 1) { frame = (frame + 1) % current.Previews.Count; LoadPicture(); } };
            KeyDown += OnKey;
            Reload("Ctrl / Shift 多选；Delete 删除选中；删除可在“已删除”中恢复，Ctrl+Z 撤销本次。");
        }

        private void SetupButton(Button button, string text, int width, Color color)
        {
            button.Text = text; button.Width = width; button.Height = 34;
            button.FlatStyle = FlatStyle.Flat; button.FlatAppearance.BorderSize = 0; button.BackColor = color; button.ForeColor = ink;
            button.Margin = new Padding(0, 0, 8, 0); button.Cursor = Cursors.Hand;
        }
        public void SwitchLibrary(string folder)
        {
            if (folder != "backgrounds" && folder != "loading-backgrounds") throw new IOException("未知背景库。");
            try
            {
                var selected = new Library(Path.Combine(managerRoot, folder));
                library = selected; lastRemoved.Clear(); undo.Enabled = false;
                filterName = "全部背景"; category.Text = "全部背景 ▾"; search.Clear();
                libraryTitle.Text = library.IsLoading ? "加载背景" : "主菜单背景";
                mainLibraryButton.BackColor = library.IsLoading ? panel : Color.FromArgb(46, 85, 130);
                loadingLibraryButton.BackColor = library.IsLoading ? Color.FromArgb(46, 85, 130) : panel;
                Reload(library.IsLoading ? "读档 / 过门加载画面；删除和恢复自动同步，下次启动游戏生效。" : "每次启动随机选择一套主菜单背景。");
            }
            catch (Exception error) { status.Text = "切换失败：" + error.Message; }
        }
        private Button MakeButton(string text, int width, bool accent)
        {
            var button = new FlatButton(); SetupButton(button, text, width, accent ? Color.FromArgb(46, 85, 130) : panel); return button;
        }
        public static Image ReadImage(string path)
        {
            Library.NoLinks(path);
            // Clone before disposing the stream: no file locks remain during move.
            using (var stream = new MemoryStream(File.ReadAllBytes(path)))
            using (var source = Image.FromStream(stream)) return new Bitmap(source);
        }
        private Image Thumbnail(Theme theme)
        {
            var bitmap = new Bitmap(166, 112);
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(Color.FromArgb(10, 14, 20)); graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                if (theme.Previews.Count > 0)
                {
                    try
                    {
                        using (var image = ReadImage(theme.Previews[0]))
                        {
                            double ratio = Math.Min(166d / image.Width, 112d / image.Height);
                            int width = (int)(image.Width * ratio), height = (int)(image.Height * ratio);
                            graphics.DrawImage(image, (166 - width) / 2, (112 - height) / 2, width, height);
                        }
                    }
                    catch { graphics.DrawString("预览不可用", Font, Brushes.Gray, 28, 42); }
                }
                else graphics.DrawString("无预览图", Font, Brushes.Gray, 38, 42);
            }
            return bitmap;
        }
        private static string Identity(Theme theme) { return theme.Removed == null ? theme.Id : "trash:" + theme.Removed.id; }

        private void Reload(string message)
        {
            try
            {
                updating = true; grid.Items.Clear(); SetPicture(null);
                icons.Images.Clear(); foreach (var image in thumbnails) image.Dispose(); thumbnails.Clear();
                themes = library.Scan();
                foreach (var theme in themes)
                {
                    var image = Thumbnail(theme); thumbnails.Add(image); icons.Images.Add(Identity(theme), image);
                }
                counts.Text = String.Format("{0} 套可用  ·  {1} 项待确认  ·  {2} 项已删除", themes.Count(t => t.State == "可用"), themes.Count(t => t.State == "待确认"), themes.Count(t => t.State == "已删除"));
                updating = false; Filter();
                status.Text = message + (library.Warnings.Count > 0 ? "  有 " + library.Warnings.Count + " 项读取失败：" + library.Warnings[0] : "");
            }
            catch (Exception error) { updating = false; status.Text = "读取失败：" + error.Message; }
        }

        private void Filter()
        {
            updating = true; grid.BeginUpdate(); grid.Items.Clear();
            string query = search.Text.Trim(); string mode = filterName;
            foreach (var theme in themes)
            {
                if (mode == "全部背景" ? theme.State == "已删除" : theme.State != mode) continue;
                if (!String.IsNullOrEmpty(query) && (theme.Name + " " + theme.Id).IndexOf(query, StringComparison.OrdinalIgnoreCase) < 0) continue;
                string shortName = theme.Name.Length > 34 ? theme.Name.Substring(0, 32) + "…" : theme.Name;
                var item = new ListViewItem(shortName, Identity(theme)) { Tag = theme, ToolTipText = theme.Name + "\n" + theme.Id + "\n" + theme.State };
                grid.Items.Add(item);
            }
            grid.EndUpdate(); updating = false;
            if (grid.Items.Count > 0) { grid.Items[0].Selected = true; grid.Items[0].Focused = true; }
            ShowSelection();
        }
        private void SetFilter(string name) { filterName = name; category.Text = name + " ▾"; Filter(); }
        private void ShowSelection()
        {
            current = grid.SelectedItems.Count > 0 ? (Theme)(grid.FocusedItem != null && grid.FocusedItem.Selected ? grid.FocusedItem.Tag : grid.SelectedItems[0].Tag) : null;
            frame = 0;
            int selected = grid.SelectedItems.Count;
            remove.Enabled = selected > 0 && current.Removed == null;
            restore.Enabled = selected > 0 && current.Removed != null;
            remove.Text = selected > 0 ? "删除选中 (" + selected + ")" : "删除选中";
            open.Enabled = current != null; zoom.Enabled = current != null && current.Previews.Count > 0;
            title.Text = current == null ? "暂无背景" : current.Name;
            detail.Text = current == null ? "试试调整搜索条件或分类。" : current.State + "   " + (current.Dimensions ?? "") +
                (current.Bytes > 0 ? "   " + (current.Bytes / 1048576d).ToString("0.0") + " MB" : "") + "\n" + current.Id +
                "\n" + (String.IsNullOrEmpty(current.Notes) ? "双击缩略图或点击“放大查看”。图片预览不包含模型动画和音乐。" : current.Notes);
            LoadPicture();
        }
        private void SetPicture(Image image)
        {
            var previous = picture.Image; picture.Image = image; if (previous != null) previous.Dispose();
            empty.Visible = image == null;
        }
        private void LoadPicture()
        {
            SetPicture(null);
            if (current == null || current.Previews.Count == 0) return;
            try
            {
                var path = current.Previews[frame];
                var large = Path.Combine(current.Directory, Path.GetFileNameWithoutExtension(path) + "-large.jpg");
                if (File.Exists(large)) path = large;
                SetPicture(ReadImage(path));
            }
            catch (Exception error) { empty.Text = "预览读取失败"; status.Text = error.Message; }
        }
        private void Step(int delta)
        {
            if (grid.Items.Count == 0) return;
            int index = grid.SelectedIndices.Count > 0 ? grid.SelectedIndices[0] : 0;
            index = Math.Max(0, Math.Min(grid.Items.Count - 1, index + delta));
            SelectAt(index);
        }
        private void SelectAt(int index)
        {
            if (grid.Items.Count == 0) return;
            updating = true;
            foreach (var item in grid.SelectedItems.Cast<ListViewItem>().ToArray()) item.Selected = false;
            var next = grid.Items[Math.Min(index, grid.Items.Count - 1)]; next.Selected = true; next.Focused = true; next.EnsureVisible();
            updating = false; ShowSelection();
        }
        private void RemoveSelected()
        {
            var selected = grid.SelectedItems.Cast<ListViewItem>().Select(i => (Theme)i.Tag).Where(t => t.Removed == null).ToList();
            if (selected.Count == 0) return;
            int index = grid.SelectedIndices[0]; var removed = new List<RemovedEntry>(); var errors = new List<string>();
            SetPicture(null);
            foreach (var theme in selected)
                try { removed.Add(library.Remove(theme)); } catch (Exception error) { errors.Add(theme.Name + "：" + error.Message); }
            if (removed.Count > 0) lastRemoved = removed;
            undo.Enabled = lastRemoved.Count > 0;
            Reload("已删除 " + removed.Count + " 套，可在“已删除”中恢复。" + (errors.Count > 0 ? "  未处理 " + errors.Count + " 套：" + errors[0] : ""));
            SelectAt(index);
        }
        private void RestoreSelected()
        {
            var selected = grid.SelectedItems.Cast<ListViewItem>().Select(i => (Theme)i.Tag).Where(t => t.Removed != null).ToList();
            var errors = new List<string>(); int count = 0; SetPicture(null);
            foreach (var theme in selected)
                try { library.Restore(theme.Removed); lastRemoved.RemoveAll(r => r.id == theme.Removed.id); count++; }
                catch (Exception error) { errors.Add(theme.Name + "：" + error.Message); }
            undo.Enabled = lastRemoved.Count > 0;
            Reload("已恢复 " + count + " 套。" + (errors.Count > 0 ? "  未恢复：" + errors[0] : ""));
        }
        private void Undo()
        {
            var pending = new List<RemovedEntry>(); var errors = new List<string>(); int count = 0;
            foreach (var record in lastRemoved)
                try { library.Restore(record); count++; } catch (Exception error) { pending.Add(record); errors.Add(error.Message); }
            lastRemoved = pending; undo.Enabled = pending.Count > 0;
            Reload("已撤销删除，恢复 " + count + " 套。" + (errors.Count > 0 ? "  " + errors[0] : ""));
        }
        private void OnKey(object sender, KeyEventArgs e)
        {
            if (search.Focused) return;
            if (e.KeyCode == Keys.Delete && remove.Enabled) { RemoveSelected(); e.Handled = true; }
            else if (e.Control && e.KeyCode == Keys.Z && undo.Enabled) { Undo(); e.Handled = true; }
            else if (e.Control && e.KeyCode == Keys.A)
            {
                updating = true; foreach (ListViewItem item in grid.Items) item.Selected = true; updating = false; ShowSelection(); e.Handled = true;
            }
        }
        private void Zoom()
        {
            if (picture.Image == null || current == null) return;
            using (var window = new Form { Text = current.Name + " — Esc 返回", BackColor = Color.FromArgb(10, 14, 20), WindowState = FormWindowState.Maximized, KeyPreview = true })
            using (var image = new Bitmap(picture.Image))
            {
                window.Controls.Add(new PictureBox { Dock = DockStyle.Fill, SizeMode = PictureBoxSizeMode.Zoom, Image = image });
                window.KeyDown += delegate(object sender, KeyEventArgs e) { if (e.KeyCode == Keys.Escape) window.Close(); };
                window.ShowDialog(this);
            }
        }

        public void SaveWindowPreview(string path)
        {
            using (var bitmap = new Bitmap(Width, Height)) { DrawToBitmap(bitmap, new Rectangle(0, 0, Width, Height)); bitmap.Save(path, ImageFormat.Png); }
        }
        public void CheckUi()
        {
            if (grid.Items.Count != 3) throw new Exception("UI initial count");
            search.Text = "第二"; if (grid.Items.Count != 1 || current.Name != "第二套") throw new Exception("UI search");
            search.Text = ""; SetFilter("待确认"); if (grid.Items.Count != 1) throw new Exception("UI review filter");
            SetFilter("可用"); grid.Items[0].Selected = true; grid.Items[0].Focused = true;
            ShowSelection(); remove.PerformClick(); if (grid.Items.Count != 1) throw new Exception("UI remove");
            undo.PerformClick(); if (grid.Items.Count != 2) throw new Exception("UI undo");
            SetFilter("已删除"); if (grid.Items.Count != 0) throw new Exception("UI empty trash");
            SetFilter("全部背景");
            System.IO.Directory.CreateDirectory(Path.Combine(managerRoot, "loading-backgrounds"));
            SwitchLibrary("loading-backgrounds");
            if (!library.IsLoading || grid.Items.Count != 0) throw new Exception("UI loading library switch");
            SwitchLibrary("backgrounds");
            if (library.IsLoading || grid.Items.Count != 3) throw new Exception("UI main library switch");
        }
        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                SetPicture(null); icons.Dispose(); foreach (var image in thumbnails) image.Dispose(); Font.Dispose();
            }
            base.Dispose(disposing);
        }
    }

    internal static class Program
    {
        [DllImport("user32.dll")] private static extern bool SetProcessDPIAware();
        [STAThread]
        private static int Main(string[] args)
        {
            SetProcessDPIAware(); Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            try
            {
                if (args.Length > 0 && args[0] == "--self-test") return BrowserTests.Run(args[1]);
                if (args.Length > 0 && args[0] == "--publish-loading")
                { LoadingLibrary.Publish(new Library(args[1])); return 0; }
                string root = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "backgrounds");
                string capture = null;
                for (int i = 0; i < args.Length; i++)
                {
                    if (args[i] == "--library" && i + 1 < args.Length) root = args[++i];
                    else if (args[i] == "--capture" && i + 1 < args.Length) capture = Path.GetFullPath(args[++i]);
                }
                using (var form = new BrowserForm(root))
                {
                    if (capture != null)
                    {
                        var timer = new Timer { Interval = 1200 };
                        timer.Tick += delegate { timer.Stop(); form.SaveWindowPreview(capture); form.Close(); timer.Dispose(); };
                        form.Shown += delegate { timer.Start(); };
                    }
                    Application.Run(form);
                }
                return 0;
            }
            catch (Exception error)
            {
                if (args.Contains("--publish-loading"))
                { File.WriteAllText(Path.Combine(args[1], "publish-error.txt"), error.ToString(), Encoding.UTF8); }
                else if (args.Contains("--capture") || args.Contains("--self-test"))
                {
                    var file = args.Contains("--self-test") ? Path.Combine(args[1], "failure.txt") : args[Array.IndexOf(args, "--capture") + 1] + ".error.txt";
                    File.WriteAllText(file, error.ToString(), Encoding.UTF8);
                }
                else MessageBox.Show(error.Message, "开屏背景管理器", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
    }
}
