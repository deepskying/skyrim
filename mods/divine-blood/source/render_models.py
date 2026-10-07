"""Render actual exported NIFs for UI cards and the review sheet."""
import sys,math,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from catalog import ROOT,catalog
sys.path.insert(0,str(ROOT.parent/'magic-arrows/source'))
from paths import ADDON
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks
import bpy
from mathutils import Vector

def camera(scene,target,scale):
    data=bpy.data.cameras.new('Camera');ob=bpy.data.objects.new('Camera',data);scene.collection.objects.link(ob)
    ob.location=Vector(target)+Vector((8,-22,7));ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=scale;scene.camera=ob
def setup(size,transparent):
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
    scene.render.resolution_x=size;scene.render.resolution_y=size;scene.render.film_transparent=transparent
    scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.025,.032,.045,1)
    scene.view_settings.view_transform='Standard';return scene
def add(row,offset):
    path=ROOT/'data/meshes/DivineBlood'/(row['key']+'.nif');nf=NifFile(str(path));raw=NifBlocks(path)
    for shape in nf.shapes:
        mesh=bpy.data.meshes.new(shape.name);mesh.from_pydata(shape.verts,[],shape.tris);mesh.update()
        uv=mesh.uv_layers.new(name='Atlas')
        for loop in mesh.loops:uv.data[loop.index].uv=shape.uvs[loop.vertex_index]
        ob=bpy.data.objects.new(shape.name,mesh);bpy.context.scene.collection.objects.link(ob);ob.location=offset
        blob=raw.blocks[struct.unpack_from('<I',raw.blocks[shape.id][1],92)[0]][1]
        length=struct.unpack_from('<I',blob,36)[0];tex=blob[40:40+length].decode();color=struct.unpack_from('<3f',blob,60+length);power=struct.unpack_from('<f',blob,76+length)[0]
        mat=bpy.data.materials.new(shape.name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
        output=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');em.inputs['Strength'].default_value=power
        image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(ROOT/'data'/tex),check_existing=True)
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*color,1)
        mat.node_tree.links.new(image.outputs['Color'],mix.inputs[1]);mat.node_tree.links.new(mix.outputs[0],em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],output.inputs['Surface']);mesh.materials.append(mat)
def render(scene,path):
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
def main():
    art=ROOT/'art/models';art.mkdir(parents=True,exist_ok=True)
    public=ROOT.parent/'durability-manager/web/public/divine-blood';public.mkdir(parents=True,exist_ok=True)
    for row in catalog():
        scene=setup(256,True);add(row,(0,0,0));camera(scene,(0,0,3),8.6);render(scene,public/(row['key']+'.png'))
    scene=setup(1600,False)
    for i,row in enumerate(catalog()):
        x=(i%4-1.5)*10;z=(3-i//4)*9
        add(row,(x,0,z))
        cu=bpy.data.curves.new(row['name'],'FONT');cu.body=row['name'];cu.size=.65;cu.align_x='CENTER';cu.font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
        ob=bpy.data.objects.new(row['name'],cu);scene.collection.objects.link(ob);ob.location=(x,-.1,z-.9);ob.rotation_euler=(math.pi/2,0,0)
        mat=bpy.data.materials.new('Label');mat.use_nodes=True
        nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(.8,.8,.8,1);mat.node_tree.links.new(em.outputs[0],out.inputs[0]);cu.materials.append(mat)
    camera(scene,(0,0,16),41)
    scene.camera.location=(0,-65,24);scene.camera.rotation_euler=(Vector((0,0,16))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=str(art/'overview.blend'));render(scene,art/'overview.png')
if __name__=='__main__':main()
