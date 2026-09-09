"""Build an Arcane Arsenal bow in Blender using the game's bow rig.

Run using the configured portable Blender. Original body geometry is not exported.
The source rig supplies bone transforms, normalized binding and weapon metadata.
"""
import bpy
import numpy as np
import math, random, json, subprocess
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
TOOLS = REPO / 'reference/bow-tools'
DATA = ROOT / 'data'
ART = ROOT / 'art'
MESH = DATA / 'meshes/weapons/arcanearsenal'
TEX = DATA / 'textures/weapons/arcanearsenal'
for folder in (ART, MESH, TEX, ROOT / 'build'):
    folder.mkdir(parents=True, exist_ok=True)
random.seed(914)
bpy.ops.wm.open_mainfile(filepath=str(TOOLS / 'validation/ironbow-textured-check.blend'))
ref = bpy.data.objects['Bow_Ironmesh:0']
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
root = rig.parent
base_mat = ref.data.materials[0]
bone_names = set(rig.data.bones.keys())

# Cache reference surface weights independently from the bowstring.
bind = []
body_points, string_points = [], []
for v in ref.data.vertices:
    co = ref.matrix_world @ v.co
    weights = {ref.vertex_groups[g.group].name:g.weight for g in v.groups
               if ref.vertex_groups[g.group].name in bone_names and g.weight > 0.0001}
    bind.append(weights)
    item = (co.copy(), v.index)
    if co.x < -12.8 and abs(co.y) < 50.5:
        string_points.append(item)
    else:
        body_points.append(item)

def tree(points):
    kd = KDTree(len(points))
    for co, i in points: kd.insert(co, i)
    kd.balance()
    return kd

body_kd, string_kd = tree(body_points), tree(string_points)

def weights_at(point, string=False):
    entries = (string_kd if string else body_kd).find_n(Vector(point), 4)
    weights = {}
    for _, i, dist in entries:
        factor = 1 / max(dist, 0.05)**2
        for name, weight in bind[i].items():
            weights[name] = weights.get(name, 0) + factor*weight
    top = sorted(weights.items(), key=lambda p:-p[1])[:4]
    total = sum(w for _,w in top)
    assert total > 0
    return {name:weight/total for name,weight in top}

def center(y):
    return Vector((1.3 - 14.97*(abs(y)/55.0)**2.35, y, 0.0))


materials={}
batches={}
class Batch:
    def __init__(self,name):
        self.name=name; self.verts=[]; self.faces=[]; self.uv=[]; self.weights=[]
    def add(self,verts,faces,uv,weights):
        offset=len(self.verts)
        self.verts.extend(verts); self.faces.extend(tuple(offset+i for i in f) for f in faces)
        self.uv.extend(uv); self.weights.extend(weights)
    def object(self):
        mesh=bpy.data.meshes.new('AA_'+self.name); mesh.from_pydata(self.verts,[],self.faces); mesh.update()
        obj=bpy.data.objects.new('AA_'+self.name,mesh); bpy.context.collection.objects.link(obj); obj.parent=root
        obj.data.materials.append(materials[self.name])
        layer=mesh.uv_layers.new(name='UVMap')
        for poly in mesh.polygons:
            for loop in poly.loop_indices: layer.data[loop].uv=self.uv[mesh.loops[loop].vertex_index]
        for name in bone_names:
            vg=obj.vertex_groups.new(name=name)
            for i,weights in enumerate(self.weights):
                if name in weights: vg.add([i],weights[name],'REPLACE')
        obj.vertex_groups.new(name='SBP_32_BODY').add(list(range(len(self.verts))),1,'REPLACE')
        mod=obj.modifiers.new('Bow deformation','ARMATURE'); mod.object=rig
        for key in ('pynBlockName','pynNodeFlags','pynVertexDesc','pynSkinInstanceType','PYN_GAME','PYN_BLENDER_XF','PYN_RENAME_BONES'):
            if key in ref: obj[key]=ref[key]
        obj['pynNodeName']=obj.name
        return obj



def crystal(base, tip, width, depth, category='ice', binding=None, roll=0):
    base,tip=Vector(base),Vector(tip); axis=(tip-base).normalized()
    transverse=axis.cross(Vector((0,0,1)))
    if transverse.length<.01: transverse=axis.cross(Vector((1,0,0)))
    transverse.normalize(); normal=axis.cross(transverse).normalized()
    verts=[]; uv=[]; faces=[]
    sides=6
    for t,radius in [(0,.44),(.20,1),(.66,.73),(.84,.40)]:
        for j in range(sides):
            a=math.tau*j/sides+roll
            p=base.lerp(tip,t)+transverse*(math.cos(a)*width*radius)+normal*(math.sin(a)*depth*radius)
            verts.append(tuple(p)); uv.append((j/sides,t))
    verts.append(tuple(tip)); uv.append((.5,1))
    faces.append(tuple(range(sides-1,-1,-1)))
    for r in range(3):
        for j in range(sides):
            a=r*sides+j; b=r*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    for j in range(sides): faces.append((18+j,18+(j+1)%sides,24))
    binding=binding or weights_at(base)
    batches[category].add(verts,faces,uv,[binding]*len(verts))

def sweep(points,radii,category,weightfunc=None,sides=8,depth=1):
    verts=[]; uv=[]; faces=[]; weights=[]
    pts=[Vector(p) for p in points]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        side=tangent.cross(Vector((0,0,1))).normalized()
        normal=tangent.cross(side).normalized()
        for j in range(sides):
            a=math.tau*j/sides
            verts.append(tuple(p+float(radii[i])*(math.cos(a)*side+depth*math.sin(a)*normal)))
            uv.append((j/sides,i/(len(pts)-1)))
            weights.append(weightfunc(p) if weightfunc else weights_at(center(p.y)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides
                faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(pts)-1)*sides+j for j in range(sides))])
    batches[category].add(verts,faces,uv,weights)
