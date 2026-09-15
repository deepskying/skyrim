"""Four approved blunt warhammer heads on the vanilla two-hand grip frame."""
import math


def build(spec,slab,rail,frame,solid):
    def loft(rings,bevel=.3):
        n=len(rings[0]);vs=[v for ring in rings for v in ring]
        fs=[tuple(range(n-1,-1,-1)),tuple(range(len(vs)-n,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
        return solid(vs,fs,bevel)

    def spindle(rings,sides=8):
        return loft([[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for i in range(sides)] for y,r in rings],.12)

    def box(x0,x1,y0,y1,depth,z=0,bevel=.5):
        return slab([(x0,y0),(x0,y1),(x1,y1),(x1,y0)],depth,z,bevel)

    def annulus(outer,inner,depth,axis='z'):
        n=len(outer);assert n==len(inner)
        vs=[((x,y,d) if axis=='z' else (d,x,y)) for d in (-depth/2,depth/2) for loop in (outer,inner) for x,y in loop]
        fs=[]
        for i in range(n):
            j=(i+1)%n;fs.extend([(i,j,j+n,i+n),(i+2*n,i+3*n,j+3*n,j+2*n),(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n)])
        return solid(vs,fs,.35)

    spindle([(-39,1.3),(35,1.3)])
    # Two unbroken hand zones; collars are outside the original grip sections.
    spindle([(-32,1.4),(-15,1.4)])
    spindle([(-12,1.4),(17,1.4)])
    for y in (-33,-14,18,32):spindle([(y-.5,1.7),(y+.5,1.7)])
    spindle([(32,1.3),(36,2.5),(40,2.5)])
    kind=spec['design']

    if kind=='leaninganvil':
        # Large blunt left strike face, stepped anvil and smaller counterweight.
        box(-28,-15,48,70,18,bevel=.8)
        box(-29,-26,49,69,19,bevel=.6)
        slab([(-16,51),(-16,68),(-7,65),(-5,62),(4,61),(6,58),(18,57),(18,51)],13,bevel=.65)
        box(17,24,48,61,14,bevel=.65)
        box(22,25,49,60,15,bevel=.5)
        rail([(-11,53),(0,37),(10,52)],3.5,9)
        spindle([(-39,1.3),(-40,2.5),(-44,2.5),(-45,1.4)],6)
        return [(-28,54,7),(-28,61,7),(-28,67,7),(-21,70,6),(-10,64,6),(24,55,6)]

    if kind=='wovenbastion':
        for sign in (-1,1):
            box(sign*22-4,sign*22+4,44,68,18,bevel=.7)
            box(sign*24-2,sign*24+2,45,67,19,bevel=.55)
        # Four arched beams weave across the front and rear of the open cage.
        for up,front in ((1,1),(-1,-1),(1,-1),(-1,1)):
            rings=[]
            for i in range(33):
                t=i/32;x=-20+40*t
                y=56+up*(9 if front==up else 7)*math.sin(math.pi*t)
                z=front*6.5*math.sin(math.pi*t)
                rings.append([(x,y+dy,z+dz) for dy,dz in [(-1.5,-1.4),(1.5,-1.4),(1.5,1.4),(-1.5,1.4)]])
            loft(rings,.26)
        # Transverse belt in the YZ plane joins the haft to the cage arches.
        outer=[(56+13*math.cos(t),9.5*math.sin(t)) for t in (i*math.tau/32 for i in range(32))]
        inner=[(56+10.3*math.cos(t),6.8*math.sin(t)) for t in (i*math.tau/32 for i in range(32))]
        annulus(outer,inner,3.5,'x')
        spindle([(37,2),(44.5,2.6)])
        spindle([(-39,1.3),(-41,2.6),(-43.2,2.6),(-46,.08)],6)
        return [(-10,53,0),(-10,59,0),(10,53,0),(10,59,0),(-5,56,0),(5,56,0)]

    if kind=='splitbastion':
        box(-21,-3.5,43,66,17,bevel=.65)
        box(3.5,20,43,63,17,bevel=.65)
        for x0,x1,y in [(-19,-5.5,66),(-17,-7.5,68),(-15,-9.5,70),(5.5,18,63),(7.5,16,65),(9.5,14,67)]:
            box(x0,x1,y,y+2,14 if y in (66,63) else 11,bevel=.35)
        for z in (-8.5,8.5):
            box(-18.5,-6,46,63,1,z,.3);box(6,17.5,46,60,1,z,.3)
        box(-22,21,40,44.5,18,bevel=.5)
        box(-6,6,60,63,3,-7,.3)
        slab([(-2.4,32),(-9,40.8),(9,40.8),(2.4,32)],9,bevel=.45)
        for z in (-1.26,1.26):
            rail([(0,-30),(0,-16)],.45,.2,z);rail([(0,-10),(0,15)],.45,.2,z)
        spindle([(-39,1.3),(-40,2.1),(-42,2.1),(-42.4,1.5),(-44.5,1.5),(-45,1)],4)
        return [(0,47,0),(0,50,0),(0,53,0),(0,56,0),(0,59,0),(0,62,0)]

    if kind=='captivehalo':
        outer=[(18*math.cos(t),56+18*math.sin(t)) for t in (math.pi/8+i*math.tau/8 for i in range(8))]
        inner=[(12.4*math.cos(t),56+12.4*math.sin(t)) for t in (math.pi/8+i*math.tau/8 for i in range(8))]
        annulus(outer,inner,10)
        for x0,x1 in ((-26,-16),(16,26)):
            box(x0,x1,43,68,18,bevel=.7)
            box(x0+.8,x1-.8,45,66,19,bevel=.5)
        rail([(-11,43),(0,31),(11,43)],3.2,7)
        rail([(-9,39),(0,29),(9,39)],1.7,5,-1)
        for t in (math.pi/2,7*math.pi/6,11*math.pi/6):
            rail([(2.3*math.cos(t),56+2.3*math.sin(t)),(12.9*math.cos(t),56+12.9*math.sin(t))],1.6,2.5,-2.5)
        solid([(0,60.5,0),(-3.5,56,0),(0,51.5,0),(3.5,56,0),(0,56,3.5),(0,56,-3.5)],
              [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],.2)
        spindle([(-39,1.3),(-41,2.8),(-46,.08)],4)
        return [(-6,58,1),(6,58,1),(-5,52,1),(5,52,1),(0,63,1),(0,49,1)]
    raise ValueError(kind)
