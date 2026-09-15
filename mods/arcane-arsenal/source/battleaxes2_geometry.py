"""Second approved battleaxe group: cleaver, falling talons, echelon, open ring."""
import math


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8,phase=math.pi/8):
        vs=[(r*math.cos(phase+i*math.tau/sides),y,r*math.sin(phase+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        fs=[tuple(range(sides-1,-1,-1)),tuple(range(len(vs)-sides,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
        return solid(vs,fs,.15)

    kind=spec['design']
    top=29 if kind=='brokenorbit' else 61 if kind=='fallingtalons' else 54
    spindle([(-34,1.35),(21,1.35),(top,1.6)])
    for y in (-30,20):spindle([(y-.4,1.65),(y+.4,1.65)])

    if kind=='spinebreaker':
        # Single uninterrupted solid blade and a stepped beard, no cut-out.
        slab([(2,58),(30,71),(19,37),(7,27),(9,37),(11,40),(10,48),(2,52)],4.2,bevel=.48)
        # Raised slashes follow the concept; they are shallow solid strips.
        for z in (-2.15,2.15):rail([(12,44),(23,65)],.48,.24,z)
        slab([(-2.8,51),(-3.3,60),(0,63),(3.3,60),(2.8,51)],4.8,bevel=.4)
        rail([(-2,56),(-8,56)],3.8,4)
        slab([(-8,52),(-12,52),(-12,61),(-8,61)],4.8,bevel=.4)
        slab([(-2.6,60),(-3.1,65),(-1.5,67),(4.5,65.5),(4.5,63),(1.5,63),(1.5,60)],4,bevel=.35)
        spindle([(-34,1.4),(-37,3),(-42,2.2),(-45,.5)],6)
        return [(29,66,1),(25,54,1),(20,40,1),(9,29,1),(16,65,1),(-12,57,1)]

    if kind=='fallingtalons':
        # Continuous polygon outlines trace two connected swept talons.
        slab([(-20,70),(-15,65),(-8,63),(1,64),(1,59),(-6,59),(-12,56),(-17,49),(-18,43),(-16,35),(-12,29),(-6,23),(-14,26),(-20,31),(-25,40),(-26,48),(-25,54),(-21,63)],3.6,bevel=.4)
        slab([(-5,60),(-9,54),(-10,48),(-9,42),(-6,37),(-11,40),(-14,47),(-14,51),(-9,59)],3.3,bevel=.36)
        slab([(-2,57),(-2.4,63),(0,67),(2.4,63),(2,57)],4.5,bevel=.35)
        slab([(1,59),(5,61),(10,57),(4,58)],3.8,bevel=.3)
        spindle([(27,1.4),(29,2.2),(31,1.4)],6)
        for sign in (-1,1):
            slab([(sign*x,y) for x,y in [(0,-34),(3.7,-38),(3.8,-42),(2.5,-46),(2.4,-40),(.2,-36)]],2.8,bevel=.24)
        spindle([(-34,1.3),(-39,.1)],4)
        return [(-21,65,1),(-26,50,1),(-23,36,1),(-9,25,1),(-14,47,1),(-7,38,1)]

    if kind=='tideshear':
        # The two plates occupy different depth planes and have separate necks.
        slab([(4,60),(30,65),(25,54),(4,46)],4.2,z=.65,bevel=.42)
        slab([(6,43),(24,51),(20,41),(6,34)],4.2,z=-.65,bevel=.42)
        rail([(1,54),(6,54)],4,4.6,z=.4)
        rail([(1,39),(8,39)],3.8,4.6,z=-.4)
        slab([(-2.5,33),(-2.5,65),(-1.5,68),(2.7,65),(2.7,33)],5.2,bevel=.4)
        slab([(-2,48),(-7,47),(-11,49),(-11,58),(-7,58),(-2,56)],5.2,bevel=.4)
        spindle([(28,1.6),(30,2.3),(32,1.6)],8)
        spindle([(-34,1.4),(-38,2.6),(-43,1.7),(-45,.4)],6)
        return [(28,62,1),(25,55,1),(23,48,1),(20,42,1),(7,35,1),(-11,54,1)]

    if kind=='brokenorbit':
        # One closed volumetric annular sector: front/back quads preserve both
        # the central void and the upper-right break through triangulation.
        angles=[65,85,110,135,160,185,210,235,260,285,310,335,355,375]
        sections=[]
        for i,deg in enumerate(angles):
            a=math.radians(deg)
            outer=23+max(0,math.cos(a))*1.5
            inner=19-max(0,math.cos(a)) * 2.4
            if i==len(angles)-1:inner=outer-.35
            sections.append([(6+r*math.cos(a),48+r*math.sin(a),z) for z,r in [(-1.8,outer),(-1.8,inner),(1.8,inner),(1.8,outer)]])
        vs=[v for s in sections for v in s];fs=[(3,2,1,0)]
        for j in range(len(sections)-1):
            for k in range(4):fs.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
        n=len(vs);fs.append((n-4,n-3,n-2,n-1));solid(vs,fs,.3)
        slab([(-2,25),(-3,33),(1,37),(4,36),(2,29),(2,25)],4.6,bevel=.38)
        rail([(-1,32),(-10,40),(-14,44)],1.8,2.6)
        rail([(1,32),(10,27)],1.8,2.6)
        rail([(0,-34),(-3.6,-40),(0,-46)],1.55,2.8)
        rail([(0,-34),(3.6,-40),(0,-46)],1.55,2.8)
        return [(-16,51,1),(-11,63,1),(11,70,1),(27,54,1),(27,39,1),(11,24,1)]
    raise ValueError(kind)
