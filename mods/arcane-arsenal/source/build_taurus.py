"""Four distinct Taurus solid-light bows on the verified vanilla bow skeleton.

Blender --background --python-exit-code 1 --python this.py -- taurusred
The output blend is the source mesh; native draw particles are appended separately.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,math,json,Vector,ROOT,ART,TEX,MESH,ref,root,rig
from geometric_helpers import string_weights,texture,polyline,ANCHORS,STRING_X

KEY=sys.argv[sys.argv.index('--')+1]
SPEC=next(s for s in json.loads((ROOT/'source/taurus_catalog.json').read_text(encoding='utf-8')) if s['key']==KEY)
DESIGN=SPEC['design'];MID={'Bow_MidBone':1.0}
di=texture(SPEC['diffuse_name'],tuple(SPEC['diffuse_color'])+(1,))
ni=texture('aa_red_n',(.5,.5,1,0),True);gi=texture('aa_red_g',(1,1,1,1))
for index,category in enumerate(('TaurusBody','TaurusEdge','TaurusString')):
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

def line(points,width=.16,category='TaurusEdge',binding=None):
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
    mb.batches['TaurusEdge'].add(verts,faces,uv,weights)

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
    mb.batches['TaurusBody'].add(verts,faces,uv,weights)
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
    mb.batches['TaurusBody'].add(verts,faces,[(.5,.5)]*len(verts),[binding]*len(verts))
    for z in (-1,1):
        rim=[p+Vector((0,0,z*depth*.27)) for p in pts]
        line(rim+[rim[0]],.065,binding=binding)


def path(sign,t):
    # A wider bowed arch than Aries; final point is the exact tested string anchor.
    knots=[(1.3,7),(3.4,13),(7,22),(9,31),(4,41),(-5.5,50),(STRING_X,abs(ANCHORS[sign]))]
    if DESIGN=='tidal_gate':knots=[(1.3,7),(4,13),(10,22),(12,31),(8,41),(-3,50),(STRING_X,abs(ANCHORS[sign]))]
    v=t*(len(knots)-1);i=min(len(knots)-2,int(v));a,b=knots[i:i+2];f=v-i
    return Vector((a[0]+(b[0]-a[0])*f,sign*(a[1]+(b[1]-a[1])*f),0))

def basis(sign,t):
    tangent=(path(sign,min(1,t+.001))-path(sign,max(0,t-.001))).normalized()
    return tangent,Vector((sign*tangent.y,-sign*tangent.x,0))

def fork(sign,coords,width=1.3,z=0,at=23):
    pts=[Vector((x,sign*y,z)) for x,y in coords]
    binding=mb.weights_at(mb.center(sign*at))
    widths=[width]*len(pts);widths[0]=.055;widths[-1]=.055
    ribbon(pts,widths,1.45,binding,.14)

def diamond(sign,t,length,width,solid=False):
    p=path(sign,t);a,b=basis(sign,t)
    pts=[p+a*length,p+b*width,p-a*length,p-b*width]
    weights=mb.weights_at(mb.center(p.y))
    if solid:plate(pts,1.3,weights)
    else:
        # Individual thick beams leave a large clean window, unlike thin wirework.
        for start,end in zip(pts,pts[1:]+pts[:1]):
            ribbon([start,end],[.57,.57],1.0,weights,.13)

line([(1.3,-7,0),(1.3,7,0)],.57,'TaurusBody',MID)
for z in (-.56,.56):line([(1.3,-6,z),(1.3,6,z)],.13,binding=MID)
anchors=[]
for sign in (-1,1):
    # Angular collars stay outside the player's palm and arrow lane.
    for y in (7.7,10):
        plate([(0,sign*(y-1),0),(2.6,sign*(y-1),0),(3.1,sign*(y+1),0),(-.5,sign*(y+1),0)],1.6,MID)
    ts=np.linspace(0,1,42);rail=[path(sign,float(t)) for t in ts]
    if DESIGN=='bull_crown':
        for side in (-1,1):
            pts=[p+basis(sign,float(t))[1]*(1.1*math.sin(math.pi*float(t)))*side+Vector((0,0,side*.38)) for p,t in zip(rail,ts)]
            ribbon(pts,[.68]*len(pts),1.05,edge=.14)
        fork(sign,[(2,34),(4,27),(7,20),(16,24),(21,30),(20,37),(16,41)],1.8,at=25)
        # Tapered solid plates give this variant the broadest shoulder mass.
        for j,t in enumerate((.26,.4,.56,.72,.85)):
            p=path(sign,t);a,b=basis(sign,t);w=2.9*(1-t)+.7
            plate([p-a*5.5-b*.6,p+a*6.5,p-a*2+b*w],1.6)
        for t in (.2,.44,.66):
            p=path(sign,t);a,b=basis(sign,t)
            plate([p-a*.9-b*1.5,p-a*.9+b*1.5,p+a*.9+b*1.5,p+a*.9-b*1.5],1.5)
    elif DESIGN=='jade_horn':
        ribbon(rail,[.60]*len(rail),1.0,edge=.12)
        for t,length,width in ((.19,6.5,3.7),(.43,8,4.3),(.67,7,3.6),(.86,4.8,2)):
            diamond(sign,t,length,width)
        fork(sign,[(3,39),(5,32),(9,27),(17,31),(21,38),(18,44)],1.25,at=29)
        # Short solid rhombi reinforce the joints without filling the large windows.
        for t in (.06,.31,.55,.79,.96):diamond(sign,t,2.0,1.5,True)
    elif DESIGN=='tidal_gate':
        # Three broad rails, with long channels and only four cross braces.
        for side in (-1,0,1):
            pts=[p+basis(sign,float(t))[1]*(3.25*math.sin(math.pi*float(t)))*side for p,t in zip(rail,ts)]
            ribbon(pts,[.68 if side else .85]*len(pts),1.25,edge=.14)
        for t in (.17,.39,.62,.82):
            p=path(sign,t);a,b=basis(sign,t);w=3.25*math.sin(math.pi*t)+1
            plate([p-a*1.2-b*w,p-a*1.2+b*w,p+a*1.2+b*w,p+a*1.2-b*w],1.65)
        # Paired horn tips, like the concept's sweeping open gate; no ram spiral.
        bound={'Bow_UpBone2' if sign>0 else 'Bow_LoBone2':1.0}
        for side in (-1,1):
            pts=[Vector((x,sign*y,0)) for x,y in [(STRING_X,52),(STRING_X+side*2.8,55),(STRING_X+side*4.5,59),(STRING_X+side*3.5,63)]]
            ribbon(pts,[1.25,1.6,1,.04],1.45,bound,.14)
    else:
        ribbon(rail,[.63]*len(rail),1.15,edge=.13)
        for t,length,width in ((.16,5.8,2.6),(.39,7,3.7),(.64,7,3.1),(.84,5,2.1)):
            diamond(sign,t,length,width)
        for t in (.32,.69):diamond(sign,t,4,2.2,True)
        # Three graduated open bull-horn forks with deliberate depth separation.
        for j in range(3):
            dy=j*3.5;scale=1-j*.15
            coords=[(3+(x-3)*scale,20+(y-20)*scale+dy) for x,y in [(1,29),(3,21),(11,23),(19,28),(21,34)]]
            fork(sign,coords,1.05-j*.12,z=(j-1)*1.45,at=25)
    tip=Vector((STRING_X,ANCHORS[sign],-.02))
    bound={'Bow_UpBone2' if sign>0 else 'Bow_LoBone2':1.0}
    line([path(sign,1),tip],.32,binding=bound)
    if DESIGN!='tidal_gate':
        # Broad faceted tips extend past the string attachment as decoration.
        start=path(sign,.94);end=tip+Vector((-1.3,sign*4,0))
        ribbon([start,tip,end],[.8,1.25,.035],1.4,bound,.13)
    for j,t in enumerate((.19,.34,.52)):
        p=path(sign,t)+basis(sign,t)[1]*(4.5+j*.65)+Vector((0,0,-2.7))
        weights=mb.weights_at(mb.center(p.y));bone=max(weights,key=weights.get)
        anchors.append({'position':list(p),'bone':bone,'side':sign})

stringpts=[(STRING_X,float(y),-.02) for y in np.linspace(ANCHORS[-1],ANCHORS[1],121)]
mb.sweep(stringpts,[.11]*len(stringpts),'TaurusString',string_weights,sides=6)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True);root.name=KEY+'_ROOT';root['pynNodeName']=KEY;rig.name=KEY+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(KEY+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
# Preserve a reproducible clean geometry base for native particle construction.
base=ROOT/'build/taurus-base';base.mkdir(exist_ok=True)
(base/(KEY+'.nif')).write_bytes((MESH/(KEY+'.nif')).read_bytes())
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.009,.013,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.resolution_x=700;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('Taurus preview');cam=bpy.data.objects.new('Taurus preview',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-220);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=129;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear()
layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.06;glare.size=7;glare.mix=-.88
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(KEY+'.blend')))
scene.render.filepath=str(ART/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.7.0','key':KEY,'design':DESIGN,'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'shapes':len(objects),'particle_anchors':anchors,'string_anchors':stringpts[::120],'power':SPEC['power'],'preview':'Actual source geometry; native particles not rendered; game bloom depends on ENB.'}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TAURUS_BUILT '+KEY+' '+str(report['triangles'])+' triangles',flush=True)
