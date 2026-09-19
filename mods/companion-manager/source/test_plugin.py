"""Structural checks against the emitted ESP, independent of the builder's globals."""
import struct
import unittest
from pathlib import Path
from plugin_records import records, subrecords, edid

ROOT=Path(__file__).resolve().parents[1]
class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=list(records(ROOT/'data/CompanionManager.esp'))
        cls.packages={r['form']:r for r in cls.rows if r['sig']==b'PACK'}
        cls.quest=next(r for r in cls.rows if r['sig']==b'QUST')
        cls.parts=list(subrecords(cls.quest['data']))

    def test_esl_has_no_overrides_or_third_party_dependencies(self):
        header=self.rows[0]
        self.assertEqual(header['sig'],b'TES4');self.assertEqual(header['flags']&0x200,0x200)
        self.assertEqual([v for k,v in subrecords(header['data']) if k==b'MAST'],[b'Skyrim.esm\0'])
        ids=[r['form'] for r in self.rows[1:]]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(all(0x01000800<=n<0x01001000 for n in ids))
        self.assertEqual(set(r['sig'] for r in self.rows[1:]),{b'FACT',b'PACK',b'QUST',b'DLBR',b'DIAL',b'INFO'})

    def test_outfit_dialogue_is_owned_scoped_and_scripted(self):
        by_type={r['sig']:dict(subrecords(r['data'])) for r in self.rows if r['sig'] in (b'DLBR',b'DIAL',b'INFO')}
        branch,topic,info=(by_type[k] for k in (b'DLBR',b'DIAL',b'INFO'))
        self.assertEqual(branch[b'QNAM'],struct.pack('<I',0x01000800))
        self.assertEqual(branch[b'DNAM'],struct.pack('<I',1)) # top-level, not blocking/exclusive
        self.assertEqual(branch[b'SNAM'],struct.pack('<I',0x01000B01))
        self.assertEqual(topic[b'BNAM'],struct.pack('<I',0x01000B00))
        self.assertEqual(topic[b'QNAM'],branch[b'QNAM'])
        self.assertEqual(topic[b'FULL'].decode('utf8').rstrip('\0'),'随机换装')
        self.assertEqual(topic[b'TIFC'],struct.pack('<I',1))
        self.assertEqual(info[b'TPIC'],branch[b'SNAM'])
        self.assertEqual(struct.unpack('<HH',info[b'ENAM']),(0x801,0))
        row=next(r for r in self.rows if r['sig']==b'INFO')
        conditions=[v for k,v in subrecords(row['data']) if k==b'CTDA']
        self.assertEqual([(struct.unpack_from('<H',c,8)[0],struct.unpack_from('<I',c,12)[0],struct.unpack_from('<f',c,4)[0]) for c in conditions],
                         [(71,0x01000801,1),(453,0,1),(46,0,0),(289,0,0)])
        self.assertTrue(all(c[0]==0 for c in conditions))
        vmad=info[b'VMAD']; offset=6
        def string():
            nonlocal offset
            n=struct.unpack_from('<H',vmad,offset)[0];offset+=2
            value=vmad[offset:offset+n].decode();offset+=n;return value
        self.assertEqual(struct.unpack_from('<HHH',vmad),(5,2,1))
        self.assertEqual(string(),'CMRandomOutfitTopic')
        self.assertEqual(vmad[offset:offset+3],b'\0\0\0');offset+=3
        self.assertEqual(vmad[offset:offset+2],b'\x02\x01');offset+=2 # OnBegin
        self.assertEqual(string(),'CMRandomOutfitTopic')
        self.assertEqual(vmad[offset],1);offset+=1 # fragment version, matching vanilla INFO
        self.assertEqual(string(),'CMRandomOutfitTopic');self.assertEqual(string(),'Fragment_0')
        self.assertEqual(offset,len(vmad))
        for script in ('CMDialogue','CMRandomOutfitTopic'):
            self.assertEqual((ROOT/f'data/Scripts/{script}.pex').read_bytes()[:4],bytes.fromhex('fa57c0de'))

    def test_optional_aliases_cannot_autofill_and_all_packages_resolve(self):
        aliases=[];active=None
        for k,v in self.parts:
            if k==b'ALST':active={'id':struct.unpack('<I',v)[0],'conditions':[],'packages':[]};aliases.append(active)
            elif active is not None:
                if k==b'FNAM':active['flags']=struct.unpack('<I',v)[0]
                if k==b'CTDA':active['conditions'].append(v)
                if k==b'ALPC':active['packages'].append(struct.unpack('<I',v)[0])
        self.assertEqual([a['id'] for a in aliases],list(range(256)))
        self.assertEqual(next(struct.unpack('<I',v)[0] for k,v in self.parts if k==b'ANAM'),256)
        for a in aliases:
            self.assertTrue(a['flags']&2);self.assertFalse(a['flags']&4)
            self.assertEqual(len(a['conditions']),2)
            self.assertEqual([struct.unpack_from('<f',c,4)[0] for c in a['conditions']],[0,1])
            for c in a['conditions']:
                self.assertEqual(struct.unpack_from('<H',c,8)[0],72)
                self.assertEqual(struct.unpack_from('<I',c,12)[0],0x14)
                self.assertEqual(c[0],0) # Equal, AND; impossible conjunction
            if a['id']<64:
                self.assertEqual(len(a['packages']),13)
                self.assertTrue(all(p in self.packages for p in a['packages']))
                home=self.packages[a['packages'][0]]
                locations=[struct.unpack('<III',v) for k,v in subrecords(home['data']) if k==b'PLDT']
                self.assertEqual(locations,[(8,64+a['id'],512)])
                self.assertEqual(home['form'],0x01000900+a['id'])
                activity=self.packages[a['packages'][1]]
                self.assertEqual([struct.unpack('<III',v) for k,v in subrecords(activity['data']) if k==b'PLDT'],[(8,128+a['id'],64)])
                self.assertEqual(edid(activity),f"CMActivity{a['id']:02}")
            else:self.assertEqual(a['packages'],[])

    def test_packages_have_scoped_owner_and_mode(self):
        modes=set()
        for r in self.packages.values():
            parts=list(subrecords(r['data']))
            self.assertEqual([struct.unpack('<I',v)[0] for k,v in parts if k==b'QNAM'],[self.quest['form']])
            condition=next(v for k,v in parts if k==b'CTDA')
            self.assertEqual(struct.unpack_from('<H',condition,8)[0],73)
            self.assertEqual(struct.unpack_from('<I',condition,12)[0],0x01000801)
            modes.add(int(struct.unpack_from('<f',condition,4)[0]))
            if edid(r).startswith('CMFollow'):
                self.assertEqual([struct.unpack('<III',v) for k,v in parts if k==b'PTDA'],[(0,0x14,0)])
        self.assertEqual(modes,{1,2,3,4,5,11,12,21,22,100})

    def test_retired_needs_have_no_active_records(self):
        self.assertFalse(any(edid(r).startswith(('CMRest','CMWater')) for r in self.rows))
        self.assertFalse(any(r['sig'] in (b'ALCH',b'COBJ') for r in self.rows))

    def test_script_binding_and_bytecode(self):
        vmad=next(v for k,v in self.parts if k==b'VMAD')
        self.assertEqual(struct.unpack_from('<HHH',vmad),(5,2,1))
        length=struct.unpack_from('<H',vmad,6)[0]
        self.assertEqual(vmad[8:8+length],b'CMController')
        self.assertEqual(vmad[8+length:],b'\0\0\0\2\0\0\0\0\0\0')
        self.assertEqual((ROOT/'data/Scripts/CMController.pex').read_bytes()[:4],bytes.fromhex('fa57c0de'))

if __name__=='__main__':unittest.main()
