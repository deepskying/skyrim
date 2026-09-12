using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace MainMenuBrowser
{
    // The loading library compiles vanilla LSCR/STAT records before the next game launch.
    // Asset copies are retained on removal so an interrupted update cannot create missing models.
    public static class LoadingLibrary
    {
        public sealed class Asset { public string path, sha256; public long bytes; }
        public sealed class Stamp { public long ticks, bytes; public string sha256; }
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 32 * 1024 * 1024 };
        public static string Hash(string file)
        {
            using (var sha = SHA256.Create()) using (var stream = File.OpenRead(file))
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        private static string Hash(byte[] bytes)
        {
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        }
        private static byte[] Read(string path)
        {
            Library.NoLinks(path);
            if (new FileInfo(path).Length > 32 * 1024 * 1024) throw new IOException("加载画面记录文件过大。");
            return File.ReadAllBytes(path);
        }
        private static void AtomicWrite(string path, byte[] bytes)
        {
            Library.NoLinks(path);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                using (var file = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                { file.Write(bytes, 0, bytes.Length); file.Flush(true); }
                if (File.Exists(path)) File.Replace(temporary, path, null); else File.Move(temporary, path);
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
        public static string SafeAsset(string relative)
        {
            if (String.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative)) throw new IOException("加载资源路径无效。");
            var parts = relative.Replace('/', '\\').Split('\\');
            if (parts.Length < 2 || parts.Any(p => p == "" || p == "." || p == ".." || p.EndsWith(".") || p.EndsWith(" ") || p.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0))
                throw new IOException("加载资源路径超出目录。");
            var result = String.Join("\\", parts);
            if (!(result.StartsWith("meshes\\interface\\", StringComparison.OrdinalIgnoreCase) && result.EndsWith(".nif", StringComparison.OrdinalIgnoreCase)) &&
                !(result.StartsWith("textures\\", StringComparison.OrdinalIgnoreCase) && result.EndsWith(".dds", StringComparison.OrdinalIgnoreCase)))
                throw new IOException("只接受加载画面的 NIF 和 DDS 资源。");
            return result;
        }
        private static string Signature(byte[] bytes, int position) { return Encoding.ASCII.GetString(bytes, position, 4); }
        private static IEnumerable<byte[]> Records(byte[] bytes)
        {
            int p = 0;
            while (p < bytes.Length)
            {
                if (bytes.Length - p < 24) throw new IOException("加载记录头不完整。");
                uint size = BitConverter.ToUInt32(bytes, p + 4);
                if (size > bytes.Length - p - 24) throw new IOException("加载记录长度无效。");
                var record = new byte[24 + (int)size]; Buffer.BlockCopy(bytes, p, record, 0, record.Length);
                if ((BitConverter.ToUInt32(record, 8) & 0x40000) != 0) throw new IOException("加载记录需先解压。");
                yield return record; p += record.Length;
            }
        }
        private static Dictionary<string, List<byte[]>> Fields(byte[] record)
        {
            var fields = new Dictionary<string, List<byte[]>>(); int p = 24;
            while (p < record.Length)
            {
                if (record.Length - p < 6) throw new IOException("加载子记录不完整。");
                string sig = Signature(record, p); int size = BitConverter.ToUInt16(record, p + 4); p += 6;
                if (sig == "XXXX" || size > record.Length - p) throw new IOException("不支持的加载子记录。");
                var value = new byte[size]; Buffer.BlockCopy(record, p, value, 0, size); p += size;
                if (!fields.ContainsKey(sig)) fields[sig] = new List<byte[]>(); fields[sig].Add(value);
            }
            return fields;
        }
        private static byte[] One(Dictionary<string, List<byte[]>> fields, string key)
        {
            if (!fields.ContainsKey(key) || fields[key].Count != 1) throw new IOException("缺少唯一的加载记录字段：" + key);
            return fields[key][0];
        }
        private static byte[] Group(string sig, IEnumerable<byte[]> records)
        {
            using (var stream = new MemoryStream()) using (var writer = new BinaryWriter(stream))
            {
                writer.Write(Encoding.ASCII.GetBytes("GRUP")); writer.Write(0);
                writer.Write(Encoding.ASCII.GetBytes(sig)); writer.Write(new byte[12]);
                foreach (var record in records) writer.Write(record);
                stream.Position = 4; writer.Write((int)stream.Length); return stream.ToArray();
            }
        }
        public static int Publish(Library library)
        {
            if (!library.IsLoading) return 0;
            if (Process.GetProcessesByName("SkyrimSE").Length != 0) throw new IOException("请先退出 Skyrim，再应用加载背景。");
            var system = Path.Combine(library.Root, "_system");
            if (!File.Exists(Path.Combine(system, "header.bin"))) throw new IOException("加载库尚未导入，当前没有可同步的加载画面。");
            var modRoot = Path.GetDirectoryName(Path.GetDirectoryName(library.Root));
            var target = Path.Combine(modRoot, "sky-backgrounds-loading.esp");
            Library.NoLinks(target); Library.NoLinks(system);
            var header = Records(Read(Path.Combine(system, "header.bin"))).Single();
            var headerFields = Fields(header);
            if (One(headerFields, "HEDR").Length != 12) throw new IOException("加载插件 HEDR 无效。");
            if (Signature(header, 0) != "TES4" || BitConverter.ToUInt32(header, 8) != 0 ||
                Encoding.ASCII.GetString(One(headerFields, "MAST")) != "Skyrim.esm\0") throw new IOException("加载库的插件模板不匹配。");
            var hashFile = Path.Combine(system, "published-hashes.txt"); Library.NoLinks(hashFile);
            var hashes = File.Exists(hashFile) ? File.ReadAllLines(hashFile).ToList() : new List<string>();
            if (File.Exists(target) && !hashes.Contains(Hash(target))) throw new IOException("sky-backgrounds-loading.esp 已被外部修改，未覆盖。请保留文件后检查。");
            var cachePath = Path.Combine(system, "deployed.json"); Library.NoLinks(cachePath);
            var cache = File.Exists(cachePath) ? Json.Deserialize<Dictionary<string, Stamp>>(Encoding.UTF8.GetString(Read(cachePath))) : new Dictionary<string, Stamp>();
            var records = new SortedDictionary<uint, byte[]>();
            var assets = new Dictionary<string, Tuple<string, Asset>>(StringComparer.OrdinalIgnoreCase);
            var themes = library.Scan();
            if (library.Warnings.Count != 0) throw new IOException("加载库有读取错误，未应用：" + library.Warnings[0]);
            foreach (var theme in themes.Where(t => t.State == "可用"))
            {
                var themeRecords = Records(Read(Path.Combine(theme.Directory, "records.bin"))).ToList();
                if (themeRecords.Count(r => Signature(r, 0) == "LSCR") != 1) throw new IOException("每个加载目录必须包含一条 LSCR 记录：" + theme.Id);
                foreach (var record in themeRecords)
                {
                    string sig = Signature(record, 0); uint id = BitConverter.ToUInt32(record, 12);
                    if ((sig != "LSCR" && sig != "STAT") || (id >> 24) != 1 || (id & 0xFFFFFF) < 0x800)
                        throw new IOException("加载库包含非独立 LSCR/STAT 记录。");
                    Fields(record);
                    if (records.ContainsKey(id) && !records[id].SequenceEqual(record)) throw new IOException("加载记录编号冲突：" + theme.Id);
                    records[id] = record;
                }
                var map = Json.Deserialize<Asset[]>(Encoding.UTF8.GetString(Read(Path.Combine(theme.Directory, "assets.json"))));
                if (map == null || map.Length == 0) throw new IOException("加载资源清单为空。");
                foreach (var asset in map)
                {
                    var relative = SafeAsset(asset.path); var source = Path.Combine(theme.Directory, "Data", relative);
                    Library.NoLinks(source);
                    if (!File.Exists(source) || new FileInfo(source).Length != asset.bytes) throw new IOException("加载资源缺失或大小发生变化：" + source);
                    if (assets.ContainsKey(relative) && assets[relative].Item2.sha256 != asset.sha256) throw new IOException("加载贴图路径冲突：" + relative);
                    assets[relative] = Tuple.Create(source, asset);
                }
            }
            foreach (var record in records.Values)
            {
                var fields = Fields(record);
                if (Signature(record, 0) == "LSCR")
                {
                    var value = One(fields, "NNAM");
                    if (value.Length != 4 || !records.ContainsKey(BitConverter.ToUInt32(value, 0)) || Signature(records[BitConverter.ToUInt32(value, 0)], 0) != "STAT")
                        throw new IOException("加载画面引用了缺失的模型记录。");
                }
                else
                {
                    var model = SafeAsset("meshes\\" + Encoding.ASCII.GetString(One(fields, "MODL")).TrimEnd('\0'));
                    if (!assets.ContainsKey(model)) throw new IOException("加载模型没有配套资源：" + model);
                }
            }
            // Validate every destination before publishing anything. Existing assets are immutable.
            foreach (var pair in assets)
            {
                var destination = Path.Combine(modRoot, pair.Key); Library.NoLinks(destination);
                if (!Library.IsInside(modRoot, destination)) throw new IOException("输出目录无效。");
                var info = new FileInfo(destination); Stamp stamp;
                if (info.Exists && !(cache.TryGetValue(pair.Key, out stamp) && stamp.bytes == info.Length && stamp.ticks == info.LastWriteTimeUtc.Ticks && stamp.sha256 == pair.Value.Item2.sha256))
                    if (Hash(destination) != pair.Value.Item2.sha256) throw new IOException("已有加载资源不同，未覆盖：" + destination);
                if (!info.Exists && Hash(pair.Value.Item1) != pair.Value.Item2.sha256) throw new IOException("加载源文件校验失败：" + pair.Value.Item1);
            }
            foreach (var pair in assets)
            {
                var destination = Path.Combine(modRoot, pair.Key);
                if (!File.Exists(destination))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(destination));
                    var temporary = destination + "." + Guid.NewGuid().ToString("N") + ".tmp";
                    try { File.Copy(pair.Value.Item1, temporary, false); File.Move(temporary, destination); }
                    finally { if (File.Exists(temporary)) File.Delete(temporary); }
                }
                var info = new FileInfo(destination);
                cache[pair.Key] = new Stamp { bytes = info.Length, ticks = info.LastWriteTimeUtc.Ticks, sha256 = pair.Value.Item2.sha256 };
            }
            AtomicWrite(cachePath, Encoding.UTF8.GetBytes(Json.Serialize(cache)));
            // Preserve form IDs, master, conditions and presentation fields; only omit inactive entries.
            int offset = 24;
            while (Signature(header, offset) != "HEDR") offset += 6 + BitConverter.ToUInt16(header, offset + 4);
            Buffer.BlockCopy(BitConverter.GetBytes(records.Count + 2), 0, header, offset + 10, 4);
            uint nextId = BitConverter.ToUInt32(header, offset + 14);
            if (records.Count > 0) nextId = Math.Max(nextId, (records.Keys.Max() & 0xFFFFFF) + 1);
            Buffer.BlockCopy(BitConverter.GetBytes(nextId), 0, header, offset + 14, 4);
            byte[] output;
            using (var stream = new MemoryStream())
            {
                stream.Write(header, 0, header.Length);
                foreach (string sig in new[] { "STAT", "LSCR" })
                { var group = Group(sig, records.Values.Where(r => Signature(r, 0) == sig)); stream.Write(group, 0, group.Length); }
                output = stream.ToArray();
            }
            if (!hashes.Contains(Hash(output))) hashes.Add(Hash(output));
            // Record both old and intended hashes first, so a crash before/after replacement is recoverable.
            AtomicWrite(hashFile, Encoding.ASCII.GetBytes(String.Join("\n", hashes)));
            AtomicWrite(target, output);
            return records.Values.Count(r => Signature(r, 0) == "LSCR");
        }
    }
}
