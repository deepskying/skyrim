"""Check delivered x64 SKSE binary and native/Papyrus bridge artifacts."""
from pathlib import Path
import struct,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/SKSE/Plugins/ArcaneStaves.dll';data=p.read_bytes()
assert data[:2]==b'MZ'
pe=struct.unpack_from('<I',data,0x3C)[0];assert data[pe:pe+4]==b'PE\0\0'
machine,count=struct.unpack_from('<HH',data,pe+4);assert machine==0x8664
opt=pe+24;size=struct.unpack_from('<H',data,pe+20)[0]
assert struct.unpack_from('<H',data,opt)[0]==0x20B
sections=[]
for i in range(count):
    at=opt+size+i*40;virtual_size,rva,raw_size,raw=struct.unpack_from('<4I',data,at+8)
    sections.append((rva,max(virtual_size,raw_size),raw))
def offset(address):
    for start,size,raw in sections:
        if start<=address<start+size:return raw+address-start
    raise AssertionError(hex(address))
def string(address):
    start=offset(address);return data[start:data.index(b'\0',start)].decode('ascii')
export=offset(struct.unpack_from('<I',data,opt+112)[0])
n=struct.unpack_from('<I',data,export+24)[0];names=offset(struct.unpack_from('<I',data,export+32)[0])
exports=[string(struct.unpack_from('<I',data,names+i*4)[0]) for i in range(n)]
assert {'SKSEPlugin_Load','SKSEPlugin_Version'}<=set(exports),exports
assert data==(ROOT/'native/build/windows/x64/release/ArcaneStaves.dll').read_bytes()
for name in ('AAStaffRuntime','AAStaffRedHit'):
    assert (ROOT/'data/scripts'/(name+'.pex')).read_bytes()[:4]==bytes.fromhex('fa57c0de')
subprocess.run(['xmake','run','staff-rules-test'],cwd=ROOT/'native',check=True)
result=dict(passed=True,machine='x64',exports=exports,dll_sha256=hashlib.sha256(data).hexdigest(),native_rules_passed=True,papyrus_compiled=True,gameplay_tested=False)
(ROOT/'build/staff-runtime-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
