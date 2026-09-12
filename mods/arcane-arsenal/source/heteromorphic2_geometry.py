"""Approved second Heteromorphic collection: cleaver, pleats, windows, hovering plates.

Reference images: art/concepts/heteromorphic-four-colors-02. Bow palm and
string anchors stay on the tested skeleton; every visible design is independent.
"""
import math
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
import mesh_builder as mb
from geometric_helpers import ANCHORS,STRING_X
from heteromorphic_geometry import binding


def build(spec,strip,ring,blade,angular):
    import solid_geometry
    solid_geometry.binding=binding
    kind=spec['design'];anchors=[]
    def plate(points,depth=2.4,bevel=.32,category='Heteromorphic2Body'):
        """Closed concave plate with planar caps, bevels and subdivided skin field."""
        pts=[Vector(v) for v in points]
        area=sum(a.x*b.y-b.x*a.y for a,b in zip(pts,pts[1:]+pts[:1]))
        if area<0:pts.reverse()
        inset=[]
        for i,p in enumerate(pts):
            a=(p-pts[i-1]).normalized();b=(pts[(i+1)%len(pts)]-p).normalized()
            na=Vector((-a.y,a.x,0));nb=Vector((-b.y,b.x,0))
            inset.append(p+(na+nb)*bevel/max(.22,1+na.dot(nb)))
        verts=[];faces=[];weights=[];uv=[]
        def add(v):
            verts.append(tuple(v));weights.append(binding(v));uv.append((v.x/30,v.y/60));return len(verts)-1
        def triangle(a,b,c):
            count=max(2,math.ceil(max((b-a).length,(c-b).length,(a-c).length)/1.8))
            grid={}
            for i in range(count+1):
                for j in range(count+1-i):grid[i,j]=add(a+(b-a)*(i/count)+(c-a)*(j/count))
            for i in range(count):
                for j in range(count-i):
                    faces.append((grid[i,j],grid[i+1,j],grid[i,j+1]))
                    if i+j<count-1:faces.append((grid[i+1,j],grid[i+1,j+1],grid[i,j+1]))
        for side in (-1,1):
            cap=[v+Vector((0,0,side*depth/2)) for v in inset]
            for tri in tessellate_polygon([cap]):
                vertices=[cap[v] if isinstance(v,int) else v for v in tri]
                triangle(*(vertices if side>0 else vertices[::-1]))
            for i in range(len(pts)):
                j=(i+1)%len(pts)
                a=pts[i]+Vector((0,0,side*depth*.26));b=pts[j]+Vector((0,0,side*depth*.26))
                c=cap[j];d=cap[i]
                for tri in ((a,b,c),(a,c,d)):
                    triangle(*(tri if side>0 else tri[::-1]))
            # Fine luminous inset traces are actual geometry on both faces.
            trace=[]
            for a,b in zip(cap,cap[1:]+cap[:1]):
                trace.extend(a.lerp(b,float(t)) for t in np.linspace(0,1,max(3,math.ceil((b-a).length/.8)))[:-1])
            trace.append(trace[0])
            mb.sweep(trace,[.065]*len(trace),'Heteromorphic2Edge',binding,sides=6)
        for a,b in zip(pts,pts[1:]+pts[:1]):
            lo=Vector((0,0,-depth*.26));hi=-lo
            triangle(a+lo,b+lo,b+hi);triangle(a+lo,b+hi,a+hi)
        mb.batches[category].add(verts,faces,uv,weights)


    def curve(points,count=71):
        a,b,c,d=map(Vector,points)
        return [a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3 for t in np.linspace(0,1,count)]

    ys=np.linspace(-5.6,5.6,53)
    if kind=='faultwing':widths=[1.25]*len(ys)
    elif kind=='foldedfan':widths=[1.12+.12*math.cos(y/5.6*math.pi) for y in ys]
    elif kind=='offsetgate':widths=[1.05+.12*(abs(y)/5.6)**2 for y in ys]
    else:widths=[1+.26*(abs(y)/5.6)**3 for y in ys]
    strip([Vector((1.3,float(y),0)) for y in ys],widths,2.7,.045)
    if kind=='offsetgate':
        # Continuous rectangular backguard, outside the hand and arrow clearance.
        angular([Vector((1.3,-6,0)),Vector((7,-6,0)),Vector((7,6,0)),Vector((1.3,6,0))],
                [.7,.8,.8,.7],2.7)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def poly(coords,depth=2.6,bevel=.28):plate([p(*v) for v in coords],depth,bevel)
        def rail(coords,widths,depth=2.6):angular([p(*v) for v in coords],widths,depth)
        tip=p(STRING_X,end)
        if kind=='faultwing':
            # The top is a single huge curved cleaver with one stepped slot.
            if sign==1:
                rail([(1.3,5.5),(2,9),(4,13)],[1.2,1.8,2.6],3.0)
                left=[(1,13),(.8,23),(1,31),(-4,42),(STRING_X,end)]
                right=[(9,13),(18,23),(18,31),(9,44),(STRING_X,end)]
                hole_l=[(5.5,18),(6,25),(8,31),(6,38),(2,43)]
                hole_r=[(8,18),(10,25),(11,31),(9,38),(4.5,43)]
                # Broad connected panels bound a real through-hole, not a painted slot.
                poly(left+hole_l[::-1],3.6)
                poly(right+hole_r[::-1],3.6)
                poly([left[0],right[0],hole_r[0],hole_l[0]],3.6)
                poly([left[-1],hole_l[-1],hole_r[-1]],3.6)
                # Two small steps on the slot edge maintain its notched silhouette.
                poly([(9.4,26),(10.8,26.4),(11,28.2),(9.5,27.8)],3.3,.18)
                poly([(9.4,34),(10.6,34.5),(10.1,36),(9,35.5)],3.3,.18)
                marks=[p(15,22,-2.6),p(17,31,-2.6),p(6,44,-2.4)]
            else:
                pts=curve([p(1.3,6),p(9,22),p(-3,41),tip])
                strip(pts,[1.25*(1-t)+.35*t+.55*math.sin(math.pi*t) for t in np.linspace(0,1,len(pts))],2.9,.052)
                # Three offset, slanted lower plates make the mass asymmetry intentional.
                for x,y,w,h in [(4.5,18,4.3,7),(3.7,29,3.8,6.5),(-1.8,40,3,5.3)]:
                    poly([(x-w,y-h/2),(x+w,y-h/2+2),(x+w-.3,y+h/2+2),(x-w-.3,y+h/2)],3.2)
                marks=[p(7,20,-2.5),p(6,31,-2.5),p(0,42,-2.4)]
            poly([(-.6,5.6),(3.5,5.6),(4.6,8.2),(-1,7.7)],3.1)
            if sign==-1:poly([(1.4,7),(9,5.3),(6,12.7),(3,10)],3.0)
        elif kind=='foldedfan':
            # Three broad joined fan sectors, sculpted into alternating real folds.
            root=p(1.6,9)
            outer=[p(19,18,-.7),p(23,30,1.25),p(17,43,-.8),tip]
            inner=[p(2,12),p(5,25),p(2,38),tip]
            pts=curve([p(1.3,6),p(10,17),p(4,39),tip])
            strip(pts,[1.2*(1-t)+.35*t for t in np.linspace(0,1,len(pts))],2.7,.055)
            # Closed bevelled planar panels on distinct folded planes. Shared root
            # and outer junctions have matching skin fields through the draw pose.
            plate([root,outer[0],outer[1]],2.5,.24)
            plate([root,outer[1],outer[2]],2.5,.24,'Heteromorphic2Fold')
            plate([root,outer[2],p(7,50,-.4),outer[3],p(-4,47),p(3,34),p(5,24)],2.5,.24)
            rail([(1.3,5.7),(5,7.8),(2,10),(0,8.2)],[.8,.95,.8,.7],2.9)
            for x,y in [(7,15),(9,19),(10.5,23)]:
                blade([p(x,y-1,-1.6),p(x+.55,y,-1.6),p(x,y+1,-1.6),p(x-.55,y,-1.6)],.8)
            marks=[p(18,21,-2.7),p(21,32,-2.7),p(12,43,-2.7)]
        elif kind=='offsetgate':
            # Three long rectangular portal frames in a depth-stepped arc.
            centers=[p(7,17,-.2),p(4,33,.4),p(-5,47,.9)]
            tangents=[p(.25,1),p(-.35,1),p(-.9,.8)]
            dims=[(4.2,10.0),(3.4,8.0),(2.4,6.2)]
            ends=[]
            for c,d,(w,h) in zip(centers,tangents,dims):
                d.normalize();n=Vector((d.y,-d.x,0))
                a=c-d*h;b=c+d*h
                ring([a-n*w,b-n*w,b+n*w,a+n*w],1.12,3.2)
                ends.append((a,b))
            joints=[(p(1.3,6),ends[0][0]),(ends[0][1],ends[1][0]),(ends[1][1],ends[2][0]),(ends[2][1],tip)]
            for a,b in joints:
                if (b-a).length>.1:angular([a,b],[1.35,.65],3.0)
            poly([(-.6,5.4),(3.2,5.4),(3.2,7.4),(-.6,7.4)],3.5,.25)
            marks=[list(c+Vector((0,0,-2.5))) for c in centers]
            marks=list(map(Vector,marks))
        else:
            # Swept continuous spine; outer lozenges are separated by real air gaps.
            spine=curve([p(1.3,8),p(12,24),p(3,41),tip])
            strip(spine,[1.0*(1-t)+.3*t+.25*math.sin(math.pi*t) for t in np.linspace(0,1,len(spine))],2.6,.055)
            if sign==1:
                ring([p(1.3,5.8),p(5.5,8),p(2.6,13),p(-.6,11)],.7,2.8)
            else:
                rail([(-.8,5.5),(1.3,8.4),(3.7,5.8)],[.8,.8,.8],2.8)
            for x,y,w,h in [(15,20,4.8,6.8),(13.8,31.5,3.8,5.4),(8.2,42,2.7,4),(-1,49,1.7,2.5)]:
                poly([(x,y-h),(x+w,y+.5),(x,y+h),(x-w,y-.5)],2.35,.25)
                nearest=min(spine,key=lambda q:abs(q.y-sign*y))
                tether_end=p(x-w-.1,y-.5)
                # Short straight energy tethers rather than added rings/branches.
                angular([nearest,tether_end],[.24,.22],.48,edge=.035)
            marks=[p(18,20,-2.1),p(16,32,-2.1),p(9,42,-2.1)]
        poly([(STRING_X-1,end-1),(STRING_X+1,end-.5),(STRING_X+.6,end+1.6)],2.2,.12)
        for pos in marks:
            w=binding(pos)
            anchors.append({'position':list(pos),'bone':max(w,key=w.get),'side':sign,'direction':(.6,sign*.5,0)})
    return anchors
