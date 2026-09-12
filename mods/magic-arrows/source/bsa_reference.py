"""Read selected local Skyrim SE BSA assets for format inspection; never write game files."""
from pathlib import Path
import struct,sys
REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'reference/bow-tools/python-libs'))
def entries(path):
    with Path(path).open('rb') as f:
        magic,version,offset,flags,nfolders,nfiles,folderlen,filelen,fileflags=struct.unpack('<4s8I',f.read(36))
        assert magic==b'BSA\0' and version==105 and flags&3==3
        f.seek(offset);folders=[struct.unpack('<QIIQ',f.read(24)) for _ in range(nfolders)]
        pending=[]
        for _,count,_,foff in folders:
            f.seek(foff-filelen)
            length=f.read(1)[0];folder=f.read(length).rstrip(b'\0').decode('utf-8')
            for _ in range(count):
                _,size,pos=struct.unpack('<QII',f.read(16));pending.append((folder,size,pos))
        names=f.read(filelen).split(b'\0');assert len(pending)==nfiles and len(names)>=nfiles
        return {(folder+'/'+name.decode('utf-8')).replace('\\','/').lower():(size,pos,flags) for (folder,size,pos),name in zip(pending,names)}
def extract(path,key):
    size,pos,flags=entries(path)[key.lower()]
    with Path(path).open('rb') as f:f.seek(pos);blob=f.read(size&0x3fffffff)
    if flags&0x100:blob=blob[1+blob[0]:]
    if bool(flags&4)^bool(size&0x40000000):
        from lz4.frame import decompress
        expected=struct.unpack_from('<I',blob)[0];blob=decompress(blob[4:]);assert len(blob)==expected
    return blob
if __name__=='__main__':
    data=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data')
    for path in sorted(data.glob('Skyrim - Meshes*.bsa')):
        found=[k for k in entries(path) if ('magic/' in k or 'effects/' in k) and any(t in k for t in ('spark','enchantfire','ember','mote'))]
        print(path.name);print('\n'.join(found[:60]))
