"""Bow collections and their test chests in one Skyrim SE 1.5.97-compatible ESP-FE."""
from pathlib import Path
import struct,json,configparser
from plugin_records import records,subrecords,edid,sub,encode,group
ROOT=Path(__file__).resolve().parents[1]
MASTER=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data\Skyrim.esm')
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
metadata=configparser.ConfigParser();metadata.read(ROOT/'packaging/meta.ini',encoding='utf-8');version=metadata['General']['version']
record_count=len(catalog)*3+16
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
    # Explicit IDs preserve save identity when catalog entries are retired.
    # Never reuse the reserved IDs recorded in retired_weapons.json.
    base=0x01000000|int(spec['stat_form'],16);stat_id=base;weapon_id=base+1;recipe_id=base+2
    model=Z('weapons\\arcanearsenal\\'+spec['key']+'.nif')
    enchant=by_name[spec['enchantment'].lower()] if spec.get('enchantment') else None
    stats.append(changed(firstperson,stat_id,{b'EDID':Z('AA'+spec['key']+'1stPerson'),b'OBND':bounds,b'MODL':model},(b'MODT',b'MODS')))
    weapon_data=bytearray(parts[b'DNAM'])
    struct.pack_into('<f',weapon_data,4,float(spec['weapon_speed']))
    weapons.append(changed(weapon,weapon_id,{
        b'EDID':Z('AA'+spec['key']),b'FULL':Z(spec['name']),b'DESC':b'\0',b'OBND':bounds,
        b'MODL':model,b'WNAM':U32(stat_id),
        **({b'EITM':U32(enchant['form']),b'EAMT':struct.pack('<H',1800)} if enchant else {}),
        b'DATA':struct.pack('<IfH',1800,float(spec['weight']),spec['damage']),
        b'DNAM':bytes(weapon_data),
    },(b'MODT',b'MODS',b'CNAM')+(() if enchant else (b'EITM',b'EAMT'))))
    ingredients=[('ingotsilver',2),('ingotmalachite',3)]
    d=sub(b'EDID',Z('AARecipe'+spec['key']))+sub(b'COCT',U32(len(ingredients)))
    for name,amount in ingredients:d+=sub(b'CNTO',struct.pack('<II',by_name[name]['form'],amount))
    d+=sub(b'CNAM',U32(weapon_id))+sub(b'BNAM',U32(by_name['craftingsmithingforge']['form']))+sub(b'NAM1',struct.pack('<H',1))
    recipes.append({'sig':b'COBJ','form':recipe_id,'version':44,'data':d})
    report.append({'name':spec['name'],'key':spec['key'],'local_form':f'{weapon_id & 0xffffff:06X}','enchantment':spec['enchantment'],'damage':spec['damage'],'weapon_speed':spec['weapon_speed'],'weight':spec['weight']})

# A spawnable, non-respawning chest provides the complete test set without scripts.
chest_id=0x0100080C
chest=changed(by_name['treaschestsmallemptynorespawn'],chest_id,
              {b'EDID':Z('AAAllBowsTestChest'),b'FULL':Z('幻律兵装·试武箱')},(b'MODT',b'COCT',b'CNTO'))
