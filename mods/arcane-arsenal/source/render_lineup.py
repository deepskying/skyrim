"""Render the collection's actual Blender weapon meshes for visual review."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
chinese_font=bpy.data.fonts.load(r'C:\Windows\Fonts\msyh.ttc')
for index,spec in enumerate(catalog):
    key=spec['key'];offset=(len(catalog)-1)*30-index*60
    with bpy.data.libraries.load(str(ROOT/'art'/(key+'.blend'))) as (available,loaded):
        loaded.objects=[name for name in available.objects if name.startswith('AA_') or name in (key+'_ROOT',key+'_Rig')]
    for obj in loaded.objects:
        scene.collection.objects.link(obj)
        if obj.parent is None:obj.location.x+=offset
    font=bpy.data.curves.new(key+'_label','FONT');font.body=spec['name'];font.align_x='CENTER';font.size=3.0
    font.font=chinese_font
    text=bpy.data.objects.new(key+'_label',font);scene.collection.objects.link(text)
    text.location=(offset,-77,-3);text.rotation_euler=(0,math.pi,0)
    mat=bpy.data.materials.new(key+'_label');mat.diffuse_color=(.72,.78,.85,1);font.materials.append(mat)
def aim(obj,at):
    f=(Vector(at)-obj.location).normalized();r=f.cross(Vector((0,1,0))).normalized();up=r.cross(f)
    obj.rotation_euler=Matrix((r,up,-f)).transposed().to_quaternion().to_euler()
cd=bpy.data.cameras.new('Lineup camera');cam=bpy.data.objects.new('Lineup camera',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-260);aim(cam,(0,0,0));cd.type='ORTHO';cd.ortho_scale=60*len(catalog)+45;scene.camera=cam
# Blender orthographic scale is the horizontal span for landscape frames.
for name,loc,power,size in [('Key',(-80,60,-95),800000,120),('Rim',(30,55,55),650000,110),('Fill',(80,-45,-65),550000,110)]:
    ld=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,ld);scene.collection.objects.link(obj);obj.location=loc;ld.energy=power;ld.shape='DISK';ld.size=size;aim(obj,(0,0,0))
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.025,.029,.04,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=460*len(catalog);scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'art/arcane-arsenal-lineup.png')
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/arcane-arsenal-lineup.blend'))
# Reopen the assembled scene so appended armatures rebuild their render caches
# using the display offsets instead of their source-file object transforms.
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/arcane-arsenal-lineup.blend'))
bpy.ops.render.render(write_still=True)
