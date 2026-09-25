import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os
from merge_exploration import merge


class MergeTests(unittest.TestCase):
    def test_dedup_collision_preferences_and_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / 'library'
            tracks = {'野外/existing.MP3': b'existing', '野外白天/一首.mp3': b'shared',
                      '野外夜晚/sub/别名.mp3': b'shared', '野外夜晚/一首.mp3': b'different',
                      '野外白天/nested/added.flac': b'personal', '城镇/town.mp3': b'town',
                      '_已删除/batch/野外白天/deleted.mp3': b'deleted', '野外白天/说明.txt': b'note'}
            for name, data in tracks.items():
                path = library / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            settings = root / 'settings.json'
            config = {'disabled': ['野外夜晚/sub/别名.mp3', '野外白天/一首.mp3', '城镇/town.mp3'],
                      'volume': .16, 'playback': {'dayStart': 6, 'fadeSeconds': 1.2}}
            settings.write_text(json.dumps(config), encoding='utf-8')
            receipt = merge(library, root / 'backup', [settings])
            self.assertEqual((receipt['sourceFiles'], receipt['uniqueTracks'], receipt['duplicatesRemoved']), (5, 4, 1))
            self.assertEqual({p.read_bytes() for p in (library / '野外').iterdir()}, {b'existing', b'shared', b'different', b'personal'})
            updated = json.loads(settings.read_text(encoding='utf-8'))
            self.assertEqual(updated['disabled'], ['野外/一首.mp3', '城镇/town.mp3'])
            self.assertEqual(updated['volume'], config['volume'])
            self.assertEqual(updated['playback'], config['playback'])
            for name, data in tracks.items():
                path = Path(name)
                target = root / 'backup/original-folders' / path if path.parts[0] in ('野外', '野外白天', '野外夜晚') else library / path
                self.assertEqual(target.read_bytes(), data)
            with self.assertRaisesRegex(RuntimeError, 'No legacy'):
                merge(library, root / 'another-backup')

    def test_validation_precedes_changes_and_failed_move_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / 'library'
            song = library / '野外白天/song.mp3'
            song.parent.mkdir(parents=True)
            song.write_bytes(b'original')
            settings = root / 'settings.json'
            settings.write_text('{invalid', encoding='utf-8')
            with self.assertRaises(ValueError):
                merge(library, root / 'invalid-settings', [settings])
            self.assertFalse((root / 'invalid-settings').exists())
            with self.assertRaisesRegex(RuntimeError, 'outside'):
                merge(library, library / 'backup')
            real_rename = os.rename

            def fail_install(source, target):
                if Path(source).name == 'incoming':
                    raise OSError('simulated file lock')
                return real_rename(source, target)

            with patch('merge_exploration.os.rename', side_effect=fail_install):
                with self.assertRaises(OSError):
                    merge(library, root / 'failed-move')
            self.assertEqual(song.read_bytes(), b'original')
            self.assertFalse((library / '野外').exists())


if __name__ == '__main__':
    unittest.main()
