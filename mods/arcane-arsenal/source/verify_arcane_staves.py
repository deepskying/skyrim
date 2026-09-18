"""Reimport both views and verify geometry, grip, apertures, shaders and Havok.

These are export checks, not an in-game animation or physics test.
"""
import bpy,sys,json,struct,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
STAGE=ROOT/'build/arcane-staves';DATA=ROOT/'data';ART=ROOT/'art/arcane-staves'
specs=json.loads((ROOT/'source/arcane_staves_catalog.json').read_text(encoding='utf-8'))
names={'AA_StaffBody','AA_StaffEdge'}
reference=NifBlocks(ROOT/'build/staves-reference/staff01.nif')
def snapshot():
    return {o.name:[o.matrix_world@v.co for v in o.data.vertices] for o in bpy.context.scene.objects if o.name in names}
def difference(a,b):
    kd=KDTree(len(b))
    for i,p in enumerate(b):kd.insert(p,i)
    kd.balance();return max(kd.find(p)[2] for p in a)
reports=[]
for spec in specs:
    key=spec['key'];bpy.ops.wm.open_mainfile(filepath=str(ART/(key+'.blend')))
    source=snapshot();assert set(source)==names
    for prefix in ('','1stperson'):
        for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
        path=DATA/'meshes/weapons/arcanearsenal/staves'/(prefix+key+'.nif')
        bpy.ops.import_scene.pynifly(filepath=str(path))
        current=snapshot();assert set(current)==names
        error=max(max(difference(source[n],current[n]),difference(current[n],source[n])) for n in names)
        assert error<.015,(key,prefix,error)
        coords=[p for arr in current.values() for p in arr]
        assert all(math.isfinite(c) for p in coords for c in p)
        assert not any(o.type=='ARMATURE' for o in bpy.context.scene.objects)
        bounds=[(min(p[i] for p in coords),max(p[i] for p in coords)) for i in range(3)]
        assert -72<bounds[1][0]<-60 and 62<bounds[1][1]<78,(key,bounds)
        # Intersect actual triangle edges with palm planes, including long faces.
        palm=[];vertices=[];faces=[];triangles=0;texture_paths=set()
        for o in bpy.context.scene.objects:
            if o.name not in names:continue
            for e in o.data.edges:
                a,b=[o.matrix_world@o.data.vertices[i].co for i in e.vertices]
                for y in (-9,-3,3):
                    if abs(a.y-b.y)>1e-8 and min(a.y,b.y)<=y<=max(a.y,b.y):
                        palm.append(a+(b-a)*((y-a.y)/(b.y-a.y)))
            offset=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices)
            faces.extend(tuple(offset+i for i in face.vertices) for face in o.data.polygons)
            o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
            for tri in o.data.loop_triangles:
                a,b,c=[o.data.vertices[i].co for i in tri.vertices]
                assert (b-a).cross(c-a).length>1e-8,(key,o.name,'degenerate face')
            mat=o.data.materials[0];shader=mat.node_tree.nodes['SkyrimShader:Default']
            label=o.name.removeprefix('AA_Staff')
            expected=spec['power'][1 if label=='Edge' else 0]
            assert abs(shader.inputs['Emission Strength'].default_value-expected)<1e-5
            assert 'SKINNED' not in mat.pyn_shader.Shader_Flags_1
            assert mat.pyn_shader.Shader_Type=='Glow_Shader'
            assert 'OWN_EMIT' in mat.pyn_shader.Shader_Flags_1
            assert 'SPECULAR' not in mat.pyn_shader.Shader_Flags_1
            for slot in ('Diffuse','Normal','Glow'):
                rel=mat['BSShaderTextureSet_'+slot].replace('\\','/');tex=DATA/rel
                assert tex.is_file(),(key,tex)
                blob=tex.read_bytes();assert blob[:4]==b'DDS '
                assert struct.unpack_from('<I',blob,28)[0]>=7,'Missing mipmaps'
                assert blob==(ROOT/'data/textures/weapons/arcanearsenal'/tex.name).read_bytes(),'Changed established geometric texture'
                texture_paths.add(rel)
        assert palm and max(math.hypot(p.x,p.z) for p in palm)<1.5,(key,'palm clearance')
        assert 0<triangles<15000,(key,triangles)
        surface=BVHTree.FromPolygons(vertices,faces)
        def hit(x,y):return surface.ray_cast(Vector((x,y,30)),Vector((0,0,-1)),60)[0] is not None
        if key in ('staffshuttle','stafffold'):
            assert not hit(0,50),'Designed aperture was filled'
            assert hit(-9,48) or hit(-8,48),'Left folded face missing'
        if key=='staffsteps':
            assert hit(0,73) and hit(6,33) and not hit(6,40),'Step silhouette missing'
        n=NifBlocks(path)
        assert b'WeaponStaff' in n.strings and b'Prn' in n.strings
        assert [k for k,b in n.blocks].count('BSInvMarker')==1
        assert [k for k,b in n.blocks].count('BSTriShape')==2
        assert sorted(struct.unpack_from('<I',b)[0] for k,b in n.blocks if k=='BSLightingShaderProperty')==[2,2]
        assert not any('SkinInstance' in k or k=='NiParticleSystem' or k=='NiAlphaProperty' for k,b in n.blocks)
        assert n.blocks[5:7]==reference.blocks[5:7],'Native rigid-body / attachment changed'
        assert n.blocks[4][0]=='bhkListShape'
        blob=n.blocks[4][1];count=struct.unpack_from('<I',blob)[0];assert count==4
        transforms=struct.unpack_from('<4I',blob,4);boxes=[]
        for idx in transforms:
            kind,tf=n.blocks[idx];assert kind=='bhkConvexTransformShape'
            box_idx=struct.unpack_from('<I',tf)[0];kind,box=n.blocks[box_idx];assert kind=='bhkBoxShape'
            center=Vector(struct.unpack_from('<3f',tf,68))*69.99125
            half=Vector(struct.unpack_from('<3f',box,16))*69.99125
            assert all(.1<v<40 for v in half),(key,half)
            boxes.append((center,half))
        assert all(any(all(abs(p[i]-center[i])<half[i]+.002 for i in range(3)) for center,half in boxes) for p in coords),'Collision misses vertices'
        # Confirm PyNifly really imported the native graph into four collision meshes.
        collision_meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('bhkBoxShape')]
        assert len(collision_meshes)==4,(key,[o.name for o in collision_meshes])
        reports.append({'key':key,'view':'first-person' if prefix else 'third-person','max_export_error':error,'triangles':triangles,'bounds':bounds,'textures':sorted(texture_paths),'grip_radius_max':max(math.hypot(p.x,p.z) for p in palm),'collision_boxes':4,'apertures_verified':True})
report={'passed':True,'gameplay_tested':False,'models':reports}
(STAGE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('STAVES_VERIFIED',json.dumps(report,ensure_ascii=False))
