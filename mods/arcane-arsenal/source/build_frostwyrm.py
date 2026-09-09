"""Sculpt the Frost Wyrm experiment around the verified Skyrim bow rig.

All surfaces are authored geometry. The reference supplies only rig/weapon metadata.
Run through portable Blender with --background --python-exit-code 1 --python.
"""
import sys,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,Vector,Matrix,math,json,subprocess,ART,TEX,MESH,ROOT
from mesh_builder import crystal,sweep,center,weights_at,ref,rig,root
random.seed(832)
key='frostwyrm';mid={'Bow_MidBone':1.0};upper={'Bow_UpBone2':1.0};lower={'Bow_LoBone2':1.0}
n=2048
u,v=np.meshgrid(np.linspace(0,1,n,dtype=np.float32),np.linspace(0,1,n,dtype=np.float32))
first=np.full_like(u,100);second=np.full_like(u,100)
for _ in range(46):
    sx,sy=random.random(),random.random()
    d=(u-sx)**2+(v-sy)**2
    second=np.minimum(second,np.maximum(first,d));first=np.minimum(first,d)
crack=np.exp(-((np.sqrt(second)-np.sqrt(first))/.0020)**2)
hair=np.exp(-((np.sqrt(second)-np.sqrt(first))/.00048)**2)
cloud=(np.sin(u*47+np.sin(v*29)*1.2)+np.sin(v*61-u*11))*.5
grain=np.random.default_rng(418).normal(0,.0015,u.shape).astype(np.float32)
height=.008*cloud+.009*crack
dy,dx=np.gradient(height)
normal=np.ones((n,n,4),np.float32)
normal[:,:,0]=.5-np.clip(dx*60,-.30,.30);normal[:,:,1]=.5+np.clip(dy*60,-.30,.30);normal[:,:,2]=1
texconv=Path(r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe')
def texture(name,pixels,noncolor=False):
    image=bpy.data.images.new(name,width=n,height=n,alpha=True)
    if noncolor:image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.astype(np.float32).ravel());image.filepath_raw=str(ART/(name+'.png'));image.file_format='PNG';image.save()
    subprocess.run([str(texconv),'-nologo','-y','-f','BC3_UNORM' if noncolor else 'BC7_UNORM','-m','0','-o',str(TEX),str(ART/(name+'.png'))],check=True,capture_output=True)
    image.filepath=str(TEX/(name+'.dds'));image.reload();return image
normal_image=texture(key+'_n',normal,True)
glow=np.ones_like(normal)
for ch,c in enumerate((.18,.62,.8)):glow[:,:,ch]=(hair*.25+.003)*c
glow_image=texture(key+'_g',glow)
palette={'deep':(.045,.12,.16),'ice':(.23,.39,.46),'frost':(.48,.62,.67),
         'edge':(.72,.82,.85),'eye':(.12,.72,.9),'mouth':(.008,.018,.028)}
for category,tint in palette.items():
    color=np.ones_like(normal)
    for ch,c in enumerate(tint):
        color[:,:,ch]=np.clip(c*(.76+cloud*.20)+crack*(.34 if category in ('ice','deep') else .14)+grain,0,1)
    if category=='ice':color[:,:,3]=np.clip(.80+crack*.15+cloud*.03,0,1)
    img=texture(key+'_'+category,color)
    mat=mb.base_mat.copy();mat.name=key+'_'+category
    nodes=mat.node_tree.nodes;shader=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE':nodes.remove(node)
    shader.inputs['Emission Color'].default_value=(.20,.69,.85,1)
    shader.inputs['Emission Strength'].default_value=.9 if category=='eye' else .012
    shader.inputs['Specular Color'].default_value=(.75,.90,1,1)
    shader.inputs['Glossiness'].default_value=210 if category in ('ice','deep') else 85
    mat.pyn_shader.Shader_Type='Glow_Shader'
    mat.pyn_shader.Shader_Flags_1='SPECULAR | SKINNED | RECEIVE_SHADOWS | CAST_SHADOWS | OWN_EMIT | ZBUFFER_TEST'
    mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    for slot,im,inlet in [('Diffuse',img,'Diffuse'),('Normal',normal_image,'Normal'),('Glow',glow_image,'Glow Map')]:
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\'+im.name+'.dds'
        node=nodes.new('ShaderNodeTexImage');node.image=im;node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
        mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
    if category=='ice':
        group=bpy.data.node_groups.get('AlphaProperty')
        if group is None:
            assets=mb.TOOLS/'blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly/blender_assets/Shaders.blend'
            with bpy.data.libraries.load(str(assets)) as (_,loaded):loaded.node_groups=['AlphaProperty']
            group=loaded.node_groups[0]
        alpha=nodes.new('ShaderNodeGroup');alpha.node_tree=group;alpha.name='AlphaProperty'
        alpha.inputs['Alpha Test'].default_value=False;alpha.inputs['Alpha Blend'].default_value=True
        alpha.inputs['Source Blend Mode'].default_value=6;alpha.inputs['Destination Blend Mode'].default_value=7
        mat.node_tree.links.new(nodes['Diffuse_Texture'].outputs['Alpha'],alpha.inputs['Alpha'])
        mat.node_tree.links.new(alpha.outputs[0],shader.inputs['Alpha Property'])
    mb.materials[category]=mat
