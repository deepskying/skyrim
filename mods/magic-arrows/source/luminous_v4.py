"""Nine flowing luminous arrow families; preserve blood, ice and holy."""
import math
from geometry import Mesh
from redesign_geometry import ribbon,loft,crystal,smooth_samples
VERSION='4.0.0'
KEYS=('fire','shock','poison','wind','water','earth','dark','soul','arcane')
PALETTE={
 'fire':((.70,.11,.025),(.95,.37,.06),(1,.72,.30)),
 'shock':((.20,.22,.65),(.41,.53,.90),(.65,.85,1)),
 'poison':((.10,.33,.09),(.29,.65,.12),(.70,.94,.29)),
 'wind':((.07,.37,.27),(.18,.66,.49),(.56,.96,.77)),
 'water':((.035,.29,.43),(.10,.57,.72),(.48,.90,1)),
 'earth':((.36,.16,.055),(.66,.37,.13),(.96,.68,.30)),
 'dark':((.16,.045,.29),(.39,.16,.57),(.74,.43,.90)),
 'soul':((.23,.14,.49),(.47,.32,.76),(.82,.68,1)),
 'arcane':((.34,.055,.31),(.70,.22,.55),(.97,.64,.86)),
}
def texture_path(key,part):return 'textures\\magicarrows\\solid.dds'
def shader_values(key,part):
    base,light,tip=PALETTE[key]
    return ({'body':base,'veil':light,'edge':tip,'core':tip}[part],1.8 if part=='core' else 1.5 if part=='edge' else 1.4)
def vein(mesh,samples,phase=0,radius=.035):
    points=[]
    for y,r,w,t,a in smooth_samples(samples):
        a+=phase;points.append((r*math.cos(a)-t*.75*math.sin(a),y,r*math.sin(a)+t*.75*math.cos(a)))
    mesh.tube(points,radius,5)
def leaf(mesh,edge,samples,phase=0):
    ribbon(mesh,samples,phase);vein(edge,samples,phase)
def point(mesh,width=.30,root=10.8):
    crystal(mesh,.06,root,width,width*.75)
