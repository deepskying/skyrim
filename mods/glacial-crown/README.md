# 极寒王冠 / Glacial Crown — 0.1.0 原型

面向 Skyrim Special Edition 1.5.97 的独立冰弓。当前是验证模型、骨架和武器记录的首版原型，尚未完成游戏内实测，也未达到概念图的最终美术与动态特效效果。

## 已有内容

- 新制作的晶簇弓身、冰蓝发光核心、细弓弦、静态分段霜环与悬浮晶体。
- 六个材质网格、13,002 个三角面、七根原版弓骨骼；弓身与弦已绑定权重。
- 1024 × 1024 DDS 材质与 mipmaps。冰面目前采用不透明材质模拟，无真实透明折射。
- 独立 GlacialCrown.esp，仅依赖 Skyrim.esm，无原版记录覆盖，无脚本或 SKSE DLL。
- 基础伤害 18、重量 10、价值 1800、附魔容量 1800，使用原版冰霜附魔 EnchWeaponFrostDamage02。
- 锻造配方：银锭 × 2、精炼孔雀石 × 3、冰盐 × 2。在铁匠锻造台制作，无技能条件。当前没有磨刀石强化配方。
- 使用普通箭矢；名称暂用英文 Glacial Crown。

## 安装和获取

MO2 使用“从压缩包安装”，选择 packaging/GlacialCrown-0.1.0.zip，随后勾选左侧模组及右侧 GlacialCrown.esp。压缩包根目录直接包含 ESP、meshes 和 textures。

推荐先使用测试角色验证。可以锻造，也可以在游戏控制台输入：

```text
help "Glacial Crown" 4
player.additem <上一条返回的 WEAP 编号> 1
```

不要照抄尖括号。武器的本地编号是 000801，前两位取决于实际插件加载顺序，不能固定写成 01。

## 验证与限制

已完成 Blender 实际模型渲染、导出 NIF 后重新导入、材质 DDS 读取，以及 SSEDump64 / xEdit 的记录与引用检查。检查输出在本地 build/ 目录。

尚未实测：第一与第三人称持握、满弓变形、箭矢对齐、背负穿插、丢落碰撞、不同光照下发光强度、附魔消耗和锻造菜单。碰撞沿用原版弓的简单盒体，未覆盖外伸装饰晶簇。

霜环目前不会旋转，也没有冰雾、蓄力联动、冰箭拖尾或特殊命中效果。这些属于后续制作内容。预览图是 Blender 渲染，不是游戏截图。

## 工程文件

- art/glacial-crown.blend：可继续编辑的 Blender 工程。
- art/glacial-crown-prototype.png：实际模型预览。
- source/build_model.py：模型、材质与 NIF 构建脚本。
- source/build_plugin.py：独立 ESP 构建脚本。
- data/：可供 MO2 加载的游戏文件。

本地构建依赖 reference/bow-tools 下的 Blender 4.5.13、PyNifly 28.2、纹理转换工具和从已安装游戏提取的弓骨架参考工程。插件构建脚本读取本机 Skyrim.esm。安装包不包含游戏主文件或原版贴图。换电脑构建需要调整脚本内工具与游戏路径。
