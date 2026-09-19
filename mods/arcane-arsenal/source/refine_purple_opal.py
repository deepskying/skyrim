"""0.51.9: reduce washed-out violet opal on the three purple greatswords."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import body, CONV, MESH, TEX
import build_luminous_greatswords as original

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/before-0.51.9/data'
STAGE = ROOT / 'build/purple-opal-refined/data'
ART = ROOT / 'art/purple-opal-refined'
CATALOG = [s for s in original.CATALOG if s['key'].endswith('purple')]
SPECS = {'purple': dict(material='P3 幻紫欧泊·显色修正', texture='aa_luminous_violetopal', power=1.3)}
EMIT = {'purple': (1., 1., 1.)}
EDGE_COLOR = (.58, .14, 1.)
EDGE_POWER = 3.6
assert len(CATALOG) == 3


def snapshot():
    original.BASE = BASE
    original.snapshot()


def edge_shader(nif):
    shape = next(b for k, b in nif.blocks if k == 'BSTriShape'
                 and nif.strings[struct.unpack_from('<I', b)[0]] == b'AA_GreatswordEdge')
    return struct.unpack_from('<I', shape, 92)[0]


def adjusted_shader(blob, edge=False):
    result = bytearray(blob)
    if edge:
        struct.pack_into('<4f', result, 44, *EDGE_COLOR, EDGE_POWER)
    else:
        struct.pack_into('<f', result, 56, 1.3)
        struct.pack_into('<f', result, 88, .28)
    return bytes(result)


def textures():
    from PIL import Image
    source = Image.open(ART / 'purple-source.png').convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS)
    rgb = np.asarray(source, dtype=np.float32) / 255.
    value = rgb.max(axis=-1)
    # Lower the bright-flake emission ceiling; retain full-surface colored glow.
    glow = rgb * (.56 + .10 * value[..., None])
    for suffix, pixels in [('d', rgb * .94), ('g', glow)]:
        rgba = np.concatenate((pixels, np.ones((*value.shape, 1))), axis=-1)
        path = ART / ('aa_luminous_violetopal_' + suffix + '.png')
        Image.fromarray(np.round(np.clip(rgba, 0, 1) * 255).astype(np.uint8)).save(path)
        subprocess.run([str(CONV), '-nologo', '-y', '-f', 'BC3_UNORM', '-m', '0',
                        '-o', str(STAGE / TEX), str(path)], check=True, capture_output=True)
    # Normal/specular texture retains original surface detail exactly.
    shutil.copy2(BASE / TEX / 'aa_luminous_violetopal_n.dds', STAGE / TEX / 'aa_luminous_violetopal_n.dds')


def verify(data):
    from PIL import Image
    snapshot()
    for spec in CATALOG:
        rel = MESH / (spec['key'] + '.nif')
        old, new = NifBlocks(BASE / rel), NifBlocks(data / rel)
        si, ti = body(old)
        ei = edge_shader(old)
        assert old.strings == new.strings and len(old.blocks) == len(new.blocks)
        assert all(a == b for i, (a, b) in enumerate(zip(old.blocks, new.blocks)) if i not in (si, ei))
        for i in (si, ei):
            assert new.blocks[i] == (old.blocks[i][0], adjusted_shader(old.blocks[i][1], i == ei))
        assert new.blocks[ti] == old.blocks[ti]
    stats = {}
    for suffix in ('d', 'g'):
        rel = TEX / ('aa_luminous_violetopal_' + suffix + '.dds')
        raw = (data / rel).read_bytes()
        assert raw[:4] == b'DDS ' and raw[84:88] == b'DXT5' and struct.unpack_from('<I', raw, 28)[0] == 11
        before = np.asarray(Image.open(BASE / rel).convert('RGB'), dtype=np.float32) / 255.
        im = Image.open(data / rel).convert('RGBA')
        assert im.size == (1024, 1024) and im.getchannel('A').getextrema() == (255, 255)
        after = np.asarray(im, dtype=np.float32)[..., :3] / 255.
        sat = lambda a: (a.max(-1) - a.min(-1)) / np.maximum(a.max(-1), .001)
        luma = lambda a: a @ np.array([.2126, .7152, .0722])
        assert sat(after).mean() > sat(before).mean() * 1.25
        assert luma(after).mean() < luma(before).mean() * .90
        if suffix == 'g':
            assert after.max(-1).min() > .15, 'Whole surface must remain emissive'
        cyan = (after[..., 1] > after[..., 0] * 1.15) & (after[..., 2] > after[..., 0] * 1.15)
        pink = (after[..., 0] > after[..., 1] * 1.2) & (after[..., 0] > after[..., 2] * .9)
        assert cyan.mean() > .02 and pink.mean() > .02, 'Keep cyan and pink opal accents'
        stats[suffix] = dict(saturation_before=float(sat(before).mean()), saturation_after=float(sat(after).mean()),
                             luminance_before=float(luma(before).mean()), luminance_after=float(luma(after).mean()),
                             cyan_fraction=float(cyan.mean()), pink_fraction=float(pink.mean()))
    assert (data / TEX / 'aa_luminous_violetopal_n.dds').read_bytes() == (BASE / TEX / 'aa_luminous_violetopal_n.dds').read_bytes()
    if data == ROOT / 'data':
        oldfiles = {Path(p) for p in json.loads((BASE.parent / 'manifest.json').read_text())}
        assert {p.relative_to(data) for p in runtime_paths()} == oldfiles
        changed = {p for p in oldfiles if (BASE / p).read_bytes() != (data / p).read_bytes()}
        assert changed == {MESH / (s['key'] + '.nif') for s in CATALOG} | {
            TEX / ('aa_luminous_violetopal_' + suffix + '.dds') for suffix in ('d', 'g')}, changed
    report = dict(version='0.51.9', passed=True, greatswords=3, texture_stats=stats,
                  body_emission=1.3, edge_emission=EDGE_POWER, edge_color=EDGE_COLOR,
                  geometry_uv_collision_particles_preserved=True, other_runtime_unchanged=True, gameplay_tested=False)
    (ROOT / 'build/purple-opal-refined-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(ROOT / 'data')
        return
    snapshot()
    for path in (STAGE / MESH, STAGE / TEX):
        path.mkdir(parents=True, exist_ok=True)
    textures()
    for spec in CATALOG:
        rel = MESH / (spec['key'] + '.nif')
        nif = NifBlocks(BASE / rel)
        si, _ = body(nif)
        ei = edge_shader(nif)
        for i in (si, ei):
            nif.blocks[i] = (nif.blocks[i][0], adjusted_shader(nif.blocks[i][1], i == ei))
        nif.save(STAGE / rel)
    verify(STAGE)
    if args.apply:
        for src in STAGE.rglob('*'):
            if src.is_file():
                dst = ROOT / 'data' / src.relative_to(STAGE)
                tmp = dst.with_name(dst.name + '.opal-tmp')
                tmp.write_bytes(src.read_bytes())
                tmp.replace(dst)
        verify(ROOT / 'data')


if __name__ == '__main__':
    main()
