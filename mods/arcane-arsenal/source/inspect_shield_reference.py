"""Inspect the vanilla shield attachment and imported coordinate system."""
import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.pynifly(filepath=str(ROOT/'build/shield-reference-elvenshield.nif'))
for o in bpy.context.scene.objects:
    print('SHIELD_OBJECT',o.name,o.type,'parent',o.parent.name if o.parent else None,'matrix',list(map(list,o.matrix_world)),'props',dict(o.items()))
    if o.type=='MESH':
        print('BOUNDS', [[min((o.matrix_world@v.co)[i] for v in o.data.vertices),max((o.matrix_world@v.co)[i] for v in o.data.vertices)] for i in range(3)])
        print('GROUPS', [g.name for g in o.vertex_groups], 'MATERIALS',[m.name for m in o.data.materials])
    if o.type=='ARMATURE':
        print('BONES',[(b.name,list(map(list,b.matrix_local))) for b in o.data.bones])
