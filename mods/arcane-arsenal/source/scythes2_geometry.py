"""Second approved scythe set: inner fangs, spiral, angular hook, open ring.

World XY design coordinates preserve the first set's two-hand shaft sections.
All negative spaces are physical openings, not painted details.
"""
import math


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8):
        vs=[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        fs=[tuple(range(sides-1,-1,-1)),tuple(range(len(vs)-sides,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
        return solid(vs,fs,.14)

    def window(outer,inner,depth=4):
        vs=[(x,y,d) for d in (-depth/2,depth/2) for loop in (outer,inner) for x,y in loop]
        fs=[]
        for i in range(4):
            j=(i+1)%4
            fs.extend([(i,j,j+4,i+4),(i+8,i+12,j+12,j+8),(i,i+8,j+8,j),(i+4,j+4,j+12,i+12)])
        return solid(vs,fs,.3)

    kind=spec['design']
    spindle([(-39,1.35),(24,1.35),(69 if kind=='coilwind' else 89,1.55)])
    for y in (-36,24,48):
        spindle([(y-1.1,1.5),(y,2.1),(y+1.1,1.5)],6 if kind in ('coilwind','silentring') else 8)

    if kind=='thorncleaver':
        # One massive cutting slab; inner notches form three separated fangs.
        slab([(-15,105),(-54,96),(-60,83),(-65,58),(-54,77),(-54,83),
              (-49,87),(-38,78),(-41,90),(-32,92),(-24,80),(-29,94),(-20,94),(-15,87)],4.2,bevel=.45)
        window([(-16,91),(-16,105),(-2,108),(-2,85)],
               [(-10,97),(-7,101),(-4,97),(-7,93)],4.2)
        slab([(-3,84),(-4,103),(-3,110),(3,110),(4,103),(3,84)],5,bevel=.42)
        rail([(3,99),(11,99)],4,4.3)
        slab([(10,95),(16,95),(16,104),(10,104)],5,bevel=.4)
        spindle([(79,1.6),(82,2.5),(84,1.6)],6)
        spindle([(-39,1.4),(-42,3.6),(-48,3.6),(-51,1.2)],6)
        return [(-61,67,1),(-56,89,1),(-40,83,1),(-26,84,1),(-29,101,1),(-10,105,1)]

    if kind=='coilwind':
        # Single broad spiral ribbon with open mouth and inner return horn.
        slab([(0,87),(-3,103),(-23,112),(-43,107),(-60,94),(-63,85),
              (-52,74),(-39,67),(-25,61),(-13,48),(-18,66),(-26,79),(-33,84),
              (-27,72),(-35,73),(-46,79),(-52,86),(-49,94),(-40,100),
              (-29,103),(-18,99),(-11,92),(-9,82),(-7,77)],3.8,bevel=.38)
        slab([(-1.6,68),(-4,76),(-6,88),(0,94),(6,88),(3,79),(1.6,68)],4.2,bevel=.35)
        slab([(3,86),(9,91),(14,98),(16,105),(17,97),(14,90),(7,83)],3.6,bevel=.3)
        rail([(0,-39),(-4.5,-43),(0,-52),(4.5,-43),(0,-39)],1.7,2.8)
        return [(-25,110,1),(-48,101,1),(-60,87,1),(-47,74,1),(-27,64,1),(-18,56,1)]

    if kind=='abyssfold':
        # High elbow followed by two severe folds; broad continuous long edge.
        slab([(-2,98),(-35,113),(-45,94),(-60,82),(-68,60),(-70,44),
              (-60,66),(-52,78),(-37,89),(-32,102),(-4,89)],4,bevel=.42)
        # Open triangular brace, connected to beam and hub at both endpoints.
        # Separate segments avoid an averaged normal filling the acute corner.
        rail([(-32,102),(-8,77)],2.5,3.3)
        rail([(-8,77),(-5,91)],2.5,3.3)
        slab([(-3,85),(-4,99),(0,107),(4,99),(3,85)],5,bevel=.4)
        slab([(3,96),(10,89),(20,72),(8,81),(3,88)],3.8,bevel=.35)
        spindle([(80,1.6),(83,2.3),(85,1.6)],8)
        spindle([(-39,1.4),(-43,2.7),(-48,2.7),(-52,.08)],6)
        return [(-67,54,1),(-63,74,1),(-54,86,1),(-43,98,1),(-35,111,1),(-18,104,1)]

    if kind=='silentring':
        # Faceted incomplete ring, broad left blade descending to an inward tip.
        slab([(-3,96),(-19,110),(-41,108),(-59,91),(-62,80),(-56,65),
              (-44,52),(-22,43),(-35,56),(-39,65),(-39,71),(-48,76),
              (-52,85),(-42,98),(-25,101),(-14,93),(-11,82),(-14,75),(-5,83)],3.9,bevel=.4)
        slab([(-1.6,78),(-4,88),(-3,100),(0,104),(4,98),(4,88),(1.6,78)],4.8,bevel=.35)
        rail([(3,94),(9,94)],2.7,3.2)
        slab([(8,94),(12,97),(20,94),(12,91)],3.6,bevel=.3)
        spindle([(74,1.6),(76,2.6),(78,1.6)],4)
        spindle([(-39,1.4),(-42,2.6),(-45,1.3)],4)
        slab([(-1,-41),(-4,-44),(-4,-52),(-6,-44),(-4,-41)],2.9,bevel=.2)
        slab([(1,-41),(4,-44),(4,-52),(6,-44),(4,-41)],2.9,bevel=.2)
        return [(-26,108,1),(-47,101,1),(-60,85,1),(-54,66,1),(-39,52,1),(-13,80,1)]
    raise ValueError(kind)
