"""Aquarius's four selected flowing-light silhouettes.

Continuous sampled ribbons retain broad faces through shoulder turns. Grips,
fans, ripple arcs and braided limbs are independently authored per concept.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import ANCHORS,STRING_X
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,53)
    if kind=='scarlet_cascade':
        gx=lambda y:1.3
        widths=[1.15+.48*(abs(y)/5.6)**2 for y in ys]
        rolls=[.28*y/5.6 for y in ys]
    elif kind=='jade_current':
        gx=lambda y:1.3+.45*math.sin(math.pi*y/6)
        widths=[1.2+.38*math.cos(math.pi*y/5.6) for y in ys]
        rolls=[.65*y/5.6 for y in ys]
    elif kind=='azure_ripple':
        gx=lambda y:1.3
        widths=[1.05+.85*math.sin(math.pi*(y+5.6)/11.2) for y in ys]
        rolls=None
    else:
        gx=lambda y:1.3+.18*math.sin(math.pi*y/6)
        widths=[1.3+.38*(abs(y)/5.6)**2 for y in ys]
        rolls=[1.15*y/5.6 for y in ys]
    strip([Vector((gx(y),float(y),0)) for y in ys],widths,2.8,.052,roll=rolls)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def sweep_chain(segments,sizes,depth=1.8,roll=None):
            # Share stations across adjacent Beziers; no mismatched end caps.
            pts=[];ws=[]
            for i,(controls,size) in enumerate(zip(segments,sizes)):
                count=max(28,int(sum((b-a).length for a,b in zip(controls,controls[1:]))*1.6))
                ts=np.linspace(0,1,count)
                ps=curve(controls,count)
                w0,bulge,w1=size
                if i:ps=ps[1:];ts=ts[1:]
                pts.extend(ps);ws.extend(w0*(1-t)+w1*t+bulge*math.sin(math.pi*t) for t in ts)
            strip(pts,ws,depth,.052,roll=roll)
            return pts
        def ribbon(ctrl,w0,bulge,w1,depth=1.8):
            return sweep_chain([ctrl],[(w0,bulge,w1)],depth)
        g=p(gx(sign*5.5),5.5);tip=p(STRING_X,end)
        if kind=='scarlet_cascade':
            # Three joined pouring folds at each end of a narrow grasp.
            for dx in (-4.0,0,4.0):
                ribbon([g,p(1.3+dx*.3,7,-.4),p(1.3+dx,9,-.6),p(1.3+dx,10.5,-.6)],.50,.35,.70,1.65)
            angular([p(-.55,5.5),p(3.15,5.5)],[.3,.3],2.85)
            j=p(10.8,19);k=p(8,35)
            sweep_chain([[g,p(2,12),p(13.8,14),j],
                         [j,p(7.8,24),p(12,29),k],
                         [k,p(4,41),p(-4,46),tip]],
                        [(1.45,.75,2.5),(2.5,.6,2.65),(2.65,.9,.16)],1.85)
            # Inner return bends independently while rejoining at both ends.
            j2=p(1.2,21);k2=p(1.0,35)
            sweep_chain([[g,p(-4,12),p(-2,16),j2],
                         [j2,p(4.4,26),p(-1,30),k2],
                         [k2,p(3,40),p(-7,48),tip]],
                        [(.70,.1,.9),(.9,.1,.72),(.72,.1,.14)],1.2)
            marks=[p(10,19,-2.6),p(8,33,-2.6),p(-1,45,-2.6)]
        elif kind=='jade_current':
            # Main broad stream and one teardrop return. Both follow a continuous S.
            a=p(11.5,23);b=p(1.0,42)
            sweep_chain([[g,p(-1,12),p(11.5,15),a],
                         [a,p(11.5,31),p(6,34),b],
                         [b,p(-4,50),p(-15,end-6),tip]],
                        [(1.6,.50,2.5),(2.5,.4,1.7),(1.7,.35,.2)],1.9)
            ribbon([p(3.6,11.5),p(-2.7,25),p(1.5,29),p(5.0,35.5)],.50,.65,.6,1.3)
            # A narrow surface flows around the shoulder into the main grasp.
            ribbon([g,p(4,8),p(-.2,10),p(3.6,11.5)],.55,.2,.75,1.6)
            # Both fish-tail blades share their root at the string seat.
            ribbon([tip,p(-10.8,end+1.8),p(-12,end+3.5),p(-14,end+5)],.65,.5,.018,1.4)
            ribbon([tip,p(-12,end+1.5),p(-10,end+2.2),p(-10.1,end+3.7)],.55,.25,.018,1.3)
            marks=[p(10,23,-2.6),p(6,34,-2.6),p(-5,46,-2.6)]
        elif kind=='azure_ripple':
            # Pouring-lip shoulder with an open semicircle and oval prism palm.
            j=p(7.8,17)
            sweep_chain([[g,p(-5,8),p(-3,13),j],
                         [j,p(18.6,21),p(21,39),tip]],
                        [(1.55,.65,2.8),(2.8,1.8,.20)],2.0)
            ribbon([g,p(3.5,8),p(.8,12),p(5.8,15.8)],.48,.35,.7,1.4)
            angular([p(-.4,5.65),p(3.0,5.65)],[.32,.32],2.9)
            # Nested inner ripple arcs, following the selected image's open layout.
            ripple=ribbon([j,p(-3,28),p(3,42),tip],.58,.10,.20,1.2)
            # Sample the existing arc for endpoints so neither ripple floats.
            a=ripple[round(.15*(len(ripple)-1))]
            b=ripple[round(.65*(len(ripple)-1))]
            ribbon([a,p(14,28),p(11.5,34),b],.55,.55,.50,1.35)
            marks=[p(11,22,-2.7),p(12,32,-2.7),p(1,43,-2.7)]
        else:
            # Wide interwoven streams; they physically meet at roots and crossings.
            n=181;ts=np.linspace(0,1,n)
            center=curve([g,p(24,15),p(8,43),tip],n)
            for side in (-1,1):
                pts=[];sizes=[];roll=[]
                for t,c in zip(ts,center):
                    spread=side*3.7*math.sin(2*math.pi*t)*math.sin(math.pi*t)
                    z=side*.50*math.sin(math.pi*t)*math.sin(2*math.pi*t)
                    pts.append(c+p(spread,0,z))
                    sizes.append(1.15*(1-t)+.16+.90*math.sin(math.pi*t))
                    roll.append(side*.15*math.sin(2*math.pi*t))
                strip(pts,sizes,1.9,.052,roll=roll)
            # A slanted overlap follows the braid into the rolled palm surface.
            blade([p(-.8,4.9),p(3.2,4.9),p(5.3,7.5),p(1.0,7.4)],2.4)
            # Small crescent crest is rooted in the shoulder, not a floating charm.
            root=p(4.1,8.5)
            ribbon([root,p(-1,18),p(-6,14.5),p(-8,12)],1.15,.7,.015,1.6)
            marks=[p(10,18,-2.8),p(11,31,-2.8),p(-1,44,-2.8)]
        if kind!='jade_current':
            # Compact recurve with a tapered luminous lip.
            ribbon([tip,p(-11.0,end+1.2),p(-12,end+3.2),p(-13.3,end+4.8)],.62,.4,.016,1.45)
        blade([tip+p(-.6,-.7),tip+p(.7,-.7),tip+p(.45,.65),tip+p(-.45,.65)],1.35)
        for pos in marks:
            w=binding(pos)
            direction=(.1,-sign,0) if kind=='scarlet_cascade' else (.45,sign*.65,0)
            anchors.append({'position':list(pos),'bone':max(w,key=w.get),'side':sign,'direction':direction})
    return anchors
