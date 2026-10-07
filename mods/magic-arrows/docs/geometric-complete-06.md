# 完整几何箭矢样品 0.6.0

完成嗜血箭之外的 11 种箭矢。01 火焰、02 冰晶、03 雷霆、04 毒素、08 大地按第一轮概念补全；05 圣辉、06 风、07 水、09 暗影、10 星魂、11 奥术沿用 0.5.0 的模型与材质，资源文件与上一版逐字节一致。嗜血箭保留现有已认可资源。

火焰为中央尖头与两片弯曲实体火焰分枝，箭尾为三片扫掠叶片；冰晶为六棱晶体与两片长短不同的棱晶肩部，箭尾为小棱晶；雷霆为菱形尖头与两片折线棱翼，箭尾为折线楔形；毒素为细中央尖头与成对的弯曲实体毒牙，箭尾为三片叶形实体；大地为五棱厚晶体与阶梯形肩部，箭尾为小楔形实体。所有箭头与细直圆柱杆共轴，构建使用封闭截面、棱锥与曲面扫掠，不追踪插画平面、不投射原图纹理。

这是用于游戏迭代的几何解释，不是插画像素级复现。简化了插画纹理与晶体内部光纹，没有实现透明折射。实体表面自发光强度 1.55，细光边 1.65，分面纹理提供简单深浅层次。单支约 796–3336 三角面，保留原版附件、箭袋拷贝与飞行碰撞。

导出位于 `build/geometric-selected-05/data`；源代码为 `source/geometric_selected.py`。完整模型渲染、90 度侧视、白模及可编辑场景位于 `art/geometric-complete-06`。新补全五支的独立预览位于其 `remaining` 子目录。渲染读取实际导出的 NIF 与材质。

安装仅覆盖 11 种箭矢的 22 个 NIF 和一张分面纹理，其他资源、插件记录、DLL、INI 与模组顺序不变。安装先备份旧资源，记录保存在 `build/geometric05-installation.json` 与本次备份目录的 `installation.json`。回退本次安装应使用该记录的 `backup`，恢复其中的文件；`original_backup` 指早期六支样品安装前的备份，不包含本轮全部资源，不能独自用于整套回退。

构建：Python 执行 `source/geometric_selected.py`；Python 执行 `source/build_models.py --geometric-selected`；验证 `source/verify_release.py --models-only --geometric-selected`；Blender 执行 `source/render_geometric_selected.py`（添加 `-- --remaining` 只预览新增五支）；打包安装 `source/package_faithful.py --geometric-selected --install`。

检查覆盖 22 个实际 NIF 的读取、图引用、纹理、附件与碰撞继承、模型边界、非退化三角面、自发光和粒子容量。与 0.5.0 安装包比对确认之前六支资源没有变化。安装后核对全部覆盖资源哈希与其他受保护资源哈希。第一人称拉弓、背部排列、飞行及实际辉光仍需游戏实测。
