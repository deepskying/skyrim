"""Deterministic, seamless 1K crystal diffuse, normal/gloss and glow maps.

Authored from analytic fields; no external artwork or borrowed texture assets.
Normal RGB encodes tangent-space detail; alpha controls Skyrim specular strength.
"""
import json
from pathlib import Path
import mesh_builder as mb
from mesh_builder import bpy,np,ART,TEX


def build(spec):
    n=1024;key=spec['key'];kind=spec['design']
    out=ART/'crystal-textures';out.mkdir(exist_ok=True)
    y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
    rng=np.random.default_rng(921+['ruby','emerald','frost','amethyst'].index(kind))
    first=np.full_like(x,9);second=first.copy();cell=np.zeros_like(x)
    for i,(sx,sy) in enumerate(rng.random((34,2))):
        dx=(x-sx+.5)%1-.5;dy=(y-sy+.5)%1-.5
        d=dx*dx+dy*dy
        cell=np.where(d<first,(i%9)/8,cell)
        second=np.minimum(second,np.maximum(first,d));first=np.minimum(first,d)
    gap=np.sqrt(second)-np.sqrt(first)
    crack=np.exp(-(gap/.0022)**2)
    hair=np.exp(-(gap/.00085)**2)
    wave=(np.sin(2*np.pi*(3*x+5*y))+.4*np.sin(2*np.pi*(11*x-7*y)))/1.4
    # Several non-aligned harmonics avoid a visible checker/weave on broad ice faces.
    fine=sum(np.sin(2*np.pi*(a*x+b*y)+phase) for a,b,phase in
             [(17,23,.2),(31,-19,1.3),(43,11,2.1),(13,-37,.9),(29,41,2.8)]) / 5
    if kind=='ruby':
        glow=.035+.68*hair+.15*crack
        tone=.30+.33*cell+.12*wave+.18*crack
        height=.08*wave-.08*crack
        gloss=.65+.25*cell
    elif kind=='emerald':
        bands=(.5+.5*np.sin(2*np.pi*(6*x+2*y)+.6*np.sin(2*np.pi*3*y)))**14
        flecks=np.maximum(0,fine-.88)*6
        glow=.028+.18*hair+.45*bands+.28*flecks
        tone=.35+.22*cell+.18*wave+.14*bands
        height=.035*wave+.022*bands+.004*fine
        gloss=.68+.20*cell
    elif kind=='frost':
        frost=(.5+.5*wave)**4
        glow=.025+.45*hair+.12*frost
        tone=.40+.18*cell+.24*frost+.025*fine
        height=.035*wave-.065*crack+.004*fine*frost
        gloss=.90-.48*frost
    else:
        bands=.5+.5*np.sin(2*np.pi*(3*x+7*y)+.7*np.sin(2*np.pi*2*x))
        bands=bands**5
        glow=.025+.47*bands+.18*hair
        tone=.27+.25*cell+.28*bands+.09*wave
        height=.03*wave+.065*bands-.024*crack
        gloss=.78+.15*cell
    color=np.array(spec['color'],np.float32)
    pale=np.array(spec['edge'],np.float32)
    diffuse=np.ones((n,n,4),np.float32)
    diffuse[:,:,:3]=np.clip(tone[:,:,None]*color+.065*pale+.03*crack[:,:,None],0,1)
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*24
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*24
    vec=np.stack((-dx,dy,np.ones_like(x)),axis=-1)
    vec/=np.linalg.norm(vec,axis=-1,keepdims=True)
    normal=np.concatenate((vec*.5+.5,np.clip(gloss,0,1)[:,:,None]),axis=-1)
    emissive=np.ones((n,n,4),np.float32);emissive[:,:,:3]=np.clip(glow[:,:,None],0,1)
    result={};report={}
    texconv=r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe'
    for suffix,pixels in [('d',diffuse),('n',normal),('g',emissive)]:
        name=key+'_'+suffix
        im=bpy.data.images.new(name,width=n,height=n,alpha=True)
        if suffix=='n':im.colorspace_settings.name='Non-Color'
        im.pixels.foreach_set(pixels.astype(np.float32).ravel())
        im.filepath_raw=str(out/(name+'.png'));im.file_format='PNG';im.save()
        mb.subprocess.run([texconv,'-nologo','-y','-f','BC3_UNORM' if suffix=='n' else 'BC7_UNORM','-m','0','-o',str(TEX),im.filepath_raw],check=True,capture_output=True)
        # Reload exactly the compressed game texture for source previews.
        im.filepath=str(TEX/(name+'.dds'));im.reload();result[suffix]=im
        report[suffix]={'resolution':n,'min_rgb':float(pixels[:,:,:3].min()),'max_rgb':float(pixels[:,:,:3].max()),'std_rgb':float(pixels[:,:,:3].std()),'alpha_min':float(pixels[:,:,3].min()),'alpha_max':float(pixels[:,:,3].max())}
    (mb.ROOT/'build'/(key+'-textures.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return result
