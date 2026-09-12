"""Validate shipped plugins with the repository's independent TES4 reader."""
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mods/glacial-crown/source"))
from plugin_records import records, subrecords
from build_plugins import MODULES, plugin


class PanelPluginTests(unittest.TestCase):
    def test_shipped_powers(self):
        for folder, (name, title) in MODULES.items():
            with self.subTest(plugin=name):
                path = ROOT / "mods" / folder / "packaging" / (name + ".esp")
                self.assertEqual(path.read_bytes(), plugin(name, title), "generated asset is stale")
                parsed = list(records(path))
                self.assertEqual([r['sig'] for r in parsed], [b'TES4', b'MGEF', b'SPEL'])
                header, effect, spell = parsed
                self.assertTrue(header['flags'] & 0x200, "must remain a light plugin")
                masters = [v for k, v in subrecords(header['data']) if k == b'MAST']
                self.assertEqual(masters, [b'Skyrim.esm\0'], "modules must install independently")
                self.assertEqual({r['form'] for r in parsed[1:]}, {0x01000800, 0x01000801})
                for r in parsed[1:]:
                    self.assertEqual(r['version'], 44)
                    self.assertFalse(r['flags'] & (0x20 | 0x80), "no deleted/localized records")
                s = dict(subrecords(spell['data']))
                self.assertEqual(s[b'FULL'].rstrip(b'\0').decode('utf-8'), title)
                self.assertEqual(struct.unpack('<I', s[b'ETYP'])[0], 0x25BEE, "use the power slot")
                cost, flags, kind, charge, cast, delivery, duration, distance, perk = struct.unpack('<IIIfIIffI', s[b'SPIT'])
                self.assertEqual((cost, kind, charge, cast, delivery, duration, distance, perk),
                                 (0, 3, 0, 1, 0, 0, 0, 0), "repeatable zero-cost self lesser power")
                self.assertTrue(flags & 1, "manual zero cost")
                self.assertTrue(flags & 0x200000, "cannot be absorbed")
                self.assertEqual(struct.unpack('<I', s[b'EFID'])[0], effect['form'])
                self.assertEqual(struct.unpack('<fII', s[b'EFIT']), (0, 0, 0))
                e = dict(subrecords(effect['data']))
                self.assertNotIn(b'VMAD', e, "no missing Papyrus dependency")
                self.assertNotIn(b'SNDD', e, "no effect sound")
                data = e[b'DATA']
                self.assertEqual(len(data), 152)
                self.assertFalse(struct.unpack_from('<I', data)[0] & 5, "nonhostile, nondetrimental")
                self.assertEqual(struct.unpack_from('<I', data, 64)[0], 1, "inert script archetype")
                self.assertEqual(struct.unpack_from('<IIi', data, 80), (1, 0, -1))
                self.assertEqual(struct.unpack_from('<f', data, 104)[0], 0, "no skill XP")
                self.assertEqual(struct.unpack_from('<I', data, 140)[0], 2, "silent")
                for offset in (8, 24, 32, 36, 72, 76, 92, 96, 100, 108, 116, 120, 124, 128, 132, 136):
                    self.assertEqual(struct.unpack_from('<I', data, offset)[0], 0, "no gameplay/visual form references")


if __name__ == '__main__':
    unittest.main()
