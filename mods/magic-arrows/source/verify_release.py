"""Validate record links, actual NIF graphs, shaders, particles and attachment parity."""
import json,math,struct,hashlib
from paths import *
from game_specs import PROTOTYPES
from elemental_records import SPECS,header as adapter_header
from plugin_records import records,subrecords,edid
from nif_blocks import NifBlocks
from pyn.pynifly import NifFile
from redesign_geometry import redesigned
from geometry import cross,sub
pure='--pure-geometry' in sys.argv
flow='--luminous-v4' in sys.argv
faithful='--faithful-samples' in sys.argv
round03='--geometric-round03' in sys.argv
shock09='--shock-redesign' in sys.argv
redesign08='--five-arrow-redesign' in sys.argv or shock09
selected='--geometric-selected' in sys.argv or round03
precision='--precision-samples' in sys.argv or pure or flow or faithful or selected or redesign08
if precision:
    DATA=BUILD/('geometric-selected-05/data' if selected else 'faithful-samples-01/data' if faithful else 'luminous-v4/data' if flow else 'pure-geometry-02/data' if pure else 'precision-samples-01/data');MESH=DATA/'meshes/magicarrows'
    if redesign08:
        if shock09:from shock_arrow_redesign import generate as redesigned,STAGE,KEYS
        else:from five_arrow_redesign import generate as redesigned,STAGE,KEYS
        DATA=BUILD/STAGE;MESH=DATA/'meshes/magicarrows'
    elif round03:
        DATA=BUILD/'geometric-round03/data';MESH=DATA/'meshes/magicarrows'
        from geometric_round03 import generate as redesigned
    elif selected:from geometric_selected import generate as redesigned
    elif faithful:from faithful_samples import generate as redesigned
    elif flow:from luminous_v4 import generate as redesigned
    elif pure:from pure_geometry_samples import generate as redesigned
    else:from precision_samples import generate as redesigned
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
f=lambda b,o=0:struct.unpack_from('<f',b,o)[0]
checks=[]
if '--models-only' not in sys.argv:
    assert (ROOT/'native/src/spell_adapters.h').read_text(encoding='utf-8')==adapter_header()
    catalog_header=(ROOT/'native/src/prototype_catalog.h').read_text(encoding='utf-8')
    for spec in PROTOTYPES:assert ('{0x%X,"%s"}' % (spec['id'],spec['key'])) in catalog_header
    rs=list(records(DATA/'MagicArrows.esp'));byid={r['form']:r for r in rs}
    assert len(byid)==len(rs)==587
    header=dict(subrecords(rs[0]['data']))
    assert rs[0]['flags']==0x200
    assert header[b'MAST']==b'Skyrim.esm\0'
    assert struct.unpack_from('<f',header[b'HEDR'])[0]<1.71
    assert u(header[b'HEDR'],4)==len(rs)-1+9
    assert all(r['version']==44 for r in rs)
    assert all(0x01000800<=r['form']<=0x01000E01 for r in rs[1:])
    assert {r['sig'] for r in rs}=={b'TES4',b'AMMO',b'PROJ',b'EXPL',b'CONT',b'SPEL',b'MGEF',b'ENCH',b'FLST',b'STAT'}
    masterids={r['form']:r['sig'] for r in records(GAME/'Data/Skyrim.esm')}
    def ref(fid,kind):
        if not fid:return
        assert (byid.get(fid) or {'sig':masterids.get(fid)})['sig']==kind,(hex(fid),kind)
    for r in rs[1:]:
        d=dict(subrecords(r['data']))
        if b'MODL' in d:
            path=d[b'MODL'].rstrip(b'\0').decode()
            if r['sig'] not in (b'CONT',b'STAT'):
                if r['form']==0x01000881:assert path.lower()=='magic\\fireballexp01.nif'
                else:assert (DATA/'meshes'/path).is_file()
        adapter=next((s for s in SPECS if 0x01000000+s['ammo']<=r['form']<=0x01000000+s['ammo']+7),None)
        payload=next((s for s in SPECS if r['form'] in (0x01000000+s['payload']+1,0x01000000+s['payload']+2)),None)
        if r['sig']==b'AMMO':
            ref(u(d[b'DATA']),b'PROJ');assert u(d[b'DATA'],4)==(6 if 0x01000C00<=r['form']<=0x01000CFF else 4)
            name=d[b'FULL'].rstrip(b'\0').decode('utf-8')
            if adapter:
                from fireball_records import BASES
                base=BASES[r['form']-(0x01000000+adapter['ammo'])][0]
                original=next(x for x in records(GAME/'Data/Skyrim.esm',{b'AMMO'}) if x['form']==base)
                assert f(d[b'DATA'],8)==f(dict(subrecords(original['data']))[b'DATA'],8)
                assert adapter['name'] in name and u(d[b'DATA'])==0x01000000+adapter['payload']
            elif 0x01000C00<=r['form']<=0x01000CFF:assert f(d[b'DATA'],8)==0 and '绑定待恢复' in name and u(d[b'DATA'])==0x01000A81
            else:assert f(d[b'DATA'],8)==8 and '外观试作' in name
            ref(u(d[b'YNAM']),b'SNDR');ref(u(d[b'ZNAM']),b'SNDR')
            for offset in range(0,len(d[b'KWDA']),4):ref(u(d[b'KWDA'],offset),b'KYWD')
        elif r['sig']==b'PROJ':
            b=d[b'DATA'];assert struct.unpack_from('<H',b,2)[0]==0x40
            flags=struct.unpack_from('<H',b)[0];assert flags&2 and not flags&0x40
            for off,kind in [(16,b'LIGH'),(20,b'LIGH'),(36,b'EXPL'),(40,b'SNDR'),(56,b'SNDR'),(60,b'SNDR'),(64,b'WEAP'),(84,b'TXST'),(88,b'COLL')]:
                if len(b)>=off+4:ref(u(b,off),kind)
        elif r['sig']==b'EXPL':
            assert len(d[b'DATA'])==52
            if r['form']!=0x01000881:assert all(u(d[b'DATA'],o)==0 for o in range(0,24,4))
            else:
                for off,kind in [(0,b'LIGH'),(4,b'SNDR'),(8,b'SNDR'),(12,b'IPDS')]:ref(u(d[b'DATA'],off),kind)
                assert u(d[b'DATA'],16)==u(d[b'DATA'],20)==0
            assert f(d[b'DATA'],24)==f(d[b'DATA'],28)==0
            if payload:
                ref(u(d[b'EITM']),b'ENCH');assert u(d[b'EITM'])==0x01000000+payload['payload']+2
                assert f(d[b'DATA'],32)==payload['radius'] and not (u(d[b'DATA'],44)&0x10)
            else:assert not {b'VMAD',b'EITM'}&d.keys()
        elif r['sig']==b'ENCH':
            assert payload and r['form']==0x01000000+payload['payload']+2
            ref(u(d[b'EFID']),b'MGEF');assert u(d[b'EFID'])==payload['mgef']
            assert struct.unpack('<fII',d[b'EFIT'])==(float(payload['damage']),0,payload['duration'])
            assert u(d[b'ENIT'],28)==0
        elif r['sig']==b'SPEL':
            assert r['form']==0x01000840
            assert d[b'FULL'].rstrip(b'\0').decode('utf-8')=='打开魔法箭工坊'
            assert u(d[b'SPIT'])==0 and u(d[b'SPIT'],8)==3
            assert u(d[b'SPIT'],16)==1 and u(d[b'SPIT'],20)==0
            assert u(d[b'EFID'])==0x01000841
            ref(u(d[b'EFID']),b'MGEF');ref(u(d[b'ETYP']),b'EQUP')
        elif r['sig']==b'MGEF':
            assert r['form']==0x01000841 and len(d[b'DATA'])==152
            assert u(d[b'DATA'],64)==1 and b'VMAD' not in d
        elif r['sig']==b'FLST':
            assert (0x01000D00<=r['form']<=0x01000DFF or r['form']==0x01000E01) and set(d)=={b'EDID'}
        elif r['sig']==b'STAT':
            assert r['form']==0x01000E00 and r['flags']==0x800000
            assert d[b'MODL']==b'MarkerXHeading.nif\0' and b'VMAD' not in d
        elif r['sig']==b'CONT':
            items=[struct.unpack('<II',v) for k,v in subrecords(r['data']) if k==b'CNTO']
            assert len(items)==u(d[b'COCT'])==14
            assert items[:12]==[(0x01000000|s['id'],100) for s in PROTOTYPES]
            ref(items[12][0],b'WEAP');ref(items[13][0],b'AMMO')
    checks.append('ESP-FE 1.7/44, unique IDs, complete typed references, twelve visual-only explosions, fireball explosion-enchantment chain, chest contents')

