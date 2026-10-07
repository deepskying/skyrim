"""Closed loft/ribbon primitives and the current energy-model entry point.

Local tip Y=0, nock Y=58. Crystals have separated faces for split normals.
"""
import math

def loft(mesh, rings, sides=8, phase=0, flat=False):
    """Closed elliptical rings (y, rx, rz, cx, cz, twist), outward winding."""
    vs, faces = [], []
    for y, rx, rz, cx, cz, twist in rings:
        for j in range(sides):
            a = math.tau*j/sides + phase
            x,z = rx*math.cos(a),rz*math.sin(a)
            vs.append((cx+x*math.cos(twist)-z*math.sin(twist),y,
                       cz+x*math.sin(twist)+z*math.cos(twist)))
    for k in range(len(rings)-1):
        for j in range(sides):
            a=k*sides+j; b=k*sides+(j+1)%sides
            faces.append((b,a,a+sides,b+sides))
    faces += [tuple(range(sides)),
              tuple((len(rings)-1)*sides+j for j in range(sides-1,-1,-1))]
    if flat:
        # Separate faces preserve the intentionally cut crystal/stone facets.
        for face in faces: mesh.append([vs[i] for i in face],[tuple(range(len(face)))])
    else: mesh.append(vs,faces)

def crystal(mesh, tip=0, root=10, width=1.65, depth=.85, x=0, z=0, twist=0):
    loft(mesh,[(tip,.025,.025,x,z,twist),
               (tip+(root-tip)*.62,width,depth,x,z,twist+.12),
               (tip+(root-tip)*.83,width*.72,depth*.83,x,z,twist-.08),
               (root,.22,.20,x,z,twist)],6,math.pi/6,True)

def smooth_samples(samples, steps=5):
    """Interpolate cross-sections without changing longitudinal bounds."""
    result=[]
    for i in range(len(samples)-1):
        a=samples[max(0,i-1)];b=samples[i];c=samples[i+1];d=samples[min(i+2,len(samples)-1)]
        for j in range(steps):
            t=j/steps
            values=[b[0]+(c[0]-b[0])*t]
            for k in range(1,5):
                value=.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t)
                values.append(max(.015,value) if k in (2,3) else value)
            result.append(tuple(values))
    return result+[samples[-1]]

def ribbon(mesh, samples, phase=0):
    """Closed sculpted ribbon: (y, radial distance, width, thickness, twist).

    Width lies in the radial plane; thickness follows its angular tangent.
    A raised centre ridge supplies volume, rather than a paper-flat outline.
    """
    rings=[]
    for y,r,w,t,a in smooth_samples(samples):
        a+=phase
        rings.append((y,w,t,r*math.cos(a),r*math.sin(a),a))
    loft(mesh,rings,4,math.pi/4)


def redesigned(key):
    if key in ('fire','holy','arcane','poison','ice'):
        from five_arrow_redesign import generate
    elif key=='blood':
        from energy_geometry import redesigned as generate
    else:
        from luminous_v4 import generate
    return generate(key)
