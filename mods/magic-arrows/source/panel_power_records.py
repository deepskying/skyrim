"""Stable ability records, matching native TESSpellCastEvent lookup at local 840."""
import struct
from plugin_records import sub
P=lambda fmt,*v:struct.pack('<'+fmt,*v)
Z=lambda s:s.encode('utf-8')+b'\0'
SPELL=0x01000840
EFFECT=0x01000841
def build():
    effect=bytearray(152)
    struct.pack_into('<I',effect,0,0x0C008E10)
    for offset in (12,16,68,88):struct.pack_into('<i',effect,offset,-1)
    struct.pack_into('<I',effect,64,1)
    struct.pack_into('<I',effect,80,1)
    struct.pack_into('<I',effect,140,2)
    name='打开魔法箭工坊'
    m=sub(b'EDID',Z('MagicArrowsPanelEffect'))+sub(b'FULL',Z(name))+sub(b'DATA',effect)+sub(b'DNAM',Z('打开魔法箭工坊面板。'))
    s=sub(b'EDID',Z('MagicArrowsPanelPower'))+sub(b'OBND',bytes(12))+sub(b'FULL',Z(name))+sub(b'ETYP',P('I',0x25BEE))
    s+=sub(b'DESC',Z('打开装备、制作与设置面板。可收藏，无魔法消耗，可重复使用。'))
    s+=sub(b'SPIT',P('IIIfIIffI',0,0xB00001,3,0,1,0,0,0,0))+sub(b'EFID',P('I',EFFECT))+sub(b'EFIT',P('fII',0,0,0))
    return [(b'MGEF',[dict(sig=b'MGEF',form=EFFECT,version=44,data=m)]),(b'SPEL',[dict(sig=b'SPEL',form=SPELL,version=44,data=s)])]
