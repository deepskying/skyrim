"""Cancer: four separately authored grips, pincer shoulders and shell limbs.

Reference: art/concepts/cancer-four-colors-01. Keep the tested grip datum and
string anchors; express the illustrations as thick solid-light geometry.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import STRING_X,ANCHORS
from geometric_flow import curve,binding

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,49)
    if kind=='pincer_armor':
        pts=[Vector((1.3,float(y),0)) for y in ys]
        strip(pts,[1.12+1.0*(abs(y)/5.6)**2 for y in ys],2.8,.055)
        # Open trapezoid guards flank the palm without crossing its face.
        for side in (-1,1):
            angular([Vector((1.3+side*2.05,-5.5,0)),Vector((1.3+side*4.6,-4,0)),
                     Vector((1.3+side*3.9,0,0)),Vector((1.3+side*4.6,4,0)),
                     Vector((1.3+side*2.05,5.5,0))],[.42,.52,.46,.52,.42],1.5)
    elif kind=='tidal_ribbons':
        pts=[Vector((1.3+.8*math.sin(y*math.pi/11.2),float(y),0)) for y in ys]
        strip(pts,[1.65+.60*(abs(y)/5.6)**2 for y in ys],2.7,.05,
              roll=[.15*math.sin(y*math.pi/5.6) for y in ys])
    elif kind=='shell_bastion':
        pts=[Vector((1.3,float(y),0)) for y in ys]
        strip(pts,[1.45+.40*(1-abs(y)/5.6) for y in ys],3.0,.055)
    else:
        pts=[Vector((1.3+.25*math.sin(y*math.pi/5.6),float(y),0)) for y in ys]
        strip(pts,[1.45+.35*(abs(y)/5.6) for y in ys],2.65,.055,
              roll=[1.35*y/5.6 for y in ys])
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def spine(t):
            # One continuous recurve, even where broad shell layers overlap.
            a,b,c,d=p(7.5,17),p(16,27),p(-5,end-6),p(STRING_X,end)
            return a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3
        def ribbon(control,w0,wm,w1,depth=1.6,steps=42):
            points=curve(control,steps)
            strip(points,[(1-t)*w0+t*w1+wm*math.sin(math.pi*t) for t in np.linspace(0,1,steps)],depth,.052)
        if kind=='pincer_armor':
            for y in (5.5,7.0):
                blade([p(-1.2,y-.65),p(4.0,y-.65),p(4.0,y+.65),p(-1.2,y+.65)],2.4)
            angular([p(1.3,5.5),p(6.0,9.0),p(3.8,13.3),p(7.5,17)],
                    [1.7,2.0,1.5,1.4],2.2)
            # An open hooked jaw on the inside of each shoulder.
            ribbon([p(6.2,8.8),p(-4.9,11.0),p(-2.5,17.0),p(-.7,18.5)],1.55,.75,.06,1.8)
            ts=np.linspace(0,1,90)
            strip([spine(t) for t in ts],[1.3-.88*t for t in ts],1.8,.055)
            for i in range(6):
                t=.02+i*.145;c=spine(t);d=spine(min(1,t+.20))
                width=5.2*(1-t)+.65
                # Broad overlapping rhomboid shell plates, not tiny saw teeth.
                blade([c+p(-1.1,-.5),c+p(width,1.6),d+p(width*.35,-.2),d+p(-1.15,1.6)],1.75)
        elif kind=='tidal_ribbons':
            # Continuous shoulder loops expand out of the curved palm.
            g=p(1.3+sign*.8,5.5)
            ribbon([g,p(7.4,6.4),p(10.0,11.0),p(7.5,17)],1.8,.50,1.25,1.9)
            ribbon([g,p(-5.4,8),p(-1.2,15.0),p(7.5,17)],1.3,.42,1.05,1.7)
            ribbon([p(4.7,7.3),p(-3.3,3.8),p(-3.7,7.2),p(-2.1,9)],1.3,.2,.06,1.6)
            for side in (-1,1):
                ts=np.linspace(0,1,116);points=[]
                for t in ts:
                    offset=side*3.2*math.sin(math.pi*t)*math.sin(2*math.pi*t+.6)
                    points.append(spine(t)+p(offset,0,side*1.2*math.sin(math.pi*t)*math.cos(2*math.pi*t+.6)))
                strip(points,[1.3-.98*t for t in ts],1.65,.05)
            for t in (.22,.50,.76):
                c=spine(t)+p(0,0,-1.15);r=1.9*(1-t)+.55
                blade([c+p(0,-r*1.7),c+p(r,0),c+p(0,r*1.7),c+p(-r,0)],1.25)
        elif kind=='shell_bastion':
            for y in (5.8,7.5):
                angular([p(-1.4,y),p(4.0,y)],[.74,.74],3.2,.06)
            # Squared C pincers: asymmetric jaws flank the collar above the hand.
            angular([p(2.6,7.8),p(6.3,8.8),p(8.3,11.8),p(6.8,14.5)],
                    [1.05,1.4,1.3,.12],2.3)
            angular([p(-.4,7.8),p(-3.1,8.9),p(-4.6,11.7),p(-3.5,13.3)],
                    [.9,1.1,1.0,.10],2.0)
            angular([p(1.3,7.4),p(2.3,12.2),p(7.5,17)],[1.35,1.55,1.6],2.3)
            ts=np.linspace(0,1,90)
            strip([spine(t) for t in ts],[1.4-1.0*t for t in ts],2.0,.055)
            for t in (.03,.31,.60):
                a=spine(t);b=spine(min(.98,t+.37));r=5.3*(1-t)
                # Nested open shield outlines, joined at both ends to the spine.
                angular([a,a+p(r,3),b+p(r*.65,-3),b],[1.2,1.65*(1-t),1.45*(1-t),.18],2.0)
                blade([a+p(.6,0),a+p(r*.58,2.8),b+p(r*.35,-3),b+p(-.2,-1)],1.7)
        else:
            # Broad counter-rotating hook shoulders; twisted palm stays clear.
            for side in (-1,1):
                ribbon([p(1.3,5.5,side*.45),p(1.3+side*6.5,6.8,side*.9),
                        p(1.3+side*7.3,10.4,side*.8),p(1.3+side*3.0,13.3,0)],
                       1.35,.55,.07,1.65)
            ribbon([p(1.3,6.2),p(6.3,9),p(4.1,13),p(7.5,17)],1.25,.45,1.15,1.8)
            for side in (-1,1):
                ts=np.linspace(0,1,100)
                points=[spine(t)+p(side*4.0*math.sin(math.pi*t),0,side*1.5*math.sin(math.pi*t)) for t in ts]
                strip(points,[1.3+.30*math.sin(math.pi*t)-1.02*t for t in ts],1.65,.052)
            for t in (.20,.49,.76):
                c=spine(t);r=1.7*(1-t)+.6
                ring([c+p(0,-r*1.5),c+p(r,0),c+p(0,r*1.5),c+p(-r,0)],.32,1.0)
                angular([c+p(-4*math.sin(math.pi*t),0),c+p(4*math.sin(math.pi*t),0)],[.24,.24],.85,.035)
        tip=p(STRING_X,end,-.02)
        # Visible string attachment remains fixed, hook grows beyond it.
        ribbon([spine(.965),tip+p(2,1),tip+p(-.6,3),tip+p(-2,3.3)],.65,.20,.05,1.3,24)
        if kind in ('tidal_ribbons','eclipse_claws'):
            ribbon([spine(.95),tip+p(-3,-2),tip+p(-4.4,.3),tip+p(-3.6,1.5)],.8,.2,.05,1.2,24)
        for j,t in enumerate((0,.23,.57)):
            c=(p(1.3,10) if j==0 else spine(t))+p(-1.6,0,-2.6)
            w=binding(c)
            direction={'pincer_armor':(-.2,-sign,0),'tidal_ribbons':(1,sign*.25,0),
                       'shell_bastion':(-.25,sign,0),'eclipse_claws':(-1,sign*.3,0)}[kind]
            anchors.append({'position':list(c),'bone':max(w,key=w.get),'side':sign,'direction':direction})
    return anchors
