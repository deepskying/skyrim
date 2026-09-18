"""Normalize existing Arcane Armory self references after adding official masters.

Only typed FormID fields from this plugin's known record schema are rewritten.
This helper is used for identity regression checks, not byte-pattern replacement.
"""
import struct
from plugin_records import subrecords,sub
def remap_self(record,old,new):
    def form(value):return (new<<24)|(value&0xffffff) if value>>24==old else value
    result=dict(record);result['form']=form(record['form']);parts=[]
    for key,value in subrecords(record['data']):
        data=bytearray(value)
        if (record['sig'],key) in {(b'WEAP',b'WNAM'),(b'COBJ',b'CNAM'),(b'CONT',b'CNTO')}:
            struct.pack_into('<I',data,0,form(struct.unpack_from('<I',data)[0]))
        elif record['sig']==b'QUST' and key==b'VMAD':
            assert struct.unpack_from('<HHH',data)==(5,2,0)
            assert struct.unpack_from('<I',data,17)[0]==(old<<24)|0x819
            struct.pack_into('<I',data,17,(new<<24)|0x819)
        parts.append(sub(key,bytes(data)))
    result['data']=b''.join(parts)
    return result
