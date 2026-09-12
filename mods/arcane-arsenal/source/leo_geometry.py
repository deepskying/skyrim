"""Leo concept silhouettes: mane fans, flowing crest, crown frames, phantom blades.

All four center assemblies are authored separately; no common ornamental grip.
The tested hand datum and vanilla animation/string anchors remain unchanged.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import STRING_X,ANCHORS
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,49)
    if kind=='radiant_mane':
        strip([Vector((1.3+.4*y/5.6,float(y),0)) for y in ys],
              [1.0+1.0*(abs(y)/5.6)**1.7 for y in ys],2.8,.055,
              roll=[.30*math.sin(math.pi*y/11.2) for y in ys])
        # Recess-like triangular face outlines emphasize the hourglass.
        for sign in (-1,1):
            ring([Vector((-.1,sign*5,-1.55)),Vector((2.7,sign*5,-1.55)),
                  Vector((1.3,sign*1.7,-1.55))],.18,.35)
    elif kind=='flowing_crest':
        strip([Vector((1.3+.85*math.sin(y*math.pi/8),float(y),0)) for y in ys],
              [1.5+.5*(abs(y)/5.6)**2 for y in ys],2.6,.052)
    elif kind=='royal_bastion':
        strip([Vector((1.3,float(y),0)) for y in ys],
              [1.05+.65*(1-abs(y)/5.6) for y in ys],3.0,.055)
        # One split polygon guard, exclusively on the outside of the bow.
        angular([Vector((2.3,-5.5,0)),Vector((6.0,-3.0,0)),Vector((6.0,3.0,0)),
                 Vector((2.3,5.5,0))],[.45,.48,.48,.45],1.45)
    else:
        strip([Vector((1.3+.65*math.sin(y*math.pi/11.2),float(y),0)) for y in ys],
              [1.15+.8*(abs(y)/5.6)**2 for y in ys],2.65,.055,
              roll=[.60*math.sin(y*math.pi/8) for y in ys])
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        bulge={'radiant_mane':17,'flowing_crest':13,'royal_bastion':12,'phantom_mane':16}[kind]
        def spine(t):
            a,b,c,d=p(7.0,19),p(bulge,31),p(-7,end-4),p(STRING_X,end)
            return a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3
        def ribbon(ctrl,w0,wm,w1,depth=1.6,steps=42):
            strip(curve(ctrl,steps),[(1-t)*w0+t*w1+wm*math.sin(math.pi*t) for t in np.linspace(0,1,steps)],depth,.052)
        def collar(y,width=2.4):
            angular([p(1.3-width,y),p(1.3+width,y)],[.6,.6],2.8,.055)
        if kind=='radiant_mane':
            collar(5.8);collar(7.0,2.8)
            # Three open crown points stay above/below the grasp region.
            for side in (-1,1):
                blade([p(1.3+side*1.8,7),p(1.3+side*4.7,10.9),p(1.3+side*3.5,7.2)],1.5)
            ring([p(1.3,7),p(2.3,9.2),p(1.3,11.0),p(.3,9.2)],.37,1.4)
            angular([p(1.3,7.5),p(6.7,12),p(3.6,15.4),p(7,19)],
                    [1.0,1.05,1.15,1.25],1.9)
            ribbon([p(2.2,9.5),p(11.4,14),p(10.2,20.6),spine(.19)],.85,.45,1.15,1.7)
            ts=np.linspace(0,1,88)
            strip([spine(t) for t in ts],[1.3-1.0*t for t in ts],1.65,.052)
            # Five individually fanned broad mane rays, not a repeated saw edge.
            for j in range(5):
                y=10.5+j*2.5;base=p(5.8+j*.72,y)
                tip=p(15.5-j*.30,10+j*4.0,-.10*j)
                blade([base+p(-.5,-1),tip,base+p(1.4,2.5)],1.6)
            for t in (.34,.55,.74):
                a=spine(t);b=spine(min(.98,t+.20));r=3.0*(1-t)+.7
                blade([a+p(-.7,-.5),a+p(r,1.5),b+p(.8,.6),b+p(-.4,1.5)],1.4)
        elif kind=='flowing_crest':
            g=p(1.3+.85*math.sin(sign*5.6*math.pi/8),5.6)
            ribbon([g,p(7.5,8.5),p(1.8,14.5),p(7,19)],1.8,.25,1.5,1.8)
            if sign==1:
                # Single upper crest with one off-center diamond opening.
                ring([p(.4,8),p(4.8,11.8),p(3.7,16.2),p(-1.1,12.3)],.65,1.7)
                angular([p(-2.1,7.8),p(4.9,11.7)],[.65,.82],1.9)
                for j in range(3):
                    x=-1.3+j*1.5;y=8.0+j*1.15
                    ribbon([p(x,y),p(x-2,y+2.3),p(x-1.4,y+5),p(x-.3,y+5.9)],.78,.20,.055,1.3,30)
            else:
                # Lower swept cuff deliberately differs from the upper crown.
                blade([p(-1.1,6),p(4.8,8.2),p(5.1,13),p(.7,10.8)],1.8)
                angular([p(-1.1,6),p(-3.5,11),p(.7,10.8)],[.65,.12,.65],1.4)
            for side in (-1,0,1):
                ts=np.linspace(0,1,108)
                pts=[spine(t)+p(side*3.35*math.sin(math.pi*t),0,side*.9*math.sin(math.pi*t)) for t in ts]
                strip(pts,[1.0+.35*math.sin(math.pi*t)-.78*t for t in ts],1.5,.052)
        elif kind=='royal_bastion':
            collar(5.8,1.85);collar(7.1,1.65)
            # Open hexagonal crown arch with three strong geometric prongs.
            angular([p(-2.9,8.5),p(-3.0,12.4),p(1.3,15),p(5.6,12.4),p(5.5,8.5)],
                    [.8,1.0,1.05,1.0,.8],2.0)
            for side in (-1,1):
                blade([p(1.3+side*3.5,11.7),p(1.3+side*7.0,16.3),
                       p(1.3+side*6.0,11.8),p(1.3+side*4.4,9.0)],1.9)
            ring([p(1.3,14),p(2.4,17.4),p(1.3,20.3),p(.2,17.4)],.50,1.6)
            angular([p(1.3,7.2),p(2.0,11),p(7,19)],[.95,1.05,1.05],1.8)
            ts=np.linspace(0,1,100)
            strip([spine(t) for t in ts],[.95-.6*t for t in ts],1.5,.05)
            # Five large connected trapezoid frames, taper and rotate with curve.
            for j in range(5):
                t=j*.18;a=spine(t);b=spine(min(.995,t+.215))
                width=4.0*(1-t)+.3
                ring([a+p(-1,0),a+p(width,1.4),b+p(width*.62,-.7),b+p(-.75,.5)],
                     .65-.35*t,1.8-.55*t)
        else:
            collar(5.8,2.0)
            # Skew open diamond cages and swept Z shoulders, connected to palm.
            ring([p(1.3,6.5),p(7.2,11.6,.7),p(3.2,16.8,1),p(-2.1,12,-.5)],.75,1.7)
            blade([p(2.0,9.6,-1.3),p(3.0,11.8,-1.3),p(2.0,14,-1.3),p(1.0,11.8,-1.3)],1.1)
            angular([p(5.1,8.8),p(-.3,15.4),p(7,19)],[.62,.92,1.3],1.7)
            for side in (-1,1):
                blade([p(1.3+side*1.4,6.3),p(1.3+side*3.9,8.7),p(1.3+side*2.9,6.2)],1.2)
            ts=np.linspace(0,1,90)
            strip([spine(t) for t in ts],[1.1-.75*t for t in ts],1.7,.052)
            # Three deep rhomboid blades fan from different attachment stations.
            for j,t in enumerate((.03,.27,.53)):
                a=spine(t);b=spine(min(.99,t+.46));r=9.0-j*1.7;z=(j-1)*1.05
                ribbon([a+p(0,0,z),a+p(r,4,z),b+p(r*.6,-4,z),b],
                       .8,.85-j*.15,.055,1.65,62)
                angular([a,a+p(r*.7,3,z),b],[.55,.75,.06],1.1,.04)
        # A compact faceted bridge covers the butt joint between shoulder/limb.
        if kind in ('flowing_crest','phantom_mane'):
            c=p(7,19)
            blade([c+p(-.9,-.8),c+p(.9,-.8),c+p(1,1.0),c+p(-1,1.0)],1.75)
        tip=p(STRING_X,end,-.02)
        angular([spine(.955),tip,tip+p(-1.5,2.3)],[.58,.64,.045],1.3,.045)
        for j,t in enumerate((0,.20,.52)):
            c=(p(6,12) if j==0 else spine(t))+p(1.4,0,-2.4)
            weights=binding(c)
            direction={'radiant_mane':(1,sign*.2,0),'flowing_crest':(.3,sign,0),
                       'royal_bastion':(.8,sign*.3,0),'phantom_mane':(-.7,sign*.5,0)}[kind]
            anchors.append({'position':list(c),'bone':max(weights,key=weights.get),'side':sign,'direction':direction})
    return anchors
