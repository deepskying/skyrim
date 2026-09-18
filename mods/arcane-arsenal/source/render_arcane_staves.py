"""Render the exported design sources together, without an AI image pass."""
import bpy,math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'art/arcane-staves'
bpy.ops.wm.read_factory_settings(use_empty=True)
specs=json.loads((ROOT/'source/arcane_staves_catalog.json').read_text(encoding='utf-8'))
for i,s in enumerate(specs):
    with bpy.data.libraries.load(str(ART/(s['key']+'.blend')),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n.startswith('AA_Staff')]
    for o in dst.objects:
        bpy.context.collection.objects.link(o);o.parent=None;o.location.x+=(i-1.5)*31
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('Background');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.012,.02,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam)
cam.location=(45,2,320);cam.rotation_euler=(0,math.atan2(45,320),0);camdata.type='ORTHO';camdata.ortho_scale=170;scene.camera=cam
scene.render.resolution_x=1400;scene.render.resolution_y=1550;scene.render.resolution_percentage=100
font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
for i,s in enumerate(specs):
    curve=bpy.data.curves.new(s['key'],'FONT');curve.body=s['name'];curve.font=font;curve.align_x='CENTER';curve.size=2.7
    o=bpy.data.objects.new('Name',curve);scene.collection.objects.link(o);o.location=((i-1.5)*31,-77,0)
    mat=bpy.data.materials.new('Caption');mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.7,.7,.75,1);bsdf.inputs['Emission Color'].default_value=(.7,.7,.75,1);bsdf.inputs['Emission Strength'].default_value=1
    o.data.materials.append(mat)
scene.render.filepath=str(ART/'lineup.png');bpy.ops.render.render(write_still=True)
