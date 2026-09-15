"""Approved first war-axe concepts in the vanilla WeaponAxe hand frame.

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

    # Uninterrupted palm zone, with collars outside the hand.
    spindle([(-8,1.2),(5,1.2)])
    spindle([(-9,1.5),(-8,1.9),(-7.4,1.9)])
    spindle([(4.6,1.9),(5.4,1.9),(7,1.4),(25,1.8),(43,2)])
    spindle([(-14.5,.25),(-12,2.4),(-10,2.4),(-8.8,1.5)])
    spindle([(24,2.2),(25,2.7),(26,2.2)])
    kind=spec['design']
    if kind=='riven_crown':
        outer=curve([(-18,54),(-29,42),(-28,26),(-16,18)],24)
        inner=curve([(-18,54),(-15,40),(-17,28),(-16,18)],24)
        blade(outer,inner,3.2)
        # Three members enclose a true triangular cutout.
        rail([(-19,48),(-2,43)],3.8,3.5)
        rail([(-19,27),(-1,38)],3.3,3.5)
        slab([(-3,35),(-3,47),(2.7,47),(2.7,35)],4,bevel=.3)
        slab([(2,36),(12,36),(12,39),(9,39),(9,42),(6,42),(6,44),(2,44)],3,bevel=.26)
        return [(-24,42,0),(-26,36,0),(-24,29,0),(-20,24,0),(-18,49,0),(-12,43,0)]
    if kind=='entwined_bough':
        outer=curve([(-18,54),(-33,40),(-28,25),(-11,20)],30)
        inner=curve([(-18,54),(-20,38),(-22,30),(-11,20)],30)
        blade(outer,inner,2.7)
        # Two load-bearing arches cross at distinct depths and join at ends.
        p=curve([(-20,48),(-8,49),(-3,47),(0,41)],28)
        band([(x,y,0) for x,y in p],3.2,2.8)
        p=curve([(-16,24),(-4,22),(0,29),(0,41)],28)
        band([(x,y,0) for x,y in p],2.7,2.8)
        for sign in (-1,1):
            p=curve([(-20,40),(-8,37),(-11,30),(0,27)],28) if sign==1 else curve([(-15,26),(-13,37),(-6,36),(0,41)],28)
            band([(x,y,sign*2.7*math.sin(math.pi*i/(len(p)-1))) for i,(x,y) in enumerate(p)],1.8,1.6)
        return [(-19,44,0),(-17,40,0),(-15,36,0),(-16,31,0),(-10,28,0),(-6,38,0)]
    if kind=='severed_bay':
        # Open lower bay; no face crosses the deep recess.
        outer=[(-24,52),(-25,42),(-25,34),(-23,27),(-18,19)]
        inner=[(-17,47),(-16,41),(-17,35),(-15,29),(-12,24)]
        blade(outer,inner,3.2)
        slab([(-24,52),(-16,47),(-3,44),(2,43),(2,37),(-6,39),(-14,40),(-17,36),(-19,35)],3.2,bevel=.26)
        slab([(-23,27),(-17,29),(-13,28),(-13,25),(-10,24),(-12,21),(-18,19)],3.2,bevel=.25)
        slab([(-3,27),(-3,46),(2.5,46),(2.5,27)],4,bevel=.3)
        slab([(2,38),(6,38),(6,43),(2,44)],3.2,bevel=.23)
        return [(-13,37,0),(-12,34,0),(-11,31,0),(-10,28,0),(-20,43,0),(-22,35,0)]
    if kind=='broken_wheel':
        cx,cy=-10,37
        # Single C-shaped polygonal structural arc: top and right are solid;
        # only the lower sector remains absent, as in the corrected concept.
        angles=[math.radians(a) for a in range(-35,251,15)]
        outer=[(cx+14*math.cos(a),cy+14*math.sin(a)) for a in angles]
        inner=[(cx+10.8*math.cos(a),cy+10.8*math.sin(a)) for a in angles]
        verts=[(x,y,z) for z in (-1.45,1.45) for loop in (outer,inner) for x,y in loop]
        n=len(angles);faces=[]
        for i in range(n-1):
            j=i+1
            faces.extend([(i,j,j+n,i+n),(i+2*n,i+3*n,j+3*n,j+2*n),(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n)])
        faces.extend([(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)])
        solid(verts,faces,.22)
        a=[math.radians(x) for x in range(105,251,5)]
        blade([(cx+18*math.cos(t),cy+18*math.sin(t)) for t in a],[(cx+13*math.cos(t),cy+13*math.sin(t)) for t in a],3.1)
        slab([(-2,24),(-3,28),(0,33),(3.5,30),(2,24)],3.5,bevel=.25)
        return [(-9,49,0),(-17,45,0),(-20,38,0),(-18,30,0),(-10,25,0),(-1,39,0)]
    raise ValueError(kind)
