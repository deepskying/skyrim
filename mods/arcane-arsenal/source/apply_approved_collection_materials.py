"""Apply the approved four-colour materials to the remaining 144 weapons.

The 20 greatswords and one-handed swords already approved in 0.52.0 are left
untouched. This script alters only each remaining weapon's Body/Fold shader and
texture set plus its Edge colour/power, preserving geometry, UVs, skeletons,
collision, animation controllers, strings and particle data byte-for-byte.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, sys
from nif_blocks import NifBlocks
from release_assets import runtime_paths

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.52.1'
BASE = ROOT / 'build/before-0.52.1/data'
STAGE = ROOT / 'build/approved-collection/data'
ART = ROOT / 'art/approved-collection'
MESH = Path('meshes/weapons/arcanearsenal')
LABELS = {
    'red': 'R5 绯玉霜华',
    'green': 'G7 青碧层晶',
    'blue': 'B7 海蓝层晶',
    'purple': 'P3 幻紫欧泊·显色修正',
}
PREFIXES = {'余烬': 'red', '流萤': 'green', '寒汐': 'blue', '梦隙': 'purple'}
CATALOG = json.loads((ROOT / 'source/catalog.json').read_text(encoding='utf-8'))
TARGETS = [s for s in CATALOG if s.get('weapon_type') not in ('greatsword', 'sword')]
assert len(CATALOG) == 164 and len(TARGETS) == 144


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


def shapes(nif):
    result = {}
    for index, (kind, blob) in enumerate(nif.blocks):
        if kind != 'BSTriShape':
            continue
        name = nif.strings[struct.unpack_from('<I', blob)[0]].decode()
        shader = struct.unpack_from('<I', blob, 92)[0]
        texture = struct.unpack_from('<I', nif.blocks[shader][1], 40)[0]
        assert nif.blocks[shader][0] == 'BSLightingShaderProperty'
        assert nif.blocks[texture][0] == 'BSShaderTextureSet'
        result[name] = (index, shader, texture)
    return result


def body_and_edge(entries):
    bodies = [value for name, value in entries.items() if name.endswith(('Body', 'Fold'))]
    edges = [value for name, value in entries.items() if name.endswith('Edge')]
    assert bodies and len(edges) == 1, (entries, bodies, edges)
    return bodies, edges[0]


def references():
    result = {}
    for color in LABELS:
        nif = NifBlocks(BASE / MESH / ('greatsword3' + color + '.nif'))
        entries = shapes(nif)
        body = entries['AA_GreatswordBody']
        edge = entries['AA_GreatswordEdge']
        result[color] = {
            'body_shader': nif.blocks[body[1]][1],
            'body_texture': nif.blocks[body[2]],
            'edge_shader': nif.blocks[edge[1]][1],
        }
    return result


def patched_shader(original, reference, texture_index):
    """Use approved material values, preserving target-only flags/references."""
    # Historical material trials have four target-specific trailing bytes.
    # Keep them intact while applying the shared BSLighting fields below.
    assert len(original) >= 100 and len(reference) == 100
    result = bytearray(original)
    # UV transform, material colour/emission, glossiness and specular strength.
    # The leading bytes retain target-specific flags, alpha and controller data;
    # this keeps skinned bows/crossbows and their independent animation intact.
    result[24:40] = reference[24:40]
    result[44:56] = reference[44:56]
    result[72:92] = reference[72:92]
    struct.pack_into('<I', result, 40, texture_index)
    return bytes(result)


def edge_shader(original, reference):
    assert len(original) == len(reference) == 100
    result = bytearray(original)
    # In particular, this carries the 0.51.9 purple anti-whitening correction.
    result[44:56] = reference[44:56]
    return bytes(result)


def texture_paths(blob):
    count = struct.unpack_from('<I', blob)[0]
    pos = 4
    paths = []
    for _ in range(count):
        size = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
        paths.append(blob[pos:pos + size].decode().replace('\\\\', '/'))
        pos += size
    assert count == 9 and pos == len(blob)
    return paths


def build_one(spec, refs):
    color = color_for(spec)
    rel = MESH / (spec['key'] + '.nif')
    nif = NifBlocks(BASE / rel)
    entries = shapes(nif)
    bodies, edge = body_and_edge(entries)
    protected = {shader for name, (_, shader, _) in entries.items() if not name.endswith(('Body', 'Fold', 'Edge'))}
    touched = set()
    for _, shader, texture in bodies:
        assert shader not in protected and texture not in protected
        material = refs[color]
        nif.blocks[shader] = ('BSLightingShaderProperty', patched_shader(nif.blocks[shader][1], material['body_shader'], texture))
        nif.blocks[texture] = material['body_texture']
        touched.update((shader, texture))
    _, edge_shader_index, _ = edge
    assert edge_shader_index not in protected
    nif.blocks[edge_shader_index] = ('BSLightingShaderProperty', edge_shader(nif.blocks[edge_shader_index][1], refs[color]['edge_shader']))
    touched.add(edge_shader_index)
    return nif, touched


def verify(data):
    snapshot()
    refs = references()
    reports = []
    for spec in TARGETS:
        color = color_for(spec)
        rel = MESH / (spec['key'] + '.nif')
        old, actual = NifBlocks(BASE / rel), NifBlocks(data / rel)
        expected, touched = build_one(spec, refs)
        assert actual.blocks == expected.blocks and actual.strings == old.strings and actual.footer == old.footer
        assert len(actual.blocks) == len(old.blocks)
        assert all(a == b for i, (a, b) in enumerate(zip(old.blocks, actual.blocks)) if i not in touched)
        entries = shapes(actual)
        bodies, edge = body_and_edge(entries)
        for _, shader, texture in bodies:
            assert actual.blocks[texture] == refs[color]['body_texture']
            assert actual.blocks[shader][1][24:40] == refs[color]['body_shader'][24:40]
            assert actual.blocks[shader][1][44:56] == refs[color]['body_shader'][44:56]
            assert actual.blocks[shader][1][72:92] == refs[color]['body_shader'][72:92]
            for path in texture_paths(actual.blocks[texture][1]):
                if path:
                    assert (BASE / path).is_file(), path
        _, edge_shader_index, _ = edge
        assert actual.blocks[edge_shader_index][1][44:56] == refs[color]['edge_shader'][44:56]
        # Native attachments and particle inventory are untouched by construction.
        particle_count = len([kind for kind, _ in actual.blocks if kind == 'NiParticleSystem'])
        assert particle_count == len([kind for kind, _ in old.blocks if kind == 'NiParticleSystem'])
        reports.append(dict(key=spec['key'], name=spec['name'], color=color, material=LABELS[color],
                            body_shapes=len(bodies), particle_systems=particle_count,
                            geometry_uv_skeleton_collision_strings_preserved=True))
    if data == ROOT / 'data':
        files = {Path(path) for path in json.loads((BASE.parent / 'manifest.json').read_text())}
        assert {path.relative_to(data) for path in runtime_paths()} == files
        changed = {path for path in files if (BASE / path).read_bytes() != (data / path).read_bytes()}
        assert changed == {MESH / (spec['key'] + '.nif') for spec in TARGETS}, changed
    type_counts = {}
    for spec in TARGETS:
        group = spec.get('weapon_type', 'bow')
        type_counts[group] = type_counts.get(group, 0) + 1
    report = dict(version=VERSION, passed=True, covered=len(TARGETS), categories=type_counts,
                  references={color: LABELS[color] for color in LABELS}, weapons=reports,
                  other_runtime_unchanged=True, gameplay_tested=False)
    (ROOT / 'build/approved-collection-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(version=VERSION, covered=len(TARGETS), categories=type_counts, passed=True)), flush=True)


def native_verify(data):
    sys.path.insert(0, str(ROOT.parents[1] / 'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
    from pyn.pynifly import NifFile
    for spec in TARGETS:
        nif = NifFile(str(data / MESH / (spec['key'] + '.nif')))
        assert not NifFile.message_log(), spec['key']
        assert any(shape.name.endswith('Body') for shape in nif.shapes), spec['key']
    print('Native NIF readback passed: 144 weapons', flush=True)


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
    refs = references()
    for spec in TARGETS:
        nif, _ = build_one(spec, refs)
        nif.save(STAGE / MESH / (spec['key'] + '.nif'))
    verify(STAGE)
    native_verify(STAGE)
    if args.apply:
        # Refuse to overwrite a concurrent edit of any target.
        for spec in TARGETS:
            rel = MESH / (spec['key'] + '.nif')
            assert (ROOT / 'data' / rel).read_bytes() in ((BASE / rel).read_bytes(), (STAGE / rel).read_bytes())
        for spec in TARGETS:
            rel = MESH / (spec['key'] + '.nif')
            dst = ROOT / 'data' / rel
            temp = dst.with_name(dst.name + '.collection-material-tmp')
            temp.write_bytes((STAGE / rel).read_bytes())
            temp.replace(dst)
        verify(ROOT / 'data')


if __name__ == '__main__':
    main()
