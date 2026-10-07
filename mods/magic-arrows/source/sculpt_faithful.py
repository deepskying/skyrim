"""Trace reference silhouettes, make real solid curved volumes, project UVs.

This is controlled single-view reconstruction, not automatic complete 3D recovery.
Original references supply individual material maps; no generated generic pattern.
"""
import sys,json,math,struct
from collections import deque
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy,bmesh,numpy as np
from paths import ROOT,BUILD
from geometry import Mesh
from precision_samples import section
ART=ROOT/'art/faithful-samples-01';STAGE=BUILD/'faithful-samples-01'
TEX=STAGE/'data/textures/magicarrows/faithful01';TEX.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
def pixels(path):
    image=bpy.data.images.load(str(path));w,h=image.size
    array=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(array)
    return array.reshape(h,w,4)[::-1].copy()
references={name:pixels(ART/'references'/f'{name}.png') for name in ('heads','tails')}
def srgb(value):return np.where(value<=.0031308,value*12.92,1.055*np.maximum(value,0)**(1/2.4)-.055)
def dds(path,rgb):
    # DDS rows are top to bottom. UVs below account for Blender's V convention.
    h,w=rgb.shape[:2];rgba=np.ones((h,w,4),dtype=np.uint8)*255
    rgba[:,:,:3]=np.clip(srgb(rgb)*255,0,255).astype(np.uint8)
    p=lambda *v:struct.pack('<'+'I'*len(v),*v)
    header=p(124,0x100f,h,w,w*4,0,1)+p(*([0]*11))+p(32,0x41,0,32,255,65280,16711680,4278190080)+p(4096,0,0,0,0)
    path.write_bytes(b'DDS '+header+rgba.tobytes())
def shift(mask,dx,dy):
    out=np.zeros_like(mask);h,w=mask.shape
    out[max(0,dy):min(h,h+dy),max(0,dx):min(w,w+dx)]=mask[max(0,-dy):min(h,h-dy),max(0,-dx):min(w,w-dx)]
    return out

def bleed_surface(rgb,mask):
    """Extend actual colored surface texels through the bevel sampling border."""
    peak=rgb.max(axis=2);chroma=peak-rgb.min(axis=2)
    valid=mask & ((chroma>.10)|(peak>.80))
    if not valid.any():raise ValueError('No colored texels for edge padding')
    out=rgb.copy();seen=valid.copy();h,w=mask.shape
    queue=deque(zip(*np.where(valid)))
    while queue:
        y,x=queue.popleft()
        for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0<=ny<h and 0<=nx<w and not seen[ny,nx]:
                out[ny,nx]=out[y,x];seen[ny,nx]=True;queue.append((ny,nx))
    return out