mb.batches={name:mb.Batch(name) for name in palette}

def catmull(points,steps=7):
    pts=[Vector(p) for p in points];out=[]
    for i in range(len(pts)-1):
        a,b,c,d=pts[max(0,i-1)],pts[i],pts[i+1],pts[min(len(pts)-1,i+2)]
        for t in np.linspace(0,1,steps,endpoint=False):
            t=float(t);out.append((2*b+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
    return out+[pts[-1]]

def tube(points,radius,category,binding=None,tip=.06,sides=9):
    pts=catmull(points)
    radii=[float(radius*(1-i/(len(pts)-1))**.72+tip) for i in range(len(pts))]
    sweep(pts,radii,category,(lambda p:binding) if binding else None,sides=sides)

def limb(y):
    p=center(y);t=max(0,min(1,(abs(y)-7)/48));p.x+=4.2*math.sin(math.pi*t)**2
    return p

def plate(outline,z,thickness,category,binding,face=-1,rim=True):
    """A thick chamfered scale with irregular pointed outline, not a flat card."""
    points=[Vector((p[0],p[1],z)) for p in outline];c=sum(points,Vector())/len(points)
    verts=[];uv=[];count=len(points)
    xmin,xmax=min(p.x for p in points),max(p.x for p in points)
    ymin,ymax=min(p.y for p in points),max(p.y for p in points)
    uoff,voff=random.uniform(0,.45),random.uniform(0,.45)
    def mapping(q):return (uoff+.50*(q.x-xmin)/max(xmax-xmin,.01),voff+.50*(q.y-ymin)/max(ymax-ymin,.01))
    for scale,depth in [(1,0),(.80,thickness*.45),(.36,thickness)]:
        for p in points:
            q=c+(p-c)*scale;q.z=z+face*depth;verts.append(tuple(q));uv.append(mapping(q))
    apex=c.copy();apex.z=z+face*thickness*1.12;verts.append(tuple(apex));uv.append(mapping(c))
    faces=[]
    for ring in range(2):
        for j in range(count):
            a=ring*count+j;b=ring*count+(j+1)%count
            faces.append((a,b,b+count,a+count))
    for j in range(count):faces.append((2*count+j,2*count+(j+1)%count,3*count))
    faces.append(tuple(range(count-1,-1,-1)))
    # Correct outward orientation on the camera-facing negative-Z surfaces.
    area=sum(points[j].x*points[(j+1)%count].y-points[(j+1)%count].x*points[j].y for j in range(count))
    if (area>0 and face<0) or (area<0 and face>0):faces=[tuple(reversed(f)) for f in faces]
    mb.batches[category].add(verts,faces,uv,[binding]*len(verts))
    if rim:
        for indices in [(1,2,3),(4,5,6)]:
            edge=[points[j%count].copy() for j in indices]
            for p in edge:p.z+=face*.10
            tube(edge,.045,'frost',binding,tip=.015,sides=5)

def scale(p,length,width,sign,binding,face=-1,category='ice'):
    p=Vector(p)
    shape=[(-.6,-.16),(-.94,.25),(-.62,.52),(-.88,.78),(-.12,.63),(.18,1.04),(.47,.59),(.94,.70),(.67,.24),(.46,-.18)]
    outline=[(p.x+x*width,p.y+sign*y*length) for x,y in shape]
    plate(outline,p.z,random.uniform(.50,.95),category,binding,face)

# Continuous deep ice limbs and a narrow unobstructed grip.
sweep([(1.3,float(y),0) for y in np.linspace(-7,7,27)],
      [1.15+.3*(abs(float(y))/7)**2 for y in np.linspace(-7,7,27)],'deep',lambda p:mid,sides=14,depth=.86)
for side in [-1,1]:
    tube([(1.4+side*.65,-6,-.92),(1.4+side*.82,-2,-.98),(1.4+side*.75,3,-.95),(1.4+side*.60,6,-.9)],.13,'ice',mid,tip=.07,sides=6)
for sign in [-1,1]:
    ys=[float(y)*sign for y in np.linspace(7,48 if sign==1 else 55,87)];pts=[limb(y) for y in ys]
    radii=[1.3+1.65*math.sin(math.pi*(abs(y)-7)/48)**.65 for y in ys]
    sweep(pts,radii,'deep',sides=12,depth=.85)
    for front in [-1,1]:
        # Alternating scales overlap along the flexible limb, with rigid per-scale binding.
        for row in [-1,1]:
            for j,y in enumerate([10.8,16.5,22.0,28.5,34.5,40.2,45.4,49.2]):
                if sign==1 and y>40.5:continue
                p=limb(sign*(y+(1.4 if row==1 else 0)))
                p+=Vector((row*(1.0+math.sin(y/55*math.pi)*1.25),0,front*(1.05+math.sin(y/55*math.pi)*.8)))
                scale(p,random.uniform(6.8,9.7),random.uniform(2.0,3.2),sign,weights_at(center(sign*y)),front,'ice')
        for j,y in enumerate([14,22,30,38,45]):
            p=limb(sign*y)+Vector((1.4,0,front*1.2))
            # Broad swept blade ridges define the silhouette, with subordinate shards.
            blade=[(p.x+x,p.y+sign*yy) for x,yy in [(-1,-1),(3,1),(8+j*.5,5),(7+j*.6,11),(5.5,6),(3,4),(1,3)]]
            plate(blade,p.z,.75,'ice',weights_at(center(sign*y)),front)
            crystal(p+Vector((1,0,front*.5)),p+Vector((4.8,sign*6,front*3)),.78,.65,'frost',weights_at(center(sign*y)),roll=j*.5)
    # Small spinal vertebrae provide a dark/light rhythm without repeated long needles.
    for j,y in enumerate(np.linspace(11,48,13)):
        if sign==1 and y>43:continue
        y=float(y);p=limb(sign*y)+Vector((0,0,-2.1))
        scale(p,3.0,1.2,sign,weights_at(center(sign*y)),-1,'deep')
    # Angular guards are kept outside the hand's 14-unit grip region.
    for face in [-1,1]:
        p=Vector((1.4,sign*8.5,face*1.05))
        scale(p,5.2,3.3,sign,mid,face,'frost')
        tube([p,p+Vector((3,sign*1.5,0)),p+Vector((4.2,sign*5,0))],.65,'ice',mid,sides=7)

# The upper limb becomes a three-dimensional dragon skull with a separate jaw.
def skull():
    rings=[(5.2,54.8,2.5,2.2),(5,58.6,3.7,3.5),(2,60.2,3.5,3.5),(-2.5,60.4,2.4,3.0),(-7,60.0,1.6,2.35),(-12.2,59.1,1.20,1.65),(-17,57.9,.65,.95)]
    verts=[];uv=[];faces=[];sides=14
    for i,(x,y,ry,rz) in enumerate(rings):
        for j in range(sides):
            a=math.tau*j/sides
            q=(x,y+math.cos(a)*ry,math.sin(a)*rz)
            verts.append(q);uv.append((j/sides,i/(len(rings)-1)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(rings)-1)*sides+j for j in range(sides))])
    mb.batches['deep'].add(verts,faces,uv,[upper]*len(verts))
