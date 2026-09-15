"""Third long-dagger concepts: eccentric mass, interlaced ribbons and real torsion."""
import math


def build(spec,slab,rail,frame,solid):
    def curve(a,b,c,d,count=18):
        return [tuple((1-t)**3*a[j]+3*(1-t)**2*t*b[j]+3*(1-t)*t*t*c[j]+t**3*d[j] for j in range(2)) for t in (i/count for i in range(count+1))]

    def loft(rings,bevel=.12):
        n=len(rings[0]);vs=[v for ring in rings for v in ring]
        fs=[tuple(range(n-1,-1,-1)),tuple(range(len(vs)-n,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
        return solid(vs,fs,bevel)

    def spindle(rings,sides=8):
        return loft([[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for i in range(sides)] for y,r in rings],.1)

    def luminous_loft(rings):
        # Explicit bevel strips avoid Blender globally clamping all bevels to
        # the tiny terminal cross-section at the tip of these long blades.
        cut=[]
        for ring in rings:
            expanded=[]
            for i,p in enumerate(ring):
                for adjacent in (ring[(i-1)%4],ring[(i+1)%4]):
                    expanded.append(tuple(.9*p[j]+.1*adjacent[j] for j in range(3)))
            cut.append(expanded)
        obj=loft(cut,0)
        for polygon in obj.data.polygons:
            if polygon.index>=2 and (polygon.index-2)%8%2==0:polygon.material_index=1
        return obj

    kind=spec['design']
    spindle([(-7,1.12),(4.6,1.12)])
    for y in (-6.7,4.5):spindle([(y-.18,1.29),(y+.18,1.29)])
    spindle([(4.4,1.05),(10,1.2)])

    if kind=='offsetfang':
        upper=curve((-8,30),(-3.5,34),(1,40),(2.1,45),20)
        right=curve((2.1,45),(2.6,34),(1.1,19),(3.3,12),22)[1:]
        root=curve((3.3,12),(1.1,10),(1.6,8.3),(2.7,6.8),10)[1:]
        lower=curve((-1.6,7),(-1.8,13),(-1.9,22),(-8,30),20)
        slab(upper+right+root+lower[:-1],2.8,bevel=.34)
        slab([(-4.9,7.9),(-2.5,9.1),(1.6,7.7),(2.8,5.5),(-1.4,6.3),(-3.9,4.9)],2.8,bevel=.22)
        rail([(1.5,7),(4.7,8.5),(6.3,10)],1.35,2.5)
        slab([(5.8,8.5),(5.8,13.6),(7.2,13.2),(7.2,8.2)],2.7,bevel=.2)
        spindle([(-7,1.1),(-8.4,2.1),(-9.4,1.9),(-12.3,.06)],6)
        return [(-7.4,30,1),(-5.8,32,1),(-4.5,25,1),(-3.1,21,1),(1.8,36,1),(6.5,12,1)]

    if kind=='braidbranch':
        # Opposite phases exchange front/back at each crossing. Crossings are
        # separated in depth, while both ribbons join at the root and single tip.
        for sign in (-1,1):
            rings=[]
            for i in range(73):
                t=i/72;y=9+36*t
                x=sign*3.05*math.sin(3*math.pi*t)
                z=sign*1.55*math.cos(3*math.pi*t)*math.sin(math.pi*t)**.35
                width=(.85+1.05*math.sin(math.pi*t)**.6)*(min(1,(1-t)/.1))+.035
                depth=.72*min(1,(1-t)/.08)+.025
                rings.append([(x-width/2,y,z),(x,y,z+depth),(x+width/2,y,z),(x,y,z-depth)])
            luminous_loft(rings)
        slab([(-1.6,7),(-2,10.5),(0,12.5),(2,10.5),(1.6,7)],2.7,bevel=.2)
        rail([(-6,11),(-5.8,8.6),(-2,6.5),(0,5.8),(2,6.5),(5.8,8.6),(6,11)],1.35,2.7)
        slab([(0,7),(-1.2,9),(0,10.7),(1.2,9)],3,bevel=.2)
        for a,b in [((0,-7),(-2.2,-9.9)),((-2.2,-9.9),(0,-13)),((0,-13),(2.2,-9.9)),((2.2,-9.9),(0,-7))]:rail([a,b],.95,1.9)
        return [(-2.8,15,.8),(2.8,15,.8),(-2.8,27,.8),(2.8,27,.8),(-2.8,39,.8),(2.8,39,.8)]

    if kind=='twinchime':
        inner=[(1.2*math.cos(t),15+1.2*math.sin(t)) for t in (math.pi+i*math.pi/14 for i in range(1,15))]
        slab([(-1.7,8),(-2,11),(-4.4,15),(-3.7,45),(-1.2,38),(-1.2,15)]+inner+
             [(1.2,39),(3.7,34.5),(4.4,15),(2,11),(1.7,8)],2.8,bevel=.28)
        slab([(-6.5,7.4),(-5.5,8.5),(-1.4,8),(0,9),(1.4,8),(5.5,8.5),(6.5,7.4),
              (6.2,4.9),(5.2,5.9),(4.8,6.7),(-4.8,6.7),(-5.2,5.9),(-6.2,4.9)],2.8,bevel=.23)
        slab([(0,6.8),(-.9,8.2),(0,9.5),(.9,8.2)],3.1,bevel=.14)
        for z in (-1.08,1.08):rail([(0,-5),(0,3)],.28,.18,z)
        spindle([(-7,1.15),(-7.5,1.65),(-8.2,1.65),(-8.4,1.2),(-9.1,1.2),(-9.3,1.65),(-10,1.65),(-11.6,.06)])
        return [(0,18,0),(0,22,0),(0,26,0),(0,30,0),(0,34,0),(0,37,0)]

    if kind=='twistprism':
        # A single solid loft rotates its diamond section by half a turn.
        rings=[]
        sections=[(9,1.35),(13,2.1),(19,3.1),(25,2.65),(31,2.9),(37,2.4),(41,1.4),(45,.035)]
        for y,w in sections:
            t=(y-9)/36;theta=math.pi*t
            depth=.85*min(1,(45-y)/4)+.035
            rings.append([(x*math.cos(theta)-z*math.sin(theta),y,x*math.sin(theta)+z*math.cos(theta)) for x,z in [(-w,0),(0,depth),(w,0),(0,-depth)]])
        luminous_loft(rings)
        slab([(-5.3,8.4),(-2.4,8.2),(-1.4,9.8),(1.5,9.3),(3,7.4),(6.1,9.4),
              (4.3,5.8),(2,6.5),(0,5.7),(-3.4,6.5)],2.8,bevel=.24)
        for a,b in [((0,5.4),(-1.7,8)),((-1.7,8),(0,10.7)),((0,10.7),(1.7,8)),((1.7,8),(0,5.4))]:rail([a,b],.65,3)
        spindle([(-7,1.1),(-8.4,1.9),(-12.5,.06)],4)
        return [(-1.5,14,.8),(-1.7,20,1.6),(.1,26,2.6),(1.8,32,1.8),(2,37,.9),(1.1,41,.8)]
    raise ValueError(kind)
