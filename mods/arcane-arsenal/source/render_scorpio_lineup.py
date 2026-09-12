"""Actual new game meshes, plus an optional controlled-flex inspection image."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1]
catalog=[s for s in json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8')) if s['key'].startswith('scorpio')]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;font=bpy.data.fonts.load(r'C:\Windows\Fonts\msyh.ttc')
for i,spec in enumerate(catalog):
    key=spec['key'];offset=72-i*48
    with bpy.data.libraries.load(str(ROOT/'art'/(key+'.blend'))) as (available,loaded):
        loaded.objects=[name for name in available.objects if name.startswith('AA_') or name in (key+'_ROOT',key+'_Rig')]
    for obj in loaded.objects:
        scene.collection.objects.link(obj)
        if obj.parent is None:obj.location.x+=offset
    text=bpy.data.curves.new(key+'_label','FONT');text.body=spec['name'];text.font=font;text.align_x='CENTER';text.size=2.2
    obj=bpy.data.objects.new(key+'_label',text);scene.collection.objects.link(obj);obj.location=(offset,-66,0);obj.rotation_euler=(0,math.pi,0)
    mat=bpy.data.materials.new(key+'_label');mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.5,.5,.5,1);shader.inputs['Emission Color'].default_value=(.5,.5,.5,1);shader.inputs['Emission Strength'].default_value=.7;text.materials.append(mat)
cd=bpy.data.cameras.new('Red collection');cam=bpy.data.objects.new('Red collection',cd);scene.collection.objects.link(cam);cam.location=(0,-3,-320);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=210;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=2100;scene.render.resolution_y=1550;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.004,.004,.004,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.1
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.03;glare.size=7;glare.mix=-.80;output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/scorpio-bows-lineup.blend'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/scorpio-bows-lineup.blend'))
scene=bpy.context.scene;scene.render.filepath=str(ROOT/'art/scorpio-bows-lineup.png');bpy.ops.render.render(write_still=True)
# This is a controlled pose, not an assertion that it is the game's full-draw animation.
angles={'Bow_LoBone1':12,'Bow_LoBone2':18,'Bow_UpBone1':-12,'Bow_UpBone2':-18,'Bow_StringBone1':-30,'Bow_StringBone2':30}
for obj in bpy.data.objects:
    if obj.type=='ARMATURE':
        for bone in obj.pose.bones:bone.matrix_basis=bone.matrix_basis@Matrix.Rotation(math.radians(angles.get(bone.name,0)),4,'Z')
bpy.context.view_layer.update();scene.render.filepath=str(ROOT/'art/scorpio-bows-flex.png');bpy.ops.render.render(write_still=True)
