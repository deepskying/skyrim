"""Standalone ESP-FE: twelve playable visual prototypes and a spawnable test chest."""
import struct,json
from paths import *
from game_specs import PROTOTYPES
from plugin_records import records,subrecords,edid,sub,encode,group
P=lambda fmt,*x:struct.pack('<'+fmt,*x)
Z=lambda s:s.encode('utf-8')+b'\0'
U=lambda n:P('I',n)
F=lambda n:0x01000000|n
source=list(records(GAME/'Data/Skyrim.esm',{b'AMMO',b'PROJ',b'CONT',b'WEAP',b'STAT'}))
byname={edid(r).lower():r for r in source};byid={r['form']:r for r in source}
ammo_template=byname['ironarrow'];ammo_parts=dict(subrecords(ammo_template['data']))
proj_template=byid[struct.unpack_from('<I',ammo_parts[b'DATA'])[0]]

def change(r,form,changes,remove=()):
    seen=set();out=[]
    for k,v in subrecords(r['data']):
        if k in remove:continue
        out.append(sub(k,changes.get(k,v)));seen.add(k)
    out.extend(sub(k,v) for k,v in changes.items() if k not in seen)
    return dict(sig=r['sig'],flags=r['flags']&~4,form=form,version=44,data=b''.join(out))

ammos=[];projectiles=[];explosions=[];manifest=[]
for s in PROTOTYPES:
    aid=F(s['id']);pid=aid+1;eid=aid+2
    ammos.append(change(ammo_template,aid,{
        b'EDID':Z('MAArrow'+s['key'].title()),b'FULL':Z(s['name']+'〔外观试作〕'),
        b'MODL':Z('magicarrows\\'+s['key']+'.nif'),b'DESC':Z('发光魔法箭外观试作。基础伤害8；尚未封存法术。'),
        b'OBND':P('6h',-8,-62,-8,8,2,8),b'DATA':P('IIfIf',pid,4,8,1,.1),
    },(b'MODT',b'MODS')))
    data=bytearray(dict(subrecords(proj_template['data']))[b'DATA'])
    flags=struct.unpack_from('<H',data)[0]
    struct.pack_into('<H',data,0,(flags&~(0x40|0x100|0x4))|0x2)
    struct.pack_into('<I',data,16,0) # no actual scene light; only emissive material
    struct.pack_into('<I',data,36,eid)
    projectiles.append(change(proj_template,pid,{
        b'EDID':Z('MAProjectile'+s['key'].title()),b'FULL':Z(s['name']),
        b'MODL':Z('magicarrows\\'+s['key']+'_flight.nif'),b'DATA':bytes(data),
    },(b'MODT',b'MODS')))
    # This explosion is visual only: no enchantment, placed object, blast damage or force.
    ed=sub(b'EDID',Z('MAImpact'+s['key'].title()))+sub(b'OBND',P('6h',-24,-24,-24,24,24,24))
    ed+=sub(b'MODL',Z('magicarrows\\'+s['key']+'_impact.nif'))
    ed+=sub(b'DATA',P('6I5fII',0,0,0,0,0,0,0,0,8,0,0,0x140,2))
    explosions.append(dict(sig=b'EXPL',form=eid,version=44,data=ed))
    manifest.append(dict(name=s['name'],editor_id='MAArrow'+s['key'].title(),local_form=f'{s["id"]:06X}',projectile=f'{s["id"]+1:06X}',damage=8,spell_bound=False))
chest=change(byname['treaschestsmallemptynorespawn'],F(0x830),{b'EDID':Z('MAArrowTestChest'),b'FULL':Z('魔法箭·外观试作箱 MAArrow')},(b'MODT',b'MODS',b'CNTO',b'COCT',b'VMAD'))
contents=[(r['form'],100) for r in ammos]+[(byname['imperialbow']['form'],1),(ammo_template['form'],100)]
inv=sub(b'COCT',U(len(contents)))+b''.join(sub(b'CNTO',P('II',*item)) for item in contents)
chest['data']=b''.join((inv if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(chest['data']))
from panel_power_records import build as build_power
from fireball_records import build as build_fireball
fammo,fproj,fexpl,fench=build_fireball(change,proj_template)
ammos.extend(fammo);projectiles.append(fproj);explosions.append(fexpl)
from elemental_records import build as build_elemental, header as adapter_header, SPECS as ADAPTERS
ea,ep,ee,en=build_elemental(change,proj_template,fench)
ammos.extend(ea);projectiles.extend(ep);explosions.extend(ee)
(ROOT/'native/src/spell_adapters.h').write_text(adapter_header(),encoding='utf-8')
from runtime_records import build as build_runtime
ra,rl=build_runtime(change,ammo_template);ammos.extend(ra)
marker=change(byname['xmarkerheading'],F(0xE00),{b'EDID':Z('MASustainedCastMarker')})
rl.append(dict(sig=b'FLST',form=F(0xE01),version=44,data=sub(b'EDID',Z('MASustainedLiveHelpers'))))
groups=[(b'EXPL',explosions),(b'PROJ',projectiles),(b'AMMO',ammos),(b'CONT',[chest])]+build_power()+[(b'ENCH',[fench]+en),(b'FLST',rl),(b'STAT',[marker])]
count=sum(len(rs)+1 for _,rs in groups) # TES4 HEDR counts records AND groups.
hdr=dict(sig=b'TES4',flags=0x200,form=0,version=44,data=
    sub(b'HEDR',P('fII',1.7,count,0xE02))+sub(b'CNAM',Z('Magic Arrows'))+
    sub(b'SNAM',Z('0.9.6 runtime arrows with explicit charge basket and partial crafting. <cp:utf8>'))+
    sub(b'MAST',Z('Skyrim.esm'))+sub(b'DATA',bytes(8)))
dest=DATA/'MagicArrows.esp'
dest.write_bytes(encode(hdr)+b''.join(group(sig,rs) for sig,rs in groups))
parsed=list(records(dest));assert len(parsed)==587
assert len({r['form'] for r in parsed})==len(parsed)
report=dict(version='0.9.6',plugin=dest.name,ESL=True,master='Skyrim.esm',arrows=manifest,chest_editor_id='MAArrowTestChest',chest_local_form='000830',panel_power='000840',fireball_ammo=[f'{0x900+i:06X}' for i in range(8)],fireball_payload=dict(projectile='000880',explosion='000881',enchantment='000882',base_damage=40),adapters=ADAPTERS,runtime_slots=dict(count=256,ammo_start="000C00",list_start="000D00",prebound_spells=0),gameplay_tested=False)
(BUILD/'plugin.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
