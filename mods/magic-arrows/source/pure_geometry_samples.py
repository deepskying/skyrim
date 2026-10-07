"""Build the approved plain-color faceted ice/holy concepts, without textures."""
import math
from geometry import Mesh,cross,sub,norm
from precision_samples import section,beveled_plate,rotate
KEYS=('ice','holy')
VERSION='0.2.0'

class Planes(Mesh):
    """Split actual faces into uniform-color materials for emissive facet depth."""
    def __init__(self,part,parts):super().__init__();self.part=part;self.parts=parts
    def append(self,verts,faces):
        for face in faces:
            vs=[verts[i] for i in face]
            normal=norm(cross(sub(vs[1],vs[0]),sub(vs[2],vs[0])))
            value=.20+.50*abs(normal[2])+.28*normal[0]
            band='bright' if value>.67 else 'mid' if value>.39 else 'shade'
            key=self.part+'_'+band
            self.parts.setdefault(key,Mesh()).append(vs,[tuple(range(len(vs)))])

def generate(key):
    if key not in KEYS:raise ValueError(key)
    parts={};shaft,head,tail,trim,edge=[Planes(p,parts) for p in ('shaft','head','tail','trim','edge')]
    shaft.tube([(0,9.5,0),(0,57,0)],.24,6 if key=='ice' else 8)
    # Two broad beveled polygonal collars; no fine rings or filigree.
    for y in (9.7,48.3):
        section(trim,[(y-.45,.33,.33,0,0,0),(y-.27,.46,.46,0,0,0),
                      (y+.27,.46,.46,0,0,0),(y+.45,.33,.33,0,0,0)],6 if key=='ice' else 8,.15)
    trim.tube([(0,56.65,0),(0,57.30,0)],[.33,.29],6 if key=='ice' else 8)
    for x in (-.18,.18):
        trim.tube([(x,57.2,0),(x,57.95,0)],[.12,.10],4,)
    # A physical narrow longitudinal rail, not a painted line.
    edge.tube([(0,10.2,.235),(0,48,.235)],.045,4)
    if key=='ice':
        section(head,[(.04,.018,.018,0,0,0),(4.0,.90,.53,0,0,0),
                      (7.2,.52,.38,0,0,0),(9.55,.27,.27,0,0,0)],6,.12)
        for sign,tip in ((1,2.9),(-1,4.0)):
            section(head,[(tip,.018,.018,sign*1.25,0,0),
                          (tip+1.8,.30,.23,sign*1.06,0,0),
                          (9.55,.16,.16,sign*.29,0,0)],6,.12)
        outline=[(.26,48.75),(2.35,54.7),(1.45,55.2),(1.19,54.7),(.73,56.5),(.26,56.5)]
    else:
        section(head,[(.04,.018,.018,0,0,0),(4.2,.94,.47,0,0,0),
                      (8.6,.40,.27,0,0,0),(9.55,.26,.25,0,0,0)],4,0)
        for sign,dy in ((1,0),(-1,.6)):
            outline_guard=[(sign*.29,9.5),(sign*.82,8.4),
                           (sign*1.38,6.1+dy),(sign*1.52,3.7+dy),(sign*.88,5.4+dy)]
            beveled_plate(trim,outline_guard,0,.17)
        outline=[(.26,48.75),(2.30,54.9),(1.64,56.3),(.65,55.8),(.26,56.5)]
    for phase in (0,math.tau/3,2*math.tau/3):
        beveled_plate(tail,outline,phase,.12)
        if key=='holy':
            # Gold edging is a thick polygon extrusion under the ivory vane.
            cx=sum(x for x,y in outline)/len(outline);cy=sum(y for x,y in outline)/len(outline)
            border=[(cx+(x-cx)*1.045,cy+(y-cy)*1.015) for x,y in outline]
            beveled_plate(trim,border,phase,.085)
    return {k:v for k,v in parts.items() if v.tris}

def texture_path(key,part):return 'textures\\magicarrows\\solid.dds'
def shader_values(key,part):
    category,band=part.rsplit('_',1)
    palette={'ice':{'shaft':(.08,.29,.48),'head':(.14,.46,.70),'tail':(.12,.42,.65),
                    'trim':(.38,.46,.53),'edge':(.18,.70,.90)},
             'holy':{'shaft':(.45,.42,.30),'head':(.62,.56,.41),'tail':(.60,.54,.40),
                     'trim':(.62,.36,.08),'edge':(.85,.53,.16)}}
    shade={'bright':1,'mid':.76,'shade':.51}[band]
    return tuple(c*shade for c in palette[key][category]),1.75 if category=='edge' else 1.4
