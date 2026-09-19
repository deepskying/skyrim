# 幻律兵装 · Arcane Armory 0.53.0

## 0.53.0 四款发光盾牌

新增已确认的四款盾牌：**绯玉日蚀**（旋叠圆盾）、**青碧折叶**（不对称叶形盾）、**海蓝潮门**（阶梯塔盾）、**幻紫星棱**（星盘菱形盾）。全部为轻甲盾，**基础护甲 90、重量 8、价值 1800**。游戏界面显示护甲会受技能和增益影响。

盾面复用现有武器的 R5 绯玉霜华、G7 青碧层晶、B7 海蓝层晶和 P3 幻紫欧泊材质，并沿用 0.52.2 降低后的发光：红/绿/蓝/紫主体分别为 0.45/0.55/0.55/0.50，亮边分别为 1.20/1.35/1.45/1.20。暗金属边框、背板和握柄不发光；没有新增附魔、脚本或 DLL。

使用原版精灵盾的 `SHIELD` 挂点、盾牌装备类型、轻甲关键词和种族支持；男女共用对应盾牌模型。保留原版库存标记和刚体设置，为每款几何生成包围模型的凸碰撞。可在熔炉用 2 个银锭和 3 个精炼孔雀石锻造。

获取整组：控制台输入 `help "AAShieldsTestChest" 4`，找到 CONT 的完整编号，再执行 `player.placeatme <完整编号> 1`。盾牌也加入现有总试武箱。单件 EditorID 分别为 `AAshieldred`、`AAshieldgreen`、`AAshieldblue`、`AAshieldpurple`。为这四件装备在既有 `-item_DISTR.ini` 中添加 `Item = <EditorID>|NONE|NONE|NONE|NONE|1|0.01`，添加前备份并保留其他规则。

当前为 **164 把武器 + 4 面盾牌、25 个试用箱、246 个运行文件**。新增 4 个 NIF 和 2 张带完整 mipmap 的 DDS；新增记录使用 `000BA0–000BAC`，不复用任何退役编号。原 164 把武器的模型、材质、属性和编号保持不变。

构建：`prepare_shield_reference.py`、`build_shield_textures.py`、Blender 运行 `build_shields.py`、`build_plugin.py`。验证：`verify_plugin.py`、`verify_shields.py`；实际 NIF/DDS 正面、背面及暗处发光预览位于 `art/shields/`，由 `render_shields.py` 生成。基线保存于 `build/before-0.53.0/`；MO2 安装和 SPID 同步均生成备份。离线检查覆盖模型解析、三角形、材质引用、装备记录、碰撞包围及旧资产保留；游戏内持盾、格挡、掉落和 ENB 显示仍需实测。

## 0.52.3 移除材质试制战斧

移除四把历史材质试制单手战斧：余烬·错牙·磨砂红宝石、余烬·错牙·黑曜石、余烬·错牙·赤钢试作与流萤·回翎·翠晶试作，同时移除 `AAMaterialTestChest` 材质对比试武箱及四条 SPID 分发规则。它们的 12 个武器相关 FormID 和试武箱 FormID `000A17` 均永久退役，不会重新分配。

现有总数调整为 **164 把武器**、**24 个试武箱**、**240 个运行文件**；异构单手战斧试武箱保留 8 把正式武器。移除了四个NIF和12张专用DDS。MO2安装会备份并删除旧文件；构建、ESP和安装验证均在本版本完成。

## 0.52.2 全武器发光与红色泛白修正

根据游戏内截图，将全部168把武器的主体、亮边和弦自发光大幅下调，使材质纹理在HDR/ENB下仍可辨认。主体发光调整为红0.45、绿0.55、蓝0.55、紫0.50；亮边为红1.20、绿1.35、蓝1.45、紫1.20；弦为红/紫0.85、绿/蓝0.95。粒子参数保持不变。

红色R5绯玉霜华另行重建彩色发光图：平均亮度从0.473降至0.259（约45%），色彩跨度从0.326提高至0.351。浅粉玉层由偏白发光改为更浓的玫红，保留冰青矿脉。漫反射、法线、高光贴图和四色材质设计本身不变。

相对0.52.1更新168个NIF的自发光倍率，以及1张红色发光DDS；无新增运行文件，仍为168把武器、256个运行文件。模型、UV、骨骼、碰撞、弦结构、粒子、属性、ESP与SPID保持不变。构建与验证：`source/tune_collection_emission.py`；基线：`build/before-0.52.2/`。离线验证包含逐块字节保留、DDS检查和168个原生NIF解析；最终效果需在游戏内ENB/光照下复看。

