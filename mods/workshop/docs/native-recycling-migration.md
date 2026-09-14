# 从简单回收迁移到工坊原生回收

1.6.0 的回收不再需要 SimpleRecycling.esp、Papyrus 回收脚本或旧 MCM。新安装只保留 DurabilityManager.esp 和 MagicArrows.esp，回收代码完全在 EquipmentWorkshop.dll 中。

迁移需退出游戏与 MO2，备份工坊目录、旧简单回收目录、modlist/plugins/loadorder 及旧存档。升级界面和 DLL，加入工坊自己的两份 recycling JSON，按 `packaging/retired-recycling-files.json` 移除旧工坊中的回收资产，再从配置中移除旧模组与 SimpleRecycling.esp。其他 ESP 排序保持原有相对顺序。安装前应检查当前启用插件的 TES4/MAST，若其他插件依赖 SimpleRecycling.esp，需先处理依赖。

旧存档可能保留简单回收的任务、脚本实例和 MCM 历史项。移除磁盘文件不等于清理了这些存档记录。首次加载可能出现缺少内容提示；先使用旧档副本验证，成功后另存新档，不覆盖唯一的原档。不要为了隐藏提示修改 ESP 名称或把不相关的新 ESP 冒充旧插件，也不要批量删除未知存档脚本。

进入游戏后的验收：

- 工坊显示 1.6.0，通用设置可录入回收键、切换启用与长按整组；退出游戏重进仍保留设置。
- SkyUI 选中普通武器、箭矢、药水、书籍与杂物，验证移除数量、材料到账和菜单刷新。
- 任务、神器、已装备、收藏物品不可回收；同名实例无法明确定位时显示拒绝原因。
- 按住回收键时切换选项、搜索、关闭背包、打开工坊或读档，不得误回收。
- 新存档再次加载后检查原有耐久、强化和魔法箭队列。确认旧 MCM 项不再可执行；如有残留，保留日志和存档副本另行诊断。

开发机已能验证编译、数量规则、按键解析、打包依赖与配置文件。没有游戏内验收结果时，不宣称旧存档已经清理干净，也不宣称所有 SkyUI 改版均已兼容。

选择索引对应关系参考 [SkyUI BasicList 源码](https://github.com/schlangster/skyui/blob/master/src/Common/skyui/components/list/BasicList.as)；原生端仍与菜单条目 FormID 交叉核验，避免只凭显示顺序删除。
