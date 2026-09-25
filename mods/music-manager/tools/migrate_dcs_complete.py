"""Import DCS core and resource music without changing any source files."""
import argparse
import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CATEGORIES = {
    'explore': '野外', 'town': '城镇',
    'tavern': '酒馆', 'home': '住宅', 'castle': '城堡', 'cemetery': '墓地',
    'temple': '神殿', 'dungeon': '地牢', 'combat': '普通战斗',
    'dragon': '龙战', 'general': '通用',
}
RANKS = {'.mp3': 0, '.flac': 1, '.wav': 2, '.xwm': 3}


def categories_for(path):
    parts = {part.upper() for part in path.parts[:-1]}
    name = path.stem.upper()
    if name.endswith('END') or name.startswith('SILENT END') or 'STINGERS' in parts or 'FINALE' in name:
        return []
    if name.startswith('COMBATDRAGON') or 'DRAGON' in name and name.startswith('COMBAT'):
        return ['dragon']
    if name.startswith('COMBAT'):
        return ['combat']
    # A directory is authoritative even when the song is named ExploreXX.
    for directory, category in [('CEMETERY', 'cemetery'), ('TEMPLE', 'temple'),
                                ('CASTLE', 'castle'), ('TAVERN', 'tavern'),
                                ('HOME', 'home'), ('DUNGEON', 'dungeon'), ('TOWN', 'town')]:
        if directory in parts or name.startswith(directory):
            return [category]
    if name.startswith('EXPLORE') or 'EXPLORE' in parts:
        return ['explore']
    return ['general']


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mislabeled_audio(path):
    with path.open('rb') as stream:
        header = stream.read(12)
    return path.suffix.lower() == '.mp3' and (header[4:8] == b'ftyp' or header[:4] == b'OggS')


def discover_sources(root):
    return sorted(p for p in root.iterdir() if p.is_dir() and
                  ('资源-DCS' in p.name or 'DCS-Dynamic Customizable Soundtrack' in p.name))


def collect_groups(sources):
    groups = {}
    for mod in sources:
        for file in sorted(mod.rglob('*')):
            if file.is_file() and file.suffix.lower() in RANKS:
                groups.setdefault(str(file.with_suffix('')).casefold(), []).append(file)
    return list(groups.values())


def run_converter(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=180)
    if result.returncode:
        detail = (result.stderr or result.stdout).decode(errors='replace')[-1800:]
        raise RuntimeError(f'{Path(command[0]).name}: {detail}')


