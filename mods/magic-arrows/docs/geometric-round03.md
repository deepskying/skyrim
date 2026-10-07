# 第三轮几何箭矢 0.7.0

按 `art/geometric-rounds/round-03-shafts-tails.png` 制作火焰、冰晶、雷霆、毒素、圣辉、大地、暗影、星魂及奥术九种实体几何箭。嗜血、风元素、水元素不参与构建与覆盖。箭杆、箭尾分别采用元素特有结构；箭头也重建为带体积的棱晶与径向分枝。

火焰为红芯与三条金色螺旋棱带、三片弯曲火焰楔尾；冰晶为六棱杆与晶节、长短错落的冰晶尾；雷霆为直芯与三条折线光棱、折线楔尾；毒素为绿黑芯与缓慢蛇形棱带、内钩爪尾；圣辉为象牙六棱杆与金色套节、分叉冠状尾；大地为八棱杆与锥形矿石节段、阶梯厚楔尾；暗影为扭转三棱杆、镰形尾；星魂为三条贴合晶芯的导光轨、厚梭形晶尾；奥术为四棱杆与八边形套环、折角阶梯尾。

几何解释保留主要轮廓与构成，未复制插画内的表面裂纹、矿石纹理和透明折射。每个组件均由封闭截面扫掠、棱锥或带端盖的多边形棱柱构成，使用不透明自发光材质及中性分面明暗纹理。表面发光强度 1.65，光棱 1.85。箭头最大径向范围约 2.496、箭尾约 2.685，主箭杆半径约 0.40，饰棱和套节适当超出。沿用嗜血箭尺寸基准、原版箭矢长度与附件坐标；尾片 Y=46–57，箭扣至 Y=57.94。

源代码 `source/geometric_round03.py`，导出 `build/geometric-round03/data`，实际 NIF 渲染及可编辑 Blender 场景 `art/geometric-round03-070`。三个渲染分别检查发光配色、90 度侧视与白模；每栏包含整箭、箭头、箭杆和箭尾。

构建：先用随 Blender 附带的 Python 执行 `source/geometric_round03.py`、`source/build_models.py --geometric-round03`。验证：`source/verify_release.py --models-only --geometric-round03`。渲染：Blender 后台执行 `source/render_geometric_selected.py -- --geometric-round03`。安装：Python 执行 `source/package_faithful.py --geometric-round03 --install`。

安装包仅含这九种箭矢的 18 个 NIF、分面纹理及所需的通用粒子纹理。安装仅更新 18 个 NIF 和分面纹理；共享分面纹理与上一版字节一致，通用粒子纹理先核验一致、不覆盖。安装前验证有效覆盖来源并备份；安装后核验目标哈希、嗜血/风/水及其他受保护资源、配置与模组顺序。记录为 `build/geometric-round03-installation.json` 与备份目录 `installation.json`。回退使用该记录的本轮 `backup`。

离线检查包括 NIF 图引用、纹理、附件/碰撞继承、有限数值、模型边界、非退化三角面、自发光和粒子容量。游戏内第一人称拉弓、背部箭袋、飞行及实际辉光仍需实测。
