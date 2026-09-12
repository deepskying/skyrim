"""Four independent cut-crystal silhouettes with a textured solid body.

Lofted closed crystals use short axial stations and continuous bow skin weights.
Large planar facets are geometric; smaller inclusions belong to the texture maps.
"""
import math
import numpy as np
from mathutils import Vector
import mesh_builder as mb
from heteromorphic_geometry import binding
from geometric_helpers import ANCHORS,STRING_X


def build(spec,strip,ring,blade,angular):
    import solid_geometry
    solid_geometry.binding=binding
    kind=spec['design'];anchors=[]

    def crystal(a,b,width,depth,category='CrystalBody',roll=0):
        a,b=Vector(a),Vector(b);axis=(b-a).normalized()
        side=Vector((axis.y,-axis.x,0)).normalized();normal=side.cross(axis).normalized()
        verts=[];faces=[];uv=[];weights=[];sides=6;stride=sides+1
        # Blunt root joins the spine; broad middle and a bevelled pointed crown.
        stations=max(6,math.ceil((b-a).length/.9))
        for i,t in enumerate(np.linspace(0,.985,stations)):
            scale=float(np.interp(t,[0,.14,.72,.90,.985],[.55,1,.92,.48,.035]))
            c=a.lerp(b,float(t))
            for j in range(stride):
                angle=math.tau*j/sides+roll
                q=c+side*(width*scale*math.cos(angle))+normal*(depth*.5*scale*math.sin(angle))
                verts.append(tuple(q));uv.append((j/sides,float(t)));weights.append(binding(c))
            if i:
                for j in range(sides):
                    v=(i-1)*stride+j;w=v+1
                    faces.append((v,w,w+stride,v+stride))
        faces.extend([tuple(range(sides-1,-1,-1)),tuple((stations-1)*stride+j for j in range(sides))])
        # Orient closed solids consistently regardless of upper/lower limb.
        volume=sum(Vector(verts[f[0]]).dot(Vector(verts[f[j]]).cross(Vector(verts[f[j+1]])))/6 for f in faces for j in range(1,len(f)-1))
        if volume<0:faces=[f[::-1] for f in faces]
        mb.batches[category].add(verts,faces,uv,weights)

    ys=np.linspace(-5.6,5.6,53)
    widths={'ruby':1.2,'emerald':1.05,'frost':1.15,'amethyst':1.0}
    strip([Vector((1.3,float(y),0)) for y in ys],[widths[kind]+.15*math.cos(y/5.6*math.pi) for y in ys],2.6,0)
    for sign in (-1,1):
        def p(x,y,z=0):return Vector((x,sign*y,z))
        end=abs(ANCHORS[sign]);tip=p(STRING_X,end)
        def rail(coords,width,depth=3):
            angular([p(*v) for v in coords],width,depth,edge=0)
        def shard(a,b,w,d=4,cat='CrystalBody',roll=0):crystal(p(*a),p(*b),w,d,cat,roll)
        if kind=='ruby':
            # Broad stepped cleaver facets, with a deep zigzag outer silhouette.
            rail([(1.3,5.5),(4,13),(7,25),(2,40),(STRING_X,end)],[1.3,2.3,2.1,1.6,.35],3.4)
            for a,b,w in [((3,9),(15,24),4.8),((6,22),(13,39),4.4),((3,36),(2,50),3.4),((-2,46),(STRING_X,end),1.8)]:shard(a,b,w,5.4)
            shard((1.3,5.7),(6,12),2.9,4.1)
            shard((4,13,-1.8),(10,21,-1.8),.7,1.2,'CrystalEdge')
            marks=[p(13,22,-3.1),p(11,35,-3.1),p(1,47,-2.8)]
        elif kind=='emerald':
            # A long fork of prismatic crystal encloses a narrow leaf-shaped void.
            rail([(1.3,5.5),(5,13),(10,27),(3,43),(STRING_X,end)],[1.1,1.5,1.7,1.5,.35],3.5)
            rail([(3,11),(-3,23),(-2,36),(3,43)],[1.2,1.5,1.3,.8],3.0)
            for a,b,w in [((5,14),(14,33),3.2),((8,29),(4,46),2.8),((-3,22),(-6,37),2.0),((1,42),(STRING_X,end),1.6)]:shard(a,b,w,4.5,roll=.15)
            shard((1.3,5.5),(-3,12),2.4,3.8)
            shard((4,11,-1.6),(8,18,-1.6),.65,1.1,'CrystalEdge')
            marks=[p(11,26,-2.8),p(-4,32,-2.5),p(2,44,-2.5)]
        elif kind=='frost':
            # Continuous wide glacier crescent, asymmetric teeth only on outer edge.
            ys2=np.linspace(5.5,end,95);t=(ys2-5.5)/(end-5.5)
            pts=[p(1.3*(1-v)+STRING_X*v+17*math.sin(math.pi*v),y) for v,y in zip(t,ys2)]
            strip(pts,[1.2*(1-v)+.3*v+3.2*math.sin(math.pi*v) for v in t],4.8,0,roll=[.15*math.sin(v*math.pi*2) for v in t])
            for a,b,w in [((9,18),(19,27),2.9),((11,28),(16,39),2.5),((7,38),(7,48),1.9)]:shard(a,b,w,5.8,roll=.45)
            shard((.2,5.7),(4,12),2.7,3.7)
            shard((7,20,-2.5),(9,32,-2.5),.7,1.0,'CrystalEdge')
            marks=[p(17,25,-3.0),p(14,36,-3.2),p(5,45,-2.7)]
        else:
            # Open elongated lozenge vaults with staggered faceted amethyst terminals.
            rail([(1.3,5.5),(3,12),(9,24),(4,38),(STRING_X,end)],[1.15,1.4,1.7,1.3,.35],3.4)
            rail([(3,12),(-3,22),(4,38)],[1.3,1.5,1.15],3.5)
            rail([(9,24),(17,31),(3,45),(-2,37)],[1.4,1.55,1.35,1.1],3.2)
            shard((9,23),(18,33),3.9,5.7,roll=.3)
            shard((3,36),(0,50),3.4,5,roll=-.3)
            shard((-2,19),(-3,29),2.7,4.5)
            shard((1.3,5.8),(4,12),2.4,4.2)
            shard((7,22,-1.6),(11,27,-1.6),.75,1.2,'CrystalEdge')
            marks=[p(-3,25,-2.8),p(15,31,-3.2),p(1,46,-2.9)]
        # A small crystal nock makes the final string contact unambiguous.
        shard((STRING_X+.5,end-2),(STRING_X,end+1),.65,1.6)
        for pos in marks:
            w=binding(pos)
            anchors.append({'position':list(pos),'bone':max(w,key=w.get),'side':sign,'direction':(.35,sign*.7,0)})
    return anchors
