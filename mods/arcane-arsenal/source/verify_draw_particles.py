"""Independent native nifly parse/write followed by semantic block comparison.

Native nifly reorders blocks and strings. Normalize those IDs before comparing
every authored particle block so parser changes/dropped fields are detectable.
This verifies serialization, not the game's renderer or Papyrus event delivery.
"""
from pathlib import Path
import sys,struct,json,collections
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
key=sys.argv[1] if len(sys.argv)>1 else 'redplates'
is_aries=key.startswith(('aries','taurus','gemini','cancer','leo','virgo','libra','sagittarius','capricorn','aquarius','pisces','scorpio','crystal','heteromorphic','geo')) or key in ('redplates','redtriangles','reddiamonds')
base_count=json.loads((ROOT/'build'/(key+'-particles.json')).read_text(encoding='utf-8'))['old_block_count'] if is_aries else 37
source=ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif')
copy=ROOT/'build'/(key+'-particles-roundtrip.nif')
native=NifFile(str(source));assert len(native.shapes)==(3 if is_aries else 4)
assert not NifFile.message_log(),NifFile.message_log()
native.filepath=str(copy);native.save()
assert not NifFile.message_log(),NifFile.message_log()
a,b=NifBlocks(source),NifBlocks(copy)
assert collections.Counter(k for k,v in a.blocks)==collections.Counter(k for k,v in b.blocks)
u=lambda blob,offset=0:struct.unpack_from('<I',blob,offset)[0]
def name(n,kind,blob):
    if kind in ('NiNode','NiParticleSystem') or kind.endswith(('Modifier','Emitter')):
        return n.strings[u(blob)]
    return None
lookup={name(b,k,v):i for i,(k,v) in enumerate(b.blocks) if name(b,k,v)}
mapping={i:lookup[name(a,k,v)] for i,(k,v) in enumerate(a.blocks) if name(a,k,v)}
systems=[i for i,(k,v) in enumerate(a.blocks) if k=='NiParticleSystem']
def match_ref(ai,bi,offset):
    av,bv=u(a.blocks[ai][1],offset),u(b.blocks[bi][1],offset)
    if av!=0xffffffff:
        if av in mapping:assert mapping[av]==bv
        mapping[av]=bv
for ai in systems:
    bi=mapping[ai]
    for offset in (8,92,96,116):match_ref(ai,bi,offset)
    for offset in range(125,149,4):match_ref(ai,bi,offset)
    ac,bc=u(a.blocks[ai][1],8),u(b.blocks[bi][1],8)
    for offset in (0,26,34):match_ref(ac,bc,offset)
verified=[]
for ai,bi in mapping.items():
    kind,blob=a.blocks[ai]
    # Existing skeleton nodes are independently covered by verify_rig.py.
    is_particle=ai>=base_count
    if not is_particle:continue
    assert b.blocks[bi][0]==kind
    normalized=bytearray(blob)
    string_offsets=[];ref_offsets=[]
    if kind in ('NiNode','NiParticleSystem'):
        string_offsets=[0];ref_offsets=[8]
        if kind=='NiNode':ref_offsets+=list(range(76,76+4*u(blob,72),4))
        else:ref_offsets += [92,96,116]+list(range(125,149,4))
    elif kind.endswith(('Modifier','Emitter')):
        string_offsets=[0];ref_offsets=[8]
        if kind=='NiPSysBoxEmitter':ref_offsets+=[69]
        if kind=='NiPSysAgeDeathModifier':ref_offsets+=[14]
    elif kind=='NiPSysEmitterCtlr':
        ref_offsets=[0,22,26,34];string_offsets=[30]
    elif kind=='NiPSysUpdateCtlr':ref_offsets=[0,22]
    elif kind=='NiFloatInterpolator':ref_offsets=[4]
    elif kind=='NiBoolInterpolator':ref_offsets=[1]
    for offset in string_offsets:
        old=u(blob,offset)
        if old!=0xffffffff:struct.pack_into('<I',normalized,offset,b.strings.index(a.strings[old]))
    for offset in ref_offsets:
        old=u(blob,offset)
        if old!=0xffffffff:struct.pack_into('<I',normalized,offset,mapping[old])
    assert bytes(normalized)==b.blocks[bi][1],(ai,kind,'native roundtrip changed authored values')
    verified.append(ai)
assert len(verified)==(96 if is_aries else 91),len(verified)
particle_report=json.loads((ROOT/'build'/(key+'-particles.json')).read_text(encoding='utf-8')) if is_aries else {'texture':'aa_red_dust.dds'}
for name in particle_report.get('textures',[particle_report['texture']]):
    texture=ROOT/'data/textures/weapons/arcanearsenal'/name
    dds=texture.read_bytes();assert len(dds)==128+128*128*4 and dds[:4]==b'DDS '
    assert struct.unpack_from('<II',dds,12)==(128,128)
    assert max(dds[131::4])>200 and min(dds[131::4])==0
report={'passed':True,'native_parser':'nifly via PyNifly 28.2','particle_blocks_roundtripped':len(verified),
        'particle_systems':len(systems),'texture_alpha_checked':True,'scope':'Offline structural checks; no in-game particle playback test.'}
(ROOT/'build'/(key+'-particles-verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
