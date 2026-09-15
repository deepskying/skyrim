"""Build model-only staves: editable Blender files and standalone SSE NIFs.

Run prepare_staff_reference.py in system Python, then this script in Blender.
Never edits the live catalog, plugin, existing runtime files or MO2 installation.
"""
import sys, json, math, struct, shutil
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from nif_blocks import NifBlocks
from staves_geometry import build

ART=ROOT/'art/staves-geometric'
STAGE=ROOT/'build/staves-geometric'
DATA=STAGE/'Data'
MESH=DATA/'meshes/weapons/arcanearsenal/staves'
TEX=DATA/'textures/weapons/arcanearsenal/staves'
for folder in (ART,STAGE,MESH,TEX):folder.mkdir(parents=True,exist_ok=True)
specs=json.loads((ROOT/'source/staves_catalog.json').read_text(encoding='utf-8'))
if '--' in sys.argv:
    keys=sys.argv[sys.argv.index('--')+1:]
    if keys:specs=[s for s in specs if s['key'] in keys]

for spec in specs:
    key=spec['key']
    # Known working Skyrim material group; only the shader template is reused.
    bpy.ops.wm.open_mainfile(filepath=str(ROOT.parents[1]/'reference/bow-tools/validation/ironbow-textured-check.blend'))
    template=bpy.data.objects['Bow_Ironmesh:0'].data.materials[0]
    materials={}
    for i,label in enumerate(('Body','Edge')):
        mat=template.copy();mat.name=key+'_'+label
        shader=mat.node_tree.nodes['SkyrimShader:Default']
        for node in list(mat.node_tree.nodes):
            if node.type=='TEX_IMAGE':mat.node_tree.nodes.remove(node)
        for prop in list(mat.keys()):
            if prop.startswith('BSShaderTextureSet_'):del mat[prop]
        color=spec['edge'] if i else spec['color']
        power=spec['power'][i]
        shader.inputs['Emission Color'].default_value=tuple(color)+(1,)
        shader.inputs['Emission Strength'].default_value=power
        shader.inputs['Specular Color'].default_value=(0,0,0,1)
        shader.inputs['Glossiness'].default_value=1
        mat.pyn_shader.Shader_Type='Glow_Shader'
        mat.pyn_shader.Shader_Flags_1='OWN_EMIT | ZBUFFER_TEST'
        mat.pyn_shader.Shader_Flags_2='ZBUFFER_WRITE | GLOW_MAP'
        for slot,name,inlet in [('Diffuse',spec['diffuse_name'],'Diffuse'),('Normal','aa_red_n','Normal'),('Glow','aa_red_g','Glow Map')]:
            path=TEX/(name+'.dds')
            shutil.copy2(ROOT/'data/textures/weapons/arcanearsenal'/(name+'.dds'),path)
            img=bpy.data.images.load(str(path),check_existing=True)
            node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=img
            node.name={'Diffuse':'Diffuse_Texture','Normal':'Normal_Texture','Glow':'Glow_Map_Texture'}[slot]
            mat['BSShaderTextureSet_'+slot]='textures\\weapons\\arcanearsenal\\staves\\'+Path(img.filepath).name
            mat.node_tree.links.new(node.outputs['Color'],shader.inputs[inlet])
        materials[label]=mat
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.pynifly(filepath=str(ROOT/'build/staves-reference/staff01.nif'))
    root=next(o for o in bpy.context.scene.objects if o.get('pynRoot'))
    ref=bpy.data.objects['Staff01:0'];props=dict(ref.items());bpy.data.objects.remove(ref,do_unlink=True)
    root['pynNodeName']=key;root.name=key+'_ROOT'
    for o in bpy.context.scene.objects:
        if o.name.startswith('bhk'):o.hide_render=True
    objects=[]
    def solid(verts,faces,bevel=.2):
        bpy.ops.object.select_all(action='DESELECT')
        mesh=bpy.data.meshes.new(key+'_part');mesh.from_pydata(verts,[],faces);mesh.update()
        obj=bpy.data.objects.new(key+'_part',mesh);bpy.context.collection.objects.link(obj)
        obj.data.materials.append(materials['Body']);obj.data.materials.append(materials['Edge'])
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        if bevel:
            mod=obj.modifiers.new('Fine physical bevel','BEVEL');mod.width=bevel;mod.segments=1;mod.affect='EDGES'
            mod.material=1
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False);objects.append(obj);return obj
    build(spec,solid)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=.000001);bpy.ops.mesh.dissolve_degenerate(threshold=.000001)
    bpy.ops.mesh.quads_convert_to_tris();bpy.ops.mesh.dissolve_degenerate(threshold=.000001)
    bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
    shapes=[o for o in bpy.context.selected_objects if o.type=='MESH']
    assert len(shapes)==2
    for o in shapes:
        label=next(k for k,v in materials.items() if o.data.materials[0]==v)
        o.name='AA_Staff'+label;o.parent=root;o.matrix_basis=Matrix.Identity(4)
        for k,v in props.items():
            if k!='pynNodeName':o[k]=v
        o['pynNodeName']=o.name
        uv=o.data.uv_layers.new(name='UVMap')
        for poly in o.data.polygons:
            for loop in poly.loop_indices:
                v=o.data.vertices[o.data.loops[loop].vertex_index].co
                uv.data[loop].uv=(v.x/8+v.z/8,v.y/12)
        o.data.update()
    bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=shapes[0]
    out=MESH/(key+'.nif')
    bpy.ops.export_scene.pynifly(filepath=str(out),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,rename_bones=True,rotate_bones_pretty=False,export_pose=False,export_modifiers=False,export_animations=False)
    n=NifBlocks(out);reference=NifBlocks(ROOT/'build/staves-reference/staff01.nif')
    assert [k for k,b in n.blocks[4:7]]==['bhkCapsuleShape','bhkRigidBody','bhkCollisionObject']
    # Preserve vanilla rigid body / attachment, replace its shape with fitted boxes.
    n.blocks[5:7]=reference.blocks[5:7]
    template_n=NifBlocks(ROOT/'build/staves-reference/collision-template.nif')
    pts=[o.matrix_world@v.co for o in shapes for v in o.data.vertices]
    collisions=[];links=[]
    for lo,hi in ((-100,-13),(-13,8),(8,30),(30,100)):
        group=[p for p in pts if lo<=p.y<hi];assert group
        low=Vector([min(p[i] for p in group)-.15 for i in range(3)])
        high=Vector([max(p[i] for p in group)+.15 for i in range(3)])
        half=(high-low)/2;center=(high+low)/2
        box=bytearray(template_n.blocks[4][1])
        struct.pack_into('<I',box,0,struct.unpack_from('<I',reference.blocks[4][1],0)[0])
        struct.pack_into('<3f',box,16,*(v/69.99125 for v in half))
        bindex=n.append('bhkBoxShape',box)
        transform=bytearray(template_n.blocks[5][1])
        struct.pack_into('<I',transform,0,bindex)
        struct.pack_into('<I',transform,4,struct.unpack_from('<I',box,0)[0])
        struct.pack_into('<16f',transform,20,1,0,0,0,0,1,0,0,0,0,1,0,*(v/69.99125 for v in center),0)
        links.append(n.append('bhkConvexTransformShape',transform))
        collisions.append({'range':[lo,hi],'center':list(center),'half_extents':list(half)})
    # Native list shape layout: refs, material, two array-property structs, filters.
    old=template_n.blocks[10][1]
    count=struct.unpack_from('<I',old,0)[0]
    tail=bytearray(old[4+4*count:4+4*count+28])
    struct.pack_into('<I',tail,0,struct.unpack_from('<I',reference.blocks[4][1],0)[0])
    blob=struct.pack('<I',len(links))+struct.pack('<'+'I'*len(links),*links)+tail+struct.pack('<I',len(links))+bytes(4*len(links))
    n.blocks[4]=('bhkListShape',bytes(blob))
    # First-person variant uses the same authored grip and geometry, with its
    # native inventory marker. Neither file contains a spell or animation graph.
    n.save(out)
    first=NifBlocks(ROOT/'build/staves-reference/1stpersonstaff01.nif')
    marker=next(i for i,(kind,blob) in enumerate(n.blocks) if kind=='BSInvMarker')
    first_marker=next(blob for kind,blob in first.blocks if kind=='BSInvMarker')
    n.blocks[marker]=(n.blocks[marker][0],n.blocks[marker][1][:4]+first_marker[4:])
    n.save(MESH/('1stperson'+key+'.nif'))
    # Hide the imported placeholder collision. Source shapes retain game coords.
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.008,.008,.012,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    cd=bpy.data.cameras.new('StaffPreview');cam=bpy.data.objects.new('StaffPreview',cd);scene.collection.objects.link(cam)
    cam.location=(22,0,220);cam.rotation_euler=(0,math.atan2(22,220),0)
    cd.type='ORTHO';cd.ortho_scale=151;scene.camera=cam
    scene.render.resolution_x=650;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
    scene.render.filepath=str(ART/(key+'.png'))
    bpy.ops.object.select_all(action='DESELECT')
    for o in shapes:o.select_set(True)
    bpy.context.view_layer.objects.active=shapes[0]
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/(key+'.blend')))
    bpy.ops.render.render(write_still=True)
    report={'key':key,'name':spec['name'],'triangles':sum(len(o.data.polygons) for o in shapes),'shapes':2,'bounds':[(min(p[i] for p in pts),max(p[i] for p in pts)) for i in range(3)],'collision_boxes':collisions,'attachment':'WeaponStaff','gameplay_tested':False,'stage':'geometric models 0.2.0'}
    (STAGE/(key+'-model.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STAFF_BUILT',json.dumps(report,ensure_ascii=False))
