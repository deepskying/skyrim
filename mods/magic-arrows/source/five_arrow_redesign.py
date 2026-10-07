"""Five approved October-7 concepts as closed, faceted energy solids.

Keep the vanilla Y=0..58 attachment frame and the approved blood-arrow scale.
Profiles are authored geometry, not projected concept textures or flat billboards.
"""
import math
import shutil
from collections import Counter
from geometry import cross
from geometric_selected import Solid, bevel_square, write_textures as original_textures
from geometric_round03 import axial, collar, ridge
from redesign_geometry import loft, smooth_samples
from paths import BUILD

VERSION = '0.8.0'
KEYS = ('fire', 'holy', 'arcane', 'poison', 'ice')
REMAINING = KEYS
LABELS = dict(zip(KEYS, ('火焰箭 · 宽弯焰刃', '圣辉箭 · 日轮十字',
                        '奥术箭 · 阶梯符文矛', '蛇牙箭 · 开放双牙', '霜晶箭 · 六棱晶簇')))
STAGE = 'five-arrow-redesign08/data'
ART = 'five-arrow-redesign08'
PALETTE = {
    'fire': ((.42, .045, .006), (.95, .19, .022), (1, .59, .13)),
    'holy': ((.72, .40, .075), (1, .79, .38), (1, .93, .70)),
    'arcane': ((.23, .025, .42), (.62, .095, .94), (.92, .40, 1)),
    'poison': ((.045, .20, .012), (.30, .78, .035), (.66, 1, .18)),
    'ice': ((.025, .23, .46), (.10, .61, .94), (.64, .94, 1)),
}


def texture_path(key, part):
    return 'textures\\magicarrows\\redesign08\\facets.dds'


def write_textures():
    # Reuse the neutral shading atlas under a separate namespace.
    original_textures()
    dst = BUILD / STAGE / 'textures/magicarrows/redesign08/facets.dds'
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUILD / 'geometric-selected-05/data/textures/magicarrows/geometric05/facets.dds', dst)


def shader_values(key, part):
    dark, base, light = PALETTE[key]
    colors = dict(head=base, accent=base, shaft=base, tail=base, trim=dark, edge=light)
    if key == 'holy':
        colors.update(head=light, shaft=light, tail=light, accent=base, trim=base)
    if key == 'fire':
        colors['shaft'] = dark
    return colors[part], 1.80 if part == 'edge' else 1.65


def area2(points):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))


