"""Frost Wyrm v2: volume sculpt, reduced game mesh, and selected-to-active baking.

This is a reproducible computational sculpt, not an AI illustration or hand sculpt.
Blender --background --python-exit-code 1 --python this_file -- clay|finish
The clay stage saves editable high/low surfaces; finish bakes their actual relief.
"""
import sys, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy, np, math, random, Vector, Matrix, ROOT, ART, TEX, MESH
from mathutils.noise import noise_vector, fractal

STAGE = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'clay'
WORK = ART/'frostwyrm-sculpt-master.blend'
VERSION = '0.3.1'
random.seed(3916)
UP = {'Bow_UpBone2': 1.0}
LO = {'Bow_LoBone2': 1.0}
MID = {'Bow_MidBone': 1.0}
highs = []

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False); obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def apply(obj, modifier):
    activate(obj); bpy.ops.object.modifier_apply(modifier=modifier.name)

def mesh(name, verts, faces):
    data=bpy.data.meshes.new(name); data.from_pydata(verts, [], faces); data.update()
    obj=bpy.data.objects.new(name, data); bpy.context.collection.objects.link(obj)
    return obj

def join(items, name):
    activate(items[0])
    for obj in items: obj.select_set(True)
    bpy.ops.object.join(); obj=bpy.context.object; obj.name=name
    return obj

