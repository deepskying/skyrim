"""Verify the shared classic hexagram and unchanged data outside the grip emblem.

Run in Blender to read the immutable classic source as the reference geometry.
"""
import bpy,json,sys,math,collections
from pathlib import Path
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
from io_scene_nifly.pyn.pynifly import NifFile
specs=json.loads((ROOT/'source/geometric_catalog.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/geometry-templates/redplates.blend'))
# In the classic authored mesh the first six rigid rail segments form the star.
reference=[v.co.copy() for v in bpy.data.objects['AA_redline'].data.vertices[:96]]
assert len(reference)==96 and all(-4.1<v.z<-3.5 for v in reference)
base=ROOT/'build/before-0.9.1/data';reports=[];changed=set()
for spec in specs:
    key=spec['key'];rel=Path('meshes/weapons/arcanearsenal')/(key+'.nif')
    source=ROOT/'data'/rel;native=NifFile(str(source))
    edge=next(s for s in native.shapes if s.name=='AA_GeometricEdge')
    candidates=[v for v in edge.verts if abs(v[1])<8.5 and -4.1<v[2]<-3.5]
    tree=KDTree(len(candidates))
    for i,v in enumerate(candidates):tree.insert(v,i)
    tree.balance();error=max(tree.find(v)[2] for v in reference)
    assert error<.003,(key,'classic star missing',error)
    if spec['classic_source']:
        assert source.read_bytes()==(base/rel).read_bytes()
    else:
        changed.add(rel.as_posix())
        old=NifBlocks(base/rel);new=NifBlocks(source)
        assert old.strings==new.strings and len(old.blocks)==len(new.blocks)
        for (kind,a),(newkind,b) in zip(old.blocks,new.blocks):
            assert kind==newkind
            if kind not in ('NiSkinData','NiSkinPartition'):assert a==b,(key,kind)
        previous=NifFile(str(base/rel))
        for a,b in zip(previous.shapes,native.shapes):
            assert a.name==b.name
            if a.name=='AA_GeometricString':assert a.verts==b.verts and a.tris==b.tris
            # Includes all limbs and tips; leave the local grip/emblem region out.
            outside=lambda shape:collections.Counter(tuple(round(x,4) for x in v) for v in shape.verts if abs(v[1])>8.3)
            assert outside(a)==outside(b),(key,a.name,'limb vertices changed')
    reports.append({'key':key,'hexagram_error':error,'passed':True})
assert len(changed)==12
unchanged=0
for path in (ROOT/'data').rglob('*'):
    if path.is_file():
        rel=path.relative_to(ROOT/'data')
        if rel.as_posix() not in changed:assert path.read_bytes()==(base/rel).read_bytes();unchanged+=1
assert unchanged==38
report={'version':'0.9.1','passed':True,'hexagrams_verified':24,'models_changed':12,'unchanged_runtime_files':38,'material_particle_and_node_blocks_unchanged':True,'models':reports}
(ROOT/'build/hexagram-update-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEXAGRAM_UPDATE_VERIFIED 24 stars, 12 replacements, 38 unchanged runtime files')
