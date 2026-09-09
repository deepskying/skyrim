"""Build the Glacial Crown prototype in Blender using the game's bow rig.

Run using the configured portable Blender. Original body geometry is not exported.
The source rig supplies bone transforms, normalized binding and weapon metadata.
"""
import bpy
import numpy as np
import math, random, json, subprocess
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
TOOLS = REPO / 'reference/bow-tools'
DATA = ROOT / 'data'
ART = ROOT / 'art'
MESH = DATA / 'meshes/weapons/glacialcrown'
TEX = DATA / 'textures/weapons/glacialcrown'
for folder in (ART, MESH, TEX, ROOT / 'build'):
    folder.mkdir(parents=True, exist_ok=True)
random.seed(914)
bpy.ops.wm.open_mainfile(filepath=str(TOOLS / 'validation/ironbow-textured-check.blend'))
ref = bpy.data.objects['Bow_Ironmesh:0']
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
root = rig.parent
base_mat = ref.data.materials[0]
bone_names = set(rig.data.bones.keys())

# Cache reference surface weights independently from the bowstring.
bind = []
body_points, string_points = [], []
for v in ref.data.vertices:
    co = ref.matrix_world @ v.co
    weights = {ref.vertex_groups[g.group].name:g.weight for g in v.groups
               if ref.vertex_groups[g.group].name in bone_names and g.weight > 0.0001}
    bind.append(weights)
    item = (co.copy(), v.index)
    if co.x < -12.8 and abs(co.y) < 50.5:
        string_points.append(item)
    else:
        body_points.append(item)

def tree(points):
    kd = KDTree(len(points))
    for co, i in points: kd.insert(co, i)
    kd.balance()
    return kd

body_kd, string_kd = tree(body_points), tree(string_points)

def weights_at(point, string=False):
    entries = (string_kd if string else body_kd).find_n(Vector(point), 4)
    weights = {}
    for _, i, dist in entries:
        factor = 1 / max(dist, 0.05)**2
        for name, weight in bind[i].items():
            weights[name] = weights.get(name, 0) + factor*weight
    top = sorted(weights.items(), key=lambda p:-p[1])[:4]
    total = sum(w for _,w in top)
    assert total > 0
    return {name:weight/total for name,weight in top}

def center(y):
    return Vector((1.3 - 14.97*(abs(y)/55.0)**2.35, y, 0.0))

# New procedural art, not recolored vanilla textures. Fracture veins and cloudy
# depth are baked into portable DDS textures; no Blender-only noise is required.
n = 1024
u,v = np.meshgrid(np.linspace(0,1,n),np.linspace(0,1,n))
cloud = (np.sin(u*19 + np.sin(v*13)*2) + np.sin(v*31-u*7) + np.sin(u*57+v*38)*0.35)/2.35
vein = np.zeros_like(u)
for phase,slope in [(0.13,0.6),(0.4,-0.8),(0.72,0.35),(0.94,-0.5)]:
    d = np.abs(u - (phase+slope*(v-.5)+0.035*np.sin(v*28+phase*19)))
    vein = np.maximum(vein, np.exp(-(d/0.0018)**2))
fine = (np.sin(u*460+v*173)*np.sin(v*347-u*51))*.018
diffuse = np.empty((n,n,4),np.float32)
for ch, (base, variation) in enumerate(((.17,.10),(.43,.18),(.66,.20))):
    diffuse[:,:,ch] = np.clip(base+cloud*variation+fine+vein*.42,0,1)
diffuse[:,:,3] = 1
glow = np.empty_like(diffuse)
for ch,c in enumerate((.12,.58,.95)): glow[:,:,ch]=(vein*.65+.015)*c
glow[:,:,3]=1
normal=np.ones_like(diffuse); normal[:,:,:3]=(.5,.5,1.)

def write_image(name, pixels, noncolor=False):
    image=bpy.data.images.new(name, width=n,height=n,alpha=True)
    if noncolor: image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw=str(ART / (name+'.png'))
    image.file_format='PNG'; image.save()
    return image

images={name:write_image(name,pix,name.endswith('_n')) for name,pix in
        [('glacier',diffuse),('glacier_g',glow),('glacier_n',normal)]}
