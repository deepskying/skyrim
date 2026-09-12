"""Reproducible 0.7.1 brightness-only migration from the immutable 0.7.0 snapshot.

Changes four-byte emission multipliers in place, preserving every other byte.
Native nifly independently checks the edited property values before distribution.
"""
from pathlib import Path
import json,struct,shutil,sys,math
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.7.1/data'
FACTOR=0.3
assert len(json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8')))==16, 'Historical 0.7.1 migration: do not run against newer collections.'
if not BASE.exists():shutil.copytree(ROOT/'data',BASE)
sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
reports=[]
for src in sorted(BASE.rglob('*.nif')):
    n=NifBlocks(src);data=bytearray(n.data)
    cursor=n.pos-sum(len(b) for k,b in n.blocks)
    changes=[];allowed=set()
    for i,(kind,b) in enumerate(n.blocks):
        offset=None
        if kind=='BSLightingShaderProperty':
            assert struct.unpack_from('<Ii',b,8)==(0,-1),'Unexpected shader extra data/controller'
            offset=56
        elif kind=='BSEffectShaderProperty':
            assert struct.unpack_from('<Ii',b,4)==(0,-1),'Unexpected shader extra data/controller'
            offset=76+struct.unpack_from('<I',b,36)[0]
        if offset is not None:
            old=struct.unpack_from('<f',b,offset)[0]
            assert math.isfinite(old) and old>=0
            new=old*FACTOR
            struct.pack_into('<f',data,cursor+offset,new)
            allowed.update(range(cursor+offset,cursor+offset+4))
            changes.append({'block':i,'kind':kind,'before':old,'after':new})
        cursor+=len(b)
    assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(n.data,data)))
    dest=ROOT/'data'/src.relative_to(BASE);dest.write_bytes(data)
    native=NifFile(str(dest));assert not NifFile.message_log(),NifFile.message_log()
    for change in changes:
        shader=native.read_node(id=change['block'])
        assert math.isclose(shader.properties.Emissive_Mult,change['after'],rel_tol=1e-6,abs_tol=1e-8)
    reports.append({'key':src.stem,'shaders':changes,'shape_strengths':{s.name:s.shader.properties.Emissive_Mult for s in native.shapes}})
assert len(reports)==16
for src in BASE.rglob('*'):
    if src.is_file() and src.suffix!='.nif':assert src.read_bytes()==(ROOT/'data'/src.relative_to(BASE)).read_bytes()
report={'version':'0.7.1','factor':FACTOR,'passed':True,'only_emission_bytes_changed':True,'non_mesh_runtime_unchanged':True,'models':reports}
(ROOT/'build/emission-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'models':len(reports),'shaders':sum(len(r['shaders']) for r in reports),'factor':FACTOR}))
