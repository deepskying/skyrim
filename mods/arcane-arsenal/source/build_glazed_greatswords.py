"""R2/P11 flowing colored glaze for all six red/purple greatswords."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import body, CONV, MESH, TEX
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.51.7/data'
STAGE=ROOT/'build/glazed-greatswords/data'
ART=ROOT/'art/glazed-greatswords'
SPECS={'red':dict(material='R2 赤霞流釉',texture='aa_glaze_coral',power=1.6),
       'purple':dict(material='P11 绯紫流釉',texture='aa_glaze_violet',power=1.6)}
EMIT={c:(1,1,1) for c in SPECS}
PALETTES={'red':['f20089','ff4d6d','f9627d'],'purple':['7b2cbf','f20089','e0aaff']}
CATALOG=[s for s in json.loads((ROOT/'source/catalog.json').read_text('utf-8')) if s.get('weapon_type')=='greatsword' and any(s['key'].endswith(c) for c in SPECS)]
assert len(CATALOG)==6

def snapshot():
    manifest=BASE.parent/'manifest.json'
    if manifest.exists():
        for p,h in json.loads(manifest.read_text()).items():assert hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h
        return
    assert not BASE.exists();hashes={}
    for p in runtime_paths():
        rel=p.relative_to(ROOT/'data');out=BASE/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
        hashes[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes,indent=2))

def textures():
    from PIL import Image
    n=1024;y,x=np.mgrid[:n,:n].astype(np.float32)/n
    # Smooth periodic domain warping gives long mineral rivers, no cellular cracks.
    warp=.11*np.sin(2*np.pi*(2*x+y))+.055*np.sin(2*np.pi*(x-3*y))
    warp+=.024*np.sin(2*np.pi*(5*x+2*y)+2*np.sin(2*np.pi*y))
    phase=2*np.pi*(5*x+2*y+warp*7)
    wide=(.5+.5*np.sin(phase))
    filaments=(.5+.5*np.sin(phase*9+.6*np.sin(2*np.pi*(7*x-3*y))))**12
    fine=(.5+.5*np.sin(phase*23))**24
    for c,s in SPECS.items():
        palette=np.array([[int(h[i:i+2],16)/255 for i in (0,2,4)] for h in PALETTES[c]])
        if c=='red':
            mid=np.clip(.24+.76*wide,0,1);highlight=np.clip(.26*filaments+.42*wide**5,0,.72)
        else:
            mid=np.clip((wide-.38)*1.7,0,1);highlight=np.clip(.5*filaments+.12*fine,0,.62)
        rgb=palette[0]*(1-mid[:,:,None])+palette[1]*mid[:,:,None]
        rgb=rgb*(1-highlight[:,:,None])+palette[2]*highlight[:,:,None]
        glow=rgb*(.48+.30*wide[:,:,None]+.10*filaments[:,:,None])
        height=.0015*wide+.0006*filaments
        dx=(np.roll(height,-1,1)-np.roll(height,1,1))*4;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*4
        normal=np.stack([-dx,dy,np.ones_like(x)],-1);normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
        for suffix,pixels,alpha in [('d',rgb,np.ones_like(x)),('g',glow,np.ones_like(x)),('n',normal,.55+.20*wide)]:
            p=ART/(s['texture']+'_'+suffix+'.png');rgba=np.concatenate([pixels,alpha[:,:,None]],-1)
            Image.fromarray(np.round(np.clip(rgba,0,1)*255).astype(np.uint8)).save(p)
            subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(STAGE/TEX),str(p)],check=True,capture_output=True)

def verify(data):
    from PIL import Image
    reports=[]
    for s in CATALOG:
        key=s['key'];c=next(c for c in SPECS if key.endswith(c));rel=MESH/(key+'.nif')
        old=NifBlocks(BASE/rel);new=NifBlocks(data/rel);si,ti=body(old)
        assert old.strings==new.strings and len(old.blocks)==len(new.blocks)
        assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,new.blocks)) if i not in (si,ti))
        sh=new.blocks[si][1];assert len(sh)==100 and struct.unpack_from('<I',sh)[0]==2
        assert np.allclose(struct.unpack_from('<4f',sh,44),(1,1,1,1.6)) and struct.unpack_from('<f',sh,64)[0]==1
        paths=[str(TEX/(SPECS[c]['texture']+'_'+suffix+'.dds')).replace('/','\\') for suffix in ('d','n','g')]+['']*6
        expected=struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths)
        assert new.blocks[ti][1]==expected
        reports.append(dict(key=key,material=SPECS[c]['material'],geometry_uv_collision_edges_particles_preserved=True))
    for c,s in SPECS.items():
        for suffix in ('d','n','g'):
            p=data/TEX/(s['texture']+'_'+suffix+'.dds');raw=p.read_bytes()
            assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and struct.unpack_from('<I',raw,28)[0]==11
            im=Image.open(p);assert im.size==(1024,1024)
            if suffix!='n':assert im.convert('RGBA').getchannel('A').getextrema()==(255,255)
            if suffix=='g':assert np.asarray(im.convert('RGB')).max(axis=-1).min()>40
    if data==ROOT/'data':
        oldfiles={p.relative_to(BASE) for p in BASE.rglob('*') if p.is_file()}
        assert {p for p in oldfiles if (BASE/p).read_bytes()!=(data/p).read_bytes()}=={MESH/(s['key']+'.nif') for s in CATALOG}
        assert {p.relative_to(data) for p in runtime_paths()}-oldfiles=={TEX/(s['texture']+'_'+suffix+'.dds') for s in SPECS.values() for suffix in ('d','n','g')}
    report=dict(version='0.51.7',greatswords=reports,palettes=PALETTES,other_runtime_unchanged=True,gameplay_tested=False)
    (ROOT/'build/glazed-greatswords-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(version='0.51.7',greatswords=6,passed=True)))

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--verify',action='store_true');args=p.parse_args()
    if args.verify:verify(ROOT/'data');return
    snapshot()
    for path in (ART,STAGE/MESH,STAGE/TEX):path.mkdir(parents=True,exist_ok=True)
    textures()
    for s in CATALOG:
        key=s['key'];c=next(c for c in SPECS if key.endswith(c));rel=MESH/(key+'.nif');n=NifBlocks(BASE/rel);si,ti=body(n)
        ref=NifBlocks(BASE/MESH/'greatsword3green.nif');ri,_=body(ref);template=ref.blocks[ri][1]
        sh=bytearray(template[:4]+n.blocks[si][1][4:16]+template[16:]);struct.pack_into('<I',sh,40,ti)
        struct.pack_into('<4f',sh,44,1,1,1,SPECS[c]['power']);struct.pack_into('<7f',sh,64,1,0,95,1,1,1,.6)
        n.blocks[si]=('BSLightingShaderProperty',bytes(sh))
        paths=['textures\\weapons\\arcanearsenal\\'+SPECS[c]['texture']+'_'+suffix+'.dds' for suffix in ('d','n','g')]+['']*6
        n.blocks[ti]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths));n.save(STAGE/rel)
    verify(STAGE)
    if args.apply:
        for p in STAGE.rglob('*'):
            if p.is_file():
                dest=ROOT/'data'/p.relative_to(STAGE)
                if dest.exists() and dest.read_bytes()==p.read_bytes():continue
                temp=dest.with_name(dest.name+'.glaze-tmp')
                temp.write_bytes(p.read_bytes());temp.replace(dest)
        verify(ROOT/'data')

if __name__=='__main__':main()
