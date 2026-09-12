# 幻律兵装 · Arcane Armory 0.24.0

当前收录 **80 把弓**：异构 8 把、几何律 24 把、十二星座各 4 把。全部基础伤害 **90**，武器攻速参数（Speed）**1.5**。

## 本版调整

新增第二组异构弓：**余烬·错翼、流萤·折岚、寒汐·叠门、梦隙·悬棱**。分别采用不对称开槽翼刃、立体折扇、错层长框、悬浮菱片，配有各自的拉弓碎光组合。绿色折扇额外使用发光值 1.05 的暗折面区分层次。

异构试武箱扩充至 8 把弓，全部武器试武箱扩充至 80 把。其余武器编号与资源保留；退役编号 0x90C–0x918 不再分配。新增武器的 SPID 概率字段为 `0.01`。

MO2 版本 **0.24.0**，插件 **ArcaneArsenal.esp** 保留 ESL 标记。更新后重启游戏。

## 现有系列

| 系列 | 款式 | 配色与命名 |
| --- | --- | --- |
| 异构 | 断层、繁枝、环阵、扇阙、错翼、折岚、叠门、悬棱 | 每款独立配色，共 8 把 |
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
| AAHeteromorphicTestChest | 异构·试武箱 | 8 把异构弓 |
| AAAllBowsTestChest | 幻律兵装·试武箱 | 全部 80 把弓 |

每个箱子另有铁箭 200 支。请生成新箱子，旧箱子的存档库存不一定跟随插件更新。已退役的武器不再提供；本次不编辑存档。

## 安装、验证与工程

安装包为 **ArcaneArmory-0.24.0.zip**。已更新到 MO2 后不需要再次安装。本次不再改名，不修改启用状态、profile 或加载顺序。MO2 若缓存旧版本号，刷新或重启即可。

目标 Skyrim SE 1.5.97；ESP 头版本 1.7、记录版本 44、ESL 标记保持不变，主文件只有 Skyrim.esm。沿用已安装的 SKSE64 2.0.20 / NetImmerse，无新增 DLL 或行为生成步骤。

本版检查武器数量、基础伤害、攻速、旧武器记录、ESL 标记和退役编号，编译并核对 80 个拉弓脚本绑定。四个新模型检查骨骼导出、三个受控姿态、粒子序列化与发射位置；这些离线检查不替代游戏内的握持、拉弓和视觉测试。相比 0.23.1，新增 4 个模型，更新插件和脚本，其余 101 个运行文件保持一致。

### SPID 分发维护

每次新增武器后，安装完成时运行 `python source/sync_spid.py`，向现有用户文件补齐缺失武器；再用 `python source/sync_spid.py --check` 检查覆盖。不会创建第二份重复分发配置。

目标文件：`C:/Users/linos/Desktop/games/+skyrim/MO2/mods/功能模组-物品分发-SPID+CID配置-🟪🟨/-item_DISTR.ini`。

规则沿用 `Item = <EditorID>|NONE|NONE|NONE|NONE|1|0.01`。保留原内容、编码和换行，写入前备份到 `build/spid-before-*.ini`，匹配已有规则避免重复。本版新增四条 `AAheteromorphic2red/green/blue/purple` 规则。

运行文件更新备份位于 `build/mo2-before-0.24.0-*`，本次改动前的源码、运行文件位于 `build/before-0.24.0/`。改名与 profile 历史备份位于 `build/mo2-rename-*`。源工程路径仍为 `mods/arcane-arsenal`，历史说明与建模素材保留，已移除武器的素材不进入运行包。

现有系列参数在 `source/geometric_catalog.json`、`source/aries_catalog.json`、`source/taurus_catalog.json`、`source/gemini_catalog.json`、`source/cancer_catalog.json`、`source/leo_catalog.json`、`source/virgo_catalog.json`、`source/libra_catalog.json`、`source/sagittarius_catalog.json`、`source/capricorn_catalog.json`、`source/aquarius_catalog.json`、`source/pisces_catalog.json`、`source/scorpio_catalog.json`、`source/heteromorphic_catalog.json`、`source/heteromorphic2_catalog.json`；固定编号在 `source/catalog.json`，退役编号在 `source/retired_weapons.json`，清理列表在 `source/obsolete_assets.json`。
