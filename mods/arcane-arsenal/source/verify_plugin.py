"""Validate upgrade identity, Chinese display names, model links and test inventory."""
from pathlib import Path
import struct,json
from plugin_records import records,subrecords,edid,sub
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
items=list(records(ROOT/'data/ArcaneArsenal.esp'));by_form={r['form']:r for r in items}
expected={'AAfrostglass':0x01000801,'AAemberwake':0x01000804,'AAastralorbit':0x01000807,
          'AAmoonthorn':0x0100080A,'AAfrostwyrm':0x0100080E,'AAAllBowsTestChest':0x0100080C,
          'AAredplates':0x01000811,'AAredtriangles':0x01000814,'AAreddiamonds':0x01000817}
expected.update({'AAariesred':0x0100081B,'AAariesgreen':0x01000821,'AAariesblue':0x01000824,'AAariespurple':0x01000827})
expected.update({'AAtaurusred':0x01000831,'AAtaurusgreen':0x01000834,'AAtaurusblue':0x01000837,'AAtauruspurple':0x0100083A})
expected.update({'AA'+s['key']:0x01000000|int(s['stat_form'],16)+1 for s in catalog if s['key'].startswith(('geo','gemini','cancer','leo','virgo','libra','sagittarius','capricorn','aquarius','pisces','scorpio','crystal','heteromorphic'))})
header=items[0];hp=dict(subrecords(header['data']))
assert header['flags']==0x200
assert abs(struct.unpack_from('<f',hp[b'HEDR'])[0]-1.7)<1e-6
assert len(items)==245 and len(by_form)==245
assert struct.unpack('<fII',hp[b'HEDR'])[1:]==(244,0x919)
assert all(r['version']==44 for r in items)
assert all(0x800<=(r['form']&0xffffff)<=0xFFF for r in items[1:])
weapons=[r for r in items if r['sig']==b'WEAP'];assert len(weapons)==76
names=[]
for r in weapons:
    assert r['form']==expected[edid(r)]
    fields=dict(subrecords(r['data']))
    spec=next(s for s in catalog if 'AA'+s['key']==edid(r))
    assert struct.unpack_from('<H',fields[b'DATA'],8)[0]==spec['damage']==90
    assert struct.unpack_from('<f',fields[b'DNAM'],4)[0]==spec['weapon_speed']==1.5
    label=fields[b'FULL'].rstrip(b'\0').decode('utf-8')
    assert label==next(s['name'] for s in catalog if 'AA'+s['key']==edid(r))
    assert all('\u4e00'<=c<='\u9fff' or c=='·' for c in label),label
    names.append(label)
    if edid(r).startswith(('AAaries','AAtaurus','AAgemini','AAcancer','AAleo','AAvirgo','AAlibra','AAsagittarius','AAcapricorn','AAaquarius','AApisces','AAscorpio','AAcrystal','AAheteromorphic','AAgeo','AAred')):
        assert b'EITM' not in fields and b'EAMT' not in fields, 'Preset enchantment would tint pure emission'
    fp=by_form[struct.unpack('<I',fields[b'WNAM'])[0]]
    assert fp['sig']==b'STAT' and dict(subrecords(fp['data']))[b'MODL']==fields[b'MODL']
    model=fields[b'MODL'].rstrip(b'\0').decode('ascii').replace('\\','/')
    assert (ROOT/'data/meshes'/model).is_file()
chest=next(r for r in items if edid(r)=='AAAllBowsTestChest')
assert chest['form']==expected['AAAllBowsTestChest']
parts=list(subrecords(chest['data']))
inventory=[struct.unpack('<II',v) for k,v in parts if k==b'CNTO']
assert len(inventory)==77
assert struct.unpack('<I',dict(parts)[b'COCT'])[0]==77
assert all((r['form'],1) in inventory for r in weapons)
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='幻律兵装·试武箱'
# Retire four crystal weapon triplets and their chest; preserve all surviving records.
baseline=list(records(ROOT/'build/before-0.23.1/data/ArcaneArsenal.esp'))
retired={0x01000000|(int(s['stat_form'],16)+j) for s in json.loads((ROOT/'source/retired_weapons.json').read_text(encoding='utf-8')) for j in range(3)}
assert len(retired)==36 and retired.isdisjoint(by_form)
old_forms={r['form'] for r in baseline}
assert set(by_form) <= old_forms
assert old_forms-set(by_form)=={0x01000000|i for i in range(0x90C,0x919)}
assert 0x01000918 not in by_form
strip=lambda r:[(k,v) for k,v in subrecords(r['data']) if k not in (b'COCT',b'CNTO')]
for old in baseline:
    if old['form'] in retired or old['form']==0x01000918:continue
    current=by_form[old['form']]
    if edid(old)=='AAAllBowsTestChest':assert strip(old)==strip(current)
    elif old['sig']!=b'TES4':assert current==old,edid(old)
