"""Update source blend emission values from the validated runtime migration.

Run in Blender. Absolute values make repeat runs safe; geometry is not rebuilt.
"""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'build/emission-verification.json').read_text(encoding='utf-8'))
assert report['version']=='0.7.1' and report['passed']
for model in report['models']:
    path=ROOT/'art'/(model['key']+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path))
    for name,strength in model['shape_strengths'].items():
        obj=bpy.data.objects.get(name)
        if obj is None:
            assert name=='AAHexagramLight'
            continue
        for mat in obj.data.materials:
            mat.node_tree.nodes['SkyrimShader:Default'].inputs['Emission Strength'].default_value=strength
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('SOURCE_EMISSION_SYNCED 16')