def convert(source, content_hash, args):
    extension = args.convert_to
    cached = args.output / '.conversion-cache' / f'{content_hash}.{extension}'
    if cached.is_file() and cached.stat().st_size:
        return cached
    cached.parent.mkdir(exist_ok=True)
    scratch = args.output / '.scratch' / content_hash
    scratch.mkdir(parents=True, exist_ok=True)
    # Keep the old Microsoft converter's command-line filenames in ASCII.
    source_audio = scratch / 'input.audio'
    prior = args.decode_cache / f'{content_hash}.flac' if args.decode_cache else None
    if prior and prior.is_file():
        shutil.copy2(prior, source_audio)
    else:
        shutil.copy2(source, source_audio)
        if source.suffix.lower() == '.xwm':
            run_converter([str(args.converter_dir / 'xWMAEncode.exe'), 'input.audio', 'output.wav'], scratch)
            source_audio = scratch / 'output.wav'
    codec = ['-acodec', 'libmp3lame', '-q:a', '2'] if extension == 'mp3' else ['-acodec', 'flac']
    output_name = f'output.{extension}'
    run_converter([str(args.converter_dir / 'ffmpeg.exe'), '-y', '-i', source_audio.name,
                   '-vn', '-map_metadata', '-1', *codec, output_name], scratch)
    converted = scratch / output_name
    if not converted.is_file() or not converted.stat().st_size:
        raise RuntimeError('Converter produced no audio')
    # Verify the complete converted stream before admitting it to the library.
    verify = [str(args.converter_dir / 'ffmpeg.exe'), '-v', 'error', '-xerror',
              '-i', output_name, '-f', 'null', '-']
    try:
        run_converter(verify, scratch)
    except RuntimeError:
        if extension != 'mp3':
            raise
        # The bundled 2012 encoder/prober fails on some VBR streams. Retry a
        # standard 44.1 kHz stereo 320 kbps MP3, then require a clean full decode.
        run_converter([str(args.converter_dir / 'ffmpeg.exe'), '-y', '-i', source_audio.name,
                       '-vn', '-acodec', 'libmp3lame', '-b:a', '320k', '-ar', '44100',
                       '-ac', '2', output_name], scratch)
        run_converter(verify, scratch)
        cached.with_suffix('.cbr').write_text('320 kbps retry passed full decode', encoding='utf-8')
    shutil.copy2(converted, cached)
    for workfile in scratch.iterdir():
        if workfile.is_file():
            workfile.unlink()
    scratch.rmdir()
    return cached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mods', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--converter-dir', required=True, type=Path)
    parser.add_argument('--convert-to', choices=['mp3', 'flac'], default='mp3')
    parser.add_argument('--decode-cache', type=Path, help='Reuse the previous lossless XWM decode cache')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    source_root, args.output = args.mods.resolve(), args.output.resolve()
    args.converter_dir = args.converter_dir.resolve()
    if args.decode_cache:
        args.decode_cache = args.decode_cache.resolve()
    if args.output == source_root or source_root in args.output.parents:
        parser.error('Output must be separate from the source MO2 mods directory.')
    if not 1 <= args.workers <= 8:
        parser.error('workers must be between 1 and 8')
    sources = discover_sources(source_root)
    if not sources:
        parser.error('No DCS core or resource directories found')
    args.output.mkdir(parents=True, exist_ok=True)
    for folder in CATEGORIES.values():
        (args.output / 'Data' / 'Music' / 'MusicManager' / folder).mkdir(parents=True, exist_ok=True)
    groups = collect_groups(sources)
    report = {'sources': [str(s) for s in sources], 'format': args.convert_to,
              'sourceFiles': sum(map(len, groups)), 'entries': [], 'errors': [],
              'counts': {k: 0 for k in CATEGORIES}}
    conversions, prepared, paths, failures = {}, [], {}, {}
    print(f'Found {len(sources)} DCS directories, {report["sourceFiles"]} audio files, {len(groups)} slots', flush=True)
    for variants in groups:
        source = min(variants, key=lambda p: RANKS[p.suffix.lower()])
        entry = {'source': str(source.relative_to(source_root)),
                 'variants': [str(p.relative_to(source_root)) for p in variants], 'destinations': []}
        report['entries'].append(entry)
        try:
            content_hash = digest(source)
            entry['sourceSha256'] = content_hash
            normalize = mislabeled_audio(source)
            needs_conversion = source.suffix.lower() == '.xwm' or normalize
            extension = '.' + args.convert_to if needs_conversion else source.suffix.lower()
            categories = categories_for(source.relative_to(source_root))
            prepared.append((source, content_hash, categories, extension, entry))
            if needs_conversion:
                conversions.setdefault(content_hash, source)
                entry['conversion'] = f'{source.suffix.lower()} -> {extension}'
                if normalize:
                    entry['note'] = 'MP3 extension contained M4A/Ogg; converted the imported copy.'
            else:
                paths[content_hash] = source
        except Exception as error:
            entry['error'] = str(error)
            report['errors'].append({'source': entry['source'], 'error': str(error)})
    print(f'Converting/checking {len(conversions)} unique files to {args.convert_to}', flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks = {pool.submit(convert, source, h, args): h for h, source in conversions.items()}
        for count, task in enumerate(as_completed(tasks), 1):
            h = tasks[task]
            try:
                paths[h] = task.result()
            except Exception as error:
                failures[h] = str(error)
                print(f'Conversion failed: {conversions[h]}: {error}', flush=True)
            if count % 25 == 0 or count == len(tasks):
                print(f'{count}/{len(tasks)} conversions, {len(failures)} failures', flush=True)
    seen = {}
    for source, h, categories, extension, entry in prepared:
        try:
            if h in failures:
                raise RuntimeError(failures[h])
            if (args.output / '.conversion-cache' / f'{h}.cbr').exists():
                entry['encoding'] = 'MP3 320 kbps CBR after VBR validation failure'
            for category in categories or ['extras']:
                key = (category, h)
                if key in seen:
                    entry['destinations'].append({'path': seen[key], 'duplicate': True})
                    continue
                directory = args.output / 'Data' / 'Music' / 'MusicManager' / CATEGORIES[category] if category != 'extras' else args.output / '待整理短音'
                directory.mkdir(parents=True, exist_ok=True)
                destination = directory / f'{source.stem} [{h[:12]}]{extension}'
                if destination.exists() and digest(destination) != digest(paths[h]):
                    raise RuntimeError(f'Existing destination differs; refusing to overwrite: {destination}')
                if not destination.exists():
                    shutil.copy2(paths[h], destination)
                seen[key] = str(destination.relative_to(args.output))
                entry['destinations'].append({'path': seen[key], 'duplicate': False})
                if category != 'extras':
                    report['counts'][category] += 1
            if not categories:
                entry['note'] = 'Short ending/stinger retained separately, not added to playlists.'
        except Exception as error:
            entry['error'] = str(error)
            report['errors'].append({'source': entry['source'], 'error': str(error)})
    (args.output / 'migration-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'counts': report['counts'], 'errors': len(report['errors'])}, ensure_ascii=False), flush=True)
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
