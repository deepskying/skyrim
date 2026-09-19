"""Native ARMO/ARMA shield records, preserving race and equipment compatibility."""
from pathlib import Path
import json,struct,math
from plugin_records import records,subrecords,edid,sub
ROOT=Path(__file__).resolve().parents[1]
CATALOG=json.loads((ROOT/'source/shields_catalog.json').read_text('utf-8'))
CHEST_FORM=0x03000BAC
NEXT_FORM=0xBAD
U32=lambda n:struct.pack('<I',n)
Z=lambda s:s.encode('utf-8')+b'\0'

def build(master,by_name,changed):
    originals=list(records(master,{b'ARMO',b'ARMA'}))
    armor=next(r for r in originals if edid(r)=='ArmorElvenShield')
    addon_id=next(struct.unpack('<I',v)[0] for k,v in subrecords(armor['data']) if k==b'MODL')
    addon=next(r for r in originals if r['form']==addon_id)
    armors=[];addons=[];recipes=[]
    for spec in CATALOG:
        key=spec['key'];aid=0x03000000|int(spec['armor_form'],16);mid=0x03000000|int(spec['addon_form'],16)
        model=Z('armor\\arcanearsenal\\'+key+'.nif')
        report=json.loads((ROOT/'build'/(key+'-model.json')).read_text('utf-8'))
        bounds=report['bounds'];obnd=struct.pack('<6h',*[math.floor(a) for a,b in bounds],*[math.ceil(b) for a,b in bounds])
        # Preserve every repeated MODL race entry on ARMA. Same mesh for both sexes.
        aa=changed(addon,mid,{b'EDID':Z('AA'+key+'Addon'),b'BOD2':struct.pack('<II',0x200,0),b'MOD2':model,b'MOD3':model},(b'BODT',b'MO2T',b'MO3T',b'MO2S',b'MO3S'))
        # Keep BOD2 before RNAM in record schema.
        parts=list(subrecords(aa['data']));bod=next(v for k,v in parts if k==b'BOD2')
        aa['data']=b''.join((sub(b'BOD2',bod) if k==b'RNAM' else b'')+sub(k,v)+(sub(b'MOD3',model) if k==b'MOD2' else b'') for k,v in parts if k not in (b'BOD2',b'MOD3'))
        addons.append(aa)
        ar=changed(armor,aid,{b'EDID':Z('AA'+key),b'FULL':Z(spec['name']),b'DESC':b'\0',b'OBND':obnd,
            b'MOD2':model,b'MODL':U32(mid),b'DATA':struct.pack('<If',spec['value'],spec['weight']),b'DNAM':U32(spec['armor']*100)},(b'MO2T',b'MO2S'))
        armors.append(ar)
        ingredients=[('ingotsilver',2),('ingotmalachite',3)]
        d=sub(b'EDID',Z('AARecipe'+key))+sub(b'COCT',U32(len(ingredients)))
        for name,count in ingredients:d+=sub(b'CNTO',struct.pack('<II',by_name[name]['form'],count))
        d+=sub(b'CNAM',U32(aid))+sub(b'BNAM',U32(by_name['craftingsmithingforge']['form']))+sub(b'NAM1',struct.pack('<H',1))
        recipes.append(dict(sig=b'COBJ',form=0x03000000|int(spec['recipe_form'],16),version=44,data=d))
    chest=changed(by_name['treaschestsmallemptynorespawn'],CHEST_FORM,{b'EDID':Z('AAShieldsTestChest'),b'FULL':Z('幻律盾牌·试用箱')},(b'MODT',b'COCT',b'CNTO'))
    contents=sub(b'COCT',U32(len(armors)))+b''.join(sub(b'CNTO',struct.pack('<II',r['form'],1)) for r in armors)
    chest['data']=b''.join((contents if k==b'DATA' else b'')+sub(k,v) for k,v in subrecords(chest['data']))
    return armors,addons,recipes,chest
