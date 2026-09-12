"""Copy-only recovery of local main-menu themes; preserves source provenance.

Inventory comes from rg --files. BSA support: Skyrim versions 104/105, zlib/LZ4.
Run inspect first, then plan/apply; destination is never used as a source.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import zlib
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'reference/bow-tools/python-libs'))
sys.stdout.reconfigure(encoding='utf-8')

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def key(value):
    result = str(value).replace('\\', '/').lower().strip('/')
    if ':' in result or '..' in PurePosixPath(result).parts:
        raise ValueError('Unsafe resource path: ' + result)
    return result

class BSA:
    def __init__(self, path):
        self.path = Path(path)
        self.files = {}
        with self.path.open('rb') as f:
            magic, self.version, offset, self.flags, nf, count, _, names_length, _ = struct.unpack('<4s8I', f.read(36))
            if magic != b'BSA\0' or self.version not in (104, 105) or self.flags & 3 != 3:
                raise ValueError(f'Unsupported BSA: v{self.version}, flags={self.flags}')
            if nf > 1000000 or count > 5000000 or names_length > 512 * 1024 * 1024:
                raise ValueError('Unreasonable BSA index size')
            f.seek(offset)
            folders = [struct.unpack('<QIIQ' if self.version == 105 else '<QII', f.read(24 if self.version == 105 else 16)) for _ in range(nf)]
            pending = []
            for folder in folders:
                n, position = folder[1], folder[-1]
                f.seek(position - names_length)
                length = f.read(1)[0]
                name = f.read(length).rstrip(b'\0').decode('utf-8', errors='replace')
                for _ in range(n):
                    _, size, position = struct.unpack('<QII', f.read(16))
                    if position + (size & 0x3fffffff) > self.path.stat().st_size:
                        raise ValueError('BSA resource outside archive bounds')
                    pending.append((name, size, position))
            names = f.read(names_length).split(b'\0')
            if len(pending) != count or len(names) < count:
                raise ValueError('BSA filename count mismatch')
            for (folder, size, position), name in zip(pending, names):
                name = name.decode('utf-8', errors='replace')
                resource = key(folder + '/' + name)
                if resource in self.files:
                    raise ValueError('Duplicate archive resource: ' + resource)
                self.files[resource] = (size, position)

    def read(self, resource):
        size, position = self.files[resource]
        with self.path.open('rb') as f:
            f.seek(position)
            blob = f.read(size & 0x3fffffff)
        if self.flags & 0x100:
            blob = blob[1 + blob[0]:]
        if bool(self.flags & 4) ^ bool(size & 0x40000000):
            expected = struct.unpack_from('<I', blob)[0]
            if expected > 1024 * 1024 * 1024:
                raise ValueError('Resource exceeds 1 GiB')
            if self.version == 105:
                from lz4.frame import decompress
                blob = decompress(blob[4:])
            else:
                blob = zlib.decompress(blob[4:])
            if len(blob) != expected:
                raise ValueError('Decompressed resource size mismatch')
        return blob

def resource_root(path):
    parts = path.parts
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].lower() in ('textures', 'meshes', 'music'):
            return Path(*parts[:i]), key('/'.join(parts[i:]))
    return None, None

def texture_refs(blob):
    refs = set()
    for match in re.finditer(rb'[^\x00-\x1f\x7f]{1,512}\.(?:dds|tga)', blob, flags=re.I):
        value = match.group().decode('utf-8', errors='replace').strip()
        normalized = value.replace('\\', '/').lower()
        at = normalized.find('textures/')
        normalized = key(normalized[at:] if at >= 0 else 'textures/' + normalized)
        refs.add(normalized)
    return sorted(refs)

def anchor(resource):
    return resource.endswith(('meshes/interface/logo/logo.nif', 'meshes/interface/logo/logo01ae.nif')) or (
        '/textures/' in '/' + resource and 'mainmenu' in PurePosixPath(resource).name and resource.endswith('.dds'))

def inventory(args):
    paths = [Path(p) for p in args.inventory.read_text(encoding='utf-8-sig').splitlines()]
    archives, errors = {}, []
    loose = []
    bsa_hits = []
    for path in paths:
        if args.destination == path or args.destination in path.parents:
            continue
        if path.suffix.lower() == '.bsa':
            try:
                bsa = BSA(path)
                archives[str(path)] = bsa
                hits = [k for k in bsa.files if anchor(k)]
                if hits:
                    bsa_hits.append({'archive': str(path), 'version': bsa.version, 'files': hits})
            except Exception as exc:
                errors.append({'archive': str(path), 'error': str(exc)})
        else:
            root, relative = resource_root(path)
            if root and anchor(relative):
                loose.append({'root': str(root), 'resource': relative, 'file': str(path)})
    broad = []
    for path, archive in archives.items():
        hits = [k for k in archive.files if k.endswith(('.dds', '.nif', '.png', '.jpg', '.swf')) and
                re.search(r'(main.?menu|wallpaper|splash|interface/.+background)', k, re.I)]
        if hits:
            broad.append({'archive': path, 'files': hits})
    report = {'archives_scanned': len(archives), 'archive_errors': errors, 'archive_hits': bsa_hits, 'broad_archive_hits': broad, 'loose_anchors': loose}
    dump(args.report / 'inspection.json', report)
    print(json.dumps({'archives_scanned': len(archives), 'archive_errors': len(errors), 'archive_hits': len(bsa_hits),
                      'broad_archive_hit_count': len(broad), 'loose_roots': len({x['root'].lower() for x in loose}), 'loose_anchors': len(loose)}, ensure_ascii=False, indent=2))
    return archives, loose

class Sources:
    def __init__(self, args, archives):
        self.archives = archives
        self.cache = {}
        game = args.game
        mo2 = game / 'MO2'
        lines = (mo2 / 'profiles' / args.profile / 'modlist.txt').read_text(encoding='utf-8-sig').splitlines()
        self.providers = [mo2 / 'overwrite'] + [mo2 / 'mods' / line[1:] for line in lines if line.startswith('+')]
        self.providers = [p for p in self.providers if p != args.destination] + [game / 'SkyrimSE/Data']
        self.by_provider = {}
        for archive in archives.values():
            self.by_provider.setdefault(str(archive.path.parent).lower(), []).append(archive)

    def resolve(self, root, relative, fallback=False):
        relative = key(relative)
        providers = [root] + (self.providers if fallback else [])
        # Loose files always take priority over archives within the chosen scope.
        local = root / relative
        if local.is_file():
            return {'kind': 'loose', 'path': str(local)}
        for archive in self.by_provider.get(str(root).lower(), []):
            if relative in archive.files:
                return {'kind': 'bsa', 'path': str(archive.path), 'key': relative}
        if fallback:
            for provider in providers[1:]:
                local = provider / relative
                if local.is_file():
                    return {'kind': 'loose', 'path': str(local), 'fallback': True}
            for provider in providers[1:]:
                for archive in self.by_provider.get(str(provider).lower(), []):
                    if relative in archive.files:
                        return {'kind': 'bsa', 'path': str(archive.path), 'key': relative, 'fallback': True}
        return None

    def read(self, source):
        path = Path(source['path'])
        if path.is_symlink() or path.is_junction():
            raise ValueError('Linked source is not supported')
        return path.read_bytes() if source['kind'] == 'loose' else self.archives[str(path)].read(source['key'])

    def describe(self, source):
        identity = (source['path'].lower(), source.get('key'))
        if identity not in self.cache:
            blob = self.read(source)
            self.cache[identity] = {'size': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
        return {**source, **self.cache[identity]}

def header_issues(relative, blob):
    if relative.endswith('.dds'):
        if len(blob) <= 128 or blob[:4] != b'DDS ' or struct.unpack_from('<I', blob, 4)[0] != 124:
            return ['无效 DDS 文件头: ' + relative]
        height, width = struct.unpack_from('<II', blob, 12)
        if not 0 < width <= 16384 or not 0 < height <= 16384:
            return ['纹理尺寸超出模组范围: ' + relative]
    elif relative.endswith('.nif'):
        if not blob.startswith(b'Gamebryo File Format, Version 20.2.0.7\n') or len(blob) < 40:
            return ['NIF 版本或文件头不兼容: ' + relative]
    elif relative.endswith(('.xwm', '.wav')):
        if blob[:4] != b'RIFF' or blob[8:12] not in (b'WAVE', b'XWMA'):
            return ['音频文件头不兼容: ' + relative]
    return []

def title(root):
    value = root.parent.name if root.name.lower() == 'data' else root.name
    if value.lower() in ('main file', 'main files'):
        value = root.parent.parent.name if root.name.lower() == 'data' else root.parent.name
    return re.sub(r'-\d{4,}-[\d-]+$', '', value).strip()

def portable_nif(blob):
    """Rewrite only verified length-prefixed absolute texture strings in blocks.

    Preserve block order, references, transforms and geometry. Update each block
    size in the NIF envelope. Non-SSE envelopes are intentionally not rewritten.
    """
    position = blob.index(b'\n') + 1
    def unpack(fmt):
        nonlocal position
        values = struct.unpack_from('<' + fmt, blob, position)
        position += struct.calcsize('<' + fmt)
        return values
    version, endian, user, count, stream = unpack('IBIII')
    if (version, endian, user, stream) != (0x14020007, 1, 12, 100):
        raise ValueError('Absolute-path repair only supports SSE NIF stream 100')
    for _ in range(3):
        length = unpack('B')[0]; position += length
    for _ in range(unpack('H')[0]):
        length = unpack('I')[0]; position += length
    position += count * 2
    sizes_at = position
    sizes = unpack('I' * count)
    nstrings, _ = unpack('II')
    for _ in range(nstrings):
        length = unpack('I')[0]; position += length
    groups = unpack('I')[0]
    if groups:
        raise ValueError('Unexpected NIF groups')
    header_end = position
    blocks, repairs = [], []
    for size in sizes:
        block = blob[position:position + size]; position += size
        matches = list(re.finditer(rb'[A-Za-z]:[/\\][^\x00-\x1f]{1,512}\.dds', block, flags=re.I))
        for match in reversed(matches):
            old = match.group()
            if match.start() < 4 or struct.unpack_from('<I', block, match.start() - 4)[0] != len(old):
                raise ValueError('Absolute texture path is not a standalone sized string')
            normalized = old.replace(b'\\', b'/')
            start = normalized.lower().find(b'textures/')
            if start < 0:
                raise ValueError('Cannot find texture root in absolute path')
            new = normalized[start:].replace(b'/', b'\\')
            block = block[:match.start() - 4] + struct.pack('<I', len(new)) + new + block[match.end():]
            repairs.append({'old': old.decode(), 'new': new.decode()})
        blocks.append(block)
    if blob[position:] != struct.pack('<II', 1, 0):
        raise ValueError('Unexpected NIF footer')
    header = bytearray(blob[:header_end])
    struct.pack_into('<' + 'I' * count, header, sizes_at, *(len(b) for b in blocks))
    return bytes(header) + b''.join(blocks) + blob[position:], repairs

def finalize(args, result, sources):
    themes = result['themes']
    repaired_files = 0
    for theme in themes:
        theme['name'] = title(Path(theme['root']))
        issue = '模型包含作者电脑的绝对纹理路径，需修正后启用'
        if issue in theme['issues']:
            failed = False
            for relative, source in theme['assets'].items():
                if not relative.endswith('.nif'):
                    continue
                blob = sources.read(source)
                if not re.search(rb'[A-Za-z]:[/\\][^\x00\r\n]+\.dds', blob, flags=re.I):
                    continue
                try:
                    fixed, repairs = portable_nif(blob)
                    if not repairs:
                        raise ValueError('No repair performed')
                    source['source_sha256'] = source['sha256']
                    source['sha256'] = hashlib.sha256(fixed).hexdigest()
                    source['size'] = len(fixed)
                    source['repairs'] = repairs
                    repaired_files += 1
                except Exception as exc:
                    theme['issues'].append('绝对路径修正失败: ' + str(exc)); failed = True
            if not failed:
                theme['issues'].remove(issue)
    # Unreferenced wallpapers are still recovered. Exact image copies already
    # represented by a complete theme are recorded there without another copy.
    extras = []
    by_image = {}
    for theme in themes:
        for relative, source in theme['assets'].items():
            if relative.endswith('.dds') and not theme['issues']:
                by_image.setdefault(source['sha256'], theme)
    for theme in themes:
        for orphan in theme['orphans']:
            owner = by_image.get(orphan['source']['sha256'])
            if owner:
                owner.setdefault('duplicate_image_sources', []).append(orphan['source']['path'])
                continue
            extras.append({'name': theme['name'] + ' - ' + PurePosixPath(orphan['resource']).stem,
                           'root': str(Path(orphan['source']['path']).parent),
                           'assets': {orphan['resource']: orphan['source']},
                           'sources': [{'root': orphan['source']['path'], 'name': theme['name']}],
                           'issues': ['同目录模型未引用此图片，保留供筛选'], 'fallback_dependencies': [], 'orphans': []})
    themes += extras
    # Partial backup copies can be represented by an existing complete effect
    # only if every recovered path and byte is already present there.
    kept, merged_partial = [], 0
    complete = [c for c in themes if not c['issues']]
    for theme in themes:
        owner = None
        if theme['issues'] and theme['assets']:
            owner = next((c for c in complete if all(k in c['assets'] and v['sha256'] == c['assets'][k]['sha256']
                          for k, v in theme['assets'].items())), None)
        if owner:
            owner.setdefault('partial_duplicate_sources', []).extend(theme['sources'])
            merged_partial += 1
        else:
            kept.append(theme)
    # Keep editable PSD source files too, outside the random-selection pool.
    for text in args.inventory.read_text(encoding='utf-8-sig').splitlines():
        path = Path(text)
        if path.suffix.lower() == '.psd' and 'mainmenu' in path.name.lower():
            source = sources.describe({'kind': 'loose', 'path': str(path)})
            kept.append({'name': 'PSD源图 - ' + path.stem, 'root': str(path.parent),
                         'sources': [{'root': str(path), 'name': path.stem}],
                         'assets': {'sourceart/' + path.name: source}, 'issues': ['PSD 编辑源文件，不直接参与游戏显示'],
                         'fallback_dependencies': [], 'orphans': []})
    unique = {}
    for theme in kept:
        theme['fingerprint'] = hashlib.sha256(json.dumps([(k, v['sha256']) for k, v in sorted(theme['assets'].items())], separators=(',', ':')).encode()).hexdigest()
        if theme['fingerprint'] in unique:
            unique[theme['fingerprint']]['sources'].extend(theme['sources'])
        else:
            unique[theme['fingerprint']] = theme
    themes = sorted(unique.values(), key=lambda c: (bool(c['issues']), c['name'].lower()))
    for index, theme in enumerate(themes, 1):
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', theme['name']).strip(' .')[:65]
        theme['folder'] = ('_待确认/' if theme['issues'] else '') + f'{index:03d}_{name}_{theme["fingerprint"][:8]}'
        theme['bytes'] = sum(v['size'] for v in theme['assets'].values())
    summary = {**result['summary'], 'complete_effects': sum(not c['issues'] for c in themes),
               'review_effects': sum(bool(c['issues']) for c in themes), 'output_folders': len(themes),
               'partial_duplicates_merged': merged_partial, 'repaired_nif_files': repaired_files,
               'bytes': sum(c['bytes'] for c in themes),
               'bsa_resource_copies': sum(v['kind'] == 'bsa' for c in themes for v in c['assets'].values()),
               'bsa_unique_resources': len({(v['path'], v.get('key')) for c in themes for v in c['assets'].values() if v['kind'] == 'bsa'})}
    final = {'summary': summary, 'themes': themes}
    dump(args.report / 'final-plan.json', final)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return final

def materialize(source, sources):
    blob = sources.read(source)
    if hashlib.sha256(blob).hexdigest() != source.get('source_sha256', source['sha256']):
        raise ValueError('Source changed after planning: ' + source['path'])
    if source.get('repairs'):
        blob, repairs = portable_nif(blob)
        if repairs != source['repairs']:
            raise ValueError('NIF repair differs from plan')
    if hashlib.sha256(blob).hexdigest() != source['sha256']:
        raise ValueError('Output hash mismatch')
    return blob

def preview(theme_root, theme):
    from PIL import Image, ImageOps
    errors, previews = [], []
    assets = theme['assets']
    primary = [k for k in assets if k.endswith('.dds') and 'mainmenuwallpaper' in k]
    if not primary:
        primary = sorted([k for k in assets if k.endswith(('.dds', '.psd'))], key=lambda k: -assets[k]['size'])[:1]
    for i, relative in enumerate(sorted(primary)):
        try:
            with Image.open(theme_root / 'Data' / relative) as original:
                dimensions = list(original.size)
                image = original.convert('RGB')
                image.thumbnail((640, 400), Image.Resampling.LANCZOS)
                filename = 'preview.jpg' if not previews else f'preview-{len(previews) + 1}.jpg'
                image.save(theme_root / filename, quality=85)
            previews.append({'path': filename, 'resource': relative, 'dimensions': dimensions})
        except Exception as exc:
            errors.append({'resource': relative, 'error': str(exc)})
    return previews, errors

def apply(args, result, sources):
    library = args.destination / 'MainMenuManager/backgrounds'
    for theme in result['themes']:
        root = library / theme['folder']
        if root.exists():
            raise ValueError('Destination already exists; no overwrite: ' + str(root))
        if not root.resolve().is_relative_to(library.resolve()):
            raise ValueError('Theme escapes destination')
    installed = []
    for index, theme in enumerate(result['themes'], 1):
        root = library / theme['folder']
        root.mkdir(parents=True)
        (root / 'disabled.txt').write_text('迁移未完成，禁止随机加载。', encoding='utf-8')
        for relative, source in theme['assets'].items():
            target = root / 'Data' / key(relative)
            if not target.resolve().is_relative_to(root.resolve()):
                raise ValueError('Resource escapes theme')
            target.parent.mkdir(parents=True, exist_ok=True)
            blob = materialize(source, sources)
            with target.open('xb') as f:
                f.write(blob)
            with target.open('rb') as f:
                if hashlib.file_digest(f, 'sha256').hexdigest() != source['sha256']:
                    raise ValueError('Copied resource differs: ' + str(target))
        previews, errors = preview(root, theme)
        metadata = {'name': theme['name'], 'enabled': not theme['issues'], 'migrationFingerprint': theme['fingerprint'],
                    'sources': theme['sources'], 'issues': theme['issues'], 'previews': previews}
        dump(root / 'theme.json', metadata)
        dump(root / 'source-manifest.json', {**theme, 'previews': previews, 'preview_errors': errors})
        (root / '来源与说明.txt').write_text('\n'.join([theme['name'], '', *theme['issues'], '', '来源：',
            *(x['root'] for x in theme['sources']), '', '原文件均保留。没有在游戏内验证显示效果。',
            '本目录可整体移出 backgrounds；也可添加 disabled.txt 暂停参与随机。']), encoding='utf-8')
        if not theme['issues']:
            (root / 'disabled.txt').unlink()
        else:
            (root / 'disabled.txt').write_text('\n'.join(theme['issues']), encoding='utf-8')
        installed.append({**theme, 'previews': previews, 'preview_errors': errors})
        if index % 25 == 0:
            print(f'Copied and verified {index}/{len(result["themes"])} theme folders', flush=True)
    result = {**result, 'themes': installed}
    dump(args.report / 'migration-result.json', result)
    report_root = args.destination / 'MainMenuManager/migration-20260912'
    dump(report_root / 'migration-result.json', result)
    inspection = json.loads((args.report / 'inspection.json').read_text(encoding='utf-8'))
    dump(report_root / 'archive-inspection.json', {k: v for k, v in inspection.items() if k != 'loose_anchors'})
    build_gallery(args, result)
    return result

def build_gallery(args, result):
    cards = []
    for theme in result['themes']:
        prefix = 'backgrounds/' + theme['folder'] + '/'
        link = quote(prefix, safe='/')
        images = ''.join(f'<a href="{link}{quote(p["path"])}"><img loading="lazy" src="{link}{quote(p["path"])}" alt="{html.escape(theme["name"])}"></a>' for p in theme.get('previews', []))
        state = '待确认' if theme['issues'] else '已迁移'
        cards.append(f'<article data-state="{state}">{images or "<div class=empty>无预览</div>"}<h2>{html.escape(theme["name"])}</h2><p class=tag>{state}</p><p>{html.escape(theme["folder"])}</p><p>{html.escape("；".join(theme["issues"]))}</p><a href="{link}来源与说明.txt">查看来源</a> · <a href="{link}">打开主题目录</a></article>')
    summary = result['summary']
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>开屏背景库</title>
<style>body{background:#141b24;color:#e7edf3;font:15px system-ui;margin:30px}h1{font-size:28px}header{position:sticky;top:0;background:#141b24ed;padding:12px 0;z-index:1}input,select{font:inherit;padding:10px;border:1px solid #506077;border-radius:6px;background:#202d3e;color:white}input{width:50%;max-width:600px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}article{background:#202b39;border-radius:10px;padding:12px;overflow:hidden}img{width:100%;aspect-ratio:16/10;object-fit:contain;background:#090d13}h2{font-size:17px}p{overflow-wrap:anywhere;font-size:13px;color:#aebdcc}a{color:#8bc5ff}.tag{color:#91dfbc}.empty{height:180px;display:grid;place-items:center}article[hidden]{display:none}</style>
<h1>开屏背景库</h1><p>一套效果一个文件夹。预览展示纹理图片，模型动画、烟雾和音乐需在游戏中确认。</p>
<p>COUNT</p><p>筛选后可在资源管理器中把整个主题文件夹移走，或新建 disabled.txt 停用。此页面只浏览，不执行删除。</p>
<header><input id="q" placeholder="搜索名称或目录编号"><select id="state"><option value="">全部</option><option>已迁移</option><option>待确认</option></select> <span id="count"></span></header><main>CARDS</main>
<script>const cards=[...document.querySelectorAll('article')],q=document.getElementById('q'),state=document.getElementById('state');function filter(){let n=0;for(const card of cards){card.hidden=!(card.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!state.value||card.dataset.state===state.value));if(!card.hidden)n++}document.getElementById('count').textContent=n+' 项'}q.oninput=filter;state.onchange=filter;filter();</script></html>'''
    document = document.replace('COUNT', f'完整效果 {summary["complete_effects"]} 套 · 待确认资源 {summary["review_effects"]} 项 · 原始资源全部保留。').replace('CARDS', '\n'.join(cards))
    path = args.destination / 'MainMenuManager/背景目录.html'
    path.write_text(document, encoding='utf-8')
    print('Gallery:', path)

def plan(args, archives, loose):
    sources = Sources(args, archives)
    roots = {row['root'] for row in loose}
    # Custom BSAs with a standard menu mesh can supply a standalone theme.
    # Original game archives are dependencies, not custom wallpaper candidates.
    vanilla = args.game / 'SkyrimSE/Data'
    for archive in archives.values():
        if archive.path.parent != vanilla and any(anchor(k) for k in archive.files):
            roots.add(str(archive.path.parent))
    candidates = []
    for number, text in enumerate(sorted(roots, key=str.lower)):
        root = Path(text)
        assets, issues, dependencies = {}, [], []
        def include(relative, fallback=False):
            relative = key(relative)
            source = sources.resolve(root, relative, fallback)
            if not source:
                return None
            try:
                blob = sources.read(source)
                issues.extend(header_issues(relative, blob))
                assets[relative] = sources.describe(source)
                if source.get('fallback'):
                    dependencies.append(relative)
                return blob
            except Exception as exc:
                issues.append(f'无法读取 {relative}: {exc}')
                return None
        logo = include('meshes/interface/logo/logo.nif')
        ae = include('meshes/interface/logo/logo01ae.nif')
        if logo is None and ae is not None:
            assets['meshes/interface/logo/logo.nif'] = dict(assets['meshes/interface/logo/logo01ae.nif'])
            logo = ae
        if logo is None:
            issues.append('缺少同套主菜单模型，未擅自配用其他主题模型')
        smoke = include('meshes/interface/intmenufogparticles.nif')
        for mesh in (logo, ae, smoke):
            if mesh:
                if re.search(rb'[a-zA-Z]:[/\\][^\x00\r\n]+\.dds', mesh, flags=re.I):
                    issues.append('模型包含作者电脑的绝对纹理路径，需修正后启用')
                try:
                    references = texture_refs(mesh)
                except Exception as exc:
                    issues.append('模型纹理路径异常: ' + str(exc))
                    references = []
                for relative in references:
                    if relative in assets:
                        continue
                    if include(relative, fallback=True) is None:
                        issues.append('缺少模型引用纹理: ' + relative)
        for relative in ('music/special/mus_maintheme.xwm', 'music/special/mus_maintheme.wav'):
            include(relative)
        if all(k in assets for k in ('music/special/mus_maintheme.xwm', 'music/special/mus_maintheme.wav')):
            issues.append('同时存在两种主菜单音乐，需要人工选择')
        # Keep orphan wallpaper files available for review, but do not copy
        # unrelated interface textures from a large source mod wholesale.
        orphans = []
        for row in loose:
            if row['root'] == text and row['resource'].endswith('.dds') and row['resource'] not in assets:
                relative = row['resource']
                if logo is None:
                    include(relative)
                else:
                    orphans.append({'resource': relative, 'source': sources.describe({'kind': 'loose', 'path': row['file']})})
        if not any(k.endswith('.dds') for k in assets):
            issues.append('没有可识别的 DDS 纹理')
        total = sum(v['size'] for v in assets.values())
        if total > 1024**3 or len(assets) > 2048:
            issues.append('超过模组资源容量限制')
        fingerprint = hashlib.sha256(json.dumps([(k, v['sha256']) for k, v in sorted(assets.items())], separators=(',', ':')).encode()).hexdigest()
        candidates.append({'name': title(root), 'root': text, 'assets': assets, 'issues': sorted(set(issues)),
                           'fallback_dependencies': sorted(set(dependencies)), 'orphans': orphans,
                           'fingerprint': fingerprint, 'bytes': total})
        if number % 50 == 0:
            print(f'Inspected {number + 1}/{len(roots)} theme roots', flush=True)
    # Prefer canonical library sources when identical effects also occur in
    # overwrite/backups or accidentally nested folders.
    candidates.sort(key=lambda c: (bool(c['issues']), '/backup/' in c['root'].replace('\\', '/').lower(),
                                    '/mainmenuwallpapers/' not in c['root'].replace('\\', '/').lower(), len(c['root'])))
    unique = {}
    for candidate in candidates:
        identity = candidate['fingerprint']
        source_info = {'root': candidate['root'], 'name': candidate['name']}
        if identity in unique:
            unique[identity]['sources'].append(source_info)
            unique[identity]['orphans'].extend(candidate['orphans'])
        else:
            unique[identity] = {**candidate, 'sources': [source_info]}
    themes = sorted(unique.values(), key=lambda c: (bool(c['issues']), c['name'].lower()))
    summary = {'candidate_roots': len(candidates), 'unique_effects': len(themes),
               'complete_effects': sum(not c['issues'] for c in themes),
               'review_effects': sum(bool(c['issues']) for c in themes),
               'duplicate_roots': len(candidates) - len(themes),
               'bytes': sum(c['bytes'] for c in themes),
               'bsa_resources': sum(v['kind'] == 'bsa' for c in themes for v in c['assets'].values())}
    result = {'summary': summary, 'themes': themes}
    dump(args.report / 'migration-plan.json', result)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Review:', json.dumps([{'name': c['name'], 'issues': c['issues']} for c in themes if c['issues']], ensure_ascii=False))
    return result, sources

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['inspect', 'plan', 'finalize', 'apply'])
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--game', type=Path, default=Path(r'C:\Users\linos\Desktop\games\+skyrim'))
    parser.add_argument('--profile', default='-std-')
    args = parser.parse_args()
    sys.path.insert(0, str(args.report / 'python-libs'))
    if args.mode in ('inspect', 'plan'):
        archives, loose = inventory(args)
        if args.mode == 'plan':
            plan(args, archives, loose)
    else:
        result = json.loads((args.report / ('final-plan.json' if args.mode == 'apply' else 'migration-plan.json')).read_text(encoding='utf-8'))
        archives = {path: BSA(path) for path in {v['path'] for c in result['themes'] for v in c['assets'].values() if v['kind'] == 'bsa'}}
        sources = Sources(args, archives)
        if args.mode == 'finalize':
            finalize(args, result, sources)
        else:
            apply(args, result, sources)
