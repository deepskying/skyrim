"""Four approved long-haft scythes, authored in the IronBattleAxe hand frame.

The shaft stays conventional at both hand positions. Large negative spaces
are constructed as closed strips, never coplanar filled polygons.
"""
import math


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8,phase=math.pi/8):
        vs=[(r*math.cos(phase+i*math.tau/sides),y,r*math.sin(phase+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        fs=[tuple(range(sides-1,-1,-1)),tuple(range(len(vs)-sides,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
        return solid(vs,fs,.14)

    def window(outer,inner,depth=3.4,z=0):
        assert len(outer)==len(inner)==4
        vs=[(x,y,z+d) for d in (-depth/2,depth/2) for loop in (outer,inner) for x,y in loop]
        fs=[]
        for i in range(4):
            j=(i+1)%4
            fs.extend([(i,j,j+4,i+4),(i+8,i+12,j+12,j+8),(i,i+8,j+8,j),(i+4,j+4,j+12,i+12)])
        return solid(vs,fs,.28)

    kind=spec['design']
    neck_start=51 if kind=='crescentwake' else 85
    spindle([(-39,1.35),(24,1.35),(neck_start,1.55)])
    # Keep collars clear of both vanilla hand sections.
    for y in (-36,24,48):
        spindle([(y-1.2,1.5),(y,2.05),(y+1.2,1.5)],8 if kind in ('riftreap','horizoncleft') else 6)

    if kind=='riftreap':
        # Broad concave cutting face, three stepped ridges along its back.
        slab([(-16,104),(-30,103),(-44,98),(-55,89),(-63,77),(-68,62),(-70,45),
              (-62,67),(-54,78),(-43,86),(-30,91),(-16,90)],3.8,bevel=.4)
        slab([(-17,99),(-23,105),(-13,108),(-14,105),(-8,101),(-8,98)],4.4,bevel=.35)
        slab([(-36,99),(-42,102),(-30,107),(-31,103),(-27,102)],4.2,bevel=.35)
        slab([(-52,89),(-57,91),(-46,99),(-46,96),(-44,94)],4,bevel=.35)
        window([(-18,101),(-2,101),(-2,89),(-18,89)],[(-15,98),(-5,98),(-5,93),(-15,93)],4)
        slab([(-3,85),(-4,99),(-2.5,103),(2.5,103),(4,99),(3,85)],5,bevel=.4)
        rail([(3,95),(10,95)],3.8,4)
        slab([(9,90),(14,90),(14,100),(9,100)],5,bevel=.4)
        spindle([(82,1.6),(85,2.3),(87,2.3)],8)
        spindle([(103,1.5),(105,2.4),(112,.07)],6)
        spindle([(-39,1.4),(-42,3.3),(-46,2.4),(-51,.08)],6)
        return [(-66,56,1),(-63,75,1),(-53,88,1),(-42,99,1),(-25,104,1),(-14,106,1)]

    if kind=='crescentwake':
        # Two thick crescents meet at the tip and neck, enclosing one true slit.
        slab([(-2,101),(-16,106),(-31,104),(-45,97),(-56,85),(-62,71),(-63,57),(-59,46),
              (-59,62),(-55,76),(-47,87),(-36,94),(-23,98),(-11,97),(-2,92)],3.5,bevel=.35)
        slab([(-3,86),(-13,90),(-24,88),(-35,83),(-45,74),(-53,60),(-59,46),
              (-56,64),(-49,77),(-38,87),(-25,93),(-13,94),(-3,93)],3.3,z=.15,bevel=.32)
        slab([(-1.6,50),(3,57),(4,62),(0,68),(-3,74),(-3,86),(-1,93),
              (2,93),(1,84),(1,77),(5,70),(8,63),(7,59),(2,50)],3.4,bevel=.3)
        slab([(0,85),(-5,96),(0,110),(5,98)],4.5,bevel=.4)
        rail([(3,97),(9,96)],2.6,3.6)
        slab([(8,100),(13,98),(19,93),(11,94),(8,95)],3.8,bevel=.3)
        rail([(0,-39),(-4,-45),(0,-52),(4,-45),(0,-39)],1.7,2.8)
        return [(-24,103,1),(-46,94,1),(-58,79,1),(-61,62,1),(-58,49,1),(-40,87,1)]

    if kind=='horizoncleft':
        # Long cantilever head: two genuine open truss bays, continuous blade.
        window([(-2,105),(-21,105),(-25,94),(-2,94)],[(-5,102),(-19,102),(-21,97),(-5,97)],3.5)
        window([(-21,105),(-45,104),(-48,94),(-25,94)],[(-24,102),(-42,101),(-44,97),(-27,97)],3.5)
        slab([(-44,104),(-54,98),(-64,85),(-70,62),(-62,77),(-53,86),(-42,90),
              (-28,92),(-13,91),(-3,88),(-3,96),(-27,97),(-45,95)],3.8,bevel=.4)
        slab([(-45,104),(-51,108),(-48,101)],3.6,bevel=.3)
        slab([(-3,86),(-4,103),(-2,106),(3,106),(4,103),(3,86)],5,bevel=.4)
        spindle([(82,1.6),(85,2.2),(87,1.6)],8)
        rail([(3,98),(13,98)],3.0,3.5)
        slab([(12,95),(17,95),(17,101),(12,101)],4.2,bevel=.35)
        spindle([(106,1.5),(111,1.5)],4)
        spindle([(-39,1.4),(-41,2.3),(-43,2.3),(-44,3.2),(-48,3.2),(-50,2.4)],8)
        return [(-67,69,1),(-62,82,1),(-56,94,1),(-46,102,1),(-31,104,1),(-13,104,1)]

    if kind=='foldednight':
        # Three physically joined blades fan from a diamond hub. Depth offsets
        # and tapering slots preserve the approved layered silhouette.
        slab([(-2,98),(-14,106),(-29,109),(-44,103),(-57,91),(-65,74),(-69,45),
              (-61,64),(-54,79),(-42,91),(-28,98),(-14,100),(-3,92)],3.8,z=.7,bevel=.38)
        slab([(-3,92),(-16,97),(-28,94),(-40,88),(-50,77),(-54,61),
              (-45,73),(-34,82),(-22,87),(-11,90),(-3,87)],3.4,z=-.4,bevel=.33)
        slab([(-3,87),(-14,88),(-24,84),(-35,77),(-41,68),
              (-30,74),(-20,78),(-10,83),(-3,83)],3.1,z=-1.1,bevel=.3)
        slab([(0,81),(-5,95),(0,111),(5,96)],4.8,bevel=.38)
        slab([(-1.5,75),(-2.5,82),(0,88),(2.5,82),(1.5,75)],3.5,bevel=.26)
        slab([(3,94),(10,97),(18,104),(13,95),(6,91)],3.6,z=.3,bevel=.33)
        spindle([(-39,1.4),(-42,2.1),(-47,3.4),(-53,.07)],4)
        return [(-64,60,1),(-59,86,1),(-43,102,1),(-29,107,1),(-50,71,1),(-36,75,1)]
    raise ValueError(kind)
