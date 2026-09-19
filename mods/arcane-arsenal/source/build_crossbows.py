"""Four concept-specific crossbows on the original Dawnguard animated skeleton.

Blender --background --python source/build_crossbows.py -- crossbowred
Exports only into build/crossbows-base until release integration is ready.
"""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,Vector,ROOT
from geometric_helpers import texture
from crossbow_native_graph import graft
KEY=sys.argv[sys.argv.index('--')+1]
SERIES='crossbows2' if KEY.startswith('crossbow2') else 'crossbows'
SPEC=next(s for s in json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text('utf-8')) if s['key']==KEY)
# Retain the known-good light material while replacing the bow reference scene.
material=mb.base_mat.copy();material.use_fake_user=True
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.import_scene.pynifly(filepath=str(ROOT/'build/crossbow-reference.nif'),import_animations=False)
mb.ref=ref=bpy.data.objects['Crossbow:0'];mb.rig=rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');mb.root=root=rig.parent
mb.bone_names=set(rig.data.bones.keys())
di=texture(SPEC['diffuse_name'],tuple(SPEC['diffuse_color'])+(1,));ni=texture('aa_red_n',(.5,.5,1,0),True);gi=texture('aa_red_g',(1,1,1,1))
mb.materials={}
for i,category in enumerate(('CrossbowBody','CrossbowEdge','CrossbowString')):
    mat=material.copy();mat.name=KEY+'_'+category;nodes=mat.node_tree.nodes;shader=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE':nodes.remove(node)
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    shader.inputs['Emission Color'].default_value=tuple(SPEC['color'] if i==0 else SPEC['edge'])+(1,)
    shader.inputs['Emission Strength'].default_value=SPEC['power'][i]
    shader.inputs['Specular Color'].default_value=(0,0,0,1);shader.inputs['Glossiness'].default_value=1
    mat.pyn_shader.Shader_Type='Glow_Shader';mat.pyn_shader.Shader_Flags_1='SKINNED | OWN_EMIT | ZBUFFER_TEST';mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
    for slot,im,inlet in [('Diffuse',di,'Diffuse'),('Normal',ni,'Normal'),('Glow',gi,'Glow Map')]:
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\'+Path(im.filepath).name
        node=nodes.new('ShaderNodeTexImage');node.image=im;mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
    mb.materials[category]=mat
mb.batches={n:mb.Batch(n) for n in mb.materials}
ROOT_BIND={'CrossbowRoot':1.0}
def limb(p):
    x=abs(p.x);side='L' if p.x>=0 else 'R'
    if x<=3:return ROOT_BIND
    if x<5:
        t=(x-3)/2;return {'CrossbowRoot':1-t,'CrossBowBone_'+side+'01':t}
    t=max(0,min(1,(x-10)/6))
    return {k:v for k,v in [('CrossBowBone_'+side+'01',1-t),('CrossBowBone_'+side+'02',t)] if v>0}
def tube(points,r=.5,category='CrossbowBody',binding=ROOT_BIND):
    pts=[Vector(p) for p in points]
    # Resample to prevent a long rail crossing several bone stations unweighted.
    dense=[]
    for a,b in zip(pts,pts[1:]):
        n=max(1,math.ceil((b-a).length/1.1));dense.extend(a.lerp(b,j/n) for j in range(n))
    dense.append(pts[-1]);weight=binding if callable(binding) else lambda p:binding
    vertices=[];faces=[];weights=[];uv=[]
    for i,p in enumerate(dense):
        tangent=(dense[min(i+1,len(dense)-1)]-dense[max(i-1,0)]).normalized()
        side=tangent.cross(Vector((0,0,1)))
        if side.length<.01:side=tangent.cross(Vector((0,1,0)))
        side.normalize();normal=tangent.cross(side).normalized()
        for j in range(8):
            angle=j*math.tau/8
            vertices.append(tuple(p+r*(side*math.cos(angle)+normal*math.sin(angle))))
            weights.append(weight(p));uv.append((j/8,i/max(1,len(dense)-1)))
        if i:
            start=(i-1)*8
            faces.extend((start+j,start+(j+1)%8,start+8+(j+1)%8,start+8+j) for j in range(8))
    faces.extend([tuple(range(7,-1,-1)),tuple((len(dense)-1)*8+j for j in range(8))])
    mb.batches[category].add(vertices,faces,uv,weights)
