"""Second approved warhammer set: fault blocks, helix drum, ram and rotated frames."""
import math

def build(spec,slab,rail,frame,solid):
    def loft(rings,bevel=.25):
        n=len(rings[0]);vs=[v for ring in rings for v in ring]
        fs=[tuple(range(n-1,-1,-1)),tuple(range(len(vs)-n,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
        return solid(vs,fs,bevel)
    def shaft(profile,sides=8):
        return loft([[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for i in range(sides)] for y,r in profile],.12)
    def barrel(profile,cy=56,sides=8,angle=math.pi/8):
        return loft([[(x,cy+r*math.cos(angle+i*math.tau/sides),r*math.sin(angle+i*math.tau/sides)) for i in range(sides)] for x,r in profile],.32)
    def box(x0,x1,y0,y1,depth,z=0,bevel=.5):
        return slab([(x0,y0),(x0,y1),(x1,y1),(x1,y0)],depth,z,bevel)
    def ring_x(x,angle=0):
        # Chamfered square annulus in the YZ plane, around the transverse head axis.
        outer=[(-9,-13),(9,-13),(13,-9),(13,9),(9,13),(-9,13),(-13,9),(-13,-9)]
        inner=[(-6.5,-9.5),(6.5,-9.5),(9.5,-6.5),(9.5,6.5),(6.5,9.5),(-6.5,9.5),(-9.5,6.5),(-9.5,-6.5)]
        c,s=math.cos(angle),math.sin(angle)
        vs=[(x+d,56+y*c-z*s,y*s+z*c) for d in (-1.8,1.8) for loop in (outer,inner) for y,z in loop]
        n=8;fs=[]
        for i in range(n):
            j=(i+1)%n
            fs.extend([(i,j,j+n,i+n),(i+2*n,i+3*n,j+3*n,j+2*n),(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n)])
        return solid(vs,fs,.32)

    shaft([(-39,1.3),(35,1.3)])
    shaft([(-32,1.4),(-15,1.4)])
    shaft([(-12,1.4),(17,1.4)])
    for y in (-33,-14,18,32):shaft([(y-.5,1.7),(y+.5,1.7)])
    shaft([(32,1.3),(36,2.4),(40,2.4)])
    kind=spec['design']
    if kind=='faultpress':
        # Three connected tapered blocks descend toward the smaller counterweight.
        for x0,x1,y0,y1,depth in [(-25,-8,50,70,19),(-9,8,47,65,16),(7,24,44,59,13)]:
            slab([(x0,y0),(x0,y1),(x1,y1-4),(x1,y0-1.5)],depth,bevel=.65)
        box(-28,-24,49,72,21,bevel=.65)
        for x,y0,y1,d in [(-9,48,67,18),(7,45,62,15),(23,43,57,14)]:
            box(x-1,x+1,y0,y1,d,bevel=.25)
        # The dogleg neck is solid, unlike the first set's open triangular yoke.
        slab([(-2.4,33),(-2.4,39),(-8,43),(-8,51),(-3,52),(-3,46),(3,42),(3,33)],8,bevel=.45)
        shaft([(-39,1.3),(-40,2.5),(-44,2.5),(-46,1.7)],4)
        return [(-28,51,8),(-28,56,8),(-28,62,8),(-28,68,8),(-10,66,9),(8,60,7)]

    if kind=='spiraldrum':
        barrel([(-26,13.8),(-22,13.8),(-20,11)],sides=6,angle=0)
        barrel([(20,11),(22,13.8),(26,13.8)],sides=6,angle=0)
        barrel([(-22,2),(22,2)],sides=8)
        # Three broad helical beams, each physically terminating in both end caps.
        for phase in (0,math.tau/3,2*math.tau/3):
            rings=[]
            for i in range(49):
                t=i/48;x=-21+42*t;a=phase+t*math.pi*1.2
                rings.append([(x,56+r*math.cos(a+b),r*math.sin(a+b)) for r,b in [(9.3,-.23),(12,-.23),(12,.23),(9.3,.23)]])
            loft(rings,.22)
        # Center saddle connects the haft to axle without obstructing the windows.
        box(-3,3,37,55,5,bevel=.5)
        shaft([(-39,1.3),(-41,2.5),(-44,2.5),(-46,1.2)],6)
        return [(-15,60,5),(-9,51,4),(-3,61,-4),(4,52,6),(10,60,-5),(16,53,-4)]

    if kind=='crossram':
        barrel([(-27,15),(-22,15),(-20,7),(18,7),(21,10),(26,10)],sides=8)
        # Blunt end rims and two raised collars break up the central prism.
        barrel([(-28,14),(-26,14)],sides=8)
        barrel([(25,10.5),(27,10.5)],sides=8)
        for x in (-12,11):barrel([(x-1.5,9.3),(x+1.5,9.3)],sides=8)
        # Three slim luminous strips across each broad visible side.
        for z in (-6.55,6.55):
            for y in (53,56,59):
                rail([(-19,y),(19,y)],.45,.28,z)
        rail([(-12,51),(-12,44),(0,36),(11,44),(11,51)],3.0,6)
        shaft([(-39,1.3),(-41,2.5),(-44,2.5),(-46,1.4)],8)
        return [(-28,52,8),(-28,56,8),(-28,61,8),(27,53,5),(27,57,5),(27,61,5)]

    if kind=='orbitalmaul':
        # Three separated transverse frames, rotated relative to one another.
        for x,a in [(-12,-.42),(0,0),(12,.42)]:ring_x(x,a)
        for y,z in [(48,-8),(48,8),(64,-8),(64,8)]:
            box(-22,22,y-.9,y+.9,1.8,z,.2)
        # Thick square ends are the actual striking surfaces.
        box(-25,-20,43,69,24,bevel=1)
        box(20,25,43,69,24,bevel=1)
        box(-26,-24,45,67,21,bevel=.4)
        box(24,26,45,67,21,bevel=.4)
        # Core is attached, with a solid axle, rather than detached floating mesh.
        barrel([(-21,1.2),(21,1.2)])
        solid([(0,61,0),(-4,56,0),(0,51,0),(4,56,0),(0,56,4),(0,56,-4)],
              [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],.22)
        slab([(-2.4,34),(-5,41),(-5,45),(5,45),(5,41),(2.4,34)],7,bevel=.45)
        shaft([(-39,1.3),(-41,2.8),(-46,.1)],4)
        return [(-7,60,4),(7,60,4),(-7,52,4),(7,52,4),(-17,57,5),(17,57,5)]
    raise ValueError(kind)
