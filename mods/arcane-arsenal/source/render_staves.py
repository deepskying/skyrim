"""Render the authored Blender meshes, including a labelled lineup and details."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'art/staves-geometric'
specs=json.loads((ROOT/'source/staves_catalog.json').read_text(encoding='utf-8'))
for spec in specs:
    bpy.ops.wm.open_mainfile(filepath=str(ART/(spec['key']+'.blend')))
    scene=bpy.context.scene;scene.camera.rotation_euler=(0,math.atan2(22,220),0)
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/(spec['key']+'.blend')))
    scene.render.filepath=str(ART/(spec['key']+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for index,spec in enumerate(specs):
    offset=(index-1.5)*46
    with bpy.data.libraries.load(str(ART/(spec['key']+'.blend'))) as (src,dst):
        dst.objects=[n for n in src.objects if n.startswith('AA_Staff') or n==spec['key']+'_ROOT']
    for obj in dst.objects:bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()
    for obj in dst.objects:
        if obj.type=='MESH':
            matrix=Matrix.Rotation(.28,4,'Y')@obj.matrix_world;matrix.translation.x+=offset
            obj.parent=None;obj.constraints.clear();obj.matrix_world=matrix
    font=bpy.data.curves.new('name','FONT');font.body=spec['name'];font.align_x='CENTER';font.size=2.65;font.font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
    obj=bpy.data.objects.new('name',font);bpy.context.collection.objects.link(obj);obj.location=(offset,-78,0)
    mat=bpy.data.materials.new('Caption');mat.use_nodes=True
    node=mat.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=(.65,.69,.75,1)
    node.inputs['Emission Color'].default_value=(.65,.69,.75,1);node.inputs['Emission Strength'].default_value=.8
    font.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('Backdrop');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.008,.012,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('Lineup');cam=bpy.data.objects.new('Lineup',cd);scene.collection.objects.link(cam)
cam.location=(0,-3,300);cd.type='ORTHO';cd.ortho_scale=197;scene.camera=cam
scene.render.resolution_x=2200;scene.render.resolution_y=1900;scene.render.resolution_percentage=100
scene.render.filepath=str(ART/'staves-lineup.png');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ART/'staves-lineup.blend'));bpy.ops.render.render(write_still=True)
cam.location=(0,45,300);cd.ortho_scale=197
scene.render.resolution_x=2400;scene.render.resolution_y=650;scene.render.filepath=str(ART/'staves-heads.png');bpy.ops.render.render(write_still=True)
