"""Approved second war-axe concepts in the vanilla WeaponAxe hand frame.

All structural parts are connected, including the purple upper arch. The
negative spaces are explicit open strips, never faces spanning an aperture.
"""
import math
from mathutils import Vector
from greatswords2_geometry import curve


def build(spec, slab, rail, frame, solid):
    def spindle(rings):
        n=8
        verts=[(r*math.cos(math.pi/8+i*math.tau/n),y,r*math.sin(math.pi/8+i*math.tau/n)) for y,r in rings for i in range(n)]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(len(verts)-n,len(verts)))]
        for j in range(len(rings)-1):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
        return solid(verts,faces,.10)

    def blade(outer,inner,depth=2.5):
        # Closed ruled wedge; a thin cutting edge and a thick inner spine.
        assert len(outer)==len(inner)
        verts=[]
        for a,b in zip(outer,inner):
            verts.extend([(a[0],a[1],-.18),(b[0],b[1],-depth/2),(b[0],b[1],depth/2),(a[0],a[1],.18)])
        faces=[(3,2,1,0)];n=len(outer)
        for j in range(n-1):
            for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
        faces.append(tuple(range(4*(n-1),4*n)))
        return solid(verts,faces,.09)

    def band(path,width=2.0,depth=2.4):
        pts=[Vector(p) for p in path];verts=[]
        for i,p in enumerate(pts):
            t=pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]
            side=Vector((-t.y,t.x,0)).normalized()*width/2
            for a,z in ((-1,-1),(1,-1),(1,1),(-1,1)):
                verts.append(p+side*a+Vector((0,0,z*depth/2)))
        faces=[(3,2,1,0),tuple(range(len(verts)-4,len(verts)))]
        for i in range(len(pts)-1):
            for j in range(4):faces.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
        return solid(verts,faces,.16)

    def ridge(outline,peak,depth=2.6):
        # Front and rear pyramidal caps form a closed raised fold face.
        n=len(outline)
        v=[(x,y,z) for z in (-depth/2,depth/2) for x,y in outline]
        v.extend([peak,(peak[0],peak[1],-peak[2])])
        faces=[]
        for i in range(n):
            j=(i+1)%n
            faces.extend([(i,j,j+n,i+n),(i+n,j+n,2*n),(j,i,2*n+1)])
        return solid(v,faces,.12)

    spindle([(-8,1.2),(5,1.2)])
    spindle([(-9,1.5),(-8,1.9),(-7.4,1.9)])
    spindle([(4.6,1.9),(5.4,1.9),(7,1.4)])
    spindle([(-14.5,.25),(-12,2.4),(-10,2.4),(-8.8,1.5)])
    kind=spec['design']
    if kind=='offset_fang':
        # Short S-kink above the palm, followed by a broad vertical socket.
        rail([(0,6),(0,15),(1.8,23),(-1.5,30),(-1.5,40)],3.1,3.1)
        slab([(-4,31),(-4,44),(1.5,44),(1.5,31)],4,bevel=.3)
        outline=[(-24,54),(-13,47),(-14,38),(-12,37),(-13,33),(-14.5,32),(-15,23),(-12,24),(-12.5,18),(-22,25),(-27,41)]
        slab(outline,3.2,bevel=.24)
        ridge([(-24,53),(-14.5,46),(-16,24),(-22,26),(-26,41)],(-20,39,2.5),2.8)
        # Two staggered bridge necks leave the narrow slot open.
        rail([(-14,43),(-3,40)],3.2,3.2)
        rail([(-14,34),(-3,34)],2.8,3.2)
        slab([(1,33),(5,32),(8,36),(5,43),(1,40)],3.4,bevel=.25)
        return [(-25,45,0),(-26,39,0),(-24,32,0),(-20,26,0),(-15,21,0),(-11,38,0)]
    if kind=='returning_sweep':
        # Continuous smooth blade curls inward; both edges converge at tips.
        outer=curve([(-23,54),(-34,40),(-26,27),(-9,17)],32)
        inner=curve([(-23,54),(-8,47),(-24,32),(-9,17)],32)
        blade(outer,inner,3.5)
        # Curved upper root sweeps across the head into a low rear wing.
        top=curve([(-23,54),(-13,43),(-8,51),(0,47)],22)
        bottom=curve([(0,42),(-9,41),(-16,39),(-20,41)],22)
        slab(top+[(9,43),(12,38),(4,40),(0,42)]+bottom[1:],3.2,bevel=.25)
        # A sculptural longitudinal fold follows the broad surface.
        fold=curve([(-20,48),(-25,37),(-19,26),(-10,18)],26)
        band([(x,y,1.0) for x,y in fold],1.0,3.0)
        neck=curve([(0,7),(1.5,19),(-3,28),(0,44)],30)
        band([(x,y,0) for x,y in neck],3.2,3.2)
        slab([(-2,32),(-6,30),(-3,36),(0,40),(2,36)],3.3,bevel=.25)
        return [(-18,25,0),(-15,22,0),(-12,20,0),(-22,35,0),(-21,42,0),(-10,43,0)]
    if kind=='staggered_cleaves':
        rail([(0,6),(0,35)],3,3)
        slab([(-3,28),(-3,47),(3,47),(3,28)],5,bevel=.35)
        slab([(-2.7,47),(-2.7,49),(2.7,49),(2.7,47)],4.4,bevel=.26)
        # Vertically staggered plates reproduce the approved illustration,
        # with a slight depth offset and a truly empty diagonal channel.
        upper=[(-26,54),(-23,44),(-19,40),(-16,41),(-4,36),(-2,38),(-2,44)]
        lower=[(-28,43),(-26,31),(-21,27),(-14,18),(-12,26),(-7,30),(-2,28),(-2,32),(-13,36)]
        slab(upper,2.8,z=-.8,bevel=.27)
        slab(lower,3.1,z=.8,bevel=.27)
        ridge([(-27,41),(-25,31),(-21,28),(-14,20),(-14,30),(-13,35)],(-21,33,2.4),2.6)
        return [(-23,42,0),(-19,39,0),(-15,38,0),(-11,36,0),(-8,34,0),(-5,34,0)]
    if kind=='folded_fan':
        rail([(0,6),(0,37)],3,3)
        slab([(-3,29),(-4,37),(-1,44),(3,39),(3,30)],4.4,bevel=.3)
        # Three broad fan leaves; narrow external seams end at a joined root.
        leaves=[([(-2,39),(-24,55),(-29,44),(-4,35)],(-18,46,2.5)),
                ([(-3,35),(-28,42),(-26,30),(-4,32)],(-17,35,2.3)),
                ([(-3,32),(-24,28),(-20,23),(-11,18),(-8,26)],(-15,26,2.4))]
        for outline,peak in leaves:ridge(outline,peak,2.5)
        slab([(2,32),(8,35),(2,40)],3.2,bevel=.25)
        return [(-23,48,0),(-26,43,0),(-26,36,0),(-23,30,0),(-18,24,0),(-13,21,0)]
    raise ValueError(kind)
