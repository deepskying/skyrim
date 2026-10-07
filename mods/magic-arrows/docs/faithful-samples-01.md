# 插画还原样品 0.4.0：立体火焰箭、圣辉箭

依据用户提供的两张箭头与箭尾概念图制作。箭杆统一为细直杆，使用对应的火焰红金或圣辉金色自发光材质。

圣辉箭保留 0.3.2 的单视图轮廓重建：有厚度、倒角与浅弯曲，正反面使用同一投影。火焰箭在 0.4.0 改为居中的闭合立体尖头，箭头、箭尾各由三片独立火焰叶片围绕箭杆分布。叶片保留参考轮廓，但中部鼓起、边缘收薄并沿长度扭曲，不再使用完整插画平面。原图中的短杆、金属接口与箭扣从叶片模型中剔除，使用共轴圆柱杆和独立接口替代。火焰裂纹与圣辉光纹仍取自对应参考图。

这仍是样品，没有进行高模法线烘焙。火焰叶片厚度、弯曲、径向排列和中央尖头属于对单视图的立体补全，因此正面轮廓也与旧版有所区别；不是原图完整三维结构的精确恢复。游戏内辉光、遮挡和第一人称拉弓仍需实测。原始图集没有单支高清源图，纹理的实际细节受约四百像素宽的原始部件限制；扩为 1024 DDS 不会增加真实图像信息。

火焰立体生成代码为 `source/solid_fire.py`；叶片构建场景与圣辉原始轮廓场景在 `art/faithful-samples-01/reference-sculpt.blend`。完整导出网格与材质可在同目录的 `overview.blend`、`angles.blend` 中查看和编辑。实际 NIF 渲染包括 `overview.png`、`details.png`、`angles.png`，无纹理白模为 `geometry.png`。原始参考图保存在同目录的 `references` 中。导出资源位于 `build/faithful-samples-01/data`。

制作：Blender 执行 `source/sculpt_faithful.py`；Python 执行 `source/build_models.py --faithful-samples`；验证执行 `source/verify_release.py --models-only --faithful-samples`；预览由 Blender 执行 `source/render_precision.py -- --faithful-samples`；打包并安装执行 `source/package_faithful.py --install`。

样品版本 0.4.0。沿用饱和度与自发光强度（1.65）；火焰侧面降低纹理反差，强化深浅层次并减少投影在厚度方向拉伸出的条纹。火焰箭约 9994 三角面/支（箭袋的六份拷贝合计约 59964），比旧版 4822 面有所增加。圣辉箭资源不变。旧资源备份与安装记录保存在 `build/faithful-installation.json`。嗜血箭和其余箭矢、插件记录、功能版本、模组顺序均不改变。

模型检查包括原版附件及碰撞继承、纹理与引用、边界、非退化三角面、自发光标记和飞行粒子容量。试用包作为单独 MO2 模组安装时，应放在装备工坊之后覆盖资源；取消该独立模组可恢复装备工坊的资源。
