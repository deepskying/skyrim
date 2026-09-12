"""Six individually authored geometric solid-light bow silhouettes.

All structural strips use a shared Y-based skin field, including their luminous
edges. The grip stays rigid; the reference skeleton and string anchors do not move.
"""
import math
import numpy as np
from mathutils import Vector
import mesh_builder as mb
from geometric_helpers import ANCHORS, STRING_X

MID={'Bow_MidBone':1.0}
GRIP_STYLES={'plates':'stepped_v_shoulders','hexagon':'faceted_arch_shoulders',
             'squares':'crossed_twist_shoulders','diamonds':'continuous_s_shoulders',
             'triangles':'offset_triangle_gates','chevron':'triple_feather_spines'}

def binding(p):
    if abs(p.y)<=6.5:return MID
    return mb.weights_at(mb.center(p.y))

def curve(control,steps=36):
    """Cubic Bezier used for deliberate continuous grip-to-limb transitions."""
    a,b,c,d=map(Vector,control)
    return [a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+d*t**3
            for t in np.linspace(0,1,steps)]

def build_flow(design,edge_builder):
    def strip(points,widths,depth=1.35,edge=.052,roll=None):
        """Closed bevelled strip, broad face and narrow front/back edge light."""
        points=list(map(Vector,points))
        if isinstance(widths,(int,float)):widths=[widths]*len(points)
        depths=[depth]*len(points) if isinstance(depth,(int,float)) else depth
        verts=[];faces=[];uv=[];weights=[];rims=[[],[],[],[]]
        # Counterclockwise around tangent, chamfered instead of a round wire.
        section=[(-1,-.52),(-.72,-1),(.72,-1),(1,-.52),
                 (1,.52),(.72,1),(-.72,1),(-1,.52)]
        station_weights=[]
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            side=Vector((tangent.y,-tangent.x,0)).normalized()
            normal=side.cross(tangent).normalized()
            if roll is not None:
                angle=roll[i];old_side=side
                side=side*math.cos(angle)+normal*math.sin(angle)
                normal=normal*math.cos(angle)-old_side*math.sin(angle)
            w=binding(p);station_weights.append(w)
            for j,(s,z) in enumerate(section):
                v=p+side*widths[i]*s+normal*(z*depths[i]*.5)
                verts.append(tuple(v));uv.append((j/7,i/(len(points)-1)));weights.append(w)
            for j,k in enumerate((1,2,5,6)):rims[j].append(Vector(verts[-8+k]))
            if i:
                base=(i-1)*8
                for j in range(8):faces.append((base+j,base+(j+1)%8,base+8+(j+1)%8,base+8+j))
        faces.extend([tuple(range(7,-1,-1)),tuple((len(points)-1)*8+j for j in range(8))])
        volume=sum(Vector(verts[f[0]]).dot(Vector(verts[f[j]]).cross(Vector(verts[f[j+1]])))/6
                   for f in faces for j in range(1,len(f)-1))
        if volume<0:faces=[tuple(reversed(f)) for f in faces]
        assert abs(volume)>.00001
        mb.batches['GeometricBody'].add(verts,faces,uv,weights)
        if edge:
            for rim in rims:edge_builder(rim,edge,station_weights)

    def ring(points,width,depth=1.3):
        # Sample each straight side so attached rails/frames deform together.
        pts=[]
        for a,b in zip(points,points[1:]+points[:1]):
            pts.extend(a.lerp(b,float(t)) for t in np.linspace(0,1,max(3,int((b-a).length/.7)+1))[:-1])
        pts.append(pts[0]);strip(pts,width,depth)

    def blade(points,depth=1.3):
        pts=list(map(Vector,points))
        if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0:pts.reverse()
        center=sum(pts,Vector())/len(pts);n=len(pts)
        # Subdivided triangle interiors sample the same skin field as the rails.
        verts=[];faces=[];uv=[];weights=[]
        for z in (-1,1):
            for i in range(n):
                a,b=pts[i],pts[(i+1)%n]
                grid={};res=6
                for u in range(res+1):
                    for v in range(res+1-u):
                        p=center+(a-center)*(u/res)+(b-center)*(v/res)
                        p.z+=z*depth*(.48-.24*(u+v)/res)
                        grid[u,v]=len(verts);verts.append(tuple(p));uv.append((u/res,v/res));weights.append(binding(p))
                for u in range(res):
                    for v in range(res-u):
                        f=(grid[u,v],grid[u+1,v],grid[u,v+1]);faces.append(f if z>0 else f[::-1])
                        if u+v<res-1:
                            f=(grid[u+1,v],grid[u+1,v+1],grid[u,v+1]);faces.append(f if z>0 else f[::-1])
        mb.batches['GeometricBody'].add(verts,faces,uv,weights)
        ring(pts,.13,depth*.48)

    def angular(points,widths,depth=1.8,edge=.052):
        """Sample an authored corner path without smoothing away its silhouette."""
        pts=[];sizes=[]
        for i,(a,b) in enumerate(zip(points,points[1:])):
            for t in np.linspace(0,1,max(3,int((b-a).length/.55)+1))[:-1]:
                pts.append(a.lerp(b,float(t)));sizes.append(widths[i]*(1-t)+widths[i+1]*t)
        pts.append(points[-1]);sizes.append(widths[-1]);strip(pts,sizes,depth,edge)

    # Six independently authored palm silhouettes. They share only the hand's
    # origin and bone, never a common grip/oval template as in 0.10.0.
    ys=np.linspace(-5.8,5.8,41)
    if design=='plates':
        grip=[Vector((1.3+.12*y,float(y),0)) for y in ys]
        widths=[float(np.interp(abs(y),[0,3.4,4.8,5.8],[1.42,1.52,2.08,2.65])) for y in ys]
        strip(grip,widths,2.7,.060)
    elif design=='hexagon':
        grip=[Vector((1.3+.68*(y/5.8)**2,float(y),0)) for y in ys]
        widths=[1.45+.78*(abs(y)/5.8)**2 for y in ys]
        strip(grip,widths,[2.8+.5*(abs(y)/5.8) for y in ys],.055)
    elif design=='squares':
        grip=[Vector((1.3+.82*math.sin(y*math.pi/11.6),float(y),0)) for y in ys]
        widths=[1.58+.46*(abs(y)/5.8) for y in ys]
        strip(grip,widths,2.5,.055,roll=[.43*math.sin(y*math.pi/11.6) for y in ys])
    elif design=='triangles':
        grip=[Vector((float(np.interp(y,[-5.8,-3.2,0,3.2,5.8],[.5,.5,1.3,2.1,2.1])),float(y),0)) for y in ys]
        widths=[1.40+.55*(abs(y)/5.8)**2 for y in ys]
        strip(grip,widths,2.65,.055)
    elif design=='chevron':
        grip=[Vector((1.3-.30*math.cos(y*math.pi/11.6),float(y),0)) for y in ys]
        widths=[1.62+.70*(abs(y)/5.8)**1.8 for y in ys]
        strip(grip,widths,[2.65+.25*(abs(y)/5.8) for y in ys],.055)
    else:
        grip=[Vector((1.3+.42*math.sin(y*math.pi/5.8),float(y),0)) for y in ys]
        widths=[1.35+.72*(abs(y)/5.8)**1.4 for y in ys]
        strip(grip,widths,[2.65-.35*(abs(y)/5.8) for y in ys],.055)
    anchors=[]
    for sign in (-1,1):
        end=abs(ANCHORS[sign])
        def point(x,y,z=0):return Vector((x,sign*y,z))
        def backbone(y):
            t=max(0,min(1,(y-20)/(end-20)))
            bulge={'plates':3.3,'hexagon':4.8,'squares':3.2,'diamonds':3.6,'triangles':4.2,'chevron':3.0}[design]
            return point(7.4*(1-t)+STRING_X*t+bulge*math.sin(math.pi*t),y)
        if design=='plates':
            # Swept triangular opening with wide faceted outer shoulders. The
            # blade collars belong at the palm ends, not at the limb junction.
            a=point(1.3+.12*sign*5.4,5.4)
            angular([a,point(8.6,8.4),point(8.8,16),backbone(22)],
                    [1.65,1.62,1.35,.75],2.15)
            inner=curve([a,point(.8,9.5),point(2.3,16.3),backbone(22)],32)
            strip(inner,[1.05-.34*t for t in np.linspace(0,1,len(inner))],1.65)
            blade([point(-.7,5.4),point(14.7,8.2),point(7.2,10.5)],2.4)
            blade([point(1.4,7.0),point(13.0,11.4),point(7.6,13.0)],1.8)
        elif design=='hexagon':
            # Compact polygonal arch: strong angular outside, concave inner
            # opening and flared faces flowing directly into the first hexagon.
            a=point(1.94,5.4)
            angular([a,point(8.9,10.0),point(7.2,18.6),backbone(22)],
                    [1.45,1.85,1.35,1.18],2.4)
            inner=curve([a,point(-.5,9.0),point(1.8,16.7),backbone(22)],32)
            strip(inner,[1.20-.35*t for t in np.linspace(0,1,len(inner))],2.0)
        elif design=='squares':
            # Two square-derived offset bands swap depth at the shoulders.
            # Their projected openings are angular and skewed, not leaf-shaped.
            a=point(1.3+.82*math.sin(sign*5.4*math.pi/11.6),5.4)
            angular([a,point(9.0,12.1,1.0),point(6.4,19.4,1.3),backbone(22)],
                    [1.15,1.15,.93,.76],1.65)
            angular([a,point(-.6,11.4,-1.1),point(1.4,17.8,-1.3),backbone(22)],
                    [1.10,.95,.96,.80],1.7)
            # A broad diagonal sweep across the shoulder crosses in depth;
            # it wraps into the outer square frame like the concept illustration.
            crossing=curve([a,point(5.6,8.8,-1.6),point(2.8,14.8,-1.5),point(6.4,19.4,.9)],32)
            strip(crossing,[.6+.18*math.sin(math.pi*t) for t in np.linspace(0,1,len(crossing))],1.2,.045)
        elif design=='triangles':
            a=point(.5 if sign<0 else 2.1,5.4)
            # Offset triangular gates grow directly out of the stepped grip.
            # Both point in the same direction, with no overlapping star emblem.
            angular([a,point(10.3,12.0),backbone(22)],[1.2,1.38,.88],2.0)
            angular([a,backbone(22)],[1.0,.82],1.65)
            inner=[point(3.2,8.5,.75),point(7.6,12.4,.75),point(6.1,17.1,.75)]
            ring(inner,.42,1.0)
        elif design=='chevron':
            a=point(1.3,5.4)
            # Three distinct swept ridges make two long slots at each shoulder.
            # Unlike the other grips there is no large closed ring or polygon.
            curves=[(curve([a,point(12.8,9.0),point(14.0,18.5),backbone(22)],40),1.30),
                    (curve([a,point(6.6,10.6),point(10.1,19.0),backbone(22)],40),.90),
                    (curve([a,point(.1,11.5),point(4.4,19.0),backbone(22)],40),.78)]
            for pts,width in curves:
                strip(pts,[width*(1-.36*t) for t in np.linspace(0,1,len(pts))],1.75,.05)
            blade([point(2.5,6.6),point(12.2,13.2),point(7.0,11.2)],1.65)
        else:
            # Flowing diamond: an elongated tapered slit. Both bands sweep to
            # the same side early, so this does not read as a symmetric oval.
            a=point(1.3,5.4)
            outer=curve([a,point(7.0,8.6),point(12.4,19.3),backbone(22)],42)
            inner=curve([a,point(2.9,11.3),point(3.1,17.3),backbone(22)],42)
            strip(outer,[1.55-.78*t for t in np.linspace(0,1,len(outer))],1.85,.05)
            strip(inner,[.93-.25*t for t in np.linspace(0,1,len(inner))],1.55,.05)
        if design=='plates':
            support=[backbone(y) for y in np.linspace(21,end,62)]
            strip(support,.65,1.25)
            # Broad stepping triangular wings, not the old thin triangle chain.
            for i,t in enumerate(np.linspace(0,1,10)):
                y=22+(end-23)*float(1-(1-t)**1.35);p=backbone(y)
                size=.65+4.5*(1-float(t))**.85
                blade([p+point(-.4,-size*.65),p+point(1.1,size*.55),p+point(size*1.6,-size*.92)],1.45)
        elif design=='hexagon':
            # Seven adjoining hexagons use shared stations rather than thin ties.
            stations=[20.5,29.5,37.2,43.3,48.0,51.4,end]
            for lo,hi in zip(stations[:-1],stations[1:]):
                mid=(lo+hi)/2;radius=(hi-lo)*.51
                pts=[backbone(lo),backbone(lo+(hi-lo)*.24)+point(radius,0),
                     backbone(hi-(hi-lo)*.24)+point(radius,0),backbone(hi),
                     backbone(hi-(hi-lo)*.24)-point(radius,0),backbone(lo+(hi-lo)*.24)-point(radius,0)]
                ring(pts,max(.28,.13*(hi-lo)),1.55)
        elif design=='squares':
            # Equilateral diamonds in projection are tilted square frames in 3D.
            for i,t in enumerate(np.linspace(0,1,9)):
                y=22+(end-22)*float(1-(1-t)**1.4);p=backbone(y)
                r=.5+4.6*(1-float(t))**.9
                angle=.28*math.sin(i*.78)
                along=point(-.44,1).normalized();across=Vector((sign*along.y,-sign*along.x,0))
                transverse=across*math.cos(angle)+Vector((0,0,math.sin(angle)))
                pts=[p+along*r,p+transverse*r,p-along*r,p-transverse*r]
                ring(pts,max(.25,.16*r),1.5)
            strip([backbone(y) for y in np.linspace(21,end,60)],.40,1.0,.035)
        elif design=='triangles':
            # Alternating shallow depth and progressive rotation preserve the
            # identity of the open-triangle design, with thick bevelled frames.
            strip([backbone(y) for y in np.linspace(21,end,56)],.34,1.0,.035)
            for i,t in enumerate(np.linspace(0,1,9)):
                y=22+(end-22)*float(1-(1-t)**1.35);p=backbone(y)
                r=.55+4.7*(1-float(t))**.85
                along=point(-.40,1).normalized()
                across=Vector((sign*along.y,-sign*along.x,0))
                tilt=.20*math.sin(i*.8)
                transverse=across*math.cos(tilt)+Vector((0,0,math.sin(tilt)))
                phase=.11*math.sin(i*.7)
                pts=[p+r*(along*math.cos(phase+k*math.tau/3)+transverse*math.sin(phase+k*math.tau/3)) for k in range(3)]
                ring(pts,max(.23,.15*r),1.35)
        elif design=='chevron':
            strip([backbone(y) for y in np.linspace(21,end,56)],.53,1.25,.045)
            # Swept paired feathers: a long outer blade and a shorter open V.
            # This is deliberately broader and more flowing than stacked plates.
            for i,t in enumerate(np.linspace(0,1,9)):
                y=22+(end-23)*float(1-(1-t)**1.4);p=backbone(y)
                r=.55+4.5*(1-float(t))**.85
                a=p+point(-.6,-r*.70)
                tip=p+point(r*1.62,r*.40)
                b=p+point(.2,r*.95)
                angular([a,tip,b],[max(.16,r*.12),max(.21,r*.17),.12],1.35,.045)
                blade([a,tip,p+point(r*.10,r*.50)],1.35)
        else:
            # Two uninterrupted wide ribbons alternately meet and separate,
            # making a chain of elongated rhombi along the curved bow silhouette.
            stations=[20.5,29.4,37.1,43.2,48.0,51.8,end]
            for direction in (-1,1):
                pts=[];width=[]
                for lo,hi in zip(stations[:-1],stations[1:]):
                    for t in np.linspace(0,1,17)[:-1]:
                        y=lo+(hi-lo)*float(t);spread=(hi-lo)*.23*(1-abs(2*float(t)-1))
                        pts.append(backbone(y)+point(direction*spread,0))
                        width.append(.27+.30*(1-(y-20.5)/(end-20.5)))
                pts.append(backbone(end));width.append(.25)
                strip(pts,width,1.35,.055)
        # Tip and nock remain at the original string's exact end location.
        tip=Vector((STRING_X,ANCHORS[sign],-.02))
        strip([backbone(end-1.5),tip,tip+point(-1.0,2.1)],[.46,.52,.075],1.0,.04)
        for y in (23,34,44):
            p=backbone(y)+point(3.5,0,-2.7);w=binding(p)
            anchors.append({'position':list(p),'bone':max(w,key=w.get),'side':sign})
    return anchors
