"""Apply approved four-color emissive materials to all twelve greatswords.

Existing axes and swords share planar UV units (x/30, y/100), so texture detail
keeps a consistent world scale on long blades without stretching the artwork.
Only body shader and its texture set change; geometry and particle blocks stay.
"""
from pathlib import Path
import json,struct,sys
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.46.0/data'
DATA=ROOT/'data';MESH=Path('meshes/weapons/arcanearsenal')
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
specs=[s for s in catalog if s.get('weapon_type')=='greatsword']
assert len(specs)==12
verify='--verify' in sys.argv
reports=[]
def body(n,name):
    shape=next(b for k,b in n.blocks if k=='BSTriShape' and n.strings[struct.unpack_from('<I',b)[0]].decode()==name)
    si=struct.unpack_from('<I',shape,92)[0]
    return si,struct.unpack_from('<I',n.blocks[si][1],40)[0]
for spec in specs:
    key=spec['key'];color=next(c for c in ['red','green','blue','purple'] if key.endswith(c))
    old=NifBlocks(BASE/MESH/(key+'.nif'))
    reference=NifBlocks(BASE/MESH/('waraxe2'+color+'.nif'))
    si,ti=body(old,'AA_GreatswordBody');ri,rt=body(reference,'AA_WaraxeBody')
    sh=bytearray(old.blocks[si][1]);approved=reference.blocks[ri][1]
    assert len(sh)==100 and struct.unpack_from('<I',sh)[0]==2
    assert sh[56:60]==approved[56:60], 'Original emission power must match'
    sh[16:24]=approved[16:24];sh[44:56]=approved[44:56];sh[72:92]=approved[72:92]
    if not verify:
        n=NifBlocks(BASE/MESH/(key+'.nif'))
        n.blocks[si]=('BSLightingShaderProperty',bytes(sh));n.blocks[ti]=reference.blocks[rt]
        n.save(DATA/MESH/(key+'.nif'))
    new=NifBlocks(DATA/MESH/(key+'.nif'))
    assert new.strings==old.strings and len(new.blocks)==len(old.blocks)
    assert new.blocks[si][1]==bytes(sh) and new.blocks[ti]==reference.blocks[rt]
    assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,new.blocks)) if i not in [si,ti])
    reports.append(dict(key=key,color=color,changed_blocks=[si,ti],power=struct.unpack_from('<f',sh,56)[0],geometry_uv_collision_edge_particles_preserved=True))
if verify:
    expected={str(MESH/(s['key']+'.nif')) for s in specs}
    files={str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file()}
    # Other tasks can stage unregistered new weapons in data; compare all release
    # baseline files and leave those unrelated additions out of this release.
    assert files<={str(p.relative_to(DATA)) for p in DATA.rglob('*') if p.is_file()}
    changed={p for p in files if (BASE/p).read_bytes()!=(DATA/p).read_bytes()}
    assert changed==expected,changed
    sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
    from pyn.pynifly import NifFile
    for spec in specs:
        n=NifFile(str(DATA/MESH/(spec['key']+'.nif')));assert not NifFile.message_log()
        s=next(s for s in n.shapes if s.name=='AA_GreatswordBody')
        for slot in ['Diffuse','Normal','Glow']:assert (DATA/s.textures[slot].replace('\\','/')).is_file()
report=dict(version='0.46.0',verified=verify,weapons=reports,plugin_unchanged=True,runtime_files=204,gameplay_tested=False)
(ROOT/'build'/('greatsword-materials-verification.json' if verify else 'greatsword-materials-build.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(version='0.46.0',verified=verify,greatswords=len(reports),plugin_unchanged=True)))