def turn(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def triangulate(points):
    """Ear clipping preserves concave flame notches and chevron recesses."""
    assert area2(points) > 0
    remaining = list(range(len(points)))
    triangles = []
    while len(remaining) > 3:
        for j, b in enumerate(remaining):
            a, c = remaining[j - 1], remaining[(j + 1) % len(remaining)]
            if turn(points[a], points[b], points[c]) <= 1e-10:
                continue
            inside = lambda p: all(turn(points[x], points[y], p) >= -1e-10
                                   for x, y in ((a, b), (b, c), (c, a)))
            if any(inside(points[i]) for i in remaining if i not in (a, b, c)):
                continue
            triangles.append((a, b, c))
            remaining.pop(j)
            break
        else:
            raise ValueError('Self-intersecting or degenerate profile')
    triangles.append(tuple(remaining))
    return triangles


def inset(points, distance):
    """Intersect inward-offset edges, preserving each original corner index."""
    result = []
    for j, b in enumerate(points):
        a, c = points[j - 1], points[(j + 1) % len(points)]
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = c[0] - b[0], c[1] - b[1]
        lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
        ux, uy, vx, vy = ux / lu, uy / lu, vx / lv, vy / lv
        p = (b[0] - uy * distance, b[1] + ux * distance)
        q = (b[0] - vy * distance, b[1] + vx * distance)
        determinant = ux * vy - uy * vx
        if abs(determinant) < 1e-8:
            result.append(p)
        else:
            t = ((q[0] - p[0]) * vy - (q[1] - p[1]) * vx) / determinant
            result.append((p[0] + t * ux, p[1] + t * uy))
    return result


def tip_scale(y):
    return max(.05, min(1, (y-.07)/2.5))


def prism(mesh, outline, depth=.42, phase=0, bevel=.055, taper_tip=False):
    """Closed beveled polygon prism, with correctly triangulated concave caps."""
    points = list(outline)
    if area2(points) < 0:
        points.reverse()
    inner = inset(points, bevel)
    caps = triangulate(inner)
    n = len(points)
    rings = ((inner, -depth), (points, -depth + bevel),
             (points, depth - bevel), (inner, depth))
    co, si = math.cos(phase), math.sin(phase)
    vertices = []
    for ring, z in rings:
        for x, y in ring:
            zz = z * tip_scale(y) if taper_tip else z
            vertices.append((x * co - zz * si, y, x * si + zz * co))
    faces = [tuple(reversed(t)) for t in caps] + [tuple(i + 3 * n for i in t) for t in caps]
    for k in range(3):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    mesh.append(vertices, faces)


def frame(mesh, outer, inner, depth=.24, phase=0):
    """A genuine open, closed-wall polygon frame; no alpha-cutout surface."""
    assert len(outer) == len(inner) and area2(outer) > 0 and area2(inner) > 0
    n = len(outer)
    co, si = math.cos(phase), math.sin(phase)
    vertices = [(x * co - z * si, y, x * si + z * co)
                for z in (-depth, depth) for ring in (outer, inner) for x, y in ring]
    faces = []
    for j in range(n):
        k = (j + 1) % n
        faces.extend(((j, k, k + 2*n, j + 2*n),
                      (j+n, j+3*n, k+3*n, k+n),
                      (j, j+n, k+n, k),
                      (j+2*n, k+2*n, k+3*n, j+3*n)))
    mesh.append(vertices, faces)


def profile_edge(mesh, points, depth=.42, phase=0, radius=.023, taper_tip=False):
    co, si = math.cos(phase), math.sin(phase)
    for z in (-depth, depth):
        ridge(mesh, [(x * co - z * (tip_scale(y) if taper_tip else 1) * si, y,
                      x * si + z * (tip_scale(y) if taper_tip else 1) * co) for x, y in points], radius)


def heads(key, p):
    head, accent, edge = p['head'], p['accent'], p['edge']
    if key == 'fire':
        outline = [(0, .07), (-.85, .85), (-1.60, 2.2), (-2.10, 3.9),
                   (-2.20, 5.5), (-1.72, 6.6), (-1.14, 6.05), (-.60, 7.0),
                   (-.25, 8.65), (0, 10.75), (.48, 10.15), (.97, 8.80),
                   (1.62, 7.6), (1.85, 6.25), (.89, 7.1), (.47, 6.68),
                   (.42, 5.65), (1.26, 4.85), (.62, 4.28), (.15, 3.5),
                   (-.12, 2.3), (-.18, 1.08)]
        # The small tip bevel shortens only the cap, never the outer silhouette.
        prism(head, outline, .50, bevel=.045, taper_tip=True)
        profile_edge(edge, outline[:6], .46, radius=.028, taper_tip=True)
        ridge(edge, [(-.04, .35, .52*tip_scale(.35)), (-.93, 3.3, .52),
                     (-.70, 6.0, .52), (.03, 10.5, .52)], .036)
        for y in (11.3, 12.6):
            prism(accent, [(0, y+1), (-.70, y-.20), (0, y+.22), (.70, y-.20)], .23, bevel=.035)
    elif key == 'holy':
        loft(head, [(.07, .025, .025, 0, 0, 0), (5.9, .83, .56, 0, 0, 0),
                    (8.3, .59, .44, 0, 0, 0), (10.8, .40, .40, 0, 0, 0)], 6)
        outer = [(2.25 * math.cos(i*math.tau/12), 6.60 + 2.25 * math.sin(i*math.tau/12)) for i in range(12)]
        inner = [(1.87 * math.cos(i*math.tau/12), 6.60 + 1.87 * math.sin(i*math.tau/12)) for i in range(12)]
        frame(accent, outer, inner, .26)
        prism(accent, [(-2.45, 6.25), (2.45, 6.25), (2.45, 6.90), (-2.45, 6.90)], .40)
        profile_edge(edge, [(-2.40, 6.25), (2.40, 6.25)], .41)
        ridge(edge, [(0, .15, .035), (0, 5.9, .57), (0, 8.3, .45), (0, 10.5, .41)], .025)
    elif key == 'arcane':
        bevel_square(head, [(.07, .025), (1.65, .44), (10.8, .34)])
        for y, w in ((1.85, .85), (4.05, 1.53), (6.25, 2.20)):
            outline = [(0, y), (w, y+1.22), (w, y+2.08),
                       (0, y+.82), (-w, y+2.08), (-w, y+1.22)]
            prism(accent, outline, .42)
            profile_edge(edge, [(-w, y+1.22), (0, y), (w, y+1.22)], .43)
        for sign in (-1, 1):
            outline = [(sign*.82, 8.85), (sign*1.77, 8.85), (sign*1.77, 9.27),
                       (sign*1.27, 9.27), (sign*1.27, 10.0), (sign*.55, 10.0),
                       (sign*.55, 9.60), (sign*.82, 9.60)]
            prism(p['trim'], outline, .40, bevel=.04)
    elif key == 'poison':
        # No centre spear: the shared root stops behind the entire open gap.
        collar(head, 10.60, .70, .65)
        for sign, delta in ((-1, 0), (1, .42)):
            samples = [(.07+delta, .70, .02, .025, 0), (1.8+delta, 1.25, .20, .20, 0),
                       (3.8, 1.85, .34, .34, 0), (5.9, 2.03, .46, .42, 0),
                       (7.8, 1.45, .46, .40, 0), (9.4, .62, .31, .27, 0),
                       (10.55, .30, .22, .22, 0)]
            rings = [(y, w, t, sign*r, 0, 0) for y, r, w, t, a in smooth_samples(samples, 3)]
            loft(accent, rings, 6)
            ridge(edge, [(sign*r, y, t*.98) for y, r, w, t, a in smooth_samples(samples, 3)], .026)
    else:
        rings = [(.07, .025, 0), (4.5, 1.12, 0), (8.25, .88, 0), (10.8, .40, 0)]
        axial(head, rings, 6)
        for sign, dy in ((-1, 0), (1, .55)):
            loft(accent, [(6.0+dy, .025, .025, sign*2.3, 0, 0),
                          (8.25+dy*.4, .45, .37, sign*1.3, 0, 0),
                          (10.55, .28, .28, sign*.40, 0, 0)], 6)
        for j in range(6):
            a = j*math.tau/6
            ridge(edge, [(r*math.cos(a), y, r*math.sin(a)) for y, r, t in rings], .022)


def shafts(key, p):
    shaft, edge, trim = p['shaft'], p['edge'], p['trim']
    if key == 'arcane':
        # Match radial envelope .40, including the beveled square corners.
        r = .40 / math.hypot(1, .72)
        bevel_square(shaft, [(10.5, r), (46.2, r), (57.25, r)])
        for y in (19.0, 31.0, 43.0):
            bevel_square(trim, [(y-.46, .38), (y-.30, .55), (y+.30, .55), (y+.46, .38)])
    else:
        axial(shaft, [(10.5, .40, 0), (46.2, .40, 0), (57.25, .40, 0)], 6 if key == 'ice' else 12)
        for y in (13.5, 45.8):
            collar(trim, y, .54, .55, 6 if key == 'ice' else 8)
    if key == 'poison':
        points = [(.43*math.cos(i*math.tau/24), 10.9+i*.11, .43*math.sin(i*math.tau/24)) for i in range(49)]
        ridge(p['accent'], points, .095)
    for phase in (0, math.pi):
        if key != 'arcane':
            ridge(edge, [(.394*math.cos(phase), y, .394*math.sin(phase)) for y in (13.7, 46.1, 57.15)], .025)


def tails(key, p):
    tail, edge = p['tail'], p['edge']
    if key == 'fire':
        outline = [(.28, 47.0), (1.10, 49.25), (2.15, 51.8), (2.50, 55.8),
                   (2.00, 54.85), (1.65, 53.15), (1.42, 53.7),
                   (1.33, 51.8), (.66, 50.10), (.28, 49.65)]
        for a in (0, math.tau/3, 2*math.tau/3):
            prism(tail, outline, .27, a, .045)
            profile_edge(edge, outline[:4], .28, a)
    elif key == 'holy':
        for a in (0, math.pi/2, math.pi, 3*math.pi/2):
            for y, w in ((49.4, 1.85), (52.9, 2.50)):
                outline = [(.29, y), (w, y+.80), (w, y+2.05), (.29, y+1.20)]
                prism(tail, outline, .27, a)
                profile_edge(edge, outline[:2], .28, a)
    elif key == 'arcane':
        outer = [(.28, 48.5), (2.45, 50.9), (2.45, 56.0), (.66, 54.35)]
        inner = [(.75, 50.0), (1.98, 51.40), (1.98, 54.80), (1.05, 53.85)]
        for a in (0, math.pi/2, math.pi, 3*math.pi/2):
            frame(tail, outer, inner, .26, a)
            profile_edge(edge, outer[:3], .27, a)
    elif key == 'poison':
        for a in (0, math.pi):
            samples = [(47.4, .31, .12, .12, 0), (49.6, 1.48, .32, .27, 0),
                       (52.2, 2.36, .35, .31, 0), (54.5, 1.80, .24, .24, 0),
                       (56.5, .88, .02, .025, 0)]
            rings = [(y, w, t, r*math.cos(a), r*math.sin(a), a)
                     for y, r, w, t, z in smooth_samples(samples, 3)]
            loft(tail, rings, 6)
            profile = [(r, y) for y, r, w, t, z in samples]
            profile_edge(edge, profile, .27, a)
    else:
        outline = [(.27, 47.8), (1.0, 48.7), (2.48, 51.35),
                   (2.48, 54.40), (1.86, 55.55), (.35, 54.35)]
        for a in (0, math.tau/3, 2*math.tau/3):
            prism(tail, outline, .36, a, .09)
            profile_edge(edge, outline[:4], .37, a)


def normalize(parts, names, low, high, target):
    vertices = [v for name in names for v in parts[name].verts if low <= v[1] <= high]
    scale = target / max(math.hypot(x, z) for x, y, z in vertices)
    for name in names:
        parts[name].verts = [(x*scale, y, z*scale) if low <= y <= high else (x, y, z)
                             for x, y, z in parts[name].verts]


def generate(key):
    if key not in KEYS:
        raise ValueError(key)
    parts = {name: Solid() for name in ('head', 'accent', 'edge', 'shaft', 'tail', 'trim')}
    heads(key, parts)
    tails(key, parts)
    normalize(parts, ('head', 'accent', 'edge'), 0, 10.9, 2.496)
    normalize(parts, ('tail', 'edge'), 46.5, 57.0, 2.685)
    shafts(key, parts)
    collar(parts['trim'], 10.7, .56, .55)
    collar(parts['trim'], 57.12, .50, .45)
    for x in (-.24, .24):
        parts['trim'].tube([(x, 57.15, 0), (x, 57.94, 0)], [.18, .12], 8)
    return parts


def audit_exported(key, nif):
    """Check the actual flight mesh: closed solids, dimensions and open gaps."""
    vertices = [v for shape in nif.shapes for v in shape.verts]
    head_radius = max(math.hypot(x, z) for x, y, z in vertices if y <= 10.9)
    tail_radius = max(math.hypot(x, z) for x, y, z in vertices if 46.5 <= y <= 57)
    shaft_radius = max(math.hypot(x, z) for shape in nif.shapes if shape.name.endswith('_shaft')
                       for x, y, z in shape.verts)
    for actual, expected in ((head_radius, 2.496), (tail_radius, 2.685), (shaft_radius, .40)):
        assert abs(actual-expected) < 1e-5, (key, actual, expected)
    body_vertices = [v for shape in nif.shapes if not shape.name.endswith('_edge') for v in shape.verts]
    assert abs(min(v[1] for v in body_vertices)-.07) < 1e-5
    assert abs(max(v[1] for v in vertices)-57.94) < 1e-5
    closed = 0
    for shape in nif.shapes:
        if shape.name.endswith('_edge'):
            continue  # Decorative seam tubes can intersect each other at junctions.
        points = [tuple(round(c, 6) for c in v) for v in shape.verts]
        edges, directions, volume = Counter(), Counter(), 0
        for tri in shape.tris:
            a, b, c = [points[i] for i in tri]
            volume += sum(x*y for x, y in zip(a, cross(b, c))) / 6
            for i, j in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                start, end = points[i], points[j]
                edges[tuple(sorted((start, end)))] += 1
                directions[(start, end)] += 1
        assert all(n == 2 for n in edges.values()), (key, shape.name, 'open/nonmanifold edge')
        assert all(directions[(a, b)] == directions[(b, a)] for a, b in edges), (key, shape.name, 'winding')
        assert volume > 0, (key, shape.name, 'inverted solid')
        closed += 1
    if key == 'poison':
        # An actual triangle crossing the centre axis may occur only at the root.
        for shape in nif.shapes:
            for tri in shape.tris:
                for i, j in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                    a, b = shape.verts[i], shape.verts[j]
                    if a[0]*b[0] < 0:
                        t = -a[0]/(b[0]-a[0])
                        assert a[1]+t*(b[1]-a[1]) >= 9.2, 'Poison central gap filled'
    if key in ('holy', 'arcane'):
        point = (1.2, 5.4) if key == 'holy' else (1.6, 52.8)
        suffixes = ('_head', '_accent') if key == 'holy' else ('_tail',)
        for shape in nif.shapes:
            if not shape.name.endswith(suffixes):
                continue
            for tri in shape.tris:
                a, b, c = [(shape.verts[i][0], shape.verts[i][1]) for i in tri]
                if abs(turn(a, b, c)) < 1e-8:
                    continue
                signs = [turn(x, y, point) for x, y in ((a, b), (b, c), (c, a))]
                assert not (min(signs) >= -1e-8 or max(signs) <= 1e-8), (key, 'Open frame hole filled')
    return dict(key=key, head_radius=head_radius, tail_radius=tail_radius,
                shaft_radius=shaft_radius, closed_solid_categories=closed,
                triangles=sum(len(s.tris) for s in nif.shapes))


if __name__ == '__main__':
    write_textures()
    for key in KEYS:
        parts = generate(key)
        print(key, sum(len(p.tris) for p in parts.values()), 'triangles')
