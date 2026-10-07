# 组件还原样品 0.1.0

两支独立试用箭：冰晶箭使用错落晶片、刻面与阶梯晶翼；圣辉箭使用有厚度的三瓣镂空曲面、尖芯与细长镂空箭尾。两者沿用原版附件变换和碰撞，自发光覆盖全部可见表面。

专用表面纹理由内置 imagegen 生成，随后转换为 DDS；16 档面向明暗烘焙到 UV 图集，保留自发光时的形体。镂空由真实网格形成。未实现真实折射，不承诺概念插画逐像素一致。

生成顺序：Blender 执行 `precision_textures.py`，Python 执行 `build_models.py --precision-samples`，`verify_release.py --models-only --precision-samples`，Blender 执行 `render_precision.py`，Python 执行 `package_precision.py`。

输出位于 `build/precision-samples-01/data`，预览和可编辑 Blender 文件位于 `art/precision-samples-01`，试用包位于 `dist`。默认构建与已安装 V3 不受影响。游戏内效果尚未测试。

结构检查已通过。圣辉箭约 13048 三角面/支，冰箭约 2222 三角面/支；圣辉样品优先验证轮廓，正式推广前应简化镂空边缘网格。样品只修改外观，独立样品版本为 0.1.0。
