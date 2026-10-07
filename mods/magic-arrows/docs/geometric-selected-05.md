# 几何模型样品 0.5.0：六支选定箭矢

根据第一轮的 06 风、07 水及第二轮的 05 圣辉、09 暗影、10 星魂、11 奥术概念制作。本轮只以插画作为造型参考，全部网格由封闭截面、棱锥与曲面扫掠构建，不追踪插画平面，也不投射原图纹理。

圣辉采用六棱尖头和三片金色曲面分枝；暗影采用三角截面尖头与三片长度略异的弯曲倒钩；星魂为六棱纺锤晶体及后部三片护瓣；奥术采用倒角方棱锥、八边形接口与三片短楔形分枝。风使用两条围绕轴线扭转的封闭曲面带，水为圆截面的尖水滴实体及底部 C 形弯曲结构。箭尾为有厚度的三片叶片，箭杆为同轴细直圆柱。

这是一轮用于实测的建模解释，不是对插画的像素级复现。曲面的截面、深度和扭转由建模补全；水与星魂为不透明发光实体，未实现插画中的透明折射。材质使用元素色与简单分面明暗，不依赖复杂纹理维持轮廓。所有实体表面包含自发光，主体强度 1.55，细光边 1.65；游戏内实际辉光受显示配置影响，仍待测试。

单支模型约 2824–3336 三角面。装备模型保留原版箭袋附件与五支拷贝，飞行模型保留原版碰撞和附件。插件记录与 DLL 不改变。MO2 只更新这六支的 12 个 NIF 与一张独立分面纹理。嗜血箭及本轮未选择的箭矢不修改。安装前备份与新增资源记录保存于 `build/geometric05-installation.json`，备份目录内也保存相同记录；回退时恢复备份，并移除记录中的新增文件。

源码：`source/geometric_selected.py`。导出：`build/geometric-selected-05/data`。实际 NIF 预览与可编辑 Blender 场景：`art/geometric-selected-05/models.png`、`side.png`、`geometry.png` 及同名 `.blend`。预览分别展示全箭、放大箭头和放大箭尾；侧视旋转 90 度，白模关闭纹理与发光以检查厚度。

构建顺序：Python 执行 `source/geometric_selected.py`；Python 执行 `source/build_models.py --geometric-selected`；验证 `source/verify_release.py --models-only --geometric-selected`；Blender 执行 `source/render_geometric_selected.py`；打包安装 `source/package_faithful.py --geometric-selected --install`。

检查覆盖实际 NIF 读取、引用与纹理、附件及碰撞继承、有限数值、模型边界、非退化面、自发光标记及飞行粒子容量。第一人称拉弓、背部排列、飞行与性能需要游戏实测，不能仅凭离线渲染确认。
