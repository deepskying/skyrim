# 幻律兵装 · Arcane Armory 0.49.1

## 0.49.1 法杖菜单崩溃修复

修正新增记录的加载顺序：魔法效果先于附魔、附魔先于武器；四把载体设为毁灭学派。对应容器菜单显示法杖、计算消耗时主要效果为空的崩溃。DLL 增加四个附魔和八个法术的加载效果检查与日志。保留全部 FormID、外观及专属法术参数。当前 MO2/安装包版本为 **0.49.1**；静态验证与编译通过，游戏内菜单及施法需复测。

当前收录 **166 把武器**：4 把几何法杖，4 把异构弩，80 把弓（异构 8、几何律 24、十二星座 48），以及异构巨剑 12 把、异构单手剑 8 把、异构钉锤 8 把、异构双手战斧 12 把、异构双手战镰 8 把、异构长刃匕首 12 把、异构双手战锤 8 把、异构单手战斧 10 把（含两把材质测试版）。弓的基础伤害 **90**、攻速参数 **1.5**；巨剑的基础伤害 **99**、攻速参数 **1.2**；单手剑测试版暂用基础伤害 **75**、攻速参数 **1.2**；钉锤基础伤害 **90**、攻速参数 **1.0**；双手战斧、战镰和战锤基础伤害 **99**、攻速参数 **1.2**；长刃匕首基础伤害 **75**、攻速参数 **1.6**；单手战斧基础伤害 **80**、攻速参数 **1.2**。

## 本版调整

0.49.0 补齐原有 **156 把正式武器**的四色全身发光材质。本次新增覆盖140把：80把弓、8把单手剑、8把钉锤、12把双手战斧、8把战镰、12把长刃匕首、8把战锤，以及第一组4把单手斧。保留此前12把巨剑和第二组4把单手斧的材质。

| 配色 | 材质 |
| --- | --- |
| 余烬·红色 | 熔光脉络 |
| 流萤·绿色 | 星砂琉璃 |
| 寒汐·冰蓝 | 层叠晶片 |
| 梦隙·紫色 | 云雾光晶 |

整张主体发光贴图都有亮度，保留原有发光倍率、亮边、粒子与数值。弓保留Skinned标志、骨骼权重、动画及纯净弓弦；流萤·折岚的折面同步使用星砂材质，保留其较低发光倍率。几何、UV及碰撞逐块不变。两把历史材质试样、新弩与新法杖保留各自已确认的外观。

已有武器进入游戏即可显示新材质。需要整组取用时，控制台执行 `help "AAAllBowsTestChest" 4`，查询CONT完整编号，再执行 `player.placeatme <完整编号> 1`；总箱包含本模组全部166把武器。原有各类试武箱也可照常使用。

材质更新版本 **0.49.0**，227个运行文件。相对0.48，仅140个NIF材质更新，其余87个运行文件完全一致，包括ESP、新弩、法杖、DLL、PEX与DDS。所有156把正式旧武器原生NIF解析通过，42个代表模型已做Blender纹理分布检查；游戏内实际ENB亮度、拉弓与粒子播放仍需实测。更新前备份见 `build/before-0.49.0/` 和 `build/mo2-before-0.49.0-*`。

## 0.48 法杖更新回顾

0.48.0 新增 **余烬·叠炬、流萤·回梭、寒汐·悬阶、梦隙·折界** 四把法杖，以及叠层引爆、穿透回梭、分段寒阶和固定延迟裂隙四种专属法术原型。沿用认可的纯几何外观与原版左右手施法操作。

需要 Skyrim SE 1.5.97 对应的 **SKSE64 与 Address Library**；法术由随包的 `ArcaneStaves.dll` 驱动。控制台 `help AAStavesTestChest 4` 可查试武箱。容量 1000，单发消耗依次为 20/30/30/40。详细机制、获取方式和实机测试步骤见 [法杖原型说明](docs/staves-prototype.md)。编译与离线校验通过，游戏内手感、结界交互和 ENB 表现尚待测试。

本版共 227 个运行时文件、166 把武器、26 个试武箱，首发版本 **0.48.0**。

## 0.47 弩更新回顾

