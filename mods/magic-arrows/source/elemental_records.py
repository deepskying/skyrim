"""Explicit ice and shock payloads; existing Fireball records remain unchanged."""
import json,struct
from paths import ROOT,GAME
from plugin_records import records,subrecords,sub
from fireball_records import BASES
SPECS=json.loads((ROOT/'source/spell_adapters.json').read_text(encoding='utf-8'))
P=lambda f,*v:struct.pack('<'+f,*v)
Z=lambda s:s.encode('utf-8')+b'\0'
F=lambda n:0x01000000|n

def build(change,proj_template,ench_template):
    src={r['form']:r for r in records(GAME/'Data/Skyrim.esm',{b'AMMO'})}
    ammos=[];projs=[];expls=[];enchs=[]
    for spec in SPECS[1:]:
        key=spec['key'];family=spec['family'];pid=F(spec['payload']);eid=pid+1;enid=pid+2
        for i,(base,name) in enumerate(BASES):
            data=bytearray(dict(subrecords(src[base]['data']))[b'DATA']);struct.pack_into('<I',data,0,pid)
            struct.pack_into('<I',data,12,20)
            ammos.append(change(src[base],F(spec['ammo']+i),{b'EDID':Z('MA'+key.title()+'Arrow'+str(i)),b'FULL':Z(spec['arrow']+'·'+spec['name']),b'DESC':Z('固定元素适配：命中点小范围元素爆发，基础伤害25。非原法术完整复制。'),b'MODL':Z('magicarrows\\'+family+'.nif'),b'DATA':bytes(data),b'OBND':P('6h',-8,-62,-8,8,2,8)},(b'MODT',b'MODS')))
        data=bytearray(dict(subrecords(proj_template['data']))[b'DATA']);flags=struct.unpack_from('<H',data)[0]
        struct.pack_into('<H',data,0,(flags&~(0x40|0x100|4))|2);struct.pack_into('<I',data,36,eid)
        projs.append(change(proj_template,pid,{b'EDID':Z('MA'+key.title()+'Projectile'),b'MODL':Z('magicarrows\\'+family+'_flight.nif'),b'DATA':bytes(data)},(b'MODT',b'MODS')))
        data=sub(b'EDID',Z('MA'+key.title()+'Explosion'))+sub(b'OBND',P('6h',-24,-24,-24,24,24,24))+sub(b'MODL',Z('magicarrows\\'+family+'_impact.nif'))
        data+=sub(b'EITM',P('I',enid))+sub(b'DATA',P('6I5fII',0,0,0,0,0,0,0,0,spec['radius'],0,0,0x140,2))
        expls.append(dict(sig=b'EXPL',form=eid,version=44,data=data))
        enchs.append(change(ench_template,enid,{b'EDID':Z('MA'+key.title()+'Enchantment'),b'FULL':Z(spec['arrow']+'·元素爆发'),b'EFID':P('I',spec['mgef']),b'EFIT':P('fII',spec['damage'],0,spec['duration'])}))
    return ammos,projs,expls,enchs

def header():
    text='#pragma once\nnamespace crafting {\nstruct Adapter {RE::FormID spell,ammo;const char *family,*arrow,*spellName,*material;RE::ActorValue resist;int damage,radius,gold,mana,charge;};\ninline constexpr std::array<Adapter,3> adapters{{\n'
    for s in SPECS:text+='    {0x%X,0x%X,"%s","%s","%s","%s",RE::ActorValue::%s,%d,%d,%d,%d,%d},\n'%(s['spell'],s['ammo'],s['family'],s['arrow'],s['name'],s['material'],s['resist'],s['damage'],s['radius'],s['gold'],s['mana'],s['charge'])
    return text+'}};\n}\n'
