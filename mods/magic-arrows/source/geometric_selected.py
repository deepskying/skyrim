"""Eleven concept arrows built entirely from closed geometric solids.

No silhouette tracing or projected illustration textures. Tip Y=.07, nock Y=58.
"""
import math,struct
from geometry import Mesh,cross,sub,norm
from redesign_geometry import loft,smooth_samples
from paths import BUILD

VERSION='0.6.1'
REMAINING=('fire','ice','shock','poison','earth')
KEYS=('fire','ice','shock','poison','holy','wind','water','earth','dark','soul','arcane')
LABELS={'fire':'01 火焰箭','ice':'02 冰晶箭','shock':'03 雷霆箭','poison':'04 毒素箭',
        'earth':'08 大地箭','holy':'05 圣辉箭','wind':'06 风元素箭','water':'07 水元素箭',
        'dark':'09 暗影箭','soul':'10 星魂箭','arcane':'11 奥术箭'}
PALETTE={
 'fire':((.38,.038,.004),(.85,.14,.015),(1,.54,.10)),
 'ice':((.025,.19,.39),(.08,.48,.78),(.55,.89,1)),
 'shock':((.028,.018,.30),(.12,.08,.73),(.43,.58,1)),
 'poison':((.028,.13,.009),(.13,.49,.035),(.49,.89,.12)),
 'earth':((.21,.08,.018),(.48,.25,.062),(.91,.57,.15)),
 'holy':((.76,.43,.10),(.92,.73,.34),(1,.91,.66)),
 'wind':((.025,.30,.25),(.06,.66,.52),(.42,.96,.81)),
 'water':((.018,.16,.50),(.035,.40,.85),(.32,.80,1)),
 'dark':((.045,.012,.10),(.12,.045,.28),(.53,.19,.95)),
 'soul':((.085,.038,.28),(.28,.16,.72),(.46,.60,1)),
 'arcane':((.19,.012,.14),(.53,.03,.33),(.95,.20,.63)),
}

