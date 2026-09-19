"""R5 luminous pink jade / P3 violet opal on all six red/purple greatswords.

Derive DDS maps from approved concept-based albedo sources. Preserve every NIF
block except the body shader and texture set. Build and verify before applying.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import body, CONV, MESH, TEX

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.51.8'
BASE = ROOT / 'build/before-0.51.8/data'
STAGE = ROOT / 'build/luminous-jade-opal/data'
ART = ROOT / 'art/luminous-jade-opal'
SPECS = {
    'red': dict(material='R5 绯玉霜华', texture='aa_luminous_pinkjade', power=1.6, gloss=85., spec=.42),
    'purple': dict(material='P3 幻紫欧泊', texture='aa_luminous_violetopal', power=1.6, gloss=110., spec=.55),
}
EMIT = {c: (1., 1., 1.) for c in SPECS}
PALETTES = {'red': ['FF5379', 'FFD1DC', 'AAEFE6'], 'purple': ['AC6AFF', 'A5FFF0', 'FFD0EC']}
CATALOG = [s for s in json.loads((ROOT / 'source/catalog.json').read_text('utf-8'))
           if s.get('weapon_type') == 'greatsword' and any(s['key'].endswith(c) for c in SPECS)]
assert len(CATALOG) == 6


def snapshot():
    manifest = BASE.parent / 'manifest.json'
    if manifest.exists():
        for rel, digest in json.loads(manifest.read_text()).items():
            assert hashlib.sha256((BASE / rel).read_bytes()).hexdigest() == digest
        return
    assert not BASE.exists(), 'Incomplete snapshot; inspect before retrying'
    hashes = {}
    for src in runtime_paths():
        rel = src.relative_to(ROOT / 'data')
        dst = BASE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        hashes[rel.as_posix()] = hashlib.sha256(src.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes, indent=2))


def textures():
    from PIL import Image, ImageFilter
    for color, spec in SPECS.items():
        source = Image.open(ART / (color + '-source.png')).convert('RGB')
        source = source.resize((1024, 1024), Image.Resampling.LANCZOS)
        rgb = np.asarray(source, dtype=np.float32) / 255.
        # Keep the concept's color relationships in the emission map. White
        # emissive tint avoids turning jade's cyan seams red or opal's pink blue.
        value = rgb.max(axis=-1)
        glow = rgb * (.64 + .14 * value[..., None])
        diffuse = rgb * .94
        # Polished stone: fine shallow relief only, not fractured geometry.
        height = np.asarray(source.convert('L').filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.
        strength = .55 if color == 'red' else .9
        dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
        dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
        normal = np.stack((-dx, dy, np.ones_like(height)), axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        normal = normal * .5 + .5
        specular = (.40 + .18 * value) if color == 'red' else (.45 + .22 * value)
        for suffix, pixels, alpha in [('d', diffuse, np.ones_like(value)),
                                      ('g', glow, np.ones_like(value)),
                                      ('n', normal, specular)]:
            rgba = np.concatenate((pixels, alpha[..., None]), axis=-1)
            path = ART / (spec['texture'] + '_' + suffix + '.png')
            Image.fromarray(np.round(np.clip(rgba, 0, 1) * 255).astype(np.uint8)).save(path)
            subprocess.run([str(CONV), '-nologo', '-y', '-f', 'BC3_UNORM', '-m', '0',
                            '-o', str(STAGE / TEX), str(path)], check=True, capture_output=True)


def texture_block(color):
    paths = [str(TEX / (SPECS[color]['texture'] + '_' + suffix + '.dds')).replace('/', '\\')
             for suffix in ('d', 'n', 'g')] + [''] * 6
    return struct.pack('<I', 9) + b''.join(struct.pack('<I', len(p)) + p.encode() for p in paths)


def shader_block(old, si, color):
    sh = bytearray(old.blocks[si][1])
    assert len(sh) == 100 and struct.unpack_from('<I', sh)[0] == 2
    # Existing planar UVs are x/30, y/100. Compensate in shader sampling,
    # leaving mesh UV bytes intact: equal world-space texel scale on both axes.
    struct.pack_into('<2f', sh, 32, .55, .55 * 100. / 30.)
    struct.pack_into('<4f', sh, 44, 1., 1., 1., SPECS[color]['power'])
    struct.pack_into('<f', sh, 72, SPECS[color]['gloss'])
    struct.pack_into('<f', sh, 88, SPECS[color]['spec'])
    return bytes(sh)


def verify(data):
    from PIL import Image
    snapshot()
    reports = []
    for spec in CATALOG:
        key = spec['key']
        color = next(c for c in SPECS if key.endswith(c))
        rel = MESH / (key + '.nif')
        old, new = NifBlocks(BASE / rel), NifBlocks(data / rel)
        si, ti = body(old)
        assert old.strings == new.strings and len(old.blocks) == len(new.blocks)
        assert old.footer == new.footer
        assert all(a == b for i, (a, b) in enumerate(zip(old.blocks, new.blocks)) if i not in (si, ti))
        assert new.blocks[si] == ('BSLightingShaderProperty', shader_block(old, si, color))
        assert new.blocks[ti] == ('BSShaderTextureSet', texture_block(color))
        assert np.allclose(struct.unpack_from('<4f', new.blocks[si][1], 44), (1, 1, 1, 1.6))
        reports.append(dict(key=key, material=SPECS[color]['material'],
                            geometry_uv_collision_edges_particles_preserved=True))
    texture_reports = []
    for color, spec in SPECS.items():
        for suffix in ('d', 'n', 'g'):
            path = data / TEX / (spec['texture'] + '_' + suffix + '.dds')
            raw = path.read_bytes()
            assert raw[:4] == b'DDS ' and raw[84:88] == b'DXT5'
            assert struct.unpack_from('<I', raw, 28)[0] == 11
            im = Image.open(path).convert('RGBA')
            assert im.size == (1024, 1024)
            if suffix != 'n':
                assert im.getchannel('A').getextrema() == (255, 255)
            if suffix == 'g':
                pixels = np.asarray(im)[..., :3]
                assert pixels.max(axis=-1).min() > 80, 'Whole body must emit'
                assert np.mean(pixels.max(axis=-1) - pixels.min(axis=-1)) > 25, 'Colored emission required'
            texture_reports.append(dict(file=path.name, size=[1024, 1024], mip_levels=11))
    if data == ROOT / 'data':
        oldfiles = {Path(p) for p in json.loads((BASE.parent / 'manifest.json').read_text())}
        assert all((data / p).is_file() for p in oldfiles)
        changed = {p for p in oldfiles if (BASE / p).read_bytes() != (data / p).read_bytes()}
        assert changed == {MESH / (s['key'] + '.nif') for s in CATALOG}, changed
        additions = {p.relative_to(data) for p in runtime_paths()} - oldfiles
        assert additions == {TEX / (s['texture'] + '_' + suffix + '.dds')
                             for s in SPECS.values() for suffix in ('d', 'n', 'g')}
    report = dict(version=VERSION, greatswords=reports, textures=texture_reports,
                  palettes=PALETTES, emission_power=1.6, other_runtime_unchanged=True,
                  gameplay_tested=False)
    (ROOT / 'build/luminous-jade-opal-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(version=VERSION, greatswords=6, passed=True)), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(ROOT / 'data')
        return
    snapshot()
    for path in (ART, STAGE / MESH, STAGE / TEX):
        path.mkdir(parents=True, exist_ok=True)
    textures()
    for spec in CATALOG:
        key = spec['key']
        color = next(c for c in SPECS if key.endswith(c))
        rel = MESH / (key + '.nif')
        nif = NifBlocks(BASE / rel)
        si, ti = body(nif)
        nif.blocks[si] = ('BSLightingShaderProperty', shader_block(nif, si, color))
        nif.blocks[ti] = ('BSShaderTextureSet', texture_block(color))
        nif.save(STAGE / rel)
    verify(STAGE)
    if args.apply:
        for src in STAGE.rglob('*'):
            if src.is_file():
                dst = ROOT / 'data' / src.relative_to(STAGE)
                temp = dst.with_name(dst.name + '.luminous-tmp')
                temp.write_bytes(src.read_bytes())
                temp.replace(dst)
        verify(ROOT / 'data')


if __name__ == '__main__':
    main()
