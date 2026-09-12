"""Libra: revised red/green/blue concepts and the selected original purple.

Continuous grasps, sweeping solid-light surfaces, and separate authored shoulder
and limb profiles; no reuse of Virgo's frame-based centers.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import ANCHORS,STRING_X
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    def grasp(y):
        if kind=='jade_flow':return 1.3+.55*math.sin(y*math.pi/6)
        if kind=='paradox_weave':return 1.3+.18*math.sin(y*math.pi/6)
        return 1.3
    ys=np.linspace(-5.6,5.6,49)
    if kind=='suspended_blades':
        widths=[1.15+.65*(abs(y)/5.6)**2 for y in ys];roll=None
    elif kind=='jade_flow':
        widths=[1.50+.25*(abs(y)/5.6) for y in ys];roll=[.35*math.sin(y*math.pi/11.2) for y in ys]
    elif kind=='folded_current':
        widths=[1.20+.75*(1-abs(y)/5.6) for y in ys];roll=None
    else:
        widths=[1.55+.25*(abs(y)/5.6)**2 for y in ys];roll=[1.25*y/5.6 for y in ys]
    strip([Vector((grasp(y),float(y),0)) for y in ys],widths,2.7,.055,roll=roll)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def ribbon(ctrl,start,bulge,finish,depth=1.6,steps=64):
            strip(curve(ctrl,steps),[start*(1-t)+finish*t+bulge*math.sin(math.pi*t) for t in np.linspace(0,1,steps)],depth,.052)
        g=p(grasp(sign*5.5),5.5);join=p(6.8,18);tip=p(STRING_X,end)
        def spine(t):
            a,b,c,d=join,p(14.5,29),p(-3.5,end-6),tip
            return a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3
        if kind=='suspended_blades':
            # Angular slit shoulders taper directly into two sweeping blade wings.
            ribbon([g,p(1.6,8.2),p(6.0,9.8),p(7.2,11.0)],1.65,.20,1.25)
            ribbon([p(7.2,11),p(3.2,14.0),p(4.7,16.5),join],1.25,.40,1.5)
            ribbon([g,p(.9,9),p(-1.6,13.0),join],1.35,.60,1.45)
            for side in (-1,1):
                ts=np.linspace(0,1,130)
                pts=[];sizes=[]
                for t in ts:
                    # A single over-under exchange, unlike the purple multi-cross weave.
                    offset=side*3.2*math.sin(2*math.pi*t)
                    pts.append(spine(t)+p(offset,0,side*.85*math.sin(math.pi*t)))
                    sizes.append(.35+1.60*math.sin(math.pi*t)**.8+.9*(1-t))
                strip(pts,sizes,1.55,.055)
        elif kind=='jade_flow':
            # Teardrop negative-space cutouts grow out of an S-shaped grasp.
            ribbon([g,p(g.x+.1,8.3),p(5.8,8.1),p(5.4,11.4)],1.6,.15,.95)
            ribbon([p(5.4,11.4),p(5.0,14.2),p(3.0,15.3),join],.95,.55,1.7)
            ribbon([g,p(-1.3,9),p(-.6,13.5),join],1.35,.20,1.5)
            # Three flowing surfaces; broad outer arc, slender inner bands.
            for rail in range(3):
                ts=np.linspace(0,1,130);pts=[];sizes=[]
                for t in ts:
                    offset=(rail-1)*5.2*math.sin(math.pi*t)
                    pts.append(spine(t)+p(offset,0,(rail-1)*.25*math.sin(math.pi*t)))
                    sizes.append((1.30 if rail==2 else .85)*(1-t)+.28+
                                 (1.05 if rail==2 else .25)*math.sin(math.pi*t))
                strip(pts,sizes,1.55,.052)
        elif kind=='folded_current':
            # Oblique wraps avoid a detached, box-like hand guard.
            for y in (5.5,6.5):
                angular([p(-.3,y-.55,-.7),p(3.0,y+.45,-.7)],[.48,.48],2.0)
            angular([g,p(6.5,10.8,1),join],[1.25,2.1,1.5],1.7)
            angular([g,p(-.7,10.7,-.6),join],[1.2,1.25,1.4],1.55)
            # Broad outer folded band and two inner supports enclose triangular slits.
            a=join;b=p(13.7,26,1.0);c=p(5.4,40,-.8)
            angular([a,b,c,tip],[1.65,2.65,2.5,.25],1.7)
            angular([a,p(8.2,27,-.8),p(9.8,30,.6),b],[.8,.85,1.25,1.3],1.4)
            angular([c,p(3.3,43,1),p(-6.6,end-5),tip],[1.15,.9,.6,.25],1.4)
            ribbon([a,p(1.5,30,-1.1),p(-1.3,end-8,-1.1),tip],.8,.10,.22,1.2)
        else:
            # Selected original purple: compact diamond cradles and continuous braid.
            angular([g,p(4.0,7.0),p(5.6,10.5),p(1.3,13.4),join],
                    [1.5,1.1,.85,.85,1.3],1.65)
            angular([g,p(-1.4,9.4),p(1.3,13.4)],[1.4,.8,.85],1.55)
            blade([p(1.4,7.5),p(2.35,9.8),p(1.4,12),p(.45,9.8)],1.5)
            # Two ribbons weave in depth rather than occupy the same plane.
            for side in (-1,1):
                ts=np.linspace(0,1,150);pts=[];sizes=[]
                for t in ts:
                    envelope=math.sin(math.pi*t)**.6
                    offset=side*3.6*math.sin(3*math.pi*t)*envelope
                    z=side*1.35*math.cos(3*math.pi*t)*envelope
                    pts.append(spine(t)+p(offset,0,z))
                    sizes.append(1.15*(1-t)+.22+.95*math.sin(math.pi*t))
                strip(pts,sizes,1.5,.052,
                      roll=[side*.32*math.sin(3*math.pi*t) for t in ts])
        # Small overlapping faceted joints hide the meeting of authored surfaces.
        blade([join+p(-1,-1),join+p(1.2,-.6),join+p(.7,1.6),join+p(-.8,1)],1.9)
        blade([tip+p(0,-2),tip+p(1.0,0),tip+p(-1.1,2),tip+p(-.8,-.2)],1.5)
        for j,t in enumerate((.10,.45,.73)):
            c=spine(t)+p(-1.3,0,-2.6)
            weights=binding(c)
            direction={'suspended_blades':(-.6,sign*.8,0),'jade_flow':(.4,sign*.7,0),
                       'folded_current':(-.7,sign*.3,0),'paradox_weave':(.65,sign*.5,0)}[kind]
            anchors.append({'position':list(c),'bone':max(weights,key=weights.get),'side':sign,'direction':direction})
    return anchors
