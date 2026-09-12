"""Check collection completeness, unchanged unrelated assets and draw-script wiring."""
from pathlib import Path
import json,re,struct,collections,sys,math,hashlib,itertools
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
specs=json.loads((ROOT/'source/geometric_catalog.json').read_text(encoding='utf-8'))
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
assert len(specs)==24 and len({s['key'] for s in specs})==24
assert collections.Counter(s['design'] for s in specs)==dict.fromkeys(('plates','triangles','diamonds','hexagon','squares','chevron'),4)
assert collections.Counter(s['color_key'] for s in specs)==dict.fromkeys(('red','green','blue','purple'),6)
managed={int(s['stat_form'],16)+1 for s in catalog if s['key'].startswith(('aries','taurus')) or s.get('series')=='geometric'}
script=(ROOT/'source/papyrus/AARedDrawFX.psc').read_text(encoding='utf-8')
bindings=re.findall(r'ariesBows\[(\d+)\] = Game.GetFormFromFile\(0x([0-9A-F]+),',script)
assert [int(i) for i,f in bindings]==list(range(32))
assert {int(f,16) for i,f in bindings}==managed
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
f=lambda b,o=0:struct.unpack_from('<f',b,o)[0]
for spec in specs:
    n=NifBlocks(ROOT/'data/meshes/weapons/arcanearsenal'/(spec['key']+'.nif'))
    powers=[];fx=[]
    for k,b in n.blocks:
        if k=='BSLightingShaderProperty':powers.append(f(b,56))
        if k=='BSEffectShaderProperty':fx.append(f(b,76+u(b,36)))
    assert len(powers)==3 and all(math.isclose(a,b,rel_tol=1e-6) for a,b in zip(powers,spec['power']))
    assert len(fx)==6 and all(math.isclose(x,spec['particle_power'],rel_tol=1e-6) for x in fx)
    assert not any(b'AAHexagramDrawFX' in s or b'AARedDrawParticles' in s for s in n.strings)
    assert sum(s.startswith(b'AAAriesDust') for s in n.strings)==6
base=ROOT/'build/before-0.11.0/data'
updated={s['key'] for s in specs if s['design'] in ('triangles','chevron')}
expected_changes={'meshes/weapons/arcanearsenal/'+key+'.nif' for key in updated}
assert len(updated)==8
unchanged=[]
changed=[]
for q in (ROOT/'data').rglob('*'):
    if q.is_file():
        rel=q.relative_to(ROOT/'data').as_posix()
        if rel not in expected_changes:
            assert (base/rel).read_bytes()==q.read_bytes(),rel
            unchanged.append(rel)
        else:
            assert (base/rel).read_bytes()!=q.read_bytes(),(rel,'model not updated')
            changed.append(rel)
            # Brightness, colors, texture choices, and particle shaders must not
            # drift while geometry and attachment locations are redesigned.
            old=NifBlocks(base/rel);new=NifBlocks(q)
            assert old.strings==new.strings
            for kind in ('BSLightingShaderProperty','BSShaderTextureSet','BSEffectShaderProperty','NiAlphaProperty'):
                assert [b for k,b in old.blocks if k==kind]==[b for k,b in new.blocks if k==kind],(rel,kind)
assert len(unchanged)==42 and set(changed)==expected_changes
assert (ROOT/'source/catalog.json').read_bytes()==(base.parent/'source/catalog.json').read_bytes()
assert (ROOT/'source/geometric_catalog.json').read_bytes()==(base.parent/'source/geometric_catalog.json').read_bytes()
assert (ROOT/'source/papyrus/AARedDrawFX.psc').read_bytes()==(base.parent/'source/papyrus/AARedDrawFX.psc').read_bytes()
plugin=(ROOT/'data/ArcaneArsenal.esp').read_bytes()
assert plugin[:4]==b'TES4' and u(plugin,8)&0x200
sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
models=[]
grip_signatures={};palm_profiles={};shoulder_profiles={}
core_names={'plates':'stepped_v_shoulders','hexagon':'faceted_arch_shoulders',
            'squares':'crossed_twist_shoulders','diamonds':'continuous_s_shoulders',
            'triangles':'offset_triangle_gates','chevron':'triple_feather_spines'}
