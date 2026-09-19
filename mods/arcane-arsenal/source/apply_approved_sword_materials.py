"""Apply the four approved greatsword materials to the eight one-handed swords.

Only Body/Edge shaders and texture sets may change. Immutable 0.51.9 runtime
snapshot supplies both source weapons and approved material references.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct
from nif_blocks import NifBlocks
from release_assets import runtime_paths

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.52.0'
BASE = ROOT / 'build/before-0.52.0/data'
STAGE = ROOT / 'build/approved-swords/data'
ART = ROOT / 'art/approved-swords'
MESH = Path('meshes/weapons/arcanearsenal')
LABELS = {'red': 'R5 绯玉霜华', 'green': 'G7 青碧层晶', 'blue': 'B7 海蓝层晶', 'purple': 'P3 幻紫欧泊·显色修正'}
CATALOG = [s for s in json.loads((ROOT / 'source/catalog.json').read_text('utf-8')) if s.get('weapon_type') == 'sword']
assert len(CATALOG) == 8
assert all(sum(s['key'].endswith(c) for s in CATALOG) == 2 for c in LABELS)


def snapshot():
    manifest = BASE.parent / 'manifest.json'
    if manifest.exists():
        for rel, digest in json.loads(manifest.read_text()).items():
            assert hashlib.sha256((BASE / rel).read_bytes()).hexdigest() == digest
        return
    assert not BASE.exists(), 'Incomplete snapshot'
    hashes = {}
    for src in runtime_paths():
        rel = src.relative_to(ROOT / 'data')
        dst = BASE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        hashes[rel.as_posix()] = hashlib.sha256(src.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes, indent=2))


def shapes(nif):
    result = {}
    for kind, blob in nif.blocks:
        if kind != 'BSTriShape':
            continue
        name = nif.strings[struct.unpack_from('<I', blob)[0]].decode()
        si = struct.unpack_from('<I', blob, 92)[0]
        assert nif.blocks[si][0] == 'BSLightingShaderProperty'
        ti = struct.unpack_from('<I', nif.blocks[si][1], 40)[0]
        assert nif.blocks[ti][0] == 'BSShaderTextureSet'
        result[name] = (si, ti)
    return result


def texture_paths(blob):
    count = struct.unpack_from('<I', blob)[0]
    pos = 4
    result = []
    for _ in range(count):
        size = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
        result.append(blob[pos:pos+size].decode().replace('\\', '/'))
        pos += size
    assert pos == len(blob) and count == 9
    return result


def build_one(key):
    color = next(c for c in LABELS if key.endswith(c))
    target = NifBlocks(BASE / MESH / (key + '.nif'))
    ref = NifBlocks(BASE / MESH / ('greatsword3' + color + '.nif'))
    targets, refs = shapes(target), shapes(ref)
    assert set(targets) == {'AA_SwordBody', 'AA_SwordEdge'}
    touched = set()
    for part in ('Body', 'Edge'):
        si, ti = targets['AA_Sword' + part]
        ri, rt = refs['AA_Greatsword' + part]
        old, approved = target.blocks[si][1], ref.blocks[ri][1]
        assert len(old) == len(approved) == 100
        # Retain target-specific name, extra-data and controller references.
        shader = bytearray(approved[:4] + old[4:16] + approved[16:])
        struct.pack_into('<I', shader, 40, ti)
        target.blocks[si] = ('BSLightingShaderProperty', bytes(shader))
        target.blocks[ti] = ref.blocks[rt]
        touched.update((si, ti))
    return target, touched


def verify(data):
    snapshot()
    reports = []
    for spec in CATALOG:
        key = spec['key']
        color = next(c for c in LABELS if key.endswith(c))
        rel = MESH / (key + '.nif')
        old, actual = NifBlocks(BASE / rel), NifBlocks(data / rel)
        expected, touched = build_one(key)
        assert actual.blocks == expected.blocks and actual.strings == old.strings
        assert actual.footer == old.footer and len(actual.blocks) == len(old.blocks)
        assert all(a == b for i, (a, b) in enumerate(zip(old.blocks, actual.blocks)) if i not in touched)
        assert b'WeaponSword' in actual.strings
        assert len([k for k, _ in actual.blocks if k == 'NiParticleSystem']) == 6
        refs = NifBlocks(BASE / MESH / ('greatsword3' + color + '.nif'))
        for part in ('Body', 'Edge'):
            si, ti = shapes(actual)['AA_Sword' + part]
            ri, rt = shapes(refs)['AA_Greatsword' + part]
            shader, reference = actual.blocks[si][1], refs.blocks[ri][1]
            assert shader[:4] == reference[:4] and shader[16:40] == reference[16:40] and shader[44:] == reference[44:]
            assert actual.blocks[ti] == refs.blocks[rt]
            assert shader[4:16] == old.blocks[si][1][4:16]
            for path in texture_paths(actual.blocks[ti][1]):
                if path:
                    assert (ROOT / 'data' / path).is_file(), path
                    assert (ROOT / 'data' / path).read_bytes() == (BASE / path).read_bytes()
        reports.append(dict(key=key, name=spec['name'], material=LABELS[color],
                            geometry_uv_collision_particles_preserved=True))
    if data == ROOT / 'data':
        oldfiles = {Path(p) for p in json.loads((BASE.parent / 'manifest.json').read_text())}
        assert {p.relative_to(data) for p in runtime_paths()} == oldfiles
        changed = {p for p in oldfiles if (BASE / p).read_bytes() != (data / p).read_bytes()}
        assert changed == {MESH / (s['key'] + '.nif') for s in CATALOG}, changed
    report = dict(version=VERSION, passed=True, swords=reports, reference='0.51.9 greatsword3 materials',
                  other_runtime_unchanged=True, gameplay_tested=False)
    (ROOT / 'build/approved-swords-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(version=VERSION, swords=8, passed=True)), flush=True)


def native_verify(data):
    # Independent parser checks final paths and shader data after byte checks.
    import sys
    sys.path.insert(0, str(ROOT.parents[1] / 'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
    from pyn.pynifly import NifFile
    for spec in CATALOG:
        nif = NifFile(str(data / MESH / (spec['key'] + '.nif')))
        assert not NifFile.message_log()
        assert {s.name for s in nif.shapes} == {'AA_SwordBody', 'AA_SwordEdge'}
        for shape in nif.shapes:
            for slot in ('Diffuse', 'Normal', 'Glow'):
                assert (ROOT / 'data' / shape.textures[slot].replace('\\', '/')).is_file()
    print('Native NIF readback passed: 8 swords', flush=True)


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
    (STAGE / MESH).mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    for spec in CATALOG:
        nif, _ = build_one(spec['key'])
        nif.save(STAGE / MESH / (spec['key'] + '.nif'))
    verify(STAGE)
    native_verify(STAGE)
    if args.apply:
        # Fail before changing anything if another task has modified a target.
        for spec in CATALOG:
            rel = MESH / (spec['key'] + '.nif')
            assert (ROOT / 'data' / rel).read_bytes() in ((BASE / rel).read_bytes(), (STAGE / rel).read_bytes())
        for spec in CATALOG:
            rel = MESH / (spec['key'] + '.nif')
            dst = ROOT / 'data' / rel
            tmp = dst.with_name(dst.name + '.material-tmp')
            tmp.write_bytes((STAGE / rel).read_bytes())
            tmp.replace(dst)
        verify(ROOT / 'data')


if __name__ == '__main__':
    main()
