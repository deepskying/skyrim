"""Prepare a lossless full-body material patch against an isolated release.

Usage: python source/apply_collection_materials.py [--verify]
The stage has baseline/, data/ and catalog.json. Does not modify live data.
Only body/fold lighting shaders and their texture sets may change. Original
emission powers, alpha, UV transforms, skinning, strings and particle data stay.
"""
from pathlib import Path
import json,struct,sys,hashlib
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'build/all-materials-stage';BASE=STAGE/'baseline';DATA=STAGE/'data'
CAT=json.loads((STAGE/'catalog.json').read_text(encoding='utf-8'))
MESH=Path('meshes/weapons/arcanearsenal');verify='--verify' in sys.argv
prefixes={'余烬':'red','流萤':'green','寒汐':'blue','梦隙':'purple'}
def shapes(n):
    result=[]
    for i,(kind,b) in enumerate(n.blocks):
        if kind!='BSTriShape':continue
        name=n.strings[struct.unpack_from('<I',b)[0]].decode()
        si=struct.unpack_from('<I',b,92)[0];ti=struct.unpack_from('<I',n.blocks[si][1],40)[0]
        result.append((name,si,ti))
    return result
refs={}
for c in prefixes.values():
    n=NifBlocks(BASE/MESH/('waraxe2'+c+'.nif'))
    _,si,ti=next(v for v in shapes(n) if v[0].endswith('Body'))
    refs[c]=(n.blocks[si][1],n.blocks[ti])
reports=[]
for spec in CAT:
    if spec.get('series')=='material_trials':continue
    key=spec['key'];color=prefixes[spec['name'].split('·')[0]]
    rel=MESH/(key+'.nif');old=NifBlocks(BASE/rel);new=NifBlocks(BASE/rel)
    targets=[v for v in shapes(old) if v[0].endswith(('Body','Fold'))]
    assert targets,key
    protected={i for name,si,ti in shapes(old) if not name.endswith(('Body','Fold')) for i in [si,ti]}
    touched=set()
    for name,si,ti in targets:
        assert not {si,ti}&protected,(key,name,'shared protected shader')
        sh=bytearray(old.blocks[si][1]);approved,tex=refs[color]
        assert len(sh)==100 and struct.unpack_from('<I',sh)[0]==2
        # Bows require the SKINNED flag (bit 1); do not copy rigid-axe flags.
        struct.pack_into('<I',sh,16,struct.unpack_from('<I',sh,16)[0]|1)
        sh[44:56]=approved[44:56];sh[72:92]=approved[72:92]
        new.blocks[si]=('BSLightingShaderProperty',bytes(sh));new.blocks[ti]=tex;touched|={si,ti}
    if not verify:new.save(DATA/rel)
    actual=NifBlocks(DATA/rel)
    assert actual.blocks==new.blocks and actual.strings==old.strings
    assert len(actual.blocks)==len(old.blocks)
    assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,actual.blocks)) if i not in touched)
    for _,si,ti in targets:
        assert old.blocks[si][1][20:44]==actual.blocks[si][1][20:44] and old.blocks[si][1][56:72]==actual.blocks[si][1][56:72]
        assert struct.unpack_from('<I',actual.blocks[si][1],16)[0]==struct.unpack_from('<I',old.blocks[si][1],16)[0]|1
    changed=(BASE/rel).read_bytes()!=(DATA/rel).read_bytes()
    reports.append(dict(key=key,name=spec['name'],color=color,changed=changed,allowed_blocks=sorted(touched),sha256=hashlib.sha256((DATA/rel).read_bytes()).hexdigest()))
assert len(reports)==156
files={p.relative_to(BASE) for p in BASE.rglob('*') if p.is_file()}
assert files=={p.relative_to(DATA) for p in DATA.rglob('*') if p.is_file()}
expected={MESH/(r['key']+'.nif') for r in reports if r['changed']}
assert {p for p in files if (BASE/p).read_bytes()!=(DATA/p).read_bytes()}==expected
if verify:
    sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
    from pyn.pynifly import NifFile
    for r in reports:
        n=NifFile(str(DATA/MESH/(r['key']+'.nif')));assert not NifFile.message_log()
        for shape in n.shapes:
            if shape.name.endswith(('Body','Fold')):
                for slot in ['Diffuse','Normal','Glow']:assert (DATA/shape.textures[slot].replace('\\','/')).is_file()
report=dict(verified=verify,covered=156,changed=len(expected),untouched_runtime_files=len(files)-len(expected),weapons=reports,geometry_skinning_uv_collision_edges_strings_particles_preserved=True,gameplay_tested=False)
(STAGE/('verification.json' if verify else 'manifest.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='weapons'}))
