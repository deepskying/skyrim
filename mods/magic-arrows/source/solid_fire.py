"""Inflated, twisted reference lobes around a solid axial fire-arrow core.

The reference supplies lobe outlines and color, not a complete 3D surface.
Only the lobes are reconstructed; the pictured rods and collars are excluded.
"""
import math
import numpy as np
import bpy,bmesh
from geometry import Mesh
from precision_samples import section

def generate(references,contours,simplify,cleanup,bleed_surface,dds,texroot):
    parts={name:Mesh() for name in ('head','headside','tail','tailside')}
    stats={}
    for part in ('head','tail'):
        box=(18,43,430,288) if part=='head' else (22,68,418,281)
        x0,t0,x1,t1=box
        rgb=references['heads' if part=='head' else 'tails'][t0:t1,x0:x1,:3]
        h,w=rgb.shape[:2];peak=rgb.max(axis=2)
        surface=cleanup(((rgb[:,:,0]>rgb[:,:,2]*1.8+.025)&(peak>.52))|(peak>.72))
        yy,xx=np.indices((h,w));gx=xx+x0;gy=yy+t0
        # Isolate the upper flame lobe; omit the illustrated rod, collar and nock.
        if part=='head':
            axis=153;left,right=61,350;y0,y1=2.1,10.9;radial=2.48/(axis-46)
            mask=surface&(gy<axis-5)&(gx>=left)&(gx<right)
        else:
            axis=155;left,right=98,386;y0,y1=47.2,56.9;radial=2.48/(axis-78)
            mask=surface&(gy<axis-12)&(gx>=left)&(gx<right)
        mask=cleanup(mask)
        paths=[simplify(loop,1.35) for loop in contours(mask)]
        if not paths:raise ValueError('Missing fire '+part+' lobe')
        # Distance inside the lobe drives a rounded belly, tapering at every edge.
        distance=np.zeros((h,w),dtype=np.float32);inside=mask.copy()
        for step in range(1,50):
            distance[inside]=step
            inside=inside & np.roll(inside,1,0)&np.roll(inside,-1,0)&np.roll(inside,1,1)&np.roll(inside,-1,1)
            inside[[0,-1],:]=False;inside[:,[0,-1]]=False
            if not inside.any():break
        for _ in range(3):
            distance=(distance*4+np.roll(distance,1,0)+np.roll(distance,-1,0)+np.roll(distance,1,1)+np.roll(distance,-1,1))/8
        def axial(px):
            u=(px+x0-left)/(right-left)
            return y1-u*(y1-y0) if part=='head' else y0+u*(y1-y0)
        cu=bpy.data.curves.new('fire-'+part+'-lobe-profile','CURVE')
        cu.dimensions='2D';cu.fill_mode='BOTH';cu.extrude=.055
        for loop in paths:
            spline=cu.splines.new('POLY');spline.points.add(len(loop)-1);spline.use_cyclic_u=True
            for p,(px,py) in zip(spline.points,loop):p.co=((axis-t0-py)*radial,axial(px),0,1)
        ob=bpy.data.objects.new(cu.name,cu);bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH')
        ob=bpy.context.object;bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        # Interior samples are needed for convex thickness, not just border extrusion.
        edges=[edge for edge in bm.edges if edge.calc_length()>.40]
        bmesh.ops.subdivide_edges(bm,edges=edges,cuts=3,use_grid_fill=True)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
        local=[];uvs=[]
        for vertex in ob.data.vertices:
            r,y,z=vertex.co
            u=(y1-y)/(y1-y0) if part=='head' else (y-y0)/(y1-y0)
            px=left+u*(right-left)-x0;py=axis-t0-r/radial
            iy=min(h-1,max(0,round(py)));ix=min(w-1,max(0,round(px)))
            belly=.43*(1-math.exp(-float(distance[iy,ix])/7))
            z=math.copysign(.055+belly,z)+.20*math.sin(math.pi*u)
            # Mild longitudinal twist gives each lobe a curved spatial surface.
            twist=.22*math.sin(math.pi*u)
            local.append((r*math.cos(twist)-z*math.sin(twist),y,r*math.sin(twist)+z*math.cos(twist)))
            uvs.append((px/w,1-py/h))
        triangles=[tuple(face.vertices) for face in ob.data.polygons]
        for sector in range(3):
            angle=sector*math.tau/3+(.20 if part=='head' else 0)
            c,s=math.cos(angle),math.sin(angle)
            transformed=[(r*c-z*s,y,r*s+z*c) for r,y,z in local]
            indices={part:{},part+'side':{}}
            for tri in triangles:
                vs=np.array([transformed[i] for i in tri]);n=np.cross(vs[1]-vs[0],vs[2]-vs[0])
                length=np.linalg.norm(n)
                if length<3.2e-5:continue
                # Distinct darker side material makes thickness visible under emission.
                tangential=abs(-n[0]*s+n[2]*c)/length
                cat=part+'side' if tangential<.60 else part
                dst=parts[cat];mapped=[]
                for i in tri:
                    if i not in indices[cat]:
                        indices[cat][i]=len(dst.verts);dst.verts.append(tuple(transformed[i]));dst.uv.append(uvs[i])
                    mapped.append(indices[cat][i])
                dst.tris.append(tuple(mapped))
            mesh=bpy.data.meshes.new('fire-'+part+'-solid-'+str(sector))
            mesh.from_pydata(transformed,[],triangles);mesh.update()
            leaf=bpy.data.objects.new(mesh.name,mesh);bpy.context.scene.collection.objects.link(leaf)
            uv=mesh.uv_layers.new(name='Reference lobe')
            for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
        bpy.data.objects.remove(ob,do_unlink=True)
        # Pad both complete maps so curved side faces never sample the grey backdrop.
        padded=bleed_surface(rgb,surface)
        yi=np.minimum(h-1,np.arange(1024)*h//1024);xi=np.minimum(w-1,np.arange(1024)*w//1024)
        tex=padded[yi[:,None],xi[None,:]].copy();mx=tex.max(axis=2,keepdims=True)
        tex=np.maximum(0,mx-(mx-tex)*1.35)*.72
        dds(texroot/f'fire_{part}.dds',tex)
        # Reduced edge contrast avoids stretching tiny projected sparks into stripes.
        dds(texroot/f'fire_{part}side.dds',tex*.30+np.array((.16,.018,.002)))
        stats[part]=dict(lobes=3,loops_per_lobe=len(paths),triangles=sum(len(parts[p].tris) for p in (part,part+'side')),
                         maximum_lobe_thickness=.97,illustrated_rod_removed=True)
    # A closed central spear supplies an actual point on the same axis as the rod.
    core=Mesh()
    section(core,[(.07,.025,.025,0,0,0),(1.5,.20,.20,0,0,.08),(3.8,.50,.50,0,0,.15),
                  (6.5,.67,.67,0,0,.24),(9.0,.42,.42,0,0,.12),(11.15,.23,.23,0,0,0)],12)
    core.uv=[((61+(10.9-y)/10.83*355-18)/412,1-(153-43-x*35)/245) for x,y,z in core.verts]
    dst=parts['head'];off=len(dst.verts);dst.verts.extend(core.verts);dst.uv.extend(core.uv)
    dst.tris.extend(tuple(i+off for i in tri) for tri in core.tris)
    # One centered connector system, independent of the reference drawing.
    shaft=Mesh();shaft.tube([(0,10.9,0),(0,57.25,0)],.19,12)
    shaft.uv=[((math.atan2(z,x)/math.tau)%1,(y-10.9)/46.35) for x,y,z in shaft.verts]
    parts['shaft']=shaft;trim=Mesh()
    for sector in range(3):
        a=sector*math.tau/3
        stem=Mesh();stem.tube([(.17*math.cos(a),47.35,.17*math.sin(a)),
                              (.82*math.cos(a),48.0,.82*math.sin(a))],[.15,.13],8)
        dst=parts['tail'];off=len(dst.verts);dst.verts.extend(stem.verts)
        dst.uv.extend([(.25,.70)]*len(stem.verts));dst.tris.extend(tuple(i+off for i in tri) for tri in stem.tris)
    for y in (11.1,47.25):
        section(trim,[(y-.25,.22,.22,0,0,0),(y-.15,.32,.32,0,0,0),
                      (y+.15,.32,.32,0,0,0),(y+.25,.22,.22,0,0,0)],12)
    for x in (-.13,.13):trim.tube([(x,57.15,0),(x,57.95,0)],[.095,.07],8)
    parts['trim']=trim
    stats['axial_center']=[0,0];stats['central_spear']=True
    return parts,stats
