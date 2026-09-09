"""Eight bows and a test chest in one Skyrim SE 1.5.97-compatible ESP-FE."""
from pathlib import Path
import struct,json,configparser
from plugin_records import records,subrecords,edid,sub,encode,group
ROOT=Path(__file__).resolve().parents[1]
MASTER=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data\Skyrim.esm')
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
metadata=configparser.ConfigParser();metadata.read(ROOT/'packaging/meta.ini',encoding='utf-8');version=metadata['General']['version']
record_count=len(catalog)*3+2
source=list(records(MASTER,{b'WEAP',b'STAT',b'ENCH',b'MISC',b'KYWD',b'INGR',b'CONT',b'AMMO'}))
by_name={edid(r).lower():r for r in source};by_form={r['form']:r for r in source}
weapon=by_name['imperialbow'];parts=dict(subrecords(weapon['data']))
firstperson=by_form[struct.unpack('<I',parts[b'WNAM'])[0]]
U32=lambda n:struct.pack('<I',n)
Z=lambda s:s.encode('utf-8')+b'\0'
bounds=struct.pack('<6h',-25,-73,-10,32,73,11)

def changed(template,form,changes,remove=()):
    content=[];seen=set();present={k for k,v in subrecords(template['data'])}
    for k,v in subrecords(template['data']):
        if k in remove:continue
        content.append(sub(k,changes.get(k,v)));seen.add(k)
        if template['sig']==b'WEAP' and k==b'MODL':
            for extra in (b'EITM',b'EAMT'):
                if extra in changes and extra not in present:
                    content.append(sub(extra,changes[extra]));seen.add(extra)
    for k,v in changes.items():
        if k not in seen:content.append(sub(k,v))
    return {'sig':template['sig'],'flags':template['flags'],'form':form,'version':44,'data':b''.join(content)}

stats=[];weapons=[];recipes=[];report=[]
for i,spec in enumerate(catalog):
    # 80C belongs to the existing test chest. Never shift existing FormIDs.
    base=0x01000800+i*3+(1 if i>=4 else 0);stat_id=base;weapon_id=base+1;recipe_id=base+2
    model=Z('weapons\\arcanearsenal\\'+spec['key']+'.nif')
    enchant=by_name[spec['enchantment'].lower()]
    stats.append(changed(firstperson,stat_id,{b'EDID':Z('AA'+spec['key']+'1stPerson'),b'OBND':bounds,b'MODL':model},(b'MODT',b'MODS')))
    weapons.append(changed(weapon,weapon_id,{
        b'EDID':Z('AA'+spec['key']),b'FULL':Z(spec['name']),b'DESC':b'\0',b'OBND':bounds,
        b'MODL':model,b'WNAM':U32(stat_id),b'EITM':U32(enchant['form']),b'EAMT':struct.pack('<H',1800),
        b'DATA':struct.pack('<IfH',1800,float(spec['weight']),spec['damage']),
    },(b'MODT',b'MODS',b'CNAM')))
    ingredients=[('ingotsilver',2),('ingotmalachite',3)]
    d=sub(b'EDID',Z('AARecipe'+spec['key']))+sub(b'COCT',U32(len(ingredients)))
    for name,amount in ingredients:d+=sub(b'CNTO',struct.pack('<II',by_name[name]['form'],amount))
    d+=sub(b'CNAM',U32(weapon_id))+sub(b'BNAM',U32(by_name['craftingsmithingforge']['form']))+sub(b'NAM1',struct.pack('<H',1))
    recipes.append({'sig':b'COBJ','form':recipe_id,'version':44,'data':d})
    report.append({'name':spec['name'],'key':spec['key'],'local_form':f'{weapon_id & 0xffffff:06X}','enchantment':spec['enchantment'],'damage':spec['damage'],'weight':spec['weight']})

# A spawnable, non-respawning chest provides the complete test set without scripts.
chest_id=0x0100080C
chest=changed(by_name['treaschestsmallemptynorespawn'],chest_id,
              {b'EDID':Z('AAAllBowsTestChest'),b'FULL':Z('异界弓藏·试武箱')},(b'MODT',b'COCT',b'CNTO'))
inventory=[(w['form'],1) for w in weapons]+[(by_name['ironarrow']['form'],200)]
extra=sub(b'COCT',U32(len(inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in inventory)
# Container inventory comes before DATA in the record schema.
chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(chest['data']))
# A hidden start-game quest with one forced player alias. No stages/objectives,
# no actor edits, and no dependency on load-order-specific light-plugin indices.
# VMAD v5 / object format 2 follows xEdit's TES5 record definitions.
quest_id=0x01000819
S16=lambda s:struct.pack('<H',len(s.encode('utf-8')))+s.encode('utf-8')
vmad=struct.pack('<HHH',5,2,0)  # no quest-level scripts
vmad+=struct.pack('<BHH',2,0,0)  # fragment bind version, zero fragments, empty filename
vmad+=struct.pack('<H',1)  # one alias script binding
vmad+=struct.pack('<HhIHHH',0,0,quest_id,5,2,1)  # alias 0 of this quest; one script
vmad+=S16('AARedDrawFX')+struct.pack('<BH',0,0)  # local script, zero properties
qd=sub(b'EDID',Z('AARedDrawFXQuest'))+sub(b'VMAD',vmad)
qd+=sub(b'DNAM',struct.pack('<HBBII',0x111,10,0,0,0))
qd+=sub(b'NEXT',b'')+sub(b'ANAM',U32(1))
qd+=sub(b'ALST',U32(0))+sub(b'ALID',Z('Player'))+sub(b'FNAM',U32(0))
qd+=sub(b'ALFR',U32(0x14))+sub(b'ALED',b'')
quest={'sig':b'QUST','form':quest_id,'version':44,'data':qd}
seq=ROOT/'data/seq/ArcaneArsenal.seq';seq.parent.mkdir(parents=True,exist_ok=True)
seq.write_bytes(U32(quest_id))
header={'sig':b'TES4','flags':0x200,'form':0,'version':44,'data':
    sub(b'HEDR',struct.pack('<fII',1.7,record_count,0x81A))+
    sub(b'CNAM',Z('Arcane Arsenal'))+
    sub(b'SNAM',Z(f'{len(catalog)} original bows and one test chest. Version {version} for Skyrim SE 1.5.97. <cp:utf8>'))+
    sub(b'MAST',b'Skyrim.esm\0')+sub(b'DATA',b'\0'*8)}
dest=ROOT/'data/ArcaneArsenal.esp';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_bytes(encode(header)+group(b'STAT',stats)+group(b'CONT',[chest])+group(b'COBJ',recipes)+group(b'WEAP',weapons)+group(b'QUST',[quest]))
parsed=list(records(dest));assert len(parsed)==record_count+1
assert parsed[0]['flags']&0x200
assert all(0x800<=(r['form']&0xffffff)<=0xFFF for r in parsed[1:])
assert len({r['form'] for r in parsed})==len(parsed)
for r in parsed:
    if r['sig']==b'WEAP':
        display=dict(subrecords(r['data']))[b'FULL'].rstrip(b'\0').decode('utf-8')
        assert display in {s['name'] for s in catalog}
result={'version':version,'plugin':'ArcaneArsenal.esp','ESL':True,'header_version':1.7,'form_version':44,'master':'Skyrim.esm','new_records':record_count,'weapons':report,'test_chest':'00080C','test_chest_contents':f'{len(catalog)} bows, 200 iron arrows','gameplay_tested':False}
(ROOT/'build/plugin-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
