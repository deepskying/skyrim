"""Four distinct Gemini meshes authored against gemini-four-colors-01 concepts."""
import math
import numpy as np
from mathutils import Vector
import mesh_builder as mb
from geometric_helpers import STRING_X,ANCHORS
from geometric_flow import curve,binding

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,41)
    if kind=='twin_blades':
        pts=[Vector((1.3+.11*y,float(y),0)) for y in ys]
        widths=[1.50+.70*(abs(y)/5.6)**3 for y in ys]
        strip(pts,widths,2.9,.06)
    elif kind=='braided_bands':
        pts=[Vector((1.3+.60*math.sin(y*math.pi/7),float(y),0)) for y in ys]
        strip(pts,[1.45+.70*(abs(y)/5.6)**1.5 for y in ys],2.7,.055)
    elif kind=='twin_pillars':
        pts=[Vector((1.3+.55*(y/5.6)**2,float(y),0)) for y in ys]
        strip(pts,[1.65+.80*(abs(y)/5.6)**2 for y in ys],3.0,.06)
    else:
        pts=[Vector((1.3,float(y),0)) for y in ys]
        strip(pts,[1.60+.60*(abs(y)/5.6)**1.8 for y in ys],2.6,.055,
              roll=[.58*math.sin(y*math.pi/11.2) for y in ys])
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def center(y):
            if y<16:return p(1.3+(7-1.3)*(y-5.5)/10.5,y)
            t=(y-16)/(end-16)
            bulge={'twin_blades':6,'braided_bands':8,'twin_pillars':7,'phase_crescents':11}[kind]
            return p(7*(1-t)+STRING_X*t+bulge*math.sin(math.pi*t),y)
        def rails(y,side,amp=2.5):
            t=(y-16)/(end-16)
            return center(y)+p(side*amp*(1-t)**.6,0)
        def crescent(y,side):
            t=(y-14)/(end-14);arc=math.sin(math.pi*t)
            return center(max(16,y))+p(side*(2.1+2.1*arc)*(1-t),y-max(16,y),side*1.5*arc)
        if kind=='twin_blades':
            # Paired trapezoid collars and a triangular throat, not an oval grip.
            for j in range(2):
                y=6.4+j*2.8
                blade([p(-1.5,y-.8,j*.25),p(8.2-j,y+1.6,j*.25),
                       p(6.7-j,y+3.0,j*.25),p(.5,y+1.4,j*.25)],2.4-j*.35)
            angular([p(1.9,5.5),p(7.2,10.3),rails(16,1)],[1.3,1.10,.88],1.8)
            angular([p(1.9,5.5),p(2.0,11.5),rails(16,-1)],[1.0,.88,.88],1.6)
            for side in (-1,1):
                values=np.linspace(16,end,76)
                strip([rails(y,side) for y in values],[.90-.52*t for t in np.linspace(0,1,len(values))],1.6,.055)
                for t in np.linspace(.08,.94,11):
                    y=16+(end-16)*float(t);a=rails(y,side);r=3.7*(1-t)+.65
                    # Opposite-facing paired fins have different lean directions.
                    blade([a+p(0,-r*.9),a+p(side*r*1.2,side*r*.5),a+p(0,r*.7)],1.3)
        elif kind=='braided_bands':
            # Full continuous ribbons, with real depth alternation at crossings.
            values=np.linspace(5.5,end,130)
            for side in (-1,1):
                ribbon=[];width=[]
                for y in values:
                    t=(y-5.5)/(end-5.5);fade=math.sin(math.pi*t)**.55
                    phase=3.4*math.pi*t
                    ribbon.append(center(y)+p(side*3.8*fade*math.sin(phase),0,side*1.6*fade*math.cos(phase)))
                    width.append(1.02-.70*t)
                strip(ribbon,width,1.45,.05)
            for y in (20,33,44):
                c=center(y)
                ring([c+p(0,-1.8),c+p(1.25,0),c+p(0,1.8),c+p(-1.25,0)],.28,1.0)
        elif kind=='twin_pillars':
            # Gemini double columns at each end of the hand, rectangular windows.
            for side in (-1,1):
                x=1.85+side*2.6
                angular([p(x,6.8),p(x,13.5),rails(17,side)],[.85,.85,.80],1.7)
            for y in (6.8,13.5):
                angular([p(-1.4,y),p(5.1,y)],[.88,.88],2.2,.06)
                for x in (-.75,4.45):
                    blade([p(x-1.05,y-.95),p(x+1.05,y-.95),p(x+1.05,y+.95),p(x-1.05,y+.95)],2.2)
            for side in (-1,1):
                values=np.linspace(16,end,74)
                strip([rails(y,side) for y in values],[.92-.55*t for t in np.linspace(0,1,len(values))],1.8,.055)
            for y in (20,26,33,40,46,50,53):
                angular([rails(y,-1),rails(y,1)],[.38,.38],1.4,.04)
        else:
            # Two connected crescent rails at different depths and lengths.
            a=p(1.3,5.4)
            angular([a,p(7.4,10.8,1),crescent(16,1)],[1.1,1.1,.82],1.7)
            angular([a,p(-1.5,10.2,-1),crescent(16,-1)],[1.05,.92,.82],1.6)
            for j,y in enumerate((7.4,12.8)):
                c=p(2.3+j*1.9,y,-1.8+j*.3)
                ring([c+p(0,-2.2),c+p(1.6,0),c+p(0,2.2),c+p(-1.6,0)],.42,1.1)
            for side in (-1,1):
                values=np.linspace(14,end,92);points=[];width=[]
                for y in values:
                    t=(y-14)/(end-14);arc=math.sin(math.pi*t)
                    points.append(crescent(y,side))
                    width.append(.90+.36*arc-.60*t)
                strip(points,width,1.5,.055)
            # Short interior crescent peaks taper away between broad bridges.
            inner=curve([crescent(16,-1),p(-1.4,28,-1.2),p(-3,39,-.6),crescent(46,-1)],58)
            strip(inner,[.07+.60*math.sin(math.pi*t) for t in np.linspace(0,1,len(inner))],1.15,.045)
            for y in (19,30,41,49):
                c=center(y)
                ring([c+p(0,-2),c+p(1.4,0),c+p(0,2),c+p(-1.4,0)],.32,1.1)
                angular([crescent(y,-1),crescent(y,1)],[.25,.25],.9,.035)
        tip=p(STRING_X,end,-.02)
        strip([center(end-1.1),tip,tip+p(-1.1,2.5)],[.55,.65,.045],1.2,.045)
        # Six local particle systems, in two opposed groups along the new roots.
        for j,y in enumerate((9.5,17.5,29)):
            c=center(y)+p((3.2 if j%2==0 else -2.8),0,-2.4)
            w=binding(c)
            direction={'twin_blades':(-.3,-sign,0),'braided_bands':(1,sign*.3,0),
                       'twin_pillars':(0,1,0),'phase_crescents':(-1,sign*.25,0)}[kind]
            anchors.append({'position':list(c),'bone':max(w,key=w.get),'side':sign,'direction':direction})
    return anchors
