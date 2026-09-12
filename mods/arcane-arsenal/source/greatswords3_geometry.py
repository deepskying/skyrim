"""Third approved set: stepped cleaver, curved saber, open vault, pleated blade."""
import math
from greatswords2_geometry import curve


def build(spec, slab, rail, frame, solid):
    kind = spec['design']
    if kind == 'counterpoise':
        outline = [(7,106),(7,16),(2,11),(-3,15),(-8,23),(-8,39),
                   (-17,57),(-12,65),(-10,70),(-13,75),(-8,83),
                   (-6,87),(-8,93)]
        slab(outline,3.5,bevel=.48)
        # A raised spine and its recessed neighbouring face form the long channel.
        slab([(4.6,20),(6.7,22),(6.7,101),(4.6,97)],.9,z=1.8,bevel=.16)
        slab([(-2,10),(-23,12),(-3,15),(2,12)],3.6,bevel=.32)
        slab([(2,10),(10,10),(10,13),(2,13)],3.8,bevel=.3)
        slab([(10,8),(14,8),(14,16),(10,16)],5,bevel=.45)
        slab([(-2,-17),(-4,-23),(0,-27),(4,-23),(2,-17)],4,bevel=.4)
        return [(-18,56,0),(-15,73,0),(-10,92,0),(-10,39,0),(-10,25,0),(-13,63,0)]
    if kind == 'sweep':
        outer=curve([(0,13),(26,36),(23,81),(-12,106)],48)
        inner=curve([(-12,106),(10,73),(12,39),(-3,16)],48)
        slab(outer+inner[1:],3.2,bevel=.42)
        # Swept face rib: a sculpted groove-like channel, never a floating bowstring.
        middle=[((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(outer,reversed(inner))]
        rail(middle[3:-3],1.05,1.1,z=1.65)
        rail(curve([(-1,10),(-13,13),(-15,20),(-10,26)],24),3.4,3.6)
        slab([(1,10),(8,13),(11,10),(10,7),(7,10)],3.5,bevel=.35)
        slab([(0,-17),(-3.7,-21),(0,-28),(3.7,-21)],4,bevel=.4)
        return [(13,32,0),(19,47,0),(21,62,0),(17,78,0),(8,92,0),(-3,102,0)]
    if kind == 'vault':
        # Actual through-window: two broad rails, two staggered depth bridges.
        for sign in (-1,1):
            slab([(sign*x,y) for x,y in [(4,20),(9,20),(9,94),(4,94)]],3.8,bevel=.38)
            slab([(sign*x,y) for x,y in [(4,94),(9,94),(0,107),(0,99)]],3.8,bevel=.32)
        slab([(-4,11),(-4,15),(-11,19),(-11,23),(-7,25),(-4,22),
              (4,22),(7,25),(11,23),(11,19),(4,15),(4,11)],4,bevel=.38)
        for y,z in [(43,1.05),(76,-1.05)]:
            slab([(-4.5,y+1.5),(-4.5,y+4.3),(4.5,y+1.7),(4.5,y-1)],1.5,z=z,bevel=.2)
        rail([(-12,6),(-12,14),(12,14),(12,6)],3,4.2)
        slab([(-2.5,-17),(-3.5,-19),(-3.5,-24),(0,-27),(3.5,-24),(3.5,-19),(2.5,-17)],4.5,bevel=.45)
        return [(0,28,0),(0,37,0),(0,53,0),(0,65,0),(0,83,0),(0,92,0)]
    if kind == 'pleat':
        # A closed folded cross-section; three ridges and two deep valleys on each face.
        top=[(-1,0),(-.67,2.2),(-.33,.5),(0,3.0),(.33,.5),(.67,2.2),(1,0)]
        cross=top+[(x,-z) for x,z in top[-2:0:-1]]
        sections=[(14,2.8,.8),(22,10,1),(32,7.3,1),(86,7.3,1),(97,3.7,.75),(107,.045,.02)]
        verts=[(x*w,y,z*d) for y,w,d in sections for x,z in cross]
        n=len(cross)
        faces=[tuple(range(n-1,-1,-1)),tuple((len(sections)-1)*n+j for j in range(n))]
        faces += [(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for i in range(len(sections)-1) for j in range(n)]
        folded=solid(verts,faces,.10)
        # Alternate folded planes use the existing lavender edge material, so
        # the actual depth remains readable even under an emissive shader.
        for face in folded.data.polygons:
            if face.normal.x*face.normal.z > .18 and abs(face.normal.y)<.8:
                face.material_index=1
        for sign in (-1,1):
            verts=[(sign*x,y,z) for x,y,z in [(1,12,0),(12,8,0),(11,18,0),(6,13,3),(1,12,-1.5),(12,8,-1.5),(11,18,-1.5)]]
            solid(verts,[(0,1,3),(1,2,3),(2,0,3),(4,6,5),(0,4,5,1),(1,5,6,2),(2,6,4,0)],.18)
        slab([(0,-16),(-3.5,-22),(0,-28),(3.5,-22)],4,bevel=.3)
        return [(-3,28,3),(3,39,3),(-3,53,3),(3,66,3),(-3,80,3),(3,91,3)]
    raise ValueError(kind)
