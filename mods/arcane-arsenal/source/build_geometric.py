"""Twenty-four geometric solid-light bows on the verified vanilla bow skeleton.

Blender --background --python-exit-code 1 --python this.py -- geohexagonred
The output blend is the source mesh; native draw particles are appended separately.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,math,json,Vector,ROOT,ART,TEX,MESH,ref,root,rig
from geometric_helpers import string_weights,texture,polyline,ANCHORS,STRING_X

KEY=sys.argv[sys.argv.index('--')+1]
SPEC=next(s for s in json.loads((ROOT/'source/geometric_catalog.json').read_text(encoding='utf-8')) if s['key']==KEY)
DESIGN=SPEC['design'];MID={'Bow_MidBone':1.0}
di=texture(SPEC['diffuse_name'],tuple(SPEC['diffuse_color'])+(1,))
ni=texture('aa_red_n',(.5,.5,1,0),True);gi=texture('aa_red_g',(1,1,1,1))
for index,category in enumerate(('GeometricBody','GeometricEdge','GeometricString')):
    mat=mb.base_mat.copy();mat.name=KEY+'_'+category
    nodes=mat.node_tree.nodes;shader=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE':nodes.remove(node)
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    shader.inputs['Emission Color'].default_value=tuple(SPEC['color'] if index==0 else SPEC['edge'])+(1,)
    shader.inputs['Emission Strength'].default_value=SPEC['power'][index]
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

def line(points,width=.16,category='GeometricEdge',binding=None):
    polyline(points,width,category,binding)

def rail_rim(points,width,station_weights):
    """Share each body station's weights so luminous rims cannot peel away on flex."""
    verts=[];faces=[];uv=[];weights=[];sides=8
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
        side=tangent.cross(Vector((0,0,1))).normalized()
        normal=tangent.cross(side).normalized()
        for j in range(sides):
            angle=math.tau*j/sides
            verts.append(tuple(p+width*(math.cos(angle)*side+math.sin(angle)*normal)))
            uv.append((j/sides,i/(len(points)-1)))
            weights.append(station_weights[i])
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides
                faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))])
    mb.batches['GeometricEdge'].add(verts,faces,uv,weights)

def ribbon(points,widths,depth=.65,binding=None,edge=.065,width_scale=None):
    """Faceted rectangular rail with bright front/back rims and a darker face."""
    width_scale=width_scale or 1.0
    widths=[w*width_scale for w in widths];depth*=1.0
    pts=[Vector(p) for p in points];verts=[];uv=[];weights=[];faces=[];rims=[[],[],[],[]]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        side=Vector((tangent.y,-tangent.x,0)).normalized()
        for j,(s,z) in enumerate(((-1,-1),(1,-1),(1,1),(-1,1))):
            v=p+side*widths[i]*s+Vector((0,0,z*depth/2))
            verts.append(tuple(v));uv.append((j/3,i/(len(pts)-1)))
            weights.append(binding or mb.weights_at(mb.center(p.y)));rims[j].append(v)
        if i:
            a=(i-1)*4
            for j in range(4):faces.append((a+j,a+(j+1)%4,a+4+(j+1)%4,a+4+j))
    faces.extend([(3,2,1,0),tuple((len(pts)-1)*4+j for j in range(4))])
    # The ring uses +Z rather than tangent.cross(side); reverse its winding so
    # the solid rail faces outward with Skyrim's single-sided glow material.
    faces=[tuple(reversed(face)) for face in faces]
    volume=sum(Vector(verts[f[0]]).dot(Vector(verts[f[j]]).cross(Vector(verts[f[j+1]])))/6 for f in faces for j in range(1,len(f)-1))
    assert volume>0,'Inverted solid rail'
    mb.batches['GeometricBody'].add(verts,faces,uv,weights)
    if edge:
        for rim in rims:rail_rim(rim,edge,weights[::4])

