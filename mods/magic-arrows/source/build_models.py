"""Build original magic-arrow meshes on vanilla attachment/collision scaffolding."""
import struct,json,math
from paths import *
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks
from geometry import generate,Mesh
from design_catalog import study
from game_specs import PROTOTYPES
from particles import children,effect_shader,add_particles
p=lambda fmt,*v:struct.pack('<'+fmt,*v)
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
def put(b,o,fmt,*v):struct.pack_into('<'+fmt,b,o,*v)

def dds(name,kind):
    size=128;rgba=bytearray()
    for y in range(size):
        for x in range(size):
            dx=((x%32)+.5-16)/15;dy=((y%32)+.5-16)/15
            if kind=='solid':a=1
            elif kind=='drop':
                width=.52*(1-(dy+.9)/2.0)
                a=max(0,1-math.sqrt((dx/max(.10,width))**2+((dy+.05)/.88)**2))**.55
            elif kind=='star':
                a=max(0,1-math.sqrt(dx*dx+dy*dy)*1.8)**1.6
                a=max(a,max(0,1-abs(dx)*13-abs(dy)*1.1)**1.4,max(0,1-abs(dy)*13-abs(dx)*1.1)**1.4)
            else:a=max(0,1-abs(dx)-abs(dy))**1.6
            rgba+=bytes((255,255,255,round(255*min(1,a))))
    header=p('7I',124,0x100f,size,size,size*4,0,1)+p('11I',*([0]*11))
    header+=p('8I',32,0x41,0,32,0xff,0xff00,0xff0000,0xff000000)+p('5I',0x1000,0,0,0,0)
    (TEX/(name+'.dds')).write_bytes(b'DDS '+header+rgba)

for key in ('solid','drop','spark','star'):dds(key,key)

def node(n,name,transform=None):
    transform=transform or p('3f9ff',0,0,0,1,0,0,0,1,0,0,0,1,1)
    return n.append('NiNode',p('IIiI',n.string(name),0,-1,14)+transform+p('iII',-1,0,0))

def attach_mesh(n,src,mesh_id,name,parent,shader,alpha):
    k,b=src.blocks[mesh_id];assert k=='BSTriShape' and u(b,4)==0
    b=bytearray(b);put(b,0,'I',n.string(name));put(b,8,'i',-1);put(b,12,'I',14)
    put(b,16,'3f9ff',0,0,0,1,0,0,0,1,0,0,0,1,1)
    shader=n.append(*n.blocks[shader])
    put(b,68,'i',-1);put(b,88,'i',-1);put(b,92,'II',shader,alpha)
    i=n.append(k,b);children(n,parent,[i]);return i

report=[]
for spec in PROTOTYPES:
    key=spec['key'];parts=study(key)
    # Solid arrow geometry; bloom comes from emission, not a transparent shell.
    parts.pop('aura',None)
    geometry_path=BUILD/(key+'-geometry.nif')
    nf=NifFile();nf.initialize('SKYRIMSE',str(geometry_path))
    for category,m in parts.items():
        nf.createShapeFromData(category,m.verts,m.tris,m.uv,m.normals())
    nf.save();src=NifBlocks(geometry_path)
    src_shapes={src.strings[u(b)].decode():i for i,(k,b) in enumerate(src.blocks) if k=='BSTriShape'}
    assert set(src_shapes)==set(parts)
    for flight in (False,True):
        n=NifBlocks(BUILD/('ironarrowflight.nif' if flight else 'ironarrow.nif'))
        original=NifFile(str(BUILD/('ironarrowflight.nif' if flight else 'ironarrow.nif')))
        # Preserve only vanilla collision and attachment metadata, not its visible meshes.
        transforms={s.name:n.blocks[s.id][1][16:68] for s in original.shapes}
        n.blocks=n.blocks[:5 if flight else 11]
        children(n,0,[] if flight else [7],True)
        if not flight:children(n,7,[],True)
        # BSX animation bit is needed for native particle playback.
        bsx=1 if flight else 2
        k,b=n.blocks[bsx];n.blocks[bsx]=(k,b[:4]+p('I',(u(b,4)|1) if flight else (u(b,4)&~1)))
        shaders={}
        alpha=0xffffffff # no alpha blending on solid arrow meshes
        for cat,opacity,power in [('body',1.0,1.35),('core',1.0,2.0)]:
            shader=bytearray(effect_shader('textures\\magicarrows\\solid.dds',spec['core'] if cat=='core' else spec['color'],opacity,power))
            put(shader,16,'I',0x11) # double-sided and depth writing
            shaders[cat]=n.append('BSEffectShaderProperty',bytes(shader))
        full_name='IronArrowFlight:0' if flight else 'Arrow:0'
        full=node(n,'MAArrowVisual' if flight else 'Arrow:0',transforms[full_name]);children(n,0,[full])
        for cat,idx in src_shapes.items():attach_mesh(n,src,idx,'MA_'+key+'_'+cat,full,shaders[cat],alpha)
        # Equipped models remain emissive but static; animated FX stay on projectiles.
        stats=[add_particles(n,full,spec,(0,8,0),True,index=0)] if flight else []
        if not flight:
            # Five complete energy arrows replace both ordinary arrows and leather quiver.
            # Their original spread/attachment transforms are retained exactly.
            for j in range(1,6):
                q=node(n,'Arrow'+str(j),transforms['Arrow'+str(j)]);children(n,7,[q])
                for cat,idx in src_shapes.items():
                    if cat!='aura':attach_mesh(n,src,idx,'MAQuiver_'+key+f'_{j}_'+cat,q,shaders[cat],alpha)
        else:
            stats.append(add_particles(n,full,spec,(0,53,0),True,index=1))
        out=MESH/(key+('_flight' if flight else '')+'.nif');n.save(out)
        check=NifFile(str(out))
        assert len(check.shapes)==(2 if flight else 12)
        assert all(len(s.verts)>0 and len(s.tris)>0 for s in check.shapes)
        reread=NifBlocks(out);assert reread.blocks==n.blocks
        report.append(dict(key=key,flight=flight,path=str(out),shapes=len(check.shapes),vertices=sum(len(s.verts) for s in check.shapes),triangles=sum(len(s.tris) for s in check.shapes),particles=stats))
    impact=MESH/(key+'_impact.nif')
    nf=NifFile();nf.initialize('SKYRIMSE',str(impact),root_type='BSFadeNode',root_name='MAImpact');nf.save()
    n=NifBlocks(impact)
    flag=n.append('BSXFlags',p('II',n.string('BSX'),1))
    kind,b=n.blocks[0];assert u(b,4)==0
    n.blocks[0]=(kind,b[:4]+p('II',1,flag)+b[8:])
    add_particles(n,0,spec,(0,0,0),index=0,burst=True)
    n.save(impact)
    assert NifBlocks(impact).blocks==n.blocks
(BUILD/'models.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
