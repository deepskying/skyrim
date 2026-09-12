"""Faultline frames, branching arbor, annular disks and radial fan-vault bows.

Selected concepts: art/concepts/heteromorphic-four-colors-01. Closed bevelled
solids and continuous skin weights; preserve the established palm and nocks.
"""
import math
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
import mesh_builder as mb
from geometric_helpers import ANCHORS, STRING_X


def binding(pos):
    """Continuous weights prevent nearest-reference-vertex steps on broad plates.

    This field is scoped to Heteromorphic. Bowstring weights retain their own mapping.
    """
    y=abs(pos.y);side='Up' if pos.y>=0 else 'Lo'
    mid='Bow_MidBone';first='Bow_'+side+'Bone1';second='Bow_'+side+'Bone2'
    if y<=6.5:return {mid:1.0}
    def mix(a,b,t):
        t=t*t*(3-2*t)
        return {a:1-t,b:t}
    if y<19:return mix(mid,first,(y-6.5)/12.5)
    if y<=21:return {first:1.0}
    if y<35:return mix(first,second,(y-21)/14)
    return {second:1.0}


def build(spec,strip,ring,blade,angular):
    import solid_geometry
    solid_geometry.binding=binding
    kind=spec['design'];anchors=[]

    def plate(points,depth=2.4,bevel=.32):
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
            mb.sweep(trace,[.065]*len(trace),'HeteromorphicEdge',binding,sides=6)
        for a,b in zip(pts,pts[1:]+pts[:1]):
            lo=Vector((0,0,-depth*.26));hi=-lo
            triangle(a+lo,b+lo,b+hi);triangle(a+lo,b+hi,a+hi)
        mb.batches['HeteromorphicBody'].add(verts,faces,uv,weights)

    def curve(points,count=65):
        a,b,c,d=map(Vector,points)
        return [a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3 for t in np.linspace(0,1,count)]

    ys=np.linspace(-5.6,5.6,53)
    if kind=='faultline':
        widths=[1.32]*len(ys);roll=None
    elif kind=='arbor':
        widths=[1.05+1.0*(1-abs(y)/5.6) for y in ys];roll=None
    elif kind=='annulus':
        widths=[1.0+.3*math.cos(y*math.pi/2.8) for y in ys];roll=None
    else:
        widths=[1.1+.3*(abs(y)/5.6)**2 for y in ys];roll=[.25*y/5.6 for y in ys]
    strip([Vector((1.3,float(y),0)) for y in ys],widths,2.8,.052,roll=roll)
    if kind=='faultline':
        angular([Vector((.5,-6.5,0)),Vector((-5.2,-4.2,0)),Vector((-5.2,4.2,0)),Vector((.5,6.5,0))],
                [1,1.05,1.05,1],2.6)
    elif kind=='annulus':
        pts=[Vector((1.3+5.5*math.cos(t),5.5*math.sin(t),0)) for t in np.linspace(-math.pi/2,math.pi/2,65)]
        strip(pts,.85,2.2,.06)
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def poly(coords,depth=2.4,bevel=.32):plate([p(*v) for v in coords],depth,bevel)
        def rail(coords,widths,depth=2.2):angular([p(*v) for v in coords],widths,depth)
        def ribbon(coords,a,b,c,depth=2.2):
            pts=curve([p(*v) for v in coords]);ts=np.linspace(0,1,len(pts))
            strip(pts,[a*(1-t)+c*t+b*math.sin(math.pi*t) for t in ts],depth,.06)
        tip=p(STRING_X,end)
        if kind=='faultline':
            # Two long closed slot-frames are offset in both plane and depth.
            rail([(1.3,6),(8.5,10),(9.5,28),(3.5,45),(STRING_X,end)],
                 [2,2.3,2.4,2.1,.55],3.0)
            for a,b,w,z in [(p(7,11),p(5.5,33),3.5,-.2),(p(5.3,30),p(-3.4,49),3.0,.65)]:
                d=(b-a).normalized();n=Vector((d.y,-d.x,0));off=Vector((0,0,z))
                ring([a-n*w+off,b-n*w+off,b+n*w+off,a+n*w+off],1.15,2.8)
            # Distinct outer stepped slabs; these sit along the frames, not free-floating.
            poly([(10,10),(14,13),(13,25),(10,27),(9.3,14)],3.2)
            poly([(8.2,29),(11.8,32),(6.3,45),(3,44)],3.5)
            poly([(-1,5.3),(3.6,5.3),(5.1,7.5),(-2.1,7.5)],3.4,.25)
            poly([(STRING_X-1.4,end-1.2),(STRING_X+1.2,end-1.2),(STRING_X+1.2,end+2),
                  (STRING_X-1.4,end+2)],3.0,.25)
            marks=[p(12,17,-2.5),p(8,32,-2.5),p(-3,47,-2.5)]
        elif kind=='arbor':
            # Connected major forks form large openings; free twigs end in polygonal points.
            ribbon([(1.3,5.5),(2,11),(6,14),(6,23)],1.2,.45,1.8)
            rail([(6,23),(9.5,36),(STRING_X,end)],[1.8,2.0,.3],2.6)
            ribbon([(2.8,10),(0,14),(-3,19),(0,23)],.85,.25,1.1,1.9)
            rail([(0,23),(1,36),(STRING_X,end)],[1.1,1.0,.3],1.9)
            poly([(-1.2,21.8),(.7,21.5),(1.4,24.2),(-.9,24.2)],2.05,.17)
            ribbon([(6,22),(12,23),(17,27),(19.2,31)],1.25,.65,.03,2.5)
            blade([p(4.2,22),p(6,20.5),p(8,23),p(6,25)],2.7)
            # Fork collar, backed by a solid tapered connection rather than another ring.
            blade([p(-.5,5),p(4.2,7),p(6.4,13),p(1,9)],2.7)
            blade([p(7.5,34),p(11.2,37),p(8.5,40),p(6.6,36.5)],2.8)
            blade([tip+p(-1.4,-.5),tip+p(1.2,0),tip+p(.4,5.3),tip+p(-1.3,1)],2.4)
            marks=[p(5,14,-2.2),p(16,27,-2.4),p(7,37,-2.5)]
        elif kind=='annulus':
            # Thick annular bodies, four large dark circular openings, no gears.
            for cx,cy,rx,ry,width,depth in [(3,21,7.1,9.0,1.7,3.1),(-7,45,3.7,4.7,1.05,2.7)]:
                pts=[p(cx+rx*math.cos(t),cy+ry*math.sin(t)) for t in np.linspace(0,math.tau,97)]
                strip(pts,width,depth,.06)
            ribbon([(1.3,6),(1.3,9),(3,10),(3,12)],1.5,.6,1.8,2.7)
            # Tangential bridges connect the disks, leaving their holes fully open.
            ribbon([(3,30),(3,33),(-6,36),(-7,40.3)],1.45,.5,1.05,2.5)
            ribbon([(-7,49.7),(-8,51),(-12,52), (STRING_X,end)],1.0,.5,.3,2.4)
            # Rounded wide collars on the otherwise slender palm.
            poly([(-1.6,5),(4.2,5),(4.7,6.2),(3.5,7.2),(-.9,7.2),(-2.1,6.2)],3.5,.45)
            blade([tip+p(-1.0,-1),tip+p(1.1,.2),tip+p(.1,5),tip+p(-1.8,1)],2.4)
            marks=[p(10,21,-2.6),p(0,34,-2.4),p(-3.3,45,-2.4)]
        else:
            # Four radial vanes match the selected illustration's open fan silhouette.
            # All fan blades meet the shoulder hub and the continuous outer bridge.
            rail([(1.3,5.5),(1.8,9),(3.5,13)],[1.2,2.0,1.7],2.7)
            outer=[(25.5,20),(26,31),(18,42),(6,50),(STRING_X,end)]
            rail(outer,[.95,1.05,1.05,.95,.4],2.4)
            tips=[((25.5,20),(25.8,28.5)),((25.7,33),(19.6,40.5)),
                  ((16.8,43),(7.8,49)),((4.9,50.5),(-9.5,54.0))]
            for i,(a,b) in enumerate(tips):
                rootx=3.8-i*1.25;rooty=11.2+i*.8
                poly([(rootx,rooty),(rootx+1.1,rooty+1),a,b,(rootx-.7,rooty+2.2)],2.35,.27)
            poly([(-1,7),(1.4,6),(5.3,9.4),(3.8,13),(.1,12)],3.1,.35)
            blade([p(.2,8.1,-1.0),p(2.5,8,-1.0),p(3.3,10,-1.0),p(1.6,11.8,-1.0)],3.2)
            blade([p(-2.1,5.6),p(1.3,4.2),p(4.8,5.6),p(1.3,6.8)],2.7)
            poly([(STRING_X-1.4,end-.8),(STRING_X+1.2,end),
                  (STRING_X+.5,end+4),(STRING_X-2.2,end+1.1)],2.6,.2)
            marks=[p(25,24,-2.6),p(22,36,-2.6),p(9,47,-2.6)]
        for pos in marks:
            w=binding(pos)
            direction={'faultline':(.6,sign*.4,0),'arbor':(.4,sign*.8,0),
                       'annulus':(.4,sign*.5,0),'fanvault':(.8,sign*.25,0)}[kind]
            anchors.append({'position':list(pos),'bone':max(w,key=w.get),'side':sign,'direction':direction})
    return anchors
