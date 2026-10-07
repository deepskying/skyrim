"""Package the review samples as a separate optional MO2 resource override."""
import json,hashlib,zipfile
from paths import ROOT,BUILD
from precision_samples import VERSION
stage=BUILD/'precision-samples-01';data=stage/'data'
verification=json.loads((BUILD/'verification-precision01.json').read_text())
assert verification['passed']
readme='''魔法箭组件样品 0.1.0：冰晶箭 / 圣辉箭

仅覆盖这两支箭的手持、箭袋和飞行模型，需已有魔法箭模组。
MO2：作为单独模组安装，放在 EquipmentWorkshop 之后，使资源覆盖生效。
取消勾选此样品即可恢复原有外观。无需新增 ESP，也不改变魔法效果。

预览是实际 NIF + DDS 纹理的 Blender 渲染。自发光材质已保留；
游戏内粒子、ENB 辉光、箭杆观感尚未实测。表面明暗是纹理烘焙，
不等同真实折射。圣辉箭有真实镂空，不依赖透明贴图。
圣辉箭约 13048 三角面/支，冰箭约 2222 三角面/支；尚未优化为量产模型。
样品检查覆盖 NIF 引用、纹理、自发光、碰撞继承、边界与非退化三角面。
'''
(stage/'README.txt').write_text(readme,encoding='utf-8')
(stage/'meta.ini').write_text('[General]\nmodid=0\nversion='+VERSION+'\n',encoding='utf-8')
files=[p for p in data.rglob('*') if p.is_file()]+[stage/'README.txt',stage/'meta.ini']
manifest={p.relative_to(stage).as_posix().removeprefix('data/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
out=ROOT/'dist'/f'MagicArrows-Precision-Samples-{VERSION}.zip';out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(stage).as_posix().removeprefix('data/'))
    z.write(stage/'manifest.json','manifest.json')
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
print(out)
