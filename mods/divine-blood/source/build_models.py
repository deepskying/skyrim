"""Sixteen authored solid relics; no image planes or concept-projected textures."""
import math, sys, struct, shutil, json
from itertools import product
from catalog import ROOT, catalog
sys.path.insert(0,str(ROOT.parent/'magic-arrows/source'))
from paths import BUILD
from geometric_selected import Solid, write_textures
from five_arrow_redesign import prism, frame, triangulate, area2
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks
from particles import children, effect_shader

COLORS=[(.9,.07,.09),(.12,.36,.95),(.22,.76,.12),(.95,.50,.09),(.93,.86,.64),(.58,.17,.94),(.97,.65,.12),(.72,.13,.07),(.59,.17,.80),(.98,.78,.26),(.09,.17,.38),(.86,.04,.10),(.49,.73,.06),(.13,.15,.17),(.9,.16,.04),(.12,.64,.83)]
def circle(cx,cy,r,n=12):return [(cx+math.cos(j*math.tau/n)*r,cy+math.sin(j*math.tau/n)*r) for j in range(n)]
def crystal(m,x,y,r,h):
    verts=[(x+r*math.cos(j*math.tau/6),y,r*math.sin(j*math.tau/6)) for j in range(6)]+[(x,y+h,0),(x,y-h*.65,0)]
    m.append(verts,[(j,(j+1)%6,6) for j in range(6)]+[((j+1)%6,j,7) for j in range(6)])
def tube(m,p,r=.19):m.tube([(x,y,z) for x,y,z in p],r,6)
def poly(m,p,d=.6):
    # Raised triangulated crystal facets give the silhouette actual front/back volume.
    p=list(p)
    if area2(p)<0:p.reverse()
    triangles=triangulate(p);n=len(p)
    vertices=[(x,y,z) for z in (-d,d) for x,y in p];faces=[]
    for side in (0,1):
        for a,b,c in triangles:
            center=(sum(p[i][0] for i in (a,b,c))/3,sum(p[i][1] for i in (a,b,c))/3)
            peak=len(vertices);vertices.append((*center,(-1 if side==0 else 1)*(d+.45)))
            aa,bb,cc=(i+side*n for i in (a,b,c))
            for face in ((aa,bb,peak),(bb,cc,peak),(cc,aa,peak)):faces.append(tuple(reversed(face)) if side==0 else face)
    faces.extend((j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n));m.append(vertices,faces)
def orb(m,cx,cy,r):
    vertices=[(cx+r*math.sin(a)*math.cos(b),cy+r*math.cos(a),r*math.sin(a)*math.sin(b))
              for a in (math.pi/5,math.pi*2/5,math.pi*3/5,math.pi*4/5) for b in [j*math.tau/10 for j in range(10)]]
    vertices.extend(((cx,cy+r,0),(cx,cy-r,0)))
    faces=[(40,j,(j+1)%10) for j in range(10)]+[(41,30+(j+1)%10,30+j) for j in range(10)]
    faces.extend((k*10+j,(k+1)*10+j,(k+1)*10+(j+1)%10,k*10+(j+1)%10) for k in range(3) for j in range(10));m.append(vertices,faces)
def rotated(p,a,origin=(0,6)):
    c,s=math.cos(a),math.sin(a);return [(origin[0]+x*c-y*s,origin[1]+x*s+y*c) for x,y in p]

