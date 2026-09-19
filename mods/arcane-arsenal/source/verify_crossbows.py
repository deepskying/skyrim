"""Compare reimported skins in controlled poses and verify native animation data."""
import bpy,sys,json,struct,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
SERIES='crossbows2' if '--crossbows2' in sys.argv else 'crossbows'
reference=NifBlocks(ROOT/'build/crossbow-reference.nif')
def rig():return next(o for o in bpy.data.objects if o.type=='ARMATURE')
def clear():
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
def snapshots():
    r=rig();result={}
    poses={'rest':{},'flex':{'CrossBowBone_L01':-.12,'CrossBowBone_R01':.12,'CrossBowBone_L02':-.16,'CrossBowBone_R02':.16,'StringL':.35,'StringR':-.35},'reload':{'CockingMechanismCtrl':.4,'RollerNutTriggerCtrl':.3,'TriggerCtrl':.2}}
    for label,angles in poses.items():
        for b in r.pose.bones:b.matrix_basis=Matrix.Rotation(angles.get(b.name,0),4,'Z')
        bpy.context.view_layer.update();dep=bpy.context.evaluated_depsgraph_get();result[label]={}
        for o in bpy.data.objects:
            if o.type!='MESH' or not o.name.startswith('AA_Crossbow'):continue
            ev=o.evaluated_get(dep);mesh=ev.to_mesh();result[label][o.name]=[ev.matrix_world@v.co for v in mesh.vertices];ev.to_mesh_clear()
    for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    return result
def distance(a,b):
    tree=KDTree(len(b))
    for i,p in enumerate(b):tree.insert(p,i)
    tree.balance();return max(tree.find(p)[2] for p in a)
reports=[]
for spec in json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text('utf-8')):
    key=spec['key'];n=NifBlocks(ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif'))
    # Added particle children are the only permitted changes to existing bones.
    for i,(kind,blob) in enumerate(reference.blocks[:39]):
        if i in (0,6):continue
        k,b=n.blocks[i];assert k==kind
        if kind=='NiNode':
            assert b[:72]==blob[:72],(key,i,'native transform/controller changed')
            old=struct.unpack_from('<'+'I'*u(blob,72),blob,76);new=struct.unpack_from('<'+'I'*u(b,72),b,76)
            assert new[:len(old)]==old
        else:assert b==blob,(key,i,'native data changed')
    assert [k for k,b in n.blocks].count('NiTransformController')==7
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art'/SERIES/(key+'.blend')))
    bones={b.name:b.matrix_local.copy() for b in rig().data.bones};expected=snapshots()
    clear();bpy.ops.import_scene.pynifly(filepath=str(ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif')),import_animations=False)
    assert set(bones)<=set(rig().data.bones.keys())
    bone_error=max(abs(b.matrix_local[i][j]-bones[b.name][i][j]) for b in rig().data.bones if b.name in bones for i in range(4) for j in range(4));assert bone_error<.01,bone_error
    actual=snapshots();pose_errors={}
    for label,shapes in expected.items():
        assert shapes.keys()==actual[label].keys()
        errors={name:max(distance(pts,actual[label][name]),distance(actual[label][name],pts)) for name,pts in shapes.items()}
        assert max(errors.values())<.04,(key,label,errors);pose_errors[label]=errors
    quality={};allpoints=[]
    for o in bpy.data.objects:
        if o.type!='MESH' or not o.name.startswith('AA_Crossbow'):continue
        o.data.calc_loop_triangles();areas=[];weight_error=0
        for v in o.data.vertices:
            assert all(math.isfinite(c) for c in v.co)
            weights=[g.weight for g in v.groups if o.vertex_groups[g.group].name in bones]
            assert 1<=len(weights)<=4;weight_error=max(weight_error,abs(sum(weights)-1))
            allpoints.append(o.matrix_world@v.co)
        for t in o.data.loop_triangles:
            a,b,c=[o.data.vertices[i].co for i in t.vertices];areas.append((b-a).cross(c-a).length*.5)
        assert min(areas)>1e-7,(key,o.name,min(areas));assert weight_error<.001
        mat=o.data.materials[0];shader=mat.node_tree.nodes['SkyrimShader:Default'];index=0 if o.name.endswith('Body') else 2 if o.name.endswith('String') else 1
        assert mat.pyn_shader.Shader_Type=='Glow_Shader' and 'SKINNED' in mat.pyn_shader.Shader_Flags_1
        assert abs(shader.inputs['Emission Strength'].default_value-spec['power'][index])<1e-5
        expected_color=spec['color'] if index==0 else spec['edge']
        assert max(abs(a-b) for a,b in zip(shader.inputs['Emission Color'].default_value[:3],expected_color))<1e-5
        quality[o.name]={'triangles':len(areas),'min_area':min(areas),'weight_error':weight_error}
    collision=n.blocks[6][1];assert u(collision,32)==8
    box=[struct.unpack_from('<4f',collision,36+16*j)[:3] for j in range(8)]
    lo=[min(v[i] for v in box)*69.99125 for i in range(3)];hi=[max(v[i] for v in box)*69.99125 for i in range(3)]
    assert all(lo[i]<=p[i]<=hi[i] for p in allpoints for i in range(3))
    reports.append({'key':key,'passed':True,'native_animation_graph_preserved':True,'bone_error':bone_error,'pose_errors':pose_errors,'mesh_quality':quality,'collision_contains_mesh':True,'gameplay_tested':False})
(ROOT/'build'/(SERIES+'-verification.json')).write_text(json.dumps(reports,indent=2),'utf-8')
print('CROSSBOWS_VERIFIED',json.dumps(reports))
