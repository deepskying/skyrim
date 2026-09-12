"""Rigid single-handed swords on the vanilla IronSword attachment frame.

Run in portable Blender with -- <key>. All visible geometry is original.
The imported reference provides WeaponSword, inventory marker and Havok metadata.
"""
import sys,math,json
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
import mesh_builder as mb
from geometric_helpers import texture
if not (ROOT/'build/ironsword-reference.nif').is_file():
    import subprocess
    subprocess.run(['python',str(ROOT/'source/prepare_sword_reference.py')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
KEY=sys.argv[sys.argv.index('--')+1]
SERIES='swords'
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
bpy.ops.import_scene.pynifly(filepath=str(ROOT/'build/ironsword-reference.nif'))
root=next(o for o in bpy.context.scene.objects if o.get('pynRoot'))
ref=bpy.data.objects['IronLongSword01:0'];props=dict(ref.items())
for o in list(bpy.context.scene.objects):
    if o.name in ('IronLongSword01:0','BloodEffects','BloodLighting','Scb'):bpy.data.objects.remove(o,do_unlink=True)
root['pynNodeName']=KEY;root.name=KEY+'_ROOT'
for o in bpy.context.scene.objects:
    if o.name.startswith('bhk'):o.hide_render=True
# Havok is restored from the vanilla block graph after export. This avoids the
# importer's Y/Z scale conversion and keeps the original mass and attachment.
anchor=bpy.data.objects.new('AASwordAnchor',None);bpy.context.collection.objects.link(anchor);anchor.parent=root
anchor['pynBlockName']='NiNode';anchor['pynNodeName']='AASwordAnchor';anchor['pynNodeFlags']='SELECTIVE_UPDATE | SELECTIVE_UPDATE_TRANSF'
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

# Short one-palm grip around the original IronSword origin.
slab([(-1.15,-8),(1.15,-8),(1.15,5),(-1.15,5)],2.2,bevel=.16)
for y in (-7.5,4):slab([(-1.35,y-.28),(1.35,y-.28),(1.35,y+.28),(-1.35,y+.28)],2.5,bevel=.10)
slab([(-1.0,4),(1.0,4),(1.0,10),(-1.0,10)],2,bevel=.12)
slab([(-.65,-10),(.65,-10),(.65,-7),(-.65,-7)],1.8,bevel=.10)
from swords_geometry import build
anchors=build(SPEC,slab,rail,frame,solid)

# Join by material into exactly two unskinned game shapes.
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();joined=bpy.context.object
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.00001)
bpy.ops.mesh.dissolve_degenerate(threshold=.0001)
bpy.ops.mesh.quads_convert_to_tris();bpy.ops.mesh.dissolve_degenerate(threshold=.0001)
bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
shapes=[o for o in bpy.context.selected_objects if o.type=='MESH']
assert len(shapes)==2
for o in shapes:
    label='Edge' if o.data.materials[0]==materials[1] else 'Body';o.name='AA_Sword'+label
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
n=NifBlocks(out);reference=NifBlocks(ROOT/'build/ironsword-reference.nif')
kind,data=n.blocks[0];old=reference.blocks[0][1]
offset=4*struct.unpack_from('<I',data,4)[0];old_offset=4*struct.unpack_from('<I',old,4)[0]
n.blocks[0]=(kind,data[:16+offset]+old[16+old_offset:68+old_offset]+data[68+offset:]);n.save(out)
expected=['bhkBoxShape','bhkConvexTransformShape']*3+['bhkListShape','bhkRigidBody','bhkCollisionObject']
assert [k for k,b in reference.blocks[4:13]]==[k for k,b in n.blocks[4:13]]==expected
assert struct.unpack_from('<I',data,68+offset)[0]==12
n.blocks[4:13]=reference.blocks[4:13]
# Preserve the original grip box. Widen the guard and blade boxes for the
# geometric silhouettes without changing the mass, constraints or links.
for block,scale in [(6,SPEC['guard_collision_scale']),(8,SPEC['collision_scale'])]:
    kind,blob=n.blocks[block];blob=bytearray(blob)
    dimensions=struct.unpack_from('<3f',blob,16)
    struct.pack_into('<3f',blob,16,*(d*s for d,s in zip(dimensions,scale)))
    n.blocks[block]=(kind,bytes(blob))
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
cd=bpy.data.cameras.new('Preview');cam=bpy.data.objects.new('Preview',cd);scene.collection.objects.link(cam);cam.location=(30,29,230);cam.rotation_euler=(0,math.atan2(30,230),0);cd.type='ORTHO';cd.ortho_scale=99;scene.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art'/(KEY+'.blend')))
scene.render.filepath=str(ROOT/'art'/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.28.0','key':KEY,'design':SPEC['design'],'triangles':sum(len(o.data.polygons) for o in shapes),'shapes':2,'particle_anchors':[{'bone':'AASwordAnchor','side':1,'position':p,'direction':[0,1,0]} for p in anchors],'power':SPEC['power'],'reference':'IronLongSword01 / WeaponSword','gameplay_tested':False}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SWORD_BUILT',KEY,report['triangles'])
