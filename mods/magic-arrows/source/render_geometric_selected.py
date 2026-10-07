"""Render actual exported NIF geometry, shaders and UVs for geometric arrows."""
import sys,math,struct,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from paths import ROOT,BUILD
from geometric_selected import KEYS,REMAINING,LABELS,VERSION
round03='--geometric-round03' in sys.argv
redesign08='--five-arrow-redesign' in sys.argv
if round03:from geometric_round03 import KEYS,REMAINING,LABELS,VERSION
if redesign08:from five_arrow_redesign import KEYS,REMAINING,LABELS,VERSION,STAGE,ART as REDESIGN_ART
from nif_blocks import NifBlocks
from pyn.pynifly import NifFile
remaining='--remaining' in sys.argv
if remaining:KEYS=REMAINING
elif not round03 and not redesign08:KEYS=('blood',)+KEYS
ART=ROOT/'art/geometric-scale-061'
if round03:ART=ROOT/'art/geometric-round03-070'
if redesign08:ART=ROOT/'art'/REDESIGN_ART
if remaining:ART=ART/'remaining'
ART.mkdir(parents=True,exist_ok=True)
DATA=BUILD/'geometric-selected-05/data'
if round03:DATA=BUILD/'geometric-round03/data'
if redesign08:DATA=BUILD/STAGE
FONT=None

def clipped_geometry(shape,low,high):
    """Clip only preview geometry; interpolate original NIF UV at section planes."""
    vertices=[];uvs=[];triangles=[]
    for tri in shape.tris:
        poly=[(tuple(shape.verts[i]),tuple(shape.uvs[i])) for i in tri]
        for plane,sign in ((low,1),(high,-1)):
            out=[]
            for j,current in enumerate(poly):
                previous=poly[j-1];a=(previous[0][1]-plane)*sign>=0;b=(current[0][1]-plane)*sign>=0
                if a!=b:
                    t=(plane-previous[0][1])/(current[0][1]-previous[0][1])
                    pos=tuple(x+t*(y-x) for x,y in zip(previous[0],current[0]))
                    uv=tuple(x+t*(y-x) for x,y in zip(previous[1],current[1]))
                    out.append((pos,uv))
                if b:out.append(current)
            poly=out
            if not poly:break
        if len(poly)<3:continue
        start=len(vertices);vertices.extend(p for p,uv in poly);uvs.extend(uv for p,uv in poly)
        triangles.extend((start,start+j,start+j+1) for j in range(1,len(poly)-1))
    return vertices,triangles,uvs

def label(text,loc,size,color=(.75,.80,.88)):
    curve=bpy.data.curves.new(text,'FONT');curve.body=text;curve.font=FONT;curve.size=size
    ob=bpy.data.objects.new(text,curve);bpy.context.scene.collection.objects.link(ob);ob.location=loc
    mat=bpy.data.materials.new(text);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=.6
    ob.data.materials.append(mat)

