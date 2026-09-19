"""Staff graph, preservation, asset and reproducibility checks (not gameplay QA)."""
from pathlib import Path
import sys,json,struct,hashlib
from plugin_records import records,subrecords,edid
ROOT=Path(__file__).resolve().parents[1]
path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/ArcaneArsenal.esp'
rs=list(records(path));byid={r['form']:r for r in rs};header=rs[0]
self_index=len([1 for k,v in subrecords(header['data']) if k==b'MAST']);F=lambda n:self_index<<24|n
# Model the load-time references, not only whether a target exists somewhere.
# Forward EFID references passed the old validator but can load as empty magic items.
loaded={}
for r in rs:
    for k,v in subrecords(r['data']):
        if k in (b'EFID',b'EITM'):
            target=struct.unpack('<I',v)[0]
            if target>>24==self_index:
                expected=b'MGEF' if k==b'EFID' else b'ENCH'
                assert target in loaded and loaded[target]==expected, (edid(r),k,'forward or invalid effect reference')
    loaded[r['form']]=r['sig']
owned=[r for r in rs if r['form']>>24==self_index and 0xB00<=r['form']&0xFFFFFF<=0xB7F]
assert len(rs)==len(byid) and len(owned)==48
assert header['flags']&0x200
assert struct.unpack_from('<I',dict(subrecords(header['data']))[b'HEDR'],4)[0]==len(rs)-1
assert not any(0x90C<=r['form']&0xFFFFFF<=0x918 for r in rs[1:])
specs=json.loads((ROOT/'source/arcane_staves_catalog.json').read_text(encoding='utf-8'))
for i,s in enumerate(specs):
    w=byid[F(0xB01+3*i)];p=dict(subrecords(w['data']))
    assert edid(w)=='AA'+s['key'] and p[b'FULL']==s['name'].encode()+b'\0'
    assert p[b'DNAM'][0]==8,'Not a staff'
    assert struct.unpack('<H',p[b'EAMT'])[0]==1000
    assert struct.unpack('<I',p[b'EITM'])[0]==F(0xB30+i)
    assert struct.unpack('<I',p[b'WNAM'])[0]==F(0xB00+3*i)
    e=dict(subrecords(byid[F(0xB30+i)]['data']))
    cost,flags,cast,amount,delivery,typ,charge,base,worn=struct.unpack('<6IfII',e[b'ENIT'])
    assert (cost,flags,cast,amount,delivery,typ)==([20,30,30,40][i],1,1,[20,30,30,40][i],2,12)
    assert abs(charge-[.45,.55,.65,.7][i])<1e-5
    assert struct.unpack('<I',e[b'EFID'])[0]==F(0xB34+i)
    d=dict(subrecords(byid[F(0xB34+i)]['data']))[b'DATA']
    assert struct.unpack_from('<I',d,72)[0]==F(0xB38+i)
    assert struct.unpack_from('<II',d,80)==(1,2)
    assert struct.unpack_from('<i',d,12)[0]==20,'Staff carrier must have a valid magic school'
    assert not struct.unpack_from('<I',d,0)[0]&0x1000000,'Carrier excluded from costliest-effect selection'
    assert struct.unpack_from('<f',d,4)[0]>0,'Carrier needs a positive base cost'
for r in owned:
    for k,v in subrecords(r['data']):
        if k==b'MODL' and r['sig']!=b'CONT':assert (ROOT/'data/meshes'/v.rstrip(b'\0').decode().replace('\\','/')).is_file()
        if k in (b'EFID',b'EITM',b'WNAM'):
            form=struct.unpack('<I',v)[0];assert form in byid
    if r['sig']==b'SPEL':
        p=dict(subrecords(r['data']));assert len(p[b'SPIT'])==36
        assert struct.unpack_from('<II',p[b'SPIT'],16)==(1,3)
        effect=byid[struct.unpack('<I',p[b'EFID'])[0]];d=dict(subrecords(effect['data']))[b'DATA']
        assert struct.unpack_from('<II',d,80)==(1,3)
        assert struct.unpack_from('<I',d,72)[0]==0,'Payload must not launch secondary projectile'
vmad=dict(subrecords(byid[F(0xB45)]['data']))[b'VMAD']
assert vmad[8:8+len('AAStaffRedHit')]==b'AAStaffRedHit'
assert b'VMAD' not in dict(subrecords(byid[F(0xB40)]['data'])),'Explosion would recursively add marks'
for n in ('AAStaffRuntime','AAStaffRedHit'):
    assert (ROOT/'data/scripts'/(n+'.pex')).read_bytes()[:4]==bytes.fromhex('fa57c0de')
ch=next(r for r in owned if edid(r)=='AAStavesTestChest')
assert [struct.unpack('<II',v) for k,v in subrecords(ch['data']) if k==b'CNTO']==[(F(0xB01+3*i),1) for i in range(4)]
baseline=ROOT/'build'/('staves-before-plugin.esp' if path.parent.name=='data' else 'staves-preview-before-plugin.esp')
before=list(records(baseline));old={r['form']:r for r in before}
retired={0x03000000|(int(s['stat_form'],16)+offset) for s in json.loads((ROOT/'source/retired_weapons.json').read_text(encoding='utf-8')) for offset in range(3)}|{0x03000A17}
assert set(old)-retired<=set(byid)
for form,r in old.items():
    if r['sig']==b'TES4':continue
    if form in retired:continue
    if edid(r) in ('AAAllBowsTestChest','AAHeteromorphicCrossbowsChest','AAHeteromorphicWaraxesChest'):
        strip=lambda x:[(k,v) for k,v in subrecords(x['data']) if k not in (b'CNTO',b'COCT')]
        assert strip(r)==strip(byid[form])
    else:assert r==byid[form],edid(r)
report=dict(passed=True,staff_records=len(owned),existing_records_preserved=len(before)-2,gameplay_tested=False,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(ROOT/'build/staff-plugin-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
