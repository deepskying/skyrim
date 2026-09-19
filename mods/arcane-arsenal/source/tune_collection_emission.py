"""0.52.2 emission retune: retain visible material detail under game HDR/ENB."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess, sys
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import CONV, MESH, TEX

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.52.2'
BASE = ROOT / 'build/before-0.52.2/data'
STAGE = ROOT / 'build/emission-retune/data'
ART = ROOT / 'art/emission-retune'
CATALOG = json.loads((ROOT / 'source/catalog.json').read_text(encoding='utf-8'))
PREFIXES = {'余烬': 'red', '流萤': 'green', '寒汐': 'blue', '梦隙': 'purple'}
# Values are deliberately below bloom threshold in typical Skyrim HDR/ENB use.
BODY_POWER = {'red': .45, 'green': .55, 'blue': .55, 'purple': .50}
EDGE_POWER = {'red': 1.20, 'green': 1.35, 'blue': 1.45, 'purple': 1.20}
STRING_POWER = {'red': .85, 'green': .95, 'blue': .95, 'purple': .85}


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


def color_for(spec):
    prefix = spec['name'].split('·', 1)[0]
    assert prefix in PREFIXES, (spec['key'], spec['name'])
    return PREFIXES[prefix]


def shape_shaders(nif):
    result = {}
    for kind, blob in nif.blocks:
        if kind != 'BSTriShape':
            continue
        name = nif.strings[struct.unpack_from('<I', blob)[0]].decode()
        shader = struct.unpack_from('<I', blob, 92)[0]
        assert nif.blocks[shader][0] == 'BSLightingShaderProperty'
        result[name] = shader
    return result


def retuned_shader(blob, part, color):
    result = bytearray(blob)
    if part in ('Body', 'Fold'):
        power = BODY_POWER[color]
    elif part == 'Edge':
        power = EDGE_POWER[color]
    else:
        assert part == 'String'
        power = STRING_POWER[color]
    struct.pack_into('<f', result, 56, power)
    return bytes(result)


def patch_nif(spec):
    color = color_for(spec)
    path = BASE / MESH / (spec['key'] + '.nif')
    nif = NifBlocks(path)
    touched = set()
    for name, index in shape_shaders(nif).items():
        part = next((suffix for suffix in ('Body', 'Fold', 'Edge', 'String') if name.endswith(suffix)), None)
        if part is None:
            continue
        kind, blob = nif.blocks[index]
        nif.blocks[index] = (kind, retuned_shader(blob, part, color))
        touched.add(index)
    assert any(name.endswith('Body') for name in shape_shaders(nif))
    return nif, touched


def red_glow():
    """Build a lower-value, saturated R5 emission map without erasing seams."""
    from PIL import Image
    source = Image.open(BASE / TEX / 'aa_luminous_pinkjade_g.dds').convert('RGB')
    rgb = np.asarray(source, dtype=np.float32) / 255.
    maximum = rgb.max(axis=-1, keepdims=True)
    minimum = rgb.min(axis=-1, keepdims=True)
    saturation = (maximum - minimum) / np.maximum(maximum, .001)
    # Only desaturating highlights are steered toward rose; saturated icy mineral
    # seams retain their hue. Gamma + scale move the entire map below white bloom.
    rose = np.array([1., .33, .47], dtype=np.float32)
    tint = np.clip((1. - saturation) * .48, 0, .48)
    cyan = (rgb[..., 1] > rgb[..., 0] * 1.02) & (rgb[..., 2] > rgb[..., 0] * 1.02)
    tint[cyan] = 0.
    tuned = rgb * (1. - tint) + rose * tint
    tuned = np.power(np.clip(tuned, 0, 1), 1.32) * np.array([.72, .66, .70], dtype=np.float32)
    path = ART / 'aa_luminous_pinkjade_g.png'
    Image.fromarray(np.round(np.clip(tuned, 0, 1) * 255).astype(np.uint8)).save(path)
    subprocess.run([str(CONV), '-nologo', '-y', '-f', 'BC3_UNORM', '-m', '0',
                    '-o', str(STAGE / TEX), str(path)], check=True, capture_output=True)


def verify(data):
    from PIL import Image
    snapshot()
    reports = []
    for spec in CATALOG:
        color = color_for(spec)
        rel = MESH / (spec['key'] + '.nif')
        old, actual = NifBlocks(BASE / rel), NifBlocks(data / rel)
        expected, touched = patch_nif(spec)
        assert actual.blocks == expected.blocks and actual.strings == old.strings and actual.footer == old.footer
        assert len(actual.blocks) == len(old.blocks)
        assert all(a == b for i, (a, b) in enumerate(zip(old.blocks, actual.blocks)) if i not in touched)
        parts = {}
        for name, index in shape_shaders(actual).items():
            part = next((suffix for suffix in ('Body', 'Fold', 'Edge', 'String') if name.endswith(suffix)), None)
            if part:
                actual_power = struct.unpack_from('<f', actual.blocks[index][1], 56)[0]
                expected_power = {'Body': BODY_POWER, 'Fold': BODY_POWER, 'Edge': EDGE_POWER, 'String': STRING_POWER}[part][color]
                assert abs(actual_power - expected_power) < 1e-6
                parts[part] = actual_power
        reports.append(dict(key=spec['key'], color=color, emission=parts,
                            geometry_uv_skeleton_collision_particles_preserved=True))
    glow_rel = TEX / 'aa_luminous_pinkjade_g.dds'
    before = np.asarray(Image.open(BASE / glow_rel).convert('RGBA'), dtype=np.float32) / 255.
    after_img = Image.open(data / glow_rel).convert('RGBA')
    after = np.asarray(after_img, dtype=np.float32) / 255.
    raw = (data / glow_rel).read_bytes()
    assert raw[:4] == b'DDS ' and raw[84:88] == b'DXT5' and struct.unpack_from('<I', raw, 28)[0] == 11
    assert after_img.size == (1024, 1024) and after_img.getchannel('A').getextrema() == (255, 255)
    luma = lambda image: image[..., :3] @ np.array([.2126, .7152, .0722])
    chroma = lambda image: image[..., :3].max(-1) - image[..., :3].min(-1)
    assert luma(after).mean() < luma(before).mean() * .68
    assert chroma(after).mean() > chroma(before).mean() * .85
    # Strongly red pixels remain dominant and cyan veins survive the correction.
    assert (after[..., 0] > after[..., 1] * 1.28).mean() > .30
    assert ((after[..., 1] > after[..., 0] * 1.02) & (after[..., 2] > after[..., 0] * 1.02)).mean() > .002
    if data == ROOT / 'data':
        files = {Path(path) for path in json.loads((BASE.parent / 'manifest.json').read_text())}
        assert {path.relative_to(data) for path in runtime_paths()} == files
        changed = {path for path in files if (BASE / path).read_bytes() != (data / path).read_bytes()}
        expected_changed = {MESH / (spec['key'] + '.nif') for spec in CATALOG} | {glow_rel}
        assert changed == expected_changed, changed
    report = dict(version=VERSION, passed=True, covered=len(CATALOG), emission={
        'body': BODY_POWER, 'edge': EDGE_POWER, 'string': STRING_POWER},
        red_glow_luminance_before=float(luma(before).mean()), red_glow_luminance_after=float(luma(after).mean()),
        red_glow_chroma_before=float(chroma(before).mean()), red_glow_chroma_after=float(chroma(after).mean()),
        weapons=reports, other_runtime_unchanged=True, gameplay_tested=False)
    (ROOT / 'build/emission-retune-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(version=VERSION, covered=len(CATALOG), passed=True)), flush=True)


def native_verify(data):
    sys.path.insert(0, str(ROOT.parents[1] / 'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
    from pyn.pynifly import NifFile
    for spec in CATALOG:
        nif = NifFile(str(data / MESH / (spec['key'] + '.nif')))
        assert not NifFile.message_log(), spec['key']
    print(f'Native NIF readback passed: {len(CATALOG)} weapons', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(ROOT / 'data')
        native_verify(ROOT / 'data')
        return
    snapshot()
    for path in (STAGE / MESH, STAGE / TEX, ART):
        path.mkdir(parents=True, exist_ok=True)
    red_glow()
    for spec in CATALOG:
        nif, _ = patch_nif(spec)
        nif.save(STAGE / MESH / (spec['key'] + '.nif'))
    verify(STAGE)
    native_verify(STAGE)
    if args.apply:
        for spec in CATALOG:
            rel = MESH / (spec['key'] + '.nif')
            assert (ROOT / 'data' / rel).read_bytes() in ((BASE / rel).read_bytes(), (STAGE / rel).read_bytes())
        for src in STAGE.rglob('*'):
            if not src.is_file():
                continue
            dst = ROOT / 'data' / src.relative_to(STAGE)
            temp = dst.with_name(dst.name + '.emission-tmp')
            temp.write_bytes(src.read_bytes())
            temp.replace(dst)
        verify(ROOT / 'data')


if __name__ == '__main__':
    main()
