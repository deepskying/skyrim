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
scene.render.engine='CYCLES';scene.cycles.samples=32
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

body=material('Dark forged metal',(.07,.085,.11),.34,.9,texture='forged')
for o in shapes:
    o.data.materials.clear();o.data.materials.append(edge if o.name.endswith('Edge') else body)
# Broad inset ribbons supplement the existing thin emissive bevel.
glow=material('Textured ember energy',(.5,.004,.012),.35)
t=glow.node_tree;n=t.nodes;p=n['Principled BSDF']
coord=n.new('ShaderNodeTexCoord');wave=n.new('ShaderNodeTexWave');wave.bands_direction='X'
wave.inputs['Scale'].default_value=8;wave.inputs['Distortion'].default_value=4
wave.inputs['Detail Scale'].default_value=3
mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1,.14,1)
t.links.new(coord.outputs['Generated'],mapping.inputs[0]);t.links.new(mapping.outputs[0],wave.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.4,.002,.006,1);ramp.color_ramp.elements[1].color=(1,.16,.09,1)
t.links.new(wave.outputs['Color'],ramp.inputs[0]);t.links.new(ramp.outputs[0],p.inputs['Emission Color'])
p.inputs['Emission Strength'].default_value=3.6
extras=[]
def ribbon(name,path,width):
    pts=[Vector(p) for p in path];verts=[]
    for i,q in enumerate(pts):
        v=pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)];side=Vector((-v.y,v.x,0)).normalized()*width/2
        verts.extend([q-side,q+side])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(pts)-1)])
    mesh.update();o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o)
    o.matrix_world=next(o for o in shapes if o.name=='AA_WaraxeBody').matrix_world.copy()
    o.data.materials.append(glow);extras.append(o)
ribbon('Cutting edge energy inset',[(-23.7,52.6,1.66),(-26.3,41,1.66),(-21.5,25.4,1.66),(-13.2,19.4,1.66)],.85)
ribbon('Grip energy core',[(0,-12,1.5),(0,-8,1.25),(0,5,1.25),(0,14.5,1.65),(1.65,22.7,1.65),(-1.5,30,1.65)],.65)
scene.use_nodes=True
nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');g=nt.nodes.new('CompositorNodeGlare');g.glare_type='FOG_GLOW';g.quality='HIGH';g.threshold=1.5;g.size=7
o=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],g.inputs['Image']);nt.links.new(g.outputs['Image'],o.inputs['Image'])
report={'weapon':'余烬·错牙','preview_only':True,'in_game_tested':False,'variants':[]}
for key,label,enabled in [('01-thin','细亮边方案',False),('02-energy','参考方向：发光刃带＋柄芯',True)]:
    for obj in extras:obj.hide_render=not enabled
    for mode in ('full','detail'):
        target=(-8,20,0) if mode=='full' else (-10,36,0)
        cam.location=(target[0],target[1],150);aim(cam,target);camdata.ortho_scale=78 if mode=='full' else 46
        scene.render.resolution_x=900;scene.render.resolution_y=1100 if mode=='full' else 900
        scene.render.filepath=str(OUT/(key+'-'+mode+'.png'));bpy.ops.render.render(write_still=True)
    report['variants'].append({'name':label,'full':key+'-full.png','detail':key+'-detail.png'})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'material-study.blend'))
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
