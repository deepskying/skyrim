"""Append the staff prototype to the current plugin without rebuilding other weapons.

Owns B00..B7F only. Derives the self index from the existing master list, so
Dawnguard/crossbow integration and existing local save identities are preserved.
"""
from pathlib import Path
import collections,struct,json,shutil
from plugin_records import records,subrecords,edid,sub,encode,group
ROOT=Path(__file__).resolve().parents[1]
U=lambda n:struct.pack('<I',n)
Z=lambda s:s.encode('utf-8')+b'\0'

def build(path=None):
    path=path or ROOT/'data/ArcaneArsenal.esp'
    original=path.read_bytes()
    baseline=ROOT/'build'/('staves-before-plugin.esp' if path.parent.name=='data' else 'staves-preview-before-plugin.esp')
    if not baseline.exists():baseline.write_bytes(original)
    existing=list(records(path));header=existing[0]
    masters=[v for k,v in subrecords(header['data']) if k==b'MAST']
    self_index=len(masters);F=lambda n:self_index<<24|n
    master=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data\Skyrim.esm')
    vanilla=list(records(master,{b'WEAP',b'STAT',b'ENCH',b'MGEF',b'SPEL',b'PROJ',b'CONT',b'KYWD',b'MISC'}))
    byid={r['form']:r for r in vanilla};byn={edid(r).lower():r for r in vanilla}
    def rec(sig,local,name,parts):
        return dict(sig=sig,form=F(local),version=44,flags=0,data=sub(b'EDID',Z(name))+b''.join(sub(k,v) for k,v in parts))
    def clone(base,local,name,changes,remove=()):
        parts=[];seen=set()
        for k,v in subrecords(base['data']):
            if k in remove or k==b'EDID':continue
            parts.append((k,changes.get(k,v)));seen.add(k)
        parts.extend((k,v) for k,v in changes.items() if k not in seen)
        return rec(base['sig'],local,name,parts)
    new=[];specs=json.loads((ROOT/'source/arcane_staves_catalog.json').read_text(encoding='utf-8'))
    weapon=byn['stafffirebolt'];wp=dict(subrecords(weapon['data']));fp=byid[struct.unpack('<I',wp[b'WNAM'])[0]]
    template_effect=byid[0x12F03];effect_data=dict(subrecords(template_effect['data']))[b'DATA']
    projectile=byid[struct.unpack_from('<I',effect_data,72)[0]]
    descriptions=['命中叠加炬印，4秒内第三次命中引爆。','发射穿透灵梭，折返时锁定施法者位置并沿直线返回。','向前依次展开四道寒阶，减速并在末段短暂定身。','命中位置留下固定裂隙，1.2秒后爆炸。']
    bounds=struct.pack('<6h',-14,-71,-6,14,77,6)
    for i,s in enumerate(specs):
        local=0xB00+3*i;key=s['key'];name=s['name'];ench=0xB30+i;cost=[20,30,30,40][i];charge=[.45,.55,.65,.7][i]
        model='weapons\\arcanearsenal\\staves\\'+key+'.nif'
        new.append(clone(fp,local,'AA'+key+'1stPerson',{b'MODL':Z('weapons\\arcanearsenal\\staves\\1stperson'+key+'.nif'),b'OBND':bounds},(b'MODT',b'MODS')))
        new.append(clone(weapon,local+1,'AA'+key,{b'FULL':Z(name),b'MODL':Z(model),b'OBND':bounds,b'EITM':U(F(ench)),b'EAMT':struct.pack('<H',1000),b'WNAM':U(F(local)),b'DESC':Z(descriptions[i]),b'DATA':struct.pack('<IfH',1800,8.,0)},(b'MODT',b'MODS',b'CNAM')))
        recipe=[(b'COCT',U(2)),(b'CNTO',struct.pack('<II',byn['ingotsilver']['form'],2)),(b'CNTO',struct.pack('<II',byn['ingotmalachite']['form'],3)),(b'CNAM',U(F(local+1))),(b'BNAM',U(byn['craftingsmithingforge']['form'])),(b'NAM1',struct.pack('<H',1))]
        new.append(rec(b'COBJ',local+2,'AARecipe'+key,recipe))
        new.append(rec(b'ENCH',ench,'AAStaffEnchant'+str(i),[(b'OBND',bytes(12)),(b'FULL',Z(name)),(b'ENIT',struct.pack('<6IfII',cost,1,1,cost,2,12,charge,0,0)),(b'EFID',U(F(0xB34+i))),(b'EFIT',struct.pack('<fII',0.,0,0))]))
        data=bytearray(effect_data)
        struct.pack_into('<I',data,0,5|0x8000|0x200|0x400|0x800|0x10) # hostile AI, inert launch carrier
        struct.pack_into('<f',data,4,1.)
        struct.pack_into('<i',data,12,20) # Destruction, as on the vanilla staff carrier
        for off in (24,32,36,76,92,96,100,104,108,116,120,124,128,132,136):struct.pack_into('<I',data,off,0)
        struct.pack_into('<I',data,64,1) # script archetype, no script: native owns effects
        struct.pack_into('<I',data,72,F(0xB38+i))
        struct.pack_into('<f',data,48,charge)
        struct.pack_into('<f',data,144,30.)
        new.append(rec(b'MGEF',0xB34+i,'AAStaffCarrier'+str(i),[(b'FULL',Z(name)),(b'DATA',bytes(data)),(b'DNAM',Z(descriptions[i]))]))
        pd=bytearray(dict(subrecords(projectile['data']))[b'DATA'])
        struct.pack_into('<HHfff',pd,0,0,1,0.,2200.,8192.)
        for off in (16,20,36,40,56,60,64):struct.pack_into('<I',pd,off,0)
        struct.pack_into('<f',pd,76,4.)
        new.append(clone(projectile,0xB38+i,'AAStaffProjectile'+str(i),{b'DATA':bytes(pd),b'FULL':Z(name),b'MODL':Z('weapons\\arcanearsenal\\staves\\fx'+str(i)+'.nif')},(b'MODT',b'MODS',b'NAM1',b'NAM2')))
    # Engine-applied health / recoverable speed effects. Damage never writes AVs directly.
    for j,(resist,av,recover) in enumerate([(41,24,False),(44,24,False),(43,24,False),(43,30,True),(43,30,True)]):
        d=bytearray(152)
        struct.pack_into('<IfIii',d,0,5|0x8000|(2 if recover else 0x200),0.,0,-1,resist)
        struct.pack_into('<II',d,64,0,av)
        struct.pack_into('<IIi',d,80,1,3,-1)
        new.append(rec(b'MGEF',0xB40+j,'AAStaffDamageEffect'+str(j),[(b'FULL',Z('法杖效果')),(b'DATA',bytes(d)),(b'DNAM',Z(''))]))
    primary=next(r for r in new if r['form']==F(0xB40))
    script=b'AAStaffRedHit'
    vmad=struct.pack('<HHHH',5,2,1,len(script))+script+struct.pack('<BH',0,0)
    redhit=clone(primary,0xB45,'AAStaffPrimaryRedDamage',{b'VMAD':vmad})
    # VMAD precedes FULL/DATA in the schema.
    rp=list(subrecords(redhit['data']));redhit['data']=sub(b'EDID',rp[0][1])+sub(b'VMAD',vmad)+b''.join(sub(k,v) for k,v in rp[1:] if k!=b'VMAD');new.append(redhit)
    for j,(effect,mag,duration) in enumerate([(5,30,0),(0,90,0),(1,45,0),(2,15,0),(1,15,0),(1,105,0),(3,25,2),(4,100,1)]):
        spit=struct.pack('<IIIfIII fI',0,1,0,0.,1,3,0,0.,0)
        new.append(rec(b'SPEL',0xB48+j,'AAStaffPayload'+str(j),[(b'OBND',bytes(12)),(b'FULL',Z('法杖专属效果')),(b'ETYP',U(0x13F45)),(b'DESC',Z('')),(b'SPIT',spit),(b'EFID',U(F(0xB40+effect))),(b'EFIT',struct.pack('<fII',mag,0,duration))]))
    for j in range(8):
        new.append(clone(fp,0xB50+j,'AAStaffVisual'+str(j),{b'MODL':Z('weapons\\arcanearsenal\\staves\\fx'+str(j)+'.nif'),b'OBND':struct.pack('<6h',-256,-256,-64,256,256,64)},(b'MODT',b'MODS')))
    new.append(rec(b'FLST',0xB59,'AAStaffTemporaryReferences',[]))
    chest=byn['treaschestsmallemptynorespawn']
    ch=clone(chest,0xB0C,'AAStavesTestChest',{b'FULL':Z('几何法杖·试武箱')},(b'MODT',b'COCT',b'CNTO'))
    inv=sub(b'COCT',U(4))+b''.join(sub(b'CNTO',struct.pack('<II',F(0xB01+3*i),1)) for i in range(4))
    ch['data']=b''.join((inv if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(ch['data']));new.append(ch)
    owned=lambda r:(r['form']>>24)==self_index and 0xB00<=(r['form']&0xFFFFFF)<=0xB7F
    for r in existing[1:]:
        if owned(r):assert edid(r).startswith(('AAstaff','AARecipe','AAStaff','AAStaves')),edid(r)
    kept=[r for r in existing[1:] if not owned(r)]
    for r in kept:
        if edid(r)=='AAAllBowsTestChest':
            parts=[(k,v) for k,v in subrecords(r['data']) if k not in (b'COCT',b'CNTO')]
            items=[v for k,v in subrecords(r['data']) if k==b'CNTO' and not 0xB00<=(struct.unpack_from('<I',v)[0]&0xFFFFFF)<=0xB7F]
            items += [struct.pack('<II',F(0xB01+3*i),1) for i in range(4)]
            inv=sub(b'COCT',U(len(items)))+b''.join(sub(b'CNTO',v) for v in items)
            r['data']=b''.join((inv if k==b'DATA' else b'')+sub(k,v) for k,v in parts)
    allrecords=kept+new
    weapon_count=sum(r['sig']==b'WEAP' for r in allrecords);chest_count=sum(r['sig']==b'CONT' for r in allrecords)
    description=Z(f'{weapon_count} weapons, {chest_count} test chests; geometric staff spell prototypes. Skyrim SE 1.5.97. <cp:utf8>')
    header['data']=b''.join(sub(k,struct.pack('<fII',1.7,len(allrecords),max(0xB80,max(r['form']&0xFFFFFF for r in allrecords)+1)) if k==b'HEDR' else description if k==b'SNAM' else v) for k,v in subrecords(header['data']))
    groups=collections.defaultdict(list)
    for r in allrecords:groups[r['sig']].append(r)
    assert len({r['form'] for r in allrecords})==len(allrecords)
    # Follow Skyrim.esm's top-level order. MagicItem loading resolves EFID while
    # reading it; emitting ENCH before its new MGEF can leave an empty effect list.
    # The item-card perk path dereferences GetCostliestEffectItem without a null check.
    order=(b'MGEF',b'ENCH',b'SPEL',b'CONT',b'STAT',b'WEAP',b'COBJ',b'PROJ',b'QUST',b'FLST')
    assert set(groups)<=set(order), 'Add new record types in Skyrim.esm order'
    output=encode(header)+b''.join(group(k,groups[k]) for k in order if k in groups)
    assert path.read_bytes()==original,'Plugin changed concurrently'
    path.write_bytes(output)
    report=dict(records=len(new),self_index=self_index,masters=[x.rstrip(b'\0').decode() for x in masters],weapons=[dict(key=s['key'],name=s['name'],local_form=hex(0xB01+3*i)) for i,s in enumerate(specs)],gameplay_tested=False)
    (ROOT/'build/staff-plugin-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__':build()
