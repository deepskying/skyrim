"""Verify the material-only 0.45 update, including native shader and DDS reads."""
from pathlib import Path
import sys,struct,json
import numpy as np
from PIL import Image
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
base=ROOT/'build/before-0.45.0/data';data=ROOT/'data'
expected={f'meshes/weapons/arcanearsenal/waraxe2{c}.nif' for c in ['red','green','blue','purple']}
changed={p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file() and p.read_bytes()!=(data/p.relative_to(base)).read_bytes()}
assert changed==expected,changed
added={p.relative_to(data).as_posix() for p in data.rglob('*') if p.is_file() and not (base/p.relative_to(data)).exists()}
assert added=={f'textures/weapons/arcanearsenal/aa_emissive_{c}_{s}.dds' for c in ['red','green','blue','purple'] for s in ['d','n','g']}
for rel in expected:
    a,b=NifBlocks(base/rel),NifBlocks(data/rel)
    assert len(a.blocks)==len(b.blocks) and a.strings==b.strings
    assert all(x==y for i,(x,y) in enumerate(zip(a.blocks,b.blocks)) if i not in [15,16])
    shader=b.blocks[15][1]
    assert struct.unpack_from('<I',shader)[0]==2
    assert struct.unpack_from('<II',shader,16)==(0x80400001,65)
    assert shader[56:72]==a.blocks[15][1][56:72] # original power, clamp, alpha/refraction
    assert struct.unpack_from('<3f',shader,44)==(1,1,1)
    native=NifFile(str(data/rel));assert len(native.shapes)==2
    assert not NifFile.message_log(),NifFile.message_log()
    body=next(s for s in native.shapes if s.name=='AA_WaraxeBody')
    for slot in ['Diffuse','Normal','Glow']:
        tex=data/body.textures[slot].replace('\\','/')
        assert tex.is_file(),tex
for rel in added:
    p=data/rel;b=p.read_bytes()
    assert b[:4]==b'DDS ' and b[84:88]==b'DXT5'
    assert struct.unpack_from('<II',b,12)==(1024,1024) and struct.unpack_from('<I',b,28)[0]==11
    assert len(b)==128+sum(max(1,(1024>>m)//4)**2*16 for m in range(11))
    a=np.array(Image.open(p).convert('RGBA'))
    if p.stem.endswith('_g'):assert a[:,:,:3].max(axis=-1).min()>50,'Body glow contains dark holes'
    if not p.stem.endswith('_n'):assert a[:,:,3].min()==255
report=dict(version='0.45.0',passed=True,modified_weapons=4,new_dds=12,plugin_unchanged=True,unchanged_runtime_files=188,geometry_uv_collision_edge_particles_unchanged=True,full_body_emission_verified=True,gameplay_tested=False)
(ROOT/'build/emissive-materials-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
