"""Read effective installed flight NIF dimensions, without modifying assets."""
import json,math,sys
from paths import BUILD,MODS
from pyn.pynifly import NifFile
from geometric_selected import KEYS
profile=MODS.parent/'profiles/-std-/modlist.txt'
active=[line[1:] for line in profile.read_text(encoding='utf-8-sig').splitlines() if line.startswith('+')]
def measure(key):
    rel='meshes/magicarrows/'+key+'_flight.nif'
    paths=[MODS.parent/'overwrite'/rel]+[MODS/name/rel for name in active]
    path=next(p for p in paths if p.is_file())
    if '--stage' in sys.argv and key!='blood':path=BUILD/'geometric-selected-05/data'/rel
    nf=NifFile(str(path));verts=[v for shape in nf.shapes for v in shape.verts]
    groups={name:[v for v in verts if low<=v[1]<=high] for name,low,high in
            (('head',0,12),('shaft',20,40),('tail',45,58.01))}
    body=[]
    for shape in nf.shapes:
        for tri in shape.tris:
            for i,j in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
                a,b=shape.verts[i],shape.verts[j]
                if min(a[1],b[1])<=30<=max(a[1],b[1]) and abs(b[1]-a[1])>1e-6:
                    t=(30-a[1])/(b[1]-a[1]);v=tuple(a[k]+(b[k]-a[k])*t for k in range(3))
                    groups['shaft'].append(v)
                    if shape.name.endswith('_body') or shape.name.endswith('_shaft'):body.append(v)
    if body:groups['shaft_body']=body
    return dict(path=str(path),total_length=max(v[1] for v in verts)-min(v[1] for v in verts),
                **{name:dict(radius=max(math.hypot(v[0],v[2]) for v in selected),
                             y_min=min(v[1] for v in selected),y_max=max(v[1] for v in selected))
                   for name,selected in groups.items()})
report={key:measure(key) for key in ('blood',)+KEYS}
(BUILD/('arrow-scale-after.json' if '--stage' in sys.argv else 'arrow-scale-before.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if '--stage' in sys.argv:
    for key in KEYS:
        assert abs(report[key]['shaft_body']['radius']-.40)<1e-4
        assert abs(report[key]['head']['radius']-2.496)<1e-4
        assert abs(report[key]['tail']['radius']-2.685)<1e-4
print(json.dumps(report,ensure_ascii=False,indent=2))
