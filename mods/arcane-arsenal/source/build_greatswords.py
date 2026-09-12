"""Rigid greatswords on the vanilla IronClaymore attachment and collision frame.

Run in portable Blender with -- <key>. All visible geometry is original.
The imported reference provides WeaponBack, inventory marker and Havok metadata.
"""
import sys,math,json
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
import mesh_builder as mb
from geometric_helpers import texture
if not (ROOT/'build/irongreatsword-reference.nif').is_file():
    from bsa_reference import extract,entries
    game=Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data')
    model='meshes/weapons/iron/ironclaymore.nif'
    archive=next(p for p in game.glob('Skyrim - Meshes*.bsa') if model in entries(p))
    (ROOT/'build/irongreatsword-reference.nif').write_bytes(extract(archive,model))
KEY=sys.argv[sys.argv.index('--')+1]
SERIES='greatswords3' if KEY.startswith('greatsword3') else 'greatswords2' if KEY.startswith('greatsword2') else 'greatswords'
SPEC=next(s for s in json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8')) if s['key']==KEY)
materials=[]
for i,label in enumerate(('Body','Edge')):
    mat=mb.base_mat.copy();mat.name=KEY+label
    shader=mat.node_tree.nodes['SkyrimShader:Default']
    for node in list(mat.node_tree.nodes):
        if node.type=='TEX_IMAGE':mat.node_tree.nodes.remove(node)
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    shader.inputs['Emission Color'].default_value=tuple(SPEC['color'] if i==0 else SPEC['edge'])+(1,)
    shader.inputs['Emission Strength'].default_value=SPEC['power'][i]
    shader.inputs['Specular Color'].default_value=(0,0,0,1);shader.inputs['Glossiness'].default_value=1
    mat.pyn_shader.Shader_Type='Glow_Shader'
    mat.pyn_shader.Shader_Flags_1='OWN_EMIT | ZBUFFER_TEST'
    mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
    for slot,name,inlet in [('Diffuse',SPEC['diffuse_name'],'Diffuse'),('Normal','aa_red_n','Normal'),('Glow','aa_red_g','Glow Map')]:
        image=bpy.data.images.load(str(ROOT/'data/textures/weapons/arcanearsenal'/(name+'.dds')),check_existing=True)
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
        node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\'+name+'.dds'
        mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
    materials.append(mat)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.pynifly(filepath=str(ROOT/'build/irongreatsword-reference.nif'))
root=next(o for o in bpy.context.scene.objects if o.get('pynRoot'))
ref=bpy.data.objects['IronClaymore01:0'];props=dict(ref.items())
for o in list(bpy.context.scene.objects):
    if o.name in ('IronClaymore01:0','BloodFX','BloodLighting'):bpy.data.objects.remove(o,do_unlink=True)
root['pynNodeName']=KEY;root.name=KEY+'_ROOT'
for o in bpy.context.scene.objects:
    if o.name.startswith('bhk'):o.hide_render=True
# Havok is restored from the vanilla block graph after export. This avoids the
# importer's Y/Z scale conversion and keeps the original mass and attachment.
anchor=bpy.data.objects.new('AAGreatswordAnchor',None);bpy.context.collection.objects.link(anchor);anchor.parent=root
anchor['pynBlockName']='NiNode';anchor['pynNodeName']='AAGreatswordAnchor';anchor['pynNodeFlags']='SELECTIVE_UPDATE | SELECTIVE_UPDATE_TRANSF'
objects=[]

def solid(verts,faces,bevel=.26):
    """Closed solid with bevelled edges; also supports twisted blade sections."""
    mesh=bpy.data.meshes.new('slab');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('slab',mesh);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(materials[0]);obj.data.materials.append(materials[1])
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    mod=obj.modifiers.new('Luminous bevel','BEVEL');mod.width=bevel;mod.segments=1;mod.affect='EDGES';mod.material=1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Recalculate consistently outward before export.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False);objects.append(obj);return obj

def plate(points,depth=2.2,bevel=.26):
    verts=[(x,y,z+d) for d in (-depth/2,depth/2) for x,y,z in points];n=len(points)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return solid(verts,faces,bevel)
def slab(points,depth=2.2,z=0,bevel=.26):return plate([(x,y,z) for x,y in points],depth,bevel)
def rail(points,width,depth=2.2,z=0):
    pts=[Vector(p) for p in points];left=[];right=[]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();side=Vector((-tangent.y,tangent.x))
        left.append(tuple(p+side*width/2));right.append(tuple(p-side*width/2))
    return slab(left+right[::-1],depth,z,min(.26,width*.15))
