"""Build one distinct bow: Blender --background --python this.py -- <catalog key>."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,Vector,Matrix,math,json,subprocess,ART,TEX,MESH,ROOT
from mesh_builder import crystal,sweep,center,weights_at,ref,rig,root

catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
key=sys.argv[sys.argv.index('--')+1]
spec=next(s for s in catalog if s['key']==key)
mid={'Bow_MidBone':1.0}
n=1024
u,v=np.meshgrid(np.linspace(0,1,n),np.linspace(0,1,n))
cloud=(np.sin(u*21+np.sin(v*13)*1.4)+np.sin(v*37-u*9))*.5
veins=np.zeros_like(u)
for phase,slope in [(.18,.40),(.49,-.67),(.82,.24)]:
    d=np.abs(u-(phase+slope*(v-.5)+.021*np.sin(v*31+phase)))
    veins=np.maximum(veins,np.exp(-(d/.0015)**2))
texconv=Path(r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe')

def texture(name,pixels,normal=False):
    image=bpy.data.images.new(name,width=n,height=n,alpha=True)
    if normal:image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.astype(np.float32).ravel())
    image.filepath_raw=str(ART/(name+'.png'));image.file_format='PNG';image.save()
    subprocess.run([str(texconv),'-nologo','-y','-f','BC3_UNORM' if normal else 'BC7_UNORM','-m','0','-o',str(TEX),str(ART/(name+'.png'))],check=True,capture_output=True)
    image.filepath=str(TEX/(name+'.dds'));image.reload()
    return image

normal=np.ones((n,n,4),np.float32);normal[:,:,:3]=(.5,.5,1)
normal_image=texture('aa_normal',normal,True)
glow=np.ones_like(normal)
for ch,c in enumerate(spec['glow']):glow[:,:,ch]=(veins*.42+.008)*c
glow_image=texture(key+'_g',glow)
for index,category in enumerate(['body','edge','core','light']):
    color=np.ones_like(normal)
    for ch,c in enumerate(spec['materials'][index]):
        color[:,:,ch]=np.clip(c*(.9+cloud*.12)+veins*(.10 if key=='frostglass' else .025),0,1)
    if key=='frostglass' and category in ('body','edge'):
        color[:,:,3]=np.clip((.65 if category=='body' else .80)+veins*.18+cloud*.025,0,1)
    img=texture(key+'_'+category,color)
    mat=mb.base_mat.copy();mat.name=key+'_'+category
    nodes=mat.node_tree.nodes;shader=nodes['SkyrimShader:Default']
    for node in list(nodes):
        if node.type=='TEX_IMAGE':nodes.remove(node)
    shader.inputs['Emission Color'].default_value=(*spec['glow'],1)
    shader.inputs['Emission Strength'].default_value=[.015,.018,.60,.27][index]
    shader.inputs['Specular Color'].default_value=(.83,.87,.94,1)
    shader.inputs['Glossiness'].default_value=160 if key=='frostglass' else 90
    mat.pyn_shader.Shader_Type='Glow_Shader'
    mat.pyn_shader.Shader_Flags_1='SPECULAR | SKINNED | RECEIVE_SHADOWS | CAST_SHADOWS | OWN_EMIT | ZBUFFER_TEST'
    mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
    for prop in list(mat.keys()):
        if prop.startswith('BSShaderTextureSet_'):del mat[prop]
    for slot,im,inlet in [('Diffuse',img,'Diffuse'),('Normal',normal_image,'Normal'),('Glow',glow_image,'Glow Map')]:
        mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\'+im.name+'.dds'
        node=nodes.new('ShaderNodeTexImage');node.image=im
        node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
        mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
    if key=='frostglass' and category in ('body','edge'):
        group=bpy.data.node_groups.get('AlphaProperty')
        if group is None:
            assets=mb.TOOLS/'blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly/blender_assets/Shaders.blend'
            with bpy.data.libraries.load(str(assets)) as (_,loaded):loaded.node_groups=['AlphaProperty']
            group=loaded.node_groups[0]
        alpha=nodes.new('ShaderNodeGroup');alpha.node_tree=group;alpha.name='AlphaProperty'
        alpha.inputs['Alpha Test'].default_value=False
        alpha.inputs['Alpha Blend'].default_value=True
        alpha.inputs['Source Blend Mode'].default_value=6
        alpha.inputs['Destination Blend Mode'].default_value=7
        mat.node_tree.links.new(nodes['Diffuse_Texture'].outputs['Alpha'],alpha.inputs['Alpha'])
        mat.node_tree.links.new(alpha.outputs[0],shader.inputs['Alpha Property'])
    mb.materials[category]=mat
mb.batches={name:mb.Batch(name) for name in mb.materials}

def limb(y):
    """New silhouettes share the proven grip and two string attachment anchors."""
    p=center(y);t=max(0,min(1,(abs(y)-7)/48))
    p.x += {'frostglass':5.2,'emberwake':2.3,'astralorbit':3.7,'moonthorn':3.3}[key]*math.sin(math.pi*t)**2
    return p

def arc(at,radius,start,end,category='edge',width=.40,tilt=0):
    pts=[Vector(at)+Vector((radius*math.cos(a),radius*math.sin(a),tilt*math.sin(a))) for a in np.linspace(math.radians(start),math.radians(end),46)]
    sweep(pts,[width]*len(pts),category,lambda p:mid,sides=8)

def leaf(p,d,length,width,category='edge',binding=None):
    p=Vector(p);d=Vector(d).normalized();side=d.cross(Vector((0,0,1))).normalized()
    verts=[p,p+d*length*.42+side*width,p+d*length,p+d*length*.42-side*width,p+d*length*.46+Vector((0,0,-width*.5))]
    mb.batches[category].add([tuple(x) for x in verts],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],[(0,0),(0,.5),(.5,1),(1,.5),(.5,.5)],[(binding or weights_at(p))]*5)

# A comfortable, narrow handle; all frostglass grip surfaces remain crystalline.
ys=np.linspace(-7,7,24)
radii=[1.15+.35*(abs(float(y))/7)**2 for y in ys]
sweep([(1.3,y,0) for y in ys],radii,'body' if key!='frostglass' else 'edge',lambda p:mid,sides=10)
if key!='frostglass':
    helix=[(1.3+1.35*math.cos(t),-6.6+13.2*t/(math.tau*5),1.35*math.sin(t)) for t in np.linspace(0,math.tau*5,150)]
    sweep(helix,[.14]*len(helix),'edge',lambda p:mid,sides=5)
else:
    for sign in [-1,1]:crystal((1.3,6.7*sign,0),(1.3,9.2*sign,0),1.7,1.1,'body',mid)

for sign in [-1,1]:
    ys=np.linspace(7,55,66)*sign
    pts=[limb(float(y)) for y in ys]
    rs=[(.9+1.2*math.sin(math.pi*max(0,(abs(float(y))-7)/48)))*(.90 if key=='astralorbit' else 1) for y in ys]
    sweep(pts,rs,'body',sides=8,depth=.7)
    if key=='frostglass':
        # Braided ice facets and a few large terminal crystals replace the comb.
        for phase in [0,math.pi]:
            braided=[p+Vector((.80*math.sin(i*.16+phase),0,.65*math.cos(i*.16+phase))) for i,p in enumerate(pts)]
            sweep(braided,[r*.46 for r in rs],'edge',sides=5)
        for j,(y,dx,dy,width) in enumerate([(37,11,12,2.5),(43,15,13,3),(48,10,15,2.7),(52,3,15,2.3),(46,17,5,2.0)]):
            p=limb(sign*y)
            crystal(p,p+Vector((dx,sign*dy,(-1)**j*1.6)),width,width*.60,'edge' if j%2 else 'body',weights_at(center(sign*y)),roll=j*.45)
        p=limb(sign*20)
        crystal(p,p+Vector((4,sign*8,-.5)),1.05,.7,'body',weights_at(center(sign*20)))
    elif key=='emberwake':
        # Heavy broken obsidian plates surround a visible molten seam.
        seam=[p+Vector((.7,0,-1.15)) for p in pts]
        sweep(seam,[.32]*len(seam),'core',sides=5)
        for j,y in enumerate([15,23,31,39,46,51]):
            p=limb(sign*y)
            crystal(p+Vector((0,0,-.5)),p+Vector((7+j*.8,sign*(8+j*.9),-1)),2.5,1.3,'body',weights_at(center(sign*y)),roll=.6)
            leaf(p+Vector((1,0,-1.4)),(1,sign*.7,0),9+j,1.4,'edge',weights_at(center(sign*y)))
        for j in range(3):
            base=limb(sign*(44+j*3));flame=[]
            for t in np.linspace(0,1,28):flame.append(base+Vector((5*math.sin(t*math.pi)+j*1.5*t,sign*(18*t),-2)))
            sweep(flame,[.8*(1-t)+.06 for t in np.linspace(0,1,28)],'core' if j==1 else 'light',lambda p,b=weights_at(center(sign*(44+j*3))):b,sides=6)
    elif key=='astralorbit':
        # Open double rails and engraved-looking transverse brass collars.
        for shift in [-1,1]:
            rail=[p+Vector((shift*2.2*math.sin(math.pi*i/(len(pts)-1)),0,.4)) for i,p in enumerate(pts)]
            sweep(rail,[.30]*len(rail),'edge',sides=8)
        for y in [15,26,37,48]:
            p=limb(sign*y)
            ring=[p+Vector((2.5*math.cos(a),.5*math.sin(a),1.4*math.sin(a))) for a in np.linspace(0,math.tau,28)]
            sweep(ring,[.23]*len(ring),'edge',lambda p,b=weights_at(center(sign*y)):b,sides=6)
        p=limb(sign*50)
        crystal(p+Vector((0,0,-.3)),p+Vector((6,sign*15,0)),2.5,1.3,'core',weights_at(center(sign*50)))
    else:
        # Twisted living vines with directional leaves and crescent thorn hooks.
        for phase in [0,math.pi]:
            vine=[p+Vector((1.55*math.sin(i*.23+phase),0,1.1*math.cos(i*.23+phase))) for i,p in enumerate(pts)]
            sweep(vine,[.55]*len(vine),'edge',sides=7)
        for j,y in enumerate([17,27,37,46]):
            p=limb(sign*y)
            leaf(p,(1,sign*.7,0),9+j,2.1,'edge',weights_at(center(sign*y)))
            leaf(p+Vector((.3,0,-.8)),(.8,sign,0),6+j,1.15,'light',weights_at(center(sign*y)))
            crystal(p+Vector((-.6,0,0)),p+Vector((-4,sign*4,-.4)),.65,.6,'body',weights_at(center(sign*y)))
        p=limb(sign*49)
        hook=[p+Vector((8*math.sin(t*math.pi),sign*13*t,-.6)) for t in np.linspace(0,1,30)]
        sweep(hook,[1.4*(1-t)+.10 for t in np.linspace(0,1,30)],'edge',lambda p,b=weights_at(center(sign*49)):b,sides=8)

if key=='frostglass':
    crystal((3,10,-2),(3,18,-2),2.0,1.4,'core',mid)
    for sign in [-1,1]:
        for j in range(3):crystal((3+sign*(3+j),10+j*2,-1),(3+sign*(5+j),14+j*3,-1),.85,.6,'edge',mid)
elif key=='emberwake':
    crystal((3,8,-2),(3,16,-2),2.1,1.3,'core',mid)
    for sign in [-1,1]:
        p=Vector((3,10,-1));crystal(p,p+Vector((sign*5,5,0)),1.2,1,'body',mid)
elif key=='astralorbit':
    at=(5,15,1)
    arc(at,10,12,168,'edge',.32,4);arc(at,10,192,348,'edge',.32,4)
    arc(at,8,0,360,'light',.12,-5)
    crystal((5,11,-2),(5,19,-2),2.2,1.5,'core',mid)
    for i in range(6):
        a=math.tau*i/6;p=Vector(at)+Vector((11*math.cos(a),11*math.sin(a),0))
        crystal(p-Vector((0,1,0)),p+Vector((0,1.8,0)),.65,.55,'core',mid)
else:
    # A small crescent moon nests above the handle, leaving the grip clear.
    arc((4,15,0),6,45,315,'edge',.72)
    crystal((3,11,-1),(3,17,-1),1.8,1.1,'core',mid)

stringpts=[(-13.674,y,-.02) for y in np.linspace(-54.70,54.97,80)]
sweep(stringpts,[.09]*len(stringpts),'light',lambda p:weights_at(p,True),sides=6)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True)
root.name=key+'_ROOT';root['pynNodeName']=key
rig.name=key+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(key+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
stats={'key':key,'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'vertices':sum(len(o.data.vertices) for o in objects),'shapes':len(objects)}
(ROOT/'build'/(key+'-model.json')).write_text(json.dumps(stats,indent=2))

# Render actual exported geometry; no generated illustration is used as a preview.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=850;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.028,.030,.04,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX'
def aim(obj,at):
    f=(Vector(at)-obj.location).normalized();r=f.cross(Vector((0,1,0))).normalized();up=r.cross(f)
    obj.rotation_euler=Matrix((r,up,-f)).transposed().to_quaternion().to_euler()
cd=bpy.data.cameras.new('Preview');cam=bpy.data.objects.new('Preview',cd);scene.collection.objects.link(cam)
cam.location=(-15,0,-215);aim(cam,(1,0,0));cd.type='ORTHO';cd.ortho_scale=150;scene.camera=cam
for name,loc,power,color,size in [('Main',(-45,40,-80),210000,(1,.95,.9),65),('Edge',(30,30,40),250000,(.8,.86,1),55),('Fill',(30,-45,-45),130000,(.86,.9,1),65)]:
    ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo);lo.location=loc;ld.energy=power;ld.color=color;ld.shape='DISK';ld.size=size;aim(lo,(0,0,0))
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ART/(key+'.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(key+'.blend')))
bpy.ops.render.render(write_still=True)
print('BUILT '+json.dumps(stats))