class Solid(Mesh):
    """Closed faces with a simple baked directional tone for emissive volume."""
    def append(self,verts,faces):
        for face in faces:
            vs=[verts[i] for i in face]
            n=norm(cross(sub(vs[1],vs[0]),sub(vs[2],vs[0])))
            # A restrained symmetric light cue, not detail copied from concept art.
            shade=.37+.63*min(1,abs(n[2])*.88+abs(n[0])*.28+abs(n[1])*.10)
            tile=min(15,max(0,round((shade-.30)/.70*15)))
            start=len(self.verts);self.verts.extend(vs)
            self.uv.extend([((tile%4+.5)/4,(tile//4+.5)/4)]*len(vs))
            for j in range(1,len(vs)-1):self.tris.append((start,start+j,start+j+1))

def texture_path(key,part):return 'textures\\magicarrows\\geometric05\\facets.dds'
def shader_values(key,part):
    dark,base,light=PALETTE[key]
    color={'head':light if key=='holy' else base,'accent':dark if key in ('dark','arcane') else base,
           'edge':light,'shaft':base,'tail':base,'trim':dark}[part]
    return color,1.65 if part=='edge' else 1.55

def write_textures():
    root=BUILD/'geometric-selected-05/data/textures/magicarrows/geometric05';root.mkdir(parents=True,exist_ok=True)
    size=64;rgba=bytearray()
    for y in range(size):
        for x in range(size):
            tile=(y//16)*4+x//16;linear=.30+.70*tile/15
            encoded=round(255*(1.055*linear**(1/2.4)-.055))
            rgba.extend((encoded,encoded,encoded,255))
    p=lambda *v:struct.pack('<'+'I'*len(v),*v)
    header=p(124,0x100f,size,size,size*4,0,1)+p(*([0]*11))
    header+=p(32,0x41,0,32,255,65280,16711680,4278190080)+p(4096,0,0,0,0)
    (root/'facets.dds').write_bytes(b'DDS '+header+rgba)

def petal(mesh,samples,phase=0,sides=8):
    rings=[]
    for y,r,w,t,a in smooth_samples(samples,6):
        a+=phase;rings.append((y,w,t,r*math.cos(a),r*math.sin(a),a))
    loft(mesh,rings,sides)

def seam(mesh,samples,phase=0,radius=.025):
    points=[]
    for y,r,w,t,a in smooth_samples(samples,6):
        a+=phase
        points.append((r*math.cos(a)-t*.96*math.sin(a),y,r*math.sin(a)+t*.96*math.cos(a)))
    mesh.tube(points,radius,6)

def bevel_square(mesh,rings):
    outline=((1,.72),(.72,1),(-.72,1),(-1,.72),(-1,-.72),(-.72,-1),(.72,-1),(1,-.72))
    vs=[];faces=[]
    for y,r in rings:vs.extend((x*r,y,z*r) for x,z in outline)
    for k in range(len(rings)-1):
        for j in range(8):
            a=k*8+j;b=k*8+(j+1)%8;faces.append((b,a,a+8,b+8))
    faces+=[tuple(range(8)),tuple((len(rings)-1)*8+j for j in range(7,-1,-1))]
    mesh.append(vs,faces)

def generate(key):
    if key not in KEYS:raise ValueError(key)
    parts={name:Solid() for name in ('head','accent','edge','shaft','tail','trim')}
    head,accent,edge,shaft,tail,trim=(parts[name] for name in parts)
    shaft.tube([(0,10.6,0),(0,45.5,0),(0,49.0,0),(0,57.25,0)],.17,12)
    for y in (10.65,49.5):
        loft(trim,[(y-.25,.20,.20,0,0,0),(y-.18,.27,.27,0,0,0),
                   (y+.18,.27,.27,0,0,0),(y+.25,.20,.20,0,0,0)],8)
    for x in (-.12,.12):trim.tube([(x,57.1,0),(x,57.94,0)],[.09,.06],8)
    if key=='fire':
        loft(head,[(.07,.022,.022,0,0,0),(4.5,.51,.51,0,0,.12),
                   (7.4,.80,.67,0,0,.12),(10.8,.23,.23,0,0,0)],6)
        for a in (0,math.pi):
            samples=[(2.9,1.12,.025,.025,-.13),(4.7,1.66,.33,.24,-.06),
                     (6.4,1.36,.44,.29,.05),(8.4,.74,.29,.21,.14),
                     (10.55,.22,.08,.08,.10)]
            petal(accent,samples,a);seam(edge,samples,a,.026)
    elif key=='ice':
        loft(head,[(.07,.025,.025,0,0,.15),(5.4,1.06,1.06,0,0,.15),
                   (8.4,.68,.68,0,0,.15),(10.8,.23,.23,0,0,.15)],6)
        for i,a in enumerate((0,math.pi)):
            rings=[]
            for y,r,w,t in ((5.3+i*.85,1.49,.023,.023),(7.5+i*.4,1.06,.29,.25),
                             (9.1,.66,.21,.18),(10.55,.23,.08,.08)):
                rings.append((y,w,t,r*math.cos(a),r*math.sin(a),a+.12))
            loft(accent,rings,5)
            edge.tube([(r*math.cos(a),y,r*math.sin(a)+t) for y,r,w,t in
                       ((5.3+i*.85,1.49,.023,.023),(7.5+i*.4,1.06,.29,.25),(10.55,.23,.08,.08))],.023,6)
    elif key=='shock':
        loft(head,[(.07,.022,.022,0,0,0),(5.7,.69,.69,0,0,0),
                   (8.7,.44,.44,0,0,0),(10.8,.23,.23,0,0,0)],4)
        for a in (0,math.pi):
            samples=[(3.9,1.67,.025,.025,0),(4.5,1.38,.19,.19,0),
                     (5.1,.88,.15,.18,0),(6.5,1.50,.20,.22,0),
                     (7.4,.81,.14,.17,0),(8.9,1.32,.18,.20,0),
                     (9.7,.60,.14,.14,0),(10.55,.23,.08,.08,0)]
            loft(accent,[(y,w,t,r*math.cos(a),r*math.sin(a),a) for y,r,w,t,_ in samples],4)
            edge.tube([(r*math.cos(a)-t*.97*math.sin(a),y,r*math.sin(a)+t*.97*math.cos(a)) for y,r,w,t,_ in samples],.025,6)
    elif key=='poison':
        loft(head,[(.07,.022,.022,0,0,0),(5.9,.34,.34,0,0,0),
                   (8.7,.30,.30,0,0,0),(10.8,.23,.23,0,0,0)],6)
        for a in (0,math.pi):
            samples=[(2.0,.65,.025,.025,-.10),(3.7,1.32,.24,.23,-.06),
                     (5.8,1.47,.41,.32,.04),(8.3,.90,.35,.28,.10),
                     (10.55,.23,.08,.08,.10)]
            petal(accent,samples,a);seam(edge,samples,a,.024)
    elif key=='earth':
        loft(head,[(.07,.025,.025,0,0,.2),(6.5,1.18,1.18,0,0,.2),
                   (8.25,1.18,1.18,0,0,.2),(8.6,.84,.84,0,0,.2),
                   (10.8,.23,.23,0,0,.2)],5)
        loft(accent,[(8.75,.83,.83,0,0,.2),(9.05,.83,.83,0,0,.2),
                     (9.35,.57,.57,0,0,.2),(10.5,.28,.28,0,0,.2)],5)
        for i in range(5):
            a=.2+i*math.tau/5
            edge.tube([(r*math.cos(a),y,r*math.sin(a)) for r,y in
                       ((.03,.13),(1.18,6.5),(1.18,8.25),(.84,8.6),(.23,10.7))],.026,6)
    elif key=='holy':
        loft(head,[(.07,.022,.022,0,0,0),(6.1,.98,.98,0,0,0),
                   (8.8,.61,.61,0,0,0),(10.8,.23,.23,0,0,0)],6)
        for a in (0,math.tau/3,2*math.tau/3):
            samples=[(6.1,1.63,.02,.025,0),(7.0,1.59,.26,.19,-.07),
                     (8.5,.99,.39,.28,-.06),(10.55,.22,.09,.09,0)]
            petal(accent,samples,a);seam(edge,samples,a)
    elif key=='dark':
        loft(head,[(.07,.02,.02,0,0,.15),(6.8,.74,.74,0,0,.15),
                   (9.4,.42,.42,0,0,.15),(10.8,.22,.22,0,0,.15)],3)
        for i,a in enumerate((0,math.tau/3,2*math.tau/3)):
            tip=5.5+i*.45
            samples=[(tip,1.73,.02,.025,-.10),(tip+1.0,1.50,.22,.16,-.05),
                     (8.6,.87,.29,.21,.05),(10.55,.23,.075,.075,.1)]
            petal(accent,samples,a,6);seam(edge,samples,a,.022)
    elif key=='soul':
        loft(head,[(.07,.02,.02,0,0,.15),(4.9,1.08,1.08,0,0,.15),
                   (7.9,.88,.88,0,0,.15),(10.8,.23,.23,0,0,.15)],6)
        for a in (0,math.tau/3,2*math.tau/3):
            samples=[(7.35,1.07,.025,.025,0),(8.4,.90,.19,.13,.06),
                     (9.6,.54,.25,.18,.04),(10.6,.20,.09,.08,0)]
            petal(accent,samples,a,6);seam(edge,samples,a,.023)
    elif key=='arcane':
        bevel_square(head,[(.07,.025),(7.85,.82),(8.15,.82)])
        loft(trim,[(8.15,.48,.48,0,0,0),(8.5,.48,.48,0,0,0),
                   (10.55,.30,.30,0,0,0),(10.85,.23,.23,0,0,0)],8)
        for a in (0,math.tau/3,2*math.tau/3):
            samples=[(7.9,1.10,.025,.025,0),(8.4,1.05,.22,.21,0),
                     (9.1,.83,.25,.22,0),(9.4,.66,.16,.17,0),(10.5,.27,.07,.075,0)]
            petal(accent,samples,a,4);seam(edge,samples,a,.023)
    elif key=='wind':
        loft(head,[(.07,.02,.02,0,0,0),(3.7,.40,.40,0,0,.15),
                   (6.8,.54,.54,0,0,.25),(10.8,.22,.22,0,0,0)],6)
        for a in (0,math.pi):
            samples=[(1.9,.23,.025,.025,-.60),(4.0,.75,.22,.17,-.10),
                     (6.3,1.61,.36,.23,.95),(8.4,1.53,.38,.24,2.0),
                     (10.6,.23,.08,.075,2.85)]
            petal(accent,samples,a,8);seam(edge,samples,a,.025)
    elif key=='water':
        loft(head,[(.07,.02,.02,0,0,0),(2.2,.24,.24,0,0,0),(4.5,.64,.64,0,0,0),
                   (6.9,1.05,1.05,0,0,0),(8.6,.91,.91,0,0,0),
                   (9.7,.48,.48,0,0,0),(10.8,.22,.22,0,0,0)],16)
        # A continuous closed-section C curl, with one end visibly meeting the neck.
        points=[(0,10.7,0),(-.75,10.6,-.20)]
        for i in range(45):
            t=math.radians(130+290*i/44)
            points.append((1.58*math.cos(t),8.9+1.65*math.sin(t),.40*math.cos(t)))
        accent.tube(points,[.19]*2+[.20-.15*(i/44)**5 for i in range(45)],10)
        # Restrained axial ridge, not cracks pretending to be geometry.
        edge.tube([(0,.13,.026),(0,2.2,.25),(0,4.5,.65),(0,6.9,1.055),
                   (0,8.6,.915),(0,9.7,.49),(0,10.7,.23)],.023,6)
    # Compact genuinely solid vanes concentric with the same rod as the head.
    for a in (0,math.tau/3,2*math.tau/3):
        if key=='shock':
            samples=[(49.4,.19,.055,.055,0),(51.0,.72,.22,.16,0),
                     (52.1,.42,.17,.14,0),(54.3,1.1,.28,.18,0),(56.3,1.28,.025,.025,0)]
            loft(tail,[(y,w,t,r*math.cos(a),r*math.sin(a),a) for y,r,w,t,_ in samples],4)
            edge.tube([(r*math.cos(a)-t*.97*math.sin(a),y,r*math.sin(a)+t*.97*math.cos(a)) for y,r,w,t,_ in samples],.021,6)
            continue
        elif key in ('ice','earth'):
            samples=[(49.4,.19,.055,.055,0),(52.0,.63,.30,.20,0),
                     (54.8,1.08,.27,.19,0),(56.3,1.22,.025,.025,0)]
            loft(tail,[(y,w,t,r*math.cos(a),r*math.sin(a),a) for y,r,w,t,_ in samples],5)
            edge.tube([(r*math.cos(a)-t*.97*math.sin(a),y,r*math.sin(a)+t*.97*math.cos(a)) for y,r,w,t,_ in samples],.021,6)
            continue
        elif key=='fire':
            samples=[(49.4,.19,.055,.055,0),(51.2,.63,.23,.16,-.10),
                     (53.7,1.14,.32,.22,.05),(56.2,.92,.025,.025,.22)]
        elif key=='poison':
            samples=[(49.4,.19,.055,.055,0),(51.9,.66,.31,.20,0),
                     (54.0,1.10,.41,.23,.05),(56.3,1.04,.025,.025,.12)]
        elif key=='wind':
            samples=[(49.4,.18,.055,.055,0),(51.4,.54,.24,.14,.15),
                     (54.3,1.15,.28,.18,.35),(56.3,.95,.025,.025,.50)]
        elif key=='water':
            samples=[(49.4,.18,.06,.06,0),(51.8,.66,.30,.19,.03),
                     (54.2,1.04,.35,.21,.08),(56.0,.88,.025,.025,.1)]
        else:
            samples=[(49.4,.19,.055,.055,0),(51.5,.66,.31,.17,0),
                     (55.3,1.18,.28,.17,0),(56.3,1.22,.025,.025,0)]
        petal(tail,samples,a,6);seam(edge,samples,a,.021)
    # Facet-edge seams on the straight spear models.
    if key in ('holy','dark','soul','arcane','wind','fire','ice','shock','poison'):
        core_angles=(0,math.pi/2,math.pi,3*math.pi/2) if key=='shock' else (0,math.tau/3,2*math.tau/3)
        for a in core_angles:
            if key in ('dark','soul','ice'):a+=.15
            if key=='arcane':path=[(.03,.13),(.82,7.85),(.82,8.15)]
            elif key=='soul':path=[(.025,.13),(1.08,4.9),(.88,7.9),(.23,10.7)]
            elif key=='holy':path=[(.025,.13),(.98,6.1),(.61,8.8),(.23,10.7)]
            elif key=='dark':path=[(.025,.13),(.74,6.8),(.42,9.4),(.23,10.7)]
            elif key=='fire':path=[(.025,.13),(.51,4.5),(.70,7.4),(.23,10.7)]
            elif key=='ice':path=[(.025,.13),(1.06,5.4),(.68,8.4),(.23,10.7)]
            elif key=='shock':path=[(.025,.13),(.69,5.7),(.44,8.7),(.23,10.7)]
            elif key=='poison':path=[(.025,.13),(.34,5.9),(.30,8.7),(.23,10.7)]
            else:path=[(.025,.13),(.40,3.7),(.54,6.8),(.23,10.7)]
            edge.tube([(r*math.cos(a),y,r*math.sin(a)) for r,y in path],.018,6)
    match_blood_scale(parts)
    return parts

def match_blood_scale(parts):
    """Match measured blood-arrow proportions without changing attachment length.

    Blood body shaft radius=.40, head envelope=2.496, tail envelope=2.685.
    Each family retains its silhouette; tail vanes begin near Y=46 and nock stays 58.
    """
    head_vertices=[v for name,mesh in parts.items() if name in ('head','accent','edge')
                   for v in mesh.verts if v[1]<20]
    tail_vertices=[v for name,mesh in parts.items() if name in ('tail','edge')
                   for v in mesh.verts if v[1]>40]
    head_scale=2.496/max(math.hypot(x,z) for x,y,z in head_vertices)
    tail_scale=2.685/max(math.hypot(x,z) for x,y,z in tail_vertices)
    for name,mesh in parts.items():
        scaled=[]
        for x,y,z in mesh.verts:
            if name=='shaft':
                x*=.40/.17;z*=.40/.17
            elif name=='trim':
                if y<20:
                    x*=2;z*=2
                elif y<55:
                    x*=2;z*=2;y=46+(y-49.4)*11/6.9
                else:
                    x*=2;z*=2
            elif name=='tail' or (name=='edge' and y>40):
                x*=tail_scale;z*=tail_scale;y=46+(y-49.4)*11/6.9
            else:
                x*=head_scale;z*=head_scale
            scaled.append((x,y,z))
        mesh.verts=scaled

if __name__=='__main__':
    write_textures()
    for key in KEYS:print(key,sum(len(p.tris) for p in generate(key).values()),'triangles')
