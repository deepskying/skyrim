"""Check the exported weapon hierarchy and deformation against its Blender rig.

Run with portable Blender --background --python-exit-code 1 --python <this file>.
These controlled poses check export fidelity; they do not replace in-game tests.
"""
from pathlib import Path
import json
import math
import sys
import struct
import bpy
from mathutils import Matrix
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
key = sys.argv[sys.argv.index('--') + 1]
is_red=key in ('redplates','redtriangles','reddiamonds')
is_geometric=key.startswith('geo') or is_red
is_aries=key.startswith(('aries','taurus','gemini','cancer','leo','virgo','libra','sagittarius','capricorn','aquarius','pisces','scorpio','crystal','heteromorphic2','heteromorphic')) or is_geometric
series='heteromorphic2' if key.startswith('heteromorphic2') else 'crystal' if key.startswith('crystal') else 'heteromorphic' if key.startswith('heteromorphic') else 'scorpio' if key.startswith('scorpio') else 'pisces' if key.startswith('pisces') else 'aquarius' if key.startswith('aquarius') else 'capricorn' if key.startswith('capricorn') else 'sagittarius' if key.startswith('sagittarius') else 'libra' if key.startswith('libra') else 'virgo' if key.startswith('virgo') else 'leo' if key.startswith('leo') else 'cancer' if key.startswith('cancer') else 'gemini' if key.startswith('gemini') else 'geometric' if is_geometric else 'taurus' if key.startswith('taurus') else 'aries'
shape_prefix=series.title()
aries=next((s for s in json.loads((ROOT/'source'/(series+'_catalog.json')).read_text(encoding='utf-8')) if s['key']==key),None)
NIF = ROOT / 'data/meshes/weapons/arcanearsenal' / (key+'.nif')
REFERENCE = ROOT.parents[1] / 'reference/bow-tools/validation/ironbow-textured-check.blend'
POSES = {
    'rest': {},
    'limb_flex': {'Bow_LoBone1': 12, 'Bow_LoBone2': 18,
                  'Bow_UpBone1': -12, 'Bow_UpBone2': -18,
                  'Bow_StringBone1': -30, 'Bow_StringBone2': 30},
    'grip_and_limbs': {'Bow_MidBone': 25, 'Bow_LoBone1': 8,
                       'Bow_LoBone2': 12, 'Bow_UpBone1': -8,
                       'Bow_UpBone2': -12},
}

def armature():
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')

def hierarchy(rig):
    return {b.name: b.parent.name if b.parent else None for b in rig.data.bones if b.name.startswith("Bow_")}

def snapshots(rig):
    basis = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('AA_')]
    result = {}
    for label, angles in POSES.items():
        for b in rig.pose.bones:
            b.matrix_basis = basis[b.name] @ Matrix.Rotation(math.radians(angles.get(b.name, 0)), 4, 'Z')
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        result[label] = {}
        for obj in meshes:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            result[label][obj.name] = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            evaluated.to_mesh_clear()
    for b in rig.pose.bones:
        b.matrix_basis = basis[b.name]
    return result

def distance(a, b):
    # NIF export splits UV and normal seams, so vertex counts need not match.
    tree = KDTree(len(b))
    for i, co in enumerate(b):
        tree.insert(co, i)
    tree.balance()
    return max(tree.find(co)[2] for co in a)

