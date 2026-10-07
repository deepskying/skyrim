# 神之血 · Divine Blood 1.0.0

从 MO2 的「玩法改进-神血-The Stones of Divines-🟩🟨-打怪掉落」迁入。保留 `The Blood of Divines.esp`、原有 15 种物品及效果的 FormID / EditorID，补齐 `0xD7B` 阿卡托什之血。旧存档已获得的属性不回退；更新后生命、魔力、体力及负重每份永久增加 **1**。其他效果维持原增量；龙吼冷却倍率每份减少 0.0001，并限制最低为零。

16 种神血分别使用新建实体模型，包含碰撞、物品栏标记和独立轮廓；工坊卡片图来自实际导出的 NIF。概念图位于 `art/concepts/divine-blood-v1.png`，实际模型总览位于 `art/models/overview.png`。

## 炼制规则

装备工坊 2.4.1 的一级菜单「神之血」选择物品，下方显示共享灵魂池与临时炼金池。必须靠近已加载、启用的炼金台，距离规则与工坊其他设施一致。

- 炼金池容量始终等于灵魂池容量，扩容自动同步。
- 选择对应功效的炼金材料只计算点数。切换神血、离开页面或关闭工坊清空选择，不扣材料。
- 初始每份需要 10 点灵魂、10 点炼金；每个适用材料提供 1 点。数量自动取两池各自可支付份数的较小值。
- 成功炼制消耗全部所选材料，炼金余量舍弃；灵魂只扣成品实际费用。面板提前列出本次消耗及舍弃点数。
- 缺资源、费用或库存变化、任务保护、请求重复、成品入包失败均取消；交易失败回补已扣材料。
- 每实际吸收同类神血 10 份，基础费用增长 10%，分别向上取整。制作与拾取不增加计数；计数随 SKSE 附属存档保存，旧档从更新后计数。

`data/SKSE/Plugins/DivineBlood.ini` 按神血 key 配置 `SoulCost`、`AlchemyCost`、`PointsPerIngredient`，重启游戏后加载。材料适配依据非负面效果的 ActorValue，独立于炼金技能与药效强度。龙吼接受龙吼冷却 / 魔力恢复，移速接受移速 / 体力，护甲接受护甲 / 格挡材料；其他对应目标属性或恢复倍率。

## 分发和安装

`DivineBlood_DISTR.ini` 单独保存原有 16 条 SPID 规则（泽尼萨尔 10%，其他 5%）。启用此文件前必须移除混合 `-important_DISTR.ini` 中同名神血规则，避免重复分发；其他规则保留。安装脚本先备份旧神血目录、工坊目录及混合 SPID 文件，再精确迁移神血规则。

神血包独立于工坊包；仅安装神血包仍可使用 / 掉落物品，工坊菜单与炼制需要 EquipmentWorkshop 2.4.0 和启用灵魂池。安装脚本已直接更新原 MO2 神血目录；该条目现在承载新版 ESP、模型、脚本和分发文件，不能删除或禁用。可修改 MO2 显示名称。若手动将新版独立包装入另一目录，必须先启用新条目并确认仅有一份同名 ESP，再移除旧条目，保持原插件位置。

## 构建与验证

依次运行 `source/import_build.py`、`source/build_script.py`、`source/build_models.py`；使用项目 Blender 后台运行 `source/render_models.py`，再运行 `source/verify.py` 和 `source/package.py`。沿用仓库 Nifly / Blender 工具及魔法箭几何工具；Papyrus 使用官方 [Caprica 0.3.0](https://github.com/Orvid/Caprica/releases/tag/v0.3.0) 的 Skyrim 后端，位于被忽略的 `reference/caprica/Caprica.exe`。导入签名仅在构建目录中补充 SKSE `Form.SendModEvent`，不向游戏分发替换 Form 脚本。

原始插件、PSC、PEX 及网格保存在 `source/upstream`；大型原始纹理本地保留并被 Git 忽略，新模型不依赖它们。原文件大小和 SHA256 见 `source/upstream-manifest.json`。

验证包括原记录非目标字段保持、16 种模型 / 图标及碰撞、PEX 魔数和回调、16 条独立分发规则，以及原生最大产量 / 费用边界测试、工坊前端测试和构建。实际游戏中的服用、存读档、炼制事务和掉落仍需实机验收。
