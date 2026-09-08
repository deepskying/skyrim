"""Read-only DCS import. Originals are never renamed, deleted or modified."""
import argparse
import hashlib
import json
import shutil
import subprocess
from contextlib import nullcontext
from pathlib import Path

CATEGORIES = {
    'explore_day': '野外白天', 'explore_night': '野外夜晚', 'town': '城镇',
    'tavern': '酒馆', 'home': '住宅', 'dungeon': '地牢', 'combat': '普通战斗',
    'dragon': '龙战', 'general': '通用',
}
# Nine categories: day and night are separate; "general" is the only fallback.

def categories_for(path):
    parts = {part.upper() for part in path.parts[:-1]}
    name = path.stem.upper()
    if name.endswith('END') or 'STINGERS' in parts or 'FINALE' in name:
        return []
    if name.startswith('COMBATDRAGON') or 'DRAGON' in name and name.startswith('COMBAT'):
        return ['dragon']
    if name.startswith('COMBAT'):
        return ['combat']
    if name.startswith('TAVERN') or 'TAVERN' in parts:
        return ['tavern']
    if name.startswith('DUNGEON') or 'DUNGEON' in parts:
        return ['dungeon']
    if name.startswith('TOWN') or 'TOWN' in parts or 'CASTLE' in parts:
        return ['town']
    if name.startswith('EXPLORE') or 'EXPLORE' in parts:
        if 'NIGHT' in parts:
            return ['explore_night']
        if parts.intersection({'DAY', 'DAWN', 'DUSK'}):
            return ['explore_day']
        return ['explore_day', 'explore_night']
    if 'HOME' in parts:
        return ['home']
    return ['general']

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def mislabeled_audio(path):
    with path.open('rb') as stream:
        header = stream.read(12)
    return path.suffix.lower() == '.mp3' and (header[4:8] == b'ftyp' or header[:4] == b'OggS')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mods', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--converter-dir', required=True, type=Path)
    args = parser.parse_args()
    source_root, output = args.mods.resolve(), args.output.resolve()
    if output == source_root or source_root in output.parents:
        raise SystemExit('Output must be separate from the source MO2 mods directory.')
    output.mkdir(parents=True, exist_ok=True)
    for folder in CATEGORIES.values():
        (output / 'Data' / 'Music' / 'MusicManager' / folder).mkdir(parents=True, exist_ok=True)
    sources = sorted(source_root.glob('*资源-DCS*'))
    if len(sources) != 4:
        raise SystemExit(f'Expected four DCS resource mods, found {len(sources)}.')
    report = {'sources': [str(s) for s in sources], 'entries': [], 'errors': [], 'counts': {k: 0 for k in CATEGORIES}}
    seen = {}
    ranks = {'.mp3': 0, '.flac': 1, '.wav': 2, '.xwm': 3}
    groups = {}
    for mod in sources:
        for file in sorted(mod.rglob('*')):
            if file.is_file() and file.suffix.lower() in ranks:
                groups.setdefault(str(file.with_suffix('')).casefold(), []).append(file)
    print(f'Importing {len(groups)} source slots', flush=True)
    # Work paths are ASCII to support the old bundled Microsoft audio converter.
    scratch_root = output / '.scratch'
    scratch_root.mkdir(exist_ok=True)
    with nullcontext(scratch_root) as temporary:
        scratch = Path(temporary)
        for index, variants in enumerate(groups.values()):
            source = min(variants, key=lambda p: ranks[p.suffix.lower()])
            relative = source.relative_to(source_root)
            entry = {'source': str(relative), 'variants': [str(p.relative_to(source_root)) for p in variants], 'destinations': []}
            report['entries'].append(entry)
            try:
                content_hash = digest(source)
                categories = categories_for(relative)
                normalize = mislabeled_audio(source)
                extension = '.flac' if source.suffix.lower() == '.xwm' or normalize else source.suffix.lower()
                converted = source
                targets = categories or ['extras']
                missing = [c for c in targets if (c, content_hash) not in seen]
                filename = f'{source.stem} [{content_hash[:12]}]{extension}'
                if (source.suffix.lower() == '.xwm' or normalize) and missing:
                    cached = output / '.conversion-cache' / f'{content_hash}.flac'
                    cached.parent.mkdir(exist_ok=True)
                    if not cached.exists():
                        shutil.copy2(source, scratch / 'input.audio')
                        for stale in ('output.wav', 'output.flac'):
                            (scratch / stale).unlink(missing_ok=True)
                        input_audio = 'input.audio'
                        if not normalize:
                            subprocess.run([str(args.converter_dir / 'xWMAEncode.exe'), input_audio, 'output.wav'], cwd=scratch, capture_output=True, check=True, timeout=120)
                            input_audio = 'output.wav'
                        subprocess.run([str(args.converter_dir / 'ffmpeg.exe'), '-y', '-i', input_audio, '-vn', '-acodec', 'flac', 'output.flac'], cwd=scratch, capture_output=True, check=True, timeout=120)
                        if not (scratch / 'output.flac').is_file() or (scratch / 'output.flac').stat().st_size == 0:
                            raise RuntimeError('Converter produced no audio')
                        shutil.move(scratch / 'output.flac', cached)
                    converted = cached
                for category in targets:
                    key = (category, content_hash)
                    if key in seen:
                        entry['destinations'].append({'path': seen[key], 'duplicate': True})
                        continue
                    directory = output / 'Data' / 'Music' / 'MusicManager' / CATEGORIES[category] if category != 'extras' else output / '待整理短音'
                    directory.mkdir(parents=True, exist_ok=True)
                    destination = directory / filename
                    if not destination.exists():
                        shutil.copy2(converted, destination)
                    # Earlier imports may contain the mislabeled copy. Preserve it
                    # outside the scanned library; never touch the MO2 originals.
                    if normalize:
                        previous = destination.with_suffix(source.suffix.lower()).resolve()
                        if output not in previous.parents:
                            raise RuntimeError('Import path escaped output root')
                        if previous.exists():
                            archive = output / '待整理原格式' / CATEGORIES.get(category, '短音')
                            archive.mkdir(parents=True, exist_ok=True)
                            archived = (archive / previous.name).resolve()
                            if output not in archived.parents:
                                raise RuntimeError('Archive path escaped output root')
                            if not archived.exists():
                                shutil.move(previous, archived)
                        entry['note'] = 'MP3 extension contained M4A/Ogg; normalized the imported copy to FLAC.'
                    seen[key] = str(destination.relative_to(output))
                    entry['destinations'].append({'path': seen[key], 'duplicate': False})
                    if category != 'extras':
                        report['counts'][category] += 1
                if not categories:
                    entry['note'] = 'Short ending/stinger retained separately, not added to playlists.'
            except Exception as error:
                entry['error'] = str(error)
                report['errors'].append({'source': str(relative), 'error': str(error)})
            if index % 25 == 0:
                print(f'{index + 1}/{len(groups)} slots; {len(report["errors"])} errors', flush=True)
                (output / 'migration-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'migration-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'counts': report['counts'], 'errors': len(report['errors'])}, ensure_ascii=False), flush=True)
    return bool(report['errors'])

if __name__ == '__main__':
    raise SystemExit(main())
