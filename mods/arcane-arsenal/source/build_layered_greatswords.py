"""B9 blue nacre / G7 teal layered crystal, colored glow and unchanged geometry."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import body, CONV, MESH, TEX

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.51.5/data'
STAGE=ROOT/'build/layered-greatswords/data'
ART=ROOT/'art/layered-greatswords'
SPECS={'blue':dict(material='B9 蓝辉贝晶',texture='aa_layered_nacre',power=1.6,gloss=85.,spec=.6),
       'green':dict(material='G7 青碧层晶',texture='aa_layered_teal',power=1.6,gloss=65.,spec=.45)}
EMIT={c:(1.,1.,1.) for c in SPECS}
PALETTES={'blue':['0077b6','00b4d8','caf0f8'],'green':['38a3a5','80ed99','c7f9cc']}

def snapshot():
    manifest=BASE.parent/'manifest.json'
    if manifest.exists():
        for rel,h in json.loads(manifest.read_text()).items():assert hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==h
        return
    assert not BASE.exists()
    hashes={}
    for p in runtime_paths():
        rel=p.relative_to(ROOT/'data');dst=BASE/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
        hashes[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes,indent=2))

def textures():
    from PIL import Image
    n=1024;y,x=np.mgrid[:n,:n].astype(np.float32)/n
    def noise(scale,seed):
        rng=np.random.default_rng(seed);out=np.zeros_like(x)
        for _ in range(20):
            a,b=rng.integers(-scale,scale+1,2);out+=np.sin(2*np.pi*(a*x+b*y)+rng.uniform(0,2*np.pi))
        return out/10
    fine=noise(80,515);cloud=noise(7,516)
    # Staggered overlapping pointed nacre plates. World UV units are x/30,y/100.
    py=y*23+.12*np.sin(2*np.pi*x*4);row=np.floor(py)
    u=((x*12+(row%2)*.5+.22*np.sin(row*2.1)+.10*cloud)%1)*2-1;v=py%1
    curve=np.clip(1-v-.48*u*u,0,1)
    seam=np.exp(-((v+.48*u*u-.92)/.05)**2)
    crest=np.exp(-(u/.17)**2)*(1-v)*.35
    fibers=np.sin(2*np.pi*(x*185+v*.8)+u*4)*.5+.5
    plate=np.clip(.16+.66*curve+crest+.045*fine+.065*cloud+.04*fibers,0,1)
    # Broad oblique green strata have crisp crystal facets and bright mint bands.
    phase=(3*x+5*y+.16*np.abs(np.sin(2*np.pi*(2*x-y)))+.045*cloud)%1
    bands=(np.tanh((phase-.2)*35)-np.tanh((phase-.47)*35))*.5
    ridge=np.exp(-((phase-.48)/.035)**2)
    # Small irregular crystal facets support the large color strata.
    px=x*15+.2*cloud;py=y*27+.2*cloud;ix=np.floor(px);iy=np.floor(py)
    facet=(np.sin(ix*127.1+iy*311.7)*43758.5453)%1
    cell_edge=np.minimum(np.minimum(px%1,1-px%1),np.minimum(py%1,1-py%1))
    fine_rim=np.exp(-(cell_edge/.023)**2)*.05
    green=np.clip(.03+.68*bands+.19*ridge+.13*facet+.03*cloud+fine_rim,0,1)
    patterns={'blue':(plate,seam,curve*.025+crest*.009+fibers*.0006,.42+.38*curve),
              'green':(green,ridge,bands*.005+facet*.0015+fine*.0002,.45+.22*bands)}
    for c,(t,detail,height,specmask) in patterns.items():
        palette=np.array([[int(h[i:i+2],16)/255 for i in (0,2,4)] for h in PALETTES[c]])
        # Piecewise ramp retains saturated midtones and reserves pale color for peaks.
        a=np.clip(t/.58,0,1)[:,:,None];b=np.clip((t-.58)/.42,0,1)[:,:,None]
        rgb=palette[0]*(1-a)+palette[1]*a;rgb=rgb*(1-b)+palette[2]*b
        if c=='blue':rgb*=1-.16*detail[:,:,None]
        glow=rgb*(.48+.36*t[:,:,None])
        dx=(np.roll(height,-1,1)-np.roll(height,1,1))*4;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*4
        normal=np.stack([-dx,dy,np.ones_like(x)],-1);normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
        for suffix,pixels,alpha in [('d',rgb,np.ones_like(x)),('g',glow,np.ones_like(x)),('n',normal,specmask)]:
            p=ART/(SPECS[c]['texture']+'_'+suffix+'.png')
            rgba=np.concatenate([pixels,alpha[:,:,None]],-1)
            Image.fromarray(np.round(np.clip(rgba,0,1)*255).astype(np.uint8)).save(p)
            subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(STAGE/TEX),str(p)],check=True,capture_output=True)

def verify(data):
    from PIL import Image
    reports=[]
    for c,s in SPECS.items():
        rel=MESH/('greatsword3'+c+'.nif');old=NifBlocks(BASE/rel);new=NifBlocks(data/rel);si,ti=body(old)
        assert new.strings==old.strings and len(new.blocks)==len(old.blocks)
        assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,new.blocks)) if i not in (si,ti))
        sh=new.blocks[si][1];assert len(sh)==100 and struct.unpack_from('<I',sh)[0]==2
        assert struct.unpack_from('<f',sh,64)[0]==1 and np.allclose(struct.unpack_from('<4f',sh,44),(1,1,1,s['power']))
        blob=new.blocks[ti][1];pos=4;paths=[]
        for _ in range(9):
            count=struct.unpack_from('<I',blob,pos)[0];pos+=4;paths.append(blob[pos:pos+count].decode().replace('\\','/'));pos+=count
        expected=[(TEX/(s['texture']+'_'+suffix+'.dds')).as_posix() for suffix in ('d','n','g')]+['']*6
        assert paths==expected
        for suffix in ('d','n','g'):
            p=data/TEX/(s['texture']+'_'+suffix+'.dds');raw=p.read_bytes()
            assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and struct.unpack_from('<I',raw,28)[0]==11
            im=Image.open(p);assert im.size==(1024,1024)
            if suffix!='n':assert im.convert('RGBA').getchannel('A').getextrema()==(255,255)
            if suffix=='g':
                rgb=np.array(im.convert('RGB'))/255
                assert rgb.max(axis=-1).min()>.18 and np.std(rgb)>.1
        reports.append(dict(color=c,material=s['material'],palette=PALETTES[c],body_emission=s['power'],geometry_uv_collision_edges_particles_preserved=True))
    if data==ROOT/'data':
        oldfiles={p.relative_to(BASE) for p in BASE.rglob('*') if p.is_file()}
        assert {p for p in oldfiles if (BASE/p).read_bytes()!=(data/p).read_bytes()}=={MESH/('greatsword3'+c+'.nif') for c in SPECS}
        assert {p.relative_to(data) for p in runtime_paths()}-oldfiles=={TEX/(s['texture']+'_'+suffix+'.dds') for s in SPECS.values() for suffix in ('d','n','g')}
    report=dict(version='0.51.5',weapons=reports,other_runtime_unchanged=True,gameplay_tested=False)
    (ROOT/'build/layered-greatswords-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if args.verify:verify(ROOT/'data');return
    snapshot()
    for path in (ART,STAGE/TEX,STAGE/MESH):path.mkdir(parents=True,exist_ok=True)
    textures()
    for c,s in SPECS.items():
        rel=MESH/('greatsword3'+c+'.nif');n=NifBlocks(BASE/rel);si,ti=body(n)
        # Copy the known-good original Glow Shader envelope; keep current links.
        reference=NifBlocks(ROOT/'build/before-0.51.2/data'/rel);ri,_=body(reference)
        sh=bytearray(reference.blocks[ri][1]);assert len(sh)==100 and struct.unpack_from('<I',sh)[0]==2
        struct.pack_into('<I',sh,40,ti);struct.pack_into('<4f',sh,44,1,1,1,s['power'])
        struct.pack_into('<7f',sh,64,1,0,s['gloss'],1,1,1,s['spec'])
        n.blocks[si]=('BSLightingShaderProperty',bytes(sh))
        paths=['textures\\weapons\\arcanearsenal\\'+s['texture']+'_'+suffix+'.dds' for suffix in ('d','n','g')]+['']*6
        n.blocks[ti]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths));n.save(STAGE/rel)
    verify(STAGE)
    if args.apply:
        for p in STAGE.rglob('*'):
            if p.is_file():shutil.copy2(p,ROOT/'data'/p.relative_to(STAGE))
        verify(ROOT/'data')

if __name__=='__main__':main()
