"""Studio overview and head details from final exported projectile NIF vertices.

Read actual self-emission color/power. Native particles and ENB bloom need
in-game review. Never use concept pixels here.
"""
import sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from paths import ROOT,MESH,BUILD
from design_catalog import ALL
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks

flow='--luminous-v4' in sys.argv
if flow:
    from luminous_v4 import KEYS
    ALL=[spec for spec in ALL if spec['key'] in KEYS]
    MESH=BUILD/'luminous-v4/data/meshes/magicarrows'
ART=ROOT/('art/luminous-v4' if flow else 'art/visual-v4')
ART.mkdir(exist_ok=True)

def label(scene,text,loc,size,color):
    cu=bpy.data.curves.new(text,'FONT');cu.body=text;cu.font=bpy.data.fonts.get('Microsoft YaHei') or bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc');cu.size=size
    ob=bpy.data.objects.new(text,cu);scene.collection.objects.link(ob);ob.location=loc
    mat=bpy.data.materials.new(text);mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Emission Color'].default_value=(*color,1)
    shader.inputs['Emission Strength'].default_value=.7
    cu.materials.append(mat)

def render(detail=False,tail=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=2400;scene.render.resolution_y=2200
    scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.045,.05,.06,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
    scene.view_settings.view_transform='Standard'
    for loc,energy,size in [((-40,20,90),40000,65),((60,-35,60),24000,50)]:
        light=bpy.data.lights.new('Studio softbox','AREA');light.energy=energy;light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(light.name,light);scene.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    for index,spec in enumerate(ALL):
        col=index%2;row=index//2;ox=-70+col*76;oy=55-row*22
        path=MESH/(spec['key']+'_flight.nif')
        nf=NifFile(str(path));raw=NifBlocks(path)
        for shape in nf.shapes:
            verts=shape.verts;tris=shape.tris
            if detail:
                tris=[t for t in tris if all(verts[i][1]>=47 if tail else verts[i][1]<=12.5 for i in t)]
                if not tris:continue
            vs=[(ox+((58 if tail else 12.5)-v[1])*4.1 if detail else ox+58-v[1],
                 oy+v[0]*(4.1 if detail else 1),v[2]*(4.1 if detail else 1)) for v in verts]
            mesh=bpy.data.meshes.new(shape.name);mesh.from_pydata(vs,[],tris);mesh.update()
            for polygon in mesh.polygons:polygon.use_smooth=True
            # Respect exported split normals; faceted crystal faces remain sharp.
            mesh.normals_split_custom_set_from_vertices([( -n[1],n[0],n[2]) for n in shape.normals])
            uv_layer=mesh.uv_layers.new(name='NIF UV')
            for loop in mesh.loops:uv_layer.data[loop.index].uv=shape.uvs[loop.vertex_index]
            ob=bpy.data.objects.new(shape.name,mesh);scene.collection.objects.link(ob)
            cat=shape.name.rsplit('_',1)[-1]
            mat=bpy.data.materials.new(shape.name);mat.use_nodes=True
            shape_data=raw.blocks[shape.id][1]
            shader_id=struct.unpack_from('<I',shape_data,92)[0]
            shader_kind,shader_data=raw.blocks[shader_id]
            assert shader_kind=='BSEffectShaderProperty'
            texture_length=struct.unpack_from('<I',shader_data,36)[0]
            color=struct.unpack_from('<3f',shader_data,60+texture_length)
            power=struct.unpack_from('<f',shader_data,76+texture_length)[0]
            nodes=mat.node_tree.nodes;nodes.clear()
            output=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeEmission')
            shader.inputs['Color'].default_value=(*color,1)
            shader.inputs['Strength'].default_value=power
            mat.node_tree.links.new(shader.outputs[0],output.inputs['Surface'])
            mesh.materials.append(mat)
        label(scene,f"{index+1:02d}  {spec['name']}",(ox,oy+9,5),2.0,spec['core'])
    label(scene,'魔法箭 / 流光第四版 · '+('箭尾特写' if tail else '箭头特写' if detail else '九箭全貌' if flow else '十二箭全貌'),(-70,73,5),2.8,(.8,.84,.9))
    label(scene,'实际导出 NIF 网格与自发光参数 · 辉光近似，游戏内效果待验收',(-70,-69,5),1.2,(.55,.6,.67))
    camera=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(cam)
    cam.location=(0,-65,180);target=Vector((0,3,0))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    camera.type='ORTHO';camera.ortho_scale=160;scene.camera=cam
    scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear()
    layers=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare')
    glare.glare_type='FOG_GLOW';glare.threshold=.8;glare.quality='HIGH'
    out=nodes.new('CompositorNodeComposite')
    scene.node_tree.links.new(layers.outputs['Image'],glare.inputs['Image']);scene.node_tree.links.new(glare.outputs['Image'],out.inputs[0])
    name='tails' if tail else 'heads' if detail else 'overview'
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ART/(name+'.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/(name+'.blend')))
    bpy.ops.render.render(write_still=True)

render();render(True)
if flow:render(True,True)
