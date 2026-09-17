"""Four opaque, full-body emissive material trials on the approved second axes.

Run with bundled Python (numpy/Pillow). Patch only body shader and texture set;
source is the immutable 0.44 baseline so rebuilds never compound modifications.
"""
from pathlib import Path
import json, struct, subprocess
import numpy as np
from PIL import Image, ImageFilter
from nif_blocks import NifBlocks

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'art/emissive-materials'; OUT.mkdir(exist_ok=True)
TEX=ROOT/'data/textures/weapons/arcanearsenal'
BASE=ROOT/'build/before-0.45.0/data/meshes/weapons/arcanearsenal'
CONV=Path('C:/Users/linos/Desktop/games/+skyrim/TOOLS/+tools-VRAMr/VRAMr/tools/texconv.exe')
N=1024
y,x=np.mgrid[:N,:N].astype(np.float32)/N
rng=np.random.default_rng(91745)

def noise(grid):
    a=rng.random((grid,grid),dtype=np.float32)
    px=x*grid;py=y*grid;ix=px.astype(int);iy=py.astype(int)
    u=px-ix;v=py-iy;u=u*u*(3-2*u);v=v*v*(3-2*v)
    return (a[iy%grid,ix%grid]*(1-u)+a[iy%grid,(ix+1)%grid]*u)*(1-v)+(a[(iy+1)%grid,ix%grid]*(1-u)+a[(iy+1)%grid,(ix+1)%grid]*u)*v

cloud=sum(noise(g)*w for g,w in [(3,.42),(7,.28),(16,.17),(37,.09),(91,.04)])
cloud=np.clip((cloud-.25)*1.8,0,1)

def cells(gx,gy,warp=0):
    px=x*gx+warp*(np.sin(y*6.283*3)+(cloud-.5)*2);py=y*gy+warp*(np.sin(x*6.283*4)+(cloud-.5)*2)
    ix=np.floor(px).astype(int);iy=np.floor(py).astype(int)
    seeds=rng.uniform(.12,.88,(gy,gx,2));tones=rng.uniform(.1,.9,(gy,gx))
    d1=np.full_like(x,1e9);d2=d1.copy();tone=np.zeros_like(x);slope=np.zeros_like(x)
    for dy in [-1,0,1]:
        for dx in [-1,0,1]:
            sx=ix+dx;sy=iy+dy;j=seeds[sy%gy,sx%gx]
            vx=px-sx-j[:,:,0];vy=py-sy-j[:,:,1];d=vx*vx+vy*vy
            near=d<d1;d2=np.where(near,d1,np.minimum(d2,d));d1=np.minimum(d1,d)
            tone=np.where(near,tones[sy%gy,sx%gx],tone)
            slope=np.where(near,vx*.25+vy*.2,slope)
    return np.sqrt(d2)-np.sqrt(d1),tone,slope

border,_,_=cells(8,15,.23)
veins=np.exp(-(border/.035)**2)
halo=np.exp(-(border/.13)**2)
fineborder,_,_=cells(23,39,.13)
veins=np.maximum(veins,.42*np.exp(-(fineborder/.025)**2)*np.clip((cloud-.45)*5,0,1))
red=.35+.25*cloud+.32*veins+.07*halo
specks=Image.new('L',(N,N));a=np.zeros((N,N),np.uint8)
for _ in range(4200):a[rng.integers(N),rng.integers(N)]=rng.integers(100,256)
specks=Image.fromarray(a).filter(ImageFilter.MaxFilter(3))
stars=np.asarray(specks,dtype=np.float32)/255
soft=np.asarray(specks.filter(ImageFilter.GaussianBlur(2)),dtype=np.float32)/255
green=np.clip(.49+.15*cloud+.31*stars+.3*soft,0,1)
border,tone,slope=cells(12,19)
plates=np.clip(.30+.6*tone+slope,0,1)
seams=np.exp(-(border/.026)**2)
blue=np.clip(.43+.34*plates+.14*seams,0,1)
nebula=np.clip((cloud-.3)*2.3,0,1)
nebula=np.clip(nebula+.2*np.exp(-((cloud-.51)/.06)**2)*noise(32),0,1)
purple=.30+.64*nebula

specs=[('red','熔光脉络',red,veins,[1,.025,.04],[1,.30,.14],veins*.15+cloud*.06),
       ('green','星砂琉璃',green,stars,[.025,.80,.24],[.40,1,.67],stars*.06),
       ('blue','层叠晶片',blue,plates,[.035,.40,1],[.40,.85,1],plates*.4),
       ('purple','云雾光晶',purple,nebula,[.42,.025,1],[.76,.30,1],cloud*.025)]
report=[]
for color,label,level,detail,base,highlight,height in specs:
    # A nonzero colored glow covers every texel, including quiet background areas.
    tint=np.array(base)[None,None,:]*(1-detail[:,:,None]*.65)+np.array(highlight)[None,None,:]*(detail[:,:,None]*.65)
    glow=np.clip(tint*level[:,:,None],0,1)
    diffuse=np.clip(tint*(.38+.34*level[:,:,None]),0,1)
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*1.2
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*1.2
    normal=np.stack((-dx,dy,np.ones_like(x)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    normal=normal*.5+.5
    key='aa_emissive_'+color
    for suffix,rgb,alpha in [('d',diffuse,1),('g',glow,1),('n',normal,.25)]:
        rgba=np.concatenate([rgb,np.full((N,N,1),alpha)],axis=-1)
        p=OUT/f'{key}_{suffix}.png';Image.fromarray(np.round(rgba*255).astype(np.uint8)).save(p)
        subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(TEX),str(p)],check=True,capture_output=True)
    nif=NifBlocks(BASE/f'waraxe2{color}.nif')
    shape=next(b for k,b in nif.blocks if k=='BSTriShape' and nif.strings[struct.unpack_from('<I',b)[0]]==b'AA_WaraxeBody')
    si=struct.unpack_from('<I',shape,92)[0];shader=bytearray(nif.blocks[si][1]);ti=struct.unpack_from('<I',shader,40)[0]
    assert struct.unpack_from('<I',shader)[0]==2 and len(shader)==100
    power=struct.unpack_from('<f',shader,56)[0]
    struct.pack_into('<3f',shader,44,1,1,1) # hue is now carried by colored glow map
    flags=struct.unpack_from('<I',shader,16)[0];struct.pack_into('<I',shader,16,flags|1)
    struct.pack_into('<f',shader,72,24 if color!='blue' else 55)
    struct.pack_into('<4f',shader,76,1,1,1,.28)
    nif.blocks[si]=('BSLightingShaderProperty',bytes(shader))
    paths=[f'textures\\weapons\\arcanearsenal\\{key}_{s}.dds' for s in ['d','n','g']]+['']*6
    nif.blocks[ti]=('BSShaderTextureSet',struct.pack('<I',9)+b''.join(struct.pack('<I',len(p))+p.encode() for p in paths))
    dest=ROOT/f'data/meshes/weapons/arcanearsenal/waraxe2{color}.nif';nif.save(dest)
    original=NifBlocks(BASE/dest.name)
    assert all(a==b for i,(a,b) in enumerate(zip(original.blocks,nif.blocks)) if i not in [si,ti])
    report.append(dict(key='waraxe2'+color,material=label,body_emission_power=power,changed_blocks=[si,ti],glow_min=float(glow.max(axis=-1).min()),glow_max=float(glow.max()),opaque=True))
(ROOT/'build/emissive-materials-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
