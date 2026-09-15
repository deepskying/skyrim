"""Approved longer-bladed daggers in the vanilla IronDagger hand frame."""
import math


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8):
        vs=[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        fs=[tuple(range(sides-1,-1,-1)),tuple(range(len(vs)-sides,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
        return solid(vs,fs,.1)

    def window(outer,inner,depth=2.1):
        n=len(outer);assert n==len(inner)
        vs=[(x,y,d) for d in (-depth/2,depth/2) for loop in (outer,inner) for x,y in loop]
        fs=[]
        for i in range(n):
            j=(i+1)%n
            fs.extend([(i,j,j+n,i+n),(i+2*n,i+3*n,j+3*n,j+2*n),(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n)])
        return solid(vs,fs,.18)

    # Single-hand grip, independent of the longer blade; no guard in palm zone.
    spindle([(-7,1.12),(4.6,1.12)])
    for y in (-6.6,4.5):spindle([(y-.2,1.3),(y+.2,1.3)])
    spindle([(4.5,1.05),(8,1.2)])
    kind=spec['design']
    if kind=='cornerfang':
        slab([(-3.6,10),(-3.6,19),(-1.8,22),(-3.6,25),(-3.6,43),(4,34),(4.8,12),(2.6,10)],2.3,bevel=.38)
        slab([(-2.1,6.5),(-2.2,10),(2.2,10),(2.4,6.5)],2.7,bevel=.25)
        slab([(-5,7),(-3.5,5.5),(1.5,6),(5.4,4.9),(4.5,7.6),(-4,8)],2.5,bevel=.22)
        spindle([(-7,1.1),(-8,1.8),(-10.5,1.8),(-11.2,1.3)],4)
        return [(-3.5,39,.8),(3,35,.8),(4.6,16,.8),(-3.5,27,.8),(-2,21,.8),(2.5,11,.8)]

    if kind=='returnfang':
        # Main hooked cutting band; side rib encloses a real curved root slit.
        slab([(-2,9),(-2.4,15),(-2.3,24),(-.5,33),(3,40),(8,44),(11,42),(12.5,38),(12,34),
              (10.8,38),(8.5,39),(6,38),(3.5,35),(1.7,31),(1,25),(1.5,19),(3.4,14),(2,11),(3,8)],2.2,bevel=.3)
        window([(-4,12),(-6,17),(-5,25),(-2,34),(-1,27),(-1.7,20)],
               [(-3.7,15.5),(-4.6,18),(-3.7,25),(-2.3,30),(-2.2,26),(-2.8,20)],1.9)
        slab([(-1.6,6.7),(-1.6,10.5),(1.6,10.5),(1.6,6.7)],2.4,bevel=.2)
        slab([(-5.3,7),(-6.1,10),(-5.7,12),(-4.6,13),(-4.9,10),(-3.6,8.6),(1,8),(4.5,6.8),(5,5.6),(2.8,6.4),(-1,6),(-4,6)],2.4,bevel=.2)
        # Four separate sides maintain the opening at acute pommel corners.
        for a,b in [((0,-7),(-2.5,-9.7)),((-2.5,-9.7),(0,-13.4)),((0,-13.4),(2.5,-9.7)),((2.5,-9.7),(0,-7))]:rail([a,b],.9,1.6)
        return [(9,42,.8),(12,37,.8),(4,38,.8),(-1,32,.8),(-4.5,23,.8),(2,13,.8)]

    if kind=='slitspear':
        # A pointed annulus, solid root and one joined spear tip.
        window([(0,46),(-3.6,13),(0,10),(3.6,13)],
               [(0,37),(-1.55,15.8),(0,13.8),(1.55,15.8)],2.2)
        slab([(-2.3,6),(-2.3,11),(-3,13),(3,13),(2.3,11),(2.3,6)],2.3,bevel=.22)
        slab([(-4.7,5.5),(-4.7,7.2),(4.7,7.2),(4.7,5.5),(3,6),(-3,6)],2.4,bevel=.17)
        spindle([(-7,1.1),(-8.5,1.65),(-10.5,1.45),(-11.5,.85)],6)
        return [(0,43,.8),(-1.3,35,.8),(1.3,35,.8),(-2.8,23,.8),(2.8,23,.8),(2.6,14,.8)]

    if kind=='offsetprism':
        # Two depth-offset planes joined by the lower spine, one open zigzag slit.
        slab([(-1.8,8),(-.7,12),(-5,27),(0,44),(2.6,29),(-.4,23),(.3,13)],2.4,z=.45,bevel=.3)
        slab([(1,8),(4.7,12),(6,28),(1.3,21),(3.4,13),(-1.8,8)],2.3,z=-.5,bevel=.28)
        # Bridge both blade planes with positive overlap, not just a shared tip.
        slab([(-1.5,8),(-1,11),(2.4,11),(1,8)],2.8,bevel=.16)
        slab([(-4.8,7.7),(-3.4,5.8),(5.2,4.6),(3.3,6.8)],2.7,z=.1,bevel=.25)
        spindle([(-7,1.1),(-9,2.2),(-12.5,.06)],4)
        return [(-.4,41,.8),(-3.5,31,.8),(1.8,29,.8),(5,25,.8),(4,13,.8),(-2.8,21,.8)]
    raise ValueError(kind)
