"""Lossless block envelope for Skyrim SE NIFs; unknown block payloads stay untouched."""
from pathlib import Path
import struct
class NifBlocks:
    def __init__(self,path):
        data=Path(path).read_bytes();self.pos=data.index(b'\n')+1;self.data=data
        self.line=data[:self.pos]
        self.version,self.endian,self.user,self.count,self.stream=self.unpack('IBIII')
        assert (self.version,self.endian,self.user,self.stream)==(0x14020007,1,12,100)
        self.info=[self.take(self.unpack('B')[0]) for _ in range(3)]
        self.types=[self.sized() for _ in range(self.unpack('H')[0])]
        indices=self.unpack('H'*self.count);sizes=self.unpack('I'*self.count)
        numstrings,maxstring=self.unpack('II');self.strings=[self.sized() for _ in range(numstrings)]
        groups=self.unpack('I')[0];assert groups==0
        self.blocks=[(self.types[i].decode(),self.take(n)) for i,n in zip(indices,sizes)]
        self.footer=data[self.pos:];assert self.footer==struct.pack('<II',1,0)
    def take(self,n):
        value=self.data[self.pos:self.pos+n];assert len(value)==n;self.pos+=n;return value
    def unpack(self,fmt):return struct.unpack('<'+fmt,self.take(struct.calcsize('<'+fmt)))
    def sized(self):return self.take(self.unpack('I')[0])
    def string(self,s):
        s=s.encode() if isinstance(s,str) else s
        if s not in self.strings:self.strings.append(s)
        return self.strings.index(s)
    def append(self,kind,data):
        self.blocks.append((kind,bytes(data)));return len(self.blocks)-1
    def save(self,path):
        types=list(dict.fromkeys(k for k,b in self.blocks));p=lambda f,*x:struct.pack('<'+f,*x)
        sized=lambda s:p('I',len(s))+s
        data=self.line+p('IBIII',self.version,1,12,len(self.blocks),100)
        data+=b''.join(p('B',len(s))+s for s in self.info)
        data+=p('H',len(types))+b''.join(sized(t.encode()) for t in types)
        data+=p('H'*len(self.blocks),*(types.index(k) for k,b in self.blocks))
        data+=p('I'*len(self.blocks),*(len(b) for k,b in self.blocks))
        data+=p('II',len(self.strings),max(map(len,self.strings),default=0))+b''.join(sized(s) for s in self.strings)+p('I',0)
        data+=b''.join(b for k,b in self.blocks)+self.footer;Path(path).write_bytes(data)
if __name__=='__main__':
    import sys
    n=NifBlocks(sys.argv[1]);print('STRINGS',list(enumerate(n.strings)))
    for i,(kind,blob) in enumerate(n.blocks):print(i,kind,len(blob),blob[:170].hex())
