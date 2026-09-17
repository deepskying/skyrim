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
def ruby(name,color,roughness,transmission,kind=None):
    m=material(name,color,roughness,0,.45,transmission)
    t=m.node_tree;n=t.nodes;p=n['Principled BSDF']
    p.inputs['IOR'].default_value=1.76
    if kind:
        coord=n.new('ShaderNodeTexCoord')
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=12
        noise.inputs['Detail'].default_value=4
        t.links.new(coord.outputs['Generated'],noise.inputs['Vector'])
        if kind=='silk':
            mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(100,3,40)
            t.links.new(coord.outputs['Generated'],mapping.inputs[0]);t.links.new(mapping.outputs[0],noise.inputs['Vector'])
            noise.inputs['Scale'].default_value=1
            ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.16,.002,.014,1);ramp.color_ramp.elements[1].color=(.5,.045,.085,1)
            t.links.new(noise.outputs['Fac'],ramp.inputs[0]);t.links.new(ramp.outputs[0],p.inputs['Base Color'])
        elif kind=='frost':
            noise.inputs['Scale'].default_value=150
            bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.045
            t.links.new(noise.outputs['Fac'],bump.inputs['Height']);t.links.new(bump.outputs[0],p.inputs['Normal'])
            p.inputs['Coat Weight'].default_value=.05
        elif kind=='fracture':
            vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=10
            t.links.new(coord.outputs['Generated'],vor.inputs['Vector'])
            ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.003;ramp.color_ramp.elements[0].color=(.65,.16,.19,1)
            ramp.color_ramp.elements[1].position=.016;ramp.color_ramp.elements[1].color=(*color,1)
            t.links.new(vor.outputs['Distance'],ramp.inputs[0]);t.links.new(ramp.outputs[0],p.inputs['Base Color'])
            bump=n.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.02
            t.links.new(vor.outputs['Distance'],bump.inputs['Height']);t.links.new(bump.outputs[0],p.inputs['Normal'])
        elif kind=='inclusions':
            noise.inputs['Scale'].default_value=18
            ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.46;ramp.color_ramp.elements[0].color=(0,0,0,1)
            ramp.color_ramp.elements[1].position=.7;ramp.color_ramp.elements[1].color=(.8,.8,.8,1)
            scatter=n.new('ShaderNodeVolumeScatter');scatter.inputs['Color'].default_value=(.8,.19,.23,1);scatter.inputs['Anisotropy'].default_value=.25
            t.links.new(noise.outputs['Fac'],ramp.inputs[0]);t.links.new(ramp.outputs[0],scatter.inputs['Density'])
            t.links.new(scatter.outputs[0],n['Material Output'].inputs['Volume'])
    return m

variants=[
    ('01-deep','深红宝石',ruby('Deep ruby',(.16,.002,.012),.12,.48),'深红主体、中等透光，保留浓郁颜色与暗面'),
    ('02-clear','通透红宝石',ruby('Clear ruby',(.65,.045,.075),.065,.94),'高透光、高折射，观察边缘与厚度变化'),
    ('03-silk','丝绒红宝石',ruby('Silky ruby',(.3,.009,.027),.26,.55,'silk'),'细密丝状纹理与柔和光泽，艺术化丝绒效果'),
    ('04-frost','磨砂红宝石',ruby('Frosted ruby',(.43,.012,.036),.48,.68,'frost'),'细磨砂表面与柔化透光'),
    ('05-fracture','冰裂红宝石',ruby('Fractured ruby',(.27,.008,.024),.14,.7,'fracture'),'红晶表面的细淡色裂纹，非额外发光纹路'),
    ('06-inclusions','云雾红宝石',ruby('Clouded ruby',(.46,.018,.045),.11,.85,'inclusions'),'体积内的云雾状散射，模拟晶体内含物'),
]
report={'weapon':'余烬·错牙','source':str(SOURCE),'source_sha256':source_hash,'geometry_changed':False,
        'renderer':'Blender Cycles','preview_only':True,'in_game_tested':False,
        'comparison':'All variants use identical geometry, camera, lights and exposure. Six artistic ruby finishes share the same geometry, camera, light rig and restrained emissive bevel. These Cycles material proposals are not verified Skyrim effects or gemological simulations.',
        'variants':[]}
for key,label,mat,description in variants:
    for o in shapes:
        o.data.materials.clear()
        o.data.materials.append(original[o.name] if mat is None else edge if o.name.endswith('Edge') else mat)
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
