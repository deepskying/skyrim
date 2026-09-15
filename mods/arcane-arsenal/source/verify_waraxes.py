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
SERIES='waraxes'
specs=json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8'))
def snapshot():
    return {o.name:[o.matrix_world@v.co for v in o.data.vertices] for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('AA_Waraxe')}
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
    current=snapshot();assert set(current)==set(source)=={'AA_WaraxeBody','AA_WaraxeEdge'}
    errors={k:max(distance(v,current[k]),distance(current[k],v)) for k,v in source.items()}
    assert max(errors.values())<.03,(key,errors)
    assert not any(o.type=='ARMATURE' for o in bpy.context.scene.objects)
    coords=[p for pts in current.values() for p in pts]
    bounds=[(min(p[i] for p in coords),max(p[i] for p in coords)) for i in range(3)]
    assert -15<bounds[1][0]<-14 and 50<bounds[1][1]<55,(key,bounds)
    # Long grip faces need not have vertices inside the palm. Intersect their
    # edges at three grip sections rather than relying on vertex placement.
    palm=[]
    for o in bpy.context.scene.objects:
        if o.name not in current:continue
        for edge in o.data.edges:
            a,b=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices]
            for y in (-5,0,3):
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
    def hit(x,y):return surface.ray_cast(Vector((x,y,25)),Vector((0,0,-1)),50)[0] is not None
    if key=='waraxered':
        assert hit(-24,36) and not hit(-10,39) and hit(8,38), 'Crescent, triangular aperture or stepped rear lost'
    elif key=='waraxegreen':
        assert hit(-25,36) and not hit(-13,44), 'Green crescent or upper window missing'
        head=[p for p in coords if -18<p.x<-5 and 29<p.y<40]
        assert max(p.z for p in head)>2.5 and min(p.z for p in head)<-2.5, 'Woven arms flattened'
        assert hit(-19,48), 'Upper arch disconnected from cutting blade'
    elif key=='waraxeblue':
        assert hit(-22,39) and hit(-14,24) and not hit(-9,31), 'Deep open bay or cutting edge missing'
    elif key=='waraxepurple':
        assert not hit(-10,37) and not hit(-10,22), 'Open wheel aperture or bottom gap filled'
        assert hit(-10,50) and hit(3,35) and hit(-26,37), 'Continuous ring or broad cutting face missing'
    assert all(hit(0,y) for y in (-5,0,3,12,20,27,33)), 'Haft or socket discontinuity'
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
    assert b'AAWaraxeDust0' in n.strings
    assert b'WeaponAxe' in n.strings and b'Prn' in n.strings
    assert len([k for k,b in n.blocks if k=='BSInvMarker'])==1
    assert len([k for k,b in n.blocks if k=='bhkRigidBody'])==1
    assert len([k for k,b in n.blocks if k=='bhkBoxShape'])==3
    reference=NifBlocks(ROOT/'build/ironwaraxe-reference.nif')
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
        assert all(.1<h<(90 if SERIES in ('scythes','scythes2') else 65) for h in half),(key,half)
        collision.append((rot.inverted(),center,half))
    for p in coords:
        assert any(all(abs((inv@(p-center))[i])<=half[i]+.001 for i in range(3)) for inv,center,half in collision),(key,'Collision misses geometry',p)
    assert not any(name in n.strings for name in (b'Scb',b'WarAxe01:0',b'WarAxeBloodFX01',b'WarAxeBloodLighting01'))
    assert not any('SkinInstance' in k for k,b in n.blocks)
    assert len([k for k,b in n.blocks if k=='NiParticleSystem'])==6
    reports.append({'key':key,'passed':True,'source_export_max_error':max(errors.values()),'bounds':bounds,'palm_clearance':True,'rigid_mesh':True,'attachment':'WeaponAxe'})
baseline=ROOT/'build/before-0.41.0/data'
old={p.relative_to(baseline).as_posix():p for p in baseline.rglob('*') if p.is_file()}
now={p.relative_to(ROOT/'data').as_posix():p for p in (ROOT/'data').rglob('*') if p.is_file()}
assert set(old)<=set(now)
assert set(now)-set(old)=={'meshes/weapons/arcanearsenal/'+s['key']+'.nif' for s in specs}
changed=[p for p in old if old[p].read_bytes()!=now[p].read_bytes()]
assert changed==['ArcaneArsenal.esp'],changed
report={'version':'0.41.0','passed':True,'weapons':reports,'unchanged_old_runtime_files':len(old)-len(changed),'changed_old_runtime_files':changed,'gameplay_tested':False}
(ROOT/'build'/(SERIES+'-verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
