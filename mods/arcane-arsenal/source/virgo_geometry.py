"""Four Virgo silhouettes authored from virgo-four-colors-01 concept sheets.

Grain lozenges, open loom, measured hexagons and folded kite bands retain a
continuous grasp and the proven vanilla string/skin coordinates.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import STRING_X,ANCHORS
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,49)
    if kind=='harvest_lozenges':
        strip([Vector((1.3,float(y),0)) for y in ys],
              [1.05+.95*(abs(y)/5.6)**2 for y in ys],2.8,.055)
    elif kind=='woven_loom':
        strip([Vector((1.3+.65*math.sin(y*math.pi/8),float(y),0)) for y in ys],
              [1.35+.7*(abs(y)/5.6)**1.6 for y in ys],2.65,.052,
              roll=[.25*math.sin(y*math.pi/11.2) for y in ys])
    elif kind=='crystalline_measure':
        strip([Vector((1.3+.35*y/5.6,float(y),0)) for y in ys],
              [1.3+.35*(1-abs(y)/5.6) for y in ys],2.9,.055)
        angular([Vector((2.7,-6.8,0)),Vector((6.0,-5.2,0)),Vector((6.0,5.2,0)),
                 Vector((2.7,6.8,0))],[.6,.7,.7,.6],1.65)
    else:
        strip([Vector((1.3+.25*math.sin(y*math.pi/6),float(y),0)) for y in ys],
              [1.35+.40*(abs(y)/5.6)**2 for y in ys],2.55,.052,
              roll=[1.5*y/5.6 for y in ys])
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def spine(t):
            bulge={'harvest_lozenges':14,'woven_loom':12,'crystalline_measure':10,'folded_silk':13}[kind]
            a,b,c,d=p(7,18),p(bulge,28),p(-5,end-5),p(STRING_X,end)
            return a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3
        def ribbon(ctrl,w0,wm,w1,depth=1.6,steps=40):
            strip(curve(ctrl,steps),[(1-t)*w0+t*w1+wm*math.sin(math.pi*t) for t in np.linspace(0,1,steps)],depth,.052)
        def collar(y,width=2.0):
            angular([p(1.3-width,y),p(1.3+width,y)],[.50,.50],2.7,.055)
        if kind=='harvest_lozenges':
            collar(5.8,2.1)
            ring([p(1.3,6.2),p(4.9,10.4),p(1.3,14.5),p(-2.3,10.4)],.67,1.75)
            blade([p(1.3,6.6,-.5),p(2.35,10.4,-.5),p(1.3,14,-.5),p(.25,10.4,-.5)],1.8)
            ring([p(1.3,13),p(6.8,15.5),p(7,21),p(2.6,18.0)],.66,1.55)
            ts=np.linspace(0,1,90)
            strip([spine(t) for t in ts],[1.0-.67*t for t in ts],1.5,.052)
            # Grain follows the local curve so outer plates do not stand upright.
            for j,t in enumerate((.02,.16,.30,.44,.58,.72,.86)):
                for side in (-1,1):
                    tt=t+(.04 if side==1 else 0);c=spine(tt)
                    along=(spine(tt+.01)-spine(tt-.01)).normalized()
                    normal=Vector((along.y*sign,-along.x*sign,0))
                    length=6.0*(1-tt)+2.2;width=3.0*(1-tt)+.9
                    blade([c-along*length*.45,c+normal*(side*width)+along*length*.1,
                           c+normal*(side*width*.7)+along*length,c+along*length*.45],1.45)
        elif kind=='woven_loom':
            g=p(1.3+.65*math.sin(sign*5.6*math.pi/8),5.5)
            ribbon([g,p(g.x+.6,9.0),p(2.5,12),p(7,18)],1.75,.15,1.2,1.85)
            if sign==1:
                frame=[p(-.9,8.5),p(6.5,10.0),p(7,18),p(-.3,15.6)]
                ring(frame,.82,1.75)
                angular([p(1.8,7.4),p(6.5,10.0)],[.80,.80],1.75)
                angular([p(-.8,10.5),p(6.8,14.7)],[.4,.4],1.15)
                angular([p(-.5,12.7),p(6.9,17.0)],[.4,.4],1.15)
            else:
                ribbon([g,p(g.x-1,8.8),p(-2.4,11.2),p(7,18)],1.25,.20,1.0,1.65)
                ring([p(1.9,10.2),p(5.5,12.5),p(6.9,17.5),p(1.7,14.5)],.50,1.2)
            for side in (-1,1):
                ts=np.linspace(0,1,96)
                strip([spine(t)+p(side*2.5*math.sin(math.pi*t),0) for t in ts],
                      [1.0-.67*t for t in ts],1.65,.052)
            for t in (.12,.39,.66):
                a=spine(t);b=spine(t+.23);mid=spine(t+.115)
                width=2.5*math.sin(math.pi*(t+.115))
                ring([a,mid+p(width,0),b,mid+p(-width,0)],.48-.19*t,1.35)
        elif kind=='crystalline_measure':
            # Stepped rhomboid collars anchor an outside grip brace.
            collar(5.8,1.7)
            blade([p(-1.4,6.8),p(1.3,5.9),p(4.0,6.8),p(1.3,8.6)],2.2)
            ring([p(-1.1,7.0,-1.1),p(1.3,6.3,-1.1),p(3.7,7.0,-1.1),p(1.3,8.4,-1.1)],.28,.65)
            angular([p(1.3,8.0),p(2.4,12),p(7,18)],[1.0,1.15,1.0],1.85)
            # Exactly three elongated hexagon windows, separated by short spines.
            for t0,t1 in ((0,.31),(.32,.65),(.66,.94)):
                a=spine(t0);b=spine(t1);d=(b-a).normalized();normal=Vector((d.y*sign,-d.x*sign,0))
                radius=2.8*(1-t0)+.55
                pts=[a,a.lerp(b,.22)+normal*radius,a.lerp(b,.78)+normal*radius,
                     b,a.lerp(b,.78)-normal*radius,a.lerp(b,.22)-normal*radius]
                ring(pts,.93-.40*t0,1.85)
                if t1<.94:angular([b,spine(t1+.025)],[.92,.92],1.65)
            angular([spine(.94),spine(1)],[.85,.30],1.4)
        else:
            # Folded shoulder kites flow from V collars into offset slit bands.
            angular([p(-1.1,6.1),p(1.3,7.4),p(3.7,6.1)],[.52,.72,.52],1.65)
            g=p(1.3,6.0);top=p(7,18)
            angular([g,p(7.4,9.2,1),p(9.7,14.0,1.4),top],[1.25,2.1,1.7,.9],1.65)
            angular([g,p(-1.6,10.1,-1),p(.2,14.1,-1.1),top],[1.0,1.65,1.5,.9],1.45)
            angular([p(-.7,8.5,-1.1),p(5.5,6.9,.9),p(8.9,11.7,1.1)],
                    [.15,.8,.12],1.35)
            for j,(t0,t1) in enumerate(((0,.35),(.34,.68),(.67,1))):
                a=spine(t0);b=spine(t1);middle=a.lerp(b,.48)
                spread=4.2*(1-t0)+.85;z=(1 if j%2==0 else -1)*1.05
                # Two broad folded sides leave an off-center long slit.
                angular([a,a.lerp(b,.27)+p(spread,0,z),a.lerp(b,.68)+p(spread*.72,0,z),b],
                        [.72,1.8-.5*t0,1.6-.5*t0,.45],1.55)
                angular([a,a.lerp(b,.34)+p(-spread*.5,0,-z),a.lerp(b,.71)+p(-spread*.43,0,-z),b],
                        [.62,1.25-.4*t0,1.15-.4*t0,.40],1.45)
                angular([a,middle+p(spread*.6,0,z),b],[.22,.38,.18],.8,.035)
        # Overlapping faceted shoulder joint, avoiding separated butt caps.
        if kind in ('woven_loom','folded_silk'):
            c=p(7,18);blade([c+p(-.9,-.8),c+p(.9,-.8),c+p(1,1),c+p(-1,1)],1.75)
        tip=p(STRING_X,end,-.02)
        angular([spine(.96),tip,tip+p(-1.2,2.0)],[.55,.60,.045],1.2,.045)
        for j,t in enumerate((0,.22,.56)):
            c=(p(4.5,11.8) if j==0 else spine(t))+p(-1.2,0,-2.4)
            weights=binding(c)
            direction={'harvest_lozenges':(.3,sign,0),'woven_loom':(.7,sign*.7,0),
                       'crystalline_measure':(.2,sign,0),'folded_silk':(-.6,sign*.4,0)}[kind]
            anchors.append({'position':list(c),'bone':max(weights,key=weights.get),'side':sign,'direction':direction})
    return anchors
