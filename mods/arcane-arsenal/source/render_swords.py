"""Render saved source models and a labelled lineup; never invent in-game results."""
import bpy,math,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SERIES='swords'
specs=json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8'))
for spec in ([] if '--lineup-only' in sys.argv else specs):
    key=spec['key'];bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art'/(key+'.blend')))
    scene=bpy.context.scene;scene.camera.rotation_euler=(0,math.atan2(30,230),0)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art'/(key+'.blend')))
    scene.render.filepath=str(ROOT/'art'/(key+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for index,spec in enumerate(specs):
    offset=(index-1.5)*32
    with bpy.data.libraries.load(str(ROOT/'art'/(spec['key']+'.blend'))) as (src,dst):
        dst.objects=[n for n in src.objects if n.startswith('AA_Sword') or n==spec['key']+'_ROOT']
    for obj in dst.objects:
        bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()
    for obj in dst.objects:
        if obj.type=='MESH':
            matrix=obj.matrix_world.copy();matrix.translation.x+=offset
            obj.parent=None;obj.constraints.clear();obj.matrix_world=matrix
    font=bpy.data.curves.new('name','FONT');font.body=spec['name'];font.align_x='CENTER';font.size=1.8;font.font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
    label=bpy.data.objects.new('name',font);bpy.context.collection.objects.link(label);label.location=(offset,-21,0)
    m=bpy.data.materials.new('label');m.diffuse_color=(.65,.65,.65,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(.5,.5,.5,1);m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.8;font.materials.append(m)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('Backdrop');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.008,.012,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('Lineup');cam=bpy.data.objects.new('Lineup',cd);scene.collection.objects.link(cam);cam.location=(0,25,300);cam.rotation_euler=(0,0,0);cd.type='ORTHO';cd.ortho_scale=139;scene.camera=cam
scene.render.resolution_x=2100;scene.render.resolution_y=1650;scene.render.resolution_percentage=100;scene.cycles.samples=24
scene.render.filepath=str(ROOT/'art'/(SERIES+'-lineup.png'));bpy.ops.render.render(write_still=True)
