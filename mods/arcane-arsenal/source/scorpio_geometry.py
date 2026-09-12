"""Four separately authored Scorpio silhouettes from scorpio-four-redesign-02.

Pincer plates, three-cell rhombic trusses, stepped armour, asymmetric stinger.
Closed bevelled polygons retain concave notches; no shared flowing-band limbs.
The palm and both string anchors stay on the established vanilla bow rig.
"""
import math
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
import mesh_builder as mb
from geometric_helpers import ANCHORS, STRING_X


def binding(pos):
    """Continuous weights prevent nearest-reference-vertex steps on broad plates.

    This field is scoped to Scorpio. Bowstring weights retain their own mapping.
    """
    y=abs(pos.y);side='Up' if pos.y>=0 else 'Lo'
    mid='Bow_MidBone';first='Bow_'+side+'Bone1';second='Bow_'+side+'Bone2'
    if y<=6.5:return {mid:1.0}
    def mix(a,b,t):
        t=t*t*(3-2*t)
        return {a:1-t,b:t}
    if y<19:return mix(mid,first,(y-6.5)/12.5)
    if y<=21:return {first:1.0}
    if y<35:return mix(first,second,(y-21)/14)
    return {second:1.0}


def build(spec,strip,ring,blade,angular):
    import solid_geometry
    solid_geometry.binding=binding
    kind=spec['design'];anchors=[]

    def plate(points,depth=2.4,bevel=.32):
        """Closed concave plate with planar caps, bevels and subdivided skin field."""
        pts=[Vector(v) for v in points]
        area=sum(a.x*b.y-b.x*a.y for a,b in zip(pts,pts[1:]+pts[:1]))
        if area<0:pts.reverse()
        inset=[]
        for i,p in enumerate(pts):
            a=(p-pts[i-1]).normalized();b=(pts[(i+1)%len(pts)]-p).normalized()
            na=Vector((-a.y,a.x,0));nb=Vector((-b.y,b.x,0))
            inset.append(p+(na+nb)*bevel/max(.22,1+na.dot(nb)))
        verts=[];faces=[];weights=[];uv=[]
        def add(v):
            verts.append(tuple(v));weights.append(binding(v));uv.append((v.x/30,v.y/60));return len(verts)-1
        def triangle(a,b,c):
            count=max(2,math.ceil(max((b-a).length,(c-b).length,(a-c).length)/1.8))
            grid={}
            for i in range(count+1):
                for j in range(count+1-i):grid[i,j]=add(a+(b-a)*(i/count)+(c-a)*(j/count))
            for i in range(count):
                for j in range(count-i):
                    faces.append((grid[i,j],grid[i+1,j],grid[i,j+1]))
                    if i+j<count-1:faces.append((grid[i+1,j],grid[i+1,j+1],grid[i,j+1]))
        for side in (-1,1):
            cap=[v+Vector((0,0,side*depth/2)) for v in inset]
            for tri in tessellate_polygon([cap]):
                vertices=[cap[v] if isinstance(v,int) else v for v in tri]
                triangle(*(vertices if side>0 else vertices[::-1]))
            for i in range(len(pts)):
                j=(i+1)%len(pts)
                a=pts[i]+Vector((0,0,side*depth*.26));b=pts[j]+Vector((0,0,side*depth*.26))
                c=cap[j];d=cap[i]
                for tri in ((a,b,c),(a,c,d)):
                    triangle(*(tri if side>0 else tri[::-1]))
            # Fine luminous inset traces are actual geometry on both faces.
            trace=[]
            for a,b in zip(cap,cap[1:]+cap[:1]):
                trace.extend(a.lerp(b,float(t)) for t in np.linspace(0,1,max(3,math.ceil((b-a).length/.8)))[:-1])
            trace.append(trace[0])
            mb.sweep(trace,[.065]*len(trace),'ScorpioEdge',binding,sides=6)
        for a,b in zip(pts,pts[1:]+pts[:1]):
            lo=Vector((0,0,-depth*.26));hi=-lo
            triangle(a+lo,b+lo,b+hi);triangle(a+lo,b+hi,a+hi)
        mb.batches['ScorpioBody'].add(verts,faces,uv,weights)

    # Four distinct palms; the fingers grasp the same tested central position.
    ys=np.linspace(-5.6,5.6,53)
    if kind=='scarlet_pincer':
        widths=[1.2+.22*math.cos(y*math.pi/11.2) for y in ys];roll=None
    elif kind=='jade_lattice':
        widths=[1.05+.15*abs(y)/5.6 for y in ys];roll=[.13*math.sin(y) for y in ys]
    elif kind=='azure_bastion':
        widths=[1.35+.28*(1-abs(y)/5.6) for y in ys];roll=None
    else:
        widths=[1.2+.5*(abs(y)/5.6)**2 for y in ys];roll=[.65*y/5.6 for y in ys]
    strip([Vector((1.3,float(y),0)) for y in ys],widths,2.8,.052,roll=roll)
    if kind=='scarlet_pincer':
        plate([(3.3,-6,0),(8.8,-3.7,0),(10,0,0),(8.8,3.7,0),(3.3,6,0),(6.1,0,0)],2.4)
    elif kind=='jade_lattice':
        angular([Vector((2.6,-7,0)),Vector((10,0,0)),Vector((2.6,7,0))],[.8,1.05,.8],2.0)
    elif kind=='violet_stinger':
        blade([Vector((3.1,5.1,0)),Vector((6.8,3.6,0)),Vector((4.7,-.4,0))],2.1)

    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def p(x,y,z=0):return Vector((x,sign*y,z))
        def poly(coords,depth=2.4,bevel=.32):plate([p(*v) for v in coords],depth,bevel)
        def rail(coords,widths,depth=2.2):angular([p(*v) for v in coords],widths,depth)
        tip=p(STRING_X,end)
        if kind=='scarlet_pincer':
            rail([(1.3,5.5),(2.5,9),(7.5,16),(8,31),(-1,46),(STRING_X,end)],
                 [1.6,2.1,1.5,1.35,1.0,.4],2.6)
            # Two opposed pincer blades with broad faces and a deep open bite.
            poly([(3.5,11),(11,17),(26,31),(13.5,27),(7,24)],3.0)
            poly([(7,25),(12,34),(23,37.5),(16,40),(15,45),(2.2,56),(7.5,37)],2.8)
            poly([(-1.2,7.5),(3.8,7),(7,10.5),(5,14),(1,13.4),(-1.9,10)],3.3)
            poly([(-.3,8.2),(3.2,8),(5.2,10.4),(4.2,12.3),(1.4,11.9)],3.6,.2)
            # Segmented neck cuffs lead into a small spear rather than a crescent.
            for t in (.55,.74,.9):
                c=p(-1,46).lerp(tip,t);d=(tip-p(-1,46)).normalized();n=Vector((d.y,-d.x,0))
                plate([c-d*.85-n*1.15,c+d*.85-n*1.15,c+d*.85+n*1.15,c-d*.85+n*1.15],2.8,.2)
            poly([(STRING_X-1,end-.8),(STRING_X+1.6,end),(STRING_X+.5,end+6),(STRING_X-1.5,end+1.5)],2.5,.2)
            marks=[p(12,22,-2.4),p(14,38,-2.4),p(-2,47,-2.0)]
        elif kind=='jade_lattice':
            ends=[p(1.3,6),p(4,20.5),p(1,38),tip]
            for i,(a,b) in enumerate(zip(ends,ends[1:])):
                d=(b-a).normalized();n=Vector((d.y,-d.x,0));c=(a+b)*.5
                q=[a,c+n*[4.1,4.8,3.4][i],b,c-n*[4.1,4.8,3.4][i]]
                ring(q,[1.0,1.15,.85][i],2.35)
                if i==1:
                    blade([c-d*4.5,c+n*1.6,c+d*4.5,c-n*1.6],3.2)
                    # Narrow rear spar supports the crystal, keeping the face open.
                    angular([a+Vector((0,0,.8)),b+Vector((0,0,.8))],[.26,.26],.7,.025)
            rail([(1.3,6),(6,18),(3.8,36),(STRING_X,end)],[.4,.5,.45,.3],1.3)
            poly([(-.5,5.3),(3.1,5.3),(3.7,6.5),(2.9,7.2),(-.3,7.2),(-1,6.4)],3.1,.23)
            blade([tip+p(-1,-1),tip+p(1.8,0),tip+p(.4,7),tip+p(-1.8,1)],3)
            blade([tip+p(-3,-.6),tip+p(-.2,-2),tip+p(3.4,1.5),tip+p(.2,1)],2.4)
            marks=[p(5,13,-2.3),p(3,29,-2.6),p(-6,45,-2.1)]
        elif kind=='azure_bastion':
            # One closed C-shaped shoulder, then three independently cut plates.
            # The large slot and staircase profile are intentionally rectilinear.
            poly([(-.9,6),(4.3,6),(7.2,9),(7.2,16),(-6.8,27),(-9.8,25),
                  (-9.8,19),(2.5,13.8),(2.5,9.8),(-.9,9.8)],3.4,.45)
            poly([(-8.2,24),(1.4,31),(1.4,40),(-6.4,45),(-8.2,42)],3.0,.4)
            poly([(-9.6,29),(-9.6,41),(-14,44),(-14,32)],2.5,.32)
            rail([(-7.6,33,.9),(-12,33,.9)],[.75,.75],1.2)
            rail([(-7.4,39,.9),(-12,39,.9)],[.75,.75],1.2)
            poly([(-7.8,43),(-7.8,51),(STRING_X,end),(STRING_X-1.8,end-2),(-15,47)],3.2,.37)
            # Recessed connecting spine remains visible only in the panel seams.
            rail([(1.3,6),(4.5,14),(-7.4,24),(-7.2,43),(STRING_X,end)],
                 [.85,.85,.7,.7,.55],1.5)
            poly([(-.5,4.8),(3.1,4.8),(3.5,6.2),(2.7,7),(-.1,7),(-.9,6.2)],3.5,.25)
            poly([(STRING_X-1.5,end-1),(STRING_X+1.4,end),(STRING_X+3,end+4),
                  (STRING_X+1.2,end+4.5),(STRING_X-2.2,end+2)],3.1,.3)
            marks=[p(3.5,15,-2.8),p(-2.5,34,-2.5),p(-11,48,-2.7)]
        else:
            # Longer visual upper limb, hooked lower tail. Both string nocks are fixed.
            if sign==1:
                joints=[p(1.3,6),p(7,18),p(6,31),p(-1,44),tip]
                widths=[3.2,3.4,2.8,1.85]
            else:
                joints=[p(1.3,6),p(7,17),p(-1,29),p(4,42),tip]
                widths=[3.1,3.5,2.6,2.05]
            for i,(a,b) in enumerate(zip(joints,joints[1:])):
                delta=b-a;d=delta.normalized();n=Vector((d.y,-d.x,0));w=widths[i]
                # Six-sided crystal armour with sharp skewed facets, not round rails.
                aa=a+d*(.6 if i else 0);bb=b-d*(.6 if i<3 else 0)
                pts=[aa,aa+delta*.26+n*w,bb-d*1.2+n*w*.42,bb,
                     bb-d*1.5-n*w*.55,aa+delta*.19-n*w*.55]
                plate(pts,2.6,.27)
                angular([aa+Vector((0,0,-1.4)),bb+Vector((0,0,-1.4))],[.08,.05],.10,.025)
                if i<3:
                    # Faceted solid coupler occupies the joints in the reference.
                    blade([b-d*1.5,b+n*1.6,b+d*1.5,b-n*1.6],3.1)
            poly([(-.4,5),(3.2,5),(4.7,6.6),(-1.8,7.4)],2.8,.25)
            if sign==1:
                poly([(STRING_X-1,end-.5),(STRING_X+1.6,end-1),
                      (STRING_X-3.0,end+10),(STRING_X-1.7,end+1)],2.6,.16)
            else:
                poly([(2.4,40),(-1,42),(STRING_X-1.8,end+5),
                      (STRING_X-2.0,end-.5),(STRING_X,end-4)],2.7,.27)
            marks=[joints[1]+p(0,0,-2.6),joints[2]+p(0,0,-2.6),joints[3]+p(0,0,-2.6)]
        # Emission moves away from each local blade face, never a central star.
        for pos in marks:
            w=binding(pos)
            direction={'scarlet_pincer':(.75,sign*.4,0),'jade_lattice':(.35,sign*.65,0),
                       'azure_bastion':(0,-sign,0),'violet_stinger':(.35,sign*.85,0)}[kind]
            anchors.append({'position':list(pos),'bone':max(w,key=w.get),'side':sign,'direction':direction})
    return anchors
