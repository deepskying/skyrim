"""Four solid-light Capricorn bows traced from capricorn-four-colors-01.

Broad horn surfaces, not a repeated wire frame. Each grasp and shoulder is
authored separately. The original bow skeleton and string endpoints are kept.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import ANCHORS,STRING_X
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,57)
    if kind=='ruby_ridge':
        gx=lambda y:1.3
        widths=[1.15+1.0*(abs(y)/5.6)**2 for y in ys];roll=None
    elif kind=='jade_tidehorn':
        gx=lambda y:1.3+.70*math.sin(y*math.pi/7)
        widths=[1.40+.50*(abs(y)/5.6)**2 for y in ys]
        roll=[.55*y/5.6 for y in ys]
    elif kind=='azure_summit':
        gx=lambda y:1.3
        widths=[1.05+.75*(1-abs(y)/5.6) for y in ys];roll=None
    else:
        gx=lambda y:1.3+.25*math.sin(y*math.pi/6)
        widths=[1.25+.60*(abs(y)/5.6)**2 for y in ys]
        roll=[.95*y/5.6 for y in ys]
    strip([Vector((gx(y),float(y),0)) for y in ys],widths,2.8,.052,roll=roll)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def ribbon(ctrl,w0,bulge,w1,depth=1.7,steps=100):
            pts=curve(ctrl,steps)
            strip(pts,[w0*(1-t)+w1*t+bulge*math.sin(math.pi*t) for t in np.linspace(0,1,steps)],depth,.052)
            return pts
        g=p(gx(sign*5.5),5.5);tip=p(STRING_X,end)
        if kind=='ruby_ridge':
            # Hourglass grip and low faceted collar; a triangular slit below the ridge.
            blade([p(-1.2,5.2),p(3.8,5.2),p(4.1,6.5),p(1.3,7.5),p(-1.5,6.5)],2.7)
            j=p(13.4,26)
            ribbon([g,p(1,13),p(10,20),j],1.5,.6,2.8)
            angular([g,p(-5.0,11.2),j],[1.5,1.5,2.2],1.9)
            upper=ribbon([j,p(16.8,32),p(2,49),tip],2.8,1.25,.18,2.0)
            ribbon([p(-4.8,11.2),p(5,29),p(3.5,43),tip],.7,.22,.16,1.25)
            for a,b,c in [((13,26),(20.6,27.8),(14.5,32.7)),((16,32),(23,34),(13.5,38))]:
                blade([p(*a),p(*b),p(*c)],1.65)
            ribbon([tip,p(-12,end+1.6),p(-12.5,end+3.4),p(-13.0,end+4.6)],.60,.35,.02,1.5,35)
            marks=[p(15,27,-2.6),p(16,36,-2.6),p(2,46,-2.6)]
        elif kind=='jade_tidehorn':
            # One broad S surface through each shoulder, with a slender inner tendon.
            for y in (5.6,6.55):
                angular([p(gx(sign*y)-2,y-.6),p(gx(sign*y)+2,y+.6)],[.4,.4],2.9)
            j=p(14,28)
            ribbon([g,p(-3,14),p(14,18),j],1.9,1.1,3.2,1.9)
            ribbon([j,p(14,39),p(-4,45),tip],3.2,1.0,.2,1.9)
            ribbon([p(.5,9),p(2,28),p(8,38),tip],.52,.1,.18,1.1)
            # The split tail grows from the endpoint instead of floating beside it.
            ribbon([tip,p(-12.5,end+2),p(-13,end+3),p(-14.8,end+5)],.6,.35,.015,1.3,40)
            ribbon([p(-9,end-2.8),p(-8.6,end),p(-10.5,end+2),p(-12.8,end+4.5)],.5,.25,.015,1.15,40)
            marks=[p(7,19,-2.7),p(17,31,-2.7),p(5,43,-2.7)]
        elif kind=='azure_summit':
            # Straight prism grasp, angular triangular shoulders and a broad mountain face.
            for y in (5.55,6.8):
                blade([p(-1.1,y-.5),p(3.7,y-.5),p(4.0,y+.45),p(1.3,y+1),p(-1.4,y+.45)],2.4)
            a=p(-4.8,12.0);j=p(15.3,26)
            angular([g,a,j],[1.55,1.8,3.1],2.0)
            angular([g,p(4.1,15),j],[.8,.9,1.5],1.4)
            angular([j,p(8.8,36),p(.8,45),tip],[3.1,2.8,1.75,.2],2.1)
            blade([p(10.8,25.4),p(15.8,21.8),p(19.2,26),p(15.5,30)],2.1)
            ribbon([a,p(.0,25),p(-.8,44),tip],.70,.10,.16,1.25)
            blade([p(12.4,28),p(19.2,26),p(14.8,32)],1.8)
            blade([p(7.8,36),p(12.0,36.8),p(7.2,40.8)],1.5)
            blade([p(.8,44),p(5.7,43.4),p(-.6,47.4)],1.4)
            ribbon([tip,p(-12.2,end+1.6),p(-9.7,end+4.1),p(-7.5,end+6)],.7,.50,.02,1.5,45)
            marks=[p(15.8,26,-2.7),p(11,36,-2.7),p(1,45,-2.7)]
        else:
            # Twisted palm, a genuine open crescent shoulder and swept horn blade.
            j=p(11.0,23)
            ribbon([g,p(-8,9),p(-5,17),j],1.65,.25,3.1,1.8)
            ribbon([g,p(-3.6,10),p(-2.2,18),j],.52,.03,.7,1.15)
            main=ribbon([j,p(15.0,37),p(1,49),tip],3.1,1.5,.18,2.05)
            # Fill the sharp shoulder turn: both swept surfaces meet at one
            # center, but their cross-sections point in different directions.
            blade([p(8.0,21.0),p(14.5,21.5),p(14.0,26.0),p(8.0,25.0)],2.05)
            outer=curve([p(16,25,-.3),p(24.5,35,-.3),p(14,47,-.3),p(-5,51,-.3)],120)
            strip(outer,[.06+.95*math.sin(math.pi*t) for t in np.linspace(0,1,120)],1.4,.045)
            for t in (.28,.64):
                a=main[round(t*(len(main)-1))];b=outer[round(t*(len(outer)-1))]
                angular([a,b],[.40,.32],1.1,.04)
            # Horn tip and low asymmetric collars echo the twist without a shared cuff.
            ribbon([tip,p(-13,end+1),p(-13.7,end+3),p(-14.1,end+4.4)],.65,.30,.02,1.35,35)
            angular([p(-.7,5.2,-.4),p(3.5,6.5,-.4)],[.5,.3],2.4)
            marks=[p(7,21,-2.8),p(14,32,-2.8),p(4,44,-2.8)]
        # Each endpoint has a compact, solid string seat.
        blade([tip+p(-.7,-1),tip+p(.8,-1),tip+p(.5,.8),tip+p(-.5,.8)],1.45)
        for pos in marks:
            weights=binding(pos)
            anchors.append({'position':list(pos),'bone':max(weights,key=weights.get),'side':sign,
                            'direction':(.35,sign*.8,0)})
    return anchors
