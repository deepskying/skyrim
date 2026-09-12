"""Import this local SDLoadingScreens library without changing its source files.

Keep original FormIDs, conditions and display transforms. No plugin merging or
arbitrary ESP import is attempted. Pillow is used only to generate preview copies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import uuid
import zlib


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def records(data):
    p = 0
    while p < len(data):
        if len(data) - p < 24:
            raise ValueError('Short record header')
        sig, size = struct.unpack_from('<4sI', data, p)
        if sig == b'GRUP':
            if size < 24 or p + size > len(data):
                raise ValueError('Invalid group size')
            yield from records(data[p + 24:p + size])
            p += size
        else:
            if p + size + 24 > len(data):
                raise ValueError('Invalid record size')
            header = bytearray(data[p:p + 24])
            body = data[p + 24:p + 24 + size]
            flags = struct.unpack_from('<I', header, 8)[0]
            if flags & 0x40000:
                expected = struct.unpack_from('<I', body)[0]
                body = zlib.decompress(body[4:])
                if len(body) != expected:
                    raise ValueError('Compressed size mismatch')
                struct.pack_into('<I', header, 4, len(body))
                struct.pack_into('<I', header, 8, flags & ~0x40000)
            yield bytes(header) + body
            p += size + 24


def fields(record):
    p = 24
    while p < len(record):
        if len(record) - p < 6:
            raise ValueError('Short subrecord')
        sig, size = struct.unpack_from('<4sH', record, p)
        p += 6
        if sig == b'XXXX' or p + size > len(record):
            raise ValueError('Unsupported subrecord')
        yield sig, record[p:p + size]
        p += size


def safe_resource(source, relative):
    parts = relative.replace('\\', '/').split('/')
    if any(x in ('', '.', '..') or ':' in x for x in parts):
        raise ValueError('Unsafe resource path: ' + relative)
    path = source.joinpath(*parts)
    if not path.resolve().is_relative_to(source.resolve()) or path.is_symlink() or not path.is_file():
        raise ValueError('Missing or linked resource: ' + str(path))
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manager', type=Path, required=True)
    parser.add_argument('--pillow', type=Path, required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, str(args.pillow))
    from PIL import Image

    source = args.source.resolve()
    target = args.manager.resolve() / 'loading-backgrounds'
    empty_readme = '放入加载背景.txt'
    if target.exists() and any(p.name != empty_readme or not p.is_file() for p in target.iterdir()):
        raise ValueError('Refusing to overwrite an existing loading library')
    stage = target.with_name('.loading-import-' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    system = stage / '_system'
    system.mkdir()
    plugin = source / 'SDLoadingScreens.esp'
    original_hash = digest(plugin)
    parsed = list(records(plugin.read_bytes()))
    if any(r[:4] not in (b'TES4', b'STAT', b'LSCR') for r in parsed):
        raise ValueError('Source contains unsupported record types')
    headers = [r for r in parsed if r[:4] == b'TES4']
    assert len(headers) == 1
    assert [v for k, v in fields(headers[0]) if k == b'MAST'] == [b'Skyrim.esm\0']
    (system / 'header.bin').write_bytes(headers[0])
    # This hash also permits a byte-identical previous copy on first deployment.
    (system / 'published-hashes.txt').write_text(original_hash + '\n', encoding='ascii')
    stats = {struct.unpack_from('<I', r, 12)[0]: r for r in parsed if r[:4] == b'STAT'}
    screens = [r for r in parsed if r[:4] == b'LSCR']
    assert len(stats) == len(screens) == 285
    hashes, used, report = {}, set(), []

    def copy_resources(folder, relatives):
        assets = []
        for relative in sorted(set(relatives)):
            source_file = safe_resource(source, relative)
            key = source_file.relative_to(source).as_posix().lower()
            used.add(key)
            if key not in hashes:
                hashes[key] = digest(source_file)
            dest = folder / 'Data' / relative.replace('\\', '/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest)
            if digest(dest) != hashes[key]:
                raise ValueError('Copied asset hash mismatch')
            assets.append(dict(path=relative, sha256=hashes[key], bytes=dest.stat().st_size))
        write_json(folder / 'assets.json', assets)
        write_json(folder / 'source-manifest.json', dict(source=str(source), bytes=sum(a['bytes'] for a in assets)))
        return assets

    def preview(folder, texture):
        with Image.open(safe_resource(source, texture)) as original:
            dimensions = original.size
            large = original.convert('RGB')
            large.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            large.save(folder / 'preview-large.jpg', quality=92)
            large.thumbnail((640, 640), Image.Resampling.LANCZOS)
            large.save(folder / 'preview.jpg', quality=88)
        return [dict(path='preview.jpg', resource=texture, dimensions=dimensions)]

    for index, screen in enumerate(sorted(screens, key=lambda r: struct.unpack_from('<I', r, 12)[0]), 1):
        values = dict(fields(screen))
        stat = stats[struct.unpack('<I', values[b'NNAM'])[0]]
        stat_values = dict(fields(stat))
        model = 'meshes/' + stat_values[b'MODL'].rstrip(b'\0').decode('ascii').replace('\\', '/')
        model_file = safe_resource(source, model)
        refs = sorted(set(v.decode('ascii').replace('\\', '/') for v in re.findall(rb'textures[\\/][^\x00\r\n]+?\.dds', model_file.read_bytes(), re.I)))
        pictures = [r for r in refs if Path(r).name.lower() != 'n.dds']
        if len(pictures) != 1:
            raise ValueError('Unexpected diffuse texture mapping: ' + model)
        form = struct.unpack_from('<I', screen, 12)[0]
        assert form >> 24 == 1 and struct.unpack_from('<I', stat, 12)[0] >> 24 == 1
        name = '加载画面 ' + Path(pictures[0]).stem
        folder = stage / ('%03d_%s_%08X' % (index, Path(model).stem, form))
        folder.mkdir()
        (folder / 'records.bin').write_bytes(stat + screen)
        assets = copy_resources(folder, [model] + refs)
        write_json(folder / 'theme.json', dict(name=name, enabled=True, kind='loading', formId='%08X' % form,
                   description=values.get(b'DESC', b'').rstrip(b'\0').decode('utf-8'), previews=preview(folder, pictures[0])))
        report.append(dict(folder=folder.name, formId='%08X' % form, model=model, picture=pictures[0], assets=len(assets)))
        if index % 40 == 0:
            print('Imported %d / %d loading screens' % (index, len(screens)), flush=True)

    unused = [p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in ('.dds', '.nif') and p.relative_to(source).as_posix().lower() not in used]
    for index, file in enumerate(unused, 1):
        folder = stage / '_待确认' / ('unused_%02d_%s' % (index, file.stem))
        folder.mkdir(parents=True)
        relative = file.relative_to(source).as_posix()
        copy_resources(folder, [relative])
        write_json(folder / 'theme.json', dict(name='未引用资源 ' + file.name, enabled=False,
            issues=['原插件的加载模型未引用此资源，保留供筛选'], previews=preview(folder, relative) if file.suffix.lower() == '.dds' else []))
    write_json(system / 'migration.json', dict(source=str(source), sourcePluginSHA256=original_hash,
        active=len(screens), unused=len(unused), themes=report, sourceHashes=hashes))
    assert digest(plugin) == original_hash
    if target.exists():
        # Only the package's empty-library README may exist here. Never remove a populated library.
        if not target.resolve().is_relative_to(args.manager.resolve()) or any(p.name != empty_readme or not p.is_file() for p in target.iterdir()):
            raise ValueError('Loading library changed during import')
        if (target / empty_readme).exists():
            (target / empty_readme).rename(stage / empty_readme)
        target.rmdir()
    stage.rename(target)
    print(json.dumps(dict(library=str(target), active=len(screens), unused=len(unused)), ensure_ascii=False))


if __name__ == '__main__':
    main()