def band(points,width=.85,depth=.9,binding=ROOT_BIND):
    # Thick polygonal beams with a narrower luminous top seam.
    tube(points,width,'CrossbowBody',binding)
    tube([(p[0],p[1],p[2]-depth*.72) for p in points],.085,'CrossbowEdge',binding)
def loop(points,width=.7,binding=ROOT_BIND):band(points+[points[0]],width,binding=binding)
def plate(points,depth=.75,binding=ROOT_BIND):
    verts=[(p[0],p[1],p[2]+z) for z in (-depth/2,depth/2) for p in points];n=len(points)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    volume=sum(Vector(verts[f[0]]).dot(Vector(verts[f[j]]).cross(Vector(verts[f[j+1]])))/6 for f in faces for j in range(1,len(f)-1))
    if volume<0:faces=[tuple(reversed(f)) for f in faces]
    weight=binding if callable(binding) else lambda p:binding
    mb.batches['CrossbowBody'].add(verts,faces,[(p[0]/30,p[1]/30) for p in verts],[weight(Vector(p)) for p in verts])
    tube([(p[0],p[1],p[2]-depth/2-.02) for p in points]+[(points[0][0],points[0][1],points[0][2]-depth/2-.02)],.085,'CrossbowEdge',binding)

# Native bolt channel is clear above Z=-1.4; left/right rails cradle it.
for sign in (-1,1):band([(sign*1.15,-7,.0),(sign*1.15,22,.0),(sign*.8,26,.1)],.58,.65)
if SERIES=='crossbows':band([(0,-26,0),(0,-17,.5),(0,-9,.5)],1.0,1.0)
band([(0,-14,1.0),(0,-7,2.0),(0,-3,1.2)],1.15,1.0)
band([(0,6,2.5),(0,14,2.5)],1.1,1.0)
band([(-3.4,19.41,2),(3.4,19.41,2)],.8,1.0)
# Independent moving trigger and loading lever use the native control bones.
band([(0,-8,2.6),(0,-10,4.7),(0,-14,5.0)],.23,.3,{'TriggerCtrl':1.0})
for sign in (-1,1):band([(sign*2.7,3,1.9),(sign*2.7,10,2.1),(sign*1.6,18,2.0)],.22,.3,{'CockingMechanismCtrl':1.0})
band([(-.7,3,.3),(.7,3,.3)],.32,.35,{'RollerNutTriggerCtrl':1.0})
design=SPEC['design'];anchors=[]
if SERIES=='crossbows2':
    from crossbows2_geometry import build
    anchors=build(globals())
else:
    for sign in (-1,1):
        def P(x,y,z=2):return (sign*x,y,z)
        path=[P(2.9,19.41),P(9,18.7),P(14,18),P(20,16),P(24.98,14.03,1.315)]
        band(path,.75,1.0,limb)
        if design=='foldedwing':
            for x,y,size in [(5,20,6),(11,20,6),(17,18.7,5.5)]:
                plate([P(x,y),P(x+size,y-1.5),P(x+size-1,y+2.8),P(x+1,y+4.2)],1.2,limb)
            loop([P(1.6,-10,0),P(5.1,-22,1),P(1,-27,2)],.75)
            plate([P(.9,7),P(3.5,9),P(2.9,18),P(.9,18)],.9)
        elif design=='twinarc':
            arc=[P(3+21.98*t,19.41-5.38*t+5*math.sin(math.pi*t),2) for t in [j/32 for j in range(33)]]
            band(arc,.62,.8,limb)
            arc2=[P(5+18*t,19-4.5*t+2.6*math.sin(math.pi*t),1.9) for t in [j/28 for j in range(29)]]
            band(arc2,.44,.6,limb)
            stock=[P(1.2+3.4*math.sin(math.pi*t),-10-17*t,1.5*math.sin(math.pi*t)) for t in [j/28 for j in range(29)]]
            band(stock,.62,.8)
        elif design=='twinrail':
            band([P(3,19),P(7,24),P(19,21),P(24.98,14.03,1.315)],.82,1.0,limb)
            for x,y in [(10,22.8),(15,21.6),(20,19.8)]:band([P(x,y),P(x,y-3)],.35,.5,limb)
            band([P(2.3,-7,1),P(2.3,24,1)],.55,.7)
            loop([P(1.2,-10),P(4.5,-17),P(4.5,-26),P(1,-27)],.78)
            plate([P(2,8),P(4,10),P(4,17),P(2,19)],.8)
        else:
            if sign<0:
                plate([P(4,19),P(6,25),P(13,24),P(13,22),P(21,21),P(25,14),P(18,17)],1.1,limb)
            else:
                for x,y,r in [(7,21,3.5),(13,20.5,3),(19,18.2,2.6)]:loop([P(x-r,y),P(x,y+r),P(x+r,y),P(x,y-r)],.65,limb)
            band([P(1,-10),P(4,-17),P(3,-26),P(1,-27)],.8,1.0)
        for x,y in [(7,23),(14,22),(21,18.5)]:
            pos=P(x,y,1.5);weights=limb(Vector(pos));anchors.append({'bone':max(weights,key=weights.get),'side':sign,'position':pos,'direction':[sign*.5,0,-1]})
    if design=='offsetframe':
        # An off-axis octagonal cage beside the receiver, never across the bolt slot.
        pts=[(4.6+3*math.cos(j*math.tau/8),-1+3*math.sin(j*math.tau/8),1.5) for j in range(8)]
        loop(pts,.65);plate([(4,-1,1.3),(4.6,-2,1.3),(5.2,-1,1.3),(4.6,0,1.3)],.7)
        band([(1.3,-4,1),(3.3,-3,1.5)],.5,.7)

