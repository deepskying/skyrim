"""Non-destructive material study on the actual approved weapon geometry.

Run in the project portable Blender. No NIF, DDS, plugin or MO2 file is written.
Cycles materials below are visual proposals, not Skyrim shader implementations.
"""
from pathlib import Path
import bpy, math, json, hashlib
from mathutils import Vector, Matrix

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
import sys
ROOT=OUT.parents[1]
weapon=sys.argv[sys.argv.index('--')+1]
key=next(c for c in ['red','green','blue','purple'] if weapon.endswith(c))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.pynifly(filepath=str(ROOT/'data/meshes/weapons/arcanearsenal'/(weapon+'.nif')))
shapes=[o for o in bpy.context.scene.objects if o.name in ('AA_GreatswordBody','AA_GreatswordEdge')]
assert len(shapes)==2
for o in shapes:
    xf=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Rotation(.32,4,'Y')@xf
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


colors={'red':((1,.015,.025),3.6,1.8),'green':((.16,1,.67),4.5,2.25),'blue':((.16,.95,1),5.4,2.25),'purple':((.72,.30,1),5.4,2.7)}
edgecolor,edgepower,power=colors[key]
for obj in shapes:
    m=material(obj.name,(.5,.5,.5),.4)
    t=m.node_tree;n=t.nodes;p=n['Principled BSDF']
    if obj.name.endswith('Body'):
        for suffix,inlet in [('d','Base Color'),('g','Emission Color')]:
            node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(ROOT/'art/emissive-materials'/('aa_emissive_'+key+'_'+suffix+'.png')))
            t.links.new(node.outputs['Color'],p.inputs[inlet])
        p.inputs['Emission Strength'].default_value=power
        node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(ROOT/'art/emissive-materials'/('aa_emissive_'+key+'_n.png')));node.image.colorspace_settings.name='Non-Color'
        nm=n.new('ShaderNodeNormalMap');t.links.new(node.outputs['Color'],nm.inputs['Color']);t.links.new(nm.outputs[0],p.inputs['Normal'])
    else:
        p.inputs['Base Color'].default_value=(*edgecolor,1);p.inputs['Emission Color'].default_value=(*edgecolor,1);p.inputs['Emission Strength'].default_value=edgepower
    obj.data.materials.clear();obj.data.materials.append(m)
scene.use_nodes=True;t=scene.node_tree;t.nodes.clear();rl=t.nodes.new('CompositorNodeRLayers');g=t.nodes.new('CompositorNodeGlare');g.glare_type='FOG_GLOW';g.threshold=1.5;g.quality='HIGH';g.size=7
out=t.nodes.new('CompositorNodeComposite');t.links.new(rl.outputs['Image'],g.inputs['Image']);t.links.new(g.outputs['Image'],out.inputs['Image'])
points=[o.matrix_world@v.co for o in shapes for v in o.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
target=(lo+hi)/2;cam.location=(target.x,target.y,200);aim(cam,target);camdata.ortho_scale=max(hi.y-lo.y,(hi.x-lo.x)*1050/800)*1.12
scene.render.resolution_x=800;scene.render.resolution_y=1050
scene.render.filepath=str(OUT/(weapon+'-nif-preview.png'));bpy.ops.render.render(write_still=True)
