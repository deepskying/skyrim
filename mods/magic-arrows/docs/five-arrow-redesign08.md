# 五款魔法箭造型重设计 0.8.0

按 2026-10-07 已确认的五款插画重做火焰箭、圣辉箭、奥术箭、蛇牙箭和霜晶箭。造型以实体能量网格表现；概念图位于 `art/concepts/2026-10-07-five-arrows/five-arrows-redesign-v1.png`，生成提示词保存在同目录。

火焰箭采用有倒角与厚度的非对称宽弯焰刃，右侧有两处火舌分叉，配三片扫掠焰尾；圣辉箭采用象牙尖刃、金色横向十字及厚十二边形日轮，配四向短光翼；奥术箭采用四棱尖芯、三层阶梯符文刃及方形支架，配四向开放梯形尾框；蛇牙箭取消中央尖针，以两根向内弯曲、长短错落的实体毒牙留出中央空隙，尾部为双钩；霜晶箭采用粗六棱主晶、两根错位短侧晶及三片切角冰板尾。

这是可建模结构的还原，不复制插画中的透明折射、表面裂纹或装饰光纹。火焰、十字和阶梯刃为封闭倒角棱柱，凹口使用耳切三角化；日轮与奥术尾框有真实开放孔洞及内壁，不以透明贴图伪造。蛇牙为封闭曲面扫掠，冰晶为封闭多棱体。所有可见表面使用不透明、自发光能量材质，中性分面纹理提供体积层次。

沿用嗜血箭校准尺寸：箭头最大径向范围 2.496、箭尾 2.685，主杆最大径向范围 0.40。主体尖端 Y=0.07，光棱在此附近略微超出，仍位于原版范围内；箭扣末端 Y=57.94。火焰刃朝尖端同步收薄，侧视也保留尖锐轮廓。原版挂点、碰撞与背部五支箭排列继续继承。装备模型静态无粒子，飞行模型沿用各家族的粒子。资源版本升至 0.8.0，ESP、DLL 与运行时版本不变。

生成源为 `source/five_arrow_redesign.py`，导出目录 `build/five-arrow-redesign08/data`。实际 NIF 渲染与可编辑 Blender 场景位于 `art/five-arrow-redesign08`，包含发光造型、90 度侧视及白模。

构建步骤（使用仓库随 Blender 附带的 Python）：

1. `source/five_arrow_redesign.py`：准备独立 `redesign08` 分面纹理。
2. `source/build_models.py --five-arrow-redesign`：导出五款装备与飞行模型。
3. `source/verify_release.py --models-only --five-arrow-redesign`：检查十个 NIF。
4. Blender 后台执行 `source/render_geometric_selected.py -- --five-arrow-redesign`：渲染实际导出资源。
5. `source/package_faithful.py --five-arrow-redesign`：生成 `dist/MagicArrows-Five-Arrow-Redesign-0.8.0-MO2.zip`。加 `--install` 可在验证有效覆盖来源并备份后安装到当前装备工坊。

安装覆盖范围仅为这五款的十个 NIF 及独立分面纹理。通用粒子纹理先核对一致再沿用。其他七款箭、命中特效、ESP、DLL、INI 和 MO2 模组顺序不变。安装记录为 `build/redesign08-installation.json`，备份目录另存 `installation.json`；回退上次安装时恢复 `backup` 内的资源，并删除 `new_files` 记录的新文件。若存在 `original_backup`，它保存本轮重设计首次安装前的资源；恢复到重设计前应使用该目录及其中记录的新文件列表。

离线验证包括 NIF 原生重读、完整图引用、附件与碰撞一致性、有限数值、边界、非退化三角形、自发光和粒子容量；另外验证实际飞行模型的尺寸、主体闭合边界和面绕序，确认蛇牙中央空隙、圣辉日轮及奥术尾框未被三角面填满。同步到仓库 `data` 后也执行全套 36 个 NIF 的模型检查。实际游戏内的第一人称拉弓、背部排列、飞行与 ENB/Community Shaders 辉光仍待验收。