def cleanup(mask):
    # Join hairline bright cracks, while retaining major through-holes.
    expanded=mask.copy()
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):expanded|=shift(mask,dx,dy)
    result=expanded.copy()
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):result&=shift(expanded,dx,dy)
    h,w=result.shape;seen=np.zeros_like(result);kept=np.zeros_like(result)
    components=[]
    for y,x in zip(*np.where(result)):
        if seen[y,x]:continue
        todo=[(x,y)];seen[y,x]=True;component=[]
        while todo:
            xx,yy=todo.pop();component.append((xx,yy))
            for nx,ny in ((xx+1,yy),(xx-1,yy),(xx,yy+1),(xx,yy-1)):
                if 0<=nx<w and 0<=ny<h and result[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;todo.append((nx,ny))
        if len(component)>=70:components.append(component)
    for component in components:
        for x,y in component:kept[y,x]=True
    # Small dark texel islands are surface texture, not intended holes.
    seen=np.zeros_like(kept)
    for y,x in zip(*np.where(~kept)):
        if seen[y,x]:continue
        todo=[(x,y)];seen[y,x]=True;component=[];boundary=False
        while todo:
            xx,yy=todo.pop();component.append((xx,yy));boundary|=xx in (0,w-1) or yy in (0,h-1)
            for nx,ny in ((xx+1,yy),(xx-1,yy),(xx,yy+1),(xx,yy-1)):
                if 0<=nx<w and 0<=ny<h and not kept[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;todo.append((nx,ny))
        if not boundary and len(component)<180:
            for xx,yy in component:kept[yy,xx]=True
    return kept
def contours(mask):
    # Oriented cell boundary; inner holes automatically wind oppositely.
    edges={};h,w=mask.shape
    for y,x in zip(*np.where(mask)):
        if y==0 or not mask[y-1,x]:edges.setdefault((x,y),[]).append((x+1,y))
        if x==w-1 or not mask[y,x+1]:edges.setdefault((x+1,y),[]).append((x+1,y+1))
        if y==h-1 or not mask[y+1,x]:edges.setdefault((x+1,y+1),[]).append((x,y+1))
        if x==0 or not mask[y,x-1]:edges.setdefault((x,y+1),[]).append((x,y))
    loops=[]
    while edges:
        start=next(iter(edges));p=start;loop=[]
        while True:
            loop.append(p);q=edges[p].pop()
            if not edges[p]:del edges[p]
            p=q
            if p==start:break
            if p not in edges:raise ValueError('Open reference contour')
        if len(loop)>8:loops.append(loop)
    return loops
def simplify(points,tolerance=1.75):
    def rdp(pts):
        if len(pts)<3:return pts
        a=np.array(pts[0]);b=np.array(pts[-1]);p=np.array(pts[1:-1]);d=b-a
        if np.dot(d,d)<1e-8:dist=np.linalg.norm(p-a,axis=1)
        else:
            t=np.clip((p-a)@d/np.dot(d,d),0,1);dist=np.linalg.norm(p-(a+t[:,None]*d),axis=1)
        i=int(np.argmax(dist))+1
        if float(dist[i-1])>tolerance:return rdp(pts[:i+1])[:-1]+rdp(pts[i:])
        return [pts[0],pts[-1]]
    # Split closed contour to avoid a coincident endpoint baseline.
    middle=len(points)//2
    return rdp(points[:middle+1])[:-1]+rdp(points[middle:]+points[:1])[:-1]
def component(key,part,box,y0,y1,maxradial,depth,centerline):
    x0,t0,x1,t1=box;rgb=references['heads' if part=='head' else 'tails'][t0:t1,x0:x1,:3]
    h,w=rgb.shape[:2]
    # Color-select actual surface, excluding charcoal backdrop and most bloom.
    mx=rgb.max(axis=2);mn=rgb.min(axis=2)
    if key=='fire':mask=(rgb[:,:,0]>rgb[:,:,2]*1.8+.025)&(mx>.52)
    else:mask=(rgb[:,:,0]>rgb[:,:,2]*1.08+.020)&(mx>.62)
    mask|=(mx>.72)
    mask=cleanup(mask)
    # Collar engraving is dark surface paint, not perforated metal.
    occupied=np.where(mask)
    left,right=int(occupied[1].min()),int(occupied[1].max())
    for px in range(left,left+int((right-left)*.19)):
        rows=np.where(mask[:,px])[0]
        if len(rows):mask[rows.min():rows.max()+1,px]=True
    # Saved masks are diagnostics for geometry extraction, not delivered concept edits.
    img=bpy.data.images.new(key+'-'+part+'-mask',width=w,height=h)
    diag=np.ones((h,w,4),dtype=np.float32);diag[:,:,:3]=mask[:,:,None]
    img.pixels.foreach_set(diag[::-1].reshape(-1));img.filepath_raw=str(ART/f'{key}-{part}-mask.png');img.file_format='PNG';img.save()
    paths=[simplify(loop) for loop in contours(mask)]
    occupied=np.where(mask);xmin,xmax=int(occupied[1].min()),int(occupied[1].max())+1
    collar=occupied[1]<(xmin+(xmax-xmin)*.07) if part=='head' else occupied[1]>(xmax-(xmax-xmin)*.04)
    cy=float(np.median(occupied[0][collar])) if np.any(collar) else centerline-t0
    if key=='fire' and part=='tail':
        # The farthest bright pixels are flame tips, not the nock center.
        cy=centerline-t0
    radial=maxradial/max(abs(occupied[0]-cy))
    def to_model(x,y):
        longitudinal=(x-xmin)/(xmax-xmin)
        axial=y0+longitudinal*(y1-y0) if part=='tail' else y1-longitudinal*(y1-y0)
        return ((cy-y)*radial,axial,0)
    def to_uv(x,y):
        longitudinal=(y-y0)/(y1-y0) if part=='tail' else (y1-y)/(y1-y0)
        return ((xmin+longitudinal*(xmax-xmin))/w,1-(cy-x/radial)/h)
    cu=bpy.data.curves.new(key+'-'+part+'-traced','CURVE');cu.dimensions='2D';cu.fill_mode='BOTH';cu.resolution_u=2
    # Blender curve's plane is XY, which matches local arrow transverse/longitudinal axes.
    cu.extrude=depth;cu.bevel_depth=.025;cu.bevel_resolution=1
    for loop in paths:
        spline=cu.splines.new('POLY');spline.points.add(len(loop)-1);spline.use_cyclic_u=True
        for p,(x,y) in zip(spline.points,loop):p.co=(*to_model(x,y),1)
    ob=bpy.data.objects.new(cu.name,cu);bpy.context.scene.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bpy.ops.object.convert(target='MESH');ob=bpy.context.object
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    # Curved solid volume with a shallow convex surface. Front/back share reference UVs.
    mesh=ob.data
    for v in mesh.vertices:
        v.co.y=max(.045,min(57.99,v.co.y))
        v.co.x=max(-3.2,min(3.2,v.co.x))
        t=(v.co.y-y0)/(y1-y0)
        bow=.18*math.sin(math.pi*max(0,min(1,t)))
        if key=='fire' and part=='tail':bow=0
        v.co.z+=bow
    mesh.update();uv=mesh.uv_layers.new(name='Reference projection')
    out={part:Mesh(),part+'side':Mesh()}
    for polygon in mesh.polygons:
        pv=np.array([mesh.vertices[i].co[:] for i in polygon.vertices])
        area=np.cross(pv[1]-pv[0],pv[2]-pv[0])
        if np.dot(area,area)<1e-9:continue
        cat=part if abs(polygon.normal.z)>.55 else part+'side';dst=out[cat]
        vertices=[tuple(mesh.vertices[i].co) for i in polygon.vertices]
        start=len(dst.verts);dst.verts.extend(vertices)
        for x,y,z in vertices:
            dst.uv.append(to_uv(x,y))
        dst.tris.append((start,start+1,start+2))
    for loop in mesh.loops:
        x,y,z=mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=to_uv(x,y)
    # Exact dedicated source projection with extra border texel padding.
    # Use 1024 square texture to fit normal Skyrim DDS dimensions.
    yi=np.minimum(h-1,np.arange(1024)*h//1024);xi=np.minimum(w-1,np.arange(1024)*w//1024)
    surface=bleed_surface(rgb,mask) if key=='fire' and part=='tail' else rgb
    tex=surface[yi[:,None],xi[None,:]].copy()
    # Increase color saturation without raising peak brightness or tinting white cores.
    peak=tex.max(axis=2,keepdims=True)
    tex=np.maximum(0,peak-(peak-tex)*(1.35 if key=='fire' else 1.30))*.72
    dds(TEX/f'{key}_{part}.dds',tex)
    dds(TEX/f'{key}_{part}side.dds',tex*.70)
    # Preview mesh material reads the same saved DDS; exported previews reread NIF.
    mat=bpy.data.materials.new(ob.name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');em.inputs['Strength'].default_value=1.65
    image=nodes.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(TEX/f'{key}_{part}.dds'))
    mat.node_tree.links.new(image.outputs['Color'],em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],output.inputs['Surface']);ob.data.materials.append(mat)
    ob.select_set(False)
    return out,dict(loops=len(paths),contour_vertices=sum(map(len,paths)),triangles=sum(len(m.tris) for m in out.values()),holes=sum(1 for loop in paths if sum(loop[i][0]*loop[(i+1)%len(loop)][1]-loop[(i+1)%len(loop)][0]*loop[i][1] for i in range(len(loop)))<0))
report={}
for key in ('fire','holy'):
    if key=='fire':head=(18,43,430,288);tail=(22,68,418,281);center_head=165;center_tail=155
    else:head=(437,347,831,546);tail=(439,349,834,582);center_head=441;center_tail=484
    if key=='fire':
        from solid_fire import generate as solid_fire
        parts,volume_stats=solid_fire(references,contours,simplify,cleanup,bleed_surface,dds,TEX)
        headstats,tailstats=volume_stats['head'],volume_stats['tail']
    else:
        parts,headstats=component(key,'head',head,.07,11.3,2.6,.16,center_head)
        extra,tailstats=component(key,'tail',tail,47.1,57.3,2.65,.10,center_tail);parts.update(extra)
    shaft=Mesh();shaft.tube([(0,10.9,0),(0,57.7,0)],.19,12)
    shaft.uv=[((math.atan2(z,x)/math.tau)%1,(y-10.9)/46.8) for x,y,z in shaft.verts]
    if key!='fire':parts['shaft']=shaft
    trim=Mesh()
    for y in (11.1,47.2):section(trim,[(y-.25,.22,.22,0,0,0),(y-.17,.29,.29,0,0,0),(y+.17,.29,.29,0,0,0),(y+.25,.22,.22,0,0,0)],12)
    for x in (-.13,.13):trim.tube([(x,57.25,0),(x,57.95,0)],[.09,.07],8)
    if key!='fire':parts['trim']=trim
    # Straight shaft, same elemental material palette as its head; no shape variants.
    rod=np.empty((512,64,3),dtype=np.float32)
    color=np.array((.32,.035,.005) if key=='fire' else (.40,.24,.055))
    for x in range(64):rod[:,x]=color*(.72+.28*abs(math.cos(math.tau*x/64)))
    dds(TEX/f'{key}_shaft.dds',rod)
    metal=np.empty((32,32,3),dtype=np.float32);metal[:]=(.25,.12,.035) if key=='fire' else (.38,.22,.06)
    dds(TEX/f'{key}_trim.dds',metal)
    dump={name:dict(verts=m.verts,tris=m.tris,uv=m.uv) for name,m in parts.items()}
    (STAGE/f'{key}-geometry.json').write_text(json.dumps(dump),encoding='utf-8')
    report[key]=dict(head=headstats,tail=tailstats,triangles=sum(len(m.tris) for m in parts.values()))
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'reference-sculpt.blend'))
(STAGE/'reconstruction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
