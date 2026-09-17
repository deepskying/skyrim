"""Non-destructive material study on the actual approved weapon geometry.

Run in the project portable Blender. No NIF, DDS, plugin or MO2 file is written.
Cycles materials below are visual proposals, not Skyrim shader implementations.
"""
from pathlib import Path
import bpy, math, json, hashlib
from mathutils import Vector, Matrix

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SOURCE=ROOT/'art/waraxe2red.blend'
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
shapes=[o for o in bpy.context.scene.objects if o.name in ('AA_WaraxeBody','AA_WaraxeEdge')]
assert len(shapes)==2
original={o.name:o.data.materials[0] for o in shapes}
for o in shapes:
    xf=o.matrix_world.copy()
    o.parent=None;o.matrix_world=Matrix.Rotation(.32,4,'Y')@xf
for o in list(bpy.context.scene.objects):
    if o not in shapes:bpy.data.objects.remove(o,do_unlink=True)

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.cycles.max_bounces=12;scene.cycles.transmission_bounces=8
scene.world=bpy.data.worlds.new('Neutral studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.075,.085,.11,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.render.resolution_percentage=100

def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def light(name,location,power,size,color,shape='DISK',size_y=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape=shape;d.size=size;d.color=color
    if size_y:d.size_y=size_y
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=location;aim(o,(-9,24,0))
light('Large soft key',(-32,58,48),42000,32,(1,.91,.83),'RECTANGLE',55)
light('Cool vertical reflection',(34,22,24),28000,9,(.68,.8,1),'RECTANGLE',55)
light('Top strip',(-10,72,12),20000,28,(1,.55,.4),'RECTANGLE',6)
light('Back rim',(-28,26,-25),35000,24,(1,.28,.16),'RECTANGLE',40)
# Neutral backing plate gives transmission a visible reference without scenery.
bpy.ops.mesh.primitive_plane_add(size=300,location=(0,20,-12))
back=bpy.context.object;back.name='Studio backing'
mat=bpy.data.materials.new('Backdrop');mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.022,.029,.043,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9
back.data.materials.append(mat)
camdata=bpy.data.cameras.new('Comparison camera');cam=bpy.data.objects.new('Comparison camera',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO'

def material(name,color,roughness,metal=0,coat=0,transmission=0,texture=None):
    m=bpy.data.materials.new(name);m.use_nodes=True
    tree=m.node_tree;n=tree.nodes;p=n['Principled BSDF']
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Coat Weight'].default_value=coat
    p.inputs['Coat Roughness'].default_value=.14
    p.inputs['Transmission Weight'].default_value=transmission
    p.inputs['IOR'].default_value=1.48
    if texture:
        coord=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY'
        mapping.inputs[1].default_value=(160,4,100) if texture=='brushed' else (35,50,35)
        tree.links.new(coord.outputs['Generated'],mapping.inputs[0])
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1
        noise.inputs['Detail'].default_value=2
        tree.links.new(mapping.outputs['Vector'],noise.inputs['Vector'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.19 if texture=='forged' else .1
        bump.inputs['Distance'].default_value=.11 if texture=='forged' else .025
        tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
        ramp=n.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(*[v*.55 for v in color],1)
        ramp.color_ramp.elements[1].color=(*[min(v*1.4,1) for v in color],1)
        tree.links.new(noise.outputs['Fac'],ramp.inputs[0]);tree.links.new(ramp.outputs[0],p.inputs['Base Color'])
    return m

edge=material('Restrained ember bevel',(.42,.012,.02),.27,.45)
ep=edge.node_tree.nodes['Principled BSDF'];ep.inputs['Emission Color'].default_value=(1,.015,.025,1)
ep.inputs['Emission Strength'].default_value=.65
def patterned(name,kind):
    m=material(name,(.013,.005,.008),.19,.08,.85)
    t=m.node_tree;n=t.nodes;p=n['Principled BSDF']
    coord=n.new('ShaderNodeTexCoord')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4
    noise.inputs['Detail'].default_value=3
    t.links.new(coord.outputs['Generated'],noise.inputs['Vector'])
    if kind=='cracks':
        vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=6
        t.links.new(coord.outputs['Generated'],vor.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.009
        ramp.color_ramp.elements[0].color=(.46,.008,.012,1)
        ramp.color_ramp.elements[1].position=.025;ramp.color_ramp.elements[1].color=(.009,.003,.006,1)
        t.links.new(vor.outputs['Distance'],ramp.inputs[0]);t.links.new(ramp.outputs[0],p.inputs['Base Color'])
        t.links.new(ramp.outputs[0],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.6
        bump=n.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.025
        t.links.new(vor.outputs['Distance'],bump.inputs['Height']);t.links.new(bump.outputs[0],p.inputs['Normal'])
    elif kind=='onyx':
        wave=n.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='DIAGONAL'
        wave.inputs['Scale'].default_value=5;wave.inputs['Distortion'].default_value=8
        wave.inputs['Detail'].default_value=3;wave.inputs['Detail Scale'].default_value=1.4
        t.links.new(coord.outputs['Generated'],wave.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.38;ramp.color_ramp.elements[0].color=(.005,.003,.005,1)
        ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.22,.009,.02,1)
        t.links.new(wave.outputs['Color'],ramp.inputs[0]);t.links.new(ramp.outputs[0],p.inputs['Base Color'])
    elif kind=='meteor':
        p.inputs['Metallic'].default_value=.82;p.inputs['Roughness'].default_value=.36;p.inputs['Coat Weight'].default_value=.1
        vor=n.new('ShaderNodeTexVoronoi');vor.inputs['Scale'].default_value=48
        t.links.new(coord.outputs['Generated'],vor.inputs['Vector'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.42;bump.inputs['Distance'].default_value=.14
        t.links.new(vor.outputs['Distance'],bump.inputs['Height']);t.links.new(bump.outputs[0],p.inputs['Normal'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.008,.01,.017,1);ramp.color_ramp.elements[1].color=(.09,.1,.13,1)
        t.links.new(noise.outputs['Fac'],ramp.inputs[0]);t.links.new(ramp.outputs[0],p.inputs['Base Color'])
    return m

gold=material('Gold bevel with ember glow',(.52,.27,.055),.23,.95)
gp=gold.node_tree.nodes['Principled BSDF'];gp.inputs['Emission Color'].default_value=(1,.014,.018,1);gp.inputs['Emission Strength'].default_value=.12
variants=[
    ('01-obsidian','黑曜石（保留对照）',material('Obsidian baseline',(.014,.003,.006),.16,.08,.9),'沿用上一组你喜欢的黑曜石'),
    ('02-fractured','裂纹黑曜石',patterned('Fractured obsidian','cracks'),'黑色镜面上点缀细红色发光裂纹'),
    ('03-onyx','红纹玛瑙',patterned('Red banded onyx','onyx'),'黑底与弯曲暗红层纹，表面抛光'),
    ('04-meteor','暗陨铁',patterned('Dark meteoric iron','meteor'),'黑灰金属与细小锤蚀凹凸，保留红色亮边'),
    ('05-gold','黑金镶边',material('Black enamel gold setting',(.009,.006,.008),.23,.15,.75),'近黑主体、金色倒角，倒角保留弱红色发光'),
    ('06-smoky','烟熏黑晶',material('Smoky garnet',(.058,.011,.022),.12,0,.7,.32),'近黑酒红晶体，降低透明度，突出暗红反光'),
]
report={'weapon':'余烬·错牙','source':str(SOURCE),'source_sha256':source_hash,'geometry_changed':False,
        'renderer':'Blender Cycles','preview_only':True,'in_game_tested':False,
        'comparison':'All variants use identical geometry, camera, lights and exposure. Baseline reproduces the approved obsidian preview. Five dark alternatives use the same red bevel except black-gold, which uses a gold surface with weak red emission. All are offline Cycles proposals.',
        'variants':[]}
for key,label,mat,description in variants:
    for o in shapes:
        o.data.materials.clear()
        o.data.materials.append(original[o.name] if mat is None else (gold if key=='05-gold' else edge) if o.name.endswith('Edge') else mat)
    for mode in ('full','detail'):
        target=(-8,20,0) if mode=='full' else (-10,36,0)
        cam.location=(target[0],target[1],150);aim(cam,target)
        camdata.ortho_scale=78 if mode=='full' else 46
        scene.render.resolution_x=900;scene.render.resolution_y=1100 if mode=='full' else 900
        scene.render.filepath=str(OUT/(key+'-'+mode+'.png'))
        bpy.ops.render.render(write_still=True)
    report['variants'].append({'key':key,'name':label,'description':description,'full':key+'-full.png','detail':key+'-detail.png'})
    print('MATERIAL_PREVIEW_DONE',key,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'material-study.blend'))
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
