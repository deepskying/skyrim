"""Build four approved shield silhouettes; run in portable Blender.

Original geometry, vanilla SHIELD attachment/physics, current collection materials.
The final NIF graft retains the native inventory, attachment and rigid body graph.
"""
import bpy, sys, json, math, struct, copy
from pathlib import Path
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
from apply_approved_sword_materials import shapes
import mesh_builder as mb
BASE_MAT=mb.base_mat.copy()
CATALOG=json.loads((ROOT/'source/shields_catalog.json').read_text('utf-8'))
OUT=ROOT/'data/meshes/armor/arcanearsenal';OUT.mkdir(parents=True,exist_ok=True)
ART=ROOT/'art/shields';ART.mkdir(parents=True,exist_ok=True)

def hull2(points):
    pts=sorted(set((round(x,5),round(y,5)) for x,y in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lo=[];hi=[]
    for p in pts:
        while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]

def final_nif(raw_path,out,color,points):
    n=NifBlocks(ROOT/'build/shield-reference-elvenshield.nif')
    exported=NifBlocks(raw_path)
    n.blocks=n.blocks[:7]  # native root, inventory marker, BSX, Prn, hull, body, collision
    ref=NifBlocks(ROOT/'data/meshes/weapons/arcanearsenal'/('greatsword3'+color+'.nif'))
    refs=shapes(ref);children=[]
    for name,(si,ti) in shapes(exported).items():
        source=next(b for k,b in exported.blocks if k=='BSTriShape' and exported.strings[struct.unpack_from('<I',b)[0]].decode()==name)
        blob=bytearray(source)
        assert struct.unpack_from('<I',blob,4)[0]==0
        assert struct.unpack_from('<i',blob,8)[0]==-1
        assert struct.unpack_from('<i',blob,88)[0]==-1  # rigid, unskinned shield
        idx=len(n.blocks);children.append(idx)
        struct.pack_into('<I',blob,0,n.string(name))
        struct.pack_into('<ii',blob,92,idx+1,-1)
        n.blocks.append(('BSTriShape',bytes(blob)))
        part=name.removeprefix('AA_Shield')
        ri,rt=refs['AA_Greatsword'+('Edge' if part=='Edge' else 'Body')]
        shader=bytearray(ref.blocks[ri][1]);assert len(shader)==100
        struct.pack_into('<iIi',shader,4,-1,0,-1)
        struct.pack_into('<I',shader,40,idx+2)
        # Shield UVs are already square in world space; sword aspect compensation is unnecessary.
        struct.pack_into('<2f',shader,32,1,1)
        if part in ('Metal','Grip'):
            struct.pack_into('<3f',shader,44,0,0,0);struct.pack_into('<f',shader,56,0)
            struct.pack_into('<f',shader,72,45 if part=='Metal' else 8)
            struct.pack_into('<3f',shader,76,*((.28,.24,.20) if part=='Metal' else (.06,.04,.03)))
            struct.pack_into('<f',shader,88,.55 if part=='Metal' else .1)
        n.blocks.append(('BSLightingShaderProperty',bytes(shader)))
        if part in ('Metal','Grip'):
            tex=['textures\\armor\\arcanearsenal\\shield_'+part.lower()+'_d.dds',
                 'textures\\weapons\\arcanearsenal\\aa_red_n.dds',
                 'textures\\weapons\\arcanearsenal\\aa_red_g.dds']+['']*6
            t=struct.pack('<I',9)+b''.join(struct.pack('<I',len(s.encode()))+s.encode() for s in tex)
            n.blocks.append(('BSShaderTextureSet',t))
        else:n.blocks.append(ref.blocks[rt])
    # Native NiNode layout: 3 extra data links, then AVObject, then child array.
    kind,root=n.blocks[0];assert len(root)==96
    root=bytearray(root[:84]);struct.pack_into('<I',root,0,n.string(out.stem))
    root+=struct.pack('<I',len(children))+struct.pack('<'+'I'*len(children),*children)+struct.pack('<I',0)
    n.blocks[0]=(kind,bytes(root))
    # Convex prism encloses the complete visual mesh, including rear grip.
    hull=hull2([(p[0],p[1]) for p in points]);scale=69.99125
    zlo=min(p[2] for p in points)-.15;zhi=max(p[2] for p in points)+.15
    vertices=[(x/scale,y/scale,z/scale,0) for z in (zlo,zhi) for x,y in hull]
    planes=[(0,0,-1,zlo/scale),(0,0,1,-zhi/scale)]
    for a,b in zip(hull,hull[1:]+hull[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);nx,ny=dy/length,-dx/length
        planes.append((nx,ny,0,-(nx*a[0]+ny*a[1])/scale))
    kind,old=n.blocks[4]
    n.blocks[4]=(kind,old[:32]+struct.pack('<I',len(vertices))+b''.join(struct.pack('<4f',*v) for v in vertices)+struct.pack('<I',len(planes))+b''.join(struct.pack('<4f',*p) for p in planes))
    n.save(out)
    return len(vertices),len(planes)

def build(spec):
    key=spec['key'];color=spec['color']
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mats=[]
    for label in ('Body','Edge','Metal','Grip'):
        m=BASE_MAT.copy();m.name='Shield'+label;mats.append(m)
    objs=[]
    def solid(vertices,faces,mat=0,bevel=.15):
        mesh=bpy.data.meshes.new('ShieldPart');mesh.from_pydata([(x,y,-z) for x,y,z in vertices],[],faces);mesh.update()
        obj=bpy.data.objects.new('ShieldPart',mesh);bpy.context.collection.objects.link(obj)
        for m in mats:mesh.materials.append(m)
        for p in mesh.polygons:p.material_index=mat
        bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        if bevel:
            mod=obj.modifiers.new('Edge chamfer','BEVEL');mod.width=bevel;mod.segments=1;mod.material=mat
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False);objs.append(obj);return obj
    def slab(poly,z=4,depth=1,mat=0,bevel=.15):
        n=len(poly);verts=[(x,y,h) for h in (z-depth/2,z+depth/2) for x,y in poly]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        return solid(verts,faces,mat,bevel)
    def rail(points,width=1,z=5,depth=.8,mat=2):
        closed=points[0]==points[-1];pts=[Vector(p) for p in (points[:-1] if closed else points)]
        vertices=[];faces=[]
        for i,p in enumerate(pts):
            prev=pts[(i-1)%len(pts)] if closed or i else p
            nxt=pts[(i+1)%len(pts)] if closed or i<len(pts)-1 else p
            direction=(nxt-prev).normalized();side=Vector((-direction.y,direction.x))*width/2
            vertices.extend([(p.x+side.x,p.y+side.y,z-depth/2),(p.x-side.x,p.y-side.y,z-depth/2),(p.x-side.x,p.y-side.y,z+depth/2),(p.x+side.x,p.y+side.y,z+depth/2)])
        for i in range(len(pts) if closed else len(pts)-1):
            a=i*4;b=((i+1)%len(pts))*4
            faces.extend((a+j,a+(j+1)%4,b+(j+1)%4,b+j) for j in range(4))
        if not closed:faces.extend([(3,2,1,0),tuple(range(len(vertices)-4,len(vertices)))])
        return solid(vertices,faces,mat,min(.1,width/5))
    def rim(poly,width=1,z=4,mat=2):rail(poly+[poly[0]],width,z,.85,mat)
    def circle(r,c=(0,-5),steps=64):return [(c[0]+r*math.cos(i*math.tau/steps),c[1]+r*math.sin(i*math.tau/steps)) for i in range(steps)]
    def jewel(cx,cy,w,h,z=7):
        poly=[(cx,cy+h),(cx-w,cy),(cx,cy-h),(cx+w,cy)]
        slab(poly,z-.7,1,2);solid([(x,y,z) for x,y in poly]+[(cx,cy,z+1.7)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],0,.03)
    if color=='red':
        outer=circle(26);slab(outer,2.1,2.2,2);slab(circle(24.8),3.4,1.1);rim(outer,1.3,4)
        for j in range(3):
            phi=j*math.tau/3
            # A broad swept crescent on a continuous protective backing.
            pts=[]
            for i in range(33):
                t=i/32;a=phi+t*2.7;r=24.7-10.5*t;pts.append((r*math.cos(a),-5+r*math.sin(a)))
            for i in range(32,-1,-1):
                t=i/32;a=phi+t*2.7;r=8+6.2*(1-t);pts.append((r*math.cos(a),-5+r*math.sin(a)))
            slab(pts,4.3+j*.15,2.1);rim(pts,.55,5.5+j*.15);rail(pts[:33],.18,6+j*.15,.25,1)
        slab(circle(8),5.2,2,2);rim(circle(8),.4,6.3,1)
        slab(circle(6.7),5.8,2,2);jewel(0,20,2.2,3.5,6.5);jewel(0,-30,2.2,3.2,6.5)
    elif color=='green':
        outer=[(2,29),(-18,16),(-23,3),(-21,-12),(-12,-28),(0,-42),(16,-18),(21,9),(11,13)]
        slab(outer,2,2.2,2);rim(outer,1,4)
        panels=[[(1,26),(-17,14),(-20,2),(-17,-10),(-7,1)],[(3,25),(-6,-1),(0,-38),(15,-17),(18,8),(10,11)], [(-18,-12),(-8,-1),(-1,-37),(-10,-26)]]
        for i,p in enumerate(panels):slab(p,4.1+i*.25,1.5);rim(p,.5,5.25+i*.25)
        spine=[(2,27),(-6,0),(0,-39)];rail(spine,1.5,5.7);rail(spine,.2,6.25,.3,1)
        rail([(-19,-10),(-6,0),(18,9)],1,5.5);jewel(-5,1,2.4,4.5,6)
    elif color=='blue':
        outer=[(-22,24),(-12,20),(-12,25),(-5,25),(-5,30),(5,30),(5,25),(12,25),(12,20),(22,24),(22,-29),(0,-42),(-22,-29)]
        slab(outer,2,2.7,2);rim(outer,1.3,4.1)
        center=[(0,29),(-10,22),(-10,-29),(0,-38),(10,-29),(10,22)]
        solid([(x,y,4) for x,y in center]+[(0,23,7.2),(0,-29,7.2)],[(0,1,6),(1,2,7,6),(2,3,7),(3,4,7),(4,5,6,7),(5,0,6),(5,4,3,2,1,0)],0,.15)
        for sign in (-1,1):
            p=[(sign*12,18),(sign*21,21),(sign*21,-28),(sign*12,-33)]
            slab(p,4,1.5)
            rail([(sign*11,-30),(sign*11,14),(sign*18,18),(sign*18,22)],1.8,5.6)
            rail([(sign*10.2,-29),(sign*10.2,15),(sign*18,19)],.22,6.4,.3,1)
            for y in (5,-6,-17):rail([(sign*12,y-4),(sign*19,y)],1.5,5.5)
        rail([(-20,-29),(0,-40),(20,-29)],1.4,5.6);rail([(0,-35),(0,26)],.2,7.5,.3,1)
    else:
        outer=[(0,30),(-24,7),(-23,-14),(0,-42),(23,-14),(24,7)]
        slab(outer,2,2.3,2);slab([(x*.95,-6+(y+6)*.95) for x,y in outer],3.4,1.1);rim(outer,1.2,4.3)
        panels=[[(0,27),(-21,6),(-8,-3)],[(0,27),(8,-3),(21,6)], [(-21,3),(-21,-13),(0,-39),(-8,-9)],[(21,3),(8,-9),(0,-39),(21,-13)]]
        for p in panels:slab(p,4.4,1.6);rim(p,.65,5.45)
        ring=[(0,15),(-16,-6),(0,-27),(16,-6)];rim(ring,.7,5.5);rim([(x*.96,-6+(y+6)*.96) for x,y in outer],.2,5,1)
        rim(circle(11,(0,-6),48),.32,5.6)
        rail([(0,25),(0,-37)],.7,5.8);rail([(-20,-6),(20,-6)],.7,5.8)
        jewel(0,-6,6,9,6)
        for x,y in [(0,27),(-22,5),(22,5),(-20,-15),(20,-15)]:jewel(x,y,1.7,3,5.8)
    # Rear grip matches the vanilla shield's attachment origin and lies behind the slab.
    for x in (-5.5,5.5):slab([(x-1,-10),(x+1,-10),(x+1,1),(x-1,1)],-.3,3,2)
    solid([(-6,-6,-2.4),(6,-6,-2.4),(6,-3,-2.4),(-6,-3,-2.4),(-6,-6,-4.5),(6,-6,-4.5),(6,-3,-4.5),(-6,-3,-4.5)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],3,.4)
    for x in range(-5,6,2):rail([(x,-5.9),(x,-3.1)],.23,-4.55,.15,2)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.00001);bpy.ops.mesh.dissolve_degenerate(threshold=.00001);bpy.ops.mesh.quads_convert_to_tris();bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
    exported=[o for o in bpy.context.selected_objects if o.type=='MESH'];assert len(exported)==4
    points=[]
    for o in exported:
        label=o.data.materials[0].name.removeprefix('Shield').split('.')[0];o.name='AA_Shield'+label;o['pynNodeName']=o.name
        o['pynBlockName']='BSTriShape';o['PYN_GAME']='SKYRIMSE';o['PYN_BLENDER_XF']=False
        uv=o.data.uv_layers.new(name='UVMap')
        for p in o.data.polygons:
            for li in p.loop_indices:
                v=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x/55+.5,v.y/55+.6)
        points.extend([tuple(v.co) for v in o.data.vertices])
    raw=ROOT/'build'/(key+'-raw.nif')
    bpy.ops.export_scene.pynifly(filepath=str(raw),target_game='SKYRIMSE',intuit_defaults=False,blender_xf=False,export_modifiers=False,export_animations=False)
    out=OUT/(key+'.nif');hv,hp=final_nif(raw,out,color,points)
    report=dict(key=key,name=spec['name'],triangles=sum(len(o.data.polygons) for o in exported),shapes=4,
                bounds=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],collision_vertices=hv,collision_planes=hp,attachment='SHIELD',gameplay_tested=False)
    (ROOT/'build'/(key+'-model.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SHIELD_BUILT',json.dumps(report,ensure_ascii=True),flush=True)

for spec in CATALOG:build(spec)
