"""Append an independent hidden hexagram to the verified redplates NIF.

Run in portable Blender. Runtime node is rigid and parented to Bow_MidBone,
so SKSE can scale it independently without touching skinned weapon geometry.
"""
from pathlib import Path
import sys, math, json
import bpy
from mathutils import Vector, Matrix
from io_scene_nifly.pyn.pynifly import NifFile
from io_scene_nifly.pyn.nifdefs import TransformBuf, PynBufferTypes, ShaderFlags1

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.4.1/redplates.nif'
if '--' in sys.argv:
    BASE=Path(sys.argv[sys.argv.index('--')+1]).resolve()
DEST=ROOT/'data/meshes/weapons/arcanearsenal/redplates.nif'
assert BASE.is_file(), 'Keep the pre-experiment model as the reproducible input.'
nif=NifFile(str(BASE))
old_shapes=list(nif.shapes)
assert not any(s.name=='AAHexagramLight' for s in old_shapes), 'Input must be the base bow without draw FX.'
mid=nif.nodes['Bow_MidBone']
# Hexagram stands perpendicular to the arrow direction (X), centered just above
# the hand and forward of the grip. Its hollow center leaves the arrow lane clear.
center=Vector((11.0,4.8,0.0));radius=12.0
rotation=Matrix([list(row) for row in mid.transform.rotation])
inv=rotation.inverted()
local=inv@(center-Vector(mid.transform.translation))
xf=TransformBuf();xf.store(local,inv,(1,1,1));xf.scale=0.0
node=nif.add_node('AAHexagramDrawFX',xf,parent=mid)
verts=[];tris=[];uvs=[];normals=[]
def rail(a,b,width=.16):
    tangent=(b-a).normalized();axis=Vector((1,0,0));side=tangent.cross(axis).normalized()
    offset=len(verts);sides=8
    for p in (a,b):
        for j in range(sides):
            normal=math.cos(j*math.tau/sides)*axis+math.sin(j*math.tau/sides)*side
            verts.append(tuple(p+width*normal));normals.append(tuple(normal));uvs.append((.5,.5))
    for j in range(sides):
        a0=offset+j;a1=offset+(j+1)%sides
        tris.extend([(a0,a1,a1+sides),(a0,a1+sides,a0+sides)])
    for j in range(1,sides-1):
        tris.extend([(offset,offset+j+1,offset+j),(offset+sides,offset+sides+j,offset+sides+j+1)])
for phase in (math.pi/2,-math.pi/2):
    p=[Vector((0,radius*math.sin(phase+j*math.tau/3),radius*math.cos(phase+j*math.tau/3))) for j in range(3)]
    for a,b in zip(p,p[1:]+p[:1]):rail(a,b)
shape=nif.createShapeFromData('AAHexagramLight',verts,tris,uvs,normals,
    use_type=PynBufferTypes.BSTriShapeBufType,parent=node)
source=next(s for s in old_shapes if s.name=='AA_redline')
props=shape.shader.properties
for field in ('Shader_Type','Shader_Flags_1','Shader_Flags_2','Emissive_Mult','Glossiness','Alpha'):
    setattr(props,field,getattr(source.shader.properties,field))
props.Shader_Flags_1 &= ~int(ShaderFlags1.SKINNED)
props.Emissive_Color[:3]=(1,0,0)
props.Emissive_Mult=8.0
props.Spec_Color[:]=(0,0,0)
shape.save_shader_attributes()
for slot,path in source.textures.items():
    if path:shape.set_texture(slot,path)
nif.filepath=str(DEST);nif.save()

# Read back actual exported bytes, not the in-memory construction.
check=NifFile(str(DEST));_ = check.shapes
fx=check.nodes['AAHexagramDrawFX'];light=next(s for s in check.shapes if s.name=='AAHexagramLight')
assert fx.parent.name=='Bow_MidBone' and fx.transform.scale==0
assert light.parent.name==fx.name and not light.has_skin_instance
assert len(light.tris)==len(tris)
assert not (light.shader.properties.Shader_Flags_1 & int(ShaderFlags1.SKINNED))
assert list(light.shader.properties.Emissive_Color)[:3]==[1,0,0]
assert light.shader.properties.Emissive_Mult==8
assert light.textures==source.textures
assert all((Vector(verts[b])-Vector(verts[a])).cross(Vector(verts[c])-Vector(verts[a])).length>1e-7 for a,b,c in tris)
# Verify the visible node maps its center and all three axes to bow coordinates.
assert (rotation@Vector(xf.translation)+Vector(mid.transform.translation)-center).length<.001
assert max(abs((rotation@inv)[i][j]-(1 if i==j else 0)) for i in range(3) for j in range(3))<.001
for original in old_shapes:
    actual=next(s for s in check.shapes if s.name==original.name)
    assert actual.verts==original.verts and actual.tris==original.tris
for name,original in nif.nodes.items():
    if name.startswith('Bow_'):
        assert check.nodes[name].transform.NearEqual(original.transform)
report={'version':'0.4.1','weapon':'AAredplates','node':fx.name,'parent':fx.parent.name,
        'hidden_by_default':True,'skinned':False,'triangles':len(tris),'center':list(center),
        'radius':radius,'emission':8,'old_geometry_unchanged':True,'gameplay_tested':False}
(ROOT/'build/draw-fx-model.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Preserve an actual-model preview with visible FX, without altering the runtime.
visible=fx.transform;visible.scale=1;fx.transform=visible
check.filepath=str(ROOT/'build/redplates-fx-visible.nif');check.save()
print(json.dumps(report))
