"""Check the exported weapon hierarchy and deformation against its Blender rig.

Run with portable Blender --background --python-exit-code 1 --python <this file>.
These controlled poses check export fidelity; they do not replace in-game tests.
"""
from pathlib import Path
import json
import math
import sys
import bpy
from mathutils import Matrix
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
NIF = Path(args[0]) if args else ROOT / 'data/meshes/weapons/glacialcrown/glacialcrown.nif'
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
    return {b.name: b.parent.name if b.parent else None for b in rig.data.bones}

def snapshots(rig):
    basis = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('GC_')]
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
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'art/glacial-crown.blend'))
assert hierarchy(armature()) == expected_hierarchy
expected_poses = snapshots(armature())
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.pynifly(filepath=str(NIF))
rig = armature()
actual_hierarchy = hierarchy(rig)
assert actual_hierarchy == expected_hierarchy, (expected_hierarchy, actual_hierarchy)
bone_error = max(abs(b.matrix_local[i][j] - expected_bones[b.name][i][j])
                 for b in rig.data.bones for i in range(4) for j in range(4))
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
          'pose_export_errors': errors, 'passed': True,
          'scope': 'Controlled Blender pose comparison, not in-game animation validation.'}
(ROOT / 'build/rig-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('RIG_VERIFIED ' + json.dumps(report))