## 0.52.1 其余武器应用已确认四色材质

按已确认的最终方案，将剩余 **148 把**武器统一更新为四色材质：红色 **R5 绯玉霜华**、绿色 **G7 青碧层晶**、蓝色 **B7 海蓝层晶**、紫色 **P3 幻紫欧泊·显色修正**。本次覆盖80把弓、8把异构弩、8把钉锤、12把双手战斧、8把双手战镰、12把长刃匕首、8把双手战锤、12把单手战斧及4把历史材质试作。此前完成的12把巨剑和8把单手剑保持现有效果。

每把剩余武器的主体（以及唯一的折叠主体块）改用当前巨剑的同色漫反射、法线/高光、彩色发光贴图和材质参数；亮边同步同色巨剑参数。紫色沿用0.51.9显色修正：主体1.3、亮边3.6及饱和紫色亮边，避免发白。保留弓弦、弩弦、骨骼、碰撞、动画控制器、粒子、模型UV、属性、名称、ESP与SPID。

相对0.52.0仅更新148个NIF材质块，无新增DDS，仍为168把武器、256个运行文件。构建与验证：`source/apply_approved_collection_materials.py`；基线：`build/before-0.52.1/`。验证覆盖逐块字节保留、贴图路径、粒子数量及148个模型的原生NIF解析；离线验证不能替代游戏内ENB、光照、装填和挥砍测试。MO2安装自动备份。

## 0.52.0 单手剑应用已确认四色材质

下一批选用两组共8把异构单手剑，每色2把，直接沿用0.51.9巨剑已确认的材质与发光参数：红色 **R5 绯玉霜华**、绿色 **G7 青碧层晶**、蓝色 **B7 海蓝层晶**、紫色 **P3 幻紫欧泊·显色修正**。红绿蓝主体倍率1.6，紫色主体1.3；紫色亮边沿用修正版3.6及饱和紫色，避免重新引入旧版发白效果。材质贴图、法线、高光、采样比例与同色巨剑一致。

仅替换8把单手剑的主体/亮边材质块，复用已有DDS；模型造型、UV、碰撞、WeaponSword挂点、原有粒子、名称、属性与编号保持不变。巨剑及其他武器、ESP和SPID不变。无新增运行文件，仍为168把武器、256个运行文件。

已有单手剑直接更新外观。取用整组：`help "AAHeteromorphicSwordsChest" 4` 查CONT编号，再执行 `player.placeatme <完整编号> 1`。构建及验证：`source/apply_approved_sword_materials.py`；实际NIF/DDS离线预览：`art/approved-swords/`；基线：`build/before-0.52.0/`。已包含逐块保留检查与独立原生NIF解析检查；游戏光照、ENB及动画仍需游戏内复看。MO2安装自动备份。

## 0.51.9 紫色巨剑发白修正

根据游戏内反馈，三把紫色巨剑的P3幻紫欧泊加深紫色基底并提高饱和度，保留冰青与珠粉碎片。降低浅色区域发光，主体倍率由1.6调整为1.3，高光强度由0.55降至0.28；独立亮边改为更饱和的紫色，倍率由5.4降至3.6。全表面自发光及原有粒子继续保留。

相对0.51.8仅修改3个紫色巨剑NIF及2个紫色漫反射/发光DDS，无新增运行文件，仍为168把武器、256个运行文件。红色R5及蓝绿材质、造型、UV、碰撞、粒子、属性、ESP及SPID保持不变。构建与验证：`source/refine_purple_opal.py`；预览：`art/purple-opal-refined/`；基线：`build/before-0.51.9/`；MO2安装自动备份。离线验证不能替代用户游戏ENB和光照实测。

## 0.51.8 红紫巨剑 R5 绯玉霜华 / P3 幻紫欧泊

将已选定的 **R5 绯玉霜华** 与 **P3 幻紫欧泊** 应用到三组全部红色、紫色巨剑，共6把。R5为明亮粉红玉质、浅粉云状矿层与少量冰青矿脉；P3为明亮紫色欧泊底材、冰青与珠粉不规则晶片。纹理源图由选定插画生成，再构建1024×1024漫反射、法线/高光与彩色发光DDS，各含11级mipmap。主体继续全表面彩色自发光，倍率1.6；原有独立亮边和粒子保留。

材质采样比例补偿原有平面UV的长宽差异，减少纹理纵向拉伸；模型UV本身不变。蓝绿巨剑及其他武器不变；6把巨剑的造型、碰撞、伤害99、攻速1.2和编号保持不变。ESP、SPID无变化。相对0.51.7仅修改6个NIF并新增6个DDS，168把武器、256个运行文件。