def geometry(index):
    core,metal=Solid(),Solid()
    # Distinct silhouettes follow the concept sheet, with thick connected geometry.
    if index==0:
        poly(core,[(0,2),(-3,5),(-3.5,7),(-2.5,9),(-1,9),(0,8),(1,9),(2.5,9),(3.5,7),(3,5)])
        tube(metal,[(-3.5,7,0),(-3.7,4,0),(0,1,0),(3.7,4,0),(3.5,7,0)],.28)
    elif index==1:
        crystal(core,0,5,1.65,6)
        for s in (-1,1):poly(metal,[(s*.8,1),(s*3.6,2.8),(s*3.6,7.5),(s*.8,5.8)],.32)
    elif index==2:
        crystal(core,0,5.2,1.8,5.5)
        for s in (-1,1):
            tube(metal,[(s*.5,1,0),(s*2.7,3.4,0),(s*3.5,7,0),(s*3.3,10,0)],.23)
            for y in (4.5,7):tube(metal,[(s*3.1,y,0),(s*4.4,y+1.2,0),(s*4.6,y+2,0)],.16)
    elif index==3:
        poly(core,[(-4.5,7),(-3.1,9),(3,9),(4.5,8),(3.2,6),(-1,6),(-.8,3),(1.8,1),(-2.5,1),(-1.4,3),(-1.5,6)],1.1)
        poly(metal,[(-3,0),(3,0),(3,1.5),(-3,1.5)],1.4)
    elif index==4:
        shield=[(0,.5),(3.5,6),(3,8),(0,10),(-3,8),(-3.5,6)]
        poly(core,shield,.65);frame(metal,shield,[(x*.87,(y-5)*.87+5) for x,y in shield],.72)
        poly(metal,[(-.27,1),(.27,1),(.27,5.6),(2.6,5.6),(2.6,6.2),(.27,6.2),(.27,9),(-.27,9),(-.27,6.2),(-2.6,6.2),(-2.6,5.6),(-.27,5.6)],.8)
    elif index==5:
        orb(core,0,5,2.8)
        for axis in range(3):
            p=[]
            for j in range(25):
                a=j*math.tau/24;c,s=math.cos(a)*3.4,math.sin(a)*3.4
                p.append((c,5+s,0) if axis==0 else (c,5,s) if axis==1 else (0,5+c,s))
            tube(metal,p,.20)
    elif index==6:
        for j in range(3):poly(core,rotated([(0,0),(.4,2.4),(2.8,4.6),(3.2,2),(2,1),(1.4,-1)],j*math.tau/3))
        crystal(metal,0,6,.65,1.1)
    elif index==7:
        poly(core,[(-1.6,9),(1.6,9),(.5,5),(1.6,1),(-1.6,1),(-.5,5)],.8)
        for s in (-1,1):poly(metal,[(s*1.5,1),(s*3.8,3),(s*3.1,8),(s*1.7,10),(s*2.5,6)],.4)
        for y in (.8,9.2):poly(metal,[(-1.8,y-.3),(1.8,y-.3),(1.8,y+.3),(-1.8,y+.3)],1)
    elif index==8:
        crescent=[(2.3,10),(-1,9),(-3.2,7),(-3.5,4),(-2,1),(1,0),(3.7,2),(1,1.5),(-.8,3),(-1.5,5),(-.5,7)]
        poly(core,crescent,.55)
        star=[(math.sin(j*math.pi/5)*(2 if j%2==0 else .85),6+math.cos(j*math.pi/5)*(2 if j%2==0 else .85)) for j in range(10)]
        poly(core,star,.8);tube(metal,[(-3,4,0),(-1,1,0),(2.5,1.5,0)],.24)
    elif index==9:
        poly(core,circle(0,5,2.4),1.15);frame(metal,circle(0,5,2.8),circle(0,5,2.5),.6)
        for j in range(8):poly(core,rotated([(-.45,2.5),(0,4.8),(.45,2.5)],j*math.tau/8,(0,5)),.4)
    elif index==10:
        feather=[(.2,1),(2.6,2.5),(3.6,5),(3.1,8),(1.5,10),(2.2,7),(1.9,4)]
        for s in (-1,1):
            poly(core,[(x*s,y) for x,y in feather],.52)
            tube(metal,[(s*.2,1,0),(s*1.8,4,0),(s*2.5,7,0),(s*1.5,10,0)],.17)
    elif index==11:
        poly(core,[(-3.6,7),(-1.6,8.5),(3.5,11),(1,7),(.3,6),(-.8,2),(-3.4,0),(-1.3,4),(-2.4,5)],.6)
        poly(metal,[(-.7,3),(.5,3),(2.5,7),(1.8,8)],.75)
    elif index==12:
        crystal(core,0,4.3,2.2,5)
        tube(metal,[(2.8*math.cos(a),1+a/math.tau*3.8,2.8*math.sin(a)) for a in [j*math.tau/16 for j in range(33)]],.30)
        poly(metal,[(2,8),(3,9),(4.3,8.5),(3.6,7.8)],.55)
    elif index==13:
        crystal(core,0,5,1.7,3.5)
        for a in (0,math.tau/3,math.tau*2/3):poly(metal,[(-2,1),(-3.5,4),(-3,7),(-1.4,10),(-2.1,6),(-1.2,3)],.45) if a==0 else metal.tube([(math.cos(a)*r,y,math.sin(a)*r) for y,r in ((1,1.2),(4,3.2),(7,2.8),(10,.8))],.4,5)
    elif index==14:
        for x,y,r,h in ((0,5,1.2,6),(-3,4,.8,4),(3,4,.8,4),(0,3,.6,3)):
            crystal(core,x,y,r,h)
        for s in (-1,1):tube(metal,[(0,1,0),(s*2.6,2,0),(s*3.8,5,0)],.35)
    else:
        poly(core,[(-1.1,1),(-2,4),(-1.3,7),(1.2,9),(4.2,11),(2,7),(2.5,5),(.8,3)],.65)
        for z in (-.8,.8):tube(metal,[(-1,1,z),(-2,4,z),(-1.8,6,z),(.2,8,z),(3.6,10,z)],.19)
    # Authoring Y-up -> game Z-up; consistent hand-sized collectible scale.
    for m in (core,metal):m.verts=[(x*.55,-z*.55,y*.55) for x,y,z in m.verts]
    return dict(core=core,metal=metal)