def render(clay=False,side=False):
    global FONT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    FONT=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    full=len(KEYS)>6
    scene.render.resolution_x=3000 if full else 2200
    scene.render.resolution_y=2800 if full else 1800;scene.render.resolution_percentage=100
    if round03:scene.render.resolution_x=2800;scene.render.resolution_y=2200
    if redesign08:scene.render.resolution_x=2600;scene.render.resolution_y=1800
    scene.world=bpy.data.worlds.new('Studio');scene.world.color=(.006,.009,.015)
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    for index,key in enumerate(KEYS):
        columns=3 if full else 2
        col=index%columns;row=index//columns
        ox=(-57 if full else -37)+col*39;oy=(34-row*25) if full else (20-row*23)
        if redesign08:ox=-44+index*22;oy=-9
        label(LABELS.get(key,'嗜血箭 · 尺寸基准'),(ox-9 if redesign08 else ox,29 if redesign08 else oy+8,6),.95 if redesign08 else 1.35)
        path=DATA/'meshes/magicarrows'/f'{key}_flight.nif'
        if key=='blood':path=Path(json.loads((BUILD/'arrow-scale-before.json').read_text(encoding='utf-8'))['blood']['path'])
        nf=NifFile(str(path));raw=NifBlocks(path)
        # Full arrow above; enlarged head and tail below. Side mode rotates 90 degrees.
        views=[(.53,ox,oy+4,0,58), (1.80,ox,oy-2,0,11.8), (.92,ox+26,oy-2,45.5,58)]
        if redesign08:
            views=[(.62,ox,oy,0,58),(1.45,ox-4,-36.5,0,11.8),(1.15,ox+6,-33.5,45.5,58)]
            label('箭头',(ox-7,-38.5,6),.75);label('箭尾',(ox+3,-38.5,6),.75)
        if round03:
            views=[(.53,ox,oy+4,0,58),(1.0,ox,oy-2,0,11.8),(.65,ox+13,oy-2,22,38),(.85,ox+25,oy-2,45.5,58)]
            for offset,text in ((0,'箭头'),(13,'箭杆'),(25,'箭尾')):label(text,(ox+offset,oy-7,6),.75)
        phase=math.pi/2 if side else .35 if redesign08 else .60;c,s=math.cos(phase),math.sin(phase)
        for scale,xpos,ypos,low,high in views:
            for shape in nf.shapes:
                vertices=shape.verts
                tris=[tri for tri in shape.tris if all(low<=vertices[i][1]<=high for i in tri)]
                uvs=shape.uvs
                if round03 or redesign08:vertices,tris,uvs=clipped_geometry(shape,low,high)
                if not tris:continue
                vs=[(xpos+(high-y)*scale,ypos+(x*c-z*s)*scale,(x*s+z*c)*scale) for x,y,z in vertices]
                if redesign08:
                    vs=[(xpos+(x*c-z*s)*scale,ypos+(high-y)*scale,(x*s+z*c)*scale) for x,y,z in vertices]
                mesh=bpy.data.meshes.new(key+'-'+shape.name);mesh.from_pydata(vs,[],tris);mesh.update()
                uv=mesh.uv_layers.new(name='Actual NIF UV')
                for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
                ob=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(ob)
                shader=raw.blocks[struct.unpack_from('<I',raw.blocks[shape.id][1],92)[0]][1]
                size=struct.unpack_from('<I',shader,36)[0];texture=shader[40:40+size].decode()
                color=struct.unpack_from('<3f',shader,60+size);power=struct.unpack_from('<f',shader,76+size)[0]
                mat=bpy.data.materials.new(ob.name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
                out=nodes.new('ShaderNodeOutputMaterial')
                if clay:
                    surface=nodes.new('ShaderNodeBsdfPrincipled');surface.inputs['Base Color'].default_value=(.35,.40,.46,1)
                    surface.inputs['Roughness'].default_value=.35
                else:
                    surface=nodes.new('ShaderNodeEmission');surface.inputs['Strength'].default_value=power
                    image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(DATA/texture),check_existing=True)
                    tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
                    tint.inputs[2].default_value=(*color,1)
                    mat.node_tree.links.new(image.outputs['Color'],tint.inputs[1]);mat.node_tree.links.new(tint.outputs[0],surface.inputs['Color'])
                mat.node_tree.links.new(surface.outputs[0],out.inputs['Surface']);mesh.materials.append(mat)
    left=-57 if full else -37;top=53 if full else 33;bottom=-55 if full else -33
    if round03:bottom=-32
    if redesign08:left=-54;top=37;bottom=-42
    label(('魔法箭 · 五款造型重设计 ' if redesign08 else '魔法箭 · 几何样品 ')+VERSION,(left,top,6),1.8)
    label('实际导出白模 · 立体结构检查' if clay else '实际 NIF · 90° 侧视' if side else '实际 NIF · 发光几何模型',(left,top-3,6),.9)
    label('各栏：整箭 / 箭头 / 箭杆 / 箭尾 · 游戏内辉光与拉弓待实测' if round03 else '各栏：整箭 / 箭头放大 / 箭尾放大 · 游戏内辉光与拉弓待实测',(left,bottom,6),.85)
    if clay:
        for loc,energy in (((-20,30,70),25000),((35,-15,50),14000)):
            light=bpy.data.lights.new('Clay area light','AREA');light.energy=energy;light.size=40
            ob=bpy.data.objects.new(light.name,light);scene.collection.objects.link(ob);ob.location=loc
            ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam)
    cam.location=(0,-10,150);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
    if round03:cam.location=(0,-4,150);cam.rotation_euler=(Vector((0,6,0))-cam.location).to_track_quat('-Z','Y').to_euler()
    if redesign08:cam.location=(0,-3,150);cam.rotation_euler=(0,0,0)
    camdata.type='ORTHO';camdata.ortho_scale=132 if full else 88;scene.camera=cam
    if round03:camdata.ortho_scale=132
    if redesign08:camdata.ortho_scale=122
    scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layers=nodes.new('CompositorNodeRLayers')
    out=nodes.new('CompositorNodeComposite')
    if clay:scene.node_tree.links.new(layers.outputs['Image'],out.inputs[0])
    else:
        glow=nodes.new('CompositorNodeGlare');glow.glare_type='FOG_GLOW';glow.threshold=1.3;glow.mix=-.88
        scene.node_tree.links.new(layers.outputs['Image'],glow.inputs[0]);scene.node_tree.links.new(glow.outputs[0],out.inputs[0])
    for img in bpy.data.images:
        if img.source=='FILE':img.pack()
    name='geometry' if clay else 'side' if side else 'models'
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ART/f'{name}.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/f'{name}.blend'));bpy.ops.render.render(write_still=True)

for clay,side in ((False,False),(False,True),(True,False)):render(clay,side)
