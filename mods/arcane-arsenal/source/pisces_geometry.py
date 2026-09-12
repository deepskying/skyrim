"""Selected Pisces concepts: twin fins, paired current, tidal blades, dreamfish.

Each shoulder and palm is individually authored, on the established bow rig.
Continuous bevelled bands provide the silhouette; shared weights bind rims.
"""
import math
import numpy as np
from mathutils import Vector
from geometric_helpers import ANCHORS,STRING_X
from geometric_flow import binding,curve

def build(spec,strip,ring,blade,angular):
    kind=spec['design'];anchors=[]
    ys=np.linspace(-5.6,5.6,53)
    if kind=='scarlet_twinfin':
        gx=lambda y:1.3+.25*math.sin(math.pi*y/5.6)
        widths=[1.0+1.1*(1-abs(y)/5.6) for y in ys]
        rolls=[.25*y/5.6 for y in ys]
    elif kind=='jade_pair':
        gx=lambda y:1.3+.38*math.sin(math.pi*y/6.5)
        widths=[1.3+.35*(abs(y)/5.6)**2 for y in ys]
        rolls=[.45*y/5.6 for y in ys]
    elif kind=='azure_twintide':
        gx=lambda y:1.3
        widths=[1.0+.78*math.sin(math.pi*(y+5.6)/11.2) for y in ys]
        rolls=None
    else:
        gx=lambda y:1.3+.5*math.sin(math.pi*y/6)
        widths=[1.25+.35*(abs(y)/5.6)**2 for y in ys]
        rolls=[1.05*y/5.6 for y in ys]
    strip([Vector((gx(y),float(y),0)) for y in ys],widths,2.8,.052,roll=rolls)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def chain(segments,sizes,depth=1.8):
            pts=[];ws=[]
            for i,(ctrl,size) in enumerate(zip(segments,sizes)):
                count=max(28,int(sum((b-a).length for a,b in zip(ctrl,ctrl[1:]))*1.6))
                ts=np.linspace(0,1,count);ps=curve(ctrl,count)
                if i:ps=ps[1:];ts=ts[1:]
                pts.extend(ps);a,bulge,b=size
                ws.extend(a*(1-t)+b*t+bulge*math.sin(math.pi*t) for t in ts)
            strip(pts,ws,depth,.052);return pts
        def ribbon(ctrl,a,bulge,b,depth=1.8):return chain([ctrl],[(a,bulge,b)],depth)
        g=p(gx(sign*5.5),5.5);tip=p(STRING_X,end)
        if kind=='scarlet_twinfin':
            a=p(10.5,23)
            main=chain([[g,p(-1.8,12),p(10.5,14),a],[a,p(10.5,34),p(-5,44),tip]],
                       [(1.5,.9,2.8),(2.8,.65,.18)],1.95)
            # Two broad fin surfaces share roots with the main leading blade.
            ribbon([p(7.8,17.5),p(2.2,24),p(-1.0,26),p(-3.8,28)],1.1,1.5,.018,1.7)
            ribbon([p(10.2,23),p(6.5,30),p(-1.5,33),p(-6,37)],1.1,1.35,.018,1.7)
            ribbon([p(.4,8.5),p(-.4,18),p(2.8,22),p(9.8,23)],.65,.25,.85,1.3)
            # Opposing crescent collars keep the central diamond grasp open.
            ribbon([p(3.1,7),p(1.0,9.2),p(-2.0,8.3),p(-2.4,5.7)],.65,.5,.015,1.7)
            marks=[p(9,19,-2.6),p(8,29,-2.6),p(-2,42,-2.6)]
        elif kind=='jade_pair':
            a=p(12.0,25);b=p(0,43)
            main=chain([[g,p(-5,12),p(12,16),a],[a,p(12,34),p(4,36),b],
                        [b,p(-4,50),p(-14,end-5),tip]],
                       [(1.7,.85,2.7),(2.7,.4,1.65),(1.65,.25,.2)],1.9)
            start=main[round(.20*(len(main)-1))];finish=main[round(.69*(len(main)-1))]
            ribbon([start,p(-4.5,25),p(5.2,30),finish],.55,.28,.55,1.3)
            # Swept collar follows the selected reference's low crescent lip.
            ribbon([p(3.0,6.3),p(-4,7.4),p(-3.0,10.7),p(-2.8,12)],.7,.55,.016,1.65)
            # Short diagonal seams are geometry above the solid palm, not decals.
            for y in (1.6,3.1):
                seam=[]
                for t in np.linspace(0,1,18):
                    gy=sign*(y-.7+1.4*t)
                    dx=.38*math.pi/6.5*math.cos(math.pi*gy/6.5)
                    tangent=Vector((dx,1,0)).normalized()
                    side=Vector((1,-dx,0)).normalized();normal=side.cross(tangent)
                    angle=.45*gy/5.6
                    rs=side*math.cos(angle)+normal*math.sin(angle)
                    rn=normal*math.cos(angle)-side*math.sin(angle)
                    width=1.3+.35*(abs(gy)/5.6)**2
                    seam.append(Vector((gx(gy),gy,0))+rs*((2*t-1)*.62*width)-rn*1.44)
                strip(seam,.07,.08,.025)
            marks=[p(9,20,-2.6),p(9,32,-2.6),p(-3,45,-2.6)]
        elif kind=='azure_twintide':
            a=p(8.5,20)
            main=chain([[g,p(-1,12),p(4.3,17),a],[a,p(17.5,26),p(13,42),tip]],
                       [(1.45,.7,2.7),(2.7,1.25,.17)],2.05)
            # Open triangular wave shoulders, broad short inner tidal sabre.
            shoulder=p(-4.2,10.2)
            chain([[g,p(1,7),p(-3.5,7.7),shoulder],
                   [shoulder,p(-3,13.5),p(3,17),a]],
                  [(1.15,.2,1.1),(1.1,.2,1.6)],1.7)
            inner=ribbon([shoulder,p(5.2,24),p(5.5,34),p(-6.5,46)],1.15,1.10,.02,1.7)
            # Both short bridges use actual sampled vertices on each blade.
            for t in (.35,.55):
                b=inner[round(t*(len(inner)-1))]
                a2=min(main,key=lambda q:abs(q.y-b.y))
                angular([a2,b],[.45,.40],1.25,.04)
            angular([p(-.3,5.65),p(2.9,5.65)],[.34,.34],2.9)
            marks=[p(9,22,-2.7),p(9,34,-2.7),p(-3,46,-2.7)]
        else:
            # One long open eye per limb, twisted in depth, joined at both ends.
            n=181;ts=np.linspace(0,1,n)
            center=curve([g,p(18,17),p(10,36),tip],n)
            for side in (-1,1):
                pts=[];sizes=[];roll=[]
                for t,c in zip(ts,center):
                    # The small end crossings frame one large central eye.
                    spread=side*4.6*math.sin(math.pi*t)*math.sin(math.pi*(t-.17)/.66)
                    pts.append(c+p(spread,0,side*.6*math.sin(2*math.pi*t)))
                    sizes.append(1.25*(1-t)+.16+.5*math.sin(math.pi*t))
                    roll.append(side*.35*math.sin(2*math.pi*t))
                strip(pts,sizes,1.85,.052,roll=roll)
            # Outward crescent tail fin connects above the palm, on the outer side.
            ribbon([p(3.1,8),p(13,9),p(18,11),p(18,16)],1.0,.65,.018,1.65)
            blade([p(-.6,5),p(3.1,5),p(4.6,7.6),p(1,7.5)],2.3)
            marks=[p(10,18,-2.8),p(10,30,-2.8),p(-3,44,-2.8)]
        if kind in ('scarlet_twinfin','jade_pair'):
            # Deliberately longer, distinct paired tail fins unlike Aquarius tips.
            ribbon([tip,p(-10.2,end+1),p(-8.3,end+4),p(-9,end+7)],.7,.8,.018,1.5)
            ribbon([tip,p(-15.8,end+1.7),p(-16.6,end+3),p(-16.3,end+5)],.60,.60,.018,1.4)
        elif kind=='azure_twintide':
            ribbon([tip,p(-14.5,end+1),p(-13.8,end+3),p(-11,end+5.7)],.7,.7,.018,1.55)
        else:
            # Sweeping moon-tail, compact enough to remain inside bow bounds.
            ribbon([tip,p(-15,end+6),p(-8,end+9),p(-4,end+6)],.65,.8,.018,1.5)
        blade([tip+p(-.6,-.7),tip+p(.7,-.7),tip+p(.45,.65),tip+p(-.45,.65)],1.35)
        for pos in marks:
            w=binding(pos)
            anchors.append({'position':list(pos),'bone':max(w,key=w.get),'side':sign,'direction':(.35,sign*.8,0)})
    return anchors
