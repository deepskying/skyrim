"""Four distinct Aries solid-light bows on the verified vanilla bow skeleton.

Blender --background --python-exit-code 1 --python this.py -- ariesred
The output blend is the source mesh; native draw particles are appended separately.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,math,json,Vector,ROOT,ART,TEX,MESH,ref,root,rig
from geometric_helpers import string_weights,texture,polyline,ANCHORS,STRING_X

KEY=sys.argv[sys.argv.index('--')+1]
SPEC=next(s for s in json.loads((ROOT/'source/aries_catalog.json').read_text(encoding='utf-8')) if s['key']==KEY)
DESIGN=SPEC['design'];MID={'Bow_MidBone':1.0}
di=texture(SPEC['diffuse_name'],tuple(SPEC['diffuse_color'])+(1,))
ni=texture('aa_red_n',(.5,.5,1,0),True);gi=texture('aa_red_g',(1,1,1,1))
for index,category in enumerate(('AriesBody','AriesEdge','AriesString')):
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

def line(points,width=.16,category='AriesEdge',binding=None):
    polyline(points,width*(3.8 if category=='AriesEdge' else 1),category,binding)

def ribbon(points,widths,depth=.65,binding=None,edge=.065,width_scale=None):
    """Faceted rectangular rail with bright front/back rims and a darker face."""
    width_scale=width_scale or (3.5 if max(widths)<.8 else 1.7)
    widths=[w*width_scale for w in widths];depth*=2.3
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
    mb.batches['AriesBody'].add(verts,faces,uv,weights)
    if edge:
        for rim in rims:line(rim,edge,binding=binding)

def plate(points,depth=.6,binding=None):
    """Convex solid triangle/quad, bevel-like central ridge on each face."""
    depth*=1.8
    pts=[Vector(p) for p in points];binding=binding or mb.weights_at(mb.center(sum(p.y for p in pts)/len(pts)))
    if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:pts.reverse()
    c=sum(pts,Vector())/len(pts);n=len(pts)
    verts=[tuple(p+Vector((0,0,z*depth*.27))) for z in (-1,1) for p in pts]
    verts += [tuple(c+Vector((0,0,z*depth*.6))) for z in (-1,1)]
    faces=[]
    for i in range(n):
        j=(i+1)%n;faces.extend([(j,i,2*n),(i+n,j+n,2*n+1),(i,j,j+n,i+n)])
    mb.batches['AriesBody'].add(verts,faces,[(.5,.5)]*len(verts),[binding]*len(verts))
    for z in (-1,1):
        rim=[p+Vector((0,0,z*depth*.27)) for p in pts]
        line(rim+[rim[0]],.065,binding=binding)

def path(sign,t):
    knots=[(1.3,7),(3.4,14),(6.3,23),(5.8,32),(-1.5,43),(-10.8,52),(STRING_X,abs(ANCHORS[sign]))]
    v=t*(len(knots)-1);i=min(len(knots)-2,int(v));a,b=knots[i:i+2];f=v-i
    return Vector((a[0]+(b[0]-a[0])*f,sign*(a[1]+(b[1]-a[1])*f),0))

def basis(sign,t):
    tangent=(path(sign,min(1,t+.001))-path(sign,max(0,t-.001))).normalized()
    return tangent,Vector((sign*tangent.y,-sign*tangent.x,0))

def horn(sign,scale=1,z=0,shift=0,width=1.0):
    # An angular ram curl, deliberately open toward the grip, on each shoulder.
    coords=[(4,18),(13,21),(19,28),(18,34),(13,37),(8,34),(9,29),(13,27),(14,30)]
    pts=[Vector((4+(x-4)*scale,sign*(18+(y-18)*scale+shift),z)) for x,y in coords]
    binding=mb.weights_at(mb.center(sign*(24+shift)))
    ribbon(pts,[width*v for v in (1.0,1.1,1.05,.95,.85,.7,.5,.3,.045)],.8,binding,.075,width_scale=1.8)

line([(1.3,-7,0),(1.3,7,0)],.54,'AriesBody',MID)
# Low-key grip rails, with no floating emblem in the arrow/hand lane.
for z in (-.5,.5):line([(1.3,-6,z),(1.3,6,z)],.065,binding=MID)
anchors=[]
for sign in (-1,1):
    for y in (7,9):
        line([(0.3,sign*y,-.65),(2.3,sign*y,-.65),(2.3,sign*y,.65),(.3,sign*y,.65),(.3,sign*y,-.65)],.10,binding=MID)
    rail=[path(sign,float(t)) for t in np.linspace(0,1,36)]
    if DESIGN=='twin_horn':
        for side in (-1,1):
            pts=[p+basis(sign,float(t))[1]*(1.3*math.sin(math.pi*float(t)))*side+Vector((0,0,side*.25)) for p,t in zip(rail,np.linspace(0,1,len(rail)))]
            ribbon(pts,[.22]*len(rail),.34,edge=.07)
        horn(sign,width=1.15)
        for t in (.25,.43,.62,.79):
            p=path(sign,t);line([p+Vector((0,0,-.85)),p+Vector((0,0,.85))],.10)
    elif DESIGN=='layered_crown':
        ribbon(rail,[.55]*len(rail),.75)
        horn(sign,scale=.93,width=1.8)
        for j,t in enumerate(np.linspace(.2,.88,8)):
            p=path(sign,float(t));a,b=basis(sign,float(t));w=3.7*(1-float(t))+.4
            plate([p-a*5-b*.5,p+a*7,p-a*2+b*w],.85)
    elif DESIGN=='open_chevron':
        line(rail,.13)
        for j,t in enumerate(np.linspace(.16,.87,7)):
            p=path(sign,float(t));a,b=basis(sign,float(t));w=3.8*(1-float(t))+.45
            pts=[p-a*6-b*w*.6,p+a*7,p-a*4+b*w]
            line(pts+[pts[0]],.18,binding=mb.weights_at(mb.center(p.y)))
            plate([pts[1],pts[1]-a*2+b*.55,pts[1]-a*2-b*.55],.35)
        horn(sign,scale=.42,shift=-3,width=.55)
    elif DESIGN=='twin_rails':
        for side in (-1,1):
            pts=[p+basis(sign,float(t))[1]*(1.0*math.sin(math.pi*float(t)))*side for p,t in zip(rail,np.linspace(0,1,len(rail)))]
            ribbon(pts,[.14]*len(pts),.38,edge=.055)
        for t in (.25,.4,.55,.7,.83):
            p=path(sign,t);a,b=basis(sign,t)
            line([p-a*.8-b*.9,p+a*.8+b*.9],.09)
        horn(sign,scale=.7,shift=2,width=.45)
    elif DESIGN=='layered_horns':
        line(rail,.16)
        for t in (.2,.38,.57,.76,.9):
            p=path(sign,t);a,b=basis(sign,t);w=2.7*(1-t)+.45
            pts=[p+a*6,p+b*w,p-a*6,p-b*w]
            line(pts+[pts[0]],.18,binding=mb.weights_at(mb.center(p.y)))
        for scale,z in ((1.0,1.3),(.78,0),(.56,-1.3)):horn(sign,scale,z,0,.65)
    elif DESIGN=='faceted_horns':
        ribbon(rail,[.75+1.1*math.sin(math.pi*t) for t in np.linspace(0,1,len(rail))],1.6,edge=.055)
        horn(sign,scale=1.02,width=2.0)
        for t in (.24,.4,.57,.72,.87):
            p=path(sign,t);a,b=basis(sign,t);w=4*(1-t)+.6
            plate([p-a*5-b*.8,p+a*6,p-a*2+b*w],1.8)
    else:
        line(rail,.10)
        for t in (.2,.4,.6,.79,.91):
            p=path(sign,t);a,b=basis(sign,t);w=3.1*(1-t)+.4
            pts=[p+a*7,p+b*w,p-a*7,p-b*w]
            ribbon(pts+[pts[0]],[.18]*5,.5,mb.weights_at(mb.center(p.y)),.065)
        horn(sign,scale=.88,width=.6)
    tip=Vector((STRING_X,ANCHORS[sign],-.02));p=path(sign,.93)
    binding={'Bow_UpBone2' if sign>0 else 'Bow_LoBone2':1.0}
    for side in (-1,1):
        end=tip+Vector((side*1.5,sign*3,side*.25))
        ribbon([p,tip+Vector((side*.7,0,0)),end],[.3,.22,.025],.35,binding,.055)
    # Keep the three emitters per wing around the visible shoulders rather than
    # the bow tips, which commonly leave the first-person camera's field of view.
    for t in (.13,.30,.52):
        p=path(sign,t)+basis(sign,t)[1]*5.0+Vector((0,0,-2.5))
        # Emitters follow a real animated limb bone instead of floating at the grip.
        weights=mb.weights_at(mb.center(p.y));bone=max(weights,key=weights.get)
        anchors.append({'position':list(p),'bone':bone,'side':sign})

stringpts=[(STRING_X,float(y),-.02) for y in np.linspace(ANCHORS[-1],ANCHORS[1],121)]
mb.sweep(stringpts,[.11]*len(stringpts),'AriesString',string_weights,sides=6)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True);root.name=KEY+'_ROOT';root['pynNodeName']=KEY;rig.name=KEY+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(KEY+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
# Preserve a reproducible clean geometry base for native particle construction.
base=ROOT/'build/aries-base';base.mkdir(exist_ok=True)
(base/(KEY+'.nif')).write_bytes((MESH/(KEY+'.nif')).read_bytes())
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.009,.013,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.resolution_x=700;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('Aries preview');cam=bpy.data.objects.new('Aries preview',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-220);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=129;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear()
layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.06;glare.size=7;glare.mix=-.88
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(KEY+'.blend')))
scene.render.filepath=str(ART/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.6.1','key':KEY,'design':DESIGN,'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'shapes':len(objects),'particle_anchors':anchors,'string_anchors':stringpts[::120],'power':SPEC['power'],'line_radius_multiplier':3.8,'preview':'Actual source geometry; native particles not rendered; game bloom depends on ENB.'}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ARIES_BUILT '+KEY+' '+str(report['triangles'])+' triangles',flush=True)
