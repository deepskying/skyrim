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
SERIES='scythes2' if '--scythes2' in sys.argv else 'scythes' if '--scythes' in sys.argv else 'battleaxes3' if '--battleaxes3' in sys.argv else 'battleaxes2' if '--battleaxes2' in sys.argv else 'battleaxes'
specs=json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8'))
def snapshot():
    return {o.name:[o.matrix_world@v.co for v in o.data.vertices] for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('AA_Battleaxe')}
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
    current=snapshot();assert set(current)==set(source)=={'AA_BattleaxeBody','AA_BattleaxeEdge'}
    errors={k:max(distance(v,current[k]),distance(current[k],v)) for k,v in source.items()}
    assert max(errors.values())<.03,(key,errors)
    assert not any(o.type=='ARMATURE' for o in bpy.context.scene.objects)
    coords=[p for pts in current.values() for p in pts]
    bounds=[(min(p[i] for p in coords),max(p[i] for p in coords)) for i in range(3)]
    if SERIES in ('scythes','scythes2'):
        assert -55<bounds[1][0]<-48 and 108<bounds[1][1]<114 and -72<bounds[0][0]<-60,(key,bounds)
    else:
        assert -49<bounds[1][0]<-40 and 64<bounds[1][1]<74,(key,bounds)
    # Long grip faces need not have vertices inside the palm. Intersect their
    # edges at three grip sections rather than relying on vertex placement.
    palm=[]
    for o in bpy.context.scene.objects:
        if o.name not in current:continue
        for edge in o.data.edges:
            a,b=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices]
            for y in (-24,-10,8):
                if abs(a.y-b.y)>1e-6 and min(a.y,b.y)<=y<=max(a.y,b.y):
                    p=a+(b-a)*((y-a.y)/(b.y-a.y))
                    if abs(p.x)<4:palm.append(p)
    assert palm and max(abs(p.x) for p in palm)<1.5 and max(abs(p.z) for p in palm)<1.5,(key,'palm clearance')
    # Probe actual exported surfaces: neither the spindle nor the aperture may
    # be filled by a triangulation error, and the blade must remain connected.
    vertices=[];faces=[]
    for o in bpy.context.scene.objects:
        if o.name not in current:continue
        start=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices)
        faces.extend(tuple(start+i for i in face.vertices) for face in o.data.polygons)
    surface=BVHTree.FromPolygons(vertices,faces)
    def hit(x,y):return surface.ray_cast(Vector((x,y,10)),Vector((0,0,-1)),20)[0] is not None
    if key=='battleaxered':
        assert not hit(-16,52) and hit(-24,55) and hit(0,54), 'Triangular window or leading blade missing'
    elif key=='battleaxegreen':
        assert hit(-23,56) and hit(23,40) and not hit(-12,49) and not hit(12,33), 'Staggered blades or open slots missing'
    elif key=='battleaxeblue':
        assert not hit(10,50) and hit(26,50) and hit(0,50), 'Gate window or blade missing'
    elif key=='battleaxepurple':
        assert not hit(0,49) and hit(-22,50) and hit(20,48) and hit(0,28), 'Diamond aperture, wings or haft missing'
    if key=='battleaxe2red':
        assert hit(16,54) and hit(19,61) and hit(10,36), 'Solid cleaver blade missing'
    elif key=='battleaxe2green':
        assert hit(-22,46) and hit(-12,48) and not hit(-16,46), 'Falling talons or channel missing'
    elif key=='battleaxe2blue':
        assert hit(12,54) and hit(12,41) and not hit(12,47.5), 'Echelon blades or inter-plate gap missing'
    elif key=='battleaxe2purple':
        assert not hit(6,48) and not hit(22,65) and hit(-16,48) and hit(27,43), 'Open ring aperture, break or rim missing'
    if key=='battleaxe3red':
        assert hit(-24,59) and hit(-22,44) and hit(-18,31) and not hit(-23,51) and not hit(-21,37), 'Three chisel courses or separating notches missing'
    elif key=='battleaxe3green':
        assert hit(-22,60) and hit(-6,34) and not hit(-12,35) and not hit(-4,49), 'S blade, lower hook or teardrop opening missing'
    elif key=='battleaxe3blue':
        assert hit(-25,55) and hit(25,50) and hit(0,56) and not hit(-8,45) and not hit(8,45), 'Crossbar or broad cutting fins missing'
    elif key=='battleaxe3purple':
        assert not hit(17,61) and not hit(26,47) and hit(8,56) and hit(16,51) and hit(17,34), 'Fan blades or two narrow windows missing'
    if key=='scythered':
        assert not hit(-10,95) and hit(-35,97) and hit(-64,65), 'Red window or scythe edge missing'
    elif key=='scythegreen':
        assert not hit(-40,90) and hit(-50,90) and hit(-42,81) and not hit(-30,65), 'Double crescent slit or blades missing'
    elif key=='scytheblue':
        assert not hit(-12,99) and not hit(-34,99) and hit(-30,103) and hit(-60,87), 'Cantilever bays or hooked edge missing'
    elif key=='scythepurple':
        assert hit(-48,93) and hit(-40,84) and hit(-27,79) and not hit(-38,92) and not hit(-29,84), 'Three blades or separating slots missing'
    if key=='scythe2red':
        assert not hit(-7,97) and hit(-45,96) and hit(-40,85) and not hit(-34,85), 'Diamond hole or inner fangs missing'
    elif key=='scythe2green':
        assert not hit(-30,87) and hit(-58,87) and hit(-24,69) and not hit(-9,60), 'Spiral aperture, return horn or open mouth missing'
    elif key=='scythe2blue':
        probes=[hit(-38,101),hit(-63,64),hit(-17,91),hit(-17,86)]
        assert probes==[True,True,False,True], ('High elbow, long blade or open triangular brace missing',probes)
    elif key=='scythe2purple':
        assert not hit(-32,83) and hit(-57,81) and hit(-39,55) and not hit(-22,62) and not hit(0,-49), 'Ring aperture, gap, lower blade or fork missing'
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
    assert b'AABattleaxeDust0' in n.strings
    assert b'WeaponBack' in n.strings and b'Prn' in n.strings
    assert len([k for k,b in n.blocks if k=='BSInvMarker'])==1
    assert len([k for k,b in n.blocks if k=='bhkRigidBody'])==1
    assert len([k for k,b in n.blocks if k=='bhkBoxShape'])==2
    reference=NifBlocks(ROOT/'build/ironbattleaxe-reference.nif')
    for i in (8,9,10):
        assert n.blocks[i]==reference.blocks[i],('Vanilla Havok metadata changed',i)
    collision=[]
    for i in (4,6):
        box=n.blocks[i][1];old=reference.blocks[i][1]
        assert box[:16]==old[:16] and box[28:]==old[28:]
        tf=n.blocks[i+1][1];original=reference.blocks[i+1][1]
        assert tf[:68]==original[:68] and tf[80:]==original[80:]
        raw=struct.unpack_from('<16f',tf,20)
        rot=Matrix([[raw[c*4+r] for c in range(3)] for r in range(3)])
        center=Vector(struct.unpack_from('<3f',tf,68))*69.99125
        half=Vector(struct.unpack_from('<3f',box,16))*69.99125
        assert all(.1<h<(90 if SERIES in ('scythes','scythes2') else 65) for h in half),(key,half)
        collision.append((rot.inverted(),center,half))
    for p in coords:
        assert any(all(abs((inv@(p-center))[i])<=half[i]+.001 for i in range(3)) for inv,center,half in collision),(key,'Collision misses geometry',p)
    assert not any(name in n.strings for name in (b'Scb',b'BattleAxe01:0',b'BloodFX01',b'BloodLighting'))
    assert not any('SkinInstance' in k for k,b in n.blocks)
    assert len([k for k,b in n.blocks if k=='NiParticleSystem'])==6
    reports.append({'key':key,'passed':True,'source_export_max_error':max(errors.values()),'bounds':bounds,'palm_clearance':True,'rigid_mesh':True,'attachment':'WeaponBack'})
