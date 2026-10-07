"""Round-three solids: nine individual shafts and radial tail assemblies.

Blood, wind and water are deliberately excluded from generation and installation.
Coordinates retain the vanilla arrow attachment frame: tip Y=.07, nock Y=58.
"""
import math
from geometric_selected import Solid,petal,seam,bevel_square,PALETTE,LABELS
from redesign_geometry import loft
from paths import BUILD

VERSION='0.7.0'
KEYS=('fire','ice','shock','poison','holy','earth','dark','soul','arcane')
REMAINING=KEYS
STAGE='geometric-round03/data'

def texture_path(key,part):return 'textures\\magicarrows\\geometric05\\facets.dds'

def write_textures():
    # Identical neutral facet atlas; never overwrite a retained arrow's material.
    from geometric_selected import write_textures as old_textures
    import shutil
    old_textures()
    dst=BUILD/STAGE/'textures/magicarrows/geometric05/facets.dds'
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BUILD/'geometric-selected-05/data/textures/magicarrows/geometric05/facets.dds',dst)

def shader_values(key,part):
    dark,base,light=PALETTE[key]
    colors=dict(head=base,accent=base,edge=light,shaft=base,tail=base,trim=dark)
    if key in ('fire','poison','dark'):colors['shaft']=dark
    if key=='holy':colors.update(head=light,tail=light,shaft=light,trim=base,accent=base)
    if key in ('dark','arcane'):colors['accent']=dark
    return colors[part],1.85 if part=='edge' else 1.65

def axial(mesh,rings,sides=6):
    loft(mesh,[(y,r,r,0,0,twist) for y,r,twist in rings],sides)

def collar(mesh,y,r=.58,length=.40,sides=8):
    axial(mesh,[(y-length/2,.41,0),(y-length*.30,r,0),
                (y+length*.30,r,0),(y+length/2,.41,0)],sides)

def ridge(mesh,points,radius=.045):mesh.tube(points,radius,6)

def angular(mesh,edge,samples,phase,sides=4):
    """Piecewise linear cross-sections keep lightning and stepped fins angular."""
    loft(mesh,[(y,w,t,r*math.cos(phase),r*math.sin(phase),phase)
               for y,r,w,t in samples],sides)
    ridge(edge,[(r*math.cos(phase)-t*.97*math.sin(phase),y,
                 r*math.sin(phase)+t*.97*math.cos(phase)) for y,r,w,t in samples],.025)

def create_head(key,parts):
    head,accent,edge=parts['head'],parts['accent'],parts['edge']
    shapes={
        'fire':(6,[(.07,.025,0),(5.7,.83,0),(8.5,.66,0),(10.8,.40,0)]),
        'ice':(6,[(.07,.025,.15),(5.2,1.12,.15),(8.5,.62,.15),(10.8,.40,.15)]),
        'shock':(4,[(.07,.025,0),(5.4,.65,0),(8.8,.46,0),(10.8,.40,0)]),
        'poison':(3,[(.07,.025,0),(5.8,.45,0),(8.8,.36,0),(10.8,.40,0)]),
        'holy':(6,[(.07,.025,0),(6.0,.86,0),(8.7,.53,0),(10.8,.40,0)]),
        'earth':(8,[(.07,.025,.12),(6.4,1.32,.12),(8.6,1.32,.12),(9.0,.76,.12),(10.8,.40,.12)]),
        'dark':(3,[(.07,.025,.15),(6.8,.68,.15),(9.2,.45,.15),(10.8,.40,.15)]),
        'soul':(6,[(.07,.025,.15),(5.3,.98,.15),(8.0,.78,.15),(10.8,.40,.15)]),
        'arcane':(4,[(.07,.025,0),(7.5,.87,0),(8.4,.87,0),(10.8,.40,0)]),
    }
    sides,rings=shapes[key]
    axial(head,rings,sides)
    for j in range(sides):
        a=math.tau*j/sides
        ridge(edge,[(r*math.cos(a+t),y,r*math.sin(a+t)) for y,r,t in rings],.022)
    for j,a in enumerate((0,math.tau/3,2*math.tau/3)):
        if key=='fire':
            samples=[(3.2,1.35,.02,.02,0),(5.5,1.58,.28,.24,0),(7.5,1.08,.33,.26,0),(10.7,.31,.10,.10,0)]
        elif key=='ice':
            angular(accent,edge,[(5.9+j*.35,1.45,.025,.025),(8.1,1.10,.29,.27),(10.7,.31,.10,.10)],a,5)
            continue
        elif key=='shock':
            angular(accent,edge,[(4.0,1.57,.025,.025),(5.1,.85,.16,.16),(6.6,1.45,.20,.20),(7.6,.70,.14,.14),(9.2,1.12,.18,.18),(10.7,.31,.10,.10)],a)
            continue
        elif key=='poison':
            samples=[(5.1,.64,.02,.02,0),(6.7,1.35,.28,.22,0),(8.4,1.15,.32,.27,0),(10.7,.31,.10,.10,0)]
        elif key=='holy':
            samples=[(6.8,1.62,.02,.02,0),(7.5,1.45,.29,.22,0),(8.8,.97,.33,.24,0),(10.7,.31,.10,.10,0)]
        elif key=='earth':
            continue
        elif key=='dark':
            samples=[(5.6+j*.45,1.70,.02,.02,0),(7.1+j*.20,1.27,.23,.18,0),(8.9,.87,.28,.22,0),(10.7,.31,.10,.10,0)]
        elif key=='soul':
            samples=[(7.5,1.03,.02,.02,0),(8.3,.98,.19,.17,0),(9.4,.65,.26,.19,0),(10.7,.31,.10,.10,0)]
        else:
            angular(accent,edge,[(8.1,1.0,.025,.025),(8.7,1.0,.20,.18),(9.4,.70,.21,.18),(10.7,.31,.10,.10)],a)
            continue
        petal(accent,samples,a,6);seam(edge,samples,a,.025)

