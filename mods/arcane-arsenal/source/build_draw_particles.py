"""Add native NiParticleSystem star dust to the existing Redplates experiment.

Only block payloads with a documented Skyrim SE layout are authored here.
The installed vanilla fountain supplies structural defaults, never geometry or
textures. Its world-space, gravity, palette and burst settings are replaced.
"""
from pathlib import Path
import struct,math,json,hashlib
from nif_blocks import NifBlocks
from bsa_reference import extract
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.4.2/redplates.nif'
DEST=ROOT/'data/meshes/weapons/arcanearsenal/redplates.nif'
TEMPLATE=ROOT/'build/fxsparkfountain.nif'
if not TEMPLATE.is_file():
    TEMPLATE.write_bytes(extract(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data\Skyrim - Meshes0.bsa','meshes/effects/fxsparkfountain.nif'))
n=NifBlocks(BASE);src=NifBlocks(TEMPLATE)
original=list(n.blocks)
p=lambda fmt,*v:struct.pack('<'+fmt,*v)
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
def patch(b,offset,fmt,*values):struct.pack_into('<'+fmt,b,offset,*values)
def named(name):
    return next(i for i,(k,b) in enumerate(n.blocks) if k=='NiNode' and n.strings[u(b)]==name.encode())
def children(index,extra):
    kind,b=n.blocks[index];assert kind=='NiNode' and u(b,4)==0
    count=u(b,72);end=76+4*count
    assert b[end:]==p('I',0)
    n.blocks[index]=(kind,b[:72]+p('I',count+len(extra))+b[76:end]+p('I'*len(extra),*extra)+b[end:])
mid=named('Bow_MidBone');star=named('AAHexagramDrawFX')
root=bytearray(n.blocks[star][1][:72])+p('II',0,0)
patch(root,0,'I',n.string('AARedDrawParticles'))
# Non-zero hidden scale avoids singular inverses in native particle emitter math.
patch(root,64,'f',.0001)
particle_root=n.append('NiNode',root);children(mid,[particle_root])

# Original white opacity mask: 4x4 identical soft diamonds for the native atlas.
texture=ROOT/'data/textures/weapons/arcanearsenal/aa_red_dust.dds'
size=128;rgba=bytearray()
for y in range(size):
    for x in range(size):
        dx=((x%32)+.5-16)/15;dy=((y%32)+.5-16)/15
        alpha=max(0,1-abs(dx)-abs(dy))**1.6
        rgba+=bytes((255,255,255,round(255*alpha)))
header=p('7I',124,0x100f,size,size,size*4,0,1)+p('11I',*([0]*11))
header+=p('8I',32,0x41,0,32,0xff0000,0xff00,0xff,0xff000000)+p('5I',0x1000,0,0,0,0)
assert len(header)==124
texture.write_bytes(b'DDS '+header+rgba)

selected=[3,4,5,6,7,8,9,11,12,13,15,17,21,22]
expected=['NiNode','NiPSysData','NiParticleSystem','NiPSysEmitterCtlr','NiPSysUpdateCtlr','NiFloatInterpolator','NiBoolInterpolator','BSEffectShaderProperty','NiAlphaProperty','NiPSysAgeDeathModifier','NiPSysBoxEmitter','BSPSysSimpleColorModifier','NiPSysPositionModifier','NiPSysBoundUpdateModifier']
assert [src.blocks[i][0] for i in selected]==expected
systems=[];links=[];emitters=[]
for j in range(6):
    mapping={i:n.append(src.blocks[i][0],b'') for i in selected}
    grow=n.append('NiPSysGrowFadeModifier',b'')
    refs=lambda i:mapping[i]
    names={i:n.string(f'AADust{j}_'+src.strings[u(src.blocks[i][1])].decode()) for i in (3,5,13,15,17,21,22)}
    for i in selected:
        kind,b0=src.blocks[i];b=bytearray(b0)
        if i==3:
            patch(b,0,'I',names[i]);patch(b,76,'I',refs(5))
            angle=math.pi/2+j*math.tau/6
            patch(b,16,'3f',0,12*math.sin(angle),12*math.cos(angle))
        elif i==4:
            # Maximum particle pool, not a burst count. Atlas table is unchanged.
            patch(b,4,'H',12)
        elif i==5:
            assert len(b)==165 and u(b,116)==4 and u(b,121)==10
            patch(b,0,'I',names[i]);patch(b,8,'I',refs(6))
            patch(b,84,'f',5.0)  # local bound radius, with short-lived slow dust
            patch(b,92,'II',refs(11),refs(12));patch(b,116,'I',refs(4))
            modifiers=[refs(13),refs(15),refs(17),grow,refs(21),refs(22)]
            b=b[:120]+p('BI',0,len(modifiers))+p('I'*len(modifiers),*modifiers)
            links.extend([(refs(5),8,refs(6)),(refs(5),92,refs(11)),(refs(5),96,refs(12)),(refs(5),116,refs(4))])
            systems.append(refs(5))
        elif i in (6,7):
            patch(b,0,'i',refs(7) if i==6 else -1)
            patch(b,4,'H',0x48)  # active, application time, loop; no manager
            patch(b,6,'4f',1,0,0,1)
            patch(b,22,'I',refs(5))
            if i==6:
                patch(b,26,'III',refs(8),names[15],refs(9))
        elif i==8:b=bytearray(p('fi',5.0,-1))  # particles/second per emitter
        elif i==9:b=bytearray(p('Bi',1,-1))  # continuously active; visibility is separate
        elif i==11:
            path=b'textures\\weapons\\arcanearsenal\\aa_red_dust.dds'
            # NiObjectNET, shader flags (vertex alpha + depth test), UV settings.
            b=bytearray(p('iIiII4f',-1,0,-1,0x80000008,0x20,0,0,1,1))
            b+=p('I',len(path))+path+p('4B',3,0,0,0)
            b+=p('4f',1,1,1,1)+p('4f',1,.035,.005,1)+p('ffI',.9,5.0,0)
        elif i==12:b=bytearray(p('iIiHB',-1,0,-1,0x100d,0))  # additive SRC_ALPHA / ONE
        elif i in (13,15,17,21,22):
            patch(b,0,'I',names[i]);patch(b,8,'I',refs(5))
            if i==13:patch(b,13,'Bi',0,-1)  # do not spawn on death
            if i==15:
                patch(b,13,'6f',2.4,1.0,math.pi/2,math.pi/2,0,math.pi)
                patch(b,37,'4f',1,1,1,1)
                patch(b,53,'4f',.48,.16,.65,.15)
                patch(b,69,'I3f',refs(3),.7,.7,.7)
                emitters.append(refs(15))
            if i==17:
                patch(b,13,'6f',.12,.68,.12,.2,.6,.8)
                patch(b,37,'12f',1,1,1,0,1,1,1,1,1,1,1,0)
        n.blocks[refs(i)]=(kind,bytes(b))
    modifier=p('IIIB',n.string(f'AADust{j}_GrowFade'),4000,refs(5),1)
    n.blocks[grow]=('NiPSysGrowFadeModifier',modifier+p('fHfHf',.08,0,.25,0,1))
    children(particle_root,[refs(3)])

n.save(DEST)
actual=NifBlocks(DEST)
assert actual.blocks==n.blocks and actual.strings==n.strings
for i,old in enumerate(original):
    if i!=mid:assert actual.blocks[i]==old,(i,old[0])
# The middle bone only gains a child: its flags, rest transform and old children survive.
assert actual.blocks[mid][1][:72]==original[mid][1][:72]
for index in systems:
    blob=actual.blocks[index][1];assert blob[120]==0 and u(blob,121)==6
    for modifier in struct.unpack_from('<6I',blob,125):
        assert actual.blocks[modifier][0].endswith(('Modifier','Emitter'))
        assert u(actual.blocks[modifier][1],8)==index
for index in emitters:
    b=actual.blocks[index][1];assert abs(struct.unpack_from('<f',b,61)[0]-.65)<1e-6
    assert actual.blocks[u(b,69)][0]=='NiNode'
for index,offset,target in links:assert u(actual.blocks[index][1],offset)==target
assert abs(struct.unpack_from('<f',actual.blocks[particle_root][1],64)[0]-.0001)<1e-8
report={'version':'0.4.2','native_particle_systems':6,'space':'local','birth_rate_per_system':5,
        'max_particle_pool_per_system':12,'typical_live_particles_per_view':21,
        'lifetime_seconds':[.5,.8],'independent_control_node':'AARedDrawParticles','hidden_scale':.0001,
        'texture':str(texture),'texture_sha256':hashlib.sha256(texture.read_bytes()).hexdigest(),
        'old_block_count':len(original),'new_block_count':len(actual.blocks),'old_meshes_unchanged':True,
        'validation':'Block layouts, references, controller links, lifespan and local-space checks passed. In-game playback remains untested.'}
(ROOT/'build/draw-particles-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