0.47.0 新增四把异构弩：**余烬·折翼、流萤·萦弧、寒汐·并轨、梦隙·偏枢**。基础伤害 **95**、攻速参数 **1.4**、重量 14。分别采用叠片翼、双弧翼、并轨框架与不对称弩翼，保留低亮度几何自发光；粒子分别为三角碎光、弯月微光、细线碎光与菱形碎光。

使用黎明守卫原版弩的骨架、装填行为与音效，使用弩箭。攻速为武器 Speed 参数，不代表每秒固定射击次数。控制台输入 `help "AAHeteromorphicCrossbowsChest" 4`，找到 CONT 完整编号后输入 `player.placeatme <完整编号> 1`，箱内有四把弩和 200 支钢弩箭。总试武箱也加入弩与钢弩箭。

插件仍为 `ArcaneArsenal.esp`，保持 ESL 标记及 1.5.97 兼容。主文件为 Skyrim.esm、Update.esm、Dawnguard.esm，旧武器的插件内编号全部保留。SPID 四条新规则均使用原有 `Item` 格式和 `0.01` 概率。MO2 显示版本 **0.47.0**。

保留 0.46 的全部 12 把巨剑材质，以及 0.45 的第二组单手战斧材质。离线模型、骨骼、粒子与插件检查完成；第一/第三人称握持、装填、射击、收武器和实际 ENB 亮度需要进游戏复测。

## 现有系列

| 系列 | 款式 | 配色与命名 |
| --- | --- | --- |
| 几何法杖 | 叠炬、回梭、悬阶、折界 | 红、绿、蓝、紫各一把，含专属法术原型 |
| 异构弩 | 折翼、萦弧、并轨、偏枢 | 红、绿、蓝、紫各一把，共 4 把 |
| 异构单手战斧 | 裂冠、萦枝、断湾、缺轮、错牙、回翎、叠潮、折冕 | 8 把原款，另加 2 把错牙材质测试版 |
| 异构双手战锤 | 倾岳、森垒、断垒、沉环、错压、绞岚、贯潮、叠轨 | 每款独立配色，共 8 把 |
| 异构长刃匕首 | 噬角、回牙、穿隙、隐棱、断霆、脉翎、折阶、蚀月、偏锋、缠枝、双鸣、回棱 | 每款独立配色，共 12 把 |
| 异构双手战镰 | 断穹、萦月、截潮、折夜、断棘、盘岚、折渊、环寂 | 每款独立配色，共 8 把 |
| 异构双手战斧 | 裂岳、回岚、断扉、蚀翼、断脊、垂岚、错潮、缺环、崩阶、卷岚、横澜、折扇 | 每款独立配色，共 12 把 |
| 异构钉锤 | 崩垒、旋棘、镇环、错棱、裂齿、棘笼、砧阶、星殛 | 每款独立配色，共 8 把 |
| 异构单手剑 | 截锋、游梭、棱隙、错影、破阙、穿岚、环衡、开屏 | 每款独立配色，共 8 把 |
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

第三组巨剑粒子分别为红色方形余烬、青绿色月牙碎光、蓝色条状光粒、紫色三角碎光。

单手剑主体和亮边沿用同色巨剑参数，粒子发光 1.8、单组发射率 4、寿命 0.85 秒。红色菱形余烬、绿色梭形光粒、蓝色空心三角、紫色短光条与小光点分别围绕各款剑身漂散；悬浮核心是静态几何。

钉锤主体与亮边沿用同色单手剑参数，粒子发光 1.8、单组发射率 4、寿命 0.85 秒；第一组依次使用方形余烬、青绿月牙、蓝色空心环和紫色三角碎光。第二组使用红色三角余烬、薄荷菱形光粒、青蓝短光条和浅紫菱形碎光，均搭配细小光点。

双手战斧主体和亮边也沿用上述低强度参数，粒子发光 1.8、单组发射率 4、寿命 0.85 秒。第一组分别使用红色三角、薄荷菱形、青蓝短光条、浅紫空心菱形；第二组分别使用红色方形、薄荷梭形、青蓝短光条、浅紫月牙，均与小光点一起从斧头附近漂散。第三组依次为红色方形余烬、薄荷月牙、青蓝短光条和浅紫三角碎光，沿用发光 1.8、单组发射率 4、寿命 0.85 秒。

