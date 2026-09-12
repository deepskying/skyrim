"""Second approved single-handed set: broadcut, streamlance, eccentric, fanblade."""
import math
from greatswords2_geometry import curve


def build(spec, slab, rail, frame, solid):
    def facet(points, ridge, depth=2.2):
        # A shallow raised plane gives solid-light faces a readable bevel ridge.
        vertices=[(x,y,depth/2) for x,y in points]+[ridge]
        n=len(points)
        return solid(vertices, [tuple(range(n-1,-1,-1))]+[(i,(i+1)%n,n) for i in range(n)], .06)

    kind=spec['design']
    if kind=='broadcut':
        # Two open rectangular recesses in a continuous broad, convex-edge slab.
        rear=[(-2,7),(-2,14),(-6,19),(-6,34),(-3.8,34),(-3.8,42),
              (-6,42),(-6,49),(-3.8,49),(-3.8,57),(-6,57),(-6,62),(7,73)]
        edge=curve([(7,73),(3.8,48),(5.0,25),(10,6)],30)
        slab(rear+edge[1:],2.5,bevel=.38)
        facet([(-3.2,17),(-3.2,59),(6.5,71),(9.4,7)],(2,39,2.0),2.5)
        rail([(2,5),(-3,8),(-11,5),(-9,-6),(-2,-11)],2,2.8)
        slab([(-2.5,-8),(-3.2,-10),(-2.2,-13),(2.2,-13),(3.2,-10),(2.5,-8)],3,bevel=.35)
        return [(-6.8,34,0),(-6,38,0),(-5.8,42,0),(-6.8,49,0),(-6,53,0),(-5.8,57,0)]

    if kind=='streamlance':
        # One narrow, genuinely prismatic main blade and one swept side fin.
        solid([(-2.1,11,0),(0,73,0),(2.1,11,0),(0,10,1.8),(0,10,-1.5)],
              [(0,1,3),(1,2,3),(2,0,3),(1,0,4),(2,1,4),(0,2,4)],.025)
        slab([(-2.1,11),(0,7),(2.1,11),(0,14)],2.4,bevel=.2)
        outer=curve([(0,7),(12,15),(7,26),(1.1,40)],34)
        inner=curve([(1.1,40),(4.6,26),(9.2,17),(0,7)],34)
        slab(outer+inner[1:-1],1.8,bevel=.23)
        guardtop=curve([(-7,5),(-4,9),(0,7),(7,3.5)],24)
        guardbottom=curve([(7,3.5),(2,5),(-2,8),(-7,5)],24)
        slab(guardtop+guardbottom[1:-1],2.6,bevel=.22)
        solid([(-2,-10,0),(0,-8,0),(2,-10,0),(0,-15,0),(0,-10,1.8),(0,-10,-1.8)],
              [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],.15)
        return [(-2.5,51,0),(2.5,55,0),(-2.5,59,0),(2,63,0),(-2,66,0),(2,69,0)]

    if kind=='eccentric':
        # Continuous right spine joins blade and hilt; off-centre ring is empty.
        slab([(-1.8,6),(-2.2,11),(1.2,15),(1.2,25),(-3.7,28),(-3.2,63),
              (0,73),(3.2,63),(4,11),(1.8,8),(1.7,6)],2.4,bevel=.33)
        cx,cy=-3.6,18
        ring=[(cx+6.5*math.cos(math.pi/8+i*math.pi/4),cy+6.5*math.sin(math.pi/8+i*math.pi/4)) for i in range(8)]
        # Closed annulus with no internal seams between the eight sides.
        inner=[(cx+4.2*math.cos(math.pi/8+i*math.pi/4),cy+4.2*math.sin(math.pi/8+i*math.pi/4)) for i in range(8)]
        verts=[(x,y,z) for z in (-1.4,1.4) for loop in (ring,inner) for x,y in loop]
        faces=[]
        for i in range(8):
            j=(i+1)%8
            faces.extend([(i,j,j+8,i+8),(i+16,i+24,j+24,j+16),
                          (i,i+16,j+16,j),(i+8,j+8,j+24,i+24)])
        solid(verts,faces,.22)
        slab([(-6,23),(-3.7,28),(1.3,25),(1.3,22)],2.4,bevel=.23)
        facet([(-3.2,28),(-2.8,62),(0,72),(3.1,62),(3.7,11),(1.5,15),(1.5,25)],(.1,43,2),2.4)
        rail([(-1,6),(9,6)],2.0,3)
        rail(curve([(-1,6),(-8,5),(-9,7),(-8.5,10)],22),1.6,2.5)
        slab([(3*math.cos(i*math.pi/4+math.pi/8),-11+3*math.sin(i*math.pi/4+math.pi/8)) for i in range(8)],3,bevel=.3)
        return [(-11,15,0),(-11,18,0),(-10,21,0),(-8,24,0),(-5,25,0),(-10,12,0)]

    if kind=='fanblade':
        # Three overlapping blade slabs, each has its own descending tip.
        # Common collar, no lateral crossbars, no open fork at the root.
        panels=[([(-1.8,8),(-7,50),(-5,73),(0,60),(1.8,8)],-.65),
                ([(-1.6,8),(-1.7,46),(0,62),(4.5,53),(1.8,8)],0),
                ([(-1.1,8),(3,35),(5.4,52),(8.5,45),(1.8,8)],.65)]
        for outline,z in panels:
            slab(outline,1.8,z=z,bevel=.30)
        slab([(-2.3,6.8),(-2.3,9),(2.3,9),(2.3,6.8)],3.6,bevel=.20)
        # Folded fan guard occupies only the area above the palm.
        for a,b in [((-7,5),(-4.5,3.3)),((-4.5,3.3),(-1.8,3.1)),
                    ((-1.8,3.1),(1.8,3.1)),((1.8,3.1),(4.5,3.3)),((4.5,3.3),(7,5))]:
            slab([(0,7.5),a,b],2.7,bevel=.18)
        solid([(-2.5,-10,0),(2.5,-10,0),(0,-15,0),(0,-9,2),(0,-9,-2)],
              [(0,1,3),(1,2,3),(2,0,3),(1,0,4),(2,1,4),(0,2,4)],.2)
        return [(-2,69,0),(2,60,0),(4,57,0),(8,51,0),(9,47,0),(9,43,0)]
    raise ValueError(kind)
