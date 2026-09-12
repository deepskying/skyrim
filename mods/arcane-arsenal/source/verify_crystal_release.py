"""Verify actual exported Crystal geometry, draw bindings and upgrade scope."""
from pathlib import Path
import json,re,struct,collections,sys,math,hashlib
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
specs=json.loads((ROOT/'source/crystal_catalog.json').read_text(encoding='utf-8'))
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
assert len(specs)==4 and len(catalog)==80
assert len({s['design'] for s in specs})==4
script=(ROOT/'source/papyrus/AARedDrawFX.psc').read_text(encoding='utf-8')
bindings=re.findall(r'ariesBows\[(\d+)\] = Game.GetFormFromFile\(0x([0-9A-F]+),',script)
assert [int(i) for i,f in bindings]==list(range(80))
assert {int(f,16) for i,f in bindings}=={int(s['stat_form'],16)+1 for s in catalog}
assert 'new Weapon[80]' in script
base=ROOT/'build/before-0.23.0/data'
old={p.relative_to(base).as_posix():p for p in base.rglob('*') if p.is_file()}
current={p.relative_to(ROOT/'data').as_posix():p for p in (ROOT/'data').rglob('*') if p.is_file()}
assert set(old)<=set(current)
assert set(current)-set(old)=={'meshes/weapons/arcanearsenal/'+s['key']+'.nif' for s in specs}|{'textures/weapons/arcanearsenal/'+s['key']+'_'+suffix+'.dds' for s in specs for suffix in ('d','n','g')}
changes=[rel for rel,p in old.items() if p.read_bytes()!=current[rel].read_bytes()]
assert set(changes)=={'ArcaneArsenal.esp','scripts/AARedDrawFX.pex'}
assert len(old)==103 and len(current)==119
old_catalog=json.loads((base.parent/'source/catalog.json').read_text(encoding='utf-8'))
assert catalog[:76]==old_catalog
for name in ('geometric_catalog.json','aries_catalog.json','taurus_catalog.json','gemini_catalog.json','cancer_catalog.json','leo_catalog.json','virgo_catalog.json','libra_catalog.json','sagittarius_catalog.json','capricorn_catalog.json','aquarius_catalog.json','pisces_catalog.json','scorpio_catalog.json','retired_weapons.json'):
    assert (ROOT/'source'/name).read_bytes()==(base.parent/'source'/name).read_bytes()
sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
f=lambda b,o=0:struct.unpack_from('<f',b,o)[0]
signatures=[];models=[]
for spec in specs:
    key=spec['key'];path=ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif')
    n=NifBlocks(path)
    powers=[f(b,56) for k,b in n.blocks if k=='BSLightingShaderProperty']
    fx=[f(b,76+u(b,36)) for k,b in n.blocks if k=='BSEffectShaderProperty']
    assert len(powers)==3 and all(math.isclose(a,b,rel_tol=1e-6) for a,b in zip(powers,spec['power']))
    assert len(fx)==6 and all(math.isclose(x,spec['particle_power'],rel_tol=1e-6) for x in fx)
    paths=[b[40:40+u(b,36)].decode('ascii') for k,b in n.blocks if k=='BSEffectShaderProperty']
    sprite_name=lambda style:('aa_scorpio_' if style=='hollowsquare' else 'aa_pisces_' if style in ('oval','hollowdiamond') else 'aa_aquarius_' if style=='ring' else 'aa_capricorn_' if style in ('droplet','hollowtriangle') else 'aa_sagittarius_' if style in ('chevron','crescent') else 'aa_virgo_' if style=='kite' else 'aa_geo_' if style in ('hexagon','needle','streak') else 'aa_aries_')+style+'.dds'
    expected_paths=['textures\\weapons\\arcanearsenal\\'+sprite_name(style) for style in (spec['fx'],spec['fx_secondary'])]
    assert collections.Counter(paths)==dict.fromkeys(expected_paths,3),'Mixed draw sprites missing'
    assert not any(b'Hexagram' in s for s in n.strings)
    native=NifFile(str(path));assert len(native.shapes)==3
    body=next(s for s in native.shapes if s.name=='AA_CrystalBody')
    grip=[v for v in body.verts if abs(v[1])<20]
    signatures.append(hashlib.sha256(repr(sorted({tuple(round(c,3) for c in v) for v in grip})).encode()).hexdigest())
    palm=[v for v in body.verts if abs(v[1])<5]
    assert len(palm)>100 and max(abs(v[2]) for v in palm)<2.5
    string=next(s for s in native.shapes if s.name=='AA_CrystalString')
    assert abs(min(v[1] for v in string.verts)+54.7)<.003
    assert abs(max(v[1] for v in string.verts)-54.97)<.003
    assert all(abs(v[0]+13.674)<.12 for v in string.verts)
    rig=json.loads((ROOT/'build'/(key+'-rig-verification.json')).read_text(encoding='utf-8'))
    assert rig['passed']
    source=json.loads((ROOT/'build'/(key+'-model.json')).read_text(encoding='utf-8'))
    assert source['version']=='0.23.0' and source['design']==spec['design']
    # Inspect all three actual DDS headers and independently decoded texels.
    from PIL import Image
    import numpy as np
    texture_report={}
    for suffix in ('d','n','g'):
        texture=ROOT/'data/textures/weapons/arcanearsenal'/(key+'_'+suffix+'.dds')
        blob=texture.read_bytes()
        assert blob[:4]==b'DDS ' and struct.unpack_from('<II',blob,12)==(1024,1024)
        assert u(blob,28)==11,'Complete mip chain required'
        decoded=np.asarray(Image.open(texture).convert('RGBA')).astype(float)/255
        assert decoded[:,:,:3].std()>.01,'Uniform crystal texture'
        texture_report[suffix]={'mipmaps':11,'resolution':1024,'std':float(decoded[:,:,:3].std())}
        if suffix=='g':
            brightness=decoded[:,:,:3].mean(axis=2)
            assert brightness.max()>.1 and (brightness<.1).mean()>.25,'Glow should leave dark crystal surfaces visible'
        if suffix=='n':
            assert decoded[:,:,:2].std()>.003
            assert decoded[:,:,3].max()-decoded[:,:,3].min()>.05
    models.append({'textures':texture_report,'key':key,'triangles':source['triangles'],'rig_verified':True})
assert len(set(signatures))==4,'Repeated central geometry'
placement=json.loads((ROOT/'build/crystal-particles-placement-verification.json').read_text(encoding='utf-8'))
assert len(placement)==4 and all(r['passed'] for r in placement)
assert collections.Counter(p.suffix for p in current.values())=={'.nif':80,'.dds':36,'.esp':1,'.pex':1,'.seq':1}
assert not any((ROOT/'data'/rel).exists() for rel in json.loads((ROOT/'source/obsolete_assets.json').read_text(encoding='utf-8')))
report={'version':'0.23.0','passed':True,'models':models,'distinct_grips':4,'managed_bows':80,'unchanged_previous_runtime_files':101,'new_models':4,'new_1k_textures':12,'changed_previous_files':changes,'gameplay_tested':False}
(ROOT/'build/crystal-release-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