第一组战镰依次使用红色方形余烬、薄荷月牙、青蓝短光条和浅紫三角碎光，每把六个发射点分布于镰刃附近。粒子发光 1.8、单组发射率 4、寿命 0.85 秒，主体和亮边沿用同色战斧参数。

第二组战镰依次使用红色棱形余烬、薄荷弧片、青蓝针状光粒和浅紫空心菱片；同样使用六个局部发射点和原有低强度参数。

第一组长刃匕首依次使用红色棱形余烬、薄荷弧片、青蓝针状光粒和浅紫三角碎片；第二组使用折角红色碎片、薄荷棱形光屑、青蓝短条和浅紫月牙微粒；第三组使用红色方片、薄荷菱形、青蓝短线和紫色三角碎片。双鸣的发射点集中在刃槽内，其余各款沿刀身分布。每把六个局部发射点，粒子发光 1.8、单组发射率 3、寿命 0.85 秒，半径 0.3。主体和亮边沿用同色单手剑的低强度参数。

第一组战锤依次使用红色三角余烬、薄荷菱形光屑、青蓝短光条和浅紫三角碎片，搭配细小光点。每把六个局部发射点，发光 1.8、单组发射率 4、寿命 0.85 秒、半径 0.4。粒子集中在锤头、笼内、双柱槽内和环内。

第二组战锤分别使用红色方形碎片、薄荷月牙、青蓝短线和浅紫菱形光屑，搭配细小光点。每把六个局部发射点，沿用粒子发光 1.8、单组发射率 4、寿命 0.85 秒、半径 0.4；发射点分布于撞击端面、螺旋间隙和叠框内部。

巨剑、单手剑、钉锤、双手战斧、战镰、匕首和战锤的粒子常驻，当前为局部漂散，未实现挥砍拖尾、圆核绕行或命中爆发。

弓的粒子在拉弓期间显示，放箭、取消、收弓、换武器时隐藏，并同步两个视角。当前为局部漂散，没有完整环绕轨道、放箭爆发、箭矢拖尾或命中特效。脚本只控制玩家，不支持 NPC 触发。

单手战斧分别使用红色三角碎片、薄荷菱形光屑、青蓝短线和浅紫三角碎片，搭配小光点；每把六个局部发射点分布于斧面与镂空附近。粒子发光 1.8、发射率 3、寿命 0.85 秒、半径 0.3，主体亮边沿用现有同色参数。

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
| AAHeteromorphicBattleaxesChest | 异构战斧·试武箱 | 12 把双手战斧 |
| AAHeteromorphicWaraxesChest | 异构单手战斧·试武箱 | 10 把单手战斧 |
| AAMaterialTestChest | 材质对比·试武箱 | 原版错牙、磨砂红宝石、黑曜石 |
| AAHeteromorphicWarhammersChest | 异构战锤·试武箱 | 8 把双手战锤 |
| AAHeteromorphicDaggersChest | 异构匕首·试武箱 | 12 把长刃匕首 |
| AAHeteromorphicScythesChest | 异构战镰·试武箱 | 8 把双手战镰 |
| AAHeteromorphicMacesChest | 异构钉锤·试武箱 | 8 把异构钉锤 |
| AAHeteromorphicSwordsChest | 异构单手剑·试武箱 | 8 把异构单手剑 |
| AAHeteromorphicGreatswordsChest | 异构巨剑·试武箱 | 12 把异构巨剑 |
| AAAllBowsTestChest | 幻律兵装·试武箱 | 全部 158 把武器 |

弓与全部武器箱另有铁箭 200 支，巨剑专用箱只含十二把巨剑，单手剑专用箱只含八把单手剑，钉锤专用箱只含八把钉锤，战斧专用箱只含十二把战斧。请生成新箱子，旧箱子的存档库存不一定跟随插件更新。已退役的武器不再提供；本次不编辑存档。

## 安装、验证与工程

安装包为 **ArcaneArmory-0.46.0.zip**。已更新到 MO2 后不需要再次安装。本次不再改名，不修改启用状态、profile 或加载顺序。MO2 若缓存旧版本号，刷新或重启即可。

目标 Skyrim SE 1.5.97；ESP 头版本 1.7、记录版本 44、ESL 标记保持不变，主文件只有 Skyrim.esm。沿用已安装的 SKSE64 2.0.20 / NetImmerse，无新增 DLL 或行为生成步骤。