已有红紫巨剑直接更新外观。需要取用时，输入 `help "AAHeteromorphicGreatswordsChest" 4`，查CONT编号后执行 `player.placeatme <完整编号> 1`。构建及验证：`source/build_luminous_greatswords.py`；预览与纹理：`art/luminous-jade-opal/`；修改前基线：`build/before-0.51.8/`。安装自动备份至 `build/mo2-before-0.51.8-*`。

离线模型预览用于检查材质分布，不包含粒子播放，不能代替用户游戏光照和ENB实测。当前是首轮游戏查看版，实际发光、颜色及高光以游戏内为准。

## 0.51.7 红紫巨剑流釉材质

三组共6把红色、紫色巨剑分别换用 **R2赤霞流釉** 与 **P11绯紫流釉**。红色采用 `#F20089 / #FF4D6D / #F9627D`，紫色采用 `#7B2CBF / #F20089 / #E0AAFF`。通过平滑流纹、细层纹、法线与彩色发光贴图表现釉面，主体发光倍率1.6，保留原有独立亮边和粒子。

蓝色B7海蓝层晶、绿色G7青碧层晶保持不变。所有造型、UV、碰撞、伤害99、攻速1.2及编号保留；ESP和SPID无变动。相对0.51.6仅更新6个NIF，新增6个DDS，共168把武器、250个运行文件。

已有红紫巨剑直接更新外观；需要取用时，输入 `help "AAHeteromorphicGreatswordsChest" 4`，查CONT编号后执行 `player.placeatme <完整编号> 1`。构建脚本 `source/build_glazed_greatswords.py`，基线 `build/before-0.51.7/`，安装自动备份至 `build/mo2-before-0.51.7-*`。颜色与亮度需在用户游戏光照及ENB下复测。

## 0.51.6 全部巨剑材质覆盖

三组共12把巨剑统一采用已确认的配色材质：红色黑曜石、绿色G7青碧层晶、蓝色B7海蓝层晶、紫色P8紫斑铜矿。蓝色由贝晶片改成不规则晶层、浅蓝层带，继续使用 `#0077B6 / #00B4D8 / #CAF0F8` 配色和1.6主体发光倍率。绿色沿用G7分层彩色发光；红色、紫色沿用已确认的反射材质。

所有巨剑保留各自造型、UV、碰撞、原有独立亮边和粒子，伤害99、攻速1.2不变。相对0.51.5更新9个NIF，另外3把已是目标材质；新增3个蓝色DDS。其余运行文件和ESP不变，无SPID变化。现有168把武器、244个运行文件。

已有巨剑直接更新外观；整组取用可执行 `help "AAHeteromorphicGreatswordsChest" 4` 查CONT编号，再执行 `player.placeatme <完整编号> 1`。构建/验证脚本为 `source/apply_final_greatsword_materials.py`，基线 `build/before-0.51.6/`，安装自动备份至 `build/mo2-before-0.51.6-*`。离线预览不代表游戏中的ENB及实际光照。

## 0.51.5 B9 蓝辉贝晶 / G7 青碧层晶

- **寒汐·空阙**：B9交叠贝晶片，以 `#0077B6`、`#00B4D8`、`#CAF0F8` 分别表现深层、主体和浅色高光。
- **流萤·掠弧**：G7青色晶层与明亮薄荷层带，使用 `#38A3A5`、`#80ED99`、`#C7F9CC`。

两把巨剑改为分层彩色主体发光贴图，主体倍率1.6，保留原有独立亮边和粒子。贝晶片以贴图和法线表现，不增加模型几何。红色黑曜石、紫色紫斑铜矿及所有属性、编号、碰撞保持不变。168把武器、241个运行文件；更新2个NIF，新增6个DDS，无插件或SPID变动。

已有武器直接显示新外观。也可用 `help "AAHeteromorphicGreatswordsChest" 4` 查CONT完整编号后执行 `player.placeatme <完整编号> 1`，取用上述两把。色值用于纹理配色，最终颜色仍受游戏光照、色调映射及ENB影响。

构建脚本 `source/build_layered_greatswords.py`；基线 `build/before-0.51.5/`，安装备份 `build/mo2-before-0.51.5-*`。模型、纹理和安装离线校验通过后交付，实际游戏效果待测试。

## 0.51.4 深青绿萤石与紫斑铜矿试作

