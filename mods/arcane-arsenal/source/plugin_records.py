"""Small, bounded TES4 record reader/writer for this standalone weapon plugin."""
from pathlib import Path
import struct
import zlib

HEADER = struct.Struct('<4sIIIIHH')

def records(path, wanted=None):
    data = Path(path).read_bytes()
    def walk(start, end):
        pos = start
        while pos < end:
            sig, size = struct.unpack_from('<4sI', data, pos)
            if sig == b'GRUP':
                assert size >= 24 and pos + size <= end
                label, kind = struct.unpack_from('<4si', data, pos + 8)
                if wanted is None or kind != 0 or label in wanted:
                    yield from walk(pos + 24, pos + size)
                pos += size
            else:
                sig, size, flags, form, rev, version, unknown = HEADER.unpack_from(data, pos)
                assert pos + 24 + size <= end
                if wanted is None or sig in wanted:
                    payload = data[pos+24:pos+24+size]
                    if flags & 0x40000:
                        expected = struct.unpack_from('<I', payload)[0]
                        payload = zlib.decompress(payload[4:])
                        assert len(payload) == expected
                    yield {'sig':sig, 'flags':flags & ~0x40000, 'form':form,
                           'version':version, 'data':payload}
                pos += 24 + size
        assert pos == end
    yield from walk(0, len(data))

def subrecords(data):
    pos = 0
    extended = None
    while pos < len(data):
        sig, size = struct.unpack_from('<4sH', data, pos)
        pos += 6
        if sig == b'XXXX':
            assert size == 4
            extended = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            continue
        if extended is not None:
            size, extended = extended, None
        assert pos + size <= len(data)
        yield sig, data[pos:pos+size]
        pos += size
    assert pos == len(data)

def edid(record):
    return next((v.rstrip(b'\0').decode('ascii') for k,v in subrecords(record['data']) if k == b'EDID'), '')

def sub(sig, value):
    if len(value) > 65535:
        return b'XXXX\x04\x00' + struct.pack('<I',len(value)) + sig + b'\0\0' + value
    return struct.pack('<4sH',sig,len(value)) + value

def encode(record):
    payload=record['data']
    return HEADER.pack(record['sig'], len(payload), record.get('flags',0),record['form'],0,record.get('version',44),0)+payload

def group(sig, items):
    body=b''.join(encode(r) for r in items)
    return struct.pack('<4sI4siHHHH',b'GRUP',len(body)+24,sig,0,0,0,0,0)+body

if __name__ == '__main__':
    import json,sys
    source=Path(sys.argv[1])
    matches=[]
    for r in records(source,{b'WEAP',b'STAT',b'ENCH',b'COBJ',b'MISC',b'KYWD'}):
        name=edid(r)
        if name in {'IronBow','IronBow1stPerson','IngotSilver','IngotRefinedMalachite','WorkbenchForge','CraftingSmithingSharpeningWheel'} or ('Ench' in name and 'Frost' in name and '01' in name):
            matches.append({'sig':r['sig'].decode(),'form':hex(r['form']),'edid':name,'subrecords':[(k.decode(),v.hex() if len(v)<120 else str(len(v))+' bytes') for k,v in subrecords(r['data'])]})
    print(json.dumps(matches,indent=2))
