"""Bevelled strips and plates with matched edge/body skin weights."""
import math
import numpy as np
from mathutils import Vector
import mesh_builder as mb
from geometric_flow import binding

def primitives(edge_builder,body_category):
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
        mb.batches[body_category].add(verts,faces,uv,weights)
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
        mb.batches[body_category].add(verts,faces,uv,weights)
        ring(pts,.13,depth*.48)

    def angular(points,widths,depth=1.8,edge=.052):
        """Sample an authored corner path without smoothing away its silhouette."""
        pts=[];sizes=[]
        for i,(a,b) in enumerate(zip(points,points[1:])):
            for t in np.linspace(0,1,max(3,int((b-a).length/.55)+1))[:-1]:
                pts.append(a.lerp(b,float(t)));sizes.append(widths[i]*(1-t)+widths[i+1]*t)
        pts.append(points[-1]);sizes.append(widths[-1]);strip(pts,sizes,depth,edge)

    return strip,ring,blade,angular
