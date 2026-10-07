"""Render the two actual exported NIFs and their DDS surface atlases."""
import sys,struct,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from paths import ROOT,BUILD
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks
pure='--pure-geometry' in sys.argv
faithful='--faithful-samples' in sys.argv
ART=ROOT/('art/faithful-samples-01' if faithful else 'art/pure-geometry-02' if pure else 'art/precision-samples-01');DATA=BUILD/('faithful-samples-01/data' if faithful else 'pure-geometry-02/data' if pure else 'precision-samples-01/data')
ART.mkdir(parents=True,exist_ok=True)
def label(text,loc,size,color=(.72,.78,.85)):
    cu=bpy.data.curves.new(text,'FONT');cu.body=text;cu.font=bpy.data.fonts.get('Microsoft YaHei') or bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc');cu.size=size
    ob=bpy.data.objects.new(text,cu);bpy.context.scene.collection.objects.link(ob);ob.location=loc
    mat=bpy.data.materials.new(text);mat.use_nodes=True
    sh=mat.node_tree.nodes.get('Principled BSDF');sh.inputs['Base Color'].default_value=(*color,1);sh.inputs['Emission Color'].default_value=(*color,1);sh.inputs['Emission Strength'].default_value=.7
    cu.materials.append(mat)
def render(detail=False,angle=False,clay=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=2000;scene.render.resolution_y=1500
    scene.world=bpy.data.worlds.new('Dark studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.018,.024,.037,1)
    scene.view_settings.view_transform='Standard'
    for index,key in enumerate(('fire','holy') if faithful else ('ice','holy')):
        path=DATA/'meshes/magicarrows'/f'{key}_flight.nif';nf=NifFile(str(path));raw=NifBlocks(path)
        rows=[('箭头',0,12.5,11),('箭尾',46.5,58,-12)] if detail else [('全貌',0,58,8-index*18)]
        for name,low,high,oy in rows:
            ox=-34+index*36 if detail else -30;scale=2.25 if detail else 1
            phase=.85 if angle else 0 if faithful else .28;co,si=math.cos(phase),math.sin(phase)
            for shape in nf.shapes:
                verts=shape.verts;tris=[t for t in shape.tris if all(low<=verts[i][1]<=high for i in t)]
                if not tris:continue
                vs=[(ox+(high-v[1])*scale,oy+(v[0]*co-v[2]*si)*scale,(v[0]*si+v[2]*co)*scale) for v in verts]
                mesh=bpy.data.meshes.new(shape.name);mesh.from_pydata(vs,[],tris);mesh.update()
                for poly in mesh.polygons:poly.use_smooth=True
                mesh.normals_split_custom_set_from_vertices([(-n[1],n[0]*co-n[2]*si,n[0]*si+n[2]*co) for n in shape.normals])
                uv=mesh.uv_layers.new(name='Exported NIF UV')
                for loop in mesh.loops:uv.data[loop.index].uv=shape.uvs[loop.vertex_index]
                ob=bpy.data.objects.new(shape.name,mesh);scene.collection.objects.link(ob)
                sb=raw.blocks[struct.unpack_from('<I',raw.blocks[shape.id][1],92)[0]][1]
                length=struct.unpack_from('<I',sb,36)[0];tex=sb[40:40+length].decode()
                color=struct.unpack_from('<3f',sb,60+length);power=struct.unpack_from('<f',sb,76+length)[0]
                mat=bpy.data.materials.new(shape.name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
                output=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');em.inputs['Strength'].default_value=power
                image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(DATA/tex),check_existing=True)
                mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*color,1)
                mat.node_tree.links.new(image.outputs['Color'],mix.inputs[1]);mat.node_tree.links.new(mix.outputs[0],em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],output.inputs['Surface']);mesh.materials.append(mat)
                if clay:
                    nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');surface=nodes.new('ShaderNodeBsdfPrincipled')
                    surface.inputs['Base Color'].default_value=(.38,.43,.49,1);surface.inputs['Roughness'].default_value=.38
                    mat.node_tree.links.new(surface.outputs[0],output.inputs['Surface'])
            label(('火焰箭' if key=='fire' else '冰晶箭' if key=='ice' else '圣辉箭')+' · '+name,(ox,oy+6,5),1.4,(1,.40,.12) if key=='fire' else (.52,.78,1) if key=='ice' else (1,.79,.39))
    label('魔法箭 · 立体火焰样品 0.4.0' if faithful else '魔法箭 · 纯几何样品 0.2.0' if pure else '魔法箭 · 两支模型样品 0.1.0',(-34,29,5),2.1)
    label(('实际 NIF 白模 / ' if clay else '实际 NIF 网格 + 纯色自发光 / ' if pure else '实际 NIF 网格 + DDS 纹理 / ')+('组件特写' if detail else '组合全貌'),(-34,25,5),1.0)
    label('自发光材质 · 游戏内粒子与辉光待实测',(-34,-27,5),.85)
    camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam)
    cam.location=(0,-18,150);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=92;scene.camera=cam
    if clay:
        for pos,energy,size in (((-25,30,70),25000,45),((35,-20,55),14000,35)):
            light=bpy.data.lights.new('Clay softbox','AREA');light.energy=energy;light.size=size
            ob=bpy.data.objects.new(light.name,light);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layers=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.threshold=1.4;glare.quality='HIGH';glare.mix=-.90
    output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layers.outputs['Image'],glare.inputs['Image']);scene.node_tree.links.new(glare.outputs['Image'],output.inputs[0])
    for image in bpy.data.images:
        if image.source=='FILE':image.pack()
    name='geometry' if clay else 'angles' if angle else 'details' if detail else 'overview';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ART/f'{name}.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/f'{name}.blend'));bpy.ops.render.render(write_still=True)
render();render(True)
if faithful:render(True,True)
if faithful:render(True,True,True)