# A continuous string uses its dedicated bones with a short shared center blend.
# Native controller samples move the two halves apart at their central ends;
# blending the middle prevents a visible seam throughout the reload sequence.
def string_binding(p):
    t=max(0,min(1,(p.x+2.5)/5))
    return {name:w for name,w in [('StringR',1-t),('StringL',t)] if w>0}
string_points=[(x,14.03,-1.49+2.805*abs(x)/24.978) for x in [-24.978+49.956*j/120 for j in range(121)]]
tube(string_points,.095,'CrossbowString',string_binding)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True)
for o in bpy.data.objects:
    if o.name.startswith('bhk'):o.hide_render=True
bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=objects[0]
base=ROOT/'build'/(SERIES+'-base');base.mkdir(exist_ok=True)
raw=base/(KEY+'-export.nif');out=base/(KEY+'.nif')
bpy.ops.export_scene.pynifly(filepath=str(raw),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
graft(ROOT/'build/crossbow-reference.nif',raw,out)
# Fit a convex box in the original Havok frame; leave mass/layers/attachment intact.
import struct,itertools
from nif_blocks import NifBlocks
n=NifBlocks(out);points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
low=[(min(p[i] for p in points)-.3)/69.99125 for i in range(3)];high=[(max(p[i] for p in points)+.3)/69.99125 for i in range(3)]
kind,blob=n.blocks[6];assert kind=='bhkConvexVerticesShape'
vertices=list(itertools.product(*zip(low,high)))
planes=[]
for axis in range(3):
    for sign in (-1,1):
        normal=[0,0,0];normal[axis]=sign;planes.append((*normal,low[axis] if sign<0 else -high[axis]))
n.blocks[6]=(kind,blob[:32]+struct.pack('<I',8)+b''.join(struct.pack('<4f',*v,0) for v in vertices)+struct.pack('<I',6)+b''.join(struct.pack('<4f',*p) for p in planes));n.save(out)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.006,.008,.013,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
cd=bpy.data.cameras.new('Crossbow preview');cam=bpy.data.objects.new('Crossbow preview',cd);scene.collection.objects.link(cam)
cam.location=(52,-63,-95);target=Vector((0,0,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=77;scene.camera=cam
art=ROOT/'art'/SERIES;art.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(art/(KEY+'.blend')))
# Preview shaders show the geometric light surfaces; the exported game material
# above retains the tested low emission. This is not an ENB brightness preview.
for o in objects:
    index=0 if o.name.endswith('Body') else 2 if o.name.endswith('String') else 1
    mat=o.data.materials[0].copy();o.data.materials[0]=mat;mat.node_tree.nodes.clear()
    output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');emit=mat.node_tree.nodes.new('ShaderNodeEmission')
    color=SPEC['color'] if index==0 else SPEC['edge'];emit.inputs[0].default_value=tuple(color)+(1,);emit.inputs[1].default_value=.7 if index==0 else 2.5
    mat.node_tree.links.new(emit.outputs[0],output.inputs['Surface'])
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.threshold=1;glare.mix=-.85
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
scene.render.filepath=str(art/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.50.0' if SERIES=='crossbows2' else '0.47.0','key':KEY,'design':design,'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'shapes':3,'particle_anchors':anchors,'power':SPEC['power'],'reference':'DLC1CrossBow / native animation graph','gameplay_tested':False}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),'utf-8')
print('CROSSBOW_BUILT',KEY,report['triangles'])
