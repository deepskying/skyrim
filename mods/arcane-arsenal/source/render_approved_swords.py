"""Inspect all eight patched NIFs using their actual DDS and shader parameters.

Blender approximates the Skyrim material; this is not an in-game ENB capture.
Particle controllers are excluded from this static geometry inspection.
"""
from pathlib import Path
import math, struct, sys
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from apply_approved_sword_materials import CATALOG, STAGE, ART, MESH, shapes, texture_paths
from nif_blocks import NifBlocks


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


for spec in CATALOG:
    key = spec['key']
    path = STAGE / MESH / (key + '.nif')
    nif = NifBlocks(path)
    parts = shapes(nif)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.pynifly(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.name in parts]
    assert len(meshes) == 2
    for obj in meshes:
        transform = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = Matrix.Rotation(.25, 4, 'Y') @ transform
    for obj in list(bpy.context.scene.objects):
        if obj not in meshes:
            bpy.data.objects.remove(obj, do_unlink=True)
    for obj in meshes:
        si, ti = parts[obj.name]
        shader = nif.blocks[si][1]
        textures = texture_paths(nif.blocks[ti][1])
        mat = bpy.data.materials.new(key + obj.name)
        mat.use_nodes = True
        tree = mat.node_tree
        bsdf = tree.nodes['Principled BSDF']
        coords = tree.nodes.new('ShaderNodeTexCoord')
        mapping = tree.nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (*struct.unpack_from('<2f', shader, 32), 1)
        mapping.inputs['Location'].default_value = (*struct.unpack_from('<2f', shader, 24), 0)
        tree.links.new(coords.outputs['UV'], mapping.inputs['Vector'])
        nodes = []
        for slot in range(3):
            tex = tree.nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(str(ROOT / 'data' / textures[slot]), check_existing=True)
            tex.extension = 'REPEAT'
            tree.links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
            nodes.append(tex)
        tree.links.new(nodes[0].outputs['Color'], bsdf.inputs['Base Color'])
        nodes[1].image.colorspace_settings.name = 'Non-Color'
        normal = tree.nodes.new('ShaderNodeNormalMap')
        tree.links.new(nodes[1].outputs['Color'], normal.inputs['Color'])
        tree.links.new(normal.outputs[0], bsdf.inputs['Normal'])
        emission = tree.nodes.new('ShaderNodeMixRGB')
        emission.blend_type = 'MULTIPLY'
        emission.inputs[0].default_value = 1.
        emission.inputs[2].default_value = (*struct.unpack_from('<3f', shader, 44), 1)
        tree.links.new(nodes[2].outputs['Color'], emission.inputs[1])
        tree.links.new(emission.outputs[0], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = struct.unpack_from('<f', shader, 56)[0]
        bsdf.inputs['Roughness'].default_value = max(.16, math.sqrt(2 / (struct.unpack_from('<f', shader, 72)[0] + 2)))
        bsdf.inputs['Specular IOR Level'].default_value = min(.5, struct.unpack_from('<f', shader, 88)[0] * .6)
        bsdf.inputs['Coat Weight'].default_value = .2
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.06, .065, .08, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    scene.view_settings.view_transform = 'AgX'
    points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    target = (low + high) / 2
    for name, location, power, size in [('Key', (-85, 100, 75), 17500, 35), ('Fill', (85, 20, 40), 6250, 30)]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.size = power, size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = location
        aim(obj, target)
    camera = bpy.data.cameras.new('Camera')
    obj = bpy.data.objects.new('Camera', camera)
    scene.collection.objects.link(obj)
    obj.location = (target.x, target.y, 250)
    aim(obj, target)
    camera.type = 'ORTHO'
    camera.ortho_scale = max(high.y - low.y, (high.x - low.x) * 1.5) * 1.12
    scene.camera = obj
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    render = tree.nodes.new('CompositorNodeRLayers')
    glow = tree.nodes.new('CompositorNodeGlare')
    glow.glare_type, glow.threshold, glow.quality, glow.size = 'FOG_GLOW', 1.5, 'HIGH', 7
    output = tree.nodes.new('CompositorNodeComposite')
    tree.links.new(render.outputs['Image'], glow.inputs['Image'])
    tree.links.new(glow.outputs['Image'], output.inputs['Image'])
    scene.render.resolution_x, scene.render.resolution_y = 700, 1050
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(ART / (key + '-preview.png'))
    bpy.ops.render.render(write_still=True)
