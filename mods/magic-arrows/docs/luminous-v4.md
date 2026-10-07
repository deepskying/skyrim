# 流光箭矢外观 4.0.0

重新制作火焰、雷棱、蛇牙、旋翼、碧波、岩锥、影镰、星魂和奥术九种箭。嗜血箭、已确认生效的冰晶箭与圣辉箭保留当前安装资源。

造型以流线形能量叶片、厚实晶体与亮色光脉组成。火焰有错落火舌，雷棱有分叉电弧，蛇牙是弯曲双牙，旋翼是扭转翼瓣，碧波是凝聚水滴，岩锥是琥珀晶簇，影镰是偏侧月牙，星魂是错落晶片，奥术是双轨光环包裹尖芯。箭尾与各自主题对应，箭杆采用细长连续自发光和轻微盘绕的表面光脉。

所有可见表面保留 OWN_EMIT 自发光效果材质；粒子只留在飞行模型，箭袋和手持保持静态。继承原版附件变换、碰撞和尺度，不改变魔法效果、插件记录或存档。

构建：`source/build_models.py --luminous-v4`；检查：`source/verify_release.py --models-only --luminous-v4`；Blender 实际模型预览：`source/render_redesign.py -- --luminous-v4`；备份并安装：`source/install_pure_geometry.py --luminous-v4`。

构建资源位于 `build/luminous-v4/data`，预览位于 `art/luminous-v4`，安装报告位于 `build/luminous-v4-installation.json`，独立资源包位于 `dist/MagicArrows-Luminous-4.0.0-MO2.zip`。更新当前 MO2 装备工坊的十八个 NIF，安装前逐一备份；其他资源和配置校验保持一致。外观版本 4.0.0，装备工坊功能版本保持不变。

检查包含 Nifly 重新载入、引用类型、纹理路径、自发光、碰撞继承、边界、非退化三角面与粒子容量。预览为实际导出网格，游戏内辉光尚未实测。若游戏正在运行，重新启动后再检查；读档后如装备仍显示临时奥术模型，可收弓换普通箭再换回。
