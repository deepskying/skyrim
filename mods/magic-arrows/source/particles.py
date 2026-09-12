"""Bounded native Skyrim particle systems, using vanilla block-layout defaults."""
import math,struct
from nif_blocks import NifBlocks
from paths import BUILD
p=lambda fmt,*v:struct.pack('<'+fmt,*v)
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
def put(b,o,fmt,*v):struct.pack_into('<'+fmt,b,o,*v)

def children(n,index,items,replace=False):
    kind,b=n.blocks[index];off=4*u(b,4);at=72+off;count=u(b,at)
    old=[] if replace else list(struct.unpack_from('<'+'I'*count,b,at+4))
    n.blocks[index]=(kind,b[:at]+p('I',len(old)+len(items))+p('I'*(len(old)+len(items)),*(old+items))+b[at+4+4*count:])

def effect_shader(path,color,alpha=1,strength=1):
    tex=path.encode('ascii')
    # Emissive, depth tested, double-sided, no material-light dependence.
    b=p('iIiII4f',-1,0,-1,0x80400000,0x10,0,0,1,1)
    return b+p('I',len(tex))+tex+p('4B',3,0,0,0)+p('4f',1,1,1,1)+p('4f',*color,alpha)+p('ffI',strength,1,0)

def add_particles(n,parent,spec,position,flight=False,index=0,burst=False):
    src=NifBlocks(BUILD/'fxsparkfountain.nif')
    selected=[3,4,5,6,7,8,9,11,12,13,15,17,21,22]
    expected=['NiNode','NiPSysData','NiParticleSystem','NiPSysEmitterCtlr','NiPSysUpdateCtlr','NiFloatInterpolator','NiBoolInterpolator','BSEffectShaderProperty','NiAlphaProperty','NiPSysAgeDeathModifier','NiPSysBoxEmitter','BSPSysSimpleColorModifier','NiPSysPositionModifier','NiPSysBoundUpdateModifier']
    assert [src.blocks[i][0] for i in selected]==expected
    mapping={i:n.append(src.blocks[i][0],b'') for i in selected}
    grow=n.append('NiPSysGrowFadeModifier',b'')
    names={i:n.string(f'MA_{spec["key"]}_Motes{index}_{i}') for i in (3,5,13,15,17,21,22)}
    rate=100.0 if burst else 22.0 if flight else 4.0
    life=.45 if burst else .22 if flight else .7
    for i in selected:
        kind,b0=src.blocks[i];b=bytearray(b0)
        if i==3:
            put(b,0,'I',names[i]);put(b,8,'i',-1);put(b,12,'I',14)
            put(b,16,'3f',*position);put(b,28,'9f',1,0,0,0,1,0,0,0,1);put(b,64,'f',1)
            put(b,76,'I',mapping[5])
        elif i==4:put(b,4,'H',20)
        elif i==5:
            assert len(b)==165 and u(b,116)==4 and u(b,121)==10
            put(b,0,'I',names[i]);put(b,8,'I',mapping[6]);put(b,84,'f',1200 if flight else 8)
            put(b,92,'II',mapping[11],mapping[12]);put(b,116,'I',mapping[4])
            mods=[mapping[13],mapping[15],mapping[17],grow,mapping[21],mapping[22]]
            b=b[:120]+p('BI',1 if flight else 0,len(mods))+p('6I',*mods)
        elif i in (6,7):
            put(b,0,'i',mapping[7] if i==6 else -1);put(b,4,'H',0x4c if burst else 0x48)
            put(b,6,'4f',1,0,0,.85 if burst else 1);put(b,22,'I',mapping[5])
            if i==6:put(b,26,'III',mapping[8],names[15],mapping[9])
        elif i==8:b=bytearray(p('fi',rate,-1))
        elif i==9:b=bytearray(p('Bi',1,-1))
        elif i==11:
            b=bytearray(effect_shader('textures\\magicarrows\\'+spec['particle']+'.dds',spec['color'],.7,1.1))
            put(b,12,'I',0x80000008);put(b,16,'I',0x20)
        elif i==12:b=bytearray(p('iIiHB',-1,0,-1,0x100d,0))
        elif i in (13,15,17,21,22):
            put(b,0,'I',names[i]);put(b,8,'I',mapping[5])
            if i==13:put(b,13,'Bi',0,-1)
            elif i==15:
                put(b,13,'6f',24 if burst else 2.2,8 if burst else 1,math.pi/2,math.pi/2,0,math.pi)
                put(b,37,'4f',1,1,1,1)
                put(b,53,'4f',.32 if spec['key']=='blood' else .42,.10,life,.05)
                put(b,69,'I3f',mapping[3],.65,1.8,.65)
            elif i==17:
                put(b,13,'6f',.1,.7,.1,.18,.55,.85)
                put(b,37,'12f',1,1,1,0,1,1,1,1,1,1,1,0)
        n.blocks[mapping[i]]=(kind,bytes(b))
    n.blocks[grow]=('NiPSysGrowFadeModifier',p('IIIB',n.string(f'MA_Grow{index}'),4000,mapping[5],1)+p('fHfHf',.04,0,.12,0,1))
    if burst:
        keys=[(0,rate),(.06,rate),(.12,0),(.85,0)]
        data=n.append('NiFloatData',p('II',len(keys),1)+b''.join(p('ff',*key) for key in keys))
        n.blocks[mapping[8]]=('NiFloatInterpolator',p('fI',rate,data))
        # Burst travels only a few units but must not be culled at the spawn point.
        k,b=n.blocks[mapping[5]];b=bytearray(b);put(b,84,'f',24);n.blocks[mapping[5]]=(k,bytes(b))
    children(n,parent,[mapping[3]])
    return dict(rate=rate,life=life,pool=20,world_space=flight,burst=burst,node=mapping[3])