def frame(cx,cy,w,h,width=1.6,z=0,angle=0):
    c,s=math.cos(angle),math.sin(angle)
    def xf(p):x,y=p;return (cx+x*c-y*s,cy+x*s+y*c)
    for a,b in [((-w/2,-h/2),(w/2,-h/2)),((w/2,-h/2),(w/2,h/2)),((w/2,h/2),(-w/2,h/2)),((-w/2,h/2),(-w/2,-h/2))]:rail([xf(a),xf(b)],width,2.6,z)

# A two-hand handle at the original attachment origin; no decorative geometry in the palm envelope.
slab([(-1.45,-15),(1.45,-15),(1.45,8),(-1.45,8)],2.7,bevel=.20)
for y in (-14,-10,-6,-2,2,6):slab([(-1.6,y-.22),(1.6,y-.22),(1.6,y+.22),(-1.6,y+.22)],2.95,bevel=.10)
kind=SPEC['design'];anchors=[]
if kind!='shatteredspire':
    # Join hilt and blade through the guard without entering either palm.
    slab([(-1.35,7),(1.35,7),(1.35,18),(-1.35,18)],2.7,bevel=.18)
slab([(-.7,-18),(.7,-18),(.7,-14),(-.7,-14)],2,bevel=.15)
if SERIES in ('greatswords2','greatswords3'):
    from importlib import import_module
    build=import_module(SERIES+'_geometry').build
    anchors=build(SPEC,slab,rail,frame,solid)
elif kind=='riftcleaver':
    # Offset through-window, uninterrupted left cutting edge and three teeth on the right.
    slab([(-8,13),(-8,102),(-3,96),(-3,17)],2.8)
    slab([(-3,96),(12,81),(12,73),(7,78),(7,84)],2.8)
    slab([(-3,17),(5,17),(7,27),(7,33),(0,39),(-3,37)],2.8)
    rail([(0,20),(0,64),(1,86)],2,2.5)
    for pts,z in [([(1,72),(7,79),(18,67),(18,51),(1,61)],.35), ([(1,49),(7,56),(18,44),(18,31),(1,40)],-.25), ([(1,29),(7,36),(14,28),(12,14),(1,16)],.3)]:slab(pts,2.8,z)
    slab([(-1,11),(-14,17),(-16,14),(-4,8)],3.0);slab([(1,11),(10,12),(15,8),(3,7)],3.0)
    slab([(-1,-16),(-5,-22),(-1,-27)],3);slab([(1,-16),(5,-22),(1,-27)],3)
    anchors=[(19,34,0),(19,46,0),(19,63,0),(13,79,0),(10,24,0),(5,90,0)]
elif kind=='bifurcate':
    slab([(0,13),(5,22),(8,37),(6,51),(13,69),(10,88),(7,103),(17,84),(20,66),(13,50),(15,35),(9,19),(4,12)],2.5)
    slab([(-1,12),(-9,22),(-16,40),(-13,51),(-12,65),(-4,79),(-8,60),(-8,51),(-11,40),(-5,27),(2,16)],2.5)
    rail([(-1,8),(-8,10),(-13,15),(-14,20),(-12,24)],2.6,3)
    slab([(1,6),(11,9),(5,11),(1,10)],3)
    frame(0,-21,6,8,1.3,angle=math.pi/4)
    anchors=[(-3,27,0),(1,39,0),(-1,51,0),(3,63,0),(6,78,0),(13,90,0)]
elif kind=='offsetmonolith':
    slab([(-1.6,10),(1.6,10),(1.6,94),(-1.6,94)],3.2)
    for cx,cy,w,h,z in [(3.3,28,13,28,-.5),(-3.2,54,14,28,1),(2.0,80,12,28,-.1)]:frame(cx,cy,w,h,2.8,z)
    slab([(-4.1,92),(2,104),(7.7,92)],3)
    rail([(-12,11),(-12,16),(9,16),(9,12)],3.1,3.8)
    rail([(-8,9),(5,9),(5,13)],2.4,3.8,1)
    frame(0,-21,6,8,1.6)
    anchors=[(-10,33,0),(13,26,0),(-14,53,0),(11,66,0),(-8,83,0),(11,89,0)]
