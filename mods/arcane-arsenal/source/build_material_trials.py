"""Create two lossless material-only copies of waraxe2red for in-game A/B testing.

Normal Python with numpy/Pillow. Only body shader/texture blocks are patched;
mesh vertices, UVs, attachments, Havok and existing emissive edge/particles stay.
"""
from pathlib import Path
import sys,struct,json,subprocess,hashlib
import numpy as np
from PIL import Image
from nif_blocks import NifBlocks

ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/'data/textures/weapons/arcanearsenal'
MESH=ROOT/'data/meshes/weapons/arcanearsenal'
OUT=ROOT/'art/material-trials';OUT.mkdir(exist_ok=True)
CONVERTER=Path('C:/Users/linos/Desktop/games/+skyrim/TOOLS/+tools-VRAMr/VRAMr/tools/texconv.exe')
SPECS=[dict(key='waraxefrostruby',name='余烬·错牙·磨砂红宝石',gloss=18.,spec=.65,env=.12,alpha=.90),
       dict(key='waraxeobsidian',name='余烬·错牙·黑曜石',gloss=135.,spec=1.1,env=.65,alpha=1.)]

def compress(path,fmt='BC3_UNORM'):
    subprocess.run([str(CONVERTER),'-nologo','-y','-f',fmt,'-m','0','-o',str(TEX),str(path)],check=True,capture_output=True)

# Self-authored neutral studio/horizon cubemap, not a borrowed game texture.
size=128
v,u=np.mgrid[0:size,0:size].astype(np.float32);u=(u+.5)/size*2-1;v=(v+.5)/size*2-1
one=np.ones_like(u)
faces=[(one,-v,-u),(-one,-v,u),(u,one,v),(u,-one,-v),(u,-v,one),(-u,-v,-one)]
pixels=[]
for face in faces:
    d=np.stack(face,-1);d/=np.linalg.norm(d,axis=-1,keepdims=True)
    horizon=np.exp(-((d[:,:,1]-.12)/.23)**2)
    softbox=np.maximum(0,d@np.array([-.45,.5,.74]))**28
    rgb=np.clip(.055+.16*horizon+.6*softbox,0,1)
    rgba=np.ones((size,size,4),np.uint8)*255
    rgba[:,:,:3]=(rgb[:,:,None]*np.array([.91,.95,1.])*255).astype(np.uint8)
    pixels.append(rgba.tobytes())
header=[124,0x100F,size,size,size*4,0,1]+[0]*11+[32,0x41,0,32,0xff,0xff00,0xff0000,0xff000000,0x1008,0xFE00,0,0,0]
cube=OUT/'aa_trial_env.dds';cube.write_bytes(b'DDS '+struct.pack('<31I',*header)+b''.join(pixels))
compress(cube,'BC1_UNORM')

n=1024;y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
rng=np.random.default_rng(91644)
# Periodic grain provides a seamless fine tangent-space normal texture.
grain=sum(np.sin(2*np.pi*(a*x+b*y)+phase) for a,b,phase in
          [(47,83,.1),(97,-61,.6),(131,101,1.3),(179,-113,2.1),(211,157,2.7)])/5
cloud=(np.sin(2*np.pi*(3*x+2*y))+.5*np.sin(2*np.pi*(7*x-5*y)))/1.5
source=MESH/'waraxe2red.nif'
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
reports=[]
for spec in SPECS:
    key=spec['key'];ruby=key=='waraxefrostruby'
    rgba=np.ones((n,n,4),np.float32)
    color=np.array([.47,.045,.09] if ruby else [.034,.016,.024])
    rgba[:,:,:3]=np.clip(color*(1+.045*cloud[:,:,None]+(.025 if ruby else .006)*grain[:,:,None]),0,1)
    height=grain*(.0035 if ruby else .00012)
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*12
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*12
    normal=np.stack((-dx,dy,np.ones_like(x)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    nm=np.ones_like(rgba);nm[:,:,:3]=normal*.5+.5;nm[:,:,3]=(.3+.025*grain) if ruby else .88
    mask=np.ones_like(rgba);mask[:,:,:3]=.28 if ruby else .7
    for suffix,data in [('d',rgba),('n',nm),('m',mask)]:
        path=OUT/(key+'_'+suffix+'.png')
        Image.fromarray(np.round(np.clip(data,0,1)*255).astype(np.uint8)).save(path)
        compress(path)
    nif=NifBlocks(source)
    shape_id=next(i for i,(k,b) in enumerate(nif.blocks) if k=='BSTriShape' and nif.strings[struct.unpack_from('<I',b)[0]]==b'AA_WaraxeBody')
    shape=bytearray(nif.blocks[shape_id][1]);shader_id=struct.unpack_from('<I',shape,92)[0]
    shader=bytearray(nif.blocks[shader_id][1]);assert len(shader)==100
    tex_id=struct.unpack_from('<I',shader,40)[0]
    # Environment-map Skyrim shader: separate body reflections and red edge glow.
    struct.pack_into('<I',shader,0,1)
    struct.pack_into('<II',shader,16,0x80000081,1)  # Z-test, specular, envmap; Z-write
    struct.pack_into('<4f',shader,44,0,0,0,0)       # no body self-emission
    struct.pack_into('<7f',shader,64,spec['alpha'],0,spec['gloss'],1,1,1,spec['spec'])
    shader+=struct.pack('<f',spec['env'])
    nif.blocks[shader_id]=('BSLightingShaderProperty',bytes(shader))
    paths=['textures\\weapons\\arcanearsenal\\'+key+'_d.dds',
           'textures\\weapons\\arcanearsenal\\'+key+'_n.dds','','',
           'textures\\weapons\\arcanearsenal\\aa_trial_env.dds',
           'textures\\weapons\\arcanearsenal\\'+key+'_m.dds','','','']
    nif.blocks[tex_id]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode('ascii') for p in paths))
    touched={shader_id,tex_id}
    if ruby:
        # SRC_ALPHA / INV_SRC_ALPHA blending, sorting enabled, no alpha test.
        alpha=nif.append('NiAlphaProperty',struct.pack('<iIiHB',-1,0,-1,0xED,0))
        struct.pack_into('<I',shape,96,alpha)
        nif.blocks[shape_id]=('BSTriShape',bytes(shape));touched.add(shape_id)
    destination=MESH/(key+'.nif');nif.save(destination)
    old=NifBlocks(source);new=NifBlocks(destination)
    assert all(old.blocks[i]==new.blocks[i] for i in range(len(old.blocks)) if i not in touched)
    assert old.strings==new.strings
    reports.append({**spec,'source':source.name,'changed_blocks':sorted(touched),'new_alpha_block':ruby,
                    'mesh_and_collision_unchanged':True,'edge_and_particles_unchanged':True})
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
(ROOT/'build/material-trials-build.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(reports,ensure_ascii=True))
