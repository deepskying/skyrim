"""Import manifest, isolated distribution rules, stable-record plugin rebuild."""
import sys, json, hashlib, struct, shutil
from collections import defaultdict
from catalog import ROOT, PLUGIN, catalog
sys.path.insert(0,str(ROOT.parent/'magic-arrows/source'))
from plugin_records import records, subrecords, sub, edid, encode, group

def main():
    upstream=ROOT/'source/upstream'; data=ROOT/'data'; data.mkdir(exist_ok=True)
    rows=catalog(); recs=list(records(upstream/PLUGIN)); by_id={r['form']&0xffffff:r for r in recs}
    assert 0xD7B not in by_id, 'Akatosh ID collision'
    extra=dict(by_id[0x800]);extra['form']=0x01000D7B
    extra['data']=b''.join(sub(k,
        b'OP_ALCH_shout_rec_Modify\0' if k==b'EDID' else
        '+阿卡托什之血'.encode()+b'\0' if k==b'FULL' else
        struct.pack('<I',0x01000D7C) if k==b'EFID' else v)
        for k,v in subrecords(extra['data']))
    recs.append(extra)
    for r in recs:
        if r['sig']==b'MGEF':
            row=next((row for row in rows if row['effect']==r['form']&0xffffff),None)
            if row:r['data']=b''.join(sub(k,('永久'+row['gain']+'。').encode()+b'\0' if k==b'DNAM' else v) for k,v in subrecords(r['data']))
        elif r['sig']==b'MESG':
            r['data']=b''.join(sub(k,v.replace(b'10',b'1') if k==b'DESC' else v) for k,v in subrecords(r['data']))
    for row in rows:
        r=next(r for r in recs if r['sig']==b'ALCH' and r['form']&0xffffff==row['form'])
        row['editorID']=edid(r)
        r['data']=b''.join(sub(k,('DivineBlood\\'+row['key']+'.nif').encode()+b'\0' if k==b'MODL' else v)
                         for k,v in subrecords(r['data']) if k!=b'MODT')
    header=recs[0]
    header['data']=b''.join(sub(k,struct.pack('<fII',1.7,len(recs)-1,0xD8D) if k==b'HEDR' else v)
                          for k,v in subrecords(header['data']))
    groups=defaultdict(list)
    for r in recs[1:]:groups[r['sig']].append(r)
    (data/PLUGIN).write_bytes(encode(header)+b''.join(group(k,v) for k,v in groups.items()))
    (ROOT/'catalog.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    web=ROOT.parent/'durability-manager/web/src/arrows/divine-demo.ts'
    web.write_text("import type { DivineBlood } from './types';\nexport const divineDemo: DivineBlood = "+json.dumps(dict(available=True,epoch=1,
        cards=[dict(key=r['key'],name=r['name'],gain=r['gain'],absorbed=0,owned=0,soulCost=10,alchemyCost=10) for r in rows],
        materials=[dict(id=1001,name='蓝山花',count=18,points={'health':1}),dict(id=1002,name='小麦',count=9,points={'health':1}),dict(id=1003,name='红山花',count=20,points={'magicka':1}),dict(id=1004,name='紫山花',count=20,points={'stamina':1})]),ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
    native=ROOT/'native/src';native.mkdir(parents=True,exist_ok=True)
    declarations=[]
    for row in rows:
        avs=(row['actorValues']+[-1]*3)[:3]
        declarations.append('    Recipe{"%s", "%s", "%s", 0x%X, {%s}},'%
                            (row['key'],row['name'],row['gain'],row['form'],','.join(map(str,avs))))
    (native/'catalog.h').write_text('#pragma once\n#include <array>\nnamespace divine_blood {\n'
        'struct Recipe {const char* key;const char* name;const char* gain;unsigned form;std::array<int,3> actorValues;};\n'
        'inline constexpr std::array<Recipe,16> recipes{{\n'+'\n'.join(declarations)+'\n}};\n}\n',encoding='utf-8')
    ini=data/'SKSE/Plugins/DivineBlood.ini';ini.parent.mkdir(parents=True,exist_ok=True)
    if not ini.exists():ini.write_text('; Costs grow by 10% for every 10 absorbed units of the same blood.\n'
        '; Ingredient points are independent of Alchemy skill.\n'+''.join(
        f'\n[{r["key"]}]\nSoulCost=10\nAlchemyCost=10\nPointsPerIngredient=1\n' for r in rows),encoding='ascii')
    # Separate file keeps the original probabilities, including Zenithar's 10%.
    (data/'DivineBlood_DISTR.ini').write_text('; Preserved legacy SPID rules; remove the old divine block before enabling this file.\n'+
        '\n'.join('Item = '+r['editorID']+'|NONE|NONE|NONE|NONE|1|'+('10' if r['key']=='carry_weight' else '5') for r in rows)+'\n',encoding='utf-8')
    manifest=[dict(path=str(f.relative_to(upstream)),size=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest())
              for f in upstream.rglob('*') if f.is_file()]
    (ROOT/'source/upstream-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
