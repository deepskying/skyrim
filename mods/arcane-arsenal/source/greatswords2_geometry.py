"""Eccentric crescent, swept lamellae, folded slab and genuine helical ribbons."""
import math
from mathutils import Vector

def curve(points,steps=18):
    p=[Vector(v) for v in points];out=[]
    for i in range(steps+1):
        t=i/steps;out.append(tuple((1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3]))
    return out

def build(spec,slab,rail,frame,solid):
    kind=spec['design']
    if kind=='eccentric':
        # One open crescent cut in the blade, with a deliberately off-centre disc.
        outline=[(9,104),(9,21),(5,18),(5,11),(-4,11),(-4,22),(-8,28),(-8,35),(-14,46),(-17,50)]
        outline += [(-5+11*math.cos(math.radians(a)),60+11*math.sin(math.radians(a))) for a in [220+i*280/50 for i in range(51)]]
        outline += [(-17,71),(-13,79),(-5,87),(-2,94)]
        slab(outline,3.2,bevel=.42)
        disc=[(-7+3.25*math.cos(i*math.tau/48),59+3.25*math.sin(i*math.tau/48)) for i in range(48)]
        slab(disc,2.8,bevel=.5)
        rail(curve([(1,9),(-5,8),(-14,10),(-14,20)]),2.6,3)
        slab([(2,8),(11,8),(11,13),(2,13)],4,bevel=.4)
        slab([(-3,-17),(-3,-23),(0,-27),(3,-23),(3,-17)],3.5,bevel=.35)
        return [(-11,62,0),(-8,55,0),(-3,60,0),(-9,67,0),(-14,75,0),(9,85,0)]
    if kind=='lamellar':
        slab([(1,12),(5,14),(5,95),(1,106),(-2,97),(-1,16)],2.8,bevel=.35)
        # Five broad curved fins with a real depth offset and open channels.
        for i,(y,length,width) in enumerate([(14,32,21),(33,27,17),(49,23,13.5),(64,19,10),(78,16,7.5)]):
            a=curve([(1,y),(-3,y+8),(-width-1,y+length-7),(-width,y+length)])
            b=curve([(-width,y+length),(-width+4,y+length-7),(0,y+length-4),(2,y+7)])
            slab(a+b[1:],2.1,z=(-1)**i*.85,bevel=.30)
        guard1=curve([(-1,10),(-7,16),(-13,17),(-13,20)])
        guard2=curve([(1,11),(6,15),(12,12),(13,7)])
        rail(guard1,2.8,3);rail(guard2,2.8,3)
        slab([(0,-16),(-3,-21),(0,-27),(3,-21)],3,bevel=.32)
        return [(-22,44,0),(-18,57,0),(-14,70,0),(-11,81,0),(-8,92,0),(-17,39,0)]
    if kind=='foldrule':
        # The entire blade changes depth and lateral position across two elbows.
        sections=[(12,0,0,6),(34,-3,0,6),(40,1,3.4,6),(67,1,3.4,6),(73,-3,-.4,6),(91,-1,-.4,5),(106,4,-.4,.06)]
        verts=[]
        for y,x,z,w in sections:verts += [(x-w,y,z-1.4),(x+w,y,z-1.4),(x+w,y,z+1.4),(x-w,y,z+1.4)]
        faces=[(3,2,1,0),(24,25,26,27)]
        for i in range(len(sections)-1):
            for j in range(4):a=i*4+j;b=i*4+(j+1)%4;faces.append((a,b,b+4,a+4))
        solid(verts,faces,.3)
        slab([(-12,10),(-12,14),(-7,14),(-7,12),(11,12),(15,8),(7,8),(5,9)],3.5,bevel=.3)
        slab([(-2.7,-17),(-2.7,-25),(2.7,-25),(2.7,-17)],4.3,bevel=.4)
        return [(8,36,2),(9,40,3),(8,68,3),(8,73,0),(-9,36,2),(-9,72,0)]
    if kind=='twistededge':
        # Two closed lofts, not flat polygons: radial width and tangential thickness.
        for side in (-1,1):
            verts=[];faces=[];count=65
            for i in range(count):
                t=i/(count-1);y=15+75*t;theta=-.7*math.pi+math.pi*t
                radial=Vector((math.cos(theta),0,math.sin(theta)));normal=Vector((-math.sin(theta),0,math.cos(theta)))
                radius=1.5+4.5*math.sin(math.pi*t)**.8;center=Vector((0,y,0))+radial*(side*radius)
                width=1.7+1.0*math.sin(math.pi*t)
                for x,z in [(-width,-.75),(width,-.75),(width,.75),(-width,.75)]:verts.append(tuple(center+radial*x+normal*z))
                if i:
                    for j in range(4):a=(i-1)*4+j;b=(i-1)*4+(j+1)%4;faces.append((a,b,b+4,a+4))
            faces += [(3,2,1,0),tuple((count-1)*4+j for j in range(4))]
            solid(verts,faces,.10)
        # Merge the two ribbons into a single long tapering point.
        verts=[]
        for y,w,d in [(84,.4,.4),(89,4.8,3.4),(96,3.2,2),(107,.045,.045)]:verts += [(-w,y,-d),(w,y,-d),(w,y,d),(-w,y,d)]
        faces=[(3,2,1,0),(12,13,14,15)]+[(i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j) for i in range(3) for j in range(4)]
        solid(verts,faces,.18)
        # Bent rhombus guard, kept above the upper palm.
        for a,b in [((0,7),(-11,14)),((-11,14),(0,21)),((0,21),(11,14)),((11,14),(0,7))]:rail([a,b],1.8,2.6,z=(a[0]+b[0])*.12)
        slab([(0,-17),(-3.5,-22),(0,-27),(3.5,-22)],3,bevel=.3)
        return [(-6,30,3),(6,40,-3),(-6,52,4),(6,64,-4),(-5,76,3),(4,86,0)]
    raise ValueError(kind)
