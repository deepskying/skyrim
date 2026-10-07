# 魔法箭立体造型 V2 / 资源包 2.0.0

以十二箭概念插画为方向，把十一种箭头替换成封闭立体网格，保留用户认可的嗜血箭全部 NIF 文件。火与圣辉为曲刃包芯，冰为晶簇，雷为折线棱刃，毒为双蛇牙，风为扭转镂空翼，水为水滴形，土为岩锥，暗为黑曜钩刃，星魂为光丝连接的悬浮晶体，奥术为纵向金属框架包晶。

外壳、装饰与晶体使用受光的 BSLightingShaderProperty，局部光芯使用 BSEffectShaderProperty。晶体目前采用不透明刻面与细光纹近似，不具备概念插画中的折射、透明内部气泡和复杂雕花。实际网格预览见 `art/visual-v2/overview.png` 和 `heads.png`；预览来自导出 NIF 的顶点、法线、UV 与实际 DDS，灯光与辉光为 Blender 近似。

这是独立的外观覆盖包，资源版本为 2.0.0；基础模组的 ESP、DLL 与运行时版本仍为 1.1.0。未改变 FormID、法术行为、原版装备挂点、碰撞、五支箭的背部排列及飞行/命中特效逻辑。外观变化也会应用于引用同一模型路径的旧存档箭矢。

## 安装

在 MO2 中安装 `MagicArrows-Visuals-2.0.0-MO2.zip` 为独立模组，并在左侧列表排在魔法箭工坊之后，使其覆盖基础模组的同名 meshes/textures。无需新增 ESP。关闭该覆盖模组即可恢复基础模组原外观。本次生成与打包没有自动修改游戏安装目录或 MO2 配置。

## 构建与验证

使用仓库 `reference/bow-tools/blender-4.5.13-windows-x64/4.5/python/bin/python.exe` 执行：

```text
mods/magic-arrows/source/build_models.py
mods/magic-arrows/source/verify_release.py --models-only
mods/magic-arrows/source/package_visuals.py
```

使用随附 Blender 的 `--background --python-exit-code 1 --python mods/magic-arrows/source/render_catalog.py` 渲染实际模型预览。

验证涵盖 36 个 NIF 的原生 Nifly 重读、节点与材质引用、DDS 路径、挂点与碰撞字节一致性、静态装备/粒子生命周期、顶点范围、有限法线与新模型非退化三角形，以及资源 ZIP 重读和逐文件 SHA-256。每支新箭飞行模型约 2800–3800 三角形，装备模型含六份相同网格。

旧的完整 `verify_release.py` 在当前仓库上会因既有 spell_adapters.h 与旧生成器接口不一致而失败；本轮使用明确的 `--models-only` 验证资源，没有重新生成 ESP 或原生头文件。

游戏内尚未验收：第一/第三人称持箭方向与遮挡、背部箭列、命中后的箭头、星魂悬浮间隙、不同 ENB/Community Shaders/环境灯光下的亮度。离线校验与 Blender 预览不代表已经在游戏内验证。
