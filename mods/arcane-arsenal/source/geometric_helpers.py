"""Shared rig binding, DDS generation and geometric rails for solid-light bows."""
import mesh_builder as mb
from mesh_builder import bpy,np,math,Vector,ref,ART,TEX
from pathlib import Path
STRING_X=-13.674
ANCHORS={1:54.97,-1:-54.70}
samples={}
for vertex in ref.data.vertices:
    p=ref.matrix_world@vertex.co
    weights={ref.vertex_groups[g.group].name:g.weight for g in vertex.groups if ref.vertex_groups[g.group].name in mb.bone_names}
    if p.x < -13.3 and any('StringBone' in name and w>0 for name,w in weights.items()):
        samples.setdefault(round(p.y,3),[]).append(weights)
string_samples=[]
for y,entries in sorted(samples.items()):
    if ANCHORS[-1]<y<ANCHORS[1]:
        average={name:sum(e.get(name,0) for e in entries)/len(entries) for name in mb.bone_names}
        string_samples.append((y,{name:w for name,w in average.items() if w>.00001}))
string_samples=[(ANCHORS[-1],{'Bow_LoBone2':1.0})]+string_samples+[(ANCHORS[1],{'Bow_UpBone2':1.0})]
assert len(string_samples)>8

def string_weights(point):
    y=Vector(point).y
    for (a,wa),(b,wb) in zip(string_samples[:-1],string_samples[1:]):
        if y<=b:
            t=max(0,min(1,(y-a)/(b-a)))
            weights={name:(1-t)*wa.get(name,0)+t*wb.get(name,0) for name in wa.keys()|wb.keys()}
            return {name:w for name,w in weights.items() if w>.000001}
    return string_samples[-1][1]

def texture(name,color,normal=False):
    path=TEX/(name+'.dds')
    if path.is_file():return bpy.data.images.load(str(path),check_existing=True)
    n=64;pixels=np.empty((n,n,4),np.float32);pixels[:]=color
    image=bpy.data.images.new(name,width=n,height=n,alpha=True)
    if normal:image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(ART/(name+'.png'));image.file_format='PNG';image.save()
    exe=r'C:\Users\linos\Desktop\games\+skyrim\TOOLS\+tools-VRAMr\VRAMr\tools\texconv.exe'
    mb.subprocess.run([exe,'-nologo','-y','-f','BC3_UNORM' if normal else 'BC7_UNORM','-m','0','-o',str(TEX),str(ART/(name+'.png'))],check=True,capture_output=True)
    image.filepath=str(path);image.reload();return image

def polyline(points,width,category,binding=None):
    for a,b in zip(points[:-1],points[1:]):
        a,b=Vector(a),Vector(b)
        if (b-a).length<.0001:continue
        # Rigid triangle edges need only their endpoints. Flexible rails are sampled.
        steps=2 if binding else max(2,int((b-a).length/.8)+1)
        pts=[a.lerp(b,float(t)) for t in np.linspace(0,1,steps)]
        tangent=(b-a).normalized();side=tangent.cross(Vector((0,0,1)))
        if side.length<.01:side=tangent.cross(Vector((0,1,0)))
        side.normalize();normal=tangent.cross(side).normalized()
        verts=[];faces=[];uv=[];weights=[];sides=8
        for i,p in enumerate(pts):
            for j in range(sides):
                angle=math.tau*j/sides
                verts.append(tuple(p+width*(math.cos(angle)*side+math.sin(angle)*normal)))
                uv.append((j/sides,i/(steps-1)))
                weights.append(binding or mb.weights_at(mb.center(p.y)))
            if i:
                for j in range(sides):
                    v=(i-1)*sides+j;w=(i-1)*sides+(j+1)%sides
                    faces.append((v,w,w+sides,v+sides))
        faces.extend([tuple(range(sides-1,-1,-1)),tuple((steps-1)*sides+j for j in range(sides))])
        mb.batches[category].add(verts,faces,uv,weights)
