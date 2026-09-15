"""Second mace concepts: staggered teeth, triangular cage, stepped head, star core."""
import math
from mathutils import Vector,Matrix


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8,phase=math.pi/8):
        v=[(rx*math.cos(phase+i*math.tau/sides),y,rz*math.sin(phase+i*math.tau/sides)) for y,rx,rz in rings for i in range(sides)]
        faces=[tuple(range(sides-1,-1,-1)),tuple(range(len(v)-sides,len(v)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
        return solid(v,faces,.12)

    def tooth(center,direction,width,length):
        c=Vector(center);d=Vector(direction).normalized();u=d.cross(Vector((0,1,0)))
        if u.length<.1:u=d.cross(Vector((1,0,0)))
        u.normalize();v=d.cross(u)
        pts=[c+u*a*width/2+v*b*width/2 for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]+[c+d*length]
        return solid(pts,[(3,2,1,0),(0,1,4),(1,2,4),(2,3,4),(3,0,4)],.14)

    spindle([(-8,1.2,1.2),(5,1.2,1.2)])
    for y in (-7.7,4.5):spindle([(y-.2,1.33,1.33),(y+.2,1.33,1.33)])
    spindle([(5,1.6,1.6),(26,1.8,1.8)])
    kind=spec['design']
    if kind=='raketeeth':
        # Broad hexagonal faces carry three alternating rows of three teeth.
        spindle([(24,2.1,2.1),(26,3,3),(27,5.5,5.5),(48,5.5,5.5),(49.5,2,2)],6,math.pi/6)
        for row,y in enumerate((30.5,37.5,44.5)):
            for j in range(3):
                a=j*math.tau/3+(row%2)*math.pi/3
                tooth((4.6*math.cos(a),y,4.6*math.sin(a)),(math.cos(a),0,math.sin(a)),4.1,5)
        tooth((0,49,0),(0,1,0),3.4,2.7)
        spindle([(5,2,2),(6.2,2.8,2.8),(7.5,2,2)],6)
        spindle([(-8,1.3,1.3),(-9.5,2.7,2.7),(-10.5,2.7,2.7),(-14,.12,.12)],6)
        return [(-10,30,0),(10,30,0),(-10,37,0),(10,37,0),(-10,44,0),(10,44,0)]

    if kind=='tricage':
        spindle([(24,2,2),(26,5,5),(27,5,5)],3,math.pi/2)
        spindle([(27,2.2,2.2),(29,2.8,2.8),(44,2.8,2.8),(47,2.2,2.2)],3,math.pi/2)
        spindle([(46,5,5),(47.5,5,5),(48,2,2)],3,math.pi/2)
        # Three straight angular ribs. At each elbow, radial width 2.4 and
        # tangential thickness 2.5 leave real windows beside the solid core.
        for j in range(3):
            a=math.pi/2+j*math.tau/3;radial=Vector((math.cos(a),0,math.sin(a)));tangent=Vector((-math.sin(a),0,math.cos(a)))
            verts=[]
            for y,r in [(26,3.4),(34,8),(39,8),(47,3.4)]:
                for dr,dt in [(-1.2,-1.25),(1.2,-1.25),(1.2,1.25),(-1.2,1.25)]:verts.append(radial*(r+dr)+tangent*dt+Vector((0,y,0)))
            faces=[(3,2,1,0),(12,13,14,15)]
            for k in range(3):
                for i in range(4):faces.append((k*4+i,k*4+(i+1)%4,(k+1)*4+(i+1)%4,(k+1)*4+i))
            solid(verts,faces,.22)
            tooth(radial*8.8+Vector((0,37,0)),radial,3.6,4.2)
        tooth((0,47.7,0),(0,1,0),3.4,4)
        spindle([(5,2,2),(7,3.6,3.6),(8,1.7,1.7)],3,math.pi/2)
        spindle([(-8,1.2,1.2),(-10,2.8,2.8),(-12.3,2.8,2.8),(-13.5,1.2,1.2)],6)
        return [(-12,35,0),(12,35,0),(-9,42,0),(9,42,0),(-5,48,0),(5,48,0)]

    if kind=='stepbreaker':
        # Five broad octagonal tiers with shallow recessed seams; a full core
        # physically joins all tiers and the shaft beneath them.
        spindle([(24,2,2),(26,3.2,3.2),(48,3.2,3.2)],8)
        for index,(y,r,h) in enumerate([(28,4.5,3),(32,6.5,4.4),(37.4,8.5,6),(43,6.5,4.4),(47,4.5,3)]):
            spindle([(y-h/2,r-.7,r-.7),(y-h/2+.6,r,r),(y+h/2-.6,r,r),(y+h/2,r-.7,r-.7)],8)
            if index in (1,2,3):
                for j in range(4):
                    a=j*math.pi/2+(index%2)*math.pi/4
                    tooth((r*.91*math.cos(a),y,r*.91*math.sin(a)),(math.cos(a),0,math.sin(a)),2.8 if index!=2 else 3.6,2.8)
        spindle([(5,2.2,2.2),(6.5,3,3),(8,3,3),(8.5,1.7,1.7)],8)
        for y in (-5,-1.5,2):spindle([(y-.15,1.3,1.3),(y+.15,1.3,1.3)])
        spindle([(-8,1.3,1.3),(-9.5,2.7,2.7),(-11.5,2.7,2.7),(-13,1.7,1.7)],8)
        return [(-11,32,0),(11,32,0),(-12,38,0),(12,38,0),(-9,44,0),(9,44,0)]

    if kind=='starcore':
        # Exact rhombic dodecahedron: 6 axial and 8 corner vertices, 12 faces.
        raw=[Vector(v) for v in [(2,0,0),(-2,0,0),(0,2,0),(0,-2,0),(0,0,2),(0,0,-2)]]
        raw += [Vector((x,y,z)) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        rot=Matrix.Rotation(.22,3,'Z')@Matrix.Rotation(.2,3,'Y');origin=Vector((0,38,0));scale=4.2
        faces=[]
        for a,b in [(0,1),(1,2),(0,2)]:
            for sa in (-1,1):
                for sb in (-1,1):
                    normal=Vector((0,0,0));normal[a]=sa;normal[b]=sb
                    ids=[i for i,p in enumerate(raw) if abs(normal.dot(p)-2)<1e-5]
                    center=sum((raw[i] for i in ids),Vector())/4
                    u=(raw[ids[0]]-center).normalized();v=normal.normalized().cross(u)
                    ids.sort(key=lambda i:math.atan2((raw[i]-center).dot(v),(raw[i]-center).dot(u)))
                    faces.append(tuple(ids))
        solid([rot@(p*scale)+origin for p in raw],faces,.28)
        for normal,length in [((1,1,0),5),((-1,1,0),5.6),((0,1,1),4.2),((1,0,1),4.8),((-1,0,1),5.2),((0,1,-1),4)]:
            n=Vector(normal);center=rot@(n*scale*.97)+origin
            tooth(center,rot@n,4.5,length)
        # Fork follows the lower diamond shoulders and keeps the head seated.
        for sign in (-1,1):slab([(sign*1,24),(sign*3,25),(sign*5.3,32),(sign*3.1,33),(sign*1.3,27)],3.5,bevel=.25)
        spindle([(23,2,2),(26,2.8,2.8),(31,2.0,2.0)],6)
        slab([(-3.8,8),(-1.8,5),(0,6),(1.8,5),(3.8,8),(0,7.2)],3.2,bevel=.22)
        spindle([(-8,1.3,1.3),(-10.5,2.8,2.8),(-14,.1,.1)],4,math.pi/4)
        return [(-11,42,3),(11,42,3),(-10,33,4),(10,35,4),(-5,49,2),(5,49,-3)]
    raise ValueError(kind)