本版相对0.45.0，仅更新12个巨剑NIF，原有其余192个运行文件逐字节一致（包括ESP及全部贴图），共204个运行文件。逐把检查原生NIF读取、贴图链接、发光倍率、模型/UV/碰撞/亮边不变；十二把的96个粒子块分别通过原生序列化验证。实际NIF逐款导入Blender检查纹理分布。尚未进行游戏内实测。

### SPID 分发维护

每次新增武器后，安装完成时运行 `python source/sync_spid.py`，向现有用户文件补齐缺失武器；再用 `python source/sync_spid.py --check` 检查覆盖。不会创建第二份重复分发配置。

目标文件：`C:/Users/linos/Desktop/games/+skyrim/MO2/mods/功能模组-物品分发-SPID+CID配置-🟪🟨/-item_DISTR.ini`。

规则沿用 `Item = <EditorID>|NONE|NONE|NONE|NONE|1|0.01`。保留原内容、编码和换行，写入前备份到 `build/spid-before-*.ini`，匹配已有规则避免重复。本版没有新增武器，验证现有 158 把武器的分发覆盖，无需追加规则。

本次更新备份位于 `build/mo2-before-0.46.0-*`，改动前的源码、运行文件位于 `build/before-0.46.0/`。改名与 profile 历史备份位于 `build/mo2-rename-*`。源工程路径仍为 `mods/arcane-arsenal`，历史说明与建模素材保留，已移除武器的素材不进入运行包。

现有系列参数在 `source/geometric_catalog.json`、`source/aries_catalog.json`、`source/taurus_catalog.json`、`source/gemini_catalog.json`、`source/cancer_catalog.json`、`source/leo_catalog.json`、`source/virgo_catalog.json`、`source/libra_catalog.json`、`source/sagittarius_catalog.json`、`source/capricorn_catalog.json`、`source/aquarius_catalog.json`、`source/pisces_catalog.json`、`source/scorpio_catalog.json`、`source/heteromorphic_catalog.json`、`source/heteromorphic2_catalog.json`、`source/greatswords_catalog.json`、`source/greatswords2_catalog.json`、`source/greatswords3_catalog.json`、`source/swords_catalog.json`、`source/swords2_catalog.json`、`source/maces_catalog.json`、`source/maces2_catalog.json`、`source/battleaxes_catalog.json`、`source/battleaxes2_catalog.json`、`source/battleaxes3_catalog.json`；固定编号在 `source/catalog.json`，退役编号在 `source/retired_weapons.json`，清理列表在 `source/obsolete_assets.json`。

巨剑构建：便携 Blender 运行 `source/build_greatswords.py -- greatswordred`（以及 green、blue、purple），随后运行 `source/build_aries_particles.py -- --greatswords` 添加常驻粒子。使用 `source/verify_greatswords.py`、`source/verify_aries_particles.py -- --greatswords` 和 `source/verify_plugin.py` 检查；`source/render_greatswords.py` 生成实际模型预览。

第二组巨剑：运行同一建模脚本并传入 `greatsword2red`、`greatsword2green`、`greatsword2blue`、`greatsword2purple`。粒子构建、位置检查、模型检查、整组预览分别使用现有脚本加 `--greatswords2` 参数；具体造型在 `source/greatswords2_geometry.py`。

第三组巨剑：建模参数为 `greatsword3red`、`greatsword3green`、`greatsword3blue`、`greatsword3purple`，配套脚本参数为 `--greatswords3`；造型在 `source/greatswords3_geometry.py`。独立模型比对以 `build/before-0.27.0/` 为基线。

单手剑构建：先用普通 Python 运行 `source/prepare_sword_reference.py` 提取本地 IronSword，再用便携 Blender 运行 `source/build_swords.py -- swordred`（以及 green、blue、purple）。粒子构建和位置检查使用 `--swords` 参数；模型检查为 `source/verify_swords.py`，整组预览为 `source/render_swords.py`。具体造型在 `source/swords_geometry.py`，第一组最初以 `build/before-0.28.0/` 为基线。

第二组单手剑：建模参数为 `sword2red`、`sword2green`、`sword2blue`、`sword2purple`。粒子构建、粒子检查、模型检查、整组预览均使用 `--swords2`；造型在 `source/swords2_geometry.py`，以 `build/before-0.29.0/` 为基线。粒子依次为方形余烬、针状微光、空心圆环和三角碎光，均搭配细小光点。