skull()
tube([(-5,45,0),(-1,50,0),(3.5,54.5,0),(4.6,58,0)],2.8,'deep',upper,tip=1.2,sides=12)
for face in [-1,1]:
    # Armour-like brow, cheek and elongated muzzle plates frame a recessed eye.
    plate([(5,62),(0,64),(-5.5,62.9),(-8,60.7),(-2,60.9),(2,60)],face*2.45,.68,'ice',upper,face)
    plate([(6,59),(2,59.3),(-.5,56.5),(2,53.8),(7,55)],face*2.35,.95,'ice',upper,face)
    plate([(-5.2,60.5),(-10.5,60.6),(-17.5,58.7),(-17,57.4),(-10.5,58),(-6.6,58.8)],face*1.8,.40,'ice',upper,face)
    plate([(-1,60.8),(-4,61.35),(-6.3,60.3),(-3.6,59.5)],face*2.94,.18,'mouth',upper,face,False)
    plate([(-1.6,60.8),(-3.8,61.02),(-5.1,60.37),(-3.4,60.12)],face*3.12,.12,'eye',upper,face,False)
    tube([(4.5,62,face*2.4),(9,65,face*3),(15.5,65.7,face*3.5),(23,63.4,face*2.4)],1.12,'ice',upper,sides=9)
    tube([(6,59,face*2.5),(11,60,face*4),(14,58.5,face*4.4)],.90,'frost',upper,sides=8)
    # Lower jaw sweeps forward and up to the original string attachment.
    tube([(4,55.1,face*1.8),(-.5,52.5,face*1.6),(-7,51.9,face*1.3),(-12.6,53.1,face*.8),(-13.674,54.75,0)],1.0,'ice',upper,tip=.16,sides=10)
    plate([(3,54.9),(-2,53.5),(-8,53),(-5.5,51.4),(.6,51.5),(4.2,53)],face*1.4,.4,'deep',upper,face)
    # Ice teeth have individual roots and sizes, and remain rigid with the skull.
    for j,(x,y) in enumerate([(-15,57.5),(-12.5,58),(-10,58.1),(-7.5,58.3),(-5,58),(-2.5,57)]):
        crystal((x,y+.9,face*1.2),(x+.25,y-(2.0 if j%2 else 2.65),face*1.2),.30,.26,'edge',upper,roll=.15*j)
    for j,x in enumerate([-11,-8.7,-6.3,-3.8]):
        crystal((x,53.0,face*1.0),(x-.25,54.4+(j%2)*.35,face*1.05),.23,.20,'frost',upper)
    for j in range(4):
        p=Vector((6-j*.7,51+j*2,face*1.7))
        scale(p,5.0,1.6,1,upper,face,'ice')
