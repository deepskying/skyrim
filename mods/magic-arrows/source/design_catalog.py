"""Twelve magic-arrow families and their current visual revision 2 geometry."""
import math
from geometry import Mesh,generate
from paths import SPECS

EXTRA=[
    ('fire','火 · 焰刃', (1,.16,.015), '三叉焰尖 / 燕尾晶羽'),
    ('ice','冰 · 霜晶', (.12,.65,1), '长棱晶尖 / 冰晶簇尾'),
    ('shock','电 · 雷棱', (.35,.55,1), '折线电刃 / 闪电尾翼'),
    ('poison','毒 · 蛇牙', (.35,1,.055), '双牙尖 / 三角毒棱'),
    ('wind','风 · 旋翼', (.12,1,.64), '偏转翼刃 / 三片旋翼'),
    ('water','水 · 碧波箭', (.025,.66,.82), '水滴矛尖 / 双层波纹'),
    ('earth','土 · 岩锥', (.67,.32,.09), '厚重矛锥 / 阶梯晶羽'),
    ('dark','暗 · 影镰', (.30,.12,.53), '侧向镰刃 / 倒钩尾翼'),
    ('arcane','奥术 · 奥术箭', (.86,.14,.76), '对称菱尖 / 几何晶环'),
]
ALL=[]
for key in ['fire','ice','shock','poison','blood','holy','wind','water','earth','dark','soul','arcane']:
    existing=next((s for s in SPECS if s['key']==key),None)
    if existing:
        ALL.append(dict(existing,description={'blood':'倒刺光刃 / 缠绕血纹','holy':'翼刃光环 / 宽翼尾羽','soul':'星芒晶尖 / 短菱晶翼'}[key]))
    else:
        _,name,color,desc=next(x for x in EXTRA if x[0]==key)
        ALL.append(dict(key=key,name=name,color=color,core=tuple(.65+.35*c for c in color),description=desc))

DESCRIPTIONS = {
    'fire':'宽弯焰刃 / 三片扫掠焰尾', 'ice':'六棱主晶与短侧晶 / 切角冰板尾',
    'shock':'分叉雷电 / 折线尾翼', 'poison':'开放双蛇牙 / 内钩双尾',
    'blood':'原版保留 / 倒钩与螺旋血纹', 'holy':'日轮十字尖刃 / 四向短光翼',
    'wind':'空心螺旋钻 / 扭转风翼', 'water':'凝流水滴 / 波浪尾翼',
    'earth':'宽口岩凿 / 阶梯岩羽', 'dark':'单侧弯钩 / 新月碎片',
    'soul':'悬浮晶簇 / 悬浮碎晶尾', 'arcane':'阶梯符文矛 / 开放梯形尾框',
}
for spec in ALL: spec['description']=DESCRIPTIONS[spec['key']]

def study(key):
    from redesign_geometry import redesigned
    return redesigned(key)