baseline=ROOT/('build/before-0.36.0/data' if SERIES=='scythes2' else 'build/before-0.35.0/data' if SERIES=='scythes' else 'build/before-0.34.0/data' if SERIES=='battleaxes3' else 'build/before-0.33.0/data' if SERIES=='battleaxes2' else 'build/before-0.32.0/data')
old={p.relative_to(baseline).as_posix():p for p in baseline.rglob('*') if p.is_file()}
now={p.relative_to(ROOT/'data').as_posix():p for p in (ROOT/'data').rglob('*') if p.is_file()}
assert set(old)<=set(now)
assert set(now)-set(old)=={'meshes/weapons/arcanearsenal/'+s['key']+'.nif' for s in specs}
changed=[p for p in old if old[p].read_bytes()!=now[p].read_bytes()]
assert changed==['ArcaneArsenal.esp'],changed
report={'version':('0.36.0' if SERIES=='scythes2' else '0.35.0' if SERIES=='scythes' else '0.34.0' if SERIES=='battleaxes3' else '0.33.0' if SERIES=='battleaxes2' else '0.32.0'),'passed':True,'weapons':reports,'unchanged_old_runtime_files':len(old)-len(changed),'changed_old_runtime_files':changed,'gameplay_tested':False}
(ROOT/'build'/(SERIES+'-verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
