"""Visual 3: distinct elemental energy silhouettes, with no physical metal shell.

Blood remains byte-identical. Tip Y=0, nock Y=58; all new surfaces are emissive.
"""
import math
from geometry import Mesh,generate
from redesign_geometry import loft,ribbon,crystal,smooth_samples

VERSION='4.1.0'
KEYS=('fire','ice','shock','poison','holy','wind','water','earth','dark','soul','arcane')

def emission(spec,category):
    if spec['key']=='shock':
        from shock_arrow_redesign import shader_values
        return shader_values(spec['key'],category)
    if spec['key'] in ('fire','holy','arcane','poison','ice'):
        from five_arrow_redesign import shader_values
        return shader_values(spec['key'],category)
    if spec['key']!='blood':
        from luminous_v4 import shader_values
        return shader_values(spec['key'],category)
    # Match the approved blood shader's brightness on the full arrow surface.
    if category=='core':return spec['core'],1.85
    if category=='accent':return tuple(.25+.75*c for c in spec['color']),1.5
    if category=='crystal':return tuple(.72*c for c in spec['color']),1.35
    return spec['color'],1.35

def ring(mesh,y,radius,thickness=.065,sides=40):
    mesh.tube([(radius*math.cos(t),y,radius*math.sin(t))
               for t in [i*math.tau/sides for i in range(sides+1)]],thickness,5)

def line(mesh,samples,phase=0,radius=.055):
    mesh.tube([(r*math.cos(a+phase),y,r*math.sin(a+phase))
               for y,r,w,t,a in smooth_samples(samples)],radius,5)

def shard(mesh,rings,phase=0,sides=6):
    transformed=[]
    for y,rx,rz,x,z,a in rings:
        transformed.append((y,rx,rz,x*math.cos(phase)-z*math.sin(phase),
                            x*math.sin(phase)+z*math.cos(phase),a+phase))
    loft(mesh,transformed,sides,.12,True)

def tails(parts,key):
    body,accent,core,gem=(parts[k] for k in ('body','accent','core','crystal'))
    phases=(0,math.tau/3,math.tau*2/3)
    if key=='arcane':
        # Hollow triangular tail cage, not three feather blades.
        for y,r in ((49,1.55),(55.5,.92)):
            points=[(r*math.cos(a),y,r*math.sin(a)) for a in phases]
            accent.tube(points+[points[0]],.07,5)
        for a in phases:
            body.tube([(.32*math.cos(a),47,.32*math.sin(a)),
                       (1.55*math.cos(a),49,1.55*math.sin(a)),
                       (.92*math.cos(a),55.5,.92*math.sin(a)),
                       (.25*math.cos(a),57,.25*math.sin(a))],.09,6)
        return
    if key=='holy':
        # Two coronas with narrow light spokes, readily distinct in the quiver.
        ring(accent,50.5,1.45,.11);ring(core,54.8,.82,.055)
        for a in phases:
            body.tube([(.28*math.cos(a),48,.28*math.sin(a)),
                       (1.45*math.cos(a),50.5,1.45*math.sin(a)),
                       (.25*math.cos(a),56.5,.25*math.sin(a))],.10,5)
        return
    if key=='soul':
        for a in phases:
            shard(gem,[(49.3,.025,.025,1.1,0,0),(52.4,.50,.30,1.3,0,.1),
                       (55.8,.15,.14,.75,0,.05)],a)
            core.tube([(.25*math.cos(a),49,.25*math.sin(a)),
                       (1.1*math.cos(a),49.3,1.1*math.sin(a))],.035,5)
        return
    outlines={
        'fire':[(48,.30,.025,.04,0),(50.5,1.5,.52,.14,.12),
                (53.1,1.28,.38,.12,.26),(56.5,.33,.025,.025,.55)],
        'ice':[(48.5,.35,.025,.03,0),(52.8,1.5,.55,.12,0),
               (56.4,.36,.025,.025,0)],
        'shock':[(48,.35,.025,.03,0),(50.3,1.72,.36,.11,0),
                 (51.1,.87,.14,.10,0),(53.2,1.55,.32,.10,0),
                 (56.2,.33,.025,.025,0)],
        'poison':[(49,.35,.04,.04,0),(51,1.25,.44,.20,.12),
                  (54,1.03,.50,.22,.2),(56.5,.32,.025,.025,.25)],
        'wind':[(48,.35,.025,.03,0),(50,1.1,.22,.10,.35),
                (53,1.4,.25,.12,1.0),(56.5,.35,.03,.04,1.5)],
        'water':[(48.3,.35,.025,.03,0),(50,1.18,.30,.12,.1),
                 (52,1.50,.52,.13,.3),(54.4,1.05,.3,.10,.08),
                 (56.5,.35,.025,.025,0)],
        'earth':[(49,.4,.10,.12,0),(49.3,1.10,.65,.20,0),
                 (53.9,1.10,.65,.20,0),(54.2,.4,.10,.12,0)],
        'dark':[(48.8,.3,.025,.03,0),(50.8,1.30,.3,.15,.10),
                (54.2,1.15,.26,.14,.18),(55.8,1.7,.025,.025,.24)],
    }
    for a in phases:
        ribbon(gem if key in ('ice','earth') else body,outlines[key],a)
        line(accent,outlines[key],a,.045)

