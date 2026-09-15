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
SERIES='daggers2'
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
    if key=='dagger2red':
        assert hit(-3.8,17) and hit(1.5,25) and hit(-2.2,33), 'Lightning elbows missing'
        assert not hit(3,18) and not hit(-4,25), 'Z silhouette filled in'
    elif key=='dagger2green':
        assert all(not hit(x,y) for x,y in ((.5,17),(.5,25),(.8,34))), 'Three leaf apertures filled'
        assert hit(-3,25) and hit(3,25) and hit(.5,21.5) and hit(.5,29.2), 'Leaf backbone or diagonal ribs missing'
    elif key=='dagger2blue':
        assert hit(-1,42) and hit(3,15) and hit(1.5,26), 'Blade terraces missing'
        assert not hit(3,26) and not hit(1.5,35), 'Three-step silhouette lost'
        assert not hit(0,6.8) and not hit(2.5,6.8) and hit(3.7,6.8), 'Rectangular guard opening missing'
    elif key=='dagger2purple':
        assert hit(-3.5,22) and not hit(1,22) and hit(2.5,29.3) and hit(2.5,14.4), 'Open crescent silhouette missing'
        assert not hit(2.8,8) and hit(4.3,7.7), 'Diamond guard aperture missing'
    if key=='dagger2blue':
        assert hit(0,5) and hit(3.7,7) and hit(0,9.2), 'Guard does not bridge grip and blade'
    else:
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
baseline=ROOT/'build/before-0.38.0/data'
old={p.relative_to(baseline).as_posix():p for p in baseline.rglob('*') if p.is_file()}
now={p.relative_to(ROOT/'data').as_posix():p for p in (ROOT/'data').rglob('*') if p.is_file()}
assert set(old)<=set(now)
assert set(now)-set(old)=={'meshes/weapons/arcanearsenal/'+s['key']+'.nif' for s in specs}
changed=[p for p in old if old[p].read_bytes()!=now[p].read_bytes()]
assert changed==['ArcaneArsenal.esp'],changed
report={'version':'0.38.0','passed':True,'weapons':reports,'unchanged_old_runtime_files':len(old)-len(changed),'changed_old_runtime_files':changed,'gameplay_tested':False}
(ROOT/'build'/(SERIES+'-verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
