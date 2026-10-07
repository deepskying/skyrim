# 神之血 · Divine Blood 1.0.1

从 MO2 的「玩法改进-神血-The Stones of Divines-🟩🟨-打怪掉落」迁入。保留 `The Blood of Divines.esp`、原有 15 种物品及效果的 FormID / EditorID，补齐 `0xD7B` 阿卡托什之血。旧存档已获得的属性不回退；更新后生命、魔力、体力及负重每份永久增加 **5**。其他效果维持原增量；龙吼冷却倍率每份减少 0.0001，并限制最低为零。

16 种神血分别使用新建实体模型，包含碰撞、物品栏标记和独立轮廓；工坊卡片图来自实际导出的 NIF。概念图位于 `art/concepts/divine-blood-v1.png`，实际模型总览位于 `art/models/overview.png`。

## 炼制规则

装备工坊 2.4.1 的一级菜单「神之血」选择物品，下方显示共享灵魂池与临时炼金池。必须靠近已加载、启用的炼金台，距离规则与工坊其他设施一致。

- 炼金池容量始终等于灵魂池容量，扩容自动同步。
- 选择对应功效的炼金材料只计算点数。切换神血、离开页面或关闭工坊清空选择，不扣材料。
- 初始每份需要 10 点灵魂、10 点炼金；每个材料按最强对应效果计算点数：`ceil(强度 × sqrt(clamp(持续秒数 / 30, 1, 4)) × PointsPerIngredient)`，即时效果按 1 倍，持续时间最多提供 2 倍加成；无强度效果按 1 点基础值，零强度、负强度及非有限数值不参与。数量自动取两池各自可支付份数的较小值。
- 成功炼制消耗全部所选材料，炼金余量舍弃；灵魂只扣成品实际费用。面板提前列出本次消耗及舍弃点数。
- 缺资源、费用或库存变化、任务保护、请求重复、成品入包失败均取消；交易失败回补已扣材料。
- 每实际吸收同类神血 10 份，基础费用增长 10%，分别向上取整。制作与拾取不增加计数；计数随 SKSE 附属存档保存，旧档从更新后计数。

`data/SKSE/Plugins/DivineBlood.ini` 按神血 key 配置 `SoulCost`、`AlchemyCost`、`PointsPerIngredient`（点数倍率，默认 1），重启游戏后加载。材料适配依据非负面效果的 ActorValue；只取对应效果的最大点数，不累加无关功效。点数读取材料当前效果强度与持续时间，不受玩家炼金技能或装备加成影响。提交炼制时重新校验每份材料点数，变化时取消而不扣资源。龙吼接受龙吼冷却 / 魔力恢复，移速接受移速 / 体力，护甲接受护甲 / 格挡材料；其他对应目标属性或恢复倍率。

## 分发和安装

`DivineBlood_DISTR.ini` 单独保存原有 16 条 SPID 规则（泽尼萨尔 10%，其他 5%）。启用此文件前必须移除混合 `-important_DISTR.ini` 中同名神血规则，避免重复分发；其他规则保留。安装脚本先备份旧神血目录、工坊目录及混合 SPID 文件，再精确迁移神血规则。

装备工坊 2.4.2 已包含全部神血资源，只需一个工坊 MO2 条目。神血源码仍作为独立项目维护，插件名称和物品 ID 保留。安装脚本会保留配置、备份旧目录及 MO2 配置，验证后将旧神血目录移至游戏目录下的 mod-backups，保持原插件加载顺序。独立神血包仅供单独使用，不与统一工坊同时启用。

## 构建与验证

依次运行 `source/import_build.py`、`source/build_script.py`、`source/build_models.py`；使用项目 Blender 后台运行 `source/render_models.py`，再运行 `source/verify.py` 和 `source/package.py`。沿用仓库 Nifly / Blender 工具及魔法箭几何工具；Papyrus 使用官方 [Caprica 0.3.0](https://github.com/Orvid/Caprica/releases/tag/v0.3.0) 的 Skyrim 后端，位于被忽略的 `reference/caprica/Caprica.exe`。导入签名仅在构建目录中补充 SKSE `Form.SendModEvent`，不向游戏分发替换 Form 脚本。

原始插件、PSC、PEX 及网格保存在 `source/upstream`；大型原始纹理本地保留并被 Git 忽略，新模型不依赖它们。原文件大小和 SHA256 见 `source/upstream-manifest.json`。

验证包括原记录非目标字段保持、16 种模型 / 图标及碰撞、PEX 魔数和回调、16 条独立分发规则，以及原生最大产量 / 费用边界测试、工坊前端测试和构建。实际游戏中的服用、存读档、炼制事务和掉落仍需实机验收。