texconv=Path(r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe')
for name in images:
    fmt='BC3_UNORM' if name.endswith('_n') else 'BC7_UNORM'
    subprocess.run([str(texconv),'-nologo','-y','-f',fmt,'-m','0','-o',str(TEX),str(ART/(name+'.png'))],check=True,capture_output=True)
    images[name].filepath=str(TEX / (name+'.dds'))
    images[name].reload()

def material(name, tint, emission=0.04, textured=True):
    mat=base_mat.copy(); mat.name=name
    nodes=mat.node_tree.nodes
    sh=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE': nodes.remove(node)
    sh.inputs['Diffuse'].default_value=(*tint,1)
    sh.inputs['Emission Color'].default_value=(.22,.68,1,1)
    sh.inputs['Emission Strength'].default_value=emission
    sh.inputs['Glossiness'].default_value=110
    sh.inputs['Specular Color'].default_value=(.65,.83,1,1)
    mat.pyn_shader.Shader_Type='Glow_Shader'
    mat.pyn_shader.Shader_Flags_1='SPECULAR | SKINNED | RECEIVE_SHADOWS | CAST_SHADOWS | OWN_EMIT | ZBUFFER_TEST'
    mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
    for key in list(mat.keys()):
        if key.startswith('BSShaderTextureSet_'): del mat[key]
    color_name='glacier'
    if not textured:
        color_name='glacier_'+name.split(' / ')[0].lower()
        pixels=np.ones_like(diffuse)
        for ch,c in enumerate(tint): pixels[:,:,ch]=np.clip(c*(.82+cloud*.18)+vein*.08,0,1)
        images[color_name]=write_image(color_name,pixels)
        subprocess.run([str(texconv),'-nologo','-y','-f','BC7_UNORM','-m','0','-o',str(TEX),str(ART/(color_name+'.png'))],check=True,capture_output=True)
        images[color_name].filepath=str(TEX/(color_name+'.dds'));images[color_name].reload()
    for slot,imgname,inputname in [('Diffuse',color_name,'Diffuse'),('Normal','glacier_n','Normal'),('Glow','glacier_g','Glow Map')]:
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\glacialcrown\\'+imgname+'.dds'
        node=nodes.new('ShaderNodeTexImage'); node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
        node.image=images[imgname]
        mat.node_tree.links.new(node.outputs['Color'],sh.inputs[inputname])
    return mat

materials={
    'ice':material('Glacier / fractured blue ice',(.2,.52,.78),.10),
    'frost':material('Frost / silver-white facets',(.36,.65,.86),.065,False),
    'deep':material('Depth / midnight crystal',(.035,.11,.22),.025,False),
    'silver':material('Frame / cold silver',(.24,.40,.52),.025,False),
    'energy':material('Core / glacial radiance',(.16,.63,.94),1.25,False),
    'grip':material('Grip / midnight wrap',(.02,.045,.075),0,False),
}

class Batch:
    def __init__(self,name):
        self.name=name; self.verts=[]; self.faces=[]; self.uv=[]; self.weights=[]
    def add(self,verts,faces,uv,weights):
        offset=len(self.verts)
        self.verts.extend(verts); self.faces.extend(tuple(offset+i for i in f) for f in faces)
        self.uv.extend(uv); self.weights.extend(weights)
    def object(self):
        mesh=bpy.data.meshes.new('GC_'+self.name); mesh.from_pydata(self.verts,[],self.faces); mesh.update()
        obj=bpy.data.objects.new('GC_'+self.name,mesh); bpy.context.collection.objects.link(obj); obj.parent=root
        obj.data.materials.append(materials[self.name])
        layer=mesh.uv_layers.new(name='UVMap')
        for poly in mesh.polygons:
            for loop in poly.loop_indices: layer.data[loop].uv=self.uv[mesh.loops[loop].vertex_index]
        for name in bone_names:
            vg=obj.vertex_groups.new(name=name)
            for i,weights in enumerate(self.weights):
                if name in weights: vg.add([i],weights[name],'REPLACE')
        obj.vertex_groups.new(name='SBP_32_BODY').add(list(range(len(self.verts))),1,'REPLACE')
        mod=obj.modifiers.new('Bow deformation','ARMATURE'); mod.object=rig
        for key in ('pynBlockName','pynNodeFlags','pynVertexDesc','pynSkinInstanceType','PYN_GAME','PYN_BLENDER_XF','PYN_RENAME_BONES'):
            if key in ref: obj[key]=ref[key]
        obj['pynNodeName']=obj.name
        return obj

batches={name:Batch(name) for name in materials}

def crystal(base, tip, width, depth, category='ice', binding=None, roll=0):
    base,tip=Vector(base),Vector(tip); axis=(tip-base).normalized()
    transverse=axis.cross(Vector((0,0,1)))
    if transverse.length<.01: transverse=axis.cross(Vector((1,0,0)))
    transverse.normalize(); normal=axis.cross(transverse).normalized()
    verts=[]; uv=[]; faces=[]
    sides=6
    for t,radius in [(0,.44),(.20,1),(.66,.73),(.84,.40)]:
        for j in range(sides):
            a=math.tau*j/sides+roll
            p=base.lerp(tip,t)+transverse*(math.cos(a)*width*radius)+normal*(math.sin(a)*depth*radius)
            verts.append(tuple(p)); uv.append((j/sides,t))
    verts.append(tuple(tip)); uv.append((.5,1))
    faces.append(tuple(range(sides-1,-1,-1)))
    for r in range(3):
        for j in range(sides):
            a=r*sides+j; b=r*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    for j in range(sides): faces.append((18+j,18+(j+1)%sides,24))
    binding=binding or weights_at(base)
    batches[category].add(verts,faces,uv,[binding]*len(verts))

def sweep(points,radii,category,weightfunc=None,sides=8,depth=1):
    verts=[]; uv=[]; faces=[]; weights=[]
    pts=[Vector(p) for p in points]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        side=tangent.cross(Vector((0,0,1))).normalized()
        normal=tangent.cross(side).normalized()
        for j in range(sides):
            a=math.tau*j/sides
            verts.append(tuple(p+radii[i]*(math.cos(a)*side+depth*math.sin(a)*normal)))
            uv.append((j/sides,i/(len(pts)-1)))
            weights.append(weightfunc(p) if weightfunc else weights_at(center(p.y)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides
                faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(pts)-1)*sides+j for j in range(sides))])
    batches[category].add(verts,faces,uv,weights)

