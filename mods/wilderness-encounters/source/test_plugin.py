"""Validate shipped binary links, saved alias binding and optional templates."""
from pathlib import Path
import json
import struct
import sys
import unittest
from plugin_records import records, subrecords, edid
from build import ROOT, REPO, GAME_ROOT, validate_config

class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def unpack(self, fmt):
        result = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += struct.calcsize(fmt)
        return result

    def string(self):
        size, = self.unpack('<H')
        value = self.data[self.pos:self.pos+size].decode('utf8')
        self.pos += size
        return value

    def script(self):
        name = self.string()
        status, count = self.unpack('<BH')
        props = {}
        for _ in range(count):
            prop = self.string()
            typ, flags, unused, alias, form = self.unpack('<BBHHI')
            if (typ, flags, unused, alias) != (1, 1, 0, 0xFFFF):
                raise ValueError('Unexpected property encoding')
            props[prop] = form
        return name, status, props

class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = list(records(ROOT / 'data/WildernessEncounters.esp'))
        cls.by_id = {row['form']: row for row in cls.rows}
        cls.by_name = {edid(row): row for row in cls.rows}
        cls.parts = {key: dict(subrecords(row['data'])) for key, row in cls.by_name.items()}

    def test_light_plugin_ids_dependencies_and_record_count(self):
        header = self.rows[0]
        self.assertEqual(header['flags'] & 0x200, 0x200)
        parts = list(subrecords(header['data']))
        self.assertEqual([v for k, v in parts if k == b'MAST'], [b'Skyrim.esm\0'])
        self.assertEqual(struct.unpack('<fII', dict(parts)[b'HEDR'])[1], len(self.rows)-1)
        ids = [r['form'] for r in self.rows[1:]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(0x01000800 <= value < 0x01001000 for value in ids))
        self.assertEqual(set(row['sig'] for row in self.rows[1:]), {b'QUST', b'FLST', b'FACT', b'MESG', b'SPEL', b'MGEF'})

    def test_startup_quest_properties_and_load_game_alias(self):
        q = self.parts['WEControllerQuest']
        self.assertEqual(struct.unpack('<HBBII', q[b'DNAM'])[0], 0x11)
        self.assertEqual(q[b'ALFR'], struct.pack('<I', 0x14))
        reader = Reader(q[b'VMAD'])
        self.assertEqual(reader.unpack('<HHH'), (5, 2, 1))
        name, status, props = reader.script()
        self.assertEqual((name, status), ('WEController', 0))
        expected_types = {'Markers': b'FLST', 'Bandits': b'FLST', 'Wolves': b'FLST', 'Trolls': b'FLST',
                          'Beasts': b'FLST', 'Extras': b'FLST', 'Menu': b'MESG', 'Robbery': b'MESG',
                          'Directions': b'MESG', 'Warning': b'MESG', 'Help': b'MESG',
                          'SideA': b'FACT', 'SideB': b'FACT', 'SettingsPower': b'SPEL'}
        self.assertEqual(set(props), set(expected_types))
        for key, typ in expected_types.items():
            self.assertEqual(self.by_id[props[key]]['sig'], typ)
        self.assertEqual(reader.unpack('<BH'), (2, 0))
        self.assertEqual(reader.string(), '')
        self.assertEqual(reader.unpack('<H'), (1,))
        self.assertEqual(reader.unpack('<HHIHHH'), (0, 0, 0x01000800, 5, 2, 1))
        self.assertEqual(reader.script(), ('WELoadAlias', 0, {}))
        self.assertEqual(reader.pos, len(reader.data))
        self.assertEqual((ROOT / 'data/SEQ/WildernessEncounters.seq').read_bytes(), struct.pack('<I', 0x01000800))

    def test_all_vanilla_pool_and_marker_links_exist(self):
        master = {r['form']: r for r in records(GAME_ROOT / 'SkyrimSE/Data/Skyrim.esm',
                                               {b'CELL', b'WRLD', b'REFR', b'NPC_', b'LVLN'})}
        for name in ('WESpawnMarkers', 'WEBanditPool', 'WEWolfPool', 'WETrollPool', 'WEBeastPool'):
            forms = [struct.unpack('<I', value)[0] for key, value in subrecords(self.by_name[name]['data']) if key == b'LNAM']
            self.assertTrue(forms)
            self.assertEqual(len(forms), len(set(forms)))
            for form in forms:
                self.assertIn(form, master)
                if name == 'WESpawnMarkers':
                    row = master[form]
                    self.assertEqual(row['sig'], b'REFR')
                    self.assertTrue(row['flags'] & 0x400) # persistent marker
                    self.assertIn(dict(subrecords(row['data']))[b'XLRT'], (struct.pack('<I', 0x4A5FE), struct.pack('<I', 0x4A5F5)))
                else:
                    self.assertIn(master[form]['sig'], (b'NPC_', b'LVLN'))

    def test_readable_choice_boxes_and_setting_spell_script(self):
        for name, buttons in (('WESettingsMenu', 6), ('WERobbery', 3), ('WEDirections', 2), ('WEWarning', 2), ('WEHelp', 2)):
            row = self.by_name[name]
            parts = list(subrecords(row['data']))
            self.assertEqual(dict(parts)[b'DNAM'], struct.pack('<I', 1)) # waits for input
            self.assertEqual(len([v for k, v in parts if k == b'ITXT']), buttons)
            text = dict(parts)[b'DESC'].decode('utf8').rstrip('\0')
            self.assertTrue(text)
            self.assertNotIn('\ufffd', text)
        spell = self.parts['WESettingsPower']
        effect_id = struct.unpack('<I', spell[b'EFID'])[0]
        self.assertEqual(self.by_id[effect_id]['sig'], b'MGEF')
        effect = Reader(dict(subrecords(self.by_id[effect_id]['data']))[b'VMAD'])
        self.assertEqual(effect.unpack('<HHH'), (5, 2, 1))
        self.assertEqual(effect.script(), ('WESettingsEffect', 0, {}))
        for name in ('WEPools', 'WEController', 'WELoadAlias', 'WESettingsEffect'):
            self.assertEqual((ROOT / f'data/Scripts/{name}.pex').read_bytes()[:4], bytes.fromhex('fa57c0de'))
        self.assertIn('强盗头目'.encode('utf8'), (ROOT / 'data/Scripts/WEController.pex').read_bytes())

    def test_conflict_sides_are_mutual_enemies(self):
        for side, other in ((0, 1), (1, 0)):
            relation = self.parts['WEEncounterSide' + str(side)][b'XNAM']
            self.assertEqual(struct.unpack('<IiI', relation), (0x01000830+other, -100, 1))

    def test_optional_templates_in_current_install_are_nonunique_combatants(self):
        sys.path.insert(0, str(REPO / 'tools/weapon-balancer'))
        import scan
        import esp
        mo2 = GAME_ROOT / 'MO2'
        if not mo2.exists():
            self.skipTest('MO2 is not present')
        paths = scan.profile_paths(mo2, None)
        index = scan.plugin_index(paths['mods_dir'], GAME_ROOT / 'SkyrimSE/Data', scan.mod_priority(paths['modlist']))
        config = json.loads((ROOT / 'source/pools.json').read_text(encoding='utf8'))
        cache = {}
        for entry in validate_config(config):
            path = index.get(entry['plugin'].lower())
            if path is None:
                continue
            if path not in cache:
                masters = esp.read_header(path)['masters']
                cache[path] = {row['form'] & 0xFFFFFF: row for row in records(path, {b'NPC_'}) if row['form'] >> 24 == len(masters)}
            for value in entry['forms']:
                with self.subTest(group=entry['key'], form=value):
                    row = cache[path][int(value, 0)]
                    props = dict(subrecords(row['data']))
                    flags = struct.unpack_from('<I', props[b'ACBS'])[0]
                    self.assertEqual(flags & (0x2 | 0x20 | 0x800 | 0x20000000 | 0x80000000), 0)
                    self.assertEqual(row['flags'] & 0x20, 0) # deleted record
                    self.assertFalse(any(word in edid(row).lower() for word in ('audio', 'sound', 'voice', 'pet')))
                    self.assertNotIn(b'VMAD', props) # custom scripts need separate review
                    position = entry['forms'].index(value)
                    self.assertEqual(edid(row), entry['editor_ids'][position])
                    if int(entry['id'], 0) > 0x908:
                        level = struct.unpack_from('<H', props[b'ACBS'], 10)[0] if flags & 128 else struct.unpack_from('<h', props[b'ACBS'], 8)[0]
                        self.assertGreaterEqual(entry['min_level'], min(level, 80))

    def test_pool_ids_preserve_previous_save_bindings(self):
        config = json.loads((ROOT / 'source/pools.json').read_text(encoding='utf8'))
        original = ('cyrodiil_wolves', 'ogres', 'ettins', 'goblins', 'mountain_lions',
                    'snow_leopards', 'monster_wolves', 'monster_trolls', 'monster_spiders')
        by_key = {entry['key']: entry for entry in config['groups']}
        for index, key in enumerate(original):
            self.assertEqual(int(by_key[key]['id'], 0), 0x900 + index)
        for entry in config['groups']:
            row = self.by_id[0x01000000 | int(entry['id'], 0)]
            self.assertEqual(row['sig'], b'FLST')
            self.assertEqual(edid(row), 'WEExtra_' + entry['key'])
        menu = self.parts['WESettingsMenu'][b'DESC'].decode('utf8')
        self.assertIn(config['version'], menu)
        self.assertIn(str(len(config['groups'])), menu)

    def test_configuration_rejects_invalid_names_and_ids(self):
        for entry in ({'key': 'a', 'plugin': 'x".esp', 'forms': ['0x800']},
                      {'key': 'a', 'plugin': 'x.esp', 'forms': ['0x01000800']},
                      {'key': 'a', 'plugin': 'x.esp', 'forms': ['0x800', '0x800']},
                      {'key': 'a', 'plugin': 'x.esp', 'forms': ['0x800'], 'min_level': 0},
                      {'key': 'a', 'plugin': 'x.esp', 'forms': ['0x800'], 'id': '0x800'}):
            with self.assertRaises(ValueError):
                validate_config({'groups': [entry]})

if __name__ == '__main__':
    unittest.main()
