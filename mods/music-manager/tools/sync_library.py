"""Install a checked migration; archive only unchanged files owned by the old manifest."""
import argparse
import json
import shutil
from pathlib import Path
from migrate_dcs_complete import digest

PREFIX = Path('Data/Music/MusicManager')


def inside(root, relative):
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise RuntimeError(f'Path escapes target root: {relative}')
    return result


def library_paths(report):
    result = set()
    for entry in report['entries']:
        for destination in entry['destinations']:
            path = Path(destination['path'])
            if path.is_relative_to(PREFIX):
                result.add(path.relative_to(PREFIX))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--import-root', required=True, type=Path)
    p.add_argument('--previous-root', required=True, type=Path)
    p.add_argument('--mod', required=True, type=Path)
    p.add_argument('--backup', required=True, type=Path)
    p.add_argument('--settings', action='append', default=[], type=Path)
    args = p.parse_args()
    new = json.loads((args.import_root / 'migration-report.json').read_text(encoding='utf-8'))
    old = json.loads((args.previous_root / 'migration-report.json').read_text(encoding='utf-8'))
    if new['errors'] or old['errors']:
        raise RuntimeError('Migration contains errors; not installing')
    root = (args.mod / 'Music/MusicManager').resolve()
    if not root.is_dir() or args.backup.exists():
        raise RuntimeError('Requires an existing library and a fresh backup directory')
    incoming = (args.import_root / PREFIX).resolve()
    previous = (args.previous_root / PREFIX).resolve()
    new_paths, old_paths = library_paths(new), library_paths(old)
    # Inspect every conflict before mutating the installed library.
    hashes, retirement, preserved = {}, [], []
    for relative in sorted(new_paths):
        source, target = inside(incoming, relative), inside(root, relative)
        hashes[relative] = digest(source)
        if target.exists() and digest(target) != hashes[relative]:
            raise RuntimeError(f'Installed file differs; refusing to overwrite: {target}')
    for relative in sorted(old_paths - new_paths):
        target, original = inside(root, relative), inside(previous, relative)
        if target.exists():
            if original.is_file() and digest(target) == digest(original):
                retirement.append(relative)
            else:
                preserved.append(str(relative))
    args.backup.mkdir(parents=True)
    added = 0
    for relative in sorted(new_paths):
        target = inside(root, relative)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inside(incoming, relative), target)
            added += 1
        if digest(target) != hashes[relative]:
            raise RuntimeError(f'Copy verification failed: {target}')
    # Only retire old generated copies after every replacement has verified.
    for relative in retirement:
        target = inside(args.backup / 'retired-music', relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(inside(root, relative), target)
    # Preserve per-song disabled settings when a FLAC becomes an MP3.
    new_by_source = {e['source']: e for e in new['entries']}
    remap = {}
    for entry in old['entries']:
        updated = new_by_source.get(entry['source'])
        if not updated:
            continue
        choices = [Path(d['path']).relative_to(PREFIX) for d in updated['destinations'] if Path(d['path']).is_relative_to(PREFIX)]
        for destination in entry['destinations']:
            prior = Path(destination['path'])
            if not prior.is_relative_to(PREFIX):
                continue
            prior = prior.relative_to(PREFIX)
            match = next((item for item in choices if item.parent == prior.parent), None)
            if match is not None and prior != match:
                remap[prior.as_posix()] = match.as_posix()
    settings_changed = []
    for index, path in enumerate(args.settings):
        if not path.is_file():
            continue
        content = json.loads(path.read_text(encoding='utf-8-sig'))
        updated = [remap.get(item, item) for item in content.get('disabled', [])]
        if updated != content.get('disabled', []):
            shutil.copy2(path, args.backup / f'settings-{index}.json')
            content['disabled'] = updated
            temporary = path.with_name(path.name + '.migration.tmp')
            temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(path)
            settings_changed.append(str(path))
    receipt = {'added': added, 'retiredToBackup': len(retirement),
               'preservedModifiedFiles': preserved, 'verifiedTracks': len(new_paths),
               'settingsUpdated': settings_changed, 'backup': str(args.backup.resolve())}
    report_path = args.mod / 'migration-report.json'
    if report_path.exists():
        shutil.copy2(report_path, args.backup / 'previous-migration-report.json')
    shutil.copy2(args.import_root / 'migration-report.json', report_path)
    (args.backup / 'sync-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