def plate(points,depth=.6,binding=None):
    """Convex solid triangle/quad, bevel-like central ridge on each face."""
    depth*=1.0
    pts=[Vector(p) for p in points];binding=binding or mb.weights_at(mb.center(sum(p.y for p in pts)/len(pts)))
    if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:pts.reverse()
    c=sum(pts,Vector())/len(pts);n=len(pts)
    verts=[tuple(p+Vector((0,0,z*depth*.27))) for z in (-1,1) for p in pts]
    verts += [tuple(c+Vector((0,0,z*depth*.6))) for z in (-1,1)]
    faces=[]
    for i in range(n):
        j=(i+1)%n;faces.extend([(j,i,2*n),(i+n,j+n,2*n+1),(i,j,j+n,i+n)])
    mb.batches['GeometricBody'].add(verts,faces,[(.5,.5)]*len(verts),[binding]*len(verts))
    for z in (-1,1):
        rim=[p+Vector((0,0,z*depth*.27)) for p in pts]
        line(rim+[rim[0]],.065,binding=binding)


def path(sign,t):
    return Vector((1.3+10*math.sin(math.pi*t)-14.974*t**1.65,
                   sign*(8+(abs(ANCHORS[sign])-8)*t),0))

def basis(sign,t):
    tangent=(path(sign,min(1,t+.001))-path(sign,max(0,t-.001))).normalized()
    return tangent,Vector((sign*tangent.y,-sign*tangent.x,0))

def frame(points,width,depth,binding):
    for a,b in zip(points,points[1:]+points[:1]):
        ribbon([a,b],[width,width],depth,binding,.085)

def polygon(center,radius,count,phase=math.pi/2):
    return [center+Vector((radius*math.cos(phase+j*math.tau/count),radius*math.sin(phase+j*math.tau/count),0)) for j in range(count)]

anchors=[]
FLOW_DESIGNS={'plates','hexagon','squares','diamonds','triangles','chevron'}
if DESIGN in FLOW_DESIGNS:
    from geometric_flow import build_flow,GRIP_STYLES
    anchors=build_flow(DESIGN,rail_rim)
    stringpts=[(STRING_X,float(y),-.02) for y in np.linspace(ANCHORS[-1],ANCHORS[1],121)]
    mb.sweep(stringpts,[.085]*len(stringpts),'GeometricString',string_weights,sides=6)
elif SPEC['classic_source']:
    # Copy the approved source vertices and weights rather than approximating them.
    # Snapshot is immutable because the red source keys are also migration outputs.
    source=ROOT/'art/geometry-templates'/(SPEC['classic_source']+'.blend')
    original_objects=set(bpy.data.objects)
    with bpy.data.libraries.load(str(source)) as (available,loaded):
        loaded.objects=[name for name in available.objects if name in ('AA_redface','AA_redline','AA_redstring')]
    categories={'AA_redface':'GeometricBody','AA_redline':'GeometricEdge','AA_redstring':'GeometricString'}
    for obj in loaded.objects:
        category=categories[obj.name]
        verts=[tuple(v.co) for v in obj.data.vertices]
        faces=[tuple(p.vertices) for p in obj.data.polygons]
        uv=[(.5,.5)]*len(verts)
        if obj.data.uv_layers.active:
            for loop in obj.data.loops:uv[loop.vertex_index]=tuple(obj.data.uv_layers.active.data[loop.index].uv)
        weights=[{obj.vertex_groups[g.group].name:g.weight for g in v.groups if obj.vertex_groups[g.group].name in mb.bone_names} for v in obj.data.vertices]
        mb.batches[category].add(verts,faces,uv,weights)
    for obj in list(bpy.data.objects):
        if obj not in original_objects:bpy.data.objects.remove(obj,do_unlink=True)
    for sign in (-1,1):
        for j,t in enumerate((.20,.36,.53)):
            y=sign*(8+(abs(ANCHORS[sign])-8)*t)
            x=1.3+4*math.sin(math.pi*t)-14.974*t**1.8
            p=Vector((x+4.2,y,-2.7));weights=mb.weights_at(mb.center(y))
            anchors.append({'position':list(p),'bone':max(weights,key=weights.get),'side':sign})
    stringpts=[(STRING_X,ANCHORS[-1],-.02),(STRING_X,ANCHORS[1],-.02)]
