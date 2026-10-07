"""Selected concept A: cyan thunder crystal, graphite shaft and metal fins."""
import math,shutil
from geometric_selected import Solid
from geometric_round03 import axial,collar,ridge
from five_arrow_redesign import prism,profile_edge,normalize,audit_exported,write_textures as atlas,tip_scale
from paths import BUILD
VERSION='0.9.2'
KEYS=REMAINING=('shock',)
LABELS={'shock':'雷棱箭 · 青蓝雷晶'}
STAGE='shock-arrow-redesign092/data'
ART='shock-arrow-redesign092'

def texture_path(key,part):return 'textures\\magicarrows\\shock09\\facets.dds'
def write_textures():
    atlas()
    dst=BUILD/STAGE/'textures/magicarrows/shock09/facets.dds'
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BUILD/'five-arrow-redesign08/data/textures/magicarrows/redesign08/facets.dds',dst)

def shader_values(key,part):
    colors={'head':(.045,.68,.91),'accent':(.035,.045,.060),'edge':(.38,.94,1),
            'shaft':(.018,.025,.035),'tail':(.028,.038,.052),'trim':(.070,.085,.105)}
    return colors[part],1.85 if part in ('head','edge') else 1.35

def generate(key):
    assert key=='shock'
    p={name:Solid() for name in ('head','accent','edge','shaft','tail','trim')}
    # The notched crystal is a closed, thick, bevelled solid, not an alpha card.
    crystal=[(0,.07),(1.18,2.7),(.69,2.55),(2.13,5.4),(1.27,8.5),
             (-.78,8.7),(-1.65,6.25),(-.92,6.45),(-1.86,4.2)]
    prism(p['head'],crystal,.58,bevel=.20,taper_tip=True)
    # Raise each cap triangle into a shallow crystal facet, preserving shared edges.
    faces=[]
    crystal_mesh=p['head']
    for tri in crystal_mesh.tris:
        points=[crystal_mesh.verts[i] for i in tri]
        sign=1 if points[0][2]>0 else -1
        is_cap=all(abs(z-sign*.58*tip_scale(y))<1e-7 for x,y,z in points)
        if is_cap:
            centre=tuple(sum(v[k] for v in points)/3 for k in range(3))
            x,y,z=centre
            idx=len(crystal_mesh.verts)
            crystal_mesh.verts.append((x,y,z+sign*.16*tip_scale(y)))
            a,b,c=tri
            faces.extend(((a,b,idx),(b,c,idx),(c,a,idx)))
        else:faces.append(tri)
    crystal_mesh.tris=faces
    # Narrow luminous ridges reinforce the long facets of the crystal.
    ridge(p['edge'],[(0,.18,.045),(.20,3.5,.60),(.12,6.0,.60),(0,8.45,.60)],.024)
    # Two dark steel clamps grip the crystal root without replacing its silhouette.
    clamp=[(.52,7.8),(1.72,7.1),(2.3,8.35),(1.2,9.65),(.48,9.7)]
    for sign in (-1,1):
        prism(p['accent'],[(sign*x,y) for x,y in clamp],.40,bevel=.07)
    axial(p['trim'],[(8.9,.63,0),(9.7,.70,0),(10.8,.46,0)],6)
    normalize(p,('head','accent','edge','trim'),0,10.9,2.496)
    # Three compact triangular steel fins, with cyan only on their outer edges.
    tail=[(.39,47.5),(2.55,54.9),(.39,54.9)]
    for phase in (0,math.tau/3,math.tau*2/3):
        prism(p['tail'],tail,.13,phase=phase,bevel=.045)
        profile_edge(p['edge'],tail[:2],.135,phase=phase,radius=.027)
    normalize(p,('tail','edge'),46.5,57,2.685)
    axial(p['shaft'],[(10.5,.40,0),(46.2,.40,0),(57.25,.40,0)],6)
    for y in (11.2,12.0,46.2,55.6,57.12):collar(p['trim'],y,.49,.38,6)
    for y in (12.0,55.6):collar(p['edge'],y,.50,.085,6)
    # Two sparse, physically raised lightning inlays along the shaft.
    for start in (19,36):
        for sign in (-1,1):
            ridge(p['edge'],[(sign*x,start+dy,.365) for x,dy in
                 ((-.18,0),(.18,1.0),(-.16,1.25),(.16,2.4))],.026)
    for x in (-.24,.24):p['trim'].tube([(x,57.15,0),(x,57.94,0)],[.18,.12],8)
    return p

if __name__=='__main__':write_textures()
