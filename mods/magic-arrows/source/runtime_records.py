"""Empty identity slots only: no spell/mod inventory is scanned at build time."""
import struct
from plugin_records import sub
P=lambda f,*v:struct.pack('<'+f,*v)
Z=lambda s:s.encode('utf-8')+b'\0'
def build(change,ammo_template):
    ammo=[];lists=[]
    for i in range(256):
        ammo.append(change(ammo_template,0x01000C00+i,{
            b'EDID':Z('MARuntimeArrow%03d'%i),b'FULL':Z('封存箭〔绑定待恢复〕'),
            b'MODL':Z('magicarrows\\arcane.nif'),b'OBND':P('6h',-8,-62,-8,8,2,8),
            b'DESC':Z('运行时封存箭。法术与实体基材引用保存在本存档中。'),
            b'DATA':P('IIfIf',0x01000A81,6,0,0,.1)},(b'MODT',b'MODS')))
        lists.append(dict(sig=b'FLST',form=0x01000D00+i,version=44,data=sub(b'EDID',Z('MARuntimeBinding%03d'%i))))
    return ammo,lists
