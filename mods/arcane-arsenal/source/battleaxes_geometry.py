"""Four approved Heteromorphic battleaxes, authored in the IronBattleAxe frame.

Y is the haft axis. The unobstructed two-hand grip spans -29..19, matching
the vanilla long handle. Openings are spaces between solid extruded pieces.
"""
import math


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8,phase=math.pi/8):
        vertices=[(r*math.cos(phase+i*math.tau/sides),y,r*math.sin(phase+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        faces=[tuple(range(sides-1,-1,-1)),tuple(range(len(vertices)-sides,len(vertices)))]
        for row in range(len(rings)-1):
            for i in range(sides):
                a=row*sides+i;b=row*sides+(i+1)%sides;faces.append((a,b,b+sides,a+sides))
        return solid(vertices,faces,.15)

    kind=spec['design']
    spindle([(-34,1.35),(21,1.35),(30,1.6)] if kind=='eclipsewing' else [(-34,1.35),(21,1.35),(34,1.6),(55,1.6)])
    for y in (-30,20):spindle([(y-.45,1.65),(y+.45,1.65)])
    if kind=='riftcleaver':
        # Broad leading face, stepped beard, and three thick sides of a triangle.
        slab([(-28,66),(-23,39),(-17,36),(-21,32),(-13,29),(-11,21),(-8,33),(-15,46),(-19,56)],3.4,bevel=.42)
        slab([(-28,66),(-19,56),(-7,52),(0,55),(0,59)],3.4,bevel=.42)
        rail([(-15,46),(-7,52),(0,53)],3,3.4)
        rail([(-19,56),(-15,46)],1.9,3.4)
        rail([(-15,38),(0,26)],2.1,2.6)
        slab([(-2.7,48),(-3.4,58),(0,61),(3.4,58),(2.7,48)],4.8,bevel=.4)
        rail([(2,54),(8,54)],3.8,3.8)
        slab([(8,49),(8,59),(14,54)],5.2,bevel=.4)
        spindle([(58,1.4),(63,2.1),(68,.08)],4)
        spindle([(-34,1.4),(-37,2.8),(-44,.08)],6)
        return [(-27,59,1),(-24,45,1),(-18,34,1),(-10,24,1),(-8,59,1),(14,54,1)]

    if kind=='forkedgale':
        # Upper left blade and its lower-right counterpart are vertically offset.
        upper=[(-6,71),(-17,66),(-25,58),(-28,51),(-22,53),(-23,42),(-19,33),(-18,43),(-15,52),(-14,57)]
        slab(upper,3.1,bevel=.38)
        rail([(-22,53),(-18,42),(-19,33)],2.2,3.0)
        rail([(-15,57),(-7,56),(-2,53)],2.5,3.1)
        rail([(-19,33),(-10,42),(-3,45)],2.5,3.1)
        # Mirror horizontally and lower the right blade; both leading hooks
        # point upward as in the approved illustration (not a 180-degree copy).
        lower=[(-x,y-16) for x,y in upper]
        slab(lower,3.1,bevel=.38)
        rail([(22,37),(18,26),(19,17)],2.2,3.0)
        rail([(15,41),(7,40),(2,37)],2.5,3.1)
        rail([(19,17),(10,26),(0,31)],2.5,3.1)
        rail([(-2,56),(4,51),(-4,43),(3,37),(0,32)],4,4.0)
        spindle([(29,1.7),(32,2.5),(34,1.7)],6)
        spindle([(54,1.6),(59,2.0),(63,.08)],4)
        # Open fork pommel, two solid tapering rails.
        rail([(0,-34),(-3.5,-39),(0,-45)],1.5,2.8)
        rail([(0,-34),(3.5,-39),(0,-45)],1.5,2.8)
        return [(-20,64,1),(-27,51,1),(-20,35,1),(20,48,1),(27,35,1),(20,19,1)]

    if kind=='gatebreaker':
        # Window occupies x=4..19, y=42..55, with one recessed diagonal brace.
        slab([(18,65),(29,65),(29,36),(21,24),(22,37),(17,40),(19,56),(18,59)],4.2,bevel=.5)
        rail([(0,55),(19,59)],4.2,4.2)
        rail([(0,40),(22,37)],3.5,4.2)
        rail([(3,48),(19,41)],1.5,2.1,z=-.5)
        slab([(-3,58),(-14,61),(-14,54),(-11,54),(-11,51),(-14,51),(-14,47),(-11,47),(-11,44),(-14,44),(-14,39),(-3,42)],4.6,bevel=.4)
        slab([(-3,39),(-3,59),(3,59),(3,39)],5.2,bevel=.4)
        spindle([(57,1.7),(63,1.7),(65,.7)],8)
        spindle([(22,1.7),(24,2.5),(26,1.7)],8)
        spindle([(-34,1.4),(-37,2.8),(-40,2.8),(-42,1.5)],8)
        return [(29,60,1),(29,47,1),(25,34,1),(20,25,1),(-15,56,1),(-15,43,1)]

    if kind=='eclipsewing':
        # Large diamond aperture. Left wing is deliberately wider than right.
        slab([(-9,68),(-18,60),(-27,51),(-25,41),(-14,31),(-17,43),(-13,53),(-7,61)],3.5,bevel=.42)
        slab([(10,64),(17,58),(24,50),(20,39),(12,34),(15,46),(12,54),(7,60)],3.5,bevel=.42)
        rail([(-8,60),(-13,49),(0,34),(12,49),(7,60)],2.8,3.5)
        rail([(-8,60),(0,63),(7,60)],2.8,3.5)
        # Stop the straight shaft below the aperture: no accidental filled window.
        # Common shaft upper section is trimmed for this design above
        # instead of placing an opaque rod through the open center.
        frame(0,32,5.5,5.5,1.5,angle=math.pi/4)
        spindle([(26,1.7),(28,2.5),(30,1.7)],6)
        rail([(0,-34),(-3.3,-40),(0,-46)],1.55,2.8)
        rail([(0,-34),(3.3,-40),(0,-46)],1.55,2.8)
        return [(-12,65,1),(-26,51,1),(-16,34,1),(16,59,1),(23,48,1),(14,36,1)]
    raise ValueError(kind)