def main():
    dst=ROOT/'data/meshes/DivineBlood';dst.mkdir(parents=True,exist_ok=True)
    write_textures();tex=ROOT/'data/textures/DivineBlood';tex.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BUILD/'geometric-selected-05/data/textures/magicarrows/geometric05/facets.dds',tex/'facets.dds')
    work=ROOT/'build';work.mkdir(exist_ok=True);report=[]
    for index,row in enumerate(catalog()):
        parts=geometry(index);stage=work/(row['key']+'-geometry.nif')
        nf=NifFile();nf.initialize('SKYRIMSE',str(stage))
        for name,m in parts.items():nf.createShapeFromData(name,m.verts,m.tris,m.uv,m.normals())
        nf.save();src=NifBlocks(stage)
        n=NifBlocks(ROOT/'source/upstream/Meshes/Props/Crystal/Crystal_Red.nif');n.blocks=n.blocks[:6];children(n,0,[],True)
        # One conservative convex box per relic, in Havok units. Preserve collectible
        # collision body, filter and inventory marker; replace its old crystal hull.
        vertices=[v for m in parts.values() for v in m.verts]
        bounds=[(min(v[a] for v in vertices),max(v[a] for v in vertices)) for a in range(3)]
        old=n.blocks[3][1];count=struct.unpack_from('<I',old,32)[0]
        assert len(old)==36+count*16+4+struct.unpack_from('<I',old,36+count*16)[0]*16
        corners=list(product(*[pair for pair in bounds]))
        hull=old[:32]+struct.pack('<I',8)+b''.join(struct.pack('<4f',*(c/69.99125 for c in v),0) for v in corners)+struct.pack('<I',6)
        for a in range(3):
            for side in (0,1):
                normal=[0.,0.,0.];normal[a]=-1. if side==0 else 1.
                hull+=struct.pack('<4f',*normal,-normal[a]*bounds[a][side]/69.99125)
        n.blocks[3]=('bhkConvexVerticesShape',hull)
        for block,payload in src.blocks:
            if block!='BSTriShape':continue
            b=bytearray(payload);name=src.strings[struct.unpack_from('<I',b)[0]].decode();assert struct.unpack_from('<I',b,4)[0]==0
            struct.pack_into('<I',b,0,n.string('DB_'+row['key']+'_'+name))
            shader=effect_shader('textures\\DivineBlood\\facets.dds',COLORS[index] if name=='core' else (.30,.21,.12),1,.9 if name=='core' else .6)
            si=n.append('BSEffectShaderProperty',shader)
            struct.pack_into('<i',b,68,-1);struct.pack_into('<i',b,88,-1);struct.pack_into('<II',b,92,si,0xffffffff)
            bi=n.append('BSTriShape',b);children(n,0,[bi])
        out=dst/(row['key']+'.nif');n.save(out)
        check=NifFile(str(out));assert len(check.shapes)==2
        assert all(all(math.isfinite(c) for v in s.verts for c in v) and len(s.tris)>0 for s in check.shapes)
        report.append(dict(key=row['key'],triangles=sum(len(s.tris) for s in check.shapes),bounds=bounds,collision='convex-box'))
    (work/'models.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('Built and reread 16 distinct collision-enabled NIFs')
if __name__=='__main__':main()
