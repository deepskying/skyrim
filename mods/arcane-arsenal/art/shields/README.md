# 四款盾牌 · 实际模型预览

版本 0.53.0。`shieldred` 绯玉日蚀、`shieldgreen` 青碧折叶、`shieldblue` 海蓝潮门、`shieldpurple` 幻紫星棱。

每款包含 `-front.png` 正面、`-back.png` 背面握柄和 `-glow.png` 暗处发光检查。图片由 `source/render_shields.py` 重新导入最终 NIF、读取实际 DDS 和自发光参数后渲染；不是概念插画，也不是游戏截图。Skyrim 的 HDR/ENB 与游戏内装备动作需另行实测。

源概念插画位于 `../concepts/shields-01/`。构建脚本 `source/build_shields.py` 保留四款独立轮廓，并采用现有武器材质。