inventory=[(w['form'],1) for w in weapons]+[(by_name['ironarrow']['form'],200)]
extra=sub(b'COCT',U32(len(inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in inventory)
# Container inventory comes before DATA in the record schema.
chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(chest['data']))
aries_chest=changed(by_name['treaschestsmallemptynorespawn'],0x0100082F,
                    {b'EDID':Z('AAAriesTestChest'),b'FULL':Z('白羊座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
aries_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s['key'].startswith('aries')]+[(by_name['ironarrow']['form'],200)]
extra=sub(b'COCT',U32(len(aries_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in aries_inventory)
aries_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(aries_chest['data']))
taurus_chest=changed(by_name['treaschestsmallemptynorespawn'],0x0100083C,
                     {b'EDID':Z('AATaurusTestChest'),b'FULL':Z('金牛座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
taurus_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s['key'].startswith('taurus')]+[(by_name['ironarrow']['form'],200)]
extra=sub(b'COCT',U32(len(taurus_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in taurus_inventory)
taurus_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(taurus_chest['data']))
geometric_chest=changed(by_name['treaschestsmallemptynorespawn'],0x0100087C,
                     {b'EDID':Z('AAGeometricTestChest'),b'FULL':Z('几何律·试武箱')},(b'MODT',b'COCT',b'CNTO'))
geometric_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='geometric']+[(by_name['ironarrow']['form'],200)]
assert len(geometric_inventory)==25
extra=sub(b'COCT',U32(len(geometric_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in geometric_inventory)
geometric_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(geometric_chest['data']))
gemini_chest=changed(by_name['treaschestsmallemptynorespawn'],0x01000889,
                     {b'EDID':Z('AAGeminiTestChest'),b'FULL':Z('双子座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
gemini_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='gemini']+[(by_name['ironarrow']['form'],200)]
assert len(gemini_inventory)==5
extra=sub(b'COCT',U32(len(gemini_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in gemini_inventory)
gemini_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(gemini_chest['data']))
cancer_chest=changed(by_name['treaschestsmallemptynorespawn'],0x01000896,
                     {b'EDID':Z('AACancerTestChest'),b'FULL':Z('巨蟹座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
cancer_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='cancer']+[(by_name['ironarrow']['form'],200)]
assert len(cancer_inventory)==5
extra=sub(b'COCT',U32(len(cancer_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in cancer_inventory)
cancer_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(cancer_chest['data']))
leo_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008A3,
                     {b'EDID':Z('AALeoTestChest'),b'FULL':Z('狮子座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
leo_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='leo']+[(by_name['ironarrow']['form'],200)]
assert len(leo_inventory)==5
extra=sub(b'COCT',U32(len(leo_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in leo_inventory)
leo_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(leo_chest['data']))
virgo_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008B0,
                     {b'EDID':Z('AAVirgoTestChest'),b'FULL':Z('处女座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
virgo_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='virgo']+[(by_name['ironarrow']['form'],200)]
assert len(virgo_inventory)==5
extra=sub(b'COCT',U32(len(virgo_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in virgo_inventory)
virgo_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(virgo_chest['data']))
libra_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008BD,
                     {b'EDID':Z('AALibraTestChest'),b'FULL':Z('天秤座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
libra_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='libra']+[(by_name['ironarrow']['form'],200)]
assert len(libra_inventory)==5
extra=sub(b'COCT',U32(len(libra_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in libra_inventory)
libra_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(libra_chest['data']))
sagittarius_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008CA,
                     {b'EDID':Z('AASagittariusTestChest'),b'FULL':Z('射手座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
sagittarius_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='sagittarius']+[(by_name['ironarrow']['form'],200)]
assert len(sagittarius_inventory)==5
extra=sub(b'COCT',U32(len(sagittarius_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in sagittarius_inventory)
sagittarius_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(sagittarius_chest['data']))
capricorn_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008D7,
                     {b'EDID':Z('AACapricornTestChest'),b'FULL':Z('摩羯座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
capricorn_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='capricorn']+[(by_name['ironarrow']['form'],200)]
assert len(capricorn_inventory)==5
extra=sub(b'COCT',U32(len(capricorn_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in capricorn_inventory)
capricorn_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(capricorn_chest['data']))
aquarius_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008E4,
                     {b'EDID':Z('AAAquariusTestChest'),b'FULL':Z('水瓶座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
aquarius_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='aquarius']+[(by_name['ironarrow']['form'],200)]
assert len(aquarius_inventory)==5
extra=sub(b'COCT',U32(len(aquarius_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in aquarius_inventory)
aquarius_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(aquarius_chest['data']))
pisces_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008F1,
                     {b'EDID':Z('AAPiscesTestChest'),b'FULL':Z('双鱼座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
pisces_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='pisces']+[(by_name['ironarrow']['form'],200)]
assert len(pisces_inventory)==5
extra=sub(b'COCT',U32(len(pisces_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in pisces_inventory)
pisces_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(pisces_chest['data']))
scorpio_chest=changed(by_name['treaschestsmallemptynorespawn'],0x010008FE,
                     {b'EDID':Z('AAScorpioTestChest'),b'FULL':Z('天蝎座·试武箱')},(b'MODT',b'COCT',b'CNTO'))
scorpio_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series')=='scorpio']+[(by_name['ironarrow']['form'],200)]
assert len(scorpio_inventory)==5
extra=sub(b'COCT',U32(len(scorpio_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in scorpio_inventory)
scorpio_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(scorpio_chest['data']))
heteromorphic_chest=changed(by_name['treaschestsmallemptynorespawn'],0x0100090B,
                     {b'EDID':Z('AAHeteromorphicTestChest'),b'FULL':Z('异构·试武箱')},(b'MODT',b'COCT',b'CNTO'))
heteromorphic_inventory=[(w['form'],1) for w,s in zip(weapons,catalog) if s.get('series') in ('heteromorphic','heteromorphic2')]+[(by_name['ironarrow']['form'],200)]
assert len(heteromorphic_inventory)==9
extra=sub(b'COCT',U32(len(heteromorphic_inventory)))+b''.join(sub(b'CNTO',struct.pack('<II',f,c)) for f,c in heteromorphic_inventory)
heteromorphic_chest['data']=b''.join((extra if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(heteromorphic_chest['data']))
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
# Crystal experiment IDs 0x90C..0x918 are retired, including chest 0x918. Never reuse.
header={'sig':b'TES4','flags':0x200,'form':0,'version':44,'data':
    sub(b'HEDR',struct.pack('<fII',1.7,record_count,0x925))+
    sub(b'CNAM',Z('Arcane Armory'))+
    sub(b'SNAM',Z(f'{len(catalog)} original bows and fifteen test chests. Version {version} for Skyrim SE 1.5.97. <cp:utf8>'))+
    sub(b'MAST',b'Skyrim.esm\0')+sub(b'DATA',b'\0'*8)}
dest=ROOT/'data/ArcaneArsenal.esp';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_bytes(encode(header)+group(b'STAT',stats)+group(b'CONT',[chest,aries_chest,taurus_chest,geometric_chest,gemini_chest,cancer_chest,leo_chest,virgo_chest,libra_chest,sagittarius_chest,capricorn_chest,aquarius_chest,pisces_chest,scorpio_chest,heteromorphic_chest])+group(b'COBJ',recipes)+group(b'WEAP',weapons)+group(b'QUST',[quest]))
parsed=list(records(dest));assert len(parsed)==record_count+1
assert parsed[0]['flags']&0x200
assert all(0x800<=(r['form']&0xffffff)<=0xFFF for r in parsed[1:])
assert len({r['form'] for r in parsed})==len(parsed)
for r in parsed:
    if r['sig']==b'WEAP':
        display=dict(subrecords(r['data']))[b'FULL'].rstrip(b'\0').decode('utf-8')
        assert display in {s['name'] for s in catalog}
result={'version':version,'plugin':'ArcaneArsenal.esp','ESL':True,'header_version':1.7,'form_version':44,'master':'Skyrim.esm','new_records':record_count,'weapons':report,'test_chest':'00080C','test_chest_contents':f'{len(catalog)} bows, 200 iron arrows','aries_chest':'00082F','aries_chest_contents':'4 Aries bows, 200 iron arrows','taurus_chest':'00083C','taurus_chest_contents':'4 Taurus bows, 200 iron arrows','geometric_chest':'00087C','geometric_chest_contents':'24 geometric bows, 200 iron arrows','gameplay_tested':False}
result.update(gemini_chest='000889',gemini_chest_contents='4 Gemini bows, 200 iron arrows')
result.update(cancer_chest='000896',cancer_chest_contents='4 Cancer bows, 200 iron arrows')
result.update(leo_chest='0008A3',leo_chest_contents='4 Leo bows, 200 iron arrows')
result.update(virgo_chest='0008B0',virgo_chest_contents='4 Virgo bows, 200 iron arrows')
result.update(libra_chest='0008BD',libra_chest_contents='4 Libra bows, 200 iron arrows')
result.update(sagittarius_chest='0008CA',sagittarius_chest_contents='4 Sagittarius bows, 200 iron arrows')
result.update(capricorn_chest='0008D7',capricorn_chest_contents='4 Capricorn bows, 200 iron arrows')
result.update(aquarius_chest='0008E4',aquarius_chest_contents='4 Aquarius bows, 200 iron arrows')
result.update(pisces_chest='0008F1',pisces_chest_contents='4 Pisces bows, 200 iron arrows')
result.update(scorpio_chest='0008FE',scorpio_chest_contents='4 Scorpio bows, 200 iron arrows')
result.update(heteromorphic_chest='00090B',heteromorphic_chest_contents='8 Heteromorphic bows, 200 iron arrows')
(ROOT/'build/plugin-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
