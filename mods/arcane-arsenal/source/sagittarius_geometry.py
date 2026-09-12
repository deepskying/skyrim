"""Four Sagittarius silhouettes authored from sagittarius-four-colors-01.

Swept fletching, a paired trajectory, folded rail blades, and comet streamers.
The grasp, vanilla skeleton and string anchors remain compatible with the
existing draw controller. Solid bands and their rims share the same skin field.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import ANCHORS,STRING_X
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    def grip_x(y):
        return 1.3+({'crimson_vector':.25,'jade_trajectory':.50,
                    'azure_rail':.15,'violet_comet':.28}[kind])*math.sin(y*math.pi/7)
    ys=np.linspace(-5.6,5.6,49)
    widths=[1.2+.65*(abs(y)/5.6)**1.8 for y in ys]
    if kind=='azure_rail':widths=[1.3+.4*(1-abs(y)/5.6) for y in ys]
    roll=([.95*y/5.6 for y in ys] if kind=='jade_trajectory' else
          [.50*y/5.6 for y in ys] if kind=='violet_comet' else None)
    strip([Vector((grip_x(y),float(y),0)) for y in ys],widths,2.8,.055,roll=roll)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def ribbon(ctrl,w0,bulge,w1,depth=1.65,steps=90):
            strip(curve(ctrl,steps),[w0*(1-t)+w1*t+bulge*math.sin(math.pi*t)
                                  for t in np.linspace(0,1,steps)],depth,.052)
        g=p(grip_x(sign*5.5),5.5);j=p(8.0,17);tip=p(STRING_X,end)
        def spine(t):
            a,b,c,d=j,p(14.7,29),p(-3.5,end-7),tip
            return a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3
        if kind=='crimson_vector':
            # Short chevron cuffs, open arrow-like shoulder, three long free blade tips.
            angular([p(-.9,6.4),p(1.3,7.4),p(3.5,6.4)],[.50,.65,.50],2.0)
            ribbon([g,p(1.8,9),p(6.0,12.0),j],1.6,.4,1.45)
            angular([g,p(-1.7,9.7),j],[1.0,.9,1.2],1.4)
            ribbon([j,p(12.0,29),p(-4,end-8),tip],1.05,.05,.25,1.4)
            # Separated sabers grow from a common root rather than repeat small plates.
            feather_paths=[[(5.3,14),(25,23),(23,32),(17,40)],
                           [(6.1,15.5),(19,27),(8,43),(-8,51)],
                           [(7,17),(5,23),(3,31),(-2,41)]]
            for i,path in enumerate(feather_paths):
                ribbon([p(x,y,(i-1)*.6) for x,y in path],1.05,1.55,.025,1.55)
        elif kind=='jade_trajectory':
            # Swept spear openings and broad asymmetrical shoulder surfaces.
            ribbon([g,p(grip_x(sign*5.5)+.2,8.7),p(4.5,9.5),p(5.2,11.0)],1.55,.3,1.2)
            ribbon([p(5.2,11),p(2.5,13.1),p(4.4,15.6),j],1.2,.25,1.7)
            ribbon([g,p(-1.6,9.5),p(-.6,13.2),j],1.15,.2,1.4)
            ts=np.linspace(0,1,130)
            for rail in (-1,1):
                pts=[spine(t)+p(rail*4.8*math.sin(math.pi*t),0,rail*.3*math.sin(math.pi*t)) for t in ts]
                sizes=[1.1*(1-t)+.20+(1.6 if rail==1 else .40)*math.sin(math.pi*t) for t in ts]
                strip(pts,sizes,1.55,.052)
            # Fine guide lies close to the inner band rather than filling the opening.
            strip([spine(t)+p(-3.3*math.sin(math.pi*t),0,-.5) for t in ts],
                  [.42*(1-t)+.15 for t in ts],1.0,.04)
            blade([p(8.9,17.2),p(10.9,21),p(11.2,16.4)],1.4)
        elif kind=='azure_rail':
            # Faceted spindle, diagonal cuffs, and one uninterrupted leading blade.
            for y in (5.6,6.55):
                angular([p(-.5,y-.45,-.65),p(3.1,y+.40,-.65)],[.42,.42],2)
            a=p(10.8,13.0)
            ribbon([g,p(1.5,8.3),p(8,9.5),a],1.3,.20,1.5)
            ribbon([g,p(-.6,9.0),p(2,13.0),a],.75,.1,.90)
            b=p(10.6,27,1);c=p(2.0,40,-.5)
            angular([a,b,c,tip],[1.75,3.1,2.25,.15],1.85)
            angular([a,p(5.6,22,-.8),p(-.3,38,-.8),tip],[.80,.72,.55,.15],1.3)
            angular([a,p(1.4,24,.4),p(-4.7,39,.4),tip],[.65,.60,.45,.15],1.2)
            # Pointed broad fold faces link to the two support rails.
            blade([a,p(6.0,19.3),p(10.65,24.2)],1.55)
        else:
            # Comet shoulder fan: one wide surface, two thin offset streamers.
            ribbon([g,p(1.0,8.7),p(9.3,9.6),p(7.5,11.8)],1.65,.5,1.45)
            ribbon([p(7.5,11.8),p(3.8,13.6),p(5,16.0),j],1.45,.8,2.0)
            ribbon([g,p(-1.7,8.9),p(-3.5,14.4),j],1.05,.4,1.25)
            ts=np.linspace(0,1,140)
            strip([spine(t)+p(1.4*math.sin(math.pi*t),0,.55*math.sin(math.pi*t)) for t in ts],
                  [1.65*(1-t)+.2+1.75*math.sin(math.pi*t) for t in ts],1.7,.055,
                  roll=[.22*math.sin(2*math.pi*t) for t in ts])
            for side in (-1,1):
                pts=[spine(t)+p(side*8.0*math.sin(math.pi*t),0,-1.25*math.sin(math.pi*t)) for t in ts]
                strip(pts,[.8*(1-t)+.15+.18*math.sin(math.pi*t) for t in ts],1.15,.045)
            # Two discreet structural connections, not a chain of decorative cages.
            for t in (.12,.66):
                c=spine(t);spread=8.0*math.sin(math.pi*t)
                angular([c+p(-spread,0,-1),c+p(spread,0,-1)],[.32,.32],.9,.035)
        # Overlapping shoulder joint covers the turn between sampled surfaces.
        joint=(p(10.8,13) if kind=='azure_rail' else j)
        blade([joint+p(-1.5,-1),joint+p(1.3,-1),joint+p(.9,1.3),joint+p(-1,1.3)],1.8)
        # Open spearhead follows the string endpoint rather than a diamond finial.
        ring([tip+p(1.8,-2.4),tip+p(-1.0,2.4),tip+p(-1.3,-1.8)],.36,1.35)
        for t in (.10,.40,.72):
            c=spine(t)+p(-1.8,0,-2.8);weights=binding(c)
            direction={'crimson_vector':(-.5,sign,0),'jade_trajectory':(.5,sign*.65,0),
                       'azure_rail':(-.3,sign,0),'violet_comet':(-.6,sign*.8,0)}[kind]
            anchors.append({'position':list(c),'bone':max(weights,key=weights.get),'side':sign,'direction':direction})
    return anchors
