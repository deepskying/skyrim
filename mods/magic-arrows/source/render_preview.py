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
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
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

for row,spec in enumerate(SPECS):
    path=MESH/(spec['key']+'_flight.nif');nf=NifFile(str(path));raw=NifBlocks(path)
    for shape in nf.shapes:
        transform=xf(shape);vs=[]
        for v in shape.verts:
            w=transform@Vector(v);vs.append((w.y+28,w.x+15-row*16,w.z))
        mesh=bpy.data.meshes.new(shape.name);mesh.from_pydata(vs,[],shape.tris);mesh.update()
        ob=bpy.data.objects.new(shape.name,mesh);scene.collection.objects.link(ob)
        cat=shape.name.rsplit('_',1)[-1]
        mat=bpy.data.materials.new(shape.name);mat.use_nodes=True
        ns=mat.node_tree.nodes;ns.clear();out=ns.new('ShaderNodeOutputMaterial')
        em=ns.new('ShaderNodeEmission');color=spec['core'] if cat=='core' else spec['color']
        em.inputs[0].default_value=(*color,1);em.inputs[1].default_value={'body':1.0,'core':1.25}[cat]
        mat.node_tree.links.new(em.outputs[0],out.inputs[0]);mesh.materials.append(mat)
    label(spec['name'],(-31,20-row*16,2),2.2,spec['color'])
label('魔法箭 · 游戏模型预览',(-32,29,2),2.6,(.75,.8,.9))
label('实际导出网格 / 辉光为预览近似 / 粒子需进游戏观察',(-32,-28,2),1.0,(.36,.4,.5))
camera=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(cam)
cam.location=(0,1,120);cam.rotation_euler=(0,0,0);camera.type='ORTHO';camera.ortho_scale=110;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layers=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.8;glare.size=7
out=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layers.outputs['Image'],glare.inputs['Image']);scene.node_tree.links.new(glare.outputs['Image'],out.inputs[0])
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'art/three-arrows-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/three-arrows-preview.blend'))
bpy.ops.render.render(write_still=True)
print('PREVIEW_COMPLETE')
