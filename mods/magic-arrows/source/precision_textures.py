"""Convert authored material sources into Skyrim-readable RGBA DDS atlases."""
import sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy,numpy as np
from paths import ROOT,BUILD
from precision_samples import KEYS
out=BUILD/'precision-samples-01/data/textures/magicarrows/precision01'
out.mkdir(parents=True,exist_ok=True)
def write_dds(path,pixels):
    h,w=pixels.shape[:2];p=lambda *v:struct.pack('<'+'I'*len(v),*v)
    header=p(124,0x100f,h,w,w*4,0,1)+p(*([0]*11))
    header+=p(32,0x41,0,32,0xff,0xff00,0xff0000,0xff000000)+p(0x1000,0,0,0,0)
    path.write_bytes(b'DDS '+header+pixels.tobytes())
for key in KEYS:
    img=bpy.data.images.load(str(ROOT/'art/precision-samples-01/material-sources'/f'{key}.png'))
    img.scale(512,512)
    pixels=np.empty(512*512*4,dtype=np.float32);img.pixels.foreach_get(pixels)
    pattern=pixels.reshape(512,512,4)[:,:,:3]
    for part in ('shaft','head','tail','trim','edge'):
        if part=='edge':
            write_dds(out/f'{key}_{part}.dds',np.full((32,32,4),255,dtype=np.uint8));continue
        base=pattern.copy()
        if key=='ice':base=base*.65+np.array((.07,.18,.25))
        if part=='trim':
            lum=base.mean(axis=2,keepdims=True)
            base=lum*np.array((.72,.82,.90) if key=='ice' else (1,.69,.28))+.08
        if part=='shaft':base=base*.65+np.array((.04,.12,.18) if key=='ice' else (.15,.12,.06))
        atlas=np.ones((2048,2048,4),dtype=np.uint8)*255
        for tile in range(16):
            x,y=tile%4,tile//4
            atlas[y*512:(y+1)*512,x*512:(x+1)*512,:3]=np.clip(base*(.35+.7*tile/15)*255,0,255).astype(np.uint8)
        write_dds(out/f'{key}_{part}.dds',atlas)
print('Precision DDS atlases complete')
