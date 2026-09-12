"""Fixed FormIDs for a save-safe, explicitly adapted Fireball recipe."""
import struct
from plugin_records import records,subrecords,sub
from paths import GAME
P=lambda f,*v:struct.pack('<'+f,*v)
Z=lambda s:s.encode('utf-8')+b'\0'
BASES=[(0x1397d,'铁箭'),(0x1397f,'钢箭'),(0x139bb,'兽人箭'),(0x139bc,'矮人箭'),(0x139bd,'精灵箭'),(0x139be,'玻璃箭'),(0x139bf,'乌木箭'),(0x139c0,'魔族箭')]
def build(change,proj_template):
    src={r['form']:r for r in records(GAME/'Data/Skyrim.esm',{b'AMMO',b'EXPL',b'ENCH'})}
    ammos=[]
    for i,(base,name) in enumerate(BASES):
        data=bytearray(dict(subrecords(src[base]['data']))[b'DATA']);struct.pack_into('<I',data,0,0x01000880)
        struct.pack_into('<I',data,12,25)
        ammos.append(change(src[base],0x01000900+i,{
            b'EDID':Z('MAFireballArrow'+str(i)),b'FULL':Z('火焰箭·火球术'),
            b'DESC':Z('命中引发火球爆炸，基础火焰伤害40，范围与原版火球爆炸一致。保留基材物理伤害；不继承第三方法术附加效果。'),
            b'MODL':Z('magicarrows\\fire.nif'),b'DATA':bytes(data),b'OBND':P('6h',-8,-62,-8,8,2,8)},(b'MODT',b'MODS')))
    data=bytearray(dict(subrecords(proj_template['data']))[b'DATA'])
    flags=struct.unpack_from('<H',data)[0];struct.pack_into('<H',data,0,(flags&~(0x40|0x100|4))|2)
    struct.pack_into('<I',data,36,0x01000881)
    proj=change(proj_template,0x01000880,{b'EDID':Z('MAFireballArrowProjectile'),b'MODL':Z('magicarrows\\fire_flight.nif'),b'DATA':bytes(data)},(b'MODT',b'MODS'))
    data=bytearray(dict(subrecords(src[0x439c0]['data']))[b'DATA'])
    struct.pack_into('<ff',data,24,0,0) # no physical explosion damage or force
    struct.pack_into('<I',data,44,0x140) # respect LOS, no camera flash/vibration
    expl=change(src[0x439c0],0x01000881,{b'EDID':Z('MAFireballArrowExplosion'),b'EITM':P('I',0x01000882),b'DATA':bytes(data)},(b'MODT',b'MNAM'))
    data=bytearray(dict(subrecords(src[0x45c2c]['data']))[b'ENIT'])
    for off in (0,12,28,32):struct.pack_into('<I',data,off,0)
    ench=change(src[0x45c2c],0x01000882,{b'EDID':Z('MAFireballArrowEnchantment'),b'FULL':Z('火球箭·火焰爆炸'),b'ENIT':bytes(data),b'EFIT':P('fII',40,0,0)})
    return ammos,proj,expl,ench
