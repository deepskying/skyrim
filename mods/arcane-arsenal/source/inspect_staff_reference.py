import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.pynifly(filepath=str(ROOT/'build/staves-reference/staff01.nif'))
for o in bpy.context.scene.objects:
    print('STAFF_REFERENCE',o.name,o.type,dict(o.items()),list(map(list,o.matrix_world)))
    if o.type=='MESH':
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        print('BOUNDS',[(min(p[i] for p in pts),max(p[i] for p in pts)) for i in range(3)])
        for y in (-60,-40,-10,0,10,30,50):
            at=[p for p in pts if abs(p.y-y)<2]
            if at:print('SECTION',y,[(min(p[i] for p in at),max(p[i] for p in at)) for i in (0,2)])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'build/staves-reference/staff-reference.blend'))
o=bpy.data.objects['Staff01:0'];o.data.materials.clear()
m=bpy.data.materials.new('clay');m.diffuse_color=(.6,.6,.6,1);o.data.materials.append(m)
for o in bpy.context.scene.objects:
    if o.name.startswith('bhk'):o.hide_render=True
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
cd=bpy.data.cameras.new('Inspect');cam=bpy.data.objects.new('Inspect',cd);scene.collection.objects.link(cam)
cam.location=(0,-20,200);cd.type='ORTHO';cd.ortho_scale=153;scene.camera=cam
scene.render.resolution_x=500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.filepath=str(ROOT/'build/staves-reference/reference.png');bpy.ops.render.render(write_still=True)
