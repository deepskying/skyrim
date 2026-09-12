# 幻律兵装 · Arcane Armory 0.23.1

当前收录 **76 把弓**：异构 4 把、几何律 24 把、十二星座各 4 把。全部基础伤害 **90**，武器攻速参数（Speed）**1.5**。

## 本版调整

移除四把水晶材质实验弓：余烬·绯晶、流萤·翠脉、寒汐·霜棱、梦隙·紫珀，同时移除其锻造配方、第一人称模型记录和「晶质·试武箱」。清理运行包中的 4 个独占模型、12 张独占贴图，并移除拉弓脚本中的四个绑定。全部武器试武箱恢复为 76 把弓。

其余 76 把武器的编号、属性、模型、贴图和粒子参数保持不变。退役的 0x90C–0x918 编号保留，不分配给其他物品。素材和源码留在项目历史中，当前运行包不再包含水晶实验。

MO2 版本 **0.23.1**，插件 **ArcaneArsenal.esp** 保留 ESL 标记。更新后重启游戏。

## 现有系列

| 系列 | 款式 | 配色与命名 |
| --- | --- | --- |
| 异构 | 断层、繁枝、环阵、扇阙 | 每款独立配色，共 4 把 |
| 几何律 | 叠弦、旋序、流菱、六垣、方旋、锋羽 | 每款四种配色，共 24 把 |
| 星座 | 白羊、金牛、双子、巨蟹、狮子、处女、天秤、天蝎、射手、摩羯、水瓶、双鱼 | 每个星座四种配色，共 48 把 |

**余烬**为红/玫红、**流萤**为翠绿/薄荷青、**寒汐**为冰蓝/青蓝、**梦隙**为蓝紫/浅紫。例如余烬·六垣、寒汐·金牛。

六款几何律现在都有各自的握把造型，全部取消静态六芒星。拉弓显示对应碎光，没有额外拉弓六芒星。几何律没有预设吸血附魔，经典三款在 0.8.0 已移除该附魔。

## 发光与粒子

原有几何光弓的主体、亮边、弦沿用 0.7.1 降低后的参数：

| 配色 | 主体 | 亮边 | 弓弦 |
| --- | ---: | ---: | ---: |
| 余烬 | 1.8 | 3.6 | 2.25 |
| 流萤 | 2.25 | 4.5 | 3.15 |
| 寒汐 | 2.25 | 5.4 | 3.6 |
| 梦隙 | 2.7 | 5.4 | 3.6 |

经典三把余烬款弦值为 2.4。粒子发光：异构与几何律 2.4、白羊 3.6、金牛 3，其他十个星座均为 2.4。本版保持原有亮度与 ENB 不变。

粒子在拉弓期间显示，放箭、取消、收弓、换武器时隐藏，并同步两个视角。当前为局部漂散，没有完整环绕轨道、放箭爆发、箭矢拖尾或命中特效。脚本只控制玩家，不支持 NPC 触发。

## 获取武器

从 MO2 的现有 SKSE 启动游戏，控制台查询对应箱子：

```text
help "AAAllBowsTestChest" 4
```

用查询到的完整 CONT 编号生成箱子：

```text
player.placeatme <CONT的完整编号> 1
```

尖括号内容需要替换；不要把本地编号当作完整编号。FE 加载前缀以实际查询为准。

| 搜索名 | 显示名称 | 内容 |
| --- | --- | --- |
| AAGeometricTestChest | 几何律·试武箱 | 24 把几何弓 |
| AAAriesTestChest | 白羊座·试武箱 | 4 把白羊弓 |
| AATaurusTestChest | 金牛座·试武箱 | 4 把金牛弓 |
| AAGeminiTestChest | 双子座·试武箱 | 4 把双子弓 |
| AACancerTestChest | 巨蟹座·试武箱 | 4 把巨蟹弓 |
| AALeoTestChest | 狮子座·试武箱 | 4 把狮子弓 |
| AAVirgoTestChest | 处女座·试武箱 | 4 把处女弓 |
| AALibraTestChest | 天秤座·试武箱 | 4 把天秤弓 |
| AASagittariusTestChest | 射手座·试武箱 | 4 把射手弓 |
| AACapricornTestChest | 摩羯座·试武箱 | 4 把摩羯弓 |
| AAAquariusTestChest | 水瓶座·试武箱 | 4 把水瓶弓 |
| AAPiscesTestChest | 双鱼座·试武箱 | 4 把双鱼弓 |
| AAScorpioTestChest | 天蝎座·试武箱 | 4 把天蝎弓 |
| AAHeteromorphicTestChest | 异构·试武箱 | 4 把异构弓 |
| AAAllBowsTestChest | 幻律兵装·试武箱 | 全部 76 把弓 |

每个箱子另有铁箭 200 支。请生成新箱子，旧箱子的存档库存不一定跟随插件更新。已退役的武器不再提供；本次不编辑存档。

## 安装、验证与工程

安装包为 **ArcaneArmory-0.23.1.zip**。已更新到 MO2 后不需要再次安装。本次不再改名，不修改启用状态、profile 或加载顺序。MO2 若缓存旧版本号，刷新或重启即可。

目标 Skyrim SE 1.5.97；ESP 头版本 1.7、记录版本 44、ESL 标记保持不变，主文件只有 Skyrim.esm。沿用已安装的 SKSE64 2.0.20 / NetImmerse，无新增 DLL 或行为生成步骤。

本版检查武器数量、基础伤害、攻速、旧武器记录、ESL 标记和退役编号。验证粒子脚本编译及其 76 个绑定；与更新前逐文件核对，除插件和脚本更新、16 个水晶独占资源移除外，其余 101 个运行文件完全一致。安装包和 MO2 进行逐文件校验。

运行文件更新备份位于 `build/mo2-before-0.23.1-*`，本次改动前的源码、运行文件位于 `build/before-0.23.1/`。改名与 profile 历史备份位于 `build/mo2-rename-*`。源工程路径仍为 `mods/arcane-arsenal`，历史说明与建模素材保留，已移除武器的素材不进入运行包。

现有系列参数在 `source/geometric_catalog.json`、`source/aries_catalog.json`、`source/taurus_catalog.json`、`source/gemini_catalog.json`、`source/cancer_catalog.json`、`source/leo_catalog.json`、`source/virgo_catalog.json`、`source/libra_catalog.json`、`source/sagittarius_catalog.json`、`source/capricorn_catalog.json`、`source/aquarius_catalog.json`、`source/pisces_catalog.json`、`source/scorpio_catalog.json`、`source/heteromorphic_catalog.json`；固定编号在 `source/catalog.json`，退役编号在 `source/retired_weapons.json`，清理列表在 `source/obsolete_assets.json`。
