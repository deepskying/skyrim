"""Stable playable prototype IDs. Never renumber existing save identities."""
from paths import SPECS
from design_catalog import ALL
NAMES={'fire':'火焰箭','ice':'霜晶箭','shock':'雷棱箭','poison':'蛇牙箭','wind':'旋翼箭','water':'碧波箭','earth':'岩锥箭','dark':'影镰箭','arcane':'奥术箭'}
PROTOTYPES=list(SPECS)
for i,key in enumerate(NAMES):
    s=next(s for s in ALL if s['key']==key)
    PROTOTYPES.append(dict(s,name=NAMES[key],id=0xA00+i*0x10,particle='star' if key in ('ice','arcane') else 'drop' if key in ('water','poison') else 'spark'))
