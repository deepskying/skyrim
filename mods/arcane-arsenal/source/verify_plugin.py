"""Validate upgrade identity, Chinese display names, model links and test inventory."""
from pathlib import Path
import struct,json
from plugin_records import records,subrecords,edid
ROOT=Path(__file__).resolve().parents[1]
catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
items=list(records(ROOT/'data/ArcaneArsenal.esp'));by_form={r['form']:r for r in items}
expected={'AAfrostglass':0x01000801,'AAemberwake':0x01000804,'AAastralorbit':0x01000807,
          'AAmoonthorn':0x0100080A,'AAfrostwyrm':0x0100080E,'AAAllBowsTestChest':0x0100080C,
          'AAredplates':0x01000811,'AAredtriangles':0x01000814,'AAreddiamonds':0x01000817}
header=items[0];hp=dict(subrecords(header['data']))
assert header['flags']==0x200
assert abs(struct.unpack_from('<f',hp[b'HEDR'])[0]-1.7)<1e-6
assert len(items)==27 and len(by_form)==27
assert struct.unpack('<fII',hp[b'HEDR'])[1:]==(26,0x81A)
assert all(r['version']==44 for r in items)
assert all(0x800<=(r['form']&0xffffff)<=0xFFF for r in items[1:])
weapons=[r for r in items if r['sig']==b'WEAP'];assert len(weapons)==8
names=[]
for r in weapons:
    assert r['form']==expected[edid(r)]
    fields=dict(subrecords(r['data']))
    label=fields[b'FULL'].rstrip(b'\0').decode('utf-8')
    assert label==next(s['name'] for s in catalog if 'AA'+s['key']==edid(r))
    assert all('\u4e00'<=c<='\u9fff' or c=='·' for c in label),label
    names.append(label)
    fp=by_form[struct.unpack('<I',fields[b'WNAM'])[0]]
    assert fp['sig']==b'STAT' and dict(subrecords(fp['data']))[b'MODL']==fields[b'MODL']
    model=fields[b'MODL'].rstrip(b'\0').decode('ascii').replace('\\','/')
    assert (ROOT/'data/meshes'/model).is_file()
chest=next(r for r in items if r['sig']==b'CONT')
assert chest['form']==expected['AAAllBowsTestChest']
parts=list(subrecords(chest['data']))
inventory=[struct.unpack('<II',v) for k,v in parts if k==b'CNTO']
assert len(inventory)==9
assert struct.unpack('<I',dict(parts)[b'COCT'])[0]==9
assert all((r['form'],1) in inventory for r in weapons)
assert dict(parts)[b'FULL'].rstrip(b'\0').decode('utf-8')=='异界弓藏·试武箱'
# This release appends records; previous weapon, static and recipe bytes must survive.
baseline=list(records(ROOT/'build/before-0.4.1/ArcaneArsenal.esp'))
for old in baseline:
    if old['sig'] in (b'WEAP',b'STAT',b'COBJ',b'CONT'):
        assert by_form[old['form']]==old,edid(old)
quest=next(r for r in items if r['sig']==b'QUST')
assert quest['form']==0x01000819 and edid(quest)=='AARedDrawFXQuest'
qp=dict(subrecords(quest['data']))
assert struct.unpack('<I',qp[b'ALFR'])[0]==0x14
assert struct.unpack_from('<H',qp[b'DNAM'])[0]==0x111
assert b'AARedDrawFX' in qp[b'VMAD']
assert (ROOT/'data/seq/ArcaneArsenal.seq').read_bytes()==struct.pack('<I',quest['form'])
assert (ROOT/'data/scripts/AARedDrawFX.pex').read_bytes()[:4]==bytes.fromhex('fa57c0de')
report={'version':'0.4.1','passed':True,'Chinese_names':names,'existing_FormIDs_preserved':True,'existing_weapon_records_byte_identical':True,'ESL':True,'test_chest_items':9,'draw_fx_quest':'000819'}
(ROOT/'build/plugin-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