mid={'Bow_MidBone':1}
for sign in (1,-1):
    ys=np.linspace(7,55,54)*sign
    points=[center(float(y)) for y in ys]
    radii=[1.65*(1-abs(float(y))/76)+.30 for y in ys]
    sweep(points,radii,'deep',depth=.72)
    sweep([p+Vector((.6,0,-1.1)) for p in points],[.22]*len(points),'energy',sides=5)
    # Long backwards-swept crown blades; clusters grow toward each limb tip.
    for i,y in enumerate([12,17,23,29,35,40,44,48,51,53]):
        p=center(float(y)*sign)
        length=10+10*(y/55)+random.uniform(-3,3)
        fan=.50+.40*(y/55)
        tip=p+Vector((length*fan,sign*length*(1.10-fan),random.uniform(-1,1)))
        crystal(p+Vector((.5,0,0)),tip,1.7+random.random()*.9,.95+random.random()*.7,'ice',weights_at(p),roll=.18*i)
        crystal(p+Vector((-.4,0,-.6)),p+Vector((length*.30,sign*length*.72,-2.1)),.45+random.random()*.45,.45,'frost',weights_at(p),roll=.3)
        crystal(p+Vector((.5,2*sign,-.7)),p+Vector((length*(fan+.22),sign*length*.13,-1)),.80,.60,'ice',weights_at(p),roll=.1)
        if i%2==0:
            crystal(p+Vector((.8,1*sign,.7)),p+Vector((length*.72,sign*length*.5,3.8)),.9,1,'ice',weights_at(p),roll=.5)
    # Swept terminal crystal keeps string attachments in the reference positions.
    end=center(54.8*sign)
    crystal(end+Vector((.7,-sign*2,0)),end+Vector((2.5,sign*10,0)),1.3,1.2,'frost',weights_at(end))

# Slender hand grip, tightly fitting spiral bands and restrained pommel.
sweep([(1.3,y,0) for y in np.linspace(-7,7,18)],[1.30]*18,'grip',lambda p:mid,sides=12)
helix=[(1.3+1.34*math.cos(t),-6.5+13*t/(math.tau*6),1.34*math.sin(t)) for t in np.linspace(0,math.tau*6,210)]
sweep(helix,[.14]*len(helix),'silver',lambda p:mid,sides=5)
for sign in (1,-1):
    crystal((1.3,sign*6.6,0),(2,sign*12,0),2.2,1.55,'silver',mid)

# Faceted heart and asymmetric frost crown, clear of the hand at y=0.
heart=Vector((3.2,12,-2.3))
crystal(heart+Vector((0,-4,0)),heart+Vector((0,5,0)),3,2,'energy',mid,roll=.2)
for i in range(8):
    a=math.tau*i/8
    direction=Vector((math.cos(a),math.sin(a),0))
    crystal(heart+direction*3+Vector((0,0,1.3)),heart+direction*(7.5 if i%2==0 else 5.4)+Vector((0,0,1.3)),.65,.45,'frost',mid)

