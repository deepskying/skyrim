"""B7 ocean crystal plus approved red/G7/P8 materials on all 12 greatswords."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths
from build_greatsword_minerals import body, CONV, MESH, TEX

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/before-0.51.6/data'
STAGE=ROOT/'build/final-greatsword-materials/data'
ART=ROOT/'art/final-greatsword-materials'
CATALOG=[s for s in json.loads((ROOT/'source/catalog.json').read_text('utf-8')) if s.get('weapon_type')=='greatsword']
assert len(CATALOG)==12
BLUE='aa_layered_ocean'
LABELS={'red':'黑曜石','green':'G7 青碧层晶','blue':'B7 海蓝层晶','purple':'P8 紫斑铜矿'}

def snapshot():
    manifest=BASE.parent/'manifest.json'
    if manifest.exists():
        for rel,h in json.loads(manifest.read_text()).items():assert hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==h
        return
    assert not BASE.exists()
    hashes={}
    for p in runtime_paths():
        rel=p.relative_to(ROOT/'data');dest=BASE/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        hashes[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes,indent=2))

def blue_textures():
    from PIL import Image
    n=1024;y,x=np.mgrid[:n,:n].astype(np.float32)/n
    # Irregular mineral facets crossed by broad bright strata, no repeating scales.
    cloud=(np.sin(2*np.pi*(3*x+2*y))+.5*np.sin(2*np.pi*(7*x-5*y)))/1.5
    px=x*11+.2*cloud;py=y*19+.2*cloud;ix=np.floor(px).astype(int);iy=np.floor(py).astype(int)
    rng=np.random.default_rng(516);seeds=rng.uniform(.15,.85,(19,11,2));tones=rng.uniform(.1,.9,(19,11))
    nearest=np.full_like(x,1e9);second=nearest.copy();tone=np.zeros_like(x);slope=np.zeros_like(x)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            sx=ix+dx;sy=iy+dy;j=seeds[sy%19,sx%11];vx=px-sx-j[:,:,0];vy=py-sy-j[:,:,1];d=vx*vx+vy*vy;m=d<nearest
            second=np.where(m,nearest,np.minimum(second,d));nearest=np.minimum(nearest,d)
            tone=np.where(m,tones[sy%19,sx%11],tone);slope=np.where(m,vx*.16+vy*.10,slope)
    edge=np.exp(-((np.sqrt(second)-np.sqrt(nearest))/.035)**2)
    phase=(2*x+4*y+.13*np.abs(np.sin(2*np.pi*(2*x-y)))+.04*cloud)%1
    strata=(np.tanh((phase-.16)*30)-np.tanh((phase-.48)*30))*.5
    level=np.clip(.10+.44*strata+.28*tone+slope+.13*edge,0,1)
    palette=np.array([[0,119,182],[0,180,216],[202,240,248]])/255
    a=np.clip(level/.55,0,1)[:,:,None];b=np.clip((level-.55)/.45,0,1)[:,:,None]
    diffuse=palette[0]*(1-a)+palette[1]*a;diffuse=diffuse*(1-b)+palette[2]*b
    glow=diffuse*(.48+.36*level[:,:,None])
    h=.008*slope+.003*strata+.001*edge
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*4;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*4
    normal=np.stack([-dx,dy,np.ones_like(x)],-1);normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
    for suffix,rgb,alpha in [('d',diffuse,np.ones_like(x)),('g',glow,np.ones_like(x)),('n',normal,.4+.35*tone)]:
        p=ART/(BLUE+'_'+suffix+'.png');rgba=np.concatenate([rgb,alpha[:,:,None]],-1)
        Image.fromarray(np.round(np.clip(rgba,0,1)*255).astype(np.uint8)).save(p)
        subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(STAGE/TEX),str(p)],check=True,capture_output=True)

def material(color):
    ref=NifBlocks(BASE/MESH/('greatsword3'+color+'.nif'));si,ti=body(ref)
    sh=ref.blocks[si][1];texture=ref.blocks[ti]
    if color=='blue':
        paths=['textures\\weapons\\arcanearsenal\\'+BLUE+'_'+s+'.dds' for s in ('d','n','g')]+['']*6
        texture=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths))
    return sh,texture

def verify(data):
    from PIL import Image
    reports=[]
    for spec in CATALOG:
        key=spec['key'];color=next(c for c in LABELS if key.endswith(c));rel=MESH/(key+'.nif')
        old=NifBlocks(BASE/rel);new=NifBlocks(data/rel);si,ti=body(old);ref,tex=material(color)
        assert old.strings==new.strings and len(old.blocks)==len(new.blocks)
        assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,new.blocks)) if i not in (si,ti))
        expected=bytearray(ref[:4]+old.blocks[si][1][4:16]+ref[16:]);struct.pack_into('<I',expected,40,ti)
        assert new.blocks[si][1]==bytes(expected) and new.blocks[ti]==tex
        blob=tex[1];pos=4
        for _ in range(9):
            count=struct.unpack_from('<I',blob,pos)[0];pos+=4;p=blob[pos:pos+count].decode().replace('\\','/');pos+=count
            if p:assert (data/p).is_file() or (ROOT/'data'/p).is_file(),p
        reports.append(dict(key=key,material=LABELS[color],geometry_uv_collision_edges_particles_preserved=True))
    for suffix in ('d','n','g'):
        p=data/TEX/(BLUE+'_'+suffix+'.dds');raw=p.read_bytes();assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and struct.unpack_from('<I',raw,28)[0]==11
        im=Image.open(p);assert im.size==(1024,1024)
        if suffix!='n':assert im.convert('RGBA').getchannel('A').getextrema()==(255,255)
    if data==ROOT/'data':
        oldfiles={p.relative_to(BASE) for p in BASE.rglob('*') if p.is_file()}
        changed={p for p in oldfiles if (BASE/p).read_bytes()!=(data/p).read_bytes()}
        expected={MESH/(s['key']+'.nif') for s in CATALOG if s['key'] not in ('greatsword3red','greatsword3green','greatsword3purple')}
        assert changed==expected,changed
        assert {p.relative_to(data) for p in runtime_paths()}-oldfiles=={TEX/(BLUE+'_'+s+'.dds') for s in ('d','n','g')}
    report=dict(version='0.51.6',greatswords=reports,other_runtime_unchanged=True,gameplay_tested=False)
    (ROOT/'build/final-greatsword-materials-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(version='0.51.6',greatswords=len(reports),passed=True)))

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.verify:verify(ROOT/'data');return
    snapshot()
    for path in (ART,STAGE/MESH,STAGE/TEX):path.mkdir(parents=True,exist_ok=True)
    blue_textures()
    for s in CATALOG:
        key=s['key'];color=next(c for c in LABELS if key.endswith(c));rel=MESH/(key+'.nif');n=NifBlocks(BASE/rel);si,ti=body(n);ref,tex=material(color)
        sh=bytearray(ref[:4]+n.blocks[si][1][4:16]+ref[16:]);struct.pack_into('<I',sh,40,ti)
        n.blocks[si]=('BSLightingShaderProperty',bytes(sh));n.blocks[ti]=tex;n.save(STAGE/rel)
    verify(STAGE)
    if a.apply:
        for p in STAGE.rglob('*'):
            if p.is_file():shutil.copy2(p,ROOT/'data'/p.relative_to(STAGE))
        verify(ROOT/'data')

if __name__=='__main__':main()
