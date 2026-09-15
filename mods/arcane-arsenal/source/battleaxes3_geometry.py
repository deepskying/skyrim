"""Approved third battleaxe concepts: stepped edge, S blade, crossbar, fan."""
import math


def build(spec,slab,rail,frame,solid):
    def spindle(rings,sides=8,phase=math.pi/8):
        vs=[(r*math.cos(phase+i*math.tau/sides),y,r*math.sin(phase+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        fs=[tuple(range(sides-1,-1,-1)),tuple(range(len(vs)-sides,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
        return solid(vs,fs,.15)

    def window(outer,inner,depth,z=0):
        """Closed quadrilateral annulus; explicit faces retain the real hole."""
        assert len(outer)==len(inner)==4
        vs=[(x,y,z+d) for d in (-depth/2,depth/2) for loop in (outer,inner) for x,y in loop]
        fs=[]
        for i in range(4):
            j=(i+1)%4
            fs.extend([(i,j,j+4,i+4),(i+8,i+12,j+12,j+8),(i,i+8,j+8,j),(i+4,j+4,j+12,i+12)])
        return solid(vs,fs,.3)

    spindle([(-34,1.35),(21,1.35),(54,1.6)])
    for y in (-30,20):spindle([(y-.4,1.65),(y+.4,1.65)])
    kind=spec['design']
    if kind=='stepreaver':
        # Three broad chisel courses carved into a single heavy slab.
        slab([(-26,70),(-30,56),(-18,51),(-26,47),(-27,42),(-15,37),(-22,34),(-22,30),(-13,27),(-12,24),(-6,21),(-8,36),(-8,44),(-4,51),(1,53),(1,60),(-12,63)],4.5,bevel=.5)
        slab([(-3,51),(-3,62),(3,62),(3,51)],5.1,bevel=.42)
        rail([(2,56),(9,56)],3.8,4.6)
        slab([(8,51),(13,51),(13,60),(8,60)],5,bevel=.4)
        spindle([(60,2),(63,2.8),(65,1)],6)
        spindle([(27,1.6),(29,2.6),(31,1.6)],8)
        spindle([(-34,1.4),(-37,3),(-42,2.6),(-44,1.7)],6)
        return [(-28,63,1),(-26,45,1),(-21,32,1),(-10,23,1),(-12,63,1),(13,56,1)]

    if kind=='coiledgale':
        # S-shaped continuous blade curls into an open lower hook.
        slab([(-22,71),(-19,67),(-11,63),(-2,62),(-7,58),(-10,55),(-10,49),(-7,42),(-4,35),(-4,31),(-7,26),(-8,22),(-13,26),(-17,31),(-17,36),(-14,32),(-11,31),(-9,33),(-9,38),(-12,43),(-18,48),(-23,51),(-26,58),(-26,65)],3.8,bevel=.4)
        rail([(-3,61),(0,61),(1,54),(1,36),(-4,33)],2.1,3.4)
        slab([(-2,52),(-2,60),(0,65),(2.4,60),(2.4,52)],4.6,bevel=.35)
        rail([(2,54),(6,54)],2.8,3.8)
        slab([(6,50),(6,59),(12,54)],4.5,bevel=.35)
        spindle([(26,1.6),(28,2.2),(30,1.6)],6)
        rail([(0,-34),(-3.6,-40),(0,-46)],1.55,2.8)
        rail([(0,-34),(3.6,-40),(0,-46)],1.55,2.8)
        return [(-24,66,1),(-25,55,1),(-18,47,1),(-15,33,1),(-8,23,1),(12,54,1)]

    if kind=='crosscurrent':
        # A solid bridge and broad opposite cutting fins, not narrow bow limbs.
        slab([(-31,70),(-25,65),(-18,62),(-15,59),(-15,48),(-12,44),(-19,40),(-22,33),(-28,43),(-31,55)],4.2,bevel=.5)
        slab([(18,58),(29,61),(31,51),(29,42),(22,34),(23,42),(15,44),(18,48)],4.2,bevel=.5)
        slab([(-19,60),(20,57),(20,51),(-19,54)],4.5,bevel=.4)
        slab([(-3.5,51),(-3.5,61),(-1.8,63),(2,63),(3.5,61),(3.5,51),(1.8,49),(-1.8,49)],5.4,bevel=.42)
        spindle([(29,1.7),(31,2.4),(33,1.7)],8)
        spindle([(-34,1.4),(-37,2.6),(-39,2.6),(-39.8,3.3),(-43,3.3),(-44,2.3)],8)
        return [(-30,64,1),(-29,50,1),(-22,35,1),(30,56,1),(30,45,1),(23,36,1)]

    if kind=='foldedfan':
        # Three broad blades share a hub; two elongated blade windows remain
        # open. Small depth offsets reveal overlaps without detached roots.
        window([(2,56),(24,72),(22,57),(7,49)],[(13,60),(21,68),(20,61),(12,56)],3.8,z=.7)
        window([(3,50),(28,59),(31,51),(28,42)],[(20,48),(28.8,48),(28,45),(22,46)],3.8,z=-.3)
        slab([(3,46),(22,39),(20,32),(11,26),(13,32),(12,37)],3.8,z=-.8,bevel=.4)
        slab([(-1.5,44),(-3.4,49),(-2,57),(2.5,57),(7,51),(5,46)],5.2,bevel=.42)
        # Short arched neck joining blade hub and conventional straight haft.
        slab([(-1.7,34),(-2.5,41),(-1,47),(2,47),(3,41),(1.7,34)],4.3,bevel=.35)
        rail([(-2,51),(-7,51)],3.4,4.2)
        slab([(-7,47),(-9,46),(-11,49),(-10,54),(-8,56),(-7,54)],4.6,bevel=.35)
        spindle([(29,1.5),(32,2.2),(34,1.5)],4)
        spindle([(-34,1.4),(-37,2.1),(-40,3),(-46,.08)],4)
        return [(24,70,1),(22,60,1),(30,53,1),(29,45,1),(21,36,1),(12,27,1)]
    raise ValueError(kind)
