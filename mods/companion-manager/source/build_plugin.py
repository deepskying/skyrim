"""Build our quest/aliases/packages from vanilla templates, without Horde data."""
from pathlib import Path
import struct
from plugin_records import records, subrecords, edid, sub, encode, group
ROOT = Path(__file__).resolve().parents[1]
MASTER = Path(r'C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data/Skyrim.esm')
SLOTS = 64
QUEST, FACTION = 0x01000800, 0x01000801
U32 = lambda n: struct.pack('<I', n)
Z = lambda s: s.encode('utf8') + b'\0'
def cond(fn, arg, value, op=0):
    return sub(b'CTDA', struct.pack('<B3sfH2sIIIII', op, b'\0'*3, float(value), fn, b'\0'*2, arg, 0, 0, 0, 0xFFFFFFFF))
def rank(n): return cond(73, FACTION, n)
vanilla = {edid(r):r for r in records(MASTER, {b'PACK'})}
def instance(template, form, name, conditions, location=None, floats=None, booleans=None,target=None):
    out=[]; index=-1; typ=''
    for k,v in subrecords(vanilla[template]['data']):
        if k in (b'CTDA',b'CIS1',b'CIS2',b'QNAM'): continue
        if k==b'EDID': v=Z(name)
        if k==b'PKDT':
            # allow swimming, services disabled, ordinary combat behavior
            v=struct.pack('<IBBBBHH',0x40000,18,0,2,0,0x7F,0)
        if k==b'PSDT':
            v=bytes.fromhex('ffff00ffff00000000000000')
            out.append(sub(k,v));out.append(conditions);out.append(sub(b'QNAM',U32(QUEST)));continue
        if k==b'ANAM': index+=1;typ=v.rstrip(b'\0').decode()
        if k==b'PTDA': v=struct.pack('<III',*(target or (0,0x14,0)))
        if k==b'PLDT' and location: v=struct.pack('<III',*location)
        if k==b'CNAM' and floats and index in floats: v=struct.pack('<f',floats[index])
        if k==b'CNAM' and booleans and index in booleans: v=bytes([booleans[index]])
        out.append(sub(k,v))
    return dict(sig=b'PACK', form=form, data=b''.join(out))
packages=[]; common=[]
# Modes: 1/11/21 follow, 2/12/22 follow+sandbox, 3 wait, 4 wait+sandbox, 5 home.
for d,(minimum,maximum) in enumerate(((128,256),(256,384),(512,768))):
    for sandbox in (False,True):
        mode=d*10+1+int(sandbox)
        fid=0x01000810+len(packages)
        if sandbox:
            packages.append(instance('DefaultSandboxCurrentLocation1024',fid,f'CMIdle{d}',rank(mode)+cond(1,0x14,maximum,0xA0),location=(0,0x14,minimum),booleans={1:False,2:False}))
            common.append(fid);fid+=1
        packages.append(instance('WERoad02Follow',fid,f'CMFollow{d}{int(sandbox)}',rank(mode),floats={1:minimum,2:maximum},booleans={3:True,4:False,5:False}))
        common.append(fid)
fid=0x01000810+len(packages)
packages.append(instance('MQ103FriendlyFollowerCrouchAtMarker01a',fid,'CMWait',rank(3),location=(2,0,32)))
common.append(fid)
fid+=1
packages.append(instance('DefaultSandboxCurrentLocation1024',fid,'CMWaitSandbox',rank(4),location=(2,0,384),booleans={1:False,2:False}))
common.append(fid)
homes=[]
for slot in range(SLOTS):
    fid=0x01000900+slot
    packages.append(instance('DefaultSandboxCurrentLocation1024',fid,f'CMHome{slot:02}',rank(5),location=(8,SLOTS+slot,512),booleans={1:False,2:False}))
    homes.append(fid)
activities=[]
for slot in range(SLOTS):
    fid=0x01000A00+slot
    packages.append(instance('DefaultSandboxCurrentLocation1024',fid,f'CMActivity{slot:02}',rank(100),location=(8,128+slot,64),booleans={1:False,2:False}))
    activities.append(fid)
# Own quest: optional aliases only, no dialogue stages, inventory or vanilla faction injections.
def wstring(s):
    b=s.encode();return struct.pack('<H',len(b))+b
vmad=struct.pack('<HHH',5,2,1)+wstring('CMController')+b'\0'+struct.pack('<H',0)
# No quest fragments or script aliases. Quest VMAD has a fragments trailer.
vmad+=struct.pack('<BH',2,0)+wstring('')+struct.pack('<H',0)
q=sub(b'EDID',Z('CMControllerQuest'))+sub(b'VMAD',vmad)+sub(b'FULL',Z('Companion Manager'))
q+=sub(b'DNAM',struct.pack('<HBBII',0x11,60,0,0,0))+sub(b'NEXT',b'')+sub(b'ANAM',U32(SLOTS*4))
for alias_id in range(SLOTS*4):
    slot, is_actor = alias_id % SLOTS, alias_id < SLOTS
    q+=sub(b'ALST',U32(alias_id))+sub(b'ALID',Z(f'CM{"Actor" if is_actor else "Home" if alias_id<128 else "Target" if alias_id<192 else "Bed"}{slot:02}'))
    q+=sub(b'FNAM',U32(2|8|16 if is_actor else 2|8))
    # An impossible fill condition prevents automatic recruitment or marker filling.
    q+=cond(72,0x14,0)+cond(72,0x14,1)
    if is_actor:
        for package in [homes[slot],activities[slot],*common]: q+=sub(b'ALPC',U32(package))
    q+=sub(b'VTCK',U32(0))+sub(b'ALED',b'')
quest=dict(sig=b'QUST',form=QUEST,data=q)
faction=dict(sig=b'FACT',form=FACTION,data=sub(b'EDID',Z('CMModeFaction'))+sub(b'DATA',U32(0)))
# Bed aliases 192..255 remain empty for cleanup of the short-lived 1.6.0 test build.
count=len(packages)+2
header=dict(sig=b'TES4',form=0,flags=0x200,data=sub(b'HEDR',struct.pack('<fII',1.7,count,0xE00))+sub(b'CNAM',Z('linos'))+sub(b'MAST',Z('Skyrim.esm'))+sub(b'DATA',b'\0'*8))
out=ROOT/'data/CompanionManager.esp';out.parent.mkdir(parents=True,exist_ok=True)
out.write_bytes(encode(header)+group(b'FACT',[faction])+group(b'PACK',packages)+group(b'QUST',[quest]))
print(f'{out}: {count} records, {SLOTS} actor slots + {SLOTS} home + {SLOTS} activity targets')
