"""Two authored component samples. Closed volume, real holes, textured emission.

These are separate review assets; they do not replace the installed V3 set.
"""
import math
from geometry import Mesh,cross,sub,norm

KEYS=('ice','holy')
VERSION='0.1.0'

class Surface(Mesh):
    """Per-face split normals and a 4x4 directional-shading texture atlas."""
    def __init__(self,part):
        super().__init__();self.part=part
    def append(self,verts,faces):
        for face in faces:
            vs=[verts[i] for i in face]
            normal=norm(cross(sub(vs[1],vs[0]),sub(vs[2],vs[0])))
            # Symmetric transverse key light, baked for robust emissive depth.
            shade=.38+.62*abs(normal[2])+.08*abs(normal[0])
            tile=min(15,max(0,round((shade-.35)/.7*15)))
            tx,ty=tile%4,tile//4
            start=len(self.verts);self.verts.extend(vs)
            y0,y1={'head':(0,12),'tail':(46,58),'shaft':(12,47),'trim':(0,58),'edge':(0,58)}[self.part]
            axis=0 if max(v[0] for v in vs)-min(v[0] for v in vs)>max(v[2] for v in vs)-min(v[2] for v in vs) else 2
            for x,y,z in vs:
                u=max(.005,min(.995,(x if axis==0 else z)/6+.5))
                v=max(.005,min(.995,(y-y0)/(y1-y0)))
                if abs(normal[1])>.95:u=x/6+.5;v=z/6+.5
                self.uv.append(((tx+.02+.96*u)/4,(ty+.02+.96*v)/4))
            for j in range(1,len(vs)-1):self.tris.append((start,start+j,start+j+1))

def section(mesh,rings,sides=8,phase=0):
    vs=[];fs=[]
    for y,rx,rz,x,z,twist in rings:
        for j in range(sides):
            a=math.tau*j/sides+phase
            # Facets form discrete material planes, not intersecting blades.
            px,pz=rx*math.cos(a),rz*math.sin(a)
            vs.append((x+px*math.cos(twist)-pz*math.sin(twist),y,
                       z+px*math.sin(twist)+pz*math.cos(twist)))
    for k in range(len(rings)-1):
        for j in range(sides):
            a=k*sides+j;b=k*sides+(j+1)%sides
            fs.append((b,a,a+sides,b+sides))
    fs+=[tuple(range(sides)),tuple((len(rings)-1)*sides+j for j in range(sides-1,-1,-1))]
    mesh.append(vs,fs)

def rotate(point,a):
    x,y,z=point
    return (x*math.cos(a)-z*math.sin(a),y,x*math.sin(a)+z*math.cos(a))

def polygon_triangles(poly):
    """Ear clipping, preserving concave stepped crystal outlines."""
    area=sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))
    indices=list(range(len(poly))) if area>0 else list(reversed(range(len(poly))))
    triangles=[]
    def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    while len(indices)>3:
        for j in range(len(indices)):
            a,b,c=indices[j-1],indices[j],indices[(j+1)%len(indices)]
            if orient(poly[a],poly[b],poly[c])<=1e-9:continue
            if any(orient(poly[a],poly[b],poly[k])>=-1e-9 and orient(poly[b],poly[c],poly[k])>=-1e-9 and orient(poly[c],poly[a],poly[k])>=-1e-9 for k in indices if k not in (a,b,c)):continue
            triangles.append((a,b,c));indices.pop(j);break
        else:raise ValueError('Invalid component outline')
    return triangles+[tuple(indices)]

def beveled_plate(mesh,outline,phase=0,thickness=.10):
    triangles=polygon_triangles(outline)
    cx=sum(x for x,y in outline)/len(outline);cy=sum(y for x,y in outline)/len(outline)
    n=len(outline);vs=[]
    for scale,z in ((1,-thickness*.40),(.96,-thickness),(1,thickness*.40),(.96,thickness)):
        vs.extend(rotate((cx+(x-cx)*scale,cy+(y-cy)*scale,z),phase) for x,y in outline)
    fs=[]
    for a,b,c in triangles:fs.extend(((n+c,n+b,n+a),(3*n+a,3*n+b,3*n+c)))
    for j in range(n):
        k=(j+1)%n
        fs.extend(((j,k,n+k,n+j),(2*n+k,2*n+j,3*n+j,3*n+k),(j,2*n+j,2*n+k,k)))
    mesh.append(vs,fs)