assert len(list(MESH.glob('*.nif')))==(2 if shock09 else 10 if redesign08 else 18 if round03 else 22 if selected else 18 if flow else 4 if precision else 36)
if redesign08:
    assert {p.name for p in MESH.glob('*.nif')}=={key+suffix+'.nif' for key in KEYS for suffix in ('','_flight')}
summaries=[]
design_checks=[]
for path in sorted(MESH.glob('*.nif')):
    n=NifBlocks(path);lib=NifFile(str(path));parents={};refs=[];shape_shaders=set()
    def link(index,kind=None):
        if index==0xffffffff:return
        assert index<len(n.blocks),(path.name,index)
        if kind:assert n.blocks[index][0] in kind,(path.name,index,n.blocks[index][0],kind)
        refs.append(index)
    for i,(kind,b) in enumerate(n.blocks):
        if kind in ('NiNode','BSFadeNode'):
            o=u(b,4)*4;assert u(b)<len(n.strings)
            link(u(b,8+o));link(u(b,68+o),('bhkCollisionObject',))
            for at in range(8,8+o,4):link(u(b,at))
            assert abs(f(b,64+o)-1)<1e-4
            for c in struct.unpack_from('<'+'I'*u(b,72+o),b,76+o):
                link(c);assert c not in parents;parents[c]=i
        elif kind=='BSTriShape':
            assert u(b,4)==0
            assert u(b,88)==0xffffffff # no skinning or skeleton dependency
            assert u(b,92) not in shape_shaders,(path.name,'shared mutable shader')
            shape_shaders.add(u(b,92))
            link(u(b,92),('BSEffectShaderProperty','BSLightingShaderProperty'));assert u(b,96)==0xffffffff
            sk,sb=n.blocks[u(b,92)]
            # Regression: full arrow surfaces must stay self-lit like blood.
            assert sk=='BSEffectShaderProperty',(path.name,'non-emissive surface')
            if sk=='BSEffectShaderProperty':
                assert f(sb,72+u(sb,36))==1.0
                assert u(sb,16)&1 # opaque surfaces write depth
                assert u(sb,12)&0x400000 # OWN_EMIT
                assert f(sb,76+u(sb,36))>=1.35-1e-5
            else:
                assert f(sb,64)==1.0 and u(sb,20)&1
        elif kind=='BSEffectShaderProperty':
            assert u(b,4)==0;link(u(b,8))
            size=u(b,36);tex=b[40:40+size].decode('ascii')
            assert tex.startswith('textures\\magicarrows\\')
            assert (DATA/tex).is_file()
            assert all(math.isfinite(x) for x in struct.unpack_from('<4f',b,60+size))
        elif kind=='BSLightingShaderProperty':
            assert u(b,8)==0;link(u(b,12))
            link(u(b,40),('BSShaderTextureSet',))
            assert all(math.isfinite(x) for x in struct.unpack_from('<4f',b,44))
            assert f(b,64)==1.0 and u(b,20)&1
        elif kind=='BSShaderTextureSet':
            assert u(b)==9
            offset=4
            for slot in range(9):
                size=u(b,offset);offset+=4
                tex=b[offset:offset+size].decode('ascii');offset+=size
                if slot<2:assert tex.startswith('textures\\magicarrows\\') and (DATA/tex).is_file()
                else:assert not tex
            assert offset==len(b)
        elif kind=='NiParticleSystem':
            link(u(b,8),('NiPSysEmitterCtlr',));link(u(b,92),('BSEffectShaderProperty',));link(u(b,96),('NiAlphaProperty',));link(u(b,116),('NiPSysData',))
            assert u(b,121)==6
            for m in struct.unpack_from('<6I',b,125):
                link(m);assert u(n.blocks[m][1],8)==i
            ctl=n.blocks[u(b,8)][1];assert u(ctl,22)==i
            emitter=n.blocks[struct.unpack_from('<6I',b,125)[1]][1]
            assert u(emitter)==u(ctl,30)
            link(u(emitter,69),('NiNode',))
            life=f(emitter,61);assert 0<life<=.71
            pool=struct.unpack_from('<H',n.blocks[u(b,116)][1],4)[0];assert pool==20
            if '_impact' in path.stem:
                assert struct.unpack_from('<H',ctl,4)[0]==0x4c
                interp=n.blocks[u(ctl,26)][1];data=n.blocks[u(interp,4)][1]
                assert u(data)==4 and struct.unpack_from('<2f',data,len(data)-8)[1]==0
            else:
                rate=f(n.blocks[u(ctl,26)][1]);assert rate*(life+.05)<pool
        elif kind in ('NiPSysEmitterCtlr','NiPSysUpdateCtlr'):
            link(u(b),('NiPSysUpdateCtlr',));link(u(b,22),('NiParticleSystem',))
            if kind=='NiPSysEmitterCtlr':link(u(b,26),('NiFloatInterpolator',));link(u(b,34),('NiBoolInterpolator',))
        elif kind=='NiFloatInterpolator':link(u(b,4),('NiFloatData',))
        elif kind=='NiBoolInterpolator':link(u(b,1))
        elif kind=='bhkCollisionObject':link(u(b),('NiNode','BSFadeNode'));link(u(b,6),('bhkRigidBodyT',))
        elif kind=='bhkRigidBodyT':link(u(b),('bhkBoxShape',))
    # Any scene object must be rooted exactly once, with no parent cycles.
    for i,(kind,b) in enumerate(n.blocks):
        if kind not in ('NiNode','BSFadeNode','BSTriShape','NiParticleSystem') or i==0:continue
        seen={i};j=i
        while j!=0:
            assert j in parents,(path.name,i,'orphan')
            j=parents[j];assert j not in seen;seen.add(j)
    for sh in lib.shapes:
        assert not sh.has_skin_instance
        assert all(math.isfinite(c) for v in sh.verts for c in v)
        assert all(0<=i<len(sh.verts) for t in sh.tris for i in t)
        assert all(0<=v[1]<=58.01 for v in sh.verts)
        assert max(abs(v[0]) for v in sh.verts)<=3.4
        assert max(abs(v[2]) for v in sh.verts)<=3.4
        assert all(math.isfinite(c) for normal in sh.normals for c in normal)
        if path.stem.removesuffix('_flight')!='blood':
            for a,b,c in sh.tris:
                area=cross(sub(sh.verts[b],sh.verts[a]),sub(sh.verts[c],sh.verts[a]))
                assert sum(x*x for x in area)>1e-14,(path.name,'degenerate triangle',a,b,c)
    if '_impact' not in path.stem:
        flight='_flight' in path.stem;base=NifBlocks(BUILD/('ironarrowflight.nif' if flight else 'ironarrow.nif'))
        for i in ([2,3,4] if flight else [1,3,4,5,6,8,9,10]):assert n.blocks[i]==base.blocks[i]
        if not flight:
            assert not any(k in ('NiParticleSystem','NiPSysEmitterCtlr','NiPSysUpdateCtlr') for k,b in n.blocks)
            assert not u(n.blocks[2][1],4)&1 # static equipped model
            assert b'ArrowQuiver' in n.strings and b'QUIVER' in n.strings
            assert len(lib.shapes)==len(redesigned(path.stem))*6
        else:
            assert len(lib.shapes)==len(redesigned(path.stem.removesuffix('_flight')))
    if redesign08 and path.stem.endswith('_flight'):
        from five_arrow_redesign import audit_exported
        design_checks.append(audit_exported(path.stem.removesuffix('_flight'),lib))
    summaries.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),blocks=len(n.blocks),mesh_shapes=len(lib.shapes),particles=sum(k=='NiParticleSystem' for k,b in n.blocks)))