def create_shaft(key,parts):
    shaft,edge,trim=parts['shaft'],parts['edge'],parts['trim']
    # Separate rings at tail root let detail previews include the actual core.
    if key=='dark':
        rings=[(10.5+i*(46.7/72),.40,i*math.tau/72) for i in range(73)]
        axial(shaft,rings,3)
        for a in (0,math.tau/3,2*math.tau/3):
            ridge(edge,[(.399*math.cos(a+t),y,.399*math.sin(a+t)) for y,r,t in rings],.032)
    elif key=='arcane':
        bevel_square(shaft,[(10.5,.30),(46,.30),(57.2,.30)])
        for x,z in ((.30,.216),(-.30,-.216),(.216,-.30),(-.216,.30)):
            ridge(edge,[(x,10.5,z),(x,46,z),(x,57.2,z)],.024)
    else:
        axial(shaft,[(10.5,.40,0),(46,.40,0),(57.2,.40,0)],6 if key!='earth' else 8)
    if key in ('fire','poison'):
        turns=1.5 if key=='fire' else 1.15
        for a in (0,math.tau/3,2*math.tau/3):
            rings=[];pts=[]
            for i in range(97):
                t=i/96;y=10.7+35.0*t;angle=a+t*turns*math.tau
                # Broad, closed raised ribs intersect the core rather than float.
                width=.115 if key=='fire' else .105+.025*math.sin(t*math.tau*2)
                rings.append((y,.11,width,.385*math.cos(angle),.385*math.sin(angle),angle))
                pts.append((.492*math.cos(angle),y,.492*math.sin(angle)))
            loft(edge if key=='fire' else parts['accent'],rings,6)
            ridge(edge,pts,.024)
    elif key=='ice':
        for a in (0,math.tau/3,2*math.tau/3):
            ridge(edge,[(.399*math.cos(a),y,.399*math.sin(a)) for y in (10.7,46,57.2)],.032)
        for y in (17.5,27.5,37.5):
            axial(parts['accent'],[(y-1.5,.39,.15),(y-.7,.59,.15),(y+.55,.55,.15),(y+1.5,.39,.15)],6)
    elif key=='shock':
        for a in (0,math.tau/3,2*math.tau/3):
            pts=[]
            for i in range(31):
                y=10.7+35*i/30;tang=.16 if i%2 else -.16
                pts.append((.34*math.cos(a)-tang*math.sin(a),y,.34*math.sin(a)+tang*math.cos(a)))
            ridge(edge,pts,.068)
    elif key=='holy':
        for y in (16.4,24.2,32,39.8):collar(trim,y,.56,.70,6)
        for a in (0,math.tau/3,2*math.tau/3):
            ridge(edge,[(.398*math.cos(a),y,.398*math.sin(a)) for y in (10.7,46,57.2)],.025)
    elif key=='earth':
        for y in (16.8,24.6,32.4,40.2):
            axial(parts['accent'],[(y-2.5,.39,.12),(y-1.1,.63,.12),(y+1.0,.63,.12),(y+2.5,.39,.12)],8)
    elif key=='soul':
        for a in (0,math.tau/3,2*math.tau/3):
            # Three integrated longitudinal rails, shallowly seated in the prism.
            ridge(edge,[(.38*math.cos(a),y,.38*math.sin(a)) for y in (10.7,46,57.2)],.072)
        for y in (22.6,36.2):collar(trim,y,.58,.65,6)
    elif key=='arcane':
        for y in (19.5,30,40.5):collar(trim,y,.57,.75,8)

