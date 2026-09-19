"""Build two independent opaque material trials inspired by the supplied art.

Outputs to build/reference-trials/data first. No live runtime files are changed.
Preserves model, UV, collision, original edge and particle blocks byte-for-byte.
"""
from pathlib import Path
import json,struct,subprocess
import numpy as np
from PIL import Image
from nif_blocks import NifBlocks
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'art/reference-material-trials';OUT.mkdir(exist_ok=True)
DATA=ROOT/'build/reference-trials/data'
TEX=DATA/'textures/weapons/arcanearsenal';TEX.mkdir(parents=True,exist_ok=True)
MESH=DATA/'meshes/weapons/arcanearsenal';MESH.mkdir(parents=True,exist_ok=True)
CONV=Path('C:/Users/linos/Desktop/games/+skyrim/TOOLS/+tools-VRAMr/VRAMr/tools/texconv.exe')
N=1024;y,x=np.mgrid[:N,:N].astype(np.float32)/N
rng=np.random.default_rng(91851)
cloud=(np.sin(2*np.pi*(3*x+2*y))+.5*np.sin(2*np.pi*(7*x-5*y)))/1.5
grain=rng.normal(0,1,(N,N)).astype(np.float32)
scratch=np.sin(2*np.pi*(223*x+2*y))*.5+np.sin(2*np.pi*(347*x-3*y))*.5
# Seamless cellular facets create broad crystalline tone changes, not cracks.
px=x*12;py=y*18;ix=px.astype(int);iy=py.astype(int)
seeds=rng.uniform(.15,.85,(18,12,2));values=rng.uniform(.55,1.25,(18,12))
nearest=np.full_like(x,1e9);facet=np.zeros_like(x);height=np.zeros_like(x)
for dy in [-1,0,1]:
    for dx in [-1,0,1]:
        sx=ix+dx;sy=iy+dy;j=seeds[sy%18,sx%12]
        vx=px-sx-j[:,:,0];vy=py-sy-j[:,:,1];d=vx*vx+vy*vy;mask=d<nearest
        nearest=np.minimum(nearest,d);facet=np.where(mask,values[sy%18,sx%12]+vx*.12+vy*.08,facet)
        height=np.where(mask,(vx*.2+vy*.12)*.018,height)
specs=[dict(key='waraxeredmetal',source='waraxe2red',name='余烬·错牙·赤钢试作',color=[.13,.065,.062],gloss=65.,spec=.85,env=.28,emit=[.85,.025,.02],power=.09),
       dict(key='waraxegreenjade',source='waraxe2green',name='流萤·回翎·翠晶试作',color=[.025,.20,.115],gloss=110.,spec=.95,env=.48,emit=[.015,.8,.32],power=.22)]
reports=[]
for s in specs:
    green=s['key']=='waraxegreenjade'
    variation=facet if green else 1+.06*cloud+.018*scratch+.012*grain
    diffuse=np.clip(variation[:,:,None]*np.array(s['color']),0,1)
    h=height if green else scratch*.002+grain*.0003
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*3;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*3
    normal=np.stack([-dx,dy,np.ones_like(x)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    normal=normal*.5+.5
    envmask=np.ones((N,N,3),np.float32)*(.6 if green else .36)
    for suffix,rgb,alpha in [('d',diffuse,1),('n',normal,.7 if green else .5),('m',envmask,1)]:
        rgba=np.concatenate([rgb,np.full((N,N,1),alpha)],-1)
        p=OUT/(s['key']+'_'+suffix+'.png');Image.fromarray(np.round(np.clip(rgba,0,1)*255).astype(np.uint8)).save(p)
        subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(TEX),str(p)],check=True,capture_output=True)
    source=ROOT/'data/meshes/weapons/arcanearsenal'/(s['source']+'.nif')
    n=NifBlocks(source);original=NifBlocks(source)
    shape=next(b for k,b in n.blocks if k=='BSTriShape' and n.strings[struct.unpack_from('<I',b)[0]]==b'AA_WaraxeBody')
    si=struct.unpack_from('<I',shape,92)[0];shader=bytearray(n.blocks[si][1]);ti=struct.unpack_from('<I',shader,40)[0]
    assert len(shader)==100
    struct.pack_into('<I',shader,0,1) # Environment map shader
    struct.pack_into('<II',shader,16,0x80400081,1) # Own emission + specular + reflection
    struct.pack_into('<4f',shader,44,*s['emit'],s['power'])
    struct.pack_into('<7f',shader,64,1,0,s['gloss'],1,1,1,s['spec'])
    shader+=struct.pack('<f',s['env']);n.blocks[si]=('BSLightingShaderProperty',bytes(shader))
    prefix='textures\\weapons\\arcanearsenal\\'
    paths=[prefix+s['key']+'_d.dds',prefix+s['key']+'_n.dds','','',prefix+'aa_trial_env.dds',prefix+s['key']+'_m.dds','','','']
    n.blocks[ti]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths))
    n.save(MESH/(s['key']+'.nif'))
    assert all(a==b for i,(a,b) in enumerate(zip(original.blocks,n.blocks)) if i not in [si,ti])
    reports.append(dict(**s,changed_blocks=[si,ti],opaque=True,geometry_uv_collision_edges_particles_unchanged=True))
(ROOT/'build/reference-trials/material-report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(reports,ensure_ascii=True))
