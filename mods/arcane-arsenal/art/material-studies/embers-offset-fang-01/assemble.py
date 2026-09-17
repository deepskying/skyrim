"""Lay out the actual Blender render comparisons with Chinese captions."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
font='C:/Windows/Fonts/msyh.ttc'
title=ImageFont.truetype(font,42);label=ImageFont.truetype(font,28);small=ImageFont.truetype(font,23)
for mode in ('full','detail'):
    cell_w=600;image_h=734 if mode=='full' else 600;cell_h=image_h+64
    sheet=Image.new('RGB',(1848,170+cell_h*2),(15,19,27));d=ImageDraw.Draw(sheet)
    d.text((24,22),'余烬·错牙 | 材质对比'+(' · 刃面细节' if mode=='detail' else ''),font=title,fill=(242,240,237))
    d.text((26,83),'同一真实模型 · 同一镜头与灯光 · Blender 预览，非游戏实拍',font=small,fill=(166,175,189))
    for i,v in enumerate(manifest['variants']):
        x=24+(i%3)*600;y=130+(i//3)*cell_h
        im=Image.open(root/v[mode]).convert('RGB').resize((588,image_h),Image.Resampling.LANCZOS)
        sheet.paste(im,(x,y))
        d.text((x+12,y+image_h+12),str(i+1).zfill(2)+'  '+v['name'],font=label,fill=(241,225,216))
    sheet.save(root/('comparison-'+mode+'.jpg'),quality=94)
readme='''# 余烬·错牙：材质试样

使用已确认的单手战斧真实 Blender 网格，未修改正式武器、贴图、插件或 MO2 文件。

- comparison-full.jpg：完整武器六种材质对比。
- comparison-detail.jpg：同一刃面镜头的六种材质细节。
- 各编号的 PNG：单独高清图片。
- material-study.blend：试样场景；render_study.py 可重建全部六种材质。

01 保留现有发光着色节点；02—06 使用不同表面材质、降低主体自发光并统一红色亮边。
对比保持网格、灯光、镜头与曝光不变；这是完整材质方案的比较，不是只换颜色贴图。

这些是 Cycles 渲染的视觉方向。Skyrim SE 的材质系统与 Cycles 不同，尤其金属反射、晶体折射和透明排序不能直接等同；选中方向后需要制作相应 DDS / NIF 材质并进行游戏内 A/B 检查。未声称任何方案已经在游戏中实现。
'''
(root/'README.md').write_text(readme,encoding='utf-8')
print(root/'comparison-full.jpg');print(root/'comparison-detail.jpg')
