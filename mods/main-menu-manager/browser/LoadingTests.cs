using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;

namespace MainMenuBrowser
{
    internal static class LoadingTests
    {
        private static int checks;
        private static void Check(bool value, string name) { checks++; if (!value) throw new Exception(name); }
        private static void Fails(Action action, string name) { bool failed = false; try { action(); } catch { failed = true; } Check(failed, name); }
        private static byte[] Join(params byte[][] items) { return items.SelectMany(x => x).ToArray(); }
        private static byte[] Sub(string sig, byte[] data) { return Join(Encoding.ASCII.GetBytes(sig), BitConverter.GetBytes((ushort)data.Length), data); }
        private static byte[] Record(string sig, uint id, params byte[][] fields)
        {
            var data = Join(fields);
            return Join(Encoding.ASCII.GetBytes(sig), BitConverter.GetBytes(data.Length), new byte[4], BitConverter.GetBytes(id), new byte[4], new byte[] {44, 0, 0, 0}, data);
        }
        private static void Fixture(string root, string name, uint id)
        {
            var theme = Path.Combine(root, name); Directory.CreateDirectory(theme);
            var relative = "meshes/interface/loadingtests/" + name + ".nif";
            var file = Path.Combine(theme, "Data", relative); Directory.CreateDirectory(Path.GetDirectoryName(file)); File.WriteAllText(file, "fixture " + name);
            File.WriteAllText(Path.Combine(theme, "theme.json"), "{\"name\":\"" + name + "\",\"enabled\":true}");
            File.WriteAllBytes(Path.Combine(theme, "records.bin"), Join(
                Record("STAT", id, Sub("MODL", Encoding.ASCII.GetBytes(relative.Substring(7).Replace('/', '\\') + "\0"))),
                Record("LSCR", id + 1, Sub("NNAM", BitConverter.GetBytes(id)))));
            File.WriteAllText(Path.Combine(theme, "assets.json"), new JavaScriptSerializer().Serialize(new[] {
                new LoadingLibrary.Asset { path = relative, bytes = new FileInfo(file).Length, sha256 = LoadingLibrary.Hash(file) } }));
        }
        public static int Run(string fixture)
        {
            checks = 0;
            var root = Path.Combine(fixture, "loadingmod", "MainMenuManager", "loading-backgrounds");
            var system = Path.Combine(root, "_system"); Directory.CreateDirectory(system);
            File.WriteAllBytes(Path.Combine(system, "header.bin"), Record("TES4", 0,
                Sub("HEDR", Join(BitConverter.GetBytes(1.7f), BitConverter.GetBytes(6), BitConverter.GetBytes(0x900))),
                Sub("MAST", Encoding.ASCII.GetBytes("Skyrim.esm\0")), Sub("DATA", new byte[8])));
            Fixture(root, "one", 0x01000800); Fixture(root, "two", 0x01000802);
            var library = new Library(root);
            Check(library.IsLoading && Path.GetFileName(library.Trash) == "deleted-loading-backgrounds", "Separate loading trash");
            Check(LoadingLibrary.Publish(library) == 2, "Compile two LSCRs");
            var plugin = Path.Combine(fixture, "loadingmod", "sky-backgrounds-loading.esp"); var original = File.ReadAllBytes(plugin);
            var first = library.Scan().First(t => t.Id == "one"); var removed = library.Remove(first);
            Check(LoadingLibrary.Publish(library) == 1 && !File.ReadAllBytes(plugin).SequenceEqual(original), "Deleting screen updates plugin");
            library.Restore(removed);
            Check(File.ReadAllBytes(plugin).SequenceEqual(original), "Restore preserves IDs and original record bytes");
            File.WriteAllText(plugin, "external edit");
            Fails(delegate { library.Remove(library.Scan().First(t => t.Id == "one")); }, "External plugin edit blocks removal");
            Check(Directory.Exists(first.Directory) && File.ReadAllText(plugin) == "external edit", "Failed publish rolls directory back");
            File.WriteAllBytes(plugin, original);
            var one = library.Remove(library.Scan().First(t => t.Id == "one"));
            var two = library.Remove(library.Scan().First(t => t.Id == "two"));
            Check(LoadingLibrary.Publish(library) == 0, "Empty library produces zero custom screens");
            library.Restore(one); library.Restore(two);
            Check(File.ReadAllBytes(plugin).SequenceEqual(original), "Restore entire library after empty pool");
            var model = Path.Combine(fixture, "loadingmod", "meshes", "interface", "loadingtests", "one.nif");
            File.WriteAllText(model, "outside changed the deployed asset");
            Fails(delegate { library.Remove(library.Scan().First(t => t.Id == "two")); }, "Changed deployed model blocks publication");
            Check(library.Scan().Count(t => t.Removed == null) == 2, "Failed asset validation rolls removal back");
            Fails(delegate { LoadingLibrary.SafeAsset("textures/../../outside.dds"); }, "Reject traversal asset");
            Fails(delegate { LoadingLibrary.SafeAsset("SKSE/Plugins/evil.dll"); }, "Reject executable assets");
            Fails(delegate { LoadingLibrary.SafeAsset("C:/outside.dds"); }, "Reject absolute asset");
            return checks;
        }
    }
}