钉锤构建：普通 Python 运行 `source/prepare_mace_reference.py`，然后用便携 Blender 运行 `source/build_maces.py -- macered`（以及 green、blue、purple）。粒子构建与位置检查使用 `--maces`；模型检查为 `source/verify_maces.py`，预览为 `source/render_maces.py -- --lineup-only`，造型在 `source/maces_geometry.py`。本组检查以 `build/before-0.30.0/` 为基线。

第二组钉锤：建模参数为 `mace2red`、`mace2green`、`mace2blue`、`mace2purple`。粒子构建、粒子检查、模型检查与整组预览使用 `--maces2`；造型在 `source/maces2_geometry.py`，以 `build/before-0.31.0/` 为基线。预览图为 `art/maces2-lineup.png`，仅展示模型结构，不代表 ENB 与游戏粒子实测。

双手战斧构建：普通 Python 运行 `source/prepare_battleaxe_reference.py` 提取本地 IronBattleAxe。便携 Blender 运行 `source/build_battleaxes.py -- battleaxered`（以及 green、blue、purple）。粒子构建和位置检查使用 `--battleaxes`；模型检查为 `source/verify_battleaxes.py`，整组预览为 `source/render_battleaxes.py -- --lineup-only`。造型在 `source/battleaxes_geometry.py`，以 `build/before-0.32.0/` 为基线。`art/battleaxes-lineup.png` 为源模型预览，不代表游戏内 ENB 与粒子实测。

第二组战斧：建模参数为 `battleaxe2red`、`battleaxe2green`、`battleaxe2blue`、`battleaxe2purple`。粒子构建、位置检查、模型检查和整组预览使用 `--battleaxes2`；造型在 `source/battleaxes2_geometry.py`，以 `build/before-0.33.0/` 为基线。`art/battleaxes2-lineup.png` 为模型结构预览，不代表游戏内 ENB 和粒子实测。

第三组战斧：建模参数为 `battleaxe3red`、`battleaxe3green`、`battleaxe3blue`、`battleaxe3purple`。粒子构建、位置检查、模型检查和整组预览使用 `--battleaxes3`；造型在 `source/battleaxes3_geometry.py`，以 `build/before-0.34.0/` 为基线。`art/battleaxes3-lineup.png` 为模型结构预览，不代表游戏内 ENB 和粒子实测。

第一组战镰：参数在 `source/scythes_catalog.json`，造型在 `source/scythes_geometry.py`。便携 Blender 运行 `source/build_battleaxes.py -- scythered`（以及 green、blue、purple）复用双手武器导出流程；粒子构建、位置检查、`verify_battleaxes.py` 模型检查与 `render_battleaxes.py` 整组预览均使用 `--scythes`。基线为 `build/before-0.35.0/`；`art/scythes-lineup.png` 为源模型结构预览，不代表游戏内发光和粒子实测。

第二组战镰：参数在 `source/scythes2_catalog.json`，造型在 `source/scythes2_geometry.py`。建模使用 `scythe2red/green/blue/purple`，粒子构建、位置检查、模型检查和整组预览使用 `--scythes2`。基线为 `build/before-0.36.0/`，预览为 `art/scythes2-lineup.png`。

第一组长刃匕首：普通 Python 运行 `source/prepare_dagger_reference.py` 提取原版参考。便携 Blender 运行 `source/build_daggers.py -- daggerred`（以及 green、blue、purple）。粒子构建和位置检查使用 `--daggers`，模型检查为 `source/verify_daggers.py`，预览为 `source/render_daggers.py -- --lineup-only`。造型、参数在 `source/daggers_geometry.py`、`source/daggers_catalog.json`，基线为 `build/before-0.37.0/`；`art/daggers-lineup.png` 是源模型预览，不代表游戏内 ENB 和粒子实测。

第二组长刃匕首：便携 Blender 运行 `source/build_daggers.py -- dagger2red`（以及 green、blue、purple）。粒子构建和位置检查使用 `--daggers2`；模型检查为 `source/verify_daggers2.py`；预览为 `source/render_daggers.py -- --daggers2 --lineup-only`。造型、参数在 `source/daggers2_geometry.py`、`source/daggers2_catalog.json`，基线为 `build/before-0.38.0/`。插画位于 `art/concepts/heteromorphic-daggers-four-colors-02/`，`art/daggers2-lineup.png` 是源模型预览。