# Broken halo follows the rigid middle bone in v0.1. No animation claim is made.
halo_center=Vector((5,12,4))
for radius,width,category in [(13.0,.25,'silver'),(14.1,.10,'energy')]:
    for amin,amax in [(-77,-13),(4,58),(77,137),(157,207),(229,260)]:
        angles=np.linspace(math.radians(amin),math.radians(amax),20)
        pts=[halo_center+Vector((radius*math.cos(a),radius*math.sin(a),0)) for a in angles]
        sweep(pts,[width]*len(pts),category,lambda p:mid,sides=6)
for i in range(12):
    a=math.tau*i/12+.08
    p=halo_center+Vector((15.5*math.cos(a),15.5*math.sin(a),0))
    crystal(p+Vector((0,-1.0,0)),p+Vector((0,1.9,0)),.70,.50,'ice',mid)

# A real skinned string: its samples inherit the original string bone weights.
stringpts=[(-13.674, y, -.02) for y in np.linspace(-54.70,54.97,80)]
sweep(stringpts,[.115]*len(stringpts),'energy',lambda p:weights_at(p,True),sides=6)

objects=[b.object() for b in batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True)
root.name='GlacialCrown_ROOT'; root['pynNodeName']='GlacialCrown'
rig.name='GlacialCrown_BowRig'
collision=bpy.data.objects.get('bhkBoxShape')
collision.hide_render=True
# The original compact bow collision remains deliberately simple for the prototype.
# It is carried over through PyNifly rather than synthesizing Havok metadata.
stats={'version':'0.1.1','triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),
       'vertices':sum(len(o.data.vertices) for o in objects),'shapes':len(objects),'bones':list(rig.data.bones.keys()),
       'features':['new crystal geometry','DDS textures','emissive crystal core','skinned bowstring','static segmented halo'],
       'not_implemented':['orbit animation','charge-reactive VFX','custom projectile','gameplay validation']}
(ROOT/'build/model-report.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children): obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
# PyNifly's automatic setting discovery overrides explicit kwargs with the
# imported root's stored defaults. Disable it so the weapon's animated bone
# hierarchy is preserved instead of exporting seven independent root bones.
bpy.ops.export_scene.pynifly(filepath=str(MESH/'glacialcrown.nif'),target_game='SKYRIMSE',
    intuit_defaults=False, preserve_hierarchy=True, blender_xf=False,
    rename_bones=True, rotate_bones_pretty=False, export_pose=False,
    export_modifiers=False, export_animations=False)
assert (MESH/'glacialcrown.nif').stat().st_size>10000

# Retain the same geometry/materials for a truthful model preview.
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=40
scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.world.color=(.06,.06,.06)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.025,.045,.075,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
scene.view_settings.view_transform='AgX'

def aim(obj,at):
    forward=(Vector(at)-obj.location).normalized()
    right=forward.cross(Vector((0,1,0))).normalized()
    up=right.cross(forward).normalized()
    obj.rotation_euler=Matrix((right,up,-forward)).transposed().to_quaternion().to_euler()
camdata=bpy.data.cameras.new('Preview camera');cam=bpy.data.objects.new('Preview camera',camdata);scene.collection.objects.link(cam)
cam.location=(-22,3,-215);aim(cam,(3,2,0));camdata.type='ORTHO';camdata.ortho_scale=145;scene.camera=cam
for name,loc,power,color,size in [('Softbox',(-40,50,-70),220000,(.61,.82,1),70),('Ice rim',(40,25,35),280000,(.15,.58,1),60),('Lower fill',(-20,-60,-30),100000,(.45,.64,1),50)]:
    ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo)
    lo.location=loc;ld.energy=power;ld.color=color;ld.shape='DISK';ld.size=size;aim(lo,(0,0,0))
scene.use_nodes=True
nt=scene.node_tree;nt.nodes.clear()
rl=nt.nodes.new('CompositorNodeRLayers'); glare=nt.nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=1.7
out=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],glare.inputs['Image']);nt.links.new(glare.outputs['Image'],out.inputs['Image'])
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ART/'glacial-crown-prototype.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'glacial-crown.blend'))
bpy.ops.render.render(write_still=True)
print('BUILD_COMPLETED '+json.dumps(stats))