else:
    line([(1.3,-7,0),(1.3,7,0)],.48,'GeometricBody',MID)
    for z in (-.45,.45):line([(1.3,-6,z),(1.3,6,z)],.085,binding=MID)
    # Match the classic three designs: radius 8, Z -3.8, two opposing triangles.
    # Rigid middle-bone binding keeps this emblem independent of limb flex.
    core=Vector((1.3,0,-3.8))
    for phase in (math.pi/2,-math.pi/2):
        points=polygon(core,8,3,phase)
        line(points+[points[0]],.24,binding=MID)
    for sign in (-1,1):
        ts=np.linspace(0,1,85);rail=[path(sign,float(t)) for t in ts]
        # The supporting rail is visible behind the repeating open frames.
        ribbon(rail,[.32]*len(rail),.65,edge=.075)
        ribbon([Vector((1.3,sign*5.6,0)),path(sign,0)],[.5,.65],.9,MID,.085)
        count=11 if DESIGN=='hexagon' else 13 if DESIGN=='squares' else 15
        for j,t in enumerate(.065+.915*(1-(1-np.linspace(0,1,count))**1.5)):
            t=float(t);p=path(sign,t);a,b=basis(sign,t)
            r=.48+4.9*(1-t)**.83
            w=mb.weights_at(mb.center(p.y))
            if DESIGN=='hexagon':
                points=[p+r*(math.cos(math.pi/6+k*math.tau/6)*b+math.sin(math.pi/6+k*math.tau/6)*a) for k in range(6)]
                frame(points,max(.19,.12*r),1.15,w)
                # A fine outward rail and short ties echo the concept's crown.
                out=p+b*r*1.04
                line([out,out+b*1.1],.14,binding=w)
            elif DESIGN=='squares':
                # Alternate in depth as well as angle, retaining a clear square hole.
                angle=.15*math.sin(j*.8);depth_axis=Vector((0,0,1))
                transverse=b*math.cos(.28*math.sin(j*.9))+depth_axis*math.sin(.28*math.sin(j*.9))
                points=[p+r*(math.cos(math.pi/4+angle+k*math.pi/2)*transverse+math.sin(math.pi/4+angle+k*math.pi/2)*a) for k in range(4)]
                frame(points,max(.18,.14*r),1.15,w)
            else:
                # Long sharp feather blades mix broad faces with hollow triangles.
                points=[p-a*r*.95-b*.5,p+a*r*1.03-b*.25,p-a*r*.60+b*r*1.55]
                if j%2==0:plate(points,1.0,w)
                else:frame(points,max(.15,.1*r),.9,w)
        tip=Vector((STRING_X,ANCHORS[sign],-.02))
        bound={'Bow_UpBone2' if sign>0 else 'Bow_LoBone2':1.0}
        ribbon([path(sign,.95),tip,tip+Vector((-1.8,sign*3.5,0))],[.65,.95,.035],1.05,bound,.085)
        for j,t in enumerate((.18,.34,.51)):
            p=path(sign,t)+basis(sign,t)[1]*6+Vector((0,0,-2.7))
            w=mb.weights_at(mb.center(p.y))
            anchors.append({'position':list(p),'bone':max(w,key=w.get),'side':sign})
    stringpts=[(STRING_X,float(y),-.02) for y in np.linspace(ANCHORS[-1],ANCHORS[1],121)]
    mb.sweep(stringpts,[.085]*len(stringpts),'GeometricString',string_weights,sides=6)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True);root.name=KEY+'_ROOT';root['pynNodeName']=KEY;rig.name=KEY+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(KEY+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
# Preserve a reproducible clean geometry base for native particle construction.
base=ROOT/'build/geometric-base';base.mkdir(exist_ok=True)
(base/(KEY+'.nif')).write_bytes((MESH/(KEY+'.nif')).read_bytes())
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.009,.013,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.resolution_x=700;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('Geometric preview');cam=bpy.data.objects.new('Geometric preview',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-220);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=129;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear()
layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.06;glare.size=7;glare.mix=-.88
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(KEY+'.blend')))
scene.render.filepath=str(ART/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.11.0' if DESIGN in ('triangles','chevron') else '0.10.1','key':KEY,'design':DESIGN,'core':GRIP_STYLES[DESIGN] if DESIGN in FLOW_DESIGNS else 'static_hexagram_radius_8','triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'shapes':len(objects),'particle_anchors':anchors,'string_anchors':[stringpts[0],stringpts[-1]],'power':SPEC['power'],'preview':'Actual source geometry; native particles not rendered; game bloom depends on ENB.'}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GEOMETRIC_BUILT '+KEY+' '+str(report['triangles'])+' triangles',flush=True)