def create_tail(key,parts):
    tail,edge=parts['tail'],parts['edge']
    for j,a in enumerate((0,math.tau/3,2*math.tau/3)):
        if key=='fire':
            samples=[(46,.34,.08,.08,0),(49.8,1.25,.38,.24,0),(53,2.15,.48,.30,0),(56.7,1.70,.025,.025,0)]
        elif key=='ice':
            angular(tail,edge,[(46,.34,.08,.08),(49.7+j*.40,.96,.28,.23),(53.6+j*.25,1.98,.38,.25),(56.4-j*.32,2.2,.025,.025)],a,5)
            continue
        elif key=='shock':
            angular(tail,edge,[(46,.34,.08,.08),(49,1.0,.28,.24),(50.3,.65,.23,.22),(52.4,1.95,.34,.26),(53.6,1.45,.26,.24),(56.6,2.1,.025,.025)],a)
            continue
        elif key=='poison':
            samples=[(46,.34,.08,.08,0),(49.5,1.45,.37,.27,0),(52.9,2.13,.37,.29,0),(55.1,1.65,.28,.20,0),(56.7,.88,.025,.025,0)]
        elif key=='holy':
            # Two tapered branches per radial vane make a restrained crown fan.
            samples=[(46,.34,.08,.08,0),(49.3,1.0,.39,.26,0),(53.4,1.9,.50,.30,0),(56.5,2.02,.025,.025,0)]
            extra=[(50.0,.47,.08,.08,0),(53.0,.88,.25,.20,0),(56.3,1.15,.025,.025,0)]
            petal(tail,extra,a,6);seam(edge,extra,a,.027)
        elif key=='earth':
            angular(tail,edge,[(46,.34,.08,.08),(49.2,.97,.44,.30),(50.2,1.58,.44,.30),(54.0,1.92,.40,.30),(54.7,1.37,.34,.26),(56.7,.60,.08,.08)],a,4)
            continue
        elif key=='dark':
            samples=[(46,.34,.08,.08,0),(49.5,1.35,.25,.22,0),(52.6,2.18,.30,.25,0),(55.0,1.90,.20,.17,0),(56.7,1.1,.025,.025,0)]
        elif key=='soul':
            # Spindle crystals have substantial radial/tangential volume.
            angular(tail,edge,[(46,.34,.08,.08),(49.9,1.07,.33,.30),(53,1.75,.55,.44),(55,1.60,.40,.33),(56.7,.94,.025,.025)],a,6)
            continue
        else:
            angular(tail,edge,[(46,.34,.08,.08),(49.1,1.16,.31,.24),(50.1,1.16,.31,.24),(50.8,1.83,.32,.25),(53.8,1.83,.32,.25),(54.6,2.22,.20,.22),(56.7,2.26,.025,.025)],a,4)
            continue
        petal(tail,samples,a,6);seam(edge,samples,a,.027)

def normalize_envelope(parts):
    # Only radial scaling of heads/vanes. Core, attachments and total length stay fixed.
    for names,low,high,target in ((('head','accent','edge'),0,11,2.496),(('tail','edge'),45.8,57.1,2.685)):
        vs=[v for name in names for v in parts[name].verts if low<=v[1]<=high]
        scale=target/max(math.hypot(x,z) for x,y,z in vs)
        for name in names:
            parts[name].verts=[(x*scale,y,z*scale) if low<=y<=high else (x,y,z) for x,y,z in parts[name].verts]

def generate(key):
    if key not in KEYS:raise ValueError(key)
    parts={name:Solid() for name in ('head','accent','edge','shaft','tail','trim')}
    create_head(key,parts);create_tail(key,parts)
    normalize_envelope(parts);create_shaft(key,parts)
    for y in (10.65,46.15):collar(parts['trim'],y,.56,.55)
    collar(parts['trim'],57.12,.50,.45)
    for x in (-.24,.24):parts['trim'].tube([(x,57.15,0),(x,57.94,0)],[.18,.12],8)
    return parts

if __name__=='__main__':
    write_textures()
    for key in KEYS:print(key,sum(len(p.tris) for p in generate(key).values()),'triangles')