bpy.ops.wm.open_mainfile(filepath=str(REFERENCE))
expected_hierarchy = hierarchy(armature())
expected_bones = {b.name: b.matrix_local.copy() for b in armature().data.bones}
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'art' / (key+'.blend')))
assert hierarchy(armature()) == expected_hierarchy
expected_poses = snapshots(armature())
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.pynifly(filepath=str(NIF))
rig = armature()
texture_paths=set()
alpha_materials=[]
ice_shaders={}
red_shaders={}
for obj in bpy.data.objects:
    if obj.type!='MESH' or not obj.name.startswith('AA_'):continue
    for material in obj.data.materials:
        if 'NiAlphaProperty_flags' in material:alpha_materials.append(material.name)
        for node in material.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image:
                path=Path(bpy.path.abspath(node.image.filepath))
                assert path.is_file(), str(path)
                resolution=1024
                if is_red or is_aries:resolution=1024 if path.name.startswith('crystal') else 64
                if key=='frostwyrm':
                    resolution=4096 if '_body_' in path.name else 64 if '_eye_' in path.name else 2048
                assert tuple(node.image.size)==(resolution,resolution), (path,tuple(node.image.size))
                texture_paths.add(str(path))
        if is_red or is_aries:
            shader=material.pyn_shader
            assert shader.Shader_Type=='Glow_Shader'
            assert 'OWN_EMIT' in shader.Shader_Flags_1
            assert 'GLOW_MAP' in shader.Shader_Flags_2
            node=material.node_tree.nodes['SkyrimShader:Default']
            color=tuple(node.inputs['Emission Color'].default_value)
            strength=node.inputs['Emission Strength'].default_value
            expected_strength=dict(zip(tuple('AA_'+shape_prefix+part for part in (('Body','Edge','String','Fold') if key=='heteromorphic2green' else ('Body','Edge','String'))),aries['power']))[obj.name] if is_aries else {'AA_redface':1.8,'AA_redline':3.6,'AA_redstring':2.4}[obj.name]
            expected_color=(aries['color'] if obj.name in ('AA_'+shape_prefix+'Body','AA_'+shape_prefix+'Fold') else aries['edge']) if is_aries else (1,0,0)
            assert abs(strength-expected_strength)<1e-5,(obj.name,strength)
            # Skyrim stores emissive RGB, not Blender's fourth color component.
            assert max(abs(a-b) for a,b in zip(color[:3],expected_color))<1e-5,color
            assert material.get('BSShaderTextureSet_Glow','').endswith(key+'_g.dds' if series=='crystal' and obj.name=='AA_CrystalBody' else 'aa_red_g.dds')
            if series=='crystal' and obj.name=='AA_CrystalBody':
                assert 'SPECULAR' in shader.Shader_Flags_1
                assert node.inputs['Glossiness'].default_value==110
            red_shaders[obj.name]={'type':shader.Shader_Type,'emissive_color':color,'emissive_strength':strength}
        if key=='frostwyrm':
            for prop,value in material.items():
                if prop.startswith('BSShaderTextureSet_') and value:
                    path=ROOT/'data'/value.replace('\\','/')
                    assert path.is_file(),path
                    data=path.read_bytes();assert data[:4]==b'DDS '
                    res=4096 if '_body_' in path.name else 128 if '_cube' in path.name else 64 if '_eye_' in path.name else 2048
                    assert struct.unpack_from('<II',data,12)==(res,res),(path,res)
                    if '_cube' in path.name:
                        assert struct.unpack_from('<I',data,112)[0]&0xFE00==0xFE00
                        assert len(data)==128+6*res*res*4
                    texture_paths.add(str(path))
            if obj.name in ('AA_SculptHead','AA_SculptBody'):
                shader=material.pyn_shader
                assert shader.Shader_Type=='Environment_Map',shader.Shader_Type
                assert 'ENVIRONMENT_MAPPING' in shader.Shader_Flags_1
                assert abs(shader.Env_Map_Scale-.48)<1e-5,shader.Env_Map_Scale
                assert material.get('BSShaderTextureSet_EnvMap','').endswith('frostwyrm_v2_cube.dds')
                assert '_m.dds' in material.get('BSShaderTextureSet_EnvMask','')
                ice_shaders[obj.name]={'type':shader.Shader_Type,'environment_scale':shader.Env_Map_Scale}
assert len(texture_paths)==(6 if series=='crystal' else 3 if is_red or is_aries else 9 if key=='frostwyrm' else 6), texture_paths
if is_red or is_aries:
    assert len(alpha_materials)==0
    assert len(red_shaders)==(4 if key=='heteromorphic2green' else 3)
    expected_textures={aries['diffuse_name']+'.dds' if is_aries else 'aa_red_d.dds','aa_red_n.dds','aa_red_g.dds'}
    if series=='crystal':
        flat='aa_red_d' if key=='crystalred' else 'aa_aries'+key.replace('crystal','')+'_d'
        expected_textures={key+'_'+x+'.dds' for x in ('d','n','g')}|{flat+'.dds','aa_red_n.dds','aa_red_g.dds'}
    assert {Path(p).name for p in texture_paths}==expected_textures
if key=='frostglass':assert len(alpha_materials)==2,alpha_materials
if key=='frostwyrm':
    assert len(alpha_materials)==0,alpha_materials
    assert len(ice_shaders)==2,ice_shaders
actual_hierarchy = hierarchy(rig)
assert actual_hierarchy == expected_hierarchy, (expected_hierarchy, actual_hierarchy)
mesh_quality={}
if is_red or is_aries:
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not obj.name.startswith('AA_'):continue
        obj.data.calc_loop_triangles()
        areas=[];weight_error=0
        for v in obj.data.vertices:
            assert all(math.isfinite(c) for c in v.co)
            influences=[g.weight for g in v.groups if obj.vertex_groups[g.group].name in rig.data.bones]
            assert 1<=len(influences)<=4,(obj.name,v.index,influences)
            weight_error=max(weight_error,abs(sum(influences)-1))
        for triangle in obj.data.loop_triangles:
            a,b,c=[obj.data.vertices[i].co for i in triangle.vertices]
            areas.append((b-a).cross(c-a).length*.5)
        assert min(areas)>1e-7,(obj.name,min(areas))
        assert weight_error<.001,(obj.name,weight_error)
        mesh_quality[obj.name]={'triangles':len(areas),'minimum_triangle_area':min(areas),'maximum_weight_error':weight_error}
bone_error = max(abs(b.matrix_local[i][j] - expected_bones[b.name][i][j])
                 for b in rig.data.bones if b.name in expected_bones for i in range(4) for j in range(4))
assert bone_error < 0.01, bone_error
actual_poses = snapshots(rig)
errors = {}
for pose, shapes in expected_poses.items():
    assert shapes.keys() == actual_poses[pose].keys()
    errors[pose] = {}
    for name, points in shapes.items():
        other = actual_poses[pose][name]
        error = max(distance(points, other), distance(other, points))
        assert error < 0.04, (pose, name, error)
        errors[pose][name] = error
report = {'hierarchy': actual_hierarchy, 'max_rest_bone_error': bone_error,
          'ice_shaders':ice_shaders,
          'red_shaders':red_shaders,
          'mesh_quality':mesh_quality,
          'textures':sorted(texture_paths),'alpha_materials':alpha_materials,
          'pose_export_errors': errors, 'passed': True,
          'scope': 'Controlled Blender pose comparison, not in-game animation validation.'}
(ROOT / 'build' / (key+'-rig-verification.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RIG_VERIFIED ' + json.dumps(report))
