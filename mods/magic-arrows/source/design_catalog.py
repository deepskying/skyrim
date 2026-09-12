"""Twelve solid-light silhouette studies. New nine are review assets, not game records."""
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

def study(key):
    if key in ('blood','holy','soul'):
        return {k:v for k,v in generate(key).items() if k!='aura'}
    body,core=Mesh(),Mesh()
    body.tube([(0,8,0),(0,57.8,0)],.4,8)
    core.tube([(0,55,0),(0,58,0)],.14,6)
    def blade(points,a=0,t=.15):body.blade(points,a,t)
    def line(points,a=0,r=.065):core.tube([(x*math.cos(a),y,x*math.sin(a)) for x,y in points],r,6)
    for a in (0,math.pi/2):
        if key=='fire':
            blade([(0,0),(1.15,5),(0,10),(-1.15,5)],a)
            for s in (-1,1):blade([(s*.5,6),(s*2.5,3.5),(s*1.5,9),(0,11)],a)
        elif key=='ice':
            blade([(0,0),(1.15,8),(0,11),(-1.15,8)],a,.3)
            for s in (-1,1):blade([(s*.55,9),(s*1.8,5),(s*2.1,10),(s*.4,12)],a)
            line([(0,1),(0,10)],a,.1)
        elif key=='shock':
            for pts in [[(0,0),(2.4,5),(-.6,6)],[(-.6,5),(2.4,5),(-2,10)],[(-2,9),(1.1,7),(0,13)]]:blade(pts,a)
            line([(0,1),(1.5,5.3),(-1.2,9),(0,12)],a)
        elif key=='poison':
            for s in (-1,1):blade([(s*1.75,0),(s*2.45,5.5),(s*.25,10),(s*.8,5)],a,.22)
            blade([(-.65,7),(.65,7),(.5,11),(-.5,11)],a)
        elif key=='wind':
            blade([(0,0),(1.05,6),(0,10),(-1.05,6)],a)
            blade([(.45,5),(3,3),(2.3,6.5),(.3,9)],a)
            blade([(-.45,6),(-3,8),(-2.3,4.5),(-.3,3)],a)
        elif key=='water':
            blade([(0,0),(2.05,6.5),(1.5,9),(0,10.5),(-1.5,9),(-2.05,6.5)],a,.23)
            line([(-1,7),(0,8.4),(1,7)],a)
        elif key=='earth':
            blade([(0,0),(2.3,5),(2.3,8),(.8,11),(-.8,11),(-2.3,8),(-2.3,5)],a,.4)
            line([(-2.1,6.6),(2.1,6.6)],a,.085)
        elif key=='dark':
            blade([(0,0),(1,6),(0,11),(-1,6)],a)
            blade([(0,5),(3,3),(2.6,6),(.1,8)],a)
            blade([(-.5,7),(-2.4,8),(-1.8,11),(0,9)],a)
        else:
            blade([(0,0),(1.8,5.5),(0,11),(-1.8,5.5)],a,.2)
            line([(0,1),(1.3,5.5),(0,9.5),(-1.3,5.5),(0,1)],a)
    tails={
        'fire':[(.2,49),(2.3,52),(.2,55)],
        'ice':[(.2,48),(1.8,51),(.2,54)],
        'shock':[(.2,48),(2.3,50),(.2,53)],
        'poison':[(.2,50),(2.1,54),(.2,56)],
        'wind':[(.2,49),(2.3,50.5),(1.3,54),(.2,56)],
        'water':[(.2,49),(1.8,51),(2.1,53),(1.4,55),(.2,56)],
        'earth':[(.2,49),(2,49),(2,53),(.2,53)],
        'dark':[(.2,49),(2.3,53),(.9,52),(.2,56)],
        'arcane':[(.2,49),(1.7,52.5),(.2,56),(-.1,52.5)]}
    for a in (0,math.tau/3,math.tau*2/3):
        pts=tails[key]
        if key=='dark':
            blade([pts[0],pts[1],pts[2]],a);blade([pts[0],pts[2],pts[3]],a)
        else:blade(pts,a)
        if key in ('fire','ice','shock','earth'):
            blade([(x*.75,y+3) for x,y in pts],a)
        line(pts+[pts[0]],a,.045)
    if key=='arcane':
        for y,r in [(12,1.6),(48,1.0)]:
            core.tube([(r*math.cos(t),y,r*math.sin(t)) for t in [i*math.tau/6 for i in range(7)]],.12,6)
    if key=='water':
        for start in (12,17):
            core.tube([(.62*math.cos(t),start+.6*math.sin(t),.62*math.sin(t)) for t in [i*math.tau/32 for i in range(33)]],.08,6)
    return dict(body=body,core=core)
