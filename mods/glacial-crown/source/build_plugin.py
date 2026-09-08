"""Create a standalone ordinary ESP using verified vanilla records as templates."""
from pathlib import Path
import struct,json
from plugin_records import records,subrecords,edid,sub,encode,group

ROOT=Path(__file__).resolve().parents[1]
MASTER=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data\Skyrim.esm')
types={b'WEAP',b'STAT',b'ENCH',b'MISC',b'KYWD',b'INGR'}
source=list(records(MASTER,types))
by_name={edid(r).lower():r for r in source}
by_form={r['form']:r for r in source}
weapon=by_name['imperialbow']
parts=dict(subrecords(weapon['data']))
firstperson=by_form[struct.unpack('<I',parts[b'WNAM'])[0]]
enchant=by_name['enchweaponfrostdamage02']
IDS={'stat':0x01000800,'weapon':0x01000801,'craft':0x01000802}
model=b'weapons\\glacialcrown\\glacialcrown.nif\0'
U32=lambda n:struct.pack('<I',n)
Z=lambda s:s.encode('utf-8')+b'\0'
# Bounds cover the new crown and orbiting crystals, not just the source bow.
bounds=struct.pack('<6h',-18,-67,-7,29,67,9)

def changed(template,form,changes,remove=()):
    content=[];seen=set()
    for k,v in subrecords(template['data']):
        if k in remove: continue
        content.append(sub(k,changes.get(k,v)));seen.add(k)
        # Bethesda's weapon schema expects enchantment fields after the model.
        if template['sig']==b'WEAP' and k==b'MODL':
            for extra in (b'EITM',b'EAMT'):
                if extra in changes and extra not in parts:
                    content.append(sub(extra,changes[extra]));seen.add(extra)
    for k,v in changes.items():
        if k not in seen: content.append(sub(k,v))
    return {'sig':template['sig'],'flags':template['flags'],'form':form,'version':44,'data':b''.join(content)}

stat=changed(firstperson,IDS['stat'],{b'EDID':Z('GCGlacialCrown1stPerson'),b'OBND':bounds,b'MODL':model},(b'MODT',b'MODS'))
weap=changed(weapon,IDS['weapon'],{
    b'EDID':Z('GCGlacialCrown'),b'FULL':Z('Glacial Crown'),b'DESC':b'\0',b'OBND':bounds,
    b'MODL':model,b'WNAM':U32(IDS['stat']),b'EITM':U32(enchant['form']),b'EAMT':struct.pack('<H',1800),
    b'DATA':struct.pack('<IfH',1800,10.,18),
},(b'MODT',b'MODS',b'CNAM'))
ingredients=[('ingotsilver',2),('ingotmalachite',3),('frostsalts',2)]
craft_data=sub(b'EDID',Z('GCRecipeGlacialCrown'))+sub(b'COCT',U32(len(ingredients)))
for name,amount in ingredients: craft_data+=sub(b'CNTO',struct.pack('<II',by_name[name]['form'],amount))
craft_data+=sub(b'CNAM',U32(IDS['weapon']))+sub(b'BNAM',U32(by_name['craftingsmithingforge']['form']))+sub(b'NAM1',struct.pack('<H',1))
craft={'sig':b'COBJ','form':IDS['craft'],'version':44,'data':craft_data}
header={'sig':b'TES4','form':0,'version':44,'data':
    sub(b'HEDR',struct.pack('<fII',1.7,3,0x803))+
    sub(b'CNAM',Z('Glacial Crown prototype'))+
    sub(b'SNAM',Z('Original crystal bow. Prototype 0.1.0 for Skyrim SE 1.5.97.'))+
    sub(b'MAST',b'Skyrim.esm\0')+sub(b'DATA',b'\0'*8)}
dest=ROOT/'data/GlacialCrown.esp';dest.parent.mkdir(exist_ok=True,parents=True)
dest.write_bytes(encode(header)+group(b'STAT',[stat])+group(b'COBJ',[craft])+group(b'WEAP',[weap]))
parsed=list(records(dest));assert len(parsed)==4
assert {r['form'] for r in parsed if r['sig']!=b'TES4'}==set(IDS.values())
assert all(r['version']==44 for r in parsed)
report={'plugin':'GlacialCrown.esp','format':'ordinary ESP, HEDR 1.7, form version 44, no ESL flag',
        'masters':['Skyrim.esm'],'records':{edid(r):f"{r['form']:08X}" for r in parsed[1:]},
        'base_damage':18,'weight':10,'value':1800,'charge':1800,
        'enchantment':{'edid':edid(enchant),'form':f"{enchant['form']:08X}"},
        'recipe':dict(ingredients),'overrides':0}
(ROOT/'build/plugin-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
