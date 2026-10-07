# 纯几何试用版 0.2.0

按已认可的纯几何概念插画实现冰晶箭和圣辉箭：晶尖与两枚短晶片、厚实折角箭尾；象牙尖芯与金色护片、楔形箭尾。细杆具有实体纵向光条，尾部保留弦槽。所有表面使用纯色自发光材质，白色基础 DDS 只作为材质占位，没有图案、裂纹或大理石纹理。

不同实体面分配不同纯色明暗，使全自发光状态下刻面仍可读。镂空花瓣样品被这次几何设计替代。冰箭约 404 三角面/支，圣辉箭约 528 三角面/支。手持和箭袋保留原版附件位置与碰撞，飞行模型沿用有界粒子配置。

构建：Python 执行 `source/build_models.py --pure-geometry`；验证：`source/verify_release.py --models-only --pure-geometry`；预览：Blender 执行 `source/render_precision.py -- --pure-geometry`。最后运行 `source/install_pure_geometry.py` 生成试用包并备份、更新当前 MO2 装备工坊中的四个模型文件。

输出位于 `build/pure-geometry-02/data`；实际模型渲染位于 `art/pure-geometry-02`；试用包位于 `dist`。安装记录位于 `build/pure-geometry-installation.json`。样品外观版本 0.2.0，装备工坊本体版本和插件内容保持不变。游戏内表现尚未实测。
