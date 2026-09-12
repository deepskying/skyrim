"""Read installed arrow conventions; write only inspection assets into build/."""
import sys,json,struct
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
GAME=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE')
MODS=GAME.parent/'MO2/mods'
sys.path.insert(0,str(REPO/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
from plugin_records import records,subrecords,edid
from bsa_reference import entries,extract

report={}
for plugin in [GAME/'Data/Skyrim.esm',MODS/'玩法改进-奥术弓手-Marc🟨/Marc.esp']:
    selected=[]
    for r in records(plugin,{b'TES4',b'AMMO',b'PROJ',b'EXPL'}):
        name=edid(r)
        if plugin.name=='Skyrim.esm' and name not in ('IronArrow','IronArrowProjectile','ElvenArrow','ElvenArrowProjectile','ExplosionFireball01') and r['sig']!=b'TES4':continue
        selected.append({'type':r['sig'].decode(),'id':hex(r['form']),'edid':name,'parts':[(k.decode(), v.rstrip(b'\0').decode('utf-8',errors='replace') if k in (b'EDID',b'FULL',b'MODL',b'MAST') else v.hex()) for k,v in subrecords(r['data'])]})
    report[plugin.name]=selected
for archive in sorted((GAME/'Data').glob('Skyrim - Meshes*.bsa')):
    for key in entries(archive):
        if key in ('meshes/weapons/iron/ironarrow.nif','meshes/weapons/iron/ironarrowflight.nif','meshes/effects/fxsparkfountain.nif'):
            path=ROOT/'build'/Path(key).name
            path.write_bytes(extract(archive,key))
            report[key]={'archive':archive.name}
paths=list((ROOT/'build').glob('iron*.nif'))+[MODS/'玩法改进-奥术弓手-Marc🟨/meshes/muken/arcanearrows/arcanearrow.nif',MODS/'玩法改进-奥术弓手-Marc🟨/meshes/muken/arcanearrows/arcanearrowproj.nif']
for path in paths:
    n=NifFile(str(path));out=[]
    for shape in n.shapes:
        vs=shape.verts
        out.append({'name':shape.name,'id':shape.id,'parent':shape.parent.name if shape.parent else None,'verts':len(vs),'bounds':[[min(v[a] for v in vs) for a in range(3)],[max(v[a] for v in vs) for a in range(3)]],'translation':list(shape.transform.translation),'rotation':[list(row) for row in shape.transform.rotation],'scale':shape.transform.scale})
    report[path.name]=out
(ROOT/'build/reference.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