aries_chest=next(r for r in items if edid(r)=='AAAriesTestChest')
assert aries_chest['form']==0x0100082F
parts=list(subrecords(aries_chest['data']))
aries_items=[struct.unpack('<II',v) for k,v in parts if k==b'CNTO']
assert len(aries_items)==5 and dict(parts)[b'COCT']==struct.pack('<I',5)
assert set(aries_items)=={(f,1) for f in (0x0100081B,0x01000821,0x01000824,0x01000827)}|{(0x1397D,200)}
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='白羊座·试武箱'
taurus_chest=next(r for r in items if edid(r)=='AATaurusTestChest')
assert taurus_chest['form']==0x0100083C
parts=list(subrecords(taurus_chest['data']))
taurus_items=[struct.unpack('<II',v) for k,v in parts if k==b'CNTO']
assert len(taurus_items)==5 and dict(parts)[b'COCT']==struct.pack('<I',5)
assert set(taurus_items)=={(f,1) for f in (0x01000831,0x01000834,0x01000837,0x0100083A)}|{(0x1397D,200)}
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='金牛座·试武箱'
assert len([r for r in items if r['sig']==b'CONT'])==15
geometric=by_form[0x0100087C]
assert edid(geometric)=='AAGeometricTestChest'
gparts=list(subrecords(geometric['data']))
ginventory=[struct.unpack('<II',v) for k,v in gparts if k==b'CNTO']
assert len(ginventory)==25 and dict(gparts)[b'COCT']==struct.pack('<I',25)
assert set(ginventory)=={(0x01000000|int(s['stat_form'],16)+1,1) for s in catalog if s.get('series')=='geometric'}|{(0x1397D,200)}
# The legacy chest changes inventory only, preserving the template and identity.
old_chest=next(r for r in baseline if edid(r)=='AAAllBowsTestChest')
strip=lambda r:[(k,v) for k,v in subrecords(r['data']) if k not in (b'COCT',b'CNTO')]
assert strip(old_chest)==strip(chest)
quest=next(r for r in items if r['sig']==b'QUST')
assert quest['form']==0x01000819 and edid(quest)=='AARedDrawFXQuest'
qp=dict(subrecords(quest['data']))
assert struct.unpack('<I',qp[b'ALFR'])[0]==0x14
assert struct.unpack_from('<H',qp[b'DNAM'])[0]==0x111
assert b'AARedDrawFX' in qp[b'VMAD']
assert (ROOT/'data/seq/ArcaneArsenal.seq').read_bytes()==struct.pack('<I',quest['form'])
assert (ROOT/'data/scripts/AARedDrawFX.pex').read_bytes()[:4]==bytes.fromhex('fa57c0de')
gemini=by_form[0x01000889]
assert edid(gemini)=='AAGeminiTestChest'
parts=list(subrecords(gemini['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='双子座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x87E,0x881,0x884,0x887)}|{(0x1397D,200)}
cancer=by_form[0x01000896]
assert edid(cancer)=='AACancerTestChest'
parts=list(subrecords(cancer['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='巨蟹座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x88B,0x88E,0x891,0x894)}|{(0x1397D,200)}
leo=by_form[0x010008A3]
assert edid(leo)=='AALeoTestChest'
parts=list(subrecords(leo['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='狮子座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x898,0x89B,0x89E,0x8A1)}|{(0x1397D,200)}
virgo=by_form[0x010008B0]
assert edid(virgo)=='AAVirgoTestChest'
parts=list(subrecords(virgo['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='处女座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8A5,0x8A8,0x8AB,0x8AE)}|{(0x1397D,200)}
libra=by_form[0x010008BD]
assert edid(libra)=='AALibraTestChest'
parts=list(subrecords(libra['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='天秤座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8B2,0x8B5,0x8B8,0x8BB)}|{(0x1397D,200)}
sagittarius=by_form[0x010008CA]
assert edid(sagittarius)=='AASagittariusTestChest'
parts=list(subrecords(sagittarius['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='射手座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8BF,0x8C2,0x8C5,0x8C8)}|{(0x1397D,200)}
capricorn=by_form[0x010008D7]
assert edid(capricorn)=='AACapricornTestChest'
parts=list(subrecords(capricorn['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='摩羯座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8CC,0x8CF,0x8D2,0x8D5)}|{(0x1397D,200)}
aquarius=by_form[0x010008E4]
assert edid(aquarius)=='AAAquariusTestChest'
parts=list(subrecords(aquarius['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='水瓶座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8D9,0x8DC,0x8DF,0x8E2)}|{(0x1397D,200)}
pisces=by_form[0x010008F1]
assert edid(pisces)=='AAPiscesTestChest'
parts=list(subrecords(pisces['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='双鱼座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8E6,0x8E9,0x8EC,0x8EF)}|{(0x1397D,200)}
scorpio=by_form[0x010008FE]
assert edid(scorpio)=='AAScorpioTestChest'
parts=list(subrecords(scorpio['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='天蝎座·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x8F3,0x8F6,0x8F9,0x8FC)}|{(0x1397D,200)}
heteromorphic=by_form[0x0100090B]
assert edid(heteromorphic)=='AAHeteromorphicTestChest'
parts=list(subrecords(heteromorphic['data']))
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='异构·试武箱'
assert dict(parts)[b'COCT']==struct.pack('<I',5)
assert {struct.unpack('<II',v) for k,v in parts if k==b'CNTO'}=={(0x01000000|f,1) for f in (0x900,0x903,0x906,0x909)}|{(0x1397D,200)}
assert [v for k,v in subrecords(header['data']) if k==b'MAST']==[b'Skyrim.esm\0']
for spec in catalog:
    base=0x01000000|int(spec['stat_form'],16)
    recipe=by_form[base+2]
    assert recipe['sig']==b'COBJ' and dict(subrecords(recipe['data']))[b'CNAM']==struct.pack('<I',base+1)
report={'version':'0.23.1','passed':True,'weapons':76,'test_chests':15,'existing_record_identities_preserved':True,'base_damage':90,'weapon_speed':1.5,'ESL':True,'new_records':0,'removed_records':13,'retired_records_absent':37,'gameplay_tested':False}
(ROOT/'build/plugin-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