# Crown ridge and nose horn.
tube([(2,62,0),(3.7,66.2,0),(8.4,68.2,0),(10.5,67,0)],1.25,'frost',upper,sides=8)
tube([(-9,60.4,0),(-11.5,63.0,0),(-14,62.8,0)],.68,'ice',upper,sides=7)

# Armoured hooked tail at the lower end; string anchor remains unchanged.
for face in [-1,1]:
    tube([(-11,-51,face*.5),(-13.7,-55,face*.4),(-11.5,-60.5,face*.6),(-5,-64.8,face*.4),(-2.4,-63,0)],1.5,'ice',lower,sides=10)
    tube([(-11.5,-55.6,face*1),(-6,-57.8,face*1.2),(-3,-60.8,0)],1.0,'frost',lower,sides=8)
    for j in range(3):scale((-10+j,-52-j*2.6,face*1.0),4.2,2.1,-1,lower,face,'ice')
tube([(-9.4,-60.8,0),(-12,-65,0),(-17.4,-68,0)],1.0,'frost',lower,sides=8)
stringpts=[(-13.674,float(y),-.02) for y in np.linspace(-54.70,54.97,100)]
sweep(stringpts,[.085]*len(stringpts),'edge',lambda p:weights_at(p,True),sides=6)

objects=[batch.object() for batch in mb.batches.values() if batch.verts]
bpy.data.objects.remove(ref,do_unlink=True)
root.name=key+'_ROOT';root['pynNodeName']=key;rig.name=key+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(key+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
stats={'key':key,'version':'0.3.0','triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'vertices':sum(len(o.data.vertices) for o in objects),'shapes':len(objects),'design_features':['sculpted dragon skull','open articulated-looking static jaw','individual ice teeth','layered chamfered scales','swept horns','hooked tail','2048 fracture diffuse and normal maps'],'not_implemented':['animated jaw','ice particles','physical refraction','gameplay validation']}
(ROOT/'build'/(key+'-model.json')).write_text(json.dumps(stats,indent=2))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=1050;scene.render.resolution_y=1650;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.022,.027,.031,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32
scene.view_settings.view_transform='AgX'
def aim(obj,at):
    f=(Vector(at)-obj.location).normalized();r=f.cross(Vector((0,1,0))).normalized();up=r.cross(f)
    obj.rotation_euler=Matrix((r,up,-f)).transposed().to_quaternion().to_euler()
cd=bpy.data.cameras.new('Preview');cam=bpy.data.objects.new('Preview',cd);scene.collection.objects.link(cam)
cam.location=(-18,3,-235);aim(cam,(2,1,0));cd.type='ORTHO';cd.ortho_scale=155;scene.camera=cam
for name,loc,power,color,size in [('Main',(-45,45,-75),180000,(.83,.91,1),60),('Rim',(38,30,40),310000,(.60,.82,1),55),('Fill',(15,-50,-50),130000,(.9,.95,1),60)]:
    ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo);lo.location=loc;ld.energy=power;ld.color=color;ld.shape='DISK';ld.size=size;aim(lo,(0,0,0))
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ART/(key+'.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(key+'.blend')))
bpy.ops.render.render(write_still=True)
# A closer view makes the geometric fidelity of the dragon head reviewable.
cam.location=(-16,60,-155);aim(cam,(0,56,0));cd.ortho_scale=54
scene.render.resolution_x=1500;scene.render.resolution_y=1050
scene.render.filepath=str(ART/(key+'-head.png'));bpy.ops.render.render(write_still=True)
print('BUILT '+json.dumps(stats))
