"""Approved mineral materials for the third greatsword set; preserve all other blocks.

Build into staging first. --apply copies verified output to data, --verify checks
the installed source tree against the immutable pre-change runtime snapshot.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess, sys
import numpy as np
from nif_blocks import NifBlocks
from release_assets import runtime_paths

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'build/before-0.51.2/data'
STAGE = ROOT/'build/greatsword-minerals/data'
ART = ROOT/'art/greatsword-minerals'
MESH = Path('meshes/weapons/arcanearsenal')
TEX = Path('textures/weapons/arcanearsenal')
CONV = Path('C:/Users/linos/Desktop/games/+skyrim/TOOLS/+tools-VRAMr/VRAMr/tools/texconv.exe')
SPECS = {
    'red': dict(material='黑曜石', texture='waraxeobsidian', gloss=135., spec=1.1, env=.65, power=0.),
    'green': dict(material='翠玉', texture='aa_mineral_jade', gloss=100., spec=.85, env=.32, power=.10),
    'blue': dict(material='青金石', texture='aa_mineral_lapis', gloss=65., spec=.65, env=.20, power=.08),
    'purple': dict(material='紫龙晶', texture='aa_mineral_charoite', gloss=90., spec=.8, env=.28, power=.10),
}
EMIT = {'red':(0.,0.,0.), 'green':(.03,.32,.12), 'blue':(.02,.14,.35), 'purple':(.18,.04,.30)}

def body(n):
    shape = next(b for k,b in n.blocks if k=='BSTriShape' and n.strings[struct.unpack_from('<I',b)[0]]==b'AA_GreatswordBody')
    si = struct.unpack_from('<I',shape,92)[0]
    return si, struct.unpack_from('<I',n.blocks[si][1],40)[0]

def snapshot():
    manifest = BASE.parent/'manifest.json'
    if manifest.exists():
        for rel,digest in json.loads(manifest.read_text()).items():
            assert hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==digest
        return
    assert not BASE.exists(), 'Incomplete snapshot; inspect before retrying'
    files = runtime_paths()
    for p in files:
        dest = BASE/p.relative_to(ROOT/'data'); dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest)
    manifest.write_text(json.dumps({p.relative_to(ROOT/'data').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))

def textures():
    from PIL import Image
    n=1024; y,x=np.mgrid[:n,:n].astype(np.float32)/n
    rng=np.random.default_rng(20260918)
    def noise(scale, seed):
        r=np.random.default_rng(seed); result=np.zeros_like(x)
        for _ in range(16):
            a,b=r.integers(-scale,scale+1,2)
            result += np.sin(2*np.pi*(a*x+b*y)+r.uniform(0,2*np.pi))
        return result/8
    cloud=noise(5,18); fine=noise(44,19); grain=rng.normal(0,1,x.shape)
    warp=x+.075*noise(3,20)+.025*noise(8,21)
    veins=np.exp(-(np.sin(2*np.pi*(3*warp+2*y+.07*noise(5,24)))/.065)**2)
    gold=(noise(90,25)>.8)*(noise(11,26)>.05)
    phase=2*np.pi*(12*x+4*y+1.8*noise(3,27)+.45*noise(7,28))
    bands=(.5+.5*np.sin(phase))**3
    fibers=.5+.5*np.sin(phase*7+.25*fine)
    jade=np.clip(.46+.65*cloud+.10*fine,0,1)
    jade_rgb=np.array([.035,.19,.105])+(np.array([.30,.65,.39])-np.array([.035,.19,.105]))*jade[:,:,None]
    lapis=np.clip(np.array([.035,.17,.39])*(1+.26*cloud[:,:,None]+.13*fine[:,:,None]),0,1)
    lapis=lapis*(1-veins[:,:,None]*.65)+np.array([.55,.60,.65])*veins[:,:,None]*.65
    lapis=np.where(gold[:,:,None],np.array([.72,.48,.12]),lapis)
    purple=np.array([.17,.055,.28])+(np.array([.58,.36,.65])-np.array([.17,.055,.28]))*bands[:,:,None]
    purple*=1+.12*(fibers[:,:,None]-.5)+.05*fine[:,:,None]
    arrays={'green':(jade_rgb,cloud*.002+fine*.0002,.65),
            'blue':(lapis,fine*.001+gold*.003,.5),
            'purple':(purple,bands*.0015+fibers*.0003,.6)}
    for color,(diffuse,height,alpha) in arrays.items():
        dx=(np.roll(height,-1,1)-np.roll(height,1,1))*8
        dy=(np.roll(height,-1,0)-np.roll(height,1,0))*8
        normal=np.stack([-dx,dy,np.ones_like(x)],-1)
        normal=normal/np.linalg.norm(normal,axis=-1,keepdims=True)*.5+.5
        mask=np.full((n,n,3),.48 if color!='blue' else .3)
        for suffix,rgb,a in [('d',diffuse,1.),('n',normal,alpha),('m',mask,1.)]:
            pixels=np.concatenate([rgb,np.full((n,n,1),a)],-1)
            p=ART/(SPECS[color]['texture']+'_'+suffix+'.png')
            Image.fromarray(np.round(np.clip(pixels,0,1)*255).astype(np.uint8)).save(p)
            subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(STAGE/TEX),str(p)],check=True,capture_output=True)

def verify(data):
    from PIL import Image
    reports=[]
    for color,s in SPECS.items():
        key='greatsword3'+color
        old=NifBlocks(BASE/MESH/(key+'.nif')); new=NifBlocks(data/MESH/(key+'.nif'))
        si,ti=body(old)
        assert old.strings==new.strings and len(old.blocks)==len(new.blocks)
        assert all(a==b for i,(a,b) in enumerate(zip(old.blocks,new.blocks)) if i not in (si,ti))
        sh=new.blocks[si][1]
        assert len(sh)==104 and struct.unpack_from('<I',sh)[0]==1
        assert struct.unpack_from('<f',sh,64)[0]==1., 'Opaque body required'
        assert abs(struct.unpack_from('<f',sh,56)[0]-s['power'])<1e-6
        blob=new.blocks[ti][1]; pos=4
        for _ in range(struct.unpack_from('<I',blob)[0]):
            size=struct.unpack_from('<I',blob,pos)[0];pos+=4
            path=blob[pos:pos+size].decode().replace('\\','/');pos+=size
            if path: assert (data/path).exists() or (ROOT/'data'/path).exists(),path
        reports.append(dict(key=key,material=s['material'],changed_blocks=[si,ti],geometry_uv_collision_edge_particles_unchanged=True))
    for p in (data/TEX).glob('aa_mineral_*.dds'):
        raw=p.read_bytes(); assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5'
        assert struct.unpack_from('<III',raw,12)[:2]==(1024,1024)
        assert struct.unpack_from('<I',raw,28)[0]==11
        image=Image.open(p);assert image.size==(1024,1024)
        if p.stem.endswith('_d'): assert image.convert('RGBA').getchannel('A').getextrema()==(255,255)
    if data==ROOT/'data':
        changed={str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file() and p.read_bytes()!=(data/p.relative_to(BASE)).read_bytes()}
        assert changed=={str(MESH/('greatsword3'+c+'.nif')) for c in SPECS},changed
        oldfiles={p.relative_to(BASE) for p in BASE.rglob('*') if p.is_file()}
        newfiles={p.relative_to(data) for p in runtime_paths()}
        assert newfiles-oldfiles=={TEX/(s['texture']+'_'+suffix+'.dds') for c,s in SPECS.items() if c!='red' for suffix in ('d','n','m')}
    report=dict(version='0.51.3',weapons=reports,plugin_unchanged=True,gameplay_tested=False)
    (ROOT/'build/greatsword-minerals-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if args.verify: verify(ROOT/'data'); return
    snapshot()
    for p in (ART,STAGE/MESH,STAGE/TEX):p.mkdir(parents=True,exist_ok=True)
    textures()
    for color,s in SPECS.items():
        key='greatsword3'+color; n=NifBlocks(BASE/MESH/(key+'.nif')); si,ti=body(n)
        shader=bytearray(n.blocks[si][1]);assert len(shader)==100
        struct.pack_into('<I',shader,0,1)
        struct.pack_into('<II',shader,16,0x80400081 if s['power'] else 0x80000081,1)
        struct.pack_into('<4f',shader,44,*EMIT[color],s['power'])
        struct.pack_into('<7f',shader,64,1,0,s['gloss'],1,1,1,s['spec'])
        shader+=struct.pack('<f',s['env']); n.blocks[si]=('BSLightingShaderProperty',bytes(shader))
        prefix='textures\\weapons\\arcanearsenal\\'
        paths=[prefix+s['texture']+'_d.dds',prefix+s['texture']+'_n.dds','','',prefix+'aa_trial_env.dds',prefix+s['texture']+'_m.dds','','','']
        n.blocks[ti]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths))
        n.save(STAGE/MESH/(key+'.nif'))
    verify(STAGE)
    if args.apply:
        for p in STAGE.rglob('*'):
            if p.is_file():shutil.copy2(p,ROOT/'data'/p.relative_to(STAGE))
        verify(ROOT/'data')

if __name__=='__main__':main()
