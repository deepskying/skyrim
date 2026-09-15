"""Pure geometric staves in the existing solid-light weapon style."""
import math
from mathutils import Vector


def build(spec, solid):
    def slab(points,depth=3,z=0,bevel=.2):
        n=len(points)
        verts=[(x,y,z+d) for d in (-depth/2,depth/2) for x,y in points]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        return solid(verts,faces,bevel)

    def band(points,width=2.5,depth=3,bevel=.2):
        pts=list(map(Vector,points));verts=[]
        for i,p in enumerate(pts):
            tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
            side=Vector((-tangent.y,tangent.x,0)).normalized()*width/2
            verts.extend(tuple(p+side*a+Vector((0,0,d*depth/2))) for a,d in ((-1,-1),(1,-1),(1,1),(-1,1)))
        faces=[(3,2,1,0),tuple(range(len(verts)-4,len(verts)))]
        for i in range(len(pts)-1):
            for j in range(4):faces.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
        return solid(verts,faces,bevel)

    def rail(points,width=2.5,depth=3,z=0,bevel=.2):
        return band([(x,y,z) for x,y in points],width,depth,bevel)

    def shaft(rings,sides=8):
        verts=[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        faces=[tuple(range(sides-1,-1,-1)),tuple(range(len(verts)-sides,len(verts)))]
        for k in range(len(rings)-1):
            for i in range(sides):
                a=k*sides+i;b=k*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
        return solid(verts,faces,.12)

    def diamond(x,y,rx,ry,depth=3,z=0):
        return slab([(x,y+ry),(x+rx,y),(x,y-ry),(x-rx,y)],depth,z,.18)

    # Uninterrupted palm prism, with collars kept outside the hand.
    shaft([(-12,1.23),(7,1.23)])
    shaft([(-14,1.25),(-13,1.85),(-12,1.85)])
    shaft([(7,1.85),(8,1.85),(9,1.25)])
    shaft([(-69,.10),(-65,1.7),(-60,1.3),(-34,1.3),(-14,1.25)])
    shaft([(9,1.25),(26,1.35),(30,2.1)])
    kind=spec['design']
    if kind=='riven_crown':
        slab([(0,27),(-13,39),(-18,51),(-10,63),(-12,50),(-7,41),(2,33)],3.4)
        slab([(0,29),(12,38),(16,51),(9,60),(12,48),(8,41),(-1,34)],3.4)
        slab([(-2,30),(-7,46),(-7,59),(0,70),(-2,55),(-1,43),(2,32)],3,-3)
        diamond(.3,49,3.3,6.8,3.5)
        rail([(0,12),(-3.5,20),(0,28),(3.5,20),(0,12)],1.1,1.3,2,.12)
        return
    if kind=='spiral_bough':
        # Two mathematical spiral arcs; no leaves or branches.
        pts=[]
        for i in range(33):
            t=i/32;a=math.radians(-80+310*t);r=14+2*t
            pts.append((r*math.cos(a),49+r*math.sin(a),-1.4))
        band(pts,3.1,3.0)
        pts=[]
        for i in range(29):
            t=i/28;a=math.radians(115+290*t);r=7.3+1.7*t
            pts.append((r*math.cos(a),49+r*math.sin(a),2.2))
        band(pts,2.4,2.6)
        rail([(0,27),(0,34),(3,35)],3,3,-1.4)
        for sign in (-1,1):
            pts=[]
            for i in range(17):
                t=i/16;a=math.pi*t
                pts.append((sign*2.7*math.sin(a),10+20*t,sign*2.8*math.sin(2*a)))
            band(pts,1.25,1.7,.14)
        diamond(0,49,2.4,3.5,3)
        return
    if kind=='suspended_balance':
        # Open interleaved rectangular brackets in distinct depth planes.
        rail([(-1,29),(-12,34),(-12,68),(-5,68)],3.2,3.6,-1.1)
        rail([(0,31),(12,31),(12,59),(6,59)],3.0,3.6,1.1)
        rail([(-9,57),(-9,38),(5,38)],1.5,2.2,2.8,.15)
        slab([(-3,44),(3,44),(3,52),(-3,52)],3.2,.2)
        slab([(-2,56),(2,56),(2,58),(-2,58)],2.4,.2,.13)
        rail([(-2.7,12),(-2.7,23),(2.7,23)],1.0,1.3,2,.1)
        return
    if kind=='broken_halo':
        angles=[math.radians(a) for a in (55,90,135,180,225,270,315,350)]
        pts=[(17*math.cos(a),49+17*math.sin(a),0) for a in angles]
        band(pts,3.5,3.6)
        rail([(-2,56),(-8,49),(0,41),(8,49),(4,53)],1.8,2.8,2.2,.18)
        diamond(0,49,2.1,3.0,3.2,2.2)
        rail([(0,28),(0,32),(-4,34)],3.4,3.6)
        rail([(-2.5,13),(2.5,18),(-2.5,23)],1.3,1.8,2,.13)
        return
    raise ValueError(kind)