- **流萤·掠弧**：采用G5绿萤石方向，主体加蓝、压深为青绿色，搭配浅色层带和原有薄荷色亮边。
- **梦隙·叠相**：采用P8紫斑铜矿方向，暗紫底色、紫红与少量蓝色斑驳，细颗粒法线和分区反光模拟矿物金属质感。环境反射只近似虹彩，不是真实随视角变化的薄膜干涉。

红色黑曜石和0.51.3偏青蓝的青金石保持不变。只替换两把巨剑主体的材质块，新增6张DDS；造型、UV、碰撞、亮边、粒子、武器属性和ESP保持不变。168把武器、235个运行文件，无新增SPID规则。已有武器直接更新外观，也可通过 `help "AAHeteromorphicGreatswordsChest" 4` 查CONT编号后执行 `player.placeatme <完整编号> 1` 取用。

构建/校验脚本为 `source/build_fluorite_bornite.py`，基线位于 `build/before-0.51.4/`，安装自动备份至 `build/mo2-before-0.51.4-*`。Blender预览用于检查贴图分布，游戏内反光和ENB亮度仍需实测。

## 0.51.3 青金石偏青调色

寒汐·空阙的青金石主体增加绿色分量，由深蓝调向青蓝；保留金斑、浅色矿脉、原有亮边和粒子。只更新该武器主体补光颜色与青金石漫反射贴图。绿色和紫色的新材质仍在概念选择阶段，游戏中暂保留0.51.2效果。更新前基线位于 `build/before-0.51.3/`，MO2安装时自动备份。

## 0.51.2 第三组巨剑矿物材质试作

根据已确认的概念图，为第三组现有巨剑更换主体材质：

| 武器 | 材质 | EditorID |
| --- | --- | --- |
| 余烬·断衡 | 黑曜石，复用已认可的黑曜石试样参数与贴图 | AAgreatsword3red |
| 流萤·掠弧 | 翠玉，绿色云状矿纹与温润反光 | AAgreatsword3green |
| 寒汐·空阙 | 青金石，深蓝底、金斑与浅色矿脉 | AAgreatsword3blue |
| 梦隙·叠相 | 紫龙晶，紫白流纹与细密纤维层次 | AAgreatsword3purple |

保留各自已确认的造型、UV、碰撞、亮边及粒子；伤害99、攻速1.2不变。主体使用不透明环境反射材质，红色主体不自发光，其余三色保留微弱主体补光，轮廓仍由原有独立亮边发光。材质通过贴图和反射模拟，不包含真实透明折射。

已有这四把武器会直接更新外观。也可输入 `help "AAHeteromorphicGreatswordsChest" 4`，查到 CONT 完整编号后执行 `player.placeatme <完整编号> 1`，从巨剑试武箱取用。

本版168把武器、229个运行文件。ESP及其他原有运行文件保持不变；仅更新4个NIF，新增9个DDS，继续复用黑曜石贴图和环境贴图。无需新增SPID规则。构建基线位于 `build/before-0.51.2/`，安装自动备份至 `build/mo2-before-0.51.2-*`。模型与贴图离线检查、Blender材质预览不能替代游戏内ENB和光照测试。

## 0.51.1 移除全部法杖

移除叠炬、回梭、悬阶、折界及法杖试武箱、专属效果、脚本、ArcaneStaves.dll 和 SPID 条目。保留其余 168 把武器、属性和编号。法杖编号 B00–B7F 永久保留，禁止重用。MO2 更新会备份并删除旧法杖文件。

旧存档里的这些法杖将不再可用；请用此前稳定存档复测。下文旧版本法杖内容仅为历史记录，不属于当前版本。

## 0.50.0 第二组异构弩

新增 **余烬·破垒、流萤·回缭、寒汐·叠汐、梦隙·离枢**，攻击力 **95**、攻速参数 **1.4**、重量 14。四种造型分别为厚重三角框架、螺旋卷翼、上下双层弩翼和不对称悬浮分节。沿用低亮度自发光，搭配三角、弯月、矩形和方形粒子。

控制台输入 `help "AAHeteromorphicCrossbowsChest" 4`，查到 CONT 完整编号后执行 `player.placeatme <完整编号> 1`。新生成的箱子包含两组共八把弩和 200 支钢弩箭；总试武箱也包含新增四把。已经生成的旧箱子不保证刷新，请重新生成箱子。

MO2 版本 **0.50.0**，231 个运行文件；保留 ESL 标记、旧编号、0.49.1 法杖修复和此前材质。四条新 SPID 分发规则的概率均为 `0.01`。模型、骨骼、粒子与插件离线检查完成；第一/第三人称装填、射击和实际发光需游戏复测。

## 0.49.1 法杖菜单崩溃修复

