"""Four approved solid-light mace heads, modelled in the IronMace hand frame."""
import math
from mathutils import Vector,Matrix
from greatswords2_geometry import curve


def build(spec,slab,rail,frame,solid):
    def box(cx,cy,cz,w,h,d,angle=0,tilt=0):
        rot=Matrix.Rotation(tilt,3,'Z')@Matrix.Rotation(angle,3,'Y')
        pts=[rot@Vector((x*w/2,y*h/2,z*d/2))+Vector((cx,cy,cz))
             for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        return solid(pts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],.32)

    def spindle(rings,sides=8,phase=math.pi/8):
        v=[(rx*math.cos(phase+i*math.tau/sides),y,rz*math.sin(phase+i*math.tau/sides)) for y,rx,rz in rings for i in range(sides)]
        faces=[tuple(range(sides-1,-1,-1)),tuple(range(len(v)-sides,len(v)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
        return solid(v,faces,.12)

    def tooth(center,direction,width,length):
        c=Vector(center);d=Vector(direction).normalized()
        u=d.cross(Vector((0,1,0)))
        if u.length<.1:u=d.cross(Vector((1,0,0)))
        u.normalize();v=d.cross(u)
        pts=[c+u*a*width/2+v*b*width/2 for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]+[c+d*length]
        solid(pts,[(3,2,1,0),(0,1,4),(1,2,4),(2,3,4),(3,0,4)],.14)

    # Straight palm-sized handle, sturdy shaft and independent decorative ends.
    spindle([(-8,1.2,1.2),(5,1.2,1.2)])
    for y in (-7.7,-4.6,-1.5,1.6,4.5):spindle([(y-.18,1.33,1.33),(y+.18,1.33,1.33)])
    spindle([(5,1.6,1.6),(25,1.8,1.8)])
    kind=spec['design']
    if kind=='bastion':
        # A heavy square head with recessed horizontal courses and four teeth.
        box(0,36,0,13,10,13)
        box(0,29.7,0,13,2.8,13);box(0,42.3,0,13,2.8,13)
        box(0,43.9,0,10,1.8,10);box(0,45.3,0,7,1.4,7)
        tooth((0,45.9,0),(0,1,0),5,4)
        for x,z in [(1,0),(0,1),(-1,0),(0,-1)]:tooth((x*6.35,36,z*6.35),(x,0,z),6,5.5)
        box(0,26,0,6,3,6)
        spindle([(26.8,2.5,2.5),(30,2.5,2.5)])
        spindle([(4.8,2.6,2.6),(6.5,3.6,3.6),(8.5,2,2)],4,math.pi/4)
        spindle([(-8,1.4,1.4),(-9,2.7,2.7),(-12,2.7,2.7),(-13,1.8,1.8)],4,math.pi/4)
        return [(-12,36,0),(12,36,0),(0,36,12),(-7.5,43,0),(7.5,43,0),(0,46,-6)]

    if kind=='spiralthorn':
        spindle([(24,3,3),(26,4,4),(29,2.6,2.6),(45,2.6,2.6),(46,3,3)],6)
        tooth((0,46,0),(0,1,0),4.6,5)
        # Three separate helical fins, each an enclosed ruled solid. The gaps
        # extend all the way through around a thick central hexagonal core.
        for fin in range(3):
            verts=[];steps=24
            for j in range(steps+1):
                t=j/steps;y=26+t*19;a=fin*math.tau/3-.8+t*1.45
                outer=2.8+5.8*math.sin(math.pi*t)**.72
                for radius,offset in [(2.1,-.8),(outer,-.8),(outer,.8),(2.1,.8)]:
                    verts.append((radius*math.cos(a)-offset*math.sin(a),y,radius*math.sin(a)+offset*math.cos(a)))
            faces=[(3,2,1,0),(steps*4,steps*4+1,steps*4+2,steps*4+3)]
            for j in range(steps):
                for i in range(4):faces.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
            solid(verts,faces,.16)
            a=fin*math.tau/3+.36
            tooth((7*math.cos(a),41,7*math.sin(a)),(math.cos(a),.4,math.sin(a)),3.5,4.5)
        rail(curve([(-4,8),(-2,4.5),(2,4.5),(4,8)],24),1.1,2.6)
        spindle([(-8,1.3,1.3),(-10,2.4,2.4),(-14,.08,.08)],6)
        return [(10,37,0),(-10,37,0),(0,37,10),(8,42,4),(-8,42,-4),(0,46,-5)]

    if kind=='ringwarden':
        cx,cy=0,37;n=8
        # Thick eight-sided annulus, small hole, substantial front-back depth.
        verts=[(r*math.cos(math.pi/8+i*math.tau/n),cy+r*math.sin(math.pi/8+i*math.tau/n),z)
               for z in (-4.5,4.5) for r in (10,4) for i in range(n)]
        faces=[]
        for i in range(n):
            j=(i+1)%n;faces.extend([(i,j,j+8,i+8),(i+16,i+24,j+24,j+16),(i,i+16,j+16,j),(i+8,j+8,j+24,i+24)])
        solid(verts,faces,.38)
        for angle in (0,math.pi/4,math.pi/2,3*math.pi/4,math.pi):
            d=(math.cos(angle),math.sin(angle),0)
            tooth((d[0]*9.3,37+d[1]*9.3,0),d,4.2,4.5)
        for sign in (-1,1):
            slab([(sign*1.1,23),(sign*3.4,25),(sign*6,30),(sign*3.8,30),(sign*1.1,26)],5,bevel=.3)
        spindle([(23,2.4,2.4),(26,2.4,2.4)])
        spindle([(5,2.2,2.2),(6.5,3,3),(8,3,3),(8.5,1.8,1.8)])
        spindle([(-8,1.3,1.3),(-9.2,2.6,2.6),(-12,2.6,2.6),(-13,1.7,1.7)])
        return [(-14,37,0),(14,37,0),(-11,44,0),(11,44,0),(-5,51,0),(5,51,0)]

    if kind=='shearblocks':
        # Two offset, rotated volumes overlap around a strong central core.
        spindle([(23,2.2,2.2),(26,3.5,3.5),(43,3.5,3.5)])
        box(1.2,31,0,11,11,10,-.10)
        box(-1.5,41,.7,12,11,11,.51,.28)
        # Offset cube corners carry four opposing wedge studs.
        for center,direction in [((6.5,32,0),(1,0,0)),((-4.5,30,0),(-1,0,0)),
                                 ((-7.0,43,3),(-1,.2,.3)),((4.0,42,4),(1,.1,.5))]:tooth(center,direction,4.8,4.6)
        # Seat the cap in the tilted cube's top face rather than world-horizontal.
        tooth((-1.5-5.25*math.sin(.28),41+5.25*math.cos(.28),.7),(-math.sin(.28),math.cos(.28),0),7,2.7)
        slab([(-3.5,8),(-1.8,5),(0,6.3),(1.8,5),(3.5,8),(0,7.3)],3.4,bevel=.23)
        spindle([(-8,1.3,1.3),(-9.4,2.6,2.6),(-10.5,2.8,2.8),(-14,.08,.08)],6)
        return [(-11,43,3),(10,42,4),(11,32,0),(-10,30,0),(-5,49,0),(4,48,3)]
    raise ValueError(kind)
