"""Render final NIF/DDS geometry, including rear grip and an unlit glow inspection."""
from pathlib import Path
import bpy,sys,struct,json,math
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
from apply_approved_sword_materials import shapes,texture_paths
CATALOG=json.loads((ROOT/'source/shields_catalog.json').read_text('utf-8'))
ART=ROOT/'art/shields';ART.mkdir(exist_ok=True)

def aim(o,p):
    forward=(Vector(p)-o.location).normalized();right=forward.cross(Vector((0,1,0))).normalized();up=right.cross(forward)
    o.rotation_euler=Matrix((right,up,-forward)).transposed().to_euler()
for spec in CATALOG:
    key=spec['key'];path=ROOT/'data/meshes/armor/arcanearsenal'/(key+'.nif')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    n=NifBlocks(path);parts=shapes(n)
    bpy.ops.import_scene.pynifly(filepath=str(path))
    meshes=[o for o in bpy.context.scene.objects if o.name in parts]
    assert len(meshes)==4
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o not in meshes:o.hide_render=True
    for o in meshes:
        si,ti=parts[o.name];shader=n.blocks[si][1];tex=texture_paths(n.blocks[ti][1])
        mat=bpy.data.materials.new(key+o.name);mat.use_nodes=True;tree=mat.node_tree;bsdf=tree.nodes['Principled BSDF']
        nodes=[]
        for slot in range(3):
            t=tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'data'/tex[slot]),check_existing=True);nodes.append(t)
        tree.links.new(nodes[0].outputs['Color'],bsdf.inputs['Base Color'])
        nodes[1].image.colorspace_settings.name='Non-Color';normal=tree.nodes.new('ShaderNodeNormalMap')
        tree.links.new(nodes[1].outputs['Color'],normal.inputs['Color']);tree.links.new(normal.outputs[0],bsdf.inputs['Normal'])
        mix=tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
        mix.inputs[2].default_value=(*struct.unpack_from('<3f',shader,44),1)
        tree.links.new(nodes[2].outputs['Color'],mix.inputs[1]);tree.links.new(mix.outputs[0],bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value=struct.unpack_from('<f',shader,56)[0]
        bsdf.inputs['Roughness'].default_value=.33 if 'Grip' not in o.name else .75
        bsdf.inputs['Metallic'].default_value=.65 if 'Metal' in o.name else .1
        o.data.materials.clear();o.data.materials.append(mat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.world=bpy.data.worlds.new('Shield studio');scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.045,.05,.065,1);bg.inputs[1].default_value=.4
    scene.view_settings.view_transform='AgX'
    lights=[]
    for name,pos,power in [('Key',(-65,90,-95),22000),('Fill',(65,0,-50),10000),('Rear',(-45,35,90),18000)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=45
        o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=pos;aim(o,(0,-6,0));lights.append(o)
    data=bpy.data.cameras.new('Shield Camera');cam=bpy.data.objects.new('Shield Camera',data);scene.collection.objects.link(cam)
    data.type='ORTHO';data.ortho_scale=86;scene.camera=cam
    scene.render.resolution_x=900;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    for label,pos in [('front',(33,-6,-180)),('back',(-50,0,175)),('glow',(33,-6,-180))]:
        if label=='glow':
            for light in lights:light.data.energy=0
            bg.inputs[1].default_value=.025
        cam.location=pos;aim(cam,(0,-6,0));scene.render.filepath=str(ART/(key+'-'+label+'.png'))
        bpy.ops.render.render(write_still=True)
    print('SHIELD_RENDERED',key,flush=True)
