"""Append bounded native draw particles, attached to six animated limb locations.

Run in Blender for matrix math. Particle layouts are also verified using native
nifly's independent read/write implementation before distribution.
"""
from pathlib import Path
import sys,struct,math,json,hashlib
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
SERIES='swords' if '--swords' in sys.argv else 'greatswords3' if '--greatswords3' in sys.argv else 'greatswords2' if '--greatswords2' in sys.argv else 'greatswords' if '--greatswords' in sys.argv else 'heteromorphic2' if '--heteromorphic2' in sys.argv else 'crystal' if '--crystal' in sys.argv else 'heteromorphic' if '--heteromorphic' in sys.argv else 'scorpio' if '--scorpio' in sys.argv else 'pisces' if '--pisces' in sys.argv else 'aquarius' if '--aquarius' in sys.argv else 'capricorn' if '--capricorn' in sys.argv else 'sagittarius' if '--sagittarius' in sys.argv else 'libra' if '--libra' in sys.argv else 'virgo' if '--virgo' in sys.argv else 'leo' if '--leo' in sys.argv else 'cancer' if '--cancer' in sys.argv else 'gemini' if '--gemini' in sys.argv else 'geometric' if '--geometric' in sys.argv else 'taurus' if '--taurus' in sys.argv else 'aries'
from nif_blocks import NifBlocks
from bsa_reference import extract
p=lambda fmt,*v:struct.pack('<'+fmt,*v)
u=lambda b,o=0:struct.unpack_from('<I',b,o)[0]
def patch(b,offset,fmt,*values):struct.pack_into('<'+fmt,b,offset,*values)
TEMPLATE=ROOT/'build/fxsparkfountain.nif'
if not TEMPLATE.is_file():TEMPLATE.write_bytes(extract(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data\Skyrim - Meshes0.bsa','meshes/effects/fxsparkfountain.nif'))
src=NifBlocks(TEMPLATE)
selected=[3,4,5,6,7,8,9,11,12,13,15,17,21,22]
expected=['NiNode','NiPSysData','NiParticleSystem','NiPSysEmitterCtlr','NiPSysUpdateCtlr','NiFloatInterpolator','NiBoolInterpolator','BSEffectShaderProperty','NiAlphaProperty','NiPSysAgeDeathModifier','NiPSysBoxEmitter','BSPSysSimpleColorModifier','NiPSysPositionModifier','NiPSysBoundUpdateModifier']
assert [src.blocks[i][0] for i in selected]==expected

def sprite(style):
    size=128;rgba=bytearray()
    for y in range(size):
        for x in range(size):
            dx=((x%32)+.5-16)/15;dy=((y%32)+.5-16)/15
            if style=='hollowsquare':
                a=max(0,1-abs(max(abs(dx),abs(dy))-.58)*14)
            elif style=='oval':
                a=max(0,1-abs(math.hypot(dx*1.4,dy)-.60)*13)
            elif style=='hollowdiamond':
                a=max(0,1-abs(abs(dx)*1.4+abs(dy)-.72)*13)
            elif style=='ring':
                a=max(0,1-abs(math.hypot(dx,dy)-.57)*13)
            elif style=='droplet':
                # Rounded base with a tapered upper point, in the existing 4x4 atlas.
                width=.58*max(0,1-(dy+.65)/1.5) if dy>-.30 else math.sqrt(max(0,.40**2-(dy+.30)**2))
                a=max(0,min(1,(width-abs(dx))*13))*max(0,min(1,(.85-dy)*12))
            elif style=='hollowtriangle':
                distance=max(-dy, .8660254*abs(dx)+.5*dy)
                a=max(0,1-abs(distance-.40)*14)
            elif style=='chevron':
                a=max(0,1-abs(dy-(abs(dx)*.95-.42))*10)*max(0,min(1,(.80-abs(dx))*8))
            elif style=='crescent':
                outer=max(0,min(1,(.78-math.hypot(dx,dy))*10))
                hole=max(0,min(1,(math.hypot(dx-.30,dy-.08)-.69)*10))
                a=outer*hole
            elif style=='kite':
                distance=abs(dx)*1.4+(dy*1.25 if dy>0 else -dy*.9)
                a=max(0,1-abs(distance-.72)*12)
            elif style=='hexagon':
                distance=max(abs(dy),.8660254*abs(dx)+.5*abs(dy))
                a=max(0,1-abs(distance-.65)*10)
            elif style=='needle':a=max(0,min((.9-dy)*2,(dy+1)*.20-abs(dx))*8)
            elif style=='triangle':a=min(1,max(0,min((.8-dy)*2,(dy+1)*.55-abs(dx))*5))
            elif style=='square':a=min(1,max(0,1-max(abs(dx),abs(dy)))*3)**.8
            elif style=='streak':a=min(1,max(0,1-abs(dx)*5-abs(dy))**1.2/(.8**1.2))
            elif style in ('mote','pearl'):
                a=max(0,1-math.hypot(dx,dy))**2
                if style=='pearl':a=max(a,.5*max(0,1-min(abs(dx),abs(dy))*14-max(abs(dx),abs(dy))))
            elif style=='flake':a=max(0,1-min(abs(dx),abs(dy),abs(dx-dy)*.7,abs(dx+dy)*.7)*10-max(abs(dx),abs(dy)))
            elif style=='shadow':a=min(1,max(0,(1-abs(dx)-abs(dy))*6))*.86
            elif style=='embers':a=max(0,1-abs(dx)*1.7-abs(dy))**1.3
            else:a=max(0,1-abs(dx)-abs(dy))**.8
            # A larger opaque core survives bright interiors and strong ENB bloom.
            if style!='shadow':a=min(1,a*1.6)
            rgba+=bytes((255,255,255,round(255*a)))
    header=p('7I',124,0x100f,size,size,size*4,0,1)+p('11I',*([0]*11))
    header+=p('8I',32,0x41,0,32,0xff0000,0xff00,0xff,0xff000000)+p('5I',0x1000,0,0,0,0)
    prefix='aa_geo_' if style in ('hexagon','needle','streak') and SERIES in ('swords','greatswords3','greatswords2','greatswords','geometric','leo','virgo','libra','sagittarius','capricorn','aquarius','pisces','scorpio','crystal','heteromorphic2','heteromorphic') else 'aa_aries_'
    if style=='kite':prefix='aa_virgo_'
    if style in ('chevron','crescent'):prefix='aa_sagittarius_'
    if style in ('droplet','hollowtriangle'):prefix='aa_capricorn_'
    if style=='ring':prefix='aa_aquarius_'
    if style in ('oval','hollowdiamond'):prefix='aa_pisces_'
    if style=='hollowsquare':prefix='aa_scorpio_'
    dest=ROOT/'data/textures/weapons/arcanearsenal'/(prefix+style+'.dds')
    dest.write_bytes(b'DDS '+header+rgba);return dest

def build(spec):
    key=spec['key'];n=NifBlocks(ROOT/'build'/(SERIES+'-base')/(key+'.nif'));original=list(n.blocks)
    model=json.loads((ROOT/'build'/(key+'-model.json')).read_text(encoding='utf-8'))
    texture=sprite(spec['fx']);textures=[texture]
    if spec.get('fx_secondary'):textures.append(sprite(spec['fx_secondary']))
    parents={};world={}
    def matrix(blob):
        offset=4*u(blob,4);r=struct.unpack_from('<9f',blob,28+offset)
        m=Matrix([r[j:j+3] for j in (0,3,6)]).to_4x4()
        scale=struct.unpack_from('<f',blob,64+offset)[0]
        for i in range(3):
            for j in range(3):m[i][j]*=scale
        m.translation=Vector(struct.unpack_from('<3f',blob,16+offset));return m
    for i,(kind,b) in enumerate(n.blocks):
        if kind not in ('NiNode','BSFadeNode'):continue
        offset=4*u(b,4)
        for child in struct.unpack_from('<'+'I'*u(b,72+offset),b,76+offset):parents[child]=i
    def global_matrix(index):
        if index not in world:
            m=matrix(n.blocks[index][1]);world[index]=global_matrix(parents[index])@m if index in parents else m
        return world[index]
    def children(index,extra):
        kind,b=n.blocks[index];assert kind=='NiNode' and u(b,4)==0
        count=u(b,72);end=76+4*count;assert b[end:]==p('I',0)
        n.blocks[index]=(kind,b[:72]+p('I',count+len(extra))+b[76:end]+p('I'*len(extra),*extra)+b[end:])
    def node(name,m,scale=1):
        r=m.to_3x3();blob=p('IIiI',n.string(name),0,-1,14)
        blob+=p('3f',*m.translation)+p('9f',*(r[i][j] for i in range(3) for j in range(3)))+p('fiII',scale,-1,0,0)
        return n.append('NiNode',blob)
    nodes={n.strings[u(b)].decode():i for i,(kind,b) in enumerate(n.blocks) if kind=='NiNode'}
    touched=set();anchor_report=[]
    for j,anchor in enumerate(model['particle_anchors']):
        node_texture=textures[j%len(textures)]
        bone=nodes[anchor['bone']];parent_matrix=global_matrix(bone);side=anchor['side']
        direction={'embers':(0,1,0),'streak':(-.5,side,0),'mote':(0,1,0),'flake':(.1,-side,0),'hollowsquare':(0,1,0),'oval':(0,1,0),'hollowdiamond':(1,0,0),'ring':(0,1,0),'droplet':(0,1,0),'hollowtriangle':(0,side,0),'diamond':(1,0,0),'kite':(1,0,0),'chevron':(0,side,0),'crescent':(1,0,0),'shadow':(1,.2,0),'pearl':(0,1,0),'triangle':(0,1,0),'square':(.1,-side,0),'hexagon':(1,0,0),'needle':(0,side,0)}[spec['fx']]
        direction=anchor.get('direction',direction)
        desired=Vector(direction).to_track_quat('Z','Y').to_matrix().to_4x4();desired.translation=Vector(anchor['position'])
        local=parent_matrix.inverted()@desired
        control=node(spec.get('particle_node_prefix','AAAriesDust')+str(j),local,spec.get('control_scale',.0001));children(bone,[control]);touched.add(bone)
        assert ((parent_matrix@local).translation-desired.translation).length<.001
        mapping={i:n.append(src.blocks[i][0],b'') for i in selected};grow=n.append('NiPSysGrowFadeModifier',b'')
        refs=lambda i:mapping[i]
        names={i:n.string(f'AAAries{j}_'+src.strings[u(src.blocks[i][1])].decode()) for i in (3,5,13,15,17,21,22)}
        dark=spec['fx']=='shadow' and j%2==0
        color=[.012,.012,.012] if dark else spec['particle_color']
        if not dark and j%2:color=spec.get('particle_secondary',color)
        radius=spec['radius'] if not (spec['fx']=='shadow' and not dark) else 1.7
        for i in selected:
            kind,b0=src.blocks[i];b=bytearray(b0)
            if i==3:
                b=bytearray(p('IIiI3f9ffiII',names[i],0,-1,14,0,0,0,1,0,0,0,1,0,0,0,1,1,-1,1,refs(5))+p('I',0))
            elif i==4:patch(b,4,'H',spec['pool'])
            elif i==5:
                assert len(b)==165 and u(b,116)==4 and u(b,121)==10
                patch(b,0,'I',names[i]);patch(b,8,'I',refs(6));patch(b,16,'3f',0,0,0);patch(b,28,'9f',1,0,0,0,1,0,0,0,1);patch(b,64,'f',1)
                patch(b,72,'4f',0,0,0,24);patch(b,92,'II',refs(11),refs(12));patch(b,116,'I',refs(4))
                mods=[refs(13),refs(15),refs(17),grow,refs(21),refs(22)]
                b=b[:120]+p('BI',0,6)+p('6I',*mods)
            elif i in (6,7):
                patch(b,0,'i',refs(7) if i==6 else -1);patch(b,4,'H',0x48);patch(b,6,'4f',1,0,0,1);patch(b,22,'I',refs(5))
                if i==6:patch(b,26,'III',refs(8),names[15],refs(9))
            elif i==8:b=bytearray(p('fi',spec['rate'],-1))
            elif i==9:b=bytearray(p('Bi',1,-1))
            elif i==11:
                path=('textures\\weapons\\arcanearsenal\\'+node_texture.name).encode('ascii')
                b=bytearray(p('iIiII4f',-1,0,-1,0x80000008,0x20,0,0,1,1))+p('I',len(path))+path+p('4B',3,0,0,0)
                b+=p('4f',1,1,1,1)+p('4f',*color,1)+p('ffI',.7 if dark else spec['particle_power'],5,0)
            elif i==12:b=bytearray(p('iIiHB',-1,0,-1,0x10ed if dark else 0x100d,0))
            elif i in (13,15,17,21,22):
                patch(b,0,'I',names[i]);patch(b,8,'I',refs(5))
                if i==13:patch(b,13,'Bi',0,-1)
                if i==15:
                    spread=math.pi/2 if spec['fx'] in ('mote','diamond','pearl') else .32
                    spread=spec.get('spread',spread)
                    patch(b,13,'6f',spec['speed'],spec['speed']*.35,0,spread,0,math.pi)
                    patch(b,37,'4f',1,1,1,1);patch(b,53,'4f',radius,radius*.3,spec['life'],spec['life']*.15)
                    patch(b,69,'I3f',refs(3),1.2,1.2,.65)
                if i==17:
                    patch(b,13,'6f',.1,.65,.1,.2,.6,.8);patch(b,37,'12f',1,1,1,0,1,1,1,1,1,1,1,0)
            n.blocks[refs(i)]=(kind,bytes(b))
        n.blocks[grow]=('NiPSysGrowFadeModifier',p('IIIBfHfHf',n.string(f'AAAries{j}_GrowFade'),4000,refs(5),1,.08,0,spec['life']*.3,0,1))
        children(control,[refs(3)])
        anchor_report.append({**anchor,'root':spec.get('particle_node_prefix','AAAriesDust')+str(j),'control_block':control,'system':refs(5),'dark_alpha':dark})
    dest=ROOT/'data/meshes/weapons/arcanearsenal'/(key+'.nif');n.save(dest)
    check=NifBlocks(dest);assert check.blocks==n.blocks and check.strings==n.strings
    for i,old in enumerate(original):
        if i not in touched:assert check.blocks[i]==old
        else:assert check.blocks[i][1][:72]==old[1][:72]
    report={'key':key,'version':'0.8.0' if SERIES=='geometric' else '0.7.1','old_block_count':len(original),'new_block_count':len(n.blocks),'native_particle_systems':6,'pool_per_system':spec['pool'],'typical_particles_per_view':round(6*spec['rate']*spec['life']),'max_particles_both_views':12*spec['pool'],'texture':texture.name,'anchors':anchor_report,'geometry_preserved':True,'hidden_scale':spec.get('control_scale',.0001),'style':spec['fx'],'scope':'Local-space native particles; in-game playback pending.'}
    if SERIES=='leo':report['version']='0.14.0'
    if SERIES=='virgo':report['version']='0.15.0'
    if SERIES=='libra':report['version']='0.16.0'
    if SERIES=='sagittarius':report['version']='0.17.0'
    if SERIES=='capricorn':report['version']='0.18.0'
    if SERIES=='aquarius':report['version']='0.19.0'
    if SERIES=='pisces':report['version']='0.20.0'
    if SERIES=='scorpio':report['version']='0.21.0'
    if SERIES=='heteromorphic':report['version']='0.22.0'
    if SERIES=='heteromorphic2':report['version']='0.24.0'
    if SERIES=='greatswords':report['version']='0.25.0'
    if SERIES=='greatswords2':report['version']='0.26.0'
    if SERIES=='greatswords3':report['version']='0.27.0'
    if SERIES=='swords':report['version']='0.28.0'
    if SERIES=='crystal':report['version']='0.23.0'
    report['textures']=[t.name for t in textures]
    (ROOT/'build'/(key+'-particles.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ARIES_PARTICLES '+key+' '+str(len(n.blocks)),flush=True)

specs=json.loads((ROOT/'source'/(SERIES+'_catalog.json')).read_text(encoding='utf-8'))
keys=set(sys.argv[sys.argv.index('--keys')+1].split(',')) if '--keys' in sys.argv else {s['key'] for s in specs}
assert keys and keys<={s['key'] for s in specs}
for spec in specs:
    if spec['key'] in keys:build(spec)
