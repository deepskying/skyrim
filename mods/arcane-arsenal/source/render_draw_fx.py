"""Actual mesh preview, with the runtime hidden node explicitly shown for inspection."""
from pathlib import Path
import bpy, math, json
from mathutils import Vector, Matrix
from io_scene_nifly.pyn.pynifly import NifFile
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/redplates.blend'))
nif=NifFile(str(ROOT/'build/redplates-fx-visible.nif'))
shape=next(s for s in nif.shapes if s.name=='AAHexagramLight')
report=json.loads((ROOT/'build/draw-fx-model.json').read_text(encoding='utf-8'))
mesh=bpy.data.meshes.new('Exported hexagram geometry');mesh.from_pydata(shape.verts,[],shape.tris);mesh.update()
obj=bpy.data.objects.new('Draw effect shown for preview',mesh);bpy.context.scene.collection.objects.link(obj)
obj.location=report['center']
mat=bpy.data.materials.new('Pure red effect preview');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();emission=nodes.new('ShaderNodeEmission')
emission.inputs['Color'].default_value=(1,0,0,1);emission.inputs['Strength'].default_value=.48
out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface']);obj.data.materials.append(mat)
scene=bpy.context.scene;cam=scene.camera
cam.location=(190,25,-155)
forward=(Vector((0,0,0))-cam.location).normalized()
right=forward.cross(Vector((0,1,0))).normalized();up=right.cross(forward)
cam.rotation_euler=Matrix((right,up,-forward)).transposed().to_euler()
cam.data.ortho_scale=124;scene.render.resolution_x=1050;scene.render.resolution_y=1400
scene.cycles.samples=24
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/redplates-draw-fx.blend'))
for visible,label in ((False,'idle'),(True,'active')):
    obj.hide_render=not visible
    scene.render.filepath=str(ROOT/f'art/redplates-fx-{label}.png');bpy.ops.render.render(write_still=True)
