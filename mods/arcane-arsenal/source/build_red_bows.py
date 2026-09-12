"""Three simple solid-light bows, using the previously verified seven-bone rig.

Blender --background --python-exit-code 1 --python this.py -- <key>
Keys: redplates, redtriangles, reddiamonds. No illustrated textures are used.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,math,json,Vector,Matrix,ROOT,ART,TEX,MESH,ref,root,rig

KEY=sys.argv[sys.argv.index('--')+1]
assert KEY in ('redplates','redtriangles','reddiamonds')
MID={'Bow_MidBone':1.0}
STAR_RADIUS=8.0
STAR_Z=-3.8
STRING_X=-13.674
ANCHORS={1:54.97,-1:-54.70}
module_records=[]

# Select actual string-weighted vertices, not nearby limb surfaces. The reference
# has two string bones with a nocking transition near y=5. Interpolate by length;
# nearest-neighbor blending can introduce kinks where the limb approaches the string.
samples={}
for vertex in ref.data.vertices:
    p=ref.matrix_world@vertex.co
    weights={ref.vertex_groups[g.group].name:g.weight for g in vertex.groups if ref.vertex_groups[g.group].name in mb.bone_names}
    if p.x < -13.3 and any('StringBone' in name and w>0 for name,w in weights.items()):
        samples.setdefault(round(p.y,3),[]).append(weights)
string_samples=[]
for y,entries in sorted(samples.items()):
    if ANCHORS[-1]<y<ANCHORS[1]:
        average={name:sum(e.get(name,0) for e in entries)/len(entries) for name in mb.bone_names}
        string_samples.append((y,{name:w for name,w in average.items() if w>.00001}))
string_samples=[(ANCHORS[-1],{'Bow_LoBone2':1.0})]+string_samples+[(ANCHORS[1],{'Bow_UpBone2':1.0})]
assert len(string_samples)>8

def string_weights(point):
    y=Vector(point).y
    for (a,wa),(b,wb) in zip(string_samples[:-1],string_samples[1:]):
        if y<=b:
            t=max(0,min(1,(y-a)/(b-a)))
            weights={name:(1-t)*wa.get(name,0)+t*wb.get(name,0) for name in wa.keys()|wb.keys()}
            return {name:w for name,w in weights.items() if w>.000001}
    return string_samples[-1][1]

def texture(name,color,normal=False):
    path=TEX/(name+'.dds')
    if path.is_file():return bpy.data.images.load(str(path),check_existing=True)
    n=64;pixels=np.empty((n,n,4),np.float32);pixels[:]=color
    image=bpy.data.images.new(name,width=n,height=n,alpha=True)
    if normal:image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(ART/(name+'.png'));image.file_format='PNG';image.save()
    exe=r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe'
    mb.subprocess.run([exe,'-nologo','-y','-f','BC3_UNORM' if normal else 'BC7_UNORM','-m','0','-o',str(TEX),str(ART/(name+'.png'))],check=True,capture_output=True)
    image.filepath=str(path);image.reload();return image

di=texture('aa_red_d',(.32,0,0,1));ni=texture('aa_red_n',(.5,.5,1,0),True);gi=texture('aa_red_g',(1,1,1,1))
for category,power in [('redface',1.8),('redline',3.6),('redstring',2.4)]:
    mat=mb.base_mat.copy();mat.name=KEY+'_'+category
    nodes=mat.node_tree.nodes;shader=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE':nodes.remove(node)
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    shader.inputs['Emission Color'].default_value=(1,0,0,1)
    shader.inputs['Emission Strength'].default_value=power
    shader.inputs['Specular Color'].default_value=(0,0,0,1)
    shader.inputs['Glossiness'].default_value=1
    mat.pyn_shader.Shader_Type='Glow_Shader'
    mat.pyn_shader.Shader_Flags_1='SKINNED | OWN_EMIT | ZBUFFER_TEST'
    mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
    for slot,im,inlet in [('Diffuse',di,'Diffuse'),('Normal',ni,'Normal'),('Glow',gi,'Glow Map')]:
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\'+Path(im.filepath).name
        node=nodes.new('ShaderNodeTexImage');node.image=im
        node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
        mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
    mb.materials[category]=mat
mb.batches={name:mb.Batch(name) for name in mb.materials}

def path(sign,t):
    # Matches exact vanilla string anchors while adding a smooth outward shoulder.
    x=1.3+4.0*math.sin(math.pi*t)-14.974*t**1.8
    y=sign*(8.0+(abs(ANCHORS[sign])-8.0)*t)
    return Vector((x,y,0))

def polyline(points,width,category,binding=None):
    for a,b in zip(points[:-1],points[1:]):
        a,b=Vector(a),Vector(b)
        if (b-a).length<.0001:continue
        # Rigid triangle edges need only their endpoints. Flexible rails are sampled.
        steps=2 if binding else max(2,int((b-a).length/.8)+1)
        pts=[a.lerp(b,float(t)) for t in np.linspace(0,1,steps)]
        tangent=(b-a).normalized();side=tangent.cross(Vector((0,0,1)))
        if side.length<.01:side=tangent.cross(Vector((0,1,0)))
        side.normalize();normal=tangent.cross(side).normalized()
        verts=[];faces=[];uv=[];weights=[];sides=8
        for i,p in enumerate(pts):
            for j in range(sides):
                angle=math.tau*j/sides
                verts.append(tuple(p+width*(math.cos(angle)*side+math.sin(angle)*normal)))
                uv.append((j/sides,i/(steps-1)))
                weights.append(binding or mb.weights_at(mb.center(p.y)))
            if i:
                for j in range(sides):
                    v=(i-1)*sides+j;w=(i-1)*sides+(j+1)%sides
                    faces.append((v,w,w+sides,v+sides))
        faces.extend([tuple(range(sides-1,-1,-1)),tuple((steps-1)*sides+j for j in range(sides))])
        mb.batches[category].add(verts,faces,uv,weights)

def filled_triangle(points,depth,binding):
    """Two-sided solid extruded triangle with real depth, not a billboard."""
    p=[Vector(v) for v in points]
    vertices=[tuple(v+Vector((0,0,z))) for z in (-depth/2,depth/2) for v in p]
    area=(p[1]-p[0]).cross(p[2]-p[0]).z
    faces=[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]
    if area<0:faces=[tuple(reversed(f)) for f in faces]
    mb.batches['redface'].add(vertices,faces,[(.15,.15),(.85,.15),(.5,.85)]*2,[binding]*6)
    # Red borders remain distinguishable from the uniformly red emissive face.
    for z in (-depth/2,depth/2):
        outline=[v+Vector((0,0,z)) for v in p]
        polyline(outline+[outline[0]],.085,'redline',binding)

# Exactly two equilateral triangle outlines, sharing the middle-bone binding.
star_triangles=[]
for phase in (math.pi/2,-math.pi/2):
    pts=[Vector((1.3+STAR_RADIUS*math.cos(phase+j*math.tau/3),STAR_RADIUS*math.sin(phase+j*math.tau/3),STAR_Z)) for j in range(3)]
    polyline(pts+[pts[0]],.24,'redline',MID)
    star_triangles.append([tuple(p) for p in pts])

# A thin red grip behind the emblem keeps the first-person hand at the proven origin.
# Its ends connect to the star outside the palm; no plate obstructs the arrow lane.
polyline([(1.3,-6,0),(1.3,6,0)],.36,'redface',MID)
for sign in (-1,1):
    polyline([(1.3,sign*5.8,0),(1.3,sign*8,STAR_Z)],.18,'redline',MID)
    p0=path(sign,0)
    polyline([(1.3,sign*8,STAR_Z),p0],.18,'redline',MID)
    # The flexible spine maintains a continuous connection while rigid modules overlap.
    pts=[path(sign,float(t)) for t in np.linspace(0,1,100)]
    mb.sweep(pts,[.15 if KEY=='redplates' else .105]*len(pts),'redline',sides=8)
    count=15 if KEY!='reddiamonds' else 12
    for j,t in enumerate(.085+.905*(1-(1-np.linspace(0,1,count))**1.6)):
        t=float(t);p=path(sign,t)
        tangent=(path(sign,min(1,t+.002))-path(sign,max(0,t-.002))).normalized()
        outward=Vector((sign*tangent.y,-sign*tangent.x,0))
        r=.70+3.80*(1-t)**.85
        binding=mb.weights_at(mb.center(p.y))
        # Tiny depth offsets make overlaps readable without scattering the silhouette.
        p.z=-.55+.065*j
        if KEY=='redplates':
            phase=math.radians(23)
            points=[p+r*(math.cos(phase+k*math.tau/3)*outward+math.sin(phase+k*math.tau/3)*tangent) for k in range(3)]
            filled_triangle(points,.34,binding)
        elif KEY=='redtriangles':
            # The apex follows the limb tangent, so triangle outlines fan along the arc.
            phase=math.pi/2
            points=[p+r*(math.cos(phase+k*math.tau/3)*outward+math.sin(phase+k*math.tau/3)*tangent) for k in range(3)]
            polyline(points+[points[0]],.185,'redline',binding)
        else:
            length=1.6+3.65*(1-t)**.7;width=.65+1.45*(1-t)**.8
            points=[p+tangent*length,p+outward*width,p-tangent*length,p-outward*width]
            polyline(points+[points[0]],.17,'redline',binding)
        module_records.append({'side':sign,'index':j,'center':tuple(p),'outline':[tuple(q) for q in points],'weights':binding})
    # The string remains attached at the exact reference tip, independent of decoration.
    tip=Vector((STRING_X,ANCHORS[sign],-.02))
    polyline([path(sign,1),tip],.12,'redline',{'Bow_UpBone2' if sign>0 else 'Bow_LoBone2':1.0})

stringpts=[(STRING_X,float(y),-.02) for y in np.linspace(ANCHORS[-1],ANCHORS[1],121)]
mb.sweep(stringpts,[.070]*len(stringpts),'redstring',string_weights,sides=6)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True);root.name=KEY+'_ROOT';root['pynNodeName']=KEY;rig.name=KEY+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(KEY+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.003,.003,.003,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.1
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.resolution_x=1000;scene.render.resolution_y=1600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('Red bow preview');cam=bpy.data.objects.new('Red bow preview',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-220);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=125;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear()
layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.name='Preview bloom - ENB dependent in game';glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.03;glare.size=7;glare.mix=-.80
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(KEY+'.blend')))
scene.render.filepath=str(ART/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.4.0','key':KEY,'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'shapes':len(objects),'modules':module_records,'star_triangles':star_triangles,'star_radius':STAR_RADIUS,'star_z':STAR_Z,'string_anchors':stringpts[::120],'emission':{'redface':6.0,'redline':12.0,'redstring':8.0},'limitations':['preview bloom is not an in-game capture','ENB glow and first-person clearance require in-game testing']}
report['string_weight_samples']=string_samples
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RED_BOW_BUILT '+KEY+' '+str(report['triangles'])+' triangles',flush=True)
