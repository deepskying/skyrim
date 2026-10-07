"""Verify record compatibility, dependency completeness and real model buffers."""
import json,sys,math,struct
from catalog import ROOT,PLUGIN,catalog
sys.path.insert(0,str(ROOT.parent/'magic-arrows/source'))
from paths import ADDON
from plugin_records import records,subrecords,edid
from nif_blocks import NifBlocks
from pyn.pynifly import NifFile
def main():
    old={r['form']:r for r in records(ROOT/'source/upstream'/PLUGIN)}
    new={r['form']:r for r in records(ROOT/'data'/PLUGIN)}
    assert len(new)==len(old)+1 and set(old)<=set(new)
    for id,r in old.items():
        modified=new[id];assert r['sig']==modified['sig'] and r['flags']==modified['flags']
        allowed={b'HEDR'} if r['sig']==b'TES4' else {b'MODL',b'MODT'} if r['sig']==b'ALCH' else {b'DNAM'} if r['sig']==b'MGEF' else {b'DESC'} if r['sig']==b'MESG' else set()
        assert [(k,v) for k,v in subrecords(r['data']) if k not in allowed]==[(k,v) for k,v in subrecords(modified['data']) if k not in allowed]
    models=[]
    for row in catalog():
        r=new[0x01000000|row['form']];assert r['sig']==b'ALCH'
        subs=list(subrecords(r['data']));assert next(v for k,v in subs if k==b'EFID')==struct.pack('<I',0x01000000|row['effect'])
        path=ROOT/'data/meshes/DivineBlood'/(row['key']+'.nif');n=NifBlocks(path);nf=NifFile(str(path))
        assert len(nf.shapes)==2 and [kind for kind,_ in n.blocks].count('bhkCollisionObject')==1
        count=0
        for s in nf.shapes:
            assert all(math.isfinite(c) for v in s.verts for c in v)
            for a,b,c in s.tris:
                va,vb,vc=(s.verts[i] for i in (a,b,c))
                ab=[vb[i]-va[i] for i in range(3)];ac=[vc[i]-va[i] for i in range(3)]
                area=sum((ab[(i+1)%3]*ac[(i+2)%3]-ab[(i+2)%3]*ac[(i+1)%3])**2 for i in range(3));assert area>1e-12
            count+=len(s.tris)
        assert (ROOT.parent/'durability-manager/web/public/divine-blood'/(row['key']+'.png')).is_file()
        models.append(dict(key=row['key'],triangles=count))
    pex=ROOT/'data/Scripts/OP_Increase_PC_Stats_Permanently.pex'
    assert pex.read_bytes()[:4]==bytes.fromhex('FA57C0DE')
    assert b'DivineBloodAbsorbed' in pex.read_bytes()
    rules=(ROOT/'data/DivineBlood_DISTR.ini').read_text(encoding='utf-8').splitlines()
    assert len([l for l in rules if l.startswith('Item = ')])==16
    (ROOT/'build/verification.json').write_text(json.dumps(dict(preservedRecords=len(old),newRecords=len(new),models=models,papyrusBytes=pex.stat().st_size),indent=2),encoding='utf-8')
    print(f'Verified {len(old)} preserved records, missing Akatosh item, 16 meshes/icons, compiled PEX and 16 isolated SPID rules')
if __name__=='__main__':main()