def spline(points, steps=8):
    pts=[Vector(p) for p in points]; out=[]
    for i in range(len(pts)-1):
        a,b,c,d=pts[max(i-1,0)],pts[i],pts[i+1],pts[min(i+2,len(pts)-1)]
        for t in np.linspace(0,1,steps,endpoint=False):
            t=float(t);out.append((2*b+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
    return out+[pts[-1]]

def loft(name, controls, radii, sides=20, depth=1, ridge=.0):
    """Variable elliptical sections follow anatomical control curves."""
    pts=spline(controls,6); rs=np.interp(np.linspace(0,len(radii)-1,len(pts)), np.arange(len(radii)),radii)
    verts=[]; faces=[]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        side=tangent.cross(Vector((0,0,1))).normalized(); normal=tangent.cross(side).normalized()
        for j in range(sides):
            a=math.tau*j/sides
            r=float(rs[i])*(1+ridge*math.cos(a*5))
            verts.append(tuple(p+r*(math.cos(a)*side+math.sin(a)*depth*normal)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides
                faces.append((a,b,b+sides,a+sides))
    faces += [tuple(range(sides-1,-1,-1)), tuple((len(pts)-1)*sides+j for j in range(sides))]
    return mesh(name,verts,faces)

def ellipsoid(name, loc, scale, rotation=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,location=loc)
    obj=bpy.context.object;obj.name=name;obj.scale=scale;obj.rotation_euler.z=rotation
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return obj

def volume(items,name,voxel=.12):
    obj=join(items,name)
    mod=obj.modifiers.new('Fuse anatomical volumes','REMESH');mod.mode='VOXEL';mod.voxel_size=voxel;mod.use_smooth_shade=True
    apply(obj,mod)
    smooth=obj.modifiers.new('Relax sculpt surface','SMOOTH');smooth.factor=.68;smooth.iterations=4;apply(obj,smooth)
    return obj

def carve(obj,cut):
    mod=obj.modifiers.new('Recessed anatomical cavity','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
    apply(obj,mod);bpy.data.objects.remove(cut,do_unlink=True)

def colorize(obj,mode='bone'):
    """Sculpt micro-relief and frost; colors are baked, not exported vertex paint."""
    data=obj.data;data.update()
    coords=[v.co.copy() for v in data.vertices]
    normals=[v.normal.copy() for v in data.vertices]
    adjacent=[[] for _ in coords]
    for e in data.edges:
        a,b=e.vertices;adjacent[a].append(b);adjacent[b].append(a)
    colors=data.color_attributes.new(name='SculptTint',type='FLOAT_COLOR',domain='POINT')
    for i,v in enumerate(data.vertices):
        p=obj.matrix_world@coords[i]; nv=normals[i]
        grain=fractal(p*3.8,1.0,2.05,3)-.5
        cloud=fractal(p*.38,1.0,2.0,3)-.5
        curvature=0
        if adjacent[i]:
            av=sum((coords[j] for j in adjacent[i]),Vector())/len(adjacent[i])
            edge_length=sum((coords[j]-coords[i]).length for j in adjacent[i])/len(adjacent[i])
            curvature=max(0,-(av-coords[i]).dot(nv))/max(.02,edge_length)
        # Small nonperiodic chisel marks survive on the high mesh and normal bake.
        v.co += nv*(grain*.018 + cloud*.010)
        frost=max(0,min(.85,.10+curvature*3.5+max(0,grain-.20)*.50))
        if mode=='tooth':frost=.73+cloud*.12
        core=Vector((.035,.105,.140)); rim=Vector((.52,.66,.70))
        tint=core.lerp(rim,frost)
        colors.data[i].color=(*tint,1)
    for poly in data.polygons:poly.use_smooth=True

def shell(name, outline, z, height, face=-1, variant=0):
    """A carved convex ice lamella: thin broken rim, raised keel, irregular veins.

    Unlike the previous three-ring polygon plates this surface has a dense relief
    sculpt. The frost mask follows its physical rim and ridge in object space.
    """
    points=[Vector((x,y,0)) for x,y in outline]
    c=sum(points,Vector())/len(points)
    # Piecewise linear contour preserves the artist-defined notches and points.
    contour=[]
    for i,p in enumerate(points):
        endpoint=points[(i+1)%len(points)];edge=endpoint-p
        perpendicular=Vector((-edge.y,edge.x,0)).normalized()
        for k,t in enumerate((0,.2,.4,.6,.8)):
            q=p.lerp(endpoint,t)
            if k:q+=perpendicular*random.uniform(-.16,.12)*min(1,edge.length/2)
            contour.append(q)
    sides=len(contour);rings=13;verts=[];faces=[];tints=[]
    core=Vector((.033,.113,.150)); frostcolor=Vector((.60,.73,.76))
    for j in range(rings):
        r=.02+.98*j/(rings-1)
        for k,p in enumerate(contour):
            q=c+(p-c)*r
            a=math.tau*k/sides
            # A continuous raised keel; asymmetric hollows expose overlapping layers.
            h=height*(1-r*r)**.64*(.80+.16*math.cos(2*a+variant))
            gn=fractal(Vector((q.x*.9,q.y*.9,variant*.73)),1,2.1,3)-.5
            vein=abs(math.sin(a*5.0+math.sin(r*7+variant)*.8))
            relief=(gn*.10-.085*math.exp(-(vein/.10)**2))*(math.sin(math.pi*r)**.6)
            verts.append((q.x,q.y,z+face*(h+relief)))
            border=math.exp(-((1-r)/.055)**2)
            frost=max(0,min(1,.07+border*.70+max(0,gn-.20)*.45))
            tints.append((*core.lerp(frostcolor,frost),1))
            if j:
                a0=(j-1)*sides+k;b0=(j-1)*sides+(k+1)%sides
                faces.append((a0,b0,b0+sides,a0+sides))
    faces.append(tuple(range(sides-1,-1,-1)))
    back=len(verts);verts.append((c.x,c.y,z-face*.14));tints.append((.018,.065,.085,1))
    for k in range(sides):faces.append(((rings-1)*sides+k,(rings-1)*sides+(k+1)%sides,back))
    # Consistent outward normals, regardless of the contour winding and face.
    obj=mesh(name,verts,faces);activate(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    attr=obj.data.color_attributes.new(name='SculptTint',type='FLOAT_COLOR',domain='POINT')
    for i,col in enumerate(tints):attr.data[i].color=col
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def tint_material():
    mat=bpy.data.materials.new('Sculpt color bake');mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='SculptTint'
    emission=nodes.new('ShaderNodeEmission');output=nodes.new('ShaderNodeOutputMaterial')
    # Bake fine frost grain in world space: it is continuous across the UV seams.
    geo=nodes.new('ShaderNodeNewGeometry');noise=nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=8;noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.7
    mat.node_tree.links.new(geo.outputs['Position'],noise.inputs['Vector'])
    remap=nodes.new('ShaderNodeMapRange');remap.inputs['To Min'].default_value=.72;remap.inputs['To Max'].default_value=1.18
    mat.node_tree.links.new(noise.outputs['Fac'],remap.inputs['Value'])
    mult=nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1
    mat.node_tree.links.new(attr.outputs['Color'],mult.inputs[1]);mat.node_tree.links.new(remap.outputs['Result'],mult.inputs[2])
    mat.node_tree.links.new(mult.outputs[0],emission.inputs['Color']);mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
    return mat

def low_copy(high,name,ratio):
    low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name=name
    dec=low.modifiers.new('Reduce sculpt for game','DECIMATE');dec.ratio=ratio;apply(low,dec)
    # Bake tangents against the exact triangulation that will be exported.
    tri=low.modifiers.new('Lock bake triangulation','TRIANGULATE');apply(low,tri)
    for attr in list(low.data.color_attributes):low.data.color_attributes.remove(attr)
    activate(low);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(85),island_margin=.002,area_weight=.1)
    bpy.ops.object.mode_set(mode='OBJECT')
    low.data.materials.clear();low.data.materials.append(bpy.data.materials.new(name+'_BakeTarget'));low.active_material.use_nodes=True
    return low

def rigged(obj,binding=None):
    obj.parent=mb.root
    for name in mb.bone_names:obj.vertex_groups.new(name=name)
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        ws=binding or mb.weights_at(mb.center(p.y))
        if binding is None and p.y < -51:ws=LO
        if binding is None and p.y > 46:ws=UP
        for name,w in ws.items():obj.vertex_groups[name].add([v.index],w,'REPLACE')
    obj.vertex_groups.new(name='SBP_32_BODY').add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Bow deformation','ARMATURE');mod.object=mb.rig
    for key in ('pynBlockName','pynNodeFlags','pynVertexDesc','pynSkinInstanceType','PYN_GAME','PYN_BLENDER_XF','PYN_RENAME_BONES'):
        if key in mb.ref:obj[key]=mb.ref[key]
    obj['pynNodeName']=obj.name

def geometry():
    skullparts=[ellipsoid('Braincase',(2.4,57.8,0),(4.3,3.5,2.6),-.18),
        loft('Bridge',[(1.7,60.5,0),(-3,60.0,0),(-7.7,58.7,0),(-11.8,56.9,0),(-13.674,54.97,0)],[2.1,1.65,1.45,1.1,.12],depth=1.1),
        loft('Neck',[(-5,43.5,0),(0,47,0),(5,51.8,0),(4.4,57,0)],[2.0,1.9,2.1,1.7],depth=.83)]
    for f in (-1,1):
        # The brow and cheek form a genuine bridge around a carved orbital cavity.
        skullparts += [loft('Brow',[(3,61.0,f*1.7),(-.4,61.3,f*2.5),(-3.4,60.4,f*2.1),(-6.3,59.1,f*1.45)],[1.2,.9,.65,.32]),
            loft('Zygomatic arch',[(4.3,58.4,f*2),(.8,56.2,f*2.6),(-3.8,57.4,f*1.8),(-7.6,57.5,f*1.35)],[1.25,.7,.6,.40]),
            loft('Upper gum',[(2,55.4,f*1.7),(-3,56.8,f*1.75),(-7.8,57.35,f*1.4),(-12.8,55.9,f*.75)],[.65,.57,.50,.22]),
            loft('Temporal horn',[(3.5,59.8,f*1.7),(7,63.3,f*2.5),(13,65.5,f*2.7),(20,66.0,f*2.2),(27,64.8,f*1.8)],[1.75,1.25,.8,.35,.035],ridge=.08),
            loft('Cheek spur',[(3.7,56.5,f*2.1),(8,58.7,f*3.4),(12.5,59.5,f*3.8)],[1.4,.65,.04],ridge=.1),
            loft('Mandible',[(3.6,54.9,f*1.6),(2.2,52.0,f*1.85),(-2,49.9,f*1.5),(-8,48.1,f*1.1),(-12.7,49.5,f*.15)],[1.15,.9,.67,.55,.03],ridge=.04)]
    skullparts += [loft('Frontal crest',[(-3.3,60.3,0),(-1,62.4,0),(3.5,63.6,0),(7.5,64.5,0)],[1.2,.8,.40,.025],depth=.55),
        loft('Nasal barb',[(-10.8,57.4,0),(-10.6,59,0),(-9.3,60.2,0)],[.62,.40,.025],depth=.6)]
    head=volume(skullparts,'HIGH_Head',.105)
    for f in (-1,1):
        carve(head,ellipsoid('Eye socket',(-1.4,59.35,f*2.5),(2.05,1.0,1.15),-.22))
        carve(head,ellipsoid('Nostril',(-9.8,57.8,f*1.25),(.70,.36,.65),-.45))
        carve(head,ellipsoid('Temple hollow',(3.0,56.9,f*2.35),(1.2,.8,.80),.5))
    colorize(head)
    additions=[]
    # Teeth originate inside the actual gum and curve into the triangular gape.
    for f in (-1,1):
        for j,(x,y,l) in enumerate([(-11.7,56.2,1.4),(-10.1,56.85,2.2),(-8.4,57.25,1.5),(-6.7,57.3,2.5),(-4.9,57.05,1.5),(-3.1,56.7,2.0),(-1.4,56.25,1.25),(.1,55.85,.85)]):
            z=f*(.9+max(0,1-abs(x+3)/10)*.7)
            tooth=loft('Fang',[(x,y+.12,z),(x-.1,y-.5,z),(x+.22,y-l,z*.96)],[.34,.23,.008],sides=12,ridge=.04);colorize(tooth,'tooth');additions.append(tooth)
        for j,(x,y) in enumerate([(-7,47.9),(-5.3,48.6),(-3.6,49.35),(-1.8,50.1),(.1,51.1)]):
            tooth=loft('Lower fang',[(x,y-.2,f*1.1),(x-.2,y+.4,f*1.1),(x-.45,y+1.1+(j%2)*.45,f*1.1)],[.26,.18,.01],sides=12);colorize(tooth,'tooth');additions.append(tooth)
        # Broad cranial lamellae describe anatomy rather than rings around a tube.
        shapes=[([(6,60),(3,62),(5,65),(8,64),(10,66),(9,61)],f*1.4,1.0),
            ([(4,55),(2,53),(4,50),(8,52),(10,55),(7,54)],f*2,1.1),
            ([(-3,60),(-.8,61.6),(2,62.8),(3,61),(.4,60.7)],f*2.15,.45),
            ([(-5,57.4),(-7.8,59),(-10.9,58.1),(-12.8,56.6),(-9.2,57.4),(-7,56.9)],f*1.2,.40)]
        for j,(outline,z,h) in enumerate(shapes):additions.append(shell('Cranial lamella',outline,z,h,f,j))
        # Imbricated plates bridge the neck into the skull, with exposed pockets between.
        for j,(x,y,w) in enumerate([(-3,45,2.0),(-.3,47,2.2),(2.4,49,2.4),(4.2,51.6,2.1),(5.4,54,1.8)]):
            outline=[(x-w*.7,y-1),(x-w,y+.7),(x-.3,y+1.1),(x-.6,y+3.5),(x+w*.8,y+2.8),(x+w*1.2,y+4.8),(x+w,y+.3)]
            additions.append(shell('Nuchal lamella',outline,f*1.4,.85,f,j+21))
    head=join([head]+additions,'HIGH_Head');highs.append(head)

    body=[]
    for sign in (-1,1):
        ys=np.linspace(7,48 if sign==1 else 55,45)*sign
        pts=[mb.center(float(y))+Vector((3.2*math.sin(math.pi*(abs(y)-7)/48)**2,0,0)) for y in ys]
        radii=[1.12+1.25*math.sin(math.pi*(abs(float(y))-7)/48)**.65 for y in ys]
        core=loft('Continuous ice core',pts,radii,sides=16,depth=.80,ridge=.06);colorize(core);body.append(core)
        for face in (-1,1):
            # Vary both spacing and scale size. Only the broad outer sails define the silhouette.
            rows=[(10,5.6,2.6),(16.7,7.7,3.8),(25,9.8,4.0),(35,8.5,3.4),(43,6.4,2.8),(49.8,5.1,2.1)]
            if sign==1:rows=rows[:-1]
            for j,(y,length,width) in enumerate(rows):
                p=mb.center(sign*y)+Vector((3.4*math.sin(math.pi*(y-7)/48)**2,0,face*1.1))
                # Swept, deeply notched ice plates, with thin edges and a curved central keel.
                shape=[(-.72,-.30),(-1.0,.12),(-.58,.19),(-.87,.62),(-.39,.50),(-.40,1.12),(.12,.67),(.85,.90),(.57,.28),(.92,.06),(.36,-.12)]
                outline=[(p.x+x*width,p.y+sign*yy*length) for x,yy in shape]
                body.append(shell('Primary lamella',outline,p.z,1.0+width*.10,face,j+sign*4))
                # Small overlapping secondary scales cover seams without filling the cavities.
                for row in (-1,1):
                    q=p+Vector((row*width*.70,sign*length*.25,face*.35))
                    sh=[(-.5,-.12),(-.8,.2),(-.5,.5),(-.65,.85),(0,.61),(.6,1.0),(.52,.30),(.36,-.06)]
                    outline=[(q.x+x*width*.65,q.y+sign*yy*length*.60) for x,yy in sh]
                    body.append(shell('Secondary lamella',outline,q.z,.65,face,j+row+8))
                if j in (1,2,3):
                    # Large outward-facing blade with a hooked tip and recessed trailing edge.
                    q=p+Vector((width*.25,sign*1.0,-face*.25))
                    shape=[(-1,-1),(2,0),(5.5,3),(8.5,8),(8.0,12),(5.5,7),(5.2,4.3),(3.2,3),(1,3.5)]
                    outline=[(q.x+x*(1 if j==2 else .85),q.y+sign*yy) for x,yy in shape]
                    body.append(shell('Dorsal ice sail',outline,q.z,.85,face,j+12))
        for j,y in enumerate([12,20,29,38,45]):
            if sign==1 and y==45:continue
            p=mb.center(sign*y)+Vector((3,0,0))
            spur=loft('Dorsal splinter',[p,p+Vector((4,sign*3,0)),p+Vector((7,sign*9,0))],[1,.55,.015],depth=.5,ridge=.12);colorize(spur);body.append(spur)
    grip=loft('Ice grip',[(1.3,-7,0),(1.3,-3,0),(1.3,3,0),(1.3,7,0)],[1.15,1.05,1.05,1.15],sides=20,depth=.85);colorize(grip);body.append(grip)
    for face in (-1,1):
        for sign in (-1,1):
            outline=[(-1,sign*7),(-3,sign*9),(-2,sign*12),(1,sign*10),(4,sign*12),(6,sign*9),(4,sign*8)]
            body.append(shell('Grip collar',outline,face*.75,.8,face,3))
        tail=loft('Terminal hook',[(-11.4,-51,face*.4),(-13.6,-55,face*.5),(-10.6,-60.3,face*.5),(-5,-64.2,face*.4),(-5.4,-68.4,0),(-9.8,-71,0)],[1.6,1.65,1.45,1.05,.45,.018],sides=20,depth=.70,ridge=.1);colorize(tail);body.append(tail)
    body=join(body,'HIGH_Body');highs.append(body)
    sculptmat=tint_material()
    for obj in highs:obj.data.materials.clear();obj.data.materials.append(sculptmat)
    headlow=low_copy(head,'AA_SculptHead',.10);bodylow=low_copy(body,'AA_SculptBody',.22)
    rigged(headlow,UP);rigged(bodylow)
    # Eyes nest inside carved sockets. Their brightness is independent of ice reflections.
    eyes=[]
    for f in (-1,1):
        eye=ellipsoid('Recessed eye',(-1.5,59.35,f*2.15),(1.18,.37,.46),-.25)
        activate(eye);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);eyes.append(eye)
    eyes=join(eyes,'AA_Eyes');rigged(eyes,UP)
    string=loft('AA_String',[(-13.674,-54.70,-.02),(-13.674,0,-.02),(-13.674,54.97,-.02)],[.07,.07,.07],sides=6)
    # String needs dense longitudinal sampling for the two animated string bones.
    rigged(string)
    for v in string.data.vertices:
        for name in mb.bone_names:string.vertex_groups[name].remove([v.index])
        for name,w in mb.weights_at(v.co,True).items():string.vertex_groups[name].add([v.index],w,'REPLACE')
    for obj in (eyes,string):
        activate(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
    mb.root.name='frostwyrm_ROOT';mb.root['pynNodeName']='frostwyrm';mb.rig.name='frostwyrm_Rig'
    bpy.data.objects.remove(mb.ref,do_unlink=True)
    for obj in highs:obj.hide_render=True;obj.hide_set(True)
    bpy.data.objects['bhkBoxShape'].hide_render=True
    return [headlow,bodylow,eyes,string]

def aim(obj,at):
    f=(Vector(at)-obj.location).normalized();r=f.cross(Vector((0,1,0))).normalized();up=r.cross(f)
    obj.rotation_euler=Matrix((r,up,-f)).transposed().to_quaternion().to_euler()

def scene_setup():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.042,.052,.063,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.40
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
    cd=bpy.data.cameras.new('Sculpt camera');cam=bpy.data.objects.new('Sculpt camera',cd);scene.collection.objects.link(cam);cd.type='ORTHO';scene.camera=cam
    for name,loc,power,color,size in [('Main',(-40,70,-65),160000,(.90,.95,1),48),('Rim',(30,50,35),230000,(.74,.88,1),40),('Fill',(-30,-40,-40),110000,(.85,.91,1),45)]:
        ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo);lo.location=loc;ld.energy=power;ld.color=color;ld.size=size;aim(lo,(0,20,0))

def render(path,at,loc,scale,size):
    scene=bpy.context.scene;cam=scene.camera;cam.location=loc;aim(cam,at);cam.data.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size;scene.render.resolution_percentage=100;scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)

def clay(objects):
    mat=bpy.data.materials.new('Neutral clay');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.30,.32,.34,1);shader.inputs['Roughness'].default_value=.66
    saved={o.name:list(o.data.materials) for o in objects}
    for o in objects:o.data.materials.clear();o.data.materials.append(mat)
    render(ART/'frostwyrm-clay-head.png',(2,56,0),(2,56,-140),51,(1500,1050))
    render(ART/'frostwyrm-clay-quarter.png',(2,55,0),(-65,65,-125),51,(1500,1050))
    render(ART/'frostwyrm-clay-full.png',(1,0,0),(-12,4,-220),159,(1050,1650))
    for o in objects:
        o.data.materials.clear()
        for m in saved[o.name]:o.data.materials.append(m)

def components(obj):
    parent=list(range(len(obj.data.vertices)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for e in obj.data.edges:
        a,b=e.vertices;parent[find(a)]=find(b)
    groups={}
    for i in range(len(parent)):groups.setdefault(find(i),[]).append(i)
    return [np.asarray(g,dtype=np.int32) for g in groups.values()]

def explode_pair(high,low):
    """Separate matching connected parts during ray projection to stop cross-hits.

    Original arrays are restored bit-for-bit after baking. This changes neither the
    playable mesh nor the atlas; it isolates skull, teeth and overlapping lamellae.
    """
    snapshots=[];descriptors=[]
    for obj in (high,low):
        a=np.empty(len(obj.data.vertices)*3,np.float32);obj.data.vertices.foreach_get('co',a);a=a.reshape((-1,3));snapshots.append(a.copy())
        groups=components(obj)
        centers=np.array([(a[g].min(axis=0)+a[g].max(axis=0))*.5 for g in groups])
        sizes=np.array([a[g].max(axis=0)-a[g].min(axis=0) for g in groups])
        descriptors.append((groups,centers,sizes))
    hg,hc,hs=descriptors[0];lg,lc,ls=descriptors[1]
    offsets=[np.array(((i%12)*170,0,(i//12)*170),np.float32) for i in range(len(hg))]
    for obj,a,groups,centers,sizes in [(high,snapshots[0].copy(),hg,hc,hs),(low,snapshots[1].copy(),lg,lc,ls)]:
        for i,g in enumerate(groups):
            match=i if obj==high else int(np.argmin(np.linalg.norm(hc-centers[i],axis=1)+np.linalg.norm(hs-sizes[i],axis=1)*.7))
            a[g]+=offsets[match]
        obj.data.vertices.foreach_set('co',a.ravel());obj.data.update()
    return snapshots

def bake(high,low,kind,resolution):
    scene=bpy.context.scene;activate(low);high.hide_render=False;high.hide_set(False);high.select_set(True)
    # Disable the rest-pose armature during ray projection, then restore it.
    arm=low.modifiers.get('Bow deformation');arm.show_render=False;arm.show_viewport=False
    originals=explode_pair(high,low) if kind in ('NORMAL','EMIT') else None
    mat=low.active_material;nodes=mat.node_tree.nodes
    image=bpy.data.images.new('frostwyrm_v2_'+low.name[3:].lower()+'_'+kind.lower(),width=resolution,height=resolution,alpha=True,float_buffer=True)
    image.colorspace_settings.name='Non-Color' if kind in ('NORMAL','AO') else 'sRGB'
    node=nodes.new('ShaderNodeTexImage');node.image=image;nodes.active=node
    scene.render.bake.use_selected_to_active=True;scene.render.bake.use_cage=False;scene.render.bake.cage_extrusion=.22;scene.render.bake.max_ray_distance=.65;scene.render.bake.margin=12
    scene.render.bake.normal_g='NEG_Y' # Skyrim uses DirectX tangent normals.
    scene.cycles.samples=16 if kind=='AO' else 1
    bpy.ops.object.bake(type=kind)
    if originals:
        for obj,a in zip((high,low),originals):obj.data.vertices.foreach_set('co',a.ravel());obj.data.update()
    image.filepath_raw=str(ART/(image.name+'.png'));image.file_format='PNG';image.save()
    high.hide_render=True;high.hide_set(True);arm.show_render=True;arm.show_viewport=True
    return image

def pixels(image):
    p=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(p);return p.reshape((image.size[1],image.size[0],4))

def dds(name,p,noncolor=False):
    im=bpy.data.images.new(name,width=p.shape[1],height=p.shape[0],alpha=True)
    if noncolor:im.colorspace_settings.name='Non-Color'
    im.pixels.foreach_set(np.clip(p,0,1).astype(np.float32).ravel());im.filepath_raw=str(ART/(name+'.png'));im.file_format='PNG';im.save()
    exe=r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe'
    mb.subprocess.run([exe,'-nologo','-y','-f','BC3_UNORM' if noncolor else 'BC7_UNORM','-m','0','-o',str(TEX),str(ART/(name+'.png'))],check=True,capture_output=True)
    im.filepath=str(TEX/(name+'.dds'));im.reload();return im

def cubemap():
    """Original analytic six-face reflection map, legacy uncompressed DDS cube."""
    n=128;header=[124,0x100F,n,n,n*4,0,1]+[0]*11
    header += [32,0x41,0,32,0xff0000,0xff00,0xff,0xff000000,0x1008,0xfe00,0,0,0]
    assert len(header)==31
    payload=[];u,v=np.meshgrid(np.linspace(-1,1,n),np.linspace(1,-1,n))
    axes=[(np.ones_like(u),v,-u),(-np.ones_like(u),v,u),(u,np.ones_like(u),-v),(u,-np.ones_like(u),v),(u,v,np.ones_like(u)),(-u,v,-np.ones_like(u))]
    for xyz in axes:
        d=np.stack(xyz,axis=-1);d/=np.linalg.norm(d,axis=-1,keepdims=True)
        light=np.maximum(0,d@np.array((-.35,.75,.56)))**28
        strip=np.exp(-((d[:,:,0]-.30)/.13)**2)*np.maximum(0,d[:,:,1])**2
        sky=.11+.13*(d[:,:,1]+1)*.5
        rgb=np.stack([sky*.78+light*.64+strip*.23,sky*.94+light*.71+strip*.27,sky+light*.73+strip*.29],axis=-1)
        rgba=np.ones((n,n,4));rgba[:,:,:3]=np.clip(rgb,0,1)
        payload.append((rgba[:,:,[2,1,0,3]]*255).astype(np.uint8).tobytes())
    path=TEX/'frostwyrm_v2_cube.dds';path.write_bytes(b'DDS '+struct.pack('<31I',*header)+b''.join(payload));return path

def game_material(name,diffuse,normal,mask=None,cube=None,glow=False):
    mat=mb.base_mat.copy();mat.name=name;nodes=mat.node_tree.nodes;shader=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE':nodes.remove(node)
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    mat.pyn_shader.Shader_Type='Glow_Shader' if glow else 'Environment_Map'
    mat.pyn_shader.Shader_Flags_1='SPECULAR | SKINNED | RECEIVE_SHADOWS | CAST_SHADOWS | ZBUFFER_TEST'+(' | OWN_EMIT' if glow else ' | ENVIRONMENT_MAPPING')
    mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE'+(' | GLOW_MAP' if glow else '')
    mat.pyn_shader.Env_Map_Scale=.48
    shader.inputs['Glossiness'].default_value=160
    shader.inputs['Specular Color'].default_value=(.65,.76,.80,1)
    shader.inputs['Emission Color'].default_value=(.20,.65,.8,1)
    shader.inputs['Emission Strength'].default_value=.7 if glow else 0
    for slot,im,inlet in [('Diffuse',diffuse,'Diffuse'),('Normal',normal,'Normal')]+([('Glow',diffuse,'Glow Map')] if glow else []):
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\'+Path(im.filepath).name
        node=nodes.new('ShaderNodeTexImage');node.image=im;node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
        mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
    if mask:
        mat['BSShaderTextureSet_EnvMask']='textures\\weapons\\arcanearsenal\\'+Path(mask.filepath).name
    if cube:mat['BSShaderTextureSet_EnvMap']='textures\\weapons\\arcanearsenal\\'+cube.name
    return mat

def finish():
    bpy.ops.wm.open_mainfile(filepath=str(WORK))
    mb.rig=bpy.data.objects['frostwyrm_Rig'];mb.root=bpy.data.objects['frostwyrm_ROOT']
    # The base shader remains in this saved file as an unused source material.
    mb.base_mat=next(m for m in bpy.data.materials if m.use_nodes and m.node_tree.nodes.get('SkyrimShader:Default'))
    cube=cubemap();report={'version':VERSION,'method':'volume sculpt and relief surfaces, decimation, selected-to-active normal/color/AO bake','bakes':{}}
    for tag,res in [('Head',2048),('Body',4096)]:
        high=bpy.data.objects['HIGH_'+tag];low=bpy.data.objects['AA_Sculpt'+tag]
        high.data.materials.clear();high.data.materials.append(tint_material())
        nm=bake(high,low,'NORMAL',res);col=bake(high,low,'EMIT',res);ao=bake(high,low,'AO',res)
        c=pixels(col);a=pixels(ao)[:,:,0];c[:,:,:3]*=(.65+.35*a[:,:,None]);c[:,:,3]=1
        normal=pixels(nm);normal[:,:,3]=np.clip(.78-c[:,:,:3].mean(axis=2)*.8,.18,.85)
        mask=np.ones_like(c);mask[:,:,:3]=np.clip(.60-c[:,:,:3].mean(axis=2)*.60,.12,.60)[:,:,None]
        prefix='frostwyrm_v2_'+tag.lower()
        di=dds(prefix+'_d',c);ni=dds(prefix+'_n',normal,True);mi=dds(prefix+'_m',mask,True)
        low.data.materials.clear();low.data.materials.append(game_material(prefix,di,ni,mi,cube))
        report['bakes'][tag]={'resolution':res,'high_triangles':sum(len(p.vertices)-2 for p in high.data.polygons),'game_triangles':len(low.data.polygons)}
    p=np.ones((64,64,4),np.float32);p[:,:,:3]=(.28,.72,.84);di=dds('frostwyrm_v2_eye_d',p)
    p[:,:,:3]=(.5,.5,1);ni=dds('frostwyrm_v2_eye_n',p,True)
    eyes=bpy.data.objects['AA_Eyes'];eyes.data.materials.clear();eyes.data.materials.append(game_material('frostwyrm_v2_eyes',di,ni,glow=True))
    string=bpy.data.objects['AA_String'];string.data.materials.clear();string.data.materials.append(game_material('frostwyrm_v2_string',di,ni,glow=True))
    objects=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('AA_')]
    activate(objects[0])
    for obj in objects+[mb.root,mb.rig,bpy.data.objects['bhkBoxShape']]+list(mb.root.children):obj.select_set(True)
    bpy.ops.export_scene.pynifly(filepath=str(MESH/'frostwyrm.nif'),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK))
    for obj in list(bpy.data.objects):
        if obj.name.startswith('HIGH_'):bpy.data.objects.remove(obj,do_unlink=True)
    scene=bpy.context.scene;scene.cycles.samples=48
    cam=scene.camera;cam.location=(-14,4,-220);aim(cam,(1,0,0));cam.data.ortho_scale=159
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/'frostwyrm.blend'))
    render(ART/'frostwyrm.png',(1,0,0),(-14,4,-220),159,(1050,1650))
    render(ART/'frostwyrm-head.png',(2,56,0),(2,56,-140),51,(1500,1050))
    render(ART/'frostwyrm-quarter.png',(2,55,0),(-65,65,-125),51,(1500,1050))
    report['triangles']=sum(len(p.vertices)-2 for o in objects for p in o.data.polygons)
    report['shapes']=len(objects);report['limitations']=['no physical refraction','Blender preview is not an in-game capture','original simple collision','in-game ENB and draw pose require user test']
    (ROOT/'build/frostwyrm-model.json').write_text(mb.json.dumps(report,indent=2),encoding='utf-8')
    print('SCULPT_FINISHED '+mb.json.dumps(report),flush=True)

if STAGE=='clay':
    objects=geometry();scene_setup();bpy.ops.wm.save_as_mainfile(filepath=str(WORK));clay(objects)
    print('CLAY_READY',flush=True)
elif STAGE=='finish':finish()
else:raise ValueError(STAGE)