def profile(verts,stations):
    result=[]
    for y in stations:
        xs=[v[0] for v in verts if abs(v[1]-y)<.24]
        assert xs,('missing cross section',y)
        result.extend((min(xs),max(xs)))
    return result
for key in sorted(s['key'] for s in specs):
    spec=next(s for s in specs if s['key']==key)
    native=NifFile(str(ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif')))
    assert len(native.shapes)==3
    for shape in native.shapes:
        assert all(0<=v<len(shape.verts) for tri in shape.tris for v in tri)
    body=next(s for s in native.shapes if s.name=='AA_GeometricBody')
    grip=[v for v in body.verts if abs(v[1])<5.9]
    assert len(grip)>100 and max(abs(v[2]) for v in grip)<=2.5
    # The previous radius-8 star was a separate depth layer at Z=-3.8.
    edge=next(s for s in native.shapes if s.name=='AA_GeometricEdge')
    assert all(abs(v[2])<2.8 for v in edge.verts if abs(v[1])<8)
    string=next(s for s in native.shapes if s.name=='AA_GeometricString')
    assert abs(min(v[1] for v in string.verts)+54.70)<.003
    assert abs(max(v[1] for v in string.verts)-54.97)<.003
    assert all(abs(v[0]+13.674)<=.09 for v in string.verts)
    source=json.loads((ROOT/'build'/(key+'-model.json')).read_text(encoding='utf-8'))
    assert source['core']==core_names[spec['design']]
    assert source['version']==('0.11.0' if key in updated else '0.10.1')
    # Actual exported geometry must differ between all six grip designs, while
    # the four colors of each design must share exactly the same geometry.
    coords=sorted({tuple(round(c,3) for c in v) for v in body.verts if abs(v[1])<20})
    signature=hashlib.sha256(repr(coords).encode()).hexdigest()
    if spec['design'] in grip_signatures:assert signature==grip_signatures[spec['design']]
    else:
        grip_signatures[spec['design']]=signature
        palm_profiles[spec['design']]=profile(body.verts,(-4,-2,0,2,4))
        shoulder_profiles[spec['design']]=profile(body.verts,(9,12,15,18))
    rig=json.loads((ROOT/'build'/(key+'-rig-verification.json')).read_text(encoding='utf-8'))
    assert rig['passed']
    if key in updated:models.append({'key':key,'triangles':source['triangles'],'rig_verified':True,'grip_star_removed':True})
assert len(set(grip_signatures.values()))==6,'Repeated grip geometry'
separations=[]
for a,b in itertools.combinations(core_names,2):
    palm=max(abs(x-y) for x,y in zip(palm_profiles[a],palm_profiles[b]))
    shoulder=max(abs(x-y) for x,y in zip(shoulder_profiles[a],shoulder_profiles[b]))
    assert palm>.2 and shoulder>.6,(a,b,'grips too similar',palm,shoulder)
    separations.append({'designs':[a,b],'palm_profile_difference':palm,'shoulder_profile_difference':shoulder})
obsolete=json.loads((ROOT/'source/obsolete_assets.json').read_text(encoding='utf-8'))
assert all(not (ROOT/'data'/rel).exists() for rel in obsolete)
assets=[p for p in (ROOT/'data').rglob('*') if p.is_file()]
assert collections.Counter(p.suffix for p in assets)=={'.nif':32,'.dds':15,'.esp':1,'.pex':1,'.seq':1}
report={'version':'0.11.0','passed':True,'geometric_bows':24,'designs':6,'colors':4,'managed_bows':32,'redesigned_models':models,'distinct_grip_profiles':separations,'unchanged_previous_runtime_files':len(unchanged),'unchanged_materials_and_esl_plugin':True,'all_string_anchors_verified':True,'runtime_files':50,'scope':'Offline validation; in-game appearance and animation still need testing.'}
(ROOT/'build/geometric-release-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