def generate(key):
    if key not in KEYS:raise ValueError(key)
    parts={p:Mesh() for p in ('body','veil','edge','core')}
    body,veil,edge,core=(parts[p] for p in parts)
    # Continuous slender glow, with a gently wandering surface light vein.
    body.tube([(0,10.5,0),(0,57.7,0)],.20,10)
    edge.tube([(.205*math.cos(i*.07),11+i*.9,.205*math.sin(i*.07)) for i in range(51)],.018,5)
    body.tube([(0,9.9,0),(0,11.3,0)],[.23,.20],10)
    for x in (-.13,.13):veil.tube([(x,57.1,0),(x,57.95,0)],[.085,.06],6)
    if key=='fire':
        leaf(veil,core,[(.06,.10,.018,.02,-.15),(2.4,.45,.23,.12,-.10),(5.4,.70,.58,.24,.1),(8.3,.38,.43,.18,.2),(10.7,.20,.10,.08,.15)])
        for a,tip in ((math.pi,2.1),(math.pi/2,4.0)):
            leaf(body,edge,[(tip,1.2,.018,.02,.1),(5.8,1.16,.28,.13,.3),(8.4,.75,.38,.15,.1),(10.7,.20,.06,.06,0)],a)
    elif key=='shock':
        point(veil,.37)
        for a in (0,math.pi):
            leaf(body,core,[(1.8,.32,.018,.02,.1),(3.8,1.05,.21,.10,.1),(5.0,.66,.15,.09,.2),(6.8,1.35,.28,.13,.15),(9.3,.62,.22,.12,.2),(10.7,.20,.05,.04,0)],a)
    elif key=='poison':
        for a,tip in ((0,.08),(math.pi,1.35)):
            leaf(veil,core,[(tip,.43,.018,.02,0),(3.3,1.13,.20,.16,.04),(6.4,1.05,.37,.24,.16),(8.8,.55,.28,.17,.12),(10.7,.18,.08,.06,0)],a)
        crystal(body,7.6,10.7,.44,.34)
    elif key=='wind':
        point(core,.20)
        for a in (0,math.tau/3,math.tau*2/3):
            leaf(veil,edge,[(1.0,.15,.018,.02,-.4),(3.4,.88,.25,.09,-.1),(6.8,1.24,.39,.14,.6),(9.3,.68,.26,.10,1.1),(10.7,.18,.04,.04,1.25)],a)
    elif key=='water':
        loft(veil,[(.06,.02,.02,0,0,0),(2.6,.26,.23,.05,0,0),(5.8,.75,.62,.10,0,.08),(8.4,1.12,.80,.04,0,.1),(9.5,.78,.58,0,0,0),(10.7,.20,.19,0,0,0)],12)
        for a in (0,math.pi):
            leaf(body,core,[(2.8,.30,.018,.02,-.1),(5.4,1.14,.23,.10,.1),(8.3,1.40,.30,.14,.2),(10.7,.20,.04,.04,.15)],a)
    elif key=='earth':
        crystal(veil,.06,10.7,.88,.70,twist=.1)
        for a,tip in ((0,4.2),(2.1,5.3),(4.2,6.0)):
            loft(body,[(tip,.02,.02,1.10*math.cos(a),1.10*math.sin(a),a),(8,.28,.22,.74*math.cos(a),.74*math.sin(a),a),(10.6,.10,.10,.20*math.cos(a),.20*math.sin(a),a)],5,flat=True)
        vein(core,[(.12,0,.02,.02,0),(5.8,.68,.02,.02,0),(8.4,.49,.02,.02,0),(10.7,.20,.02,.02,0)])
    elif key=='dark':
        leaf(veil,core,[(.06,-.22,.018,.02,0),(2.8,.45,.24,.12,.04),(6.1,1.25,.52,.24,.12),(8.7,.92,.35,.19,.18),(10.7,.20,.06,.06,.1)])
        leaf(body,edge,[(4.5,.55,.018,.02,0),(6.8,1.0,.19,.12,.04),(9.0,.72,.25,.16,.1),(10.7,.20,.05,.05,0)],math.pi)
    elif key=='soul':
        crystal(veil,.06,10.7,.73,.52,twist=.18)
        for a,tip in ((0,3.1),(2.1,4.1),(4.2,5.0)):
            loft(body,[(tip,.02,.02,1.28*math.cos(a),1.28*math.sin(a),a),
                       (tip+1.7,.30,.24,1.19*math.cos(a),1.19*math.sin(a),a),
                       (9.8,.07,.07,.26*math.cos(a),.26*math.sin(a),a)],6,flat=True)
            edge.tube([(1.28*math.cos(a),tip,.05+1.28*math.sin(a)),
                       (1.19*math.cos(a),tip+1.7,.27+1.19*math.sin(a)),
                       (.26*math.cos(a),9.8,.08+.26*math.sin(a))],.026,5)
        core.tube([(0,.12,.025),(0,6.2,.54),(0,10.7,.22)],.025,5)
    elif key=='arcane':
        point(veil,.43)
        # Two narrow elliptical energy orbits cradle the core at different angles.
        for phase in (.3,1.8):
            pts=[]
            for i in range(49):
                t=math.tau*i/48;r=1.05*math.sin(t)
                pts.append((r*math.cos(phase),6.6+3.1*math.cos(t),r*math.sin(phase)))
            body.tube(pts,.11,6)
            edge.tube([(x*1.025,y,z*1.025) for x,y,z in pts],.023,5)
        core.tube([(0,.12,0),(0,10.7,0)],.05,6)
    # Curved feather-like energy vanes; widths and sweep distinguish each family.
    tails={
     'fire':[(48,.22,.018,.02,0),(50.6,1.10,.32,.10,.15),(53.4,1.27,.42,.15,.35),(56.6,.28,.02,.02,.55)],
     'shock':[(48,.22,.018,.02,0),(50.2,1.26,.21,.09,.12),(51.8,.83,.16,.10,.15),(54.3,1.32,.24,.11,.2),(56.6,.28,.02,.02,.2)],
     'poison':[(48.6,.24,.018,.02,0),(51.5,1.12,.39,.15,.06),(54,1.20,.37,.14,.18),(56.6,.28,.02,.02,.25)],
     'wind':[(48,.22,.018,.02,-.2),(50.8,1.02,.24,.09,.2),(53.8,1.30,.29,.11,.85),(56.6,.28,.02,.02,1.3)],
     'water':[(48,.22,.018,.02,0),(50.8,1.14,.37,.13,.05),(53.1,1.33,.44,.16,.22),(55,.88,.24,.11,.1),(56.6,.28,.02,.02,0)],
     'earth':[(48.6,.25,.025,.025,0),(51.2,.98,.40,.18,.08),(54,1.07,.43,.21,.1),(56.2,.28,.025,.025,0)],
     'dark':[(48.6,.22,.018,.02,0),(51,1.20,.33,.13,.12),(54.1,1.14,.31,.14,.22),(56.6,.60,.018,.02,.28)],
     'soul':[(48.4,.22,.018,.02,0),(51.5,1.27,.27,.13,.15),(53.7,1.16,.30,.14,.25),(56.5,.27,.02,.02,.1)],
     'arcane':[(48,.22,.018,.02,-.2),(51,1.15,.26,.11,.1),(54,1.24,.31,.12,.6),(56.5,.28,.02,.02,.9)],
    }
    for a in (0,math.tau/3,math.tau*2/3):leaf(veil,edge,tails[key],a)
    return {k:m for k,m in parts.items() if m.tris}
