"""Second approved long-dagger set: trace each concept's distinct silhouette."""
import math


def build(spec,slab,rail,frame,solid):
    def curve(a,b,c,d,count=18):
        return [tuple((1-t)**3*a[j]+3*(1-t)**2*t*b[j]+3*(1-t)*t*t*c[j]+t**3*d[j] for j in range(2)) for t in (i/count for i in range(count+1))]

    def smooth_loop(points):
        out=[];n=len(points)
        for i,p1 in enumerate(points):
            p0,p2,p3=points[(i-1)%n],points[(i+1)%n],points[(i+2)%n]
            for t in (0,.25,.5,.75):
                out.append(tuple(.5*((2*p1[j])+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t**3) for j in range(2)))
        return out

    def spindle(rings,sides=8):
        vs=[(r*math.cos(math.pi/8+i*math.tau/sides),y,r*math.sin(math.pi/8+i*math.tau/sides)) for y,r in rings for i in range(sides)]
        fs=[tuple(range(sides-1,-1,-1)),tuple(range(len(vs)-sides,len(vs)))]
        for j in range(len(rings)-1):
            for i in range(sides):
                a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
        return solid(vs,fs,.1)

    def window(outer,inner,depth=2.2):
        # Explicit annular faces keep apertures open in the triangulated NIF.
        if spec['design']=='veinwing':outer,inner=smooth_loop(outer),smooth_loop(inner)
        n=len(outer);assert n==len(inner)
        vs=[(x,y,d) for d in (-depth/2,depth/2) for loop in (outer,inner) for x,y in loop]
        fs=[]
        for i in range(n):
            j=(i+1)%n
            fs.extend([(i,j,j+n,i+n),(i+2*n,i+3*n,j+3*n,j+2*n),(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n)])
        return solid(vs,fs,.16)

    kind=spec['design']
    spindle([(-7,1.12),(4.6,1.12)],4 if kind in ('thunderbreak','terrace') else 8)
    for y in (-6.7,4.5):spindle([(y-.18,1.29),(y+.18,1.29)])
    spindle([(4.4,1.08),(5.4 if kind=='terrace' else 9.2,1.2)])

    if kind=='thunderbreak':
        # Broad continuous zigzag, with two unmistakable changes of direction.
        slab([(-2.1,8),(-2.8,12),(-5,17),(-.8,25),(-3.9,34),(3.3,45),
              (.7,34),(3.3,25),(-.1,17),(2.4,11),(1.6,8)],2.6,bevel=.36)
        slab([(-2.1,6.6),(-2.1,9.2),(1.9,10.2),(2.6,7)],2.8,bevel=.22)
        slab([(-4.9,6.7),(-3.2,8),(3.6,7.3),(5.1,5.6),(1,6),(-1.1,5.3)],2.8,bevel=.23)
        spindle([(-7,1.1),(-8,1.8),(-9.4,1.5),(-12.4,.06)],4)
        return [(-4.6,17,.9),(-3.4,33.5,.9),(2.9,25,.9),(.3,36,.9),(-1.6,22,.9),(-.2,11,.9)]

    if kind=='veinwing':
        # One connected leaf perimeter plus two diagonal ribs: three true holes.
        window([(0,8),(-2,11),(-3.6,18),(-4.8,26),(-4.2,33),(-2.3,39),
                (3,45),(2.2,38),(3.3,32),(4.2,24),(3.1,16),(1.8,10)],
               [(.3,13),(-.5,15),(-1,19),(-1.2,25),(-.4,31),(.2,35),
                (1.5,39),(1.1,35),(1.7,31),(2.3,24),(1.6,18),(.9,15)],2.4)
        rail([(-1.7,20),(-.2,20.8),(2.8,23.4)],1.1,2.4)
        rail([(-1.4,28),(-.1,28.7),(2.3,31.1)],1.1,2.4)
        slab([(-1.5,7),(-1.5,10.2),(1.7,10.2),(1.7,7)],2.5,bevel=.18)
        slab([(-4,7),(-1.7,9),(2,9.5),(5.1,12),(4.2,8.4),(1.2,6),(-.4,5.2)],2.7,bevel=.24)
        rail([(-2.7,7.6),(.2,8.1),(3.7,10)],.6,2.8)
        spindle([(-7,1.1),(-9,2.1),(-12.3,.06)],6)
        return [(-3.8,29,.9),(-2.6,35,.9),(2.5,32,.9),(3.5,24,.9),(2.3,17,.9),(-2.6,17,.9)]

    if kind=='terrace':
        # Continuous straight edge, three large spine terraces and a tanto tip.
        slab([(-2.6,9),(-2.6,45),(.6,39),(.6,31),(2.2,29.5),(2.2,22),
              (3.9,20.5),(3.9,9)],2.8,bevel=.3)
        for z in (-1.35,1.35):
            rail([(-2,44),(.1,38.8),(.1,30.8),(1.7,29.2),(1.7,21.8),(3.4,20.2),(3.4,9.5)],.5,.35,z)
        # The guard itself carries the blade, leaving a genuine full-width hole.
        window([(-4.2,4.6),(-4.2,9.4),(4.2,9.4),(4.2,4.6)],
               [(-2.9,5.8),(-2.9,8.2),(2.9,8.2),(2.9,5.8)],2.8)
        spindle([(-7,1.15),(-7.6,1.5),(-10.7,1.5),(-11.3,1.2)],4)
        return [(.2,37,.9),(.2,31.5,.9),(1.8,28,.9),(1.8,22.5,.9),(3.5,18,.9),(3.5,12,.9)]

    if kind=='eclipsecrescent':
        # Follow the approved final image: a deep OPEN crescent cutout.
        outer=curve((-1.9,8),(-9.5,19),(-4.5,36),(3.8,45),24)
        upper=curve((3.8,45),(.1,37),(-.4,30),(5,29),16)[1:]
        notch=[(5+5.8*math.cos(t),22+7*math.sin(t)) for t in (math.pi/2+i*math.pi/24 for i in range(1,25))]
        lower=curve((5,15),(1,14),(2.5,10),(1.3,8),10)[1:]
        slab(outer+upper+notch+lower,2.5,bevel=.26)
        for a,b in [((-4.7,7.7),(0,11)),((0,11),(4.7,7.7)),((4.7,7.7),(0,5.2)),((0,5.2),(-4.7,7.7))]:
            rail([a,b],.95,2.8)
        slab([(0,8),(-1.3,10.3),(0,13.7),(1.3,10.3)],2.9,bevel=.22)
        spindle([(-7,1.12),(-7.7,1.5),(-8.3,1.1),(-9.3,1.8),(-12.6,.06)],4)
        return [(2.8,29,.9),(.1,25.5,.9),(-.4,22,.9),(.2,18,.9),(3.2,15.2,.9),(-2.8,33,.9)]
    raise ValueError(kind)