def common(parts,key):
    body,accent,core,gem=(parts[k] for k in ('body','accent','core','crystal'))
    # Full shaft emission is explicit; it does not depend on thin surface seams.
    body.tube([(0,11,0),(0,57.7,0)],.29,8)
    core.tube([(0,57.6,0),(0,58,0)],.17,6)
    body.tube([(0,9.8,0),(0,11.5,0)],[.24,.31],8)
    if key in ('ice','earth'):
        for y in (17,25,33,41):
            ring(accent,y,.34,.04,6 if key=='ice' else 4)
    elif key in ('fire','poison'):
        for y in (18,28,38,46):
            crystal(gem,y-.65,y+.65,.36,.31)
    elif key=='shock':
        core.tube([(.29 if i%2==0 else -.29,14+i*2,.31) for i in range(17)],.035,4)
    elif key=='water':
        core.tube([(.28*math.sin(i*.3),13+i*.85,.31) for i in range(41)],.025,4)
    elif key=='wind':
        core.tube([(.31*math.cos(i*.14),13+i*.85,.31*math.sin(i*.14)) for i in range(41)],.025,4)
    elif key=='holy':
        for x in (-.31,.31):accent.tube([(x,14,0),(x,47,0)],.035,4)
    elif key=='arcane':
        for y in (18,29,40):ring(accent,y,.40,.035,3)
    elif key=='soul':
        for y in (19,31,43):crystal(gem,y-.4,y+.4,.34,.31)
    tails(parts,key)

