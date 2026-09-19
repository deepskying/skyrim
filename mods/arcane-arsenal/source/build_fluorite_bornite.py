"""G5 deep teal fluorite and P8 purple bornite on the approved greatswords.

Only body shader/texture blocks change. Build in staging; --apply installs to
the source data tree after checks. Baseline is immutable for repeatable audits.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import body, CONV, MESH, TEX

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.51.4/data'
STAGE=ROOT/'build/fluorite-bornite/data'
ART=ROOT/'art/fluorite-bornite'
SPECS={
    'green':dict(material='深青绿萤石',texture='aa_mineral_fluorite',gloss=110.,spec=.85,env=.32,power=.08),
    'purple':dict(material='紫斑铜矿',texture='aa_mineral_bornite',gloss=75.,spec=1.15,env=.55,power=.045),
}
EMIT={'green':(.015,.25,.22),'purple':(.20,.025,.24)}

def snapshot():
    manifest=BASE.parent/'manifest.json'
    if manifest.exists():
        for p,h in json.loads(manifest.read_text()).items():
            assert hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h
        return
    assert not BASE.exists()
    hashes={}
    for p in runtime_paths():
        rel=p.relative_to(ROOT/'data');out=BASE/rel;out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,out);hashes[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes,indent=2))

def textures():
    from PIL import Image
    n=1024;y,x=np.mgrid[:n,:n].astype(np.float32)/n
    def noise(scale,seed):
        rng=np.random.default_rng(seed);out=np.zeros_like(x)
        for _ in range(24):
            a,b=rng.integers(-scale,scale+1,2)
            out+=np.sin(2*np.pi*(a*x+b*y)+rng.uniform(0,2*np.pi))
        return out/12
    cloud=noise(5,41);fine=noise(95,42)
    # Periodic angular bands: crystalline layers, not jade clouds or cracks.
    layer=(3*x+5*y+.20*np.abs(np.sin(2*np.pi*(2*x-y)))+.05*cloud)%1
    band=(np.tanh((layer-.18)*30)-np.tanh((layer-.46)*30))*.5
    thin=np.exp(-((layer-.63)/.018)**2)
    fluorite=np.array([.015,.105,.105])+(np.array([.10,.36,.30])-np.array([.015,.105,.105]))*band[:,:,None]
    fluorite+=thin[:,:,None]*np.array([.06,.12,.105])
    fluorite*=1+.16*cloud[:,:,None]+.035*fine[:,:,None]
    # Periodic Voronoi grains with independently varied slope and mineral tint.
    rng=np.random.default_rng(514);px=x*35;py=y*55;ix=px.astype(int);iy=py.astype(int)
    seeds=rng.uniform(.1,.9,(55,35,2));tone=rng.uniform(0,1,(55,35));slopes=rng.uniform(-1,1,(55,35,2))
    nearest=np.full_like(x,1e9);second=nearest.copy();cell=np.zeros_like(x);height=np.zeros_like(x)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            sx=ix+dx;sy=iy+dy;j=seeds[sy%55,sx%35]
            vx=px-sx-j[:,:,0];vy=py-sy-j[:,:,1];d=vx*vx+vy*vy;m=d<nearest
            second=np.where(m,nearest,np.minimum(second,d));nearest=np.minimum(nearest,d)
            cell=np.where(m,tone[sy%55,sx%35],cell)
            slope=slopes[sy%55,sx%35];height=np.where(m,(vx*slope[:,:,0]+vy*slope[:,:,1])*.007,height)
    patch=noise(9,43);blue=np.clip((patch-.25)*1.5,0,.7);rose=np.clip((-patch-.1)*1.5,0,.75)
    bornite=np.ones((n,n,3))*np.array([.16,.035,.22])
    bornite=bornite*(1-blue[:,:,None])+np.array([.035,.10,.30])*blue[:,:,None]
    bornite=bornite*(1-rose[:,:,None])+np.array([.38,.085,.24])*rose[:,:,None]
    bornite*=.6+.8*cell[:,:,None]+.10*fine[:,:,None]
    boundary=np.clip((second-nearest)*12,0,1)
    bornite*=.75+.25*boundary[:,:,None]
    arrays={'green':(fluorite,band*.001+fine*.0001,np.full_like(x,.65),np.full_like(x,.43)),
            'purple':(bornite,height+fine*.001,np.clip(.45+.45*cell+.08*fine,.2,.95),.24+.52*cell)}
    for color,(diffuse,h,specmask,reflection) in arrays.items():
        dx=(np.roll(h,-1,1)-np.roll(h,1,1))*6;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*6
        normal=np.stack([-dx,dy,np.ones_like(x)],-1);normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
        for suffix,rgb,alpha in [('d',diffuse,np.ones_like(x)),('n',normal,specmask),('m',np.repeat(reflection[:,:,None],3,axis=2),np.ones_like(x))]:
            rgba=np.concatenate([rgb,alpha[:,:,None]],-1)
            p=ART/(SPECS[color]['texture']+'_'+suffix+'.png')
            Image.fromarray(np.round(np.clip(rgba,0,1)*255).astype(np.uint8)).save(p)
            subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(STAGE/TEX),str(p)],capture_output=True,check=True)

def verify(data):
    from PIL import Image
    reports=[]
    for color,s in SPECS.items():
        rel=MESH/('greatsword3'+color+'.nif');old=NifBlocks(BASE/rel);new=NifBlocks(data/rel);si,ti=body(old)
        assert old.strings==new.strings and len(old.blocks)==len(new.blocks)
        assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,new.blocks)) if i not in (si,ti))
        sh=new.blocks[si][1];assert len(sh)==104 and struct.unpack_from('<I',sh)[0]==1
        assert struct.unpack_from('<f',sh,64)[0]==1
        assert np.allclose(struct.unpack_from('<4f',sh,44),(*EMIT[color],s['power']))
        blob=new.blocks[ti][1];pos=4
        for _ in range(9):
            length=struct.unpack_from('<I',blob,pos)[0];pos+=4
            path=blob[pos:pos+length].decode().replace('\\','/');pos+=length
            if path:assert (data/path).is_file() or (ROOT/'data'/path).is_file(),path
        for suffix in ('d','n','m'):
            p=data/TEX/(s['texture']+'_'+suffix+'.dds');raw=p.read_bytes()
            assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and struct.unpack_from('<I',raw,28)[0]==11
            im=Image.open(p);assert im.size==(1024,1024)
            if suffix=='d':assert im.convert('RGBA').getchannel('A').getextrema()==(255,255)
        reports.append(dict(color=color,material=s['material'],changed_blocks=[si,ti],geometry_uv_collision_edges_particles_preserved=True))
    if data==ROOT/'data':
        oldfiles={p.relative_to(BASE) for p in BASE.rglob('*') if p.is_file()}
        changed={p for p in oldfiles if (BASE/p).read_bytes()!=(data/p).read_bytes()}
        assert changed=={MESH/('greatsword3'+c+'.nif') for c in SPECS},changed
        added={p.relative_to(data) for p in runtime_paths()}-oldfiles
        assert added=={TEX/(s['texture']+'_'+z+'.dds') for s in SPECS.values() for z in ('d','n','m')}
    report=dict(version='0.51.4',weapons=reports,other_runtime_unchanged=True,gameplay_tested=False)
    (ROOT/'build/fluorite-bornite-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.verify:verify(ROOT/'data');return
    snapshot()
    for path in (ART,STAGE/TEX,STAGE/MESH):path.mkdir(parents=True,exist_ok=True)
    textures()
    for color,s in SPECS.items():
        rel=MESH/('greatsword3'+color+'.nif');n=NifBlocks(BASE/rel);si,ti=body(n);sh=bytearray(n.blocks[si][1]);assert len(sh)==104
        struct.pack_into('<4f',sh,44,*EMIT[color],s['power'])
        struct.pack_into('<7f',sh,64,1,0,s['gloss'],1,1,1,s['spec']);struct.pack_into('<f',sh,100,s['env'])
        n.blocks[si]=('BSLightingShaderProperty',bytes(sh))
        prefix='textures\\weapons\\arcanearsenal\\'
        paths=[prefix+s['texture']+'_d.dds',prefix+s['texture']+'_n.dds','','',prefix+'aa_trial_env.dds',prefix+s['texture']+'_m.dds','','','']
        n.blocks[ti]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(v))+v.encode() for v in paths));n.save(STAGE/rel)
    verify(STAGE)
    if a.apply:
        for path in STAGE.rglob('*'):
            if path.is_file():shutil.copy2(path,ROOT/'data'/path.relative_to(STAGE))
        verify(ROOT/'data')

if __name__=='__main__':main()