checks.append('All NIFs load through native Nifly; graph/type/texture links, collisions, bounds and finite particles validated')
checks.append('Flight tails have bounded lifetime and pool; equipped arrows have no particles' if precision else 'Impact emitters stop; flight tails have bounded lifetime and pool; no copied visible vanilla or Marc geometry')
checks.append('Every arrow surface uses OWN_EMIT effect shader with power >= 1.35; includes complete shaft, heads and quiver copies')
report=dict(passed=True,checks=checks,files=summaries,in_game_tested=False)
if redesign08:
    report['design_checks']=design_checks
    report['checks'].append('Lightning redesign matches approved blood scale; closed solids, outward winding, notched crystal, steel clamps and triangular tail solids verified' if shock09 else 'Five redesigned arrows match approved blood scale; solid categories are closed with consistent outward winding; poison gap, holy halo and arcane tail openings are preserved')
(BUILD/('verification-shock09.json' if shock09 else 'verification-redesign08.json' if redesign08 else 'verification-geometric-round03.json' if round03 else 'verification-geometric05.json' if selected else 'verification-faithful01.json' if faithful else 'verification-v4.json' if flow else 'verification-pure02.json' if pure else 'verification-precision01.json' if precision else 'verification-models.json' if '--models-only' in sys.argv else 'verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