修正新增记录的加载顺序：魔法效果先于附魔、附魔先于武器；四把载体设为毁灭学派。对应容器菜单显示法杖、计算消耗时主要效果为空的崩溃。DLL 增加四个附魔和八个法术的加载效果检查与日志。保留全部 FormID、外观及专属法术参数。该修复发布版本为 **0.49.1**；静态验证与编译通过，游戏内菜单及施法需复测。

当前收录 **164 把武器**：8 把异构弩，80 把弓（异构 8、几何律 24、十二星座 48），以及异构巨剑 12 把、异构单手剑 8 把、异构钉锤 8 把、异构双手战斧 12 把、异构双手战镰 8 把、异构长刃匕首 12 把、异构双手战锤 8 把、异构单手战斧 8 把。弓的基础伤害 **90**、攻速参数 **1.5**；巨剑的基础伤害 **99**、攻速参数 **1.2**；单手剑测试版暂用基础伤害 **75**、攻速参数 **1.2**；钉锤基础伤害 **90**、攻速参数 **1.0**；双手战斧、战镰和战锤基础伤害 **99**、攻速参数 **1.2**；长刃匕首基础伤害 **75**、攻速参数 **1.6**；单手战斧基础伤害 **80**、攻速参数 **1.2**。

## 0.49 材质更新回顾

0.51.0 新增两把独立材质测试武器，参考用户提供的红色金属与绿色翡翠晶质插画：

| 武器 | 材质方向 | EditorID |
| --- | --- | --- |
| 余烬·错牙·赤钢试作 | 深红金属、细磨痕、环境反射与微弱红光 | AAwaraxeredmetal |
| 流萤·回翎·翠晶试作 | 翡翠色折面、清晰反光与微弱绿光 | AAwaraxegreenjade |

基础伤害80、攻速1.2、重量12。保留原有几何、亮边及粒子，使用不透明表面和环境贴图模拟质感。主体发光降低以保留暗面，未增加透明折射。原有红绿武器材质不变。

控制台输入 `help "AAMaterialTestChest" 4`，取得CONT完整编号后执行 `player.placeatme <完整编号> 1`。材质箱包含当前错牙、回翎，两把新试作，以及历史磨砂红宝石/黑曜石试样，共6把；新版本名称带“试作”。

172把武器、26个试武箱、239个运行文件。相对0.50仅插件更新，新增2个NIF和6个DDS，原230个非ESP运行文件逐字节一致。模型、贴图、粒子及记录身份检查通过；SSEDump与基线相比没有新增诊断，旧法杖PROJ顺序/NAM1报错仍存在，不能宣称全插件零错误。实际材质和ENB亮度尚待游戏内测试。

当前版本 **0.51.0**，构建基线位于 `build/before-0.51.0/`，安装备份位于 `build/mo2-before-0.51.0-*`。新增两条SPID规则仍为`0.01`。

## 0.50 更新回顾

0.49.0 补齐原有 **156 把正式武器**的四色全身发光材质。本次新增覆盖140把：80把弓、8把单手剑、8把钉锤、12把双手战斧、8把战镰、12把长刃匕首、8把战锤，以及第一组4把单手斧。保留此前12把巨剑和第二组4把单手斧的材质。

| 配色 | 材质 |
| --- | --- |
| 余烬·红色 | 熔光脉络 |
| 流萤·绿色 | 星砂琉璃 |
| 寒汐·冰蓝 | 层叠晶片 |
| 梦隙·紫色 | 云雾光晶 |

整张主体发光贴图都有亮度，保留原有发光倍率、亮边、粒子与数值。弓保留Skinned标志、骨骼权重、动画及纯净弓弦；流萤·折岚的折面同步使用星砂材质，保留其较低发光倍率。几何、UV及碰撞逐块不变。两把历史材质试样、新弩与新法杖保留各自已确认的外观。

已有武器进入游戏即可显示新材质。需要整组取用时，控制台执行 `help "AAAllBowsTestChest" 4`，查询CONT完整编号，再执行 `player.placeatme <完整编号> 1`；总箱现包含本模组全部170把武器。原有各类试武箱也可照常使用。

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
| 异构弩 | 折翼、萦弧、并轨、偏枢、破垒、回缭、叠汐、离枢 | 红、绿、蓝、紫各两把，共 8 把 |
| 异构单手战斧 | 裂冠、萦枝、断湾、缺轮、错牙、回翎、叠潮、折冕 | 8 把原款，另加 4 把材质测试版 |
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
| AAHeteromorphicWaraxesChest | 异构单手战斧·试武箱 | 8 把单手战斧 |
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
