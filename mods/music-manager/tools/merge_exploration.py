"""Merge the installed day/night library, preserving originals in a fresh backup.

Run with Skyrim closed. Only exact file-content duplicates are collapsed. Deleted
archives and other categories are never imported. No original music is deleted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

FOLDERS = ('野外', '野外白天', '野外夜晚')
AUDIO = {'.mp3', '.flac', '.wav'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(root, path):
    # Check each component, including the root, before following any links.
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise RuntimeError(f'Links/reparse points are not supported: {item}')
    if not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError(f'Path escapes its intended root: {path}')
    return path


def merge(library, backup, settings=()):
    library, backup = Path(library).absolute(), Path(backup).absolute()
    checked(library, library)
    checked(backup, backup)
    if not library.is_dir() or backup.exists():
        raise RuntimeError('Requires an existing library and a fresh backup directory')
    if backup.is_relative_to(library) or library.is_relative_to(backup):
        raise RuntimeError('Backup must be outside the library')
    existing = [checked(library, library / name) for name in FOLDERS if (library / name).exists()]
    if not any(path.name != '野外' for path in existing):
        raise RuntimeError('No legacy day/night folders to merge (already merged or wrong library)')
    # Inspect the entire source trees so even non-audio links cannot be moved.
    files, hashes, remap, chosen, names = [], {}, {}, {}, set()
    for folder in existing:
        if not folder.is_dir():
            raise RuntimeError(f'Not a directory: {folder}')
        for path in sorted(folder.rglob('*')):
            checked(library, path)
            if path.is_file():
                files.append(path)
                hashes[path] = digest(path)
                if path.suffix.lower() not in AUDIO:
                    continue
                content = hashes[path]
                if content not in chosen:
                    name = path.name
                    suffix = 0
                    while name.casefold() in names:
                        suffix += 1
                        name = f'{path.stem} [{content[:12]}-{suffix}]{path.suffix}'
                    names.add(name.casefold())
                    chosen[content] = (path, name)
                remap[path.relative_to(library).as_posix()] = '野外/' + chosen[content][1]
    preferences = []
    for path in dict.fromkeys(Path(p).absolute() for p in settings):
        if not path.exists():
            continue
        checked(path.parent, path)
        original = path.read_bytes()
        content = json.loads(original.decode('utf-8-sig'))
        disabled = content.get('disabled', [])
        if not isinstance(disabled, list) or any(not isinstance(item, str) for item in disabled):
            raise RuntimeError(f'Invalid disabled list: {path}')
        # If either copy was disabled, keep the combined song disabled.
        updated = list(dict.fromkeys(remap.get(item, item) for item in disabled))
        if updated != disabled:
            content['disabled'] = updated
            preferences.append((path, original, json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')))
    backup.mkdir(parents=True)
    incoming = checked(backup, backup / 'incoming')
    incoming.mkdir()
    for content, (source, name) in chosen.items():
        target = checked(backup, incoming / name)
        shutil.copy2(source, target)
        if digest(target) != content:
            raise RuntimeError(f'Copy verification failed; originals unchanged: {source}')
    # Detect concurrent user edits before retiring any source folder.
    for folder in existing:
        current = [checked(library, p) for p in sorted(folder.rglob('*')) if p.is_file()]
        if set(current) != {p for p in files if p.is_relative_to(folder)}:
            raise RuntimeError('Library changed during merge; originals unchanged')
    if any(digest(path) != content for path, content in hashes.items()):
        raise RuntimeError('Music changed during merge; originals unchanged')
    for index, (path, original, _) in enumerate(preferences):
        if path.read_bytes() != original:
            raise RuntimeError('Settings changed during merge; originals unchanged')
        (backup / f'settings-{index}.json').write_bytes(original)
    retired = checked(backup, backup / 'original-folders')
    retired.mkdir()
    moved, saved = [], []
    target = checked(library, library / '野外')
    installed = False
    try:
        for source in existing:
            destination = checked(backup, retired / source.name)
            # Explicit absolute source/destination checks before directory moves.
            os.rename(checked(library, source), destination)
            moved.append((source, destination))
        os.rename(incoming, target)
        installed = True
        for path, original, updated in preferences:
            temporary = path.with_name(path.name + '.explore-merge.tmp')
            with temporary.open('xb') as stream:
                stream.write(updated)
            os.replace(temporary, path)
            saved.append((path, original))
    except Exception:
        for path, original in saved:
            path.write_bytes(original)
        if installed:
            os.rename(checked(library, target), checked(backup, incoming))
        for source, destination in reversed(moved):
            os.rename(checked(backup, destination), checked(library, source))
        raise
    receipt = {'sourceFiles': len(remap), 'uniqueTracks': len(chosen),
               'duplicatesRemoved': len(remap) - len(chosen), 'library': str(library),
               'backup': str(backup), 'settingsUpdated': [str(p) for p, _, _ in preferences],
               'remap': remap}
    (backup / 'merge-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--settings', type=Path, action='append', default=[])
    args = parser.parse_args()
    receipt = merge(args.library, args.backup, args.settings)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'remap'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
