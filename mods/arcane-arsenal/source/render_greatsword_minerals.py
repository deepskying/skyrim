"""Offline NIF/texture inspection in Blender, not an in-game lighting capture."""
from pathlib import Path
import sys, math
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from build_greatsword_minerals import SPECS, EMIT
OUT=ROOT/'art/greatsword-minerals'
STAGE=ROOT/'build/greatsword-minerals/data'
updated='--fluorite-bornite' in sys.argv
if updated:
    from build_fluorite_bornite import SPECS, EMIT, ART, STAGE
    OUT=ART
layered='--layered' in sys.argv
if layered:
    from build_layered_greatswords import SPECS, EMIT, ART, STAGE
    OUT=ART
final='--final-greatswords' in sys.argv
if final:
    from apply_final_greatsword_materials import CATALOG, STAGE, ART, BLUE
    from build_fluorite_bornite import SPECS as mineral_specs, EMIT as mineral_emit
    from build_greatsword_minerals import SPECS as original_specs
    from build_layered_greatswords import SPECS as layered_specs
    SPECS={'red':dict(original_specs['red'],art=ROOT/'art/material-trials'),
           'green':dict(layered_specs['green'],art=ROOT/'art/layered-greatswords'),
           'blue':dict(layered_specs['blue'],texture=BLUE,art=ART),
           'purple':dict(mineral_specs['purple'],art=ROOT/'art/fluorite-bornite')}
    EMIT={'red':(0,0,0),'green':(1,1,1),'blue':(1,1,1),'purple':mineral_emit['purple']}
    OUT=ART;updated=True
if '--glazed' in sys.argv:
    from build_glazed_greatswords import CATALOG, STAGE, ART, SPECS, EMIT
    SPECS={c:dict(s,art=ART) for c,s in SPECS.items()}
    OUT=ART;final=True;layered=True;updated=False
if '--luminous-jade-opal' in sys.argv:
    from build_luminous_greatswords import CATALOG, STAGE, ART, SPECS, EMIT
    SPECS={c:dict(s,art=ART) for c,s in SPECS.items()}
    OUT=ART;final=True;layered=True;updated=False
colors={'red':(1,.015,.025),'green':(.16,1,.67),'blue':(.16,.95,1),'purple':(.72,.3,1)}
powers={'red':3.6,'green':4.5,'blue':5.4,'purple':5.4}
if '--refined-opal' in sys.argv:
    from refine_purple_opal import CATALOG, STAGE, ART, SPECS, EMIT, EDGE_COLOR, EDGE_POWER
    SPECS={c:dict(s,art=ART) for c,s in SPECS.items()}
    OUT=ART;final=True;layered=True;updated=False
    colors['purple']=EDGE_COLOR;powers['purple']=EDGE_POWER
luminous_sampling=('--luminous-jade-opal' in sys.argv or '--refined-opal' in sys.argv)

def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

items=[('greatsword3'+c,c,s) for c,s in SPECS.items()]
if final:
    items=[(s['key'],c,SPECS[c]) for s in CATALOG for c in SPECS if s['key'].endswith(c)]
for weapon,color,spec in items:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    path=STAGE/'meshes/weapons/arcanearsenal'/(weapon+'.nif')
    bpy.ops.import_scene.pynifly(filepath=str(path))
    shapes=[o for o in bpy.context.scene.objects if o.name in ('AA_GreatswordBody','AA_GreatswordEdge')]
    assert len(shapes)==2
    for o in shapes:
        xf=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Rotation(.25,4,'Y')@xf
    for o in list(bpy.context.scene.objects):
        if o not in shapes:bpy.data.objects.remove(o,do_unlink=True)
    for o in shapes:
        m=bpy.data.materials.new(o.name);m.use_nodes=True;t=m.node_tree;p=t.nodes['Principled BSDF']
        if o.name.endswith('Body'):
            texture_dir=ROOT/'art/material-trials' if color=='red' else OUT
            if final:texture_dir=spec['art']
            for suffix in ('d','n'):
                node=t.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(texture_dir/(spec['texture']+'_'+suffix+'.png')))
                if luminous_sampling:
                    coords=t.nodes.new('ShaderNodeTexCoord');scale=t.nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
                    scale.inputs[1].default_value=(.55,.55*100/30,1)
                    t.links.new(coords.outputs['UV'],scale.inputs[0]);t.links.new(scale.outputs[0],node.inputs['Vector'])
                if suffix=='d':t.links.new(node.outputs['Color'],p.inputs['Base Color'])
                else:
                    node.image.colorspace_settings.name='Non-Color';nm=t.nodes.new('ShaderNodeNormalMap')
                    t.links.new(node.outputs['Color'],nm.inputs['Color']);t.links.new(nm.outputs[0],p.inputs['Normal'])
            p.inputs['Roughness'].default_value={'red':.13,'green':.23,'blue':.31,'purple':.26}[color]
            p.inputs['Coat Weight'].default_value=.35
            if '--refined-opal' in sys.argv:p.inputs['Specular IOR Level'].default_value=.28/.55*.5
            if updated and color=='purple':
                p.inputs['Metallic'].default_value=.75
                p.inputs['Roughness'].default_value=.32
                p.inputs['Coat Weight'].default_value=.10
                rough=t.nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=.2;rough.inputs['From Max'].default_value=.95
                rough.inputs['To Min'].default_value=.48;rough.inputs['To Max'].default_value=.20
                t.links.new(node.outputs['Alpha'],rough.inputs['Value']);t.links.new(rough.outputs['Result'],p.inputs['Roughness'])
            p.inputs['Emission Color'].default_value=(*EMIT[color],1)
            p.inputs['Emission Strength'].default_value=spec['power']
            if layered or (final and color in ('blue','green')):
                glow=t.nodes.new('ShaderNodeTexImage');glow.image=bpy.data.images.load(str(texture_dir/(spec['texture']+'_g.png')))
                if luminous_sampling:t.links.new(scale.outputs[0],glow.inputs['Vector'])
                t.links.new(glow.outputs['Color'],p.inputs['Emission Color'])
        else:
            p.inputs['Base Color'].default_value=(*colors[color],1)
            p.inputs['Emission Color'].default_value=(*colors[color],1)
            p.inputs['Emission Strength'].default_value=powers[color]
        o.data.materials.clear();o.data.materials.append(m)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.06,.065,.08,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    scene.view_settings.view_transform='AgX'
    points=[o.matrix_world@v.co for o in shapes for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    target=(lo+hi)/2
    for name,loc,power,size in [('Key',(-85,100,75),70000,35),('Fill',(85,20,40),25000,30)]:
        if luminous_sampling:power*=.25
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size
        o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;aim(o,target)
    d=bpy.data.cameras.new('Camera');o=bpy.data.objects.new('Camera',d);scene.collection.objects.link(o)
    o.location=(target.x,target.y,250);aim(o,target);d.type='ORTHO';d.ortho_scale=max(hi.y-lo.y,(hi.x-lo.x)*1.5)*1.12;scene.camera=o
    scene.use_nodes=True;t=scene.node_tree;t.nodes.clear();r=t.nodes.new('CompositorNodeRLayers')
    g=t.nodes.new('CompositorNodeGlare');g.glare_type='FOG_GLOW';g.threshold=1.5;g.quality='HIGH';g.size=7
    out=t.nodes.new('CompositorNodeComposite');t.links.new(r.outputs['Image'],g.inputs['Image']);t.links.new(g.outputs['Image'],out.inputs['Image'])
    scene.render.resolution_x=700;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(weapon+'-preview.png'))
    bpy.ops.render.render(write_still=True)
