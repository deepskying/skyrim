"""First approved one-handed set, modelled around the IronSword grip origin."""
from greatswords2_geometry import curve


def build(spec, slab, rail, frame, solid):
    kind=spec['design']
    if kind=='shear':
        # Clip point, deep open notch and a continuous full-length cutting spine.
        outline=[(-2,7),(-2,30),(-3.8,47),(-1,61),(0,51),(3,54),
                 (4,58),(3.3,58.5),(9,65),(10,73),(16,61),(13,62.8),
                 (8,50),(5,38),(2,11),(2.8,8)]
        slab(outline,2.2,bevel=.38)
        # Large oblique facet ridge, tapered into the root and spine.
        verts=[(-1.7,14,1.1),(-3.2,46,1.1),(11,65,1.1),(2,35,2.05)]
        solid(verts,[(0,1,3),(1,2,3),(2,0,3),(0,2,1)],.06)
        slab([(-1,5),(-5,9),(-6,13),(-1,9)],2.8,bevel=.3)
        slab([(0,5),(5,7),(12,17),(3,11)],2.8,bevel=.3)
        slab([(0,-8.5),(-2.6,-11.5),(0,-16),(2.6,-11.5)],2.8,bevel=.25)
        return [(1,54,0),(1,58,0),(2,62,0),(6,65,0),(-4,49,0),(6,52,0)]
    if kind=='shuttle':
        # The upper S blade is continuous; two curved rails enclose a spindle
        # window in the lower third without filling its negative space.
        left=curve([(-2,7),(-2,10),(-3.3,12),(-4,15)],12)
        left+=curve([(-4,15),(0,28),(0,34),(-1,42)],24)[1:]
        left+=curve([(-1,42),(-5,55),(-5,60),(3,73)],24)[1:]
        right=curve([(3,73),(-1,61),(3.8,53),(4.2,43)],24)
        right+=curve([(4.2,43),(4.5,29),(.8,15),(3,8)],24)[1:]
        window_l=curve([(1,16),(.1,25),(.7,32),(2,36)],22)
        window_r=curve([(2,36),(3.0,27),(1.9,22),(1,16)],22)
        # Cut the slot from one continuous slab, avoiding seams between blade sections.
        import bpy
        blade=slab(left+right[1:],2.1,bevel=.23)
        loop=window_l+window_r[1:-1];n=len(loop)
        vertices=[(x,y,z) for z in (-5,5) for x,y in loop]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        mesh=bpy.data.meshes.new('Spindle cutter');mesh.from_pydata(vertices,[],faces);mesh.update()
        cutter=bpy.data.objects.new('Spindle cutter',mesh);bpy.context.collection.objects.link(cutter)
        bpy.ops.object.select_all(action='DESELECT');cutter.select_set(True)
        bpy.context.view_layer.objects.active=cutter
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
        cutter.select_set(False)
        bpy.context.view_layer.objects.active=blade
        cut=blade.modifiers.new('Through spindle','BOOLEAN');cut.operation='DIFFERENCE';cut.solver='EXACT';cut.object=cutter
        bpy.ops.object.modifier_apply(modifier=cut.name)
        bpy.data.objects.remove(cutter,do_unlink=True)
        rim=blade.modifiers.new('Slot bevel','BEVEL');rim.width=.12;rim.segments=1;rim.material=1
        bpy.ops.object.modifier_apply(modifier=rim.name)
        rail(window_l+window_r[1:],.26,.24,z=1.08)
        rail(curve([(-2,6),(-1,4),(2,4),(4,6)],14),1.65,2.7)
        # Outer knuckle arch remains clear of the single palm envelope.
        rail(curve([(3,6),(14,3),(11,-7),(1,-8)],32),1.6,2.5)
        slab([(-2,-8),(-3,-10),(0,-12.5),(3,-10),(2,-8)],3,bevel=.3)
        return [(3.5,20,0),(4,24,0),(4,28,0),(3.8,32,0),(2.8,37,0),(5,44,0)]
    if kind=='aperture':
        # Two shoulders enclose a real lower blade window and meet at its apex.
        for side in (-1,1):
            slab([(side*x,y) for x,y in [(1.8,7),(4.2,19),(3.0,27),(0,38),(2.1,38),(7.4,19),(4,7)]],2.2,bevel=.25)
        slab([(-2.1,36),(-3.6,60),(0,73),(3.6,60),(2.1,36),(0,38)],2.2,bevel=.28)
        # A faceted floating triangle, offset within the aperture.
        solid([(-.9,17,0),(1.7,20,.3),(.3,26,0),(.2,21,1.7),(.2,21,-1.2)],
              [(0,1,3),(1,2,3),(2,0,3),(1,0,4),(2,1,4),(0,2,4)],.12)
        slab([(-3.7,5),(-5,7),(-3.7,9),(3.7,9),(5,7),(3.7,5)],3.2,bevel=.35)
        for side in (-1,1):
            slab([(side*x,y) for x,y in [(4,8),(8,6),(10,1),(7,3),(5,6)]],2.4,bevel=.26)
        slab([(-2,-8),(-3.5,-11),(0,-14.5),(3.5,-11),(2,-8)],3.3,bevel=.3)
        return [(0,12,0),(-.3,16,0),(.5,26,0),(0,30,0),(-.2,33,0),(.1,35,0)]
    if kind=='parallax':
        # Staggered plates are distinct in depth, joined by two solid bridges.
        slab([(-2,6),(-4,14),(-4,64),(1.4,73),(1.4,8)],2.1,z=-.7,bevel=.32)
        short=slab([(2,9),(2,50),(5.8,56),(5.8,14),(4,10)],1.9,z=.85,bevel=.28)
        for face in short.data.polygons:
            if abs(face.normal.z)>.85:face.material_index=1
        for y in (22,47):
            verts=[(x,y+dy,z) for x,dy,z in [(.5,0,.3),(5, -1,1.8),(5,1,1.8),(.5,2,.3),(.5,0,-.7),(5,-1,.8),(5,1,.8),(.5,2,-.7)]]
            solid(verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],.15)
        solid([(-8,7,0),(0,10,0),(8,6,0),(0,3.8,0),(0,7,2.7),(0,7,-2.1)],
              [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],.15)
        slab([(-2,-8.5),(-2.8,-12),(1.5,-13.5),(2.8,-9.5)],3,z=.3,bevel=.3)
        return [(6,17,0),(6.5,28,0),(6.5,38,0),(6.5,48,0),(2.8,61,0),(2.8,66,0)]
    raise ValueError(kind)
