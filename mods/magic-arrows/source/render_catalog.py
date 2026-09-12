"""Blender preview built from the final exported NIF meshes, not concept imagery.

Material glow is approximated by Blender emission. Native particle playback and
the user's ENB/lighting need game testing and are not simulated in this preview.
"""
import sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Matrix,Vector
from paths import *
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks
from design_catalog import ALL,study
import json,math
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=2400;scene.render.resolution_y=2200;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.002,.003,.006,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.1
scene.view_settings.view_transform='Standard'
font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
def label(text,loc,size,color):
    cu=bpy.data.curves.new(text,'FONT');cu.body=text;cu.font=font;cu.size=size
    ob=bpy.data.objects.new(text,cu);scene.collection.objects.link(ob);ob.location=loc
    mat=bpy.data.materials.new(text);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(*color,1);em.inputs[1].default_value=.8
    mat.node_tree.links.new(em.outputs[0],out.inputs[0]);cu.materials.append(mat)

def xf(obj):
    t=obj.transform;mat=Matrix([list(r) for r in t.rotation]).to_4x4()
    for i in range(3):
        for j in range(3):mat[i][j]*=t.scale
    mat.translation=Vector(t.translation)
    if obj.parent:mat=xf(obj.parent)@mat
    return mat

catalog=ROOT/'art/twelve-arrow-studies';catalog.mkdir(exist_ok=True)
report=[]
for index,spec in enumerate(ALL):
    col=index%2;row=index//2;ox=-70+col*76;oy=55-row*22
    path=catalog/(spec['key']+'.nif')
    nf=NifFile();nf.initialize('SKYRIMSE',str(path))
    parts=study(spec['key'])
    for cat,m in parts.items():
        assert all(math.isfinite(c) for v in m.verts for c in v)
        assert all(-.01<=v[1]<=58.01 and abs(v[0])<=3.4 and abs(v[2])<=3.4 for v in m.verts)
        assert all(0<=i<len(m.verts) for face in m.tris for i in face)
        nf.createShapeFromData(cat,m.verts,m.tris,m.uv,m.normals())
    nf.save();nf=NifFile(str(path));assert len(nf.shapes)==2
    for shape in nf.shapes:
        vs=[(ox+58-v[1],oy+v[0],v[2]) for v in shape.verts]
        mesh=bpy.data.meshes.new(spec['key']+shape.name);mesh.from_pydata(vs,[],shape.tris);mesh.update()
        ob=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(ob)
        mat=bpy.data.materials.new(mesh.name);mat.use_nodes=True
        ns=mat.node_tree.nodes;ns.clear();out=ns.new('ShaderNodeOutputMaterial');em=ns.new('ShaderNodeEmission')
        color=spec['core'] if shape.name=='core' else spec['color']
        em.inputs[0].default_value=(*color,1);em.inputs[1].default_value=1.15 if shape.name=='core' else 1
        mat.node_tree.links.new(em.outputs[0],out.inputs[0]);mesh.materials.append(mat)
    label(f"{index+1:02d}  {spec['name']}",(ox,oy+6,3),2.1,spec['color'])
    label(spec['description'],(ox,oy-7,3),1.1,(.44,.49,.57))
    report.append(dict(key=spec['key'],name=spec['name'],file=str(path),vertices=sum(len(s.verts) for s in nf.shapes),triangles=sum(len(s.tris) for s in nf.shapes)))
label('魔法箭工坊 / 十二种箭矢造型审阅',(-70,72,3),3,(.8,.85,.92))
label('纯色发光 · 等比例网格预览 · 新增九款为造型草案，尚未安装为游戏物品',(-70,-67,3),1.2,(.44,.49,.57))
(catalog/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
camera=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(cam)
cam.location=(0,3,120);cam.rotation_euler=(0,0,0);camera.type='ORTHO';camera.ortho_scale=158;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layers=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.8;glare.size=7
out=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layers.outputs['Image'],glare.inputs['Image']);scene.node_tree.links.new(glare.outputs['Image'],out.inputs[0])
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'art/twelve-arrows-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/twelve-arrows-review.blend'))
bpy.ops.render.render(write_still=True)
print('PREVIEW_COMPLETE')
