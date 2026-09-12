"""Original solid-light arrow geometry. Tip is Y=0, nock Y=58, vanilla scale."""
import math

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return mul(a,1/max(1e-9,math.sqrt(sum(x*x for x in a))))

class Mesh:
    def __init__(self):self.verts=[];self.tris=[];self.uv=[]
    def append(self,verts,faces):
        off=len(self.verts);self.verts.extend(verts)
        self.uv.extend([(.5,.5)]*len(verts))
        for face in faces:
            for j in range(1,len(face)-1):self.tris.append(tuple(off+i for i in (face[0],face[j],face[j+1])))
    def tube(self,points,radius,sides=6):
        if not isinstance(radius,list):radius=[radius]*len(points)
        verts=[];faces=[]
        for i,p in enumerate(points):
            t=norm(sub(points[min(i+1,len(points)-1)],points[max(i-1,0)]))
            a=norm(cross(t,(0,0,1) if abs(t[2])<.9 else (1,0,0)));b=cross(t,a)
            for j in range(sides):
                angle=math.tau*j/sides;verts.append(add(p,add(mul(a,math.cos(angle)*radius[i]),mul(b,math.sin(angle)*radius[i]))))
            if i:
                for j in range(sides):
                    q=(i-1)*sides+j;r=(i-1)*sides+(j+1)%sides
                    faces.append((q,r,r+sides,q+sides))
        faces += [tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+j for j in range(sides))]
        self.append(verts,faces)
    def blade(self,outline,angle=0,thick=.13):
        n=len(outline);vs=[]
        for z in (-thick,thick):
            for x,y in outline:vs.append((x*math.cos(angle)-z*math.sin(angle),y,x*math.sin(angle)+z*math.cos(angle)))
        # All outlines are triangulated as a fan around an explicit interior ridge.
        cx=sum(v[0] for v in outline)/n;cy=sum(v[1] for v in outline)/n
        vs += [(cx*math.cos(angle)+thick*2*math.sin(angle),cy,cx*math.sin(angle)-thick*2*math.cos(angle)),(cx*math.cos(angle)-thick*2*math.sin(angle),cy,cx*math.sin(angle)+thick*2*math.cos(angle))]
        fs=[]
        for i in range(n):
            j=(i+1)%n;fs.extend([(j,i,2*n),(i+n,j+n,2*n+1),(i,j,j+n,i+n)])
        self.append(vs,fs)
    def normals(self):
        ns=[(0,0,0)]*len(self.verts)
        for a,b,c in self.tris:
            n=cross(sub(self.verts[b],self.verts[a]),sub(self.verts[c],self.verts[a]))
            for i in (a,b,c):ns[i]=add(ns[i],n)
        return [norm(n) for n in ns]

def generate(key):
    parts={k:Mesh() for k in ('body','core','aura')}
    body,core,aura=[parts[k] for k in ('body','core','aura')]
    body.tube([(0,9,0),(0,57.8,0)],.40,8)
    core.tube([(0,.3,0),(0,58,0)],.12,6)
    aura.tube([(0,10,0),(0,57.6,0)],.46,8)
    if key=='blood':
        # A central spear and two separate backswept barbs keep silhouettes manifold.
        for a in (0,math.pi/2):
            body.blade([(0,0),(1.35,7),(0,9.8),(-1.35,7)],a)
            for s in (-1,1):
                body.blade([(s*.55,4.6),(s*2.45,11),(s*1.45,8.9)],a,.08)
                core.tube([(0,.5,0),(s*1.15*math.cos(a),6.8,s*1.15*math.sin(a)),(s*2.45*math.cos(a),11,s*2.45*math.sin(a))],.048)
        for phase in (0,math.tau/3,math.tau*2/3):
            pts=[(.46*math.cos(t*math.tau*4+phase),10+47*t,.46*math.sin(t*math.tau*4+phase)) for t in [i/100 for i in range(101)]]
            core.tube(pts,.04,5)
    elif key=='holy':
        for a in (0,math.pi/2):
            body.blade([(0,0),(1.05,6),(0,10),(-1.05,6)],a)
            for s in (-1,1):
                body.blade([(s*.5,4),(s*3,10),(s*.6,8)],a,.09)
                core.tube([(0,.2,0),(s*3*math.cos(a),10,s*3*math.sin(a))],.06)
        ring=[(2*math.cos(t),11.2,2*math.sin(t)) for t in [i*math.tau/64 for i in range(65)]]
        core.tube(ring,.10,6);aura.tube(ring,.26,6)
    else:
        # A long crystal point with short radial star rays, all solid light.
        # Two perpendicular planes keep the star silhouette readable when nocked.
        for a in (0,math.pi/2):
            body.blade([(0,0),(1.05,6),(0,10.5),(-1.05,6)],a,.18)
            core.blade([(0,.08),(.43,2.9),(0,4.4),(-.43,2.9)],a,.20)
            for side in (-1,1):
                body.blade([(side*.45,4.8),(side*3.0,6.0),(side*.55,7.5),(side*.25,6.0)],a,.16)
                core.blade([(side*1.6,5.85),(side*2.98,6.0),(side*1.6,6.23)],a,.18)
    # Energy vanes; no physical feathers. Slightly different silhouettes per family.
    for a in (0,math.tau/3,math.tau*2/3):
        outline={'blood':[(.18,46),(2.3,54.5),(.15,57),(1.0,52)],'holy':[(.15,45.5),(2.35,51.5),(1.6,56),(.15,57)],'soul':[(.15,50),(1.85,52.8),(.15,56),(-.12,52.8)]}[key]
        outline=[(x*1.15,y) for x,y in outline]
        # Split into convex triangles for the concave blood vane.
        if key=='blood':
            body.blade([outline[0],outline[1],outline[3]],a,.12)
            body.blade([outline[1],outline[2],outline[3]],a,.12)
        else:body.blade(outline,a,.12)
        pts=[(x*math.cos(a),y,x*math.sin(a)) for x,y in outline]
        core.tube(pts+[pts[0]],.04,5)
    return parts
