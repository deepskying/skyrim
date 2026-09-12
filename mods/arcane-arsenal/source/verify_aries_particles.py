"""Check final particle anchors, transform invertibility and bounded native playback.

Run with Blender. Raw NIF readback is compared with the separate source model
anchors and the unchanged geometry base, including parent hierarchy transforms.
"""
import sys,json,struct,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
SERIES='heteromorphic2' if '--heteromorphic2' in sys.argv else 'crystal' if '--crystal' in sys.argv else 'heteromorphic' if '--heteromorphic' in sys.argv else 'scorpio' if '--scorpio' in sys.argv else 'pisces' if '--pisces' in sys.argv else 'aquarius' if '--aquarius' in sys.argv else 'capricorn' if '--capricorn' in sys.argv else 'sagittarius' if '--sagittarius' in sys.argv else 'libra' if '--libra' in sys.argv else 'virgo' if '--virgo' in sys.argv else 'leo' if '--leo' in sys.argv else 'cancer' if '--cancer' in sys.argv else 'gemini' if '--gemini' in sys.argv else 'geometric' if '--geometric' in sys.argv else 'taurus' if '--taurus' in sys.argv else 'aries'
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
f=lambda b,o=0:struct.unpack_from('<f',b,o)[0]
reports=[]
for spec in json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8')):
    key=spec['key'];n=NifBlocks(ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif'))
    base=NifBlocks(ROOT/'build'/(SERIES+'-base')/(key+'.nif'))
    source=json.loads((ROOT/'build'/(key+'-model.json')).read_text(encoding='utf-8'))
    names={n.strings[u(b)].decode():i for i,(k,b) in enumerate(n.blocks) if k in ('NiNode','BSFadeNode')}
    parents={}
    for i,(k,b) in enumerate(n.blocks):
        if k not in ('NiNode','BSFadeNode'):continue
        offset=4*u(b,4)
        for child in struct.unpack_from('<'+'I'*u(b,72+offset),b,76+offset):
            assert child not in parents,(key,child,'multiple parents')
            parents[child]=i
    def matrix(index,visible=False):
        b=n.blocks[index][1];o=4*u(b,4);r=struct.unpack_from('<9f',b,28+o)
        m=Matrix([r[j:j+3] for j in (0,3,6)]).to_4x4()
        scale=1 if visible else f(b,64+o)
        for i in range(3):
            for j in range(3):m[i][j]*=scale
        m.translation=Vector(struct.unpack_from('<3f',b,16+o));return m
    def world(index):return world(parents[index])@matrix(index) if index in parents else matrix(index)
    touched=set();max_anchor_error=0
    assert not any('Hexagram' in s.decode() for s in n.strings)  # Classic static stars are ordinary skinned geometry.
    assert len([k for k,b in n.blocks if k=='NiParticleSystem'])==6
    for j,anchor in enumerate(source['particle_anchors']):
        index=names['AAAriesDust'+str(j)];parent=parents[index]
        assert parent==names[anchor['bone']]
        touched.add(parent)
        assert abs(f(n.blocks[index][1],64)-.0001)<1e-8
        assert abs(matrix(index).to_3x3().determinant())>1e-13
        actual=world(parent)@matrix(index,True)
        error=(actual.translation-Vector(anchor['position'])).length
        assert error<.001,(key,j,error);max_anchor_error=max(max_anchor_error,error)
        # Emission axes preserve unit length under the original bone transforms.
        for col in actual.to_3x3().col:assert abs(col.length-1)<.001
    for i,old in enumerate(base.blocks):
        if i not in touched:assert n.blocks[i]==old,(key,i,'base changed')
        else:
            b=n.blocks[i][1];assert b[:72]==old[1][:72]
            old_children=struct.unpack_from('<'+'I'*u(old[1],72),old[1],76)
            new_children=struct.unpack_from('<'+'I'*u(b,72),b,76)
            assert tuple(new_children[:len(old_children)])==old_children
    for i,(k,b) in enumerate(n.blocks):
        if k=='NiParticleSystem':
            assert b[120]==0 and u(b,121)==6
            assert f(b,84)>=spec['speed']*1.35*spec['life']*1.15+spec['radius']*1.3
            data=n.blocks[u(b,116)][1];assert struct.unpack_from('<H',data,4)[0]==spec['pool']
            ctlr=n.blocks[u(b,8)][1]
            assert struct.unpack_from('<H',ctlr,4)[0]==0x48 and u(ctlr,22)==i
            assert abs(f(n.blocks[u(ctlr,26)][1])-spec['rate'])<1e-5
            assert n.blocks[u(ctlr,34)][1][0]==1
            mods=struct.unpack_from('<6I',b,125)
            for m in mods:assert u(n.blocks[m][1],8)==i
            emitter=n.blocks[mods[1]][1]
            assert u(emitter)==u(ctlr,30)
            assert parents[i]==u(emitter,69)
            assert abs(f(emitter,61)-spec['life'])<1e-5
            assert spec['rate']*spec['life']*1.15<spec['pool']
    reports.append({'key':key,'passed':True,'anchor_error':max_anchor_error,'native_systems':6,'base_geometry_unchanged':True,'particle_pool_per_view':6*spec['pool']})
(ROOT/'build'/(SERIES+'-particles-placement-verification.json')).write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports))
