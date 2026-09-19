"""Second crossbow set: broad beveled frames, scrolls, tiers and floating blocks."""
import math
from mathutils import Vector

def build(api):
    mb=api['mb'];tube=api['tube'];limb=api['limb'];plate=api['plate'];design=api['design'];root={'CrossbowRoot':1.0}
    def ribbon(points,width=1,depth=1.4,binding=root):
        points=[Vector(p) for p in points];pts=[]
        for a,b in zip(points,points[1:]):
            count=max(1,math.ceil((b-a).length/.8))
            pts.extend(a.lerp(b,j/count) for j in range(count))
        pts.append(points[-1]);vertices=[];faces=[];weights=[];uv=[];edges=[[],[]]
        # Eight corners make a broad top face with a deliberate bevel, not wire.
        section=[(-1,-.55),(-.72,-1),(.72,-1),(1,-.55),(1,.55),(.72,1),(-.72,1),(-1,.55)]
        for i,p in enumerate(pts):
            axis=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
            side=axis.cross(Vector((0,0,1)))
            if side.length<.01:side=Vector((1,0,0))
            side.normalize();normal=axis.cross(side).normalized()
            for j,(x,z) in enumerate(section):
                q=p+side*x*width+normal*z*depth/2
                vertices.append(tuple(q));uv.append((j/7,i*.04));weights.append(binding(p) if callable(binding) else binding)
            for j,x in enumerate((-.72,.72)):edges[j].append(p+side*x*width-normal*(depth/2+.015))
            if i:
                start=(i-1)*8
                faces.extend((start+j,start+(j+1)%8,start+8+(j+1)%8,start+8+j) for j in range(8))
        faces.extend([tuple(range(7,-1,-1)),tuple((len(pts)-1)*8+j for j in range(8))])
        volume=sum(Vector(vertices[f[0]]).dot(Vector(vertices[f[j]]).cross(Vector(vertices[f[j+1]])))/6 for f in faces for j in range(1,len(f)-1))
        if volume<0:faces=[tuple(reversed(f)) for f in faces]
        mb.batches['CrossbowBody'].add(vertices,faces,uv,weights)
        for edge in edges:tube(edge,.075,'CrossbowEdge',binding)
    def frame(points,width=1,depth=1.4,binding=root):
        # Separate mitered beams intersect at vertices, keeping sharp frame corners.
        for a,b in zip(points,points[1:]+points[:1]):ribbon([a,b],width,depth,binding)
    anchors=[]
    for sign in (-1,1):
        def P(x,y,z=1.8):return (sign*x,y,z)
        nock=P(24.978,14.03,1.315)
        if design=='siegewedge':
            frame([P(3,19.4),P(8,26),nock],1.3,1.9,limb)
            # Wide roots and tapered arrow-shaped nocks add visual weight.
            plate([P(3,17.8),P(7,18.3),P(8.3,25.7),P(4,22.5)],1.7,limb)
            plate([P(23,12),P(27,14.03),P(23.6,17)],1.45,limb)
            frame([P(.7,-9,.7),P(5.2,-26,.7),P(.7,-28,.7)],1.0,1.7)
            ribbon([P(1.9,-4),P(3.6,1),P(3.3,10),P(1.9,12)],.8,1.5)
            positions=[P(8,26),P(17,20),P(26,14)]
        elif design=='spiralcoil':
            # Each scroll is a full changing-radius spiral, beyond the old arcs.
            ribbon([P(3,19.4),P(7,22),P(12,24),P(18,23),P(23,20),nock],1,1.35,limb)
            scroll=[]
            for j in range(91):
                t=j/90;angle=-math.tau*1.28*t;radius=7.978*(1-t)+1.0*t
                scroll.append(P(17+radius*math.cos(angle),14.03+radius*math.sin(angle),1.315))
            ribbon(scroll,.84,1.25,limb)
            stock=[P(.6+4.4*math.sin(math.pi*t),-9-19*t,.5) for t in [j/38 for j in range(39)]]
            ribbon(stock,.9,1.5)
            ribbon([P(.8,-9),P(2.5,-3),P(3.3,3),P(1.9,10)],.62,1.2)
            positions=[P(9,21),P(17,7),P(24,15)]
        elif design=='verticaltiers':
            lower=[P(3,19.4),P(13.5,18.1),nock]
            upper=[P(3,19.4,-6.2),P(13.5,18.1,-6.2),P(24.978,14.03,-6.2)]
            ribbon(lower,1.15,1.5,limb);ribbon(upper,1.15,1.5,limb)
            for x,y in ((4,19.2),(14,18),(24,14.4)):
                ribbon([P(x,y,1.6),P(x,y,-6.2)],.72,1.25,limb)
            frame([P(.7,-10),P(4.8,-15),P(4.8,-28),P(.7,-28)],.95,1.6)
            ribbon([P(1,-21),P(4.8,-21)],.75,1.5)
            plate([P(1.5,-4),P(3.7,0),P(3.7,8),P(1.5,12)],1.5)
            positions=[P(5,20,-6.5),P(14,19,-6.5),P(24,15,-6.5)]
        elif design=='driftsegments':
            # Thin light tethers bridge intentional gaps; all chunks still flex.
            centers=[P(3,19.4),P(7,23 if sign<0 else 19),P(13,24 if sign<0 else 17),P(19,21 if sign<0 else 12),nock]
            tube(centers,.14,'CrossbowEdge',limb)
            ribbon([centers[0],centers[1]],.8,1.4,limb)
            for a,b in zip(centers[1:],centers[2:]):
                a,b=Vector(a),Vector(b);delta=b-a;start=a+delta*.1;end=b-delta*.12
                ribbon([start,end],1.65 if sign<0 else 1.4,1.8,limb)
            ribbon([P(.7,-9),P(3.7,-15),P(4.4,-27)],.95,1.8)
            ribbon([P(4.4,-27),P(.8,-28)],.95,1.8)
            # A lower cantilever is separated by one small luminous bridge.
            ribbon([P(.8,-13,4.5),P(3.2,-19,4.5)],.65,1.2)
            positions=centers[1:4]
        else:raise ValueError(design)
        for p in positions:
            weights=limb(Vector(p));anchors.append({'bone':max(weights,key=weights.get),'side':sign,'position':p,'direction':[sign*.35,0,-1]})
    if design=='driftsegments':
        frame([(2.4,-3,1),(6.4,-.5,1),(8.2,4,1),(3.4,1,1)],.7,1.4)
        plate([(4.5,-.2,.8),(5.8,-.7,.8),(6.2,.8,.8),(4.9,1.2,.8)],1.2)
    return anchors
