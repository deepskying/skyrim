"""Independently reimport exported rigid meshes and compare source coordinates.

Includes palm clearance, attachment metadata, emission, collision bounds and
old-release scope checks. These do not replace an in-game animation test.
"""
from pathlib import Path
import sys,json,struct,math,hashlib
import bpy
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
SERIES='daggers3'
specs=json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8'))
def snapshot():
    return {o.name:[o.matrix_world@v.co for v in o.data.vertices] for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('AA_Dagger')}
def distance(a,b):
    kd=KDTree(len(b))
    for i,p in enumerate(b):kd.insert(p,i)
    kd.balance();return max(kd.find(p)[2] for p in a)
reports=[]
for spec in specs:
    key=spec['key'];bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art'/(key+'.blend')))
    source=snapshot()
    for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
    path=ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif')
    bpy.ops.import_scene.pynifly(filepath=str(path))
    current=snapshot();assert set(current)==set(source)=={'AA_DaggerBody','AA_DaggerEdge'}
    errors={k:max(distance(v,current[k]),distance(current[k],v)) for k,v in source.items()}
    assert max(errors.values())<.03,(key,errors)
    assert not any(o.type=='ARMATURE' for o in bpy.context.scene.objects)
    coords=[p for pts in current.values() for p in pts]
    bounds=[(min(p[i] for p in coords),max(p[i] for p in coords)) for i in range(3)]
    assert -15<bounds[1][0]<-10 and 42<bounds[1][1]<47,(key,bounds)
    # Long grip faces need not have vertices inside the palm. Intersect their
    # edges at three grip sections rather than relying on vertex placement.
    palm=[]
    for o in bpy.context.scene.objects:
        if o.name not in current:continue
        for edge in o.data.edges:
            a,b=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices]
            for y in (-4,0,2):
                if abs(a.y-b.y)>1e-6 and min(a.y,b.y)<=y<=max(a.y,b.y):
                    p=a+(b-a)*((y-a.y)/(b.y-a.y))
                    if abs(p.x)<4:palm.append(p)
    assert palm and max(abs(p.x) for p in palm)<1.4 and max(abs(p.z) for p in palm)<1.4,(key,'palm clearance')
    # Probe actual exported surfaces: neither the spindle nor the aperture may
    # be filled by a triangulation error, and the blade must remain connected.
    vertices=[];faces=[]
    for o in bpy.context.scene.objects:
        if o.name not in current:continue
        start=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices)
        faces.extend(tuple(start+i for i in face.vertices) for face in o.data.polygons)
    surface=BVHTree.FromPolygons(vertices,faces)
    def hit(x,y):return surface.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),20)[0] is not None
    if key=='dagger3red':
        assert hit(-6,30) and hit(1.5,39) and hit(6.5,11), 'Offset blade shoulder or connected counterweight missing'
        assert not hit(-5,17) and hit(4,8.2), 'Eccentric root or counterweight strut missing'
    elif key=='dagger3green':
        assert all(not hit(0,y) for y in (15,27,39)), 'Three braid apertures filled'
        assert all(hit(0,y) for y in (21,33)), 'Interlaced crossings missing'
        # A real over-under crossing has four separate surface intersections.
        # Two flat intersecting silhouettes would only produce two.
        for y in (21,33):
            zs=[];start_z=8
            for i in range(8):
                p=surface.ray_cast(Vector((0,y,start_z)),Vector((0,0,-1)),20)[0]
                if p is None:break
                zs.append(p.z);start_z=p.z-.01
            assert len(zs)==4 and zs[1]-zs[2]>.2, ('No physical over-under separation',y,zs)
        assert not hit(0,-10), 'Open pommel filled'
    elif key=='dagger3blue':
        assert hit(-3,42) and hit(1.8,37) and not hit(2,42), 'Unequal double tips missing'
        assert all(not hit(0,y) for y in (16,25,35,41)), 'Fork must remain open to the top'
        assert hit(0,12) and hit(-2.4,26) and hit(2.4,26), 'Fork base or prong missing'
    elif key=='dagger3purple':
        # The long blade turns its widest face from X into Z at mid-length.
        lower=[p for p in coords if 12.5<p.y<13.5]
        middle=[p for p in coords if 24.5<p.y<25.5]
        assert lower and middle
        assert max(abs(p.x) for p in lower)>1.7
        assert max(abs(p.z) for p in middle)>2.3 and max(abs(p.x) for p in middle)<1.5, 'Blade is flat rather than twisted'
    assert all(hit(0,y) for y in (5,7,8.5,9)), 'Blade root is disconnected'
    for o in bpy.context.scene.objects:
        if o.name not in current:continue
        o.data.calc_loop_triangles()
        for tri in o.data.loop_triangles:
            a,b,c=[o.data.vertices[i].co for i in tri.vertices]
            assert (b-a).cross(c-a).length>1e-7,(key,'degenerate face')
        mat=o.data.materials[0];node=mat.node_tree.nodes['SkyrimShader:Default']
        i=0 if o.name.endswith('Body') else 1
        assert abs(node.inputs['Emission Strength'].default_value-spec['power'][i])<1e-5
        assert 'SKINNED' not in mat.pyn_shader.Shader_Flags_1
        assert 'OWN_EMIT' in mat.pyn_shader.Shader_Flags_1
        assert mat.pyn_shader.Shader_Type=='Glow_Shader'
        for slot in ('Diffuse','Normal','Glow'):
            relative=mat['BSShaderTextureSet_'+slot].replace('\\','/')
            assert (ROOT/'data'/relative).is_file()
    n=NifBlocks(path)
    assert not any(b'AAAriesDust' in name for name in n.strings)
    assert b'AADaggerDust0' in n.strings
    assert b'WeaponDagger' in n.strings and b'Prn' in n.strings
    assert len([k for k,b in n.blocks if k=='BSInvMarker'])==1
    assert len([k for k,b in n.blocks if k=='bhkRigidBody'])==1
    assert len([k for k,b in n.blocks if k=='bhkBoxShape'])==3
    reference=NifBlocks(ROOT/'build/irondagger-reference.nif')
    for i in (10,11,12):
        assert n.blocks[i]==reference.blocks[i],('Vanilla Havok metadata changed',i)
    collision=[]
    for i in (4,6,8):
        box=n.blocks[i][1];old=reference.blocks[i][1]
        assert box[:16]==old[:16] and box[28:]==old[28:]
        tf=n.blocks[i+1][1];original=reference.blocks[i+1][1]
        assert tf[:68]==original[:68] and tf[80:]==original[80:]
        raw=struct.unpack_from('<16f',tf,20)
        rot=Matrix([[raw[c*4+r] for c in range(3)] for r in range(3)])
        center=Vector(struct.unpack_from('<3f',tf,68))*69.99125
        half=Vector(struct.unpack_from('<3f',box,16))*69.99125
        assert all(.1<h<45 for h in half),(key,half)
        collision.append((rot.inverted(),center,half))
    for p in coords:
        assert any(all(abs((inv@(p-center))[i])<=half[i]+.001 for i in range(3)) for inv,center,half in collision),(key,'Collision misses geometry',p)
    assert not any(name in n.strings for name in (b'Scb',b'IronDagger01:0',b'DaggerBloodFX',b'DaggerBloodLighting01'))
    assert not any('SkinInstance' in k for k,b in n.blocks)
    assert len([k for k,b in n.blocks if k=='NiParticleSystem'])==6
    reports.append({'key':key,'passed':True,'source_export_max_error':max(errors.values()),'bounds':bounds,'palm_clearance':True,'rigid_mesh':True,'attachment':'WeaponDagger'})
baseline=ROOT/'build/before-0.39.0/data'
old={p.relative_to(baseline).as_posix():p for p in baseline.rglob('*') if p.is_file()}
now={p.relative_to(ROOT/'data').as_posix():p for p in (ROOT/'data').rglob('*') if p.is_file()}
assert set(old)<=set(now)
assert set(now)-set(old)=={'meshes/weapons/arcanearsenal/'+s['key']+'.nif' for s in specs}
changed=[p for p in old if old[p].read_bytes()!=now[p].read_bytes()]
assert changed==['ArcaneArsenal.esp'],changed
report={'version':'0.39.0','passed':True,'weapons':reports,'unchanged_old_runtime_files':len(old)-len(changed),'changed_old_runtime_files':changed,'gameplay_tested':False}
(ROOT/'build'/(SERIES+'-verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
