"""24 actual source models, organized by shape and color; no simulated particles."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1]
specs=json.loads((ROOT/'source/geometric_catalog.json').read_text(encoding='utf-8'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;font=bpy.data.fonts.load(r'C:\Windows\Fonts\msyh.ttc')
for i,spec in enumerate(specs):
    key=spec['key'];x=150-(i//4)*60;y=202.5-(i%4)*135
    with bpy.data.libraries.load(str(ROOT/'art'/(key+'.blend'))) as (available,loaded):
        loaded.objects=[name for name in available.objects if name.startswith('AA_Geometric') or name in (key+'_ROOT',key+'_Rig')]
    for obj in loaded.objects:
        scene.collection.objects.link(obj)
        if obj.parent is None:obj.location.x+=x;obj.location.y+=y
    text=bpy.data.curves.new(key+'_label','FONT');text.body=spec['name'];text.font=font;text.align_x='CENTER';text.size=3.4
    obj=bpy.data.objects.new(key+'_label',text);scene.collection.objects.link(obj);obj.location=(x,y-62,0);obj.rotation_euler=(0,math.pi,0)
    mat=bpy.data.materials.new(key+'_label');mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.5,.5,.5,1);shader.inputs['Emission Color'].default_value=(.5,.5,.5,1);shader.inputs['Emission Strength'].default_value=.7;text.materials.append(mat)
cd=bpy.data.cameras.new('Geometric collection');cam=bpy.data.objects.new('Geometric collection',cd);scene.collection.objects.link(cam);cam.location=(0,-3,-500);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=560;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=2400;scene.render.resolution_y=3600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.004,.004,.004,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.1
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layer=nodes.new('CompositorNodeRLayers');output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/geometric-bows-lineup.blend'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/geometric-bows-lineup.blend'))
scene=bpy.context.scene
scene.render.filepath=str(ROOT/'art/geometric-bows-lineup.png');bpy.ops.render.render(write_still=True)
angles={'Bow_LoBone1':12,'Bow_LoBone2':18,'Bow_UpBone1':-12,'Bow_UpBone2':-18,'Bow_StringBone1':-30,'Bow_StringBone2':30}
for obj in scene.objects:
    if obj.type=='ARMATURE':
        for bone in obj.pose.bones:bone.matrix_basis=bone.matrix_basis@Matrix.Rotation(math.radians(angles.get(bone.name,0)),4,'Z')
bpy.context.view_layer.update();scene.render.filepath=str(ROOT/'art/geometric-bows-flex.png');bpy.ops.render.render(write_still=True)
