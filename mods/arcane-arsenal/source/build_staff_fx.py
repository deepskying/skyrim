"""Small, collision-free geometric spell visuals, using the staff's own shaders."""
import bpy,math,sys,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/meshes/weapons/arcanearsenal/staves'
ART=ROOT/'art/arcane-staves'
keys=['stafftorch','staffshuttle','staffsteps','stafffold','stafftorch','stafffold','staffsteps','stafffold']
for index,key in enumerate(keys):
    bpy.ops.wm.open_mainfile(filepath=str(ART/(key+'.blend')))
    mat=bpy.data.objects['AA_StaffEdge'].data.materials[0].copy()
    for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
    parts=[]
    def box(center,scale,angle=0):
        bpy.ops.mesh.primitive_cube_add(size=2,location=center)
        o=bpy.context.object;o.scale=scale;o.rotation_euler.z=angle
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);parts.append(o)
    def shard(center,r=5,h=12,angle=0):
        x,y,z=center;c=math.cos(angle);s=math.sin(angle)
        pts=[(-r,0,0),(0,-r,0),(r,0,0),(0,r,0),(0,0,h),(0,0,-h)]
        verts=[(x+a*c-b*s,y+a*s+b*c,z+d) for a,b,d in pts]
        faces=[(i,(i+1)%4,4) for i in range(4)]+[((i+1)%4,i,5) for i in range(4)]
        mesh=bpy.data.meshes.new('Facet');mesh.from_pydata(verts,[],faces);mesh.update()
        o=bpy.data.objects.new('Facet',mesh);bpy.context.collection.objects.link(o);parts.append(o)
    if index in (0,2,3):
        shard((0,0,0),4,9)
        if index==0:shard((6,0,-6),2.3,7)
    elif index==1:
        # A compact hollow shuttle; the runtime orients Y along its flight.
        for sign in (-1,1):
            box((sign*4,-5,0),(1.3,7,1.2),sign*-.45)
            box((sign*4,5,0),(1.3,7,1.2),sign*.45)
    elif index==4:
        for i in range(12):
            a=i*math.tau/12;shard((math.cos(a)*95,math.sin(a)*95,0),4,22,a)
        for i in range(6):
            a=i*math.tau/6;shard((math.cos(a)*42,math.sin(a)*42,0),4,28,a)
    elif index==5:
        for i in range(12):
            a=i*math.tau/12;box((math.cos(a)*175,math.sin(a)*175,0),(24,1.5,1.5),a+math.pi/2)
        shard((0,0,0),6,18)
    elif index==6:
        for y in (-68,0,68):box((0,y,0),(104,1.8,1.5))
        for x in (-104,104):box((x,0,0),(1.8,68,1.5))
        for x in (-80,-40,0,40,80):shard((x,0,6),4,16)
    else:
        for i in range(9):
            a=i*math.tau/9;shard((math.cos(a)*100,math.sin(a)*100,0),8,33,a)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='AAStaffFX'+str(index)
    o.data.materials.clear();o.data.materials.append(mat)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.mesh.quads_convert_to_tris();bpy.ops.object.mode_set(mode='OBJECT')
    uv=o.data.uv_layers.new(name='UVMap')
    for loop in o.data.loops:
        p=o.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x/20,p.y/20)
    bpy.ops.export_scene.pynifly(filepath=str(OUT/('fx'+str(index)+'.nif')),target_game='SKYRIMSE',intuit_defaults=False,preserve_hierarchy=True,blender_xf=False,export_modifiers=False,export_animations=False)
    print('FX_BUILT',index,len(o.data.polygons))