第三组长刃匕首：便携 Blender 运行 `source/build_daggers.py -- dagger3red`（以及 green、blue、purple）。粒子构建和位置检查使用 `--daggers3`；模型检查为 `source/verify_daggers3.py`；预览为 `source/render_daggers.py -- --daggers3 --lineup-only`。造型和参数位于 `source/daggers3_geometry.py`、`source/daggers3_catalog.json`，基线为 `build/before-0.39.0/`。概念插画位于 `art/concepts/heteromorphic-daggers-four-colors-03/`，`art/daggers3-lineup.png` 是源模型预览。

第一组双手战锤：普通 Python 运行 `source/prepare_warhammer_reference.py` 提取本地原版参考。便携 Blender 运行 `source/build_warhammers.py -- warhammerred`（以及 green、blue、purple）。粒子构建和位置检查使用 `--warhammers`；模型检查为 `source/verify_warhammers.py`；预览为 `source/render_warhammers.py -- --lineup-only`。造型和参数位于 `source/warhammers_geometry.py`、`source/warhammers_catalog.json`，基线为 `build/before-0.40.0/`。`art/warhammers-lineup.png` 是源模型结构预览，不代表游戏内 ENB 与粒子实测。

第一组单手战斧：普通 Python 运行 `source/prepare_waraxe_reference.py`，便携 Blender 运行 `source/build_waraxes.py -- waraxered`（以及 green、blue、purple）。粒子构建和位置检查使用 `--waraxes`；模型检查为 `source/verify_waraxes.py`，原生序列化检查为 `source/verify_draw_particles.py <key>`，整组预览为 `source/render_waraxes.py -- --lineup-only`。造型和参数位于 `source/waraxes_geometry.py`、`source/waraxes_catalog.json`，基线为 `build/before-0.41.0/`。`art/waraxes-lineup.png` 为源模型结构预览，不代表游戏内 ENB 或粒子实测。

第二组单手战斧：建模参数为 `waraxe2red`、`waraxe2green`、`waraxe2blue`、`waraxe2purple`，复用 `source/build_waraxes.py`。粒子构建、位置检查和整组渲染参数为 `--waraxes2`；模型检查为 `source/verify_waraxes2.py`。造型与配色位于 `source/waraxes2_geometry.py`、`source/waraxes2_catalog.json`。粒子分别是红色三角、薄荷月牙、青蓝短线、浅紫三角，六个局部发射点沿斧面或刃槽分布，沿用粒子发光 1.8、发射率 3、寿命 0.85 秒、半径 0.3。基线为 `build/before-0.42.0/`，`art/waraxes2-lineup.png` 为模型结构预览，游戏内挥砍与粒子表现仍需实测。

第二组双手战锤：建模参数为 `warhammer2red`、`warhammer2green`、`warhammer2blue`、`warhammer2purple`，复用 `source/build_warhammers.py`。粒子构建、位置检查和整组渲染参数为 `--warhammers2`；模型检查为 `source/verify_warhammers2.py`。造型与参数位于 `source/warhammers2_geometry.py`、`source/warhammers2_catalog.json`。基线为 `build/before-0.43.0/`，`art/warhammers2-lineup.png` 为源模型结构预览，不代表游戏内发光与粒子实测。

四色发光材质：`source/build_emissive_materials.py` 生成四组 DDS 并仅修改第二组单手斧的主体材质；`source/verify_emissive_materials.py` 独立验证。使用包含 numpy/Pillow 的 bundled Python。实际 NIF 的离线预览位于 `art/emissive-materials/`。

巨剑材质覆盖：`python source/apply_greatsword_materials.py`；验证：`python source/apply_greatsword_materials.py --verify`。材质基线为 `build/before-0.46.0/`，预览工程与图片位于 `art/greatsword-materials/`。

全武器材质：`source/apply_collection_materials.py` 在独立stage生成/验证材质；`source/merge_collection_materials.py` 在比对基线后合入140个模型。方案及42个代表预览位于 `art/collection-materials/`。不包含任何游戏实拍验收声明。
