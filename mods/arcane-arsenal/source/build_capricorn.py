"""Four distinct Capricorn solid-light bows on the verified vanilla bow skeleton.

Blender --background --python-exit-code 1 --python this.py -- capricornred
The output blend is the source mesh; native draw particles are appended separately.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_builder as mb
from mesh_builder import bpy,np,math,json,Vector,ROOT,ART,TEX,MESH,ref,root,rig
from geometric_helpers import string_weights,texture,polyline,ANCHORS,STRING_X

KEY=sys.argv[sys.argv.index('--')+1]
SPEC=next(s for s in json.loads((ROOT/'source/capricorn_catalog.json').read_text(encoding='utf-8')) if s['key']==KEY)
DESIGN=SPEC['design'];MID={'Bow_MidBone':1.0}
di=texture(SPEC['diffuse_name'],tuple(SPEC['diffuse_color'])+(1,))
ni=texture('aa_red_n',(.5,.5,1,0),True);gi=texture('aa_red_g',(1,1,1,1))
for index,category in enumerate(('CapricornBody','CapricornEdge','CapricornString')):
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

def line(points,width=.16,category='CapricornEdge',binding=None):
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
    mb.batches['CapricornEdge'].add(verts,faces,uv,weights)

from solid_geometry import primitives
from capricorn_geometry import build
strip,ring,blade,angular=primitives(rail_rim,'CapricornBody')
anchors=build(SPEC,strip,ring,blade,angular)

stringpts=[(STRING_X,float(y),-.02) for y in np.linspace(ANCHORS[-1],ANCHORS[1],121)]
mb.sweep(stringpts,[.11]*len(stringpts),'CapricornString',string_weights,sides=6)
objects=[b.object() for b in mb.batches.values() if b.verts]
bpy.data.objects.remove(ref,do_unlink=True);root.name=KEY+'_ROOT';root['pynNodeName']=KEY;rig.name=KEY+'_Rig'
collision=bpy.data.objects['bhkBoxShape'];collision.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in objects+[root,rig,collision]+list(root.children):obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.pynifly(filepath=str(MESH/(KEY+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
# Preserve a reproducible clean geometry base for native particle construction.
base=ROOT/'build/capricorn-base';base.mkdir(exist_ok=True)
(base/(KEY+'.nif')).write_bytes((MESH/(KEY+'.nif')).read_bytes())
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.009,.013,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.resolution_x=700;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
cd=bpy.data.cameras.new('Capricorn preview');cam=bpy.data.objects.new('Capricorn preview',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-220);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=129;scene.camera=cam
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear()
layer=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=.06;glare.size=7;glare.mix=-.88
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layer.outputs['Image'],glare.inputs[0]);scene.node_tree.links.new(glare.outputs[0],output.inputs[0])
bpy.ops.wm.save_as_mainfile(filepath=str(ART/(KEY+'.blend')))
scene.render.filepath=str(ART/(KEY+'.png'));bpy.ops.render.render(write_still=True)
report={'version':'0.18.0','key':KEY,'design':DESIGN,'triangles':sum(len(p.vertices)-2 for o in objects for p in o.data.polygons),'shapes':len(objects),'particle_anchors':anchors,'string_anchors':stringpts[::120],'power':SPEC['power'],'preview':'Actual source geometry; native particles not rendered; game bloom depends on ENB.'}
(ROOT/'build'/(KEY+'-model.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CAPRICORN_BUILT '+KEY+' '+str(report['triangles'])+' triangles',flush=True)
