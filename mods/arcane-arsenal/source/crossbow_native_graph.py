"""Graft authored skin/material blocks onto the intact native crossbow rig.

PyNifly does not round-trip the crossbow's embedded controller sequence. Keep
the original graph, bone transforms, behavior path and collision configuration.
Only the visible geometry is replaced. No vanilla visible mesh is distributed.
"""
import struct
from nif_blocks import NifBlocks
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
def graft(reference,generated,destination):
    ref=NifBlocks(reference);src=NifBlocks(generated)
    assert ref.blocks[39][0]=='BSTriShape'
    ref.blocks=ref.blocks[:39]
    nodes={ref.strings[u(b)]:i for i,(k,b) in enumerate(ref.blocks) if k in ('NiNode','BSFadeNode')}
    supported={'BSTriShape','NiSkinInstance','NiSkinData','NiSkinPartition','BSLightingShaderProperty','BSShaderTextureSet','NiAlphaProperty'}
    picked=[i for i,(k,b) in enumerate(src.blocks) if k in supported]
    remap={i:39+j for j,i in enumerate(picked)}
    for i,(k,b) in enumerate(src.blocks):
        if k in ('NiNode','BSFadeNode'):
            name=src.strings[u(b)]
            if i==0:remap[i]=0
            elif name in nodes:remap[i]=nodes[name]
    def link(b,o):
        value=u(b,o)
        if value!=0xffffffff:struct.pack_into('<I',b,o,remap[value])
    def string(b,o):
        value=u(b,o)
        if value!=0xffffffff:struct.pack_into('<I',b,o,ref.string(src.strings[value]))
    shapes=[]
    for i in picked:
        kind,blob=src.blocks[i];b=bytearray(blob)
        if kind=='BSTriShape':
            string(b,0);assert u(b,4)==0
            for o in (8,68,88,92,96):link(b,o)
            shapes.append(remap[i])
        elif kind=='NiSkinInstance':
            for o in (0,4):link(b,o)
            struct.pack_into('<I',b,8,0)
            for j in range(u(b,12)):link(b,16+4*j)
        elif kind=='BSLightingShaderProperty':
            string(b,4);assert u(b,8)==0;link(b,12);link(b,40)
        elif kind=='NiAlphaProperty':
            string(b,0);assert u(b,4)==0;link(b,8)
        ref.append(kind,b)
    kind,b=ref.blocks[0];off=4*u(b,4);n=u(b,72+off)
    children=list(struct.unpack_from('<'+'I'*n,b,76+off));assert children==[5,39]
    children=[5]+shapes
    ref.blocks[0]=(kind,b[:72+off]+struct.pack('<I',len(children))+struct.pack('<'+'I'*len(children),*children)+b[76+off+4*n:])
    ref.save(destination)
    return shapes
