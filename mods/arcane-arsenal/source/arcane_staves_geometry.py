"""The approved stacked torch, open shuttle, suspended steps and folded void.

Y is the staff axis; the continuous narrow palm section spans -12..8.
All silhouette details are solid geometry. No alpha planes or central gems.
"""
import math
from mathutils import Vector


def build(spec, solid):
    key=spec['key']
    def prism(name,points,depth=2,z=0,bevel=.13):
        n=len(points)
        obj=solid([(x,y,z+d) for d in (-depth/2,depth/2) for x,y in points],
                  [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],bevel)
        obj.name=name
        return obj
    def ribbon(name,sections,bevel=.15):
        # Each cross section specifies center, width, depth, rotation about Y.
        verts=[]
        for x,y,z,w,d,a in sections:
            a=math.radians(a)
            for sx,sz in ((-1,-1),(1,-1),(1,1),(-1,1)):
                u=sx*w/2;v=sz*d/2
                verts.append((x+u*math.cos(a)+v*math.sin(a),y,z-u*math.sin(a)+v*math.cos(a)))
        faces=[(3,2,1,0),tuple(range(len(verts)-4,len(verts)))]
        for i in range(len(sections)-1):
            faces.extend((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j) for j in range(4))
        obj=solid(verts,faces,bevel);obj.name=name
        return obj
    # Small square/faceted section, a modest butt and no collar inside the palm.
    ribbon('Shaft',[(0,-70,0,3.6,3.6,0),(0,-65,0,3.6,3.6,0),(0,-64,0,2.5,2.5,0),(0,-60,0,2.5,2.5,0),(0,-58,0,2.1,2.1,10),
                    (0,-15,0,2,2,0),(0,-12,0,2,2,0),(0,8,0,2,2,0),
                    (0,20,0,2.3,2.3,10),(0,30,0,2.6,2.6,25)],.1)
    # Inset-looking rails are physical chamfered bars, outside the palm.
    prism('LowerChannel',[(-.23,-56),(.23,-56),(.23,-17),(-.23,-17)],.18,1.03,.04)
    prism('UpperChannel',[(-.25,10),(.25,10),(.25,25),(-.25,25)],.2,1.2,.04)
    ribbon('ButtCollar',[(0,-64,0,2.8,2.8,0),(0,-63,0,3.5,3.5,0),(0,-59,0,3.5,3.5,0),(0,-58,0,2.1,2.1,0)],.1)
    ribbon('NeckCollar',[(0,9,0,2.3,2.3,0),(0,10,0,3.3,3.3,0),(0,11,0,2.3,2.3,0)],.09)
    if key=='stafftorch':
        ribbon('TorchSpine',[(0,11,0,2.5,2.5,10),(-2,27,0,3.4,2.4,35),(-1,46,0,2.6,2.2,15),(-.5,67,0,.3,.3,15)])
        for i,(x,y,z,w,h) in enumerate([(-1,14,1,6,25),(4,35,-.5,7,23),(-4,44,.5,8,22),(1,57,-.8,8,19)]):
            # Raised middle ridge gives each tapered plate two genuinely different faces.
            pts=[(x+w*.15,y,z),(x+w*.52,y+h-7,z),(x-w*.58,y+h,z),(x-w*.20,y+8,z)]
            vs=pts+[(x+w*.2,y+h-8,z+2),(x-w*.20,y+8,z+.4)]
            obj=solid(vs,[(3,2,1,0),(0,1,4),(1,2,4),(2,5,4),(5,3,0,4),(3,5,2)],.12);obj.name='TorchPlate'+str(i)
        return
    if key=='staffshuttle':
        ribbon('ShuttleFront',[(0,11,-1,2.8,1.6,-20),(2,22,1,3.4,1.7,20),(-3,35,0,4,1.7,-25),(-9,48,1,4.3,1.7,-25),(-7,57,2,4,1.7,-20),(-1,76,0,.3,1,15)])
        ribbon('ShuttleBack',[(0,11,1,2.8,1.6,25),(-2,24,-1,3.4,1.7,-20),(4,35,1,3.8,1.7,25),(9,49,-1,4.2,1.7,20),(6,60,-2,3.7,1.7,15),(-1,76,0,.3,1,-15)])
        return
    if key=='staffsteps':
        ribbon('StepSpine',[(0,25,0,2.4,2.4,20),(0,62,0,1.7,1.7,20),(0,75,0,.2,.2,20)])
        for i,(y,w,angle) in enumerate([(31,19,-18),(43,17,22),(55,13,-20),(65,7,20)]):
            ribbon('Step'+str(i),[(0,y,0,w,4,angle),(0,y+4.3,0,w,4,angle)],.17)
        ribbon('StepNeck',[(0,19,0,2.4,2.4,10),(0,29,0,3.6,2.6,65),(0,35,0,2.5,2.5,25)],.13)
        return
    if key=='stafffold':
        ribbon('FoldNeck',[(0,11,0,2.5,2.5,0),(-2,23,0,3,2,30),(0,39,0,3,2,65)])
        # Four folded broad faces enclose a real, elongated open volume.
        ribbon('FoldLeft',[(0,33,0,1.8,1.4,20),(-9,45,2,5.2,1.7,-35),(-7,56,1,5,1.7,-25),(4,76,-1,.25,1,0)],.17)
        ribbon('FoldRight',[(0,33,0,1.8,1.4,-10),(8,46,-2,5,1.7,35),(8,57,-2,4.8,1.7,20),(4,76,-1,.25,1,0)],.17)
        return
    raise ValueError(key)