elif kind=='shatteredspire':
    # Distinct blade slabs with visible air gaps, held by one narrow energy filament.
    rail([(0,14),(0,101)],.45,.55)
    for pts,z in [([(-8,24),(-8,43),(7,33),(7,17)],.2),([(-7,47),(-7,62),(6,52),(6,37)],-.25),([(-6,66),(-6,80),(5,71),(5,56)],.2),([(-4,84),(-4,94),(4,87),(4,75)],-.15),([(-3,97),(0,108),(4,90)],.1)]:slab(pts,2.7,z)
    slab([(-1,7),(-9,11),(-12,24),(-7,20),(-5,12)],3.0)
    slab([(1,7),(8,11),(12,19),(7,21),(5,14)],3)
    slab([(0,12),(-2,16),(0,20),(2,16)],2.5)
    slab([(0,-16),(-4,-20),(0,-27),(4,-20)],3)
    for x,y in [(11,36),(10,57),(8,75)]:slab([(x,y-2),(x-1,y),(x,y+2),(x+1,y)],.7,bevel=.12)
    anchors=[(10,28,0),(10,44,0),(9,61,0),(8,77,0),(5,91,0),(3,18,0)]
else:raise ValueError(kind)

# Join by material into exactly two unskinned game shapes.
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();joined=bpy.context.object
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.00001);bpy.ops.mesh.quads_convert_to_tris();bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
shapes=[o for o in bpy.context.selected_objects if o.type=='MESH']
assert len(shapes)==2
for o in shapes:
    label='Edge' if o.data.materials[0]==materials[1] else 'Body';o.name='AA_Greatsword'+label
    inv=root.matrix_world.inverted()
    for v in o.data.vertices:v.co=inv@v.co
    o.parent=root;o.matrix_basis=Matrix.Identity(4)
    for k,v in props.items():
        if k!='pynNodeName':o[k]=v
    o['pynNodeName']=o.name
    uv=o.data.uv_layers.new(name='UVMap')
    for poly in o.data.polygons:
        for loop in poly.loop_indices:
            v=o.data.vertices[o.data.loops[loop].vertex_index].co;uv.data[loop].uv=(v.x/30,v.y/100)
    o.data.update()
bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=shapes[0]
out=ROOT/'data/meshes/weapons/arcanearsenal'/(KEY+'.nif')
bpy.ops.export_scene.pynifly(filepath=str(out),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
# PyNifly resets an unskinned root rotation while retaining root-local vertices.
# Restore the vanilla attachment frame, then verify global geometry by reimport.
from nif_blocks import NifBlocks
import struct
n=NifBlocks(out);reference=NifBlocks(ROOT/'build/irongreatsword-reference.nif')
kind,data=n.blocks[0];old=reference.blocks[0][1]
offset=4*struct.unpack_from('<I',data,4)[0];old_offset=4*struct.unpack_from('<I',old,4)[0]
n.blocks[0]=(kind,data[:16+offset]+old[16+old_offset:68+old_offset]+data[68+offset:]);n.save(out)
expected=['bhkBoxShape','bhkConvexTransformShape','bhkBoxShape','bhkConvexTransformShape','bhkListShape','bhkRigidBody','bhkCollisionObject']
assert [k for k,b in reference.blocks[4:11]]==[k for k,b in n.blocks[4:11]]==expected
assert struct.unpack_from('<I',data,68+offset)[0]==10
n.blocks[4:11]=reference.blocks[4:11]
kind,blob=n.blocks[4];blob=bytearray(blob)
dimensions=struct.unpack_from('<3f',blob,16)
collision_scale=SPEC.get('collision_scale',(6,1.18,2))
struct.pack_into('<3f',blob,16,*(d*s for d,s in zip(dimensions,collision_scale)))
n.blocks[4]=(kind,bytes(blob))
for index,(kind,blob) in enumerate(n.blocks):
    if kind=='BSXFlags':
        blob=bytearray(blob);struct.pack_into('<I',blob,4,struct.unpack_from('<I',blob,4)[0]|1)
        n.blocks[index]=(kind,bytes(blob))  # Animated: native particle controllers.
n.save(out)
base=ROOT/'build'/(SERIES+'-base');base.mkdir(exist_ok=True);(base/out.name).write_bytes(out.read_bytes())
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.008,.012,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
scene.render.resolution_x=750;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
cd=bpy.data.cameras.new('Preview');cam=bpy.data.objects.new('Preview',cd);scene.collection.objects.link(cam);cam.location=(45,41,230);cam.rotation_euler=(0,math.atan2(45,230),0);cd.type='ORTHO';cd.ortho_scale=148;scene.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art'/(KEY+'.blend')))
scene.render.filepath=str(ROOT/'art'/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.27.0' if SERIES=='greatswords3' else '0.26.0' if SERIES=='greatswords2' else '0.25.0','key':KEY,'design':SPEC['design'],'triangles':sum(len(o.data.polygons) for o in shapes),'shapes':2,'particle_anchors':[{'bone':'AAGreatswordAnchor','side':1,'position':p,'direction':[0,1,0]} for p in anchors],'power':SPEC['power'],'reference':'IronClaymore01 / WeaponBack','gameplay_tested':False}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GREATSWORD_BUILT',KEY,report['triangles'])
