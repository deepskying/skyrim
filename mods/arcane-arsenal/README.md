# 幻律兵装 · Arcane Armory 0.27.0

当前收录 **92 把武器**：80 把弓（异构 8、几何律 24、十二星座 48），以及异构巨剑 12 把。弓的基础伤害 **90**、攻速参数 **1.5**；巨剑的基础伤害 **99**、攻速参数 **1.2**。

## 本版调整

0.27.0 新增第三组异构巨剑：**余烬·断衡、流萤·掠弧、寒汐·空阙、梦隙·叠相**。分别采用三段阶梯斩刃、连续大弧度曲刃、带错层横桥的镂空剑身、三道纵向折脊。每款都有独立护手与常驻碎光组合。

使用原版双手铁巨剑的握持基准、双手装备类型、背部挂点与声音。几何体为独立刚性网格；延续已有低强度发光，未增加附魔染色或调整 ENB。紫色剑身有实际三维折面，并用现有深紫/浅紫材质交替区分折面；绿色曲刃与蓝色镂空均为真实几何。

现有「异构巨剑·试武箱」扩充至 12 把，全部武器试武箱扩充至 92 把。旧武器编号、属性、模型、贴图与脚本保持不变。四把新巨剑加入现有 SPID 名单，概率字段均为 `0.01`。

MO2 版本 **0.27.0**，插件 **ArcaneArsenal.esp** 保留 ESL 标记。更新后重启游戏。

## 现有系列

| 系列 | 款式 | 配色与命名 |
| --- | --- | --- |
| 异构巨剑 | 裂疆、双岚、错界、悬劫、偏蚀、逐翎、折矩、回旋、断衡、掠弧、空阙、叠相 | 每款独立配色，共 12 把 |
| 异构弓 | 断层、繁枝、环阵、扇阙、错翼、折岚、叠门、悬棱 | 每款独立配色，共 8 把 |
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

经典三把余烬款弦值为 2.4。粒子发光：异构与几何律 2.4、白羊 3.6、金牛 3，其他十个星座均为 2.4。巨剑主体和亮边沿用表中相应值，粒子发光 1.8，单组发射率 5、寿命 0.85 秒。保持现有 ENB 配置。

第三组粒子分别为红色方形余烬、青绿色月牙碎光、蓝色条状光粒、紫色三角碎光。

巨剑的粒子常驻，当前为局部漂散，未实现挥砍拖尾、圆核绕行或命中爆发。

弓的粒子在拉弓期间显示，放箭、取消、收弓、换武器时隐藏，并同步两个视角。当前为局部漂散，没有完整环绕轨道、放箭爆发、箭矢拖尾或命中特效。脚本只控制玩家，不支持 NPC 触发。

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
| AAHeteromorphicGreatswordsChest | 异构巨剑·试武箱 | 12 把异构巨剑 |
| AAAllBowsTestChest | 幻律兵装·试武箱 | 全部 92 把武器 |

弓与全部武器箱另有铁箭 200 支，巨剑专用箱只含十二把巨剑。请生成新箱子，旧箱子的存档库存不一定跟随插件更新。已退役的武器不再提供；本次不编辑存档。

## 安装、验证与工程

安装包为 **ArcaneArmory-0.27.0.zip**。已更新到 MO2 后不需要再次安装。本次不再改名，不修改启用状态、profile 或加载顺序。MO2 若缓存旧版本号，刷新或重启即可。

目标 Skyrim SE 1.5.97；ESP 头版本 1.7、记录版本 44、ESL 标记保持不变，主文件只有 Skyrim.esm。沿用已安装的 SKSE64 2.0.20 / NetImmerse，无新增 DLL 或行为生成步骤。

本版核对 92 把武器的属性、双手剑装备类型、中文名、模型链接、ESL 标记及旧记录身份，并用 xEdit 检查插件。四把新巨剑重新导入 NIF 与源模型比对，检查握持区、发光材质、粒子位置与原生文件序列化。旧版 115 个运行文件中仅插件更新，另新增 4 个巨剑模型；其余 114 个文件保持一致。游戏内握持、挥砍、背挂与粒子表现仍需实测。

### SPID 分发维护

每次新增武器后，安装完成时运行 `python source/sync_spid.py`，向现有用户文件补齐缺失武器；再用 `python source/sync_spid.py --check` 检查覆盖。不会创建第二份重复分发配置。

目标文件：`C:/Users/linos/Desktop/games/+skyrim/MO2/mods/功能模组-物品分发-SPID+CID配置-🟪🟨/-item_DISTR.ini`。

规则沿用 `Item = <EditorID>|NONE|NONE|NONE|NONE|1|0.01`。保留原内容、编码和换行，写入前备份到 `build/spid-before-*.ini`，匹配已有规则避免重复。本版新增四条 `AAgreatsword3red/green/blue/purple` 规则。

0.27.0 更新备份位于 `build/mo2-before-0.27.0-*`，改动前的源码、运行文件位于 `build/before-0.27.0/`。改名与 profile 历史备份位于 `build/mo2-rename-*`。源工程路径仍为 `mods/arcane-arsenal`，历史说明与建模素材保留，已移除武器的素材不进入运行包。

现有系列参数在 `source/geometric_catalog.json`、`source/aries_catalog.json`、`source/taurus_catalog.json`、`source/gemini_catalog.json`、`source/cancer_catalog.json`、`source/leo_catalog.json`、`source/virgo_catalog.json`、`source/libra_catalog.json`、`source/sagittarius_catalog.json`、`source/capricorn_catalog.json`、`source/aquarius_catalog.json`、`source/pisces_catalog.json`、`source/scorpio_catalog.json`、`source/heteromorphic_catalog.json`、`source/heteromorphic2_catalog.json`、`source/greatswords_catalog.json`、`source/greatswords2_catalog.json`、`source/greatswords3_catalog.json`；固定编号在 `source/catalog.json`，退役编号在 `source/retired_weapons.json`，清理列表在 `source/obsolete_assets.json`。

巨剑构建：便携 Blender 运行 `source/build_greatswords.py -- greatswordred`（以及 green、blue、purple），随后运行 `source/build_aries_particles.py -- --greatswords` 添加常驻粒子。使用 `source/verify_greatswords.py`、`source/verify_aries_particles.py -- --greatswords` 和 `source/verify_plugin.py` 检查；`source/render_greatswords.py` 生成实际模型预览。

第二组巨剑：运行同一建模脚本并传入 `greatsword2red`、`greatsword2green`、`greatsword2blue`、`greatsword2purple`。粒子构建、位置检查、模型检查、整组预览分别使用现有脚本加 `--greatswords2` 参数；具体造型在 `source/greatswords2_geometry.py`。

第三组巨剑：建模参数为 `greatsword3red`、`greatsword3green`、`greatsword3blue`、`greatsword3purple`，配套脚本参数为 `--greatswords3`；造型在 `source/greatswords3_geometry.py`。独立模型比对以 `build/before-0.27.0/` 为基线。