def redesigned(key):
    if key=='blood':return {k:v for k,v in generate(key).items() if k!='aura'}
    parts={k:Mesh() for k in ('body','accent','crystal','core')}
    common(parts,key)
    body,accent,gem,core=(parts[k] for k in ('body','accent','crystal','core'))
    if key=='fire':
        # Off-axis, curling flame tongue. No central spear or paired barbs.
        rings=[(.05,.025,.025,-.40,0,0),(2.1,.34,.22,-.12,0,.10),
               (4.3,.70,.39,.78,0,.22),(6.9,.73,.43,.40,0,.35),
               (9,.44,.31,-.25,0,.15),(11,.24,.23,0,0,0)]
        loft(body,rings,7)
        ribbon(accent,[(3.2,.65,.025,.025,.18),(5.2,1.7,.28,.18,.12),
                       (8.3,1.1,.42,.23,.2),(10.5,.26,.15,.14,.3)])
        core.tube([(-.4,.12,.05),(-.12,2.1,.23),(.78,4.3,.42),
                   (.4,6.9,.46),(-.25,9,.35),(0,10.8,.25)],.06,5)
    elif key=='ice':
        # Very slender hexagonal icicle, with an uneven cluster at the base.
        shard(gem,[(.05,.025,.025,0,0,0),(6,.52,.48,.07,0,0),
                   (9,.72,.57,0,0,0),(11,.24,.23,0,0,0)])
        for a,tip in ((0,4.9),(2.2,6.2),(4.1,7.0)):
            shard(body,[(tip,.025,.025,1.45,0,.15),
                        (9.3,.35,.26,1.08,0,.13),(11,.20,.16,.18,0,0)],a)
        core.tube([(0,.12,.03),(0,6,.49),(0,9,.60),(0,10.8,.25)],.045,5)
    elif key=='shock':
        # A forked lightning bolt; the wide zigzags are the solid arrowhead.
        pts=[(0,.08,0),(.8,2.6,0),(-.65,4.4,0),(.9,6.4,0),(-.5,8.3,0),(0,11,0)]
        body.tube(pts,[.04,.30,.38,.45,.34,.25],4)
        core.tube([(x,y,z+.32) for x,y,z in pts],.065,5)
        accent.tube([(-1.25,2.7,0),(-.55,5.5,0),(.9,6.4,0)],[.03,.20,.22],4)
    elif key=='poison':
        # Two exposed fangs, an open gap, and no spear filling the centre.
        for phase,offset in ((0,0),(math.pi,1.65)):
            shard(body,[(.08+offset,.025,.025,1.17,0,.1),
                        (3.1+offset,.26,.22,1.49,0,.1),
                        (6.7+offset,.35,.28,.97,0,.1),
                        (10.8,.20,.17,.10,0,0)],phase,7)
            core.tube([(1.17*math.cos(phase),.18+offset,.03),
                       (1.49*math.cos(phase),3.1+offset,.25),
                       (.97*math.cos(phase),6.7+offset,.31),
                       (.10*math.cos(phase),10.8,.20)],.04,5)
        crystal(gem,8.8,10.9,.48,.39)
    elif key=='holy':
        # Sacred elongated halo with a small light needle, no winged broadhead.
        points=[(1.70*math.cos(t),6.9+3.8*math.sin(t),.28*math.cos(t))
                for t in [i*math.tau/72 for i in range(73)]]
        body.tube(points,.16,7)
        core.tube([(x*1.035,y,z+.10) for x,y,z in points],.035,5)
        shard(gem,[(.05,.025,.025,0,0,0),(2.8,.35,.31,0,0,0),
                   (4,.12,.12,0,0,0)],0,6)
        accent.tube([(0,3.6,0),(0,11,0)],.13,6)
        ring(accent,9.3,.56,.075,24)
    elif key=='wind':
        # One open corkscrew flight with a genuine empty centre.
        samples=[]
        for i in range(35):
            t=i/34
            samples.append((.1+10.8*t,.12+1.42*math.sin(math.pi*t),
                            .12+.12*math.sin(math.pi*t),.10,math.tau*1.4*t))
        ribbon(body,samples)
        line(core,samples,radius=.035)
        body.tube([(0,.06,0),(0,1.25,0)],[.025,.18],5)
    elif key=='water':
        # A round pear-shaped droplet, wide at the rear and curved at its tip.
        rings=[(.08,.025,.025,-.25,0,0),(2.5,.36,.31,-.05,0,0),
               (5.5,1.04,.85,.28,0,.12),(8.2,1.80,1.17,.18,0,.18),
               (9.5,1.39,1.07,.04,0,.2),(11,.24,.22,0,0,0)]
        loft(gem,rings,16)
        core.tube([(-.25,.18,.04),(-.05,2.5,.34),(.28,5.5,.90),
                   (.18,8.2,1.22),(.04,9.5,1.11),(0,10.8,.25)],.04,5)
        ribbon(accent,[(4.1,1.12,.025,.025,.05),(6.4,1.90,.21,.15,.10),
                       (8.8,1.35,.24,.14,.17),(10.8,.28,.06,.05,.22)])
    elif key=='earth':
        # Stepped chisel/spade with a broad cutting edge rather than a needle.
        shard(gem,[(.08,.88,.035,0,0,0),(2.5,1.45,.62,0,0,0),
                   (5.2,1.85,1.02,0,0,.06),(7.8,1.75,.94,.10,0,.02),
                   (8.2,.72,.56,0,0,0),(11,.25,.23,0,0,0)],0,4)
        shard(body,[(3.8,.025,.025,-1.94,0,0),(6.3,.43,.34,-1.55,0,.1),
                    (9.3,.16,.16,-.40,0,0)],0,5)
        core.tube([(-.62,.14,.07),(-.3,3.4,.63),(.2,5.8,1.05),
                   (-.28,7.8,.98),(0,10.5,.29)],.05,5)
    elif key=='dark':
        # A single curved crescent beak; asymmetry carries the identity.
        shard(body,[(.08,.025,.025,-.50,0,0),(2.9,.30,.26,.46,0,.15),
                    (5.7,.63,.43,1.47,0,.25),(8.8,.52,.38,.93,0,.2),
                    (11,.24,.22,0,0,0)],0,7)
        core.tube([(-.5,.18,.03),(.46,2.9,.29),(1.47,5.7,.46),
                   (.93,8.8,.41),(0,10.8,.24)],.055,5)
        # Isolated lower crescent accent, short and clearly separated.
        shard(gem,[(4.5,.025,.025,-.64,0,0),(6.9,.22,.15,-.88,0,.12),
                   (9.7,.08,.08,-.25,0,0)],0,5)
    elif key=='soul':
        # Short floating crystal cluster with three distinct separated shards.
        shard(gem,[(.08,.025,.025,.25,0,0),(3.5,1.02,.72,.30,0,.10),
                   (6.1,.65,.56,.20,0,.1)],0,6)
        for phase,tip in ((0,2.8),(math.pi,4.0),(math.pi/2,4.8)):
            shard(body,[(tip,.025,.025,1.62,0,.1),(tip+1.5,.31,.24,1.49,0,.15),
                        (8.1,.14,.12,.97,0,.05)],phase,5)
            core.tube([(.97*math.cos(phase),8.1,.97*math.sin(phase)),
                       (.20*math.cos(phase),10.7,.20*math.sin(phase))],.035,5)
        core.tube([(.25,.2,.04),(.30,3.5,.76),(.20,6.1,.60),
                   (0,10.6,.12)],.045,5)
    elif key=='arcane':
        # Open triangular pyramid cage with a floating rune core, no solid prism.
        phases=(0,math.tau/3,2*math.tau/3)
        perimeter=[(1.88*math.cos(a),6.8,1.88*math.sin(a)) for a in phases]
        accent.tube(perimeter+[perimeter[0]],.11,6)
        for a in phases:
            body.tube([(0,.08,0),(1.88*math.cos(a),6.8,1.88*math.sin(a)),
                       (.30*math.cos(a),11,.30*math.sin(a))],[.035,.13,.10],6)
        # A small suspended octahedron in the cage's empty middle.
        shard(gem,[(4.5,.025,.025,0,0,.2),(6.1,.58,.58,0,0,.2),
                   (7.7,.025,.025,0,0,.2)],0,4)
        core.tube([(0,.12,0),(0,4.55,0)],.055,5)
    else:raise ValueError(key)
    result={k:m for k,m in parts.items() if m.tris}
    for mesh in result.values():
        mesh.uv=[((math.atan2(z,x)/math.tau)%1,y/58) for x,y,z in mesh.verts]
    return result