def petal(mesh,edge,y0,y1,phase,width,bend,thickness=.10):
    """Annular lens-shaped petal with an actual open almond through-hole."""
    n=64;outer=[];inner=[]
    for j in range(n):
        a=math.tau*j/n
        y=(y0+y1)/2+(y1-y0)/2*math.cos(a)
        t=(y-y0)/(y1-y0)
        x=.22+bend*math.sin(math.pi*t)+width*math.sin(a)
        outer.append((x,y))
        yi=(y0+y1)/2+(y1-y0)*.32*math.cos(a)
        ti=(yi-y0)/(y1-y0)
        xi=.22+bend*math.sin(math.pi*ti)+width*.40*math.sin(a)
        inner.append((xi,yi))
    vs=[]
    # Top and bottom annular surfaces bow gently in three dimensions.
    for curve,z in ((outer,-thickness*.45),(inner,-thickness),
                    (outer,thickness*.45),(inner,thickness)):
        for x,y in curve:
            u=(y-y0)/(y1-y0)
            vs.append(rotate((x,y,z+.12*math.sin(math.pi*u)),phase))
    fs=[]
    for j in range(n):
        k=(j+1)%n
        fs.extend(((j,k,n+k,n+j),(2*n+k,2*n+j,3*n+j,3*n+k),
                   (k,j,2*n+j,2*n+k),(n+j,n+k,3*n+k,3*n+j)))
    mesh.append(vs,fs)
    # Highlight the perimeter without filling the negative space.
    for curve in (outer,inner):
        pts=[rotate((x,y,thickness+.12*math.sin(math.pi*(y-y0)/(y1-y0))),phase) for x,y in curve]
        edge.tube(pts+[pts[0]],.014,5)

def collar(trim,edge,y,key):
    for dy,r in ((-.38,.42),(-.25,.51),(.25,.51),(.38,.42)):
        trim.tube([(0,y+dy-.035,0),(0,y+dy+.035,0)],r,20)
    trim.tube([(0,y-.25,0),(0,y+.25,0)],.45,20)
    for j in range(12):
        a=math.tau*j/12
        pts=[rotate((.48,y-.20,0),a),rotate((.54,y,0),a+.045),rotate((.48,y+.20,0),a)]
        edge.tube(pts,.018,5)
    if key=='holy':
        # Small modeled sunburst on the outward collar face.
        for j in range(12):
            a=math.tau*j/12
            trim.tube([(.12*math.cos(a),y+.12*math.sin(a),.47),
                       (.26*math.cos(a),y+.26*math.sin(a),.48)],.017,5)

def generate(key):
    if key not in KEYS:raise ValueError(key)
    parts={k:Surface(k) for k in ('shaft','head','tail','trim','edge')}
    shaft,head,tail,trim,edge=(parts[k] for k in parts)
    shaft.tube([(0,11.4,0),(0,57.55,0)],.27,12 if key=='ice' else 20)
    collar(trim,edge,11.7,key);collar(trim,edge,47.3,key)
    trim.tube([(0,56.6,0),(0,57.35,0)],[.29,.22],16)
    # Two physically separated string-notch prongs at the nock.
    for x in (-.14,.14):trim.tube([(x,57.15,0),(x,57.95,0)],[.10,.07],10)
    if key=='ice':
        section(head,[(.04,.025,.025,0,0,0),(2.5,.40,.24,.04,0,.03),
                      (5.4,.93,.55,-.05,0,.04),(7.8,1.23,.70,.07,0,-.03),
                      (9.5,.87,.54,0,0,0),(11.1,.30,.28,0,0,0)],8,.18)
        for phase,tip in ((0,4.5),(math.pi,5.5),(math.pi/2,7.1)):
            rings=[(tip,.025,.025,1.48,0,.10),(8.7,.40,.27,1.08,0,.15),(11,.16,.15,.30,0,.05)]
            # Rotate the off-axis centres and cross-section orientation together.
            transformed=[]
            for y,rx,rz,x,z,a in rings:
                px,py,pz=rotate((x,y,z),phase);transformed.append((py,rx,rz,px,pz,a+phase))
            section(head,transformed,6,.15)
        outline=[(.30,48.1),(.86,49.2),(1.66,51.0),(2.72,54.3),
                 (1.76,53.8),(2.42,55.6),(1.18,54.9),(.38,56.6)]
        for phase in (0,math.tau/3,2*math.tau/3):
            beveled_plate(tail,outline,phase,.13)
            pts=[rotate((x,y,.15),phase) for x,y in outline]
            edge.tube(pts+[pts[0]],.014,5)
        # Fine icy longitudinal seam, no repeated helix.
        edge.tube([(.15,12,.235),(.12,22,.25),(.18,32,.22),(.12,46,.25)],.015,5)
    else:
        # The accepted pointed luminous core, three pierced swept petals.
        section(head,[(.04,.025,.025,0,0,0),(3.7,.42,.34,0,0,0),
                      (7.6,.30,.29,0,0,.10),(11,.24,.23,0,0,0)],8,.12)
        for phase,offset in ((0,0),(math.tau/3,.45),(2*math.tau/3,.15)):
            petal(head,edge,2.1+offset,10.8,phase,.70,1.32,.14)
            petal(tail,edge,48.1,56.5-offset,phase,.73,1.57,.12)
        # Three straight flutes and five tiny surface lozenges on the shaft.
        for phase in (0,math.tau/3,2*math.tau/3):
            edge.tube([rotate((.29,12.3,0),phase),rotate((.29,46.5,0),phase)],.016,5)
        for y in (18,24,30,36,42):
            beveled_plate(trim,[(-.11,y),(.0,y-.35),(.11,y),(.0,y+.35)],0,.29)
    return parts

def texture_path(key,part):
    return 'textures\\magicarrows\\precision01\\'+key+'_'+part+'.dds'

def shader_values(key,part):
    if part=='edge':return ((.60,.82,1) if key=='ice' else (1,.84,.40)),1.70
    return (1,1,1),1.40
