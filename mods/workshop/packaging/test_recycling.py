import json
import unittest
from package import OUT, ROOT

class NativeRecyclingTests(unittest.TestCase):
    def test_reported_mod_armor_reaches_resolvable_category_fallback(self):
        rules = json.loads((ROOT / 'data/SKSE/Plugins/EquipmentWorkshop.recycling.rules.json').read_text())
        # ARMO metadata read from Ninirim Collection and WoW Accessories ESPs.
        # Neither item has a crafting recipe or a material keyword.
        examples = [
            ('a00ClothesLinkleCape', {'ArmorClothing', 'ClothingBody', 'VendorItemClothing'}),
            ('Sho13b', {'ArmorLight'}),
        ]
        for editor_id, keywords in examples:
            with self.subTest(editor_id=editor_id):
                match = next(r for r in rules['rules'] if r.get('formType', 26) == 26
                             and (not r.get('keyword') or r['keyword'] in keywords))
                self.assertEqual(match['output'], {'plugin': 'Skyrim.esm', 'id': 0x800E4})
                self.assertGreater(match['weightRatio'], 0)

    def test_rules_reference_only_native_masters(self):
        rules = json.loads((ROOT / 'data/SKSE/Plugins/EquipmentWorkshop.recycling.rules.json').read_text())
        self.assertEqual(rules['version'], 1)
        self.assertGreaterEqual(sum(len(g['items']) for g in rules['groups']), 70)
        for record in [r['output'] for r in rules['rules']] + [g['output'] for g in rules['groups']] + [i for g in rules['groups'] for i in g['items']]:
            self.assertIn(record['plugin'], ['Skyrim.esm', 'HearthFires.esm', 'Dragonborn.esm'])
            self.assertTrue(0 < record['id'] <= 0xFFFFFF)

    def test_package_has_no_old_recycling_runtime(self):
        self.assertTrue((OUT / 'SKSE/Plugins/EquipmentWorkshop.dll').is_file())
        self.assertTrue((OUT / 'SKSE/Plugins/EquipmentWorkshop.recycling.rules.json').is_file())
        self.assertEqual({'DurabilityManager.esp', 'MagicArrows.esp'}, {p.name for p in OUT.glob('*.esp')})
        self.assertFalse(list(OUT.rglob('zsr*')))
        self.assertFalse(list(OUT.rglob('SimpleRecycling*')))

if __name__ == '__main__': unittest.main()
