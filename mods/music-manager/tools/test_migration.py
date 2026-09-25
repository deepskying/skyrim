import tempfile
import unittest
import json
import subprocess
import sys
from pathlib import Path
from migrate_dcs_complete import CATEGORIES, RANKS, categories_for, collect_groups, discover_sources


class MigrationTests(unittest.TestCase):
    def test_core_and_resources_are_both_discovered(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = ['----资源-DCS-城镇', '音乐模组-背景音效-DCS-Dynamic Customizable Soundtrack Music SE', '音乐管理器']
            for name in names:
                (root / name).mkdir()
            core = root / names[1]
            for name in ['Cemetery01.mp3', 'Cemetery01.xwm', 'Town01.xwm', '说明.txt']:
                (core / name).write_text('fixture')
            sources = discover_sources(root)
            self.assertEqual({p.name for p in sources}, set(names[:2]))
            groups = collect_groups(sources)
            self.assertEqual(len(groups), 2)
            self.assertEqual(sum(map(len, groups)), 3)
            cemetery = next(g for g in groups if g[0].stem == 'Cemetery01')
            self.assertEqual(min(cemetery, key=lambda p: RANKS[p.suffix]).suffix, '.mp3')

    def test_categories_and_priority(self):
        cases = {
            'Music/00DCS/TOWN/ALL/ANY/Explore20.xwm': ['town'],
            'Music/00DCS/CASTLE/WHITERUN/ANY/Castle01.xwm': ['castle'],
            'Music/00DCS/CEMETERY/Cemetery01.mp3': ['cemetery'],
            'Music/00DCS/TEMPLE/Music01.xwm': ['temple'],
            'Music/00DCS/TAVERN/ALL/Tavern01.xwm': ['tavern'],
            'Music/00DCS/EXPLORE/ALL/NIGHT/Explore01.xwm': ['explore'],
            'Music/00DCS/EXPLORE/ALL/ANY/Explore01.xwm': ['explore'],
            'Music/00DCS/ALL/ANY/CombatBoss01.xwm': ['combat'],
            'Music/00DCS/ALL/ANY/CombatDragon01.xwm': ['dragon'],
            'Music/00DCS/ALL/ANY/CombatDragonEnd.xwm': [],
            'Music/00DCS/STINGERS/LevelUp.xwm': [],
            'Music/00DCS/Silent End (copy, rename, & use for CombatXXEnd where needed).xwm': [],
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(categories_for(Path(path)), expected)
        self.assertEqual(len(CATEGORIES), 11)

    def test_sync_preserves_music_and_disabled_preferences(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old, new, mod = [root / name for name in ['old', 'new', 'mod']]
            prefix = Path('Data/Music/MusicManager')
            for base in [old / prefix, new / prefix, mod / 'Music/MusicManager']:
                (base / '墓地').mkdir(parents=True)
            for base in [old / prefix, mod / 'Music/MusicManager']:
                (base / '墓地/song.flac').write_bytes(b'old decoded copy')
            (mod / 'Music/MusicManager/墓地/personal.mp3').write_bytes(b'personal music')
            (new / prefix / '墓地/song.mp3').write_bytes(b'converted MP3')
            for base, extension in [(old, 'flac'), (new, 'mp3')]:
                report = {'errors': [], 'entries': [{'source': 'DCS/song.xwm', 'destinations': [
                    {'path': str(prefix / f'墓地/song.{extension}'), 'duplicate': False}]}]}
                (base / 'migration-report.json').write_text(json.dumps(report), encoding='utf-8')
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'disabled': ['墓地/song.flac'], 'volume': .37}), encoding='utf-8')
            script = Path(__file__).with_name('sync_library.py')
            subprocess.run([sys.executable, str(script), '--import-root', str(new), '--previous-root', str(old),
                            '--mod', str(mod), '--backup', str(root / 'backup'), '--settings', str(settings)],
                           check=True, capture_output=True)
            self.assertFalse((mod / 'Music/MusicManager/墓地/song.flac').exists())
            self.assertTrue((root / 'backup/retired-music/墓地/song.flac').exists())
            self.assertEqual((mod / 'Music/MusicManager/墓地/personal.mp3').read_bytes(), b'personal music')
            self.assertTrue((old / prefix / '墓地/song.flac').exists())
            updated = json.loads(settings.read_text(encoding='utf-8'))
            self.assertEqual(updated, {'disabled': ['墓地/song.mp3'], 'volume': .37})


if __name__ == '__main__':
    unittest.main()
