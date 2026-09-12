# Marc 施放机制对照（0.9.5）

检查对象为用户安装目录中的 Marc.esp 配套 source/scripts。只读取参考文件，未复制或修改 Marc 文件。

- MarcArcaneBinding.psc:33–60：取玩家已装备法术，按学派/关键词分配槽位，不限制在少数效果 archetype 中。
- MarcArcaneArrowCast.psc:26–38：第一项效果 delivery 非 3 时，由命中处临时参考对象 RemoteCast 完整 Spell；delivery 0 使用自身参考点，否则使用落点对象。
- MarcArcaneArrowCastDirect.psc:15–18：delivery 3 单独调用玩家的 DoCombatSpellApply，目标为命中角色。
- Marc 会支付施法法力并设置冷却；本项目仍在制作时支付成本，执行时用实际射手归属，不要求附魔弓。

## 本项目的差异与修订

0.9.4 瞬发路径是 Projectile::Launch，仅取主投射物；过滤器为此拒绝了 Script、Rally、多种无条件投射物和 Missile/Beam 以外的投射物，且只接受 aimed。这些限制不是 Marc 的兼容机制。

0.9.5 统一调用落点参考对象的 NonActorMagicCaster::CastSpellImmediate，原始 SpellItem 完整保留，传入实际射手作为 blameActor；不改全局 MGEF、投射物、法术的 casting/delivery。持续施法仍由原生更新一次启动的 caster，不按帧重复施法。锁定目标/接触使用捕获的命中 Actor；本项目用原生 caster 已设置的 target handle，不调用 Marc 的 Papyrus DoCombatSpellApply。当地 1.5.97 FindTargets (Address Library 33632) 的 delivery 3 分支读取 caster +0x20 目标句柄（build/caster-targets.asm.txt），能使用已设置目标。此代码路径检查不代替游戏测试。

分类取决于施放行为而非毁灭学派：

| 路线 | 接受条件 | 命中行为 |
|---|---|---|
| aimed | 有 Missile/Grenade/Beam/Flamethrower/Cone/Barrier 魔法投射物 | 从落点前方朝落点施放完整法术 |
| actor | 敌对接触/锁定角色 | 仅命中存活角色时施放；射地面不触发 |
| location | 地点法术，含敌对效果或魔法投射物 | 临时目标设为落点，放置条件仍由引擎决定 |
| area | 敌对、瞬发、自身范围，且有有效非 NoArea 的范围 | 以落点为中心施放 |

无条件拒绝未知/缺失/异常数据及超过 128 项效果的法术。暂不设计治疗箭、召唤箭、斗篷载体、变身、念动、绑定装备。脚本不再按来源插件白名单拦截；是否要求特定施法状态等行为仍取决于原脚本。

## 生命周期与验证边界

持续 caster 最多 16 个，保持 3 秒；瞬发辅助参考最多 32 对，保存 1 秒后清理，二者分别淘汰最早项。仅清理本模组 E00 标记物；目标 Actor 从不删除。FLST E01 记录临时对象用于保存/读档清理；读档终止未完成施放。16/32 上限不会相互挤掉另一类型。

保留所有 ESP FormID 和法术＋基材绑定，旧成品在读档时依照新规则恢复。新增规则测试涵盖脚本、多投射物、六种投射物、瞬发/持续锁定目标、落点范围、治疗/斗篷/召唤排除和异常输入。结构可制作不等于第三方效果已经实测；不承诺全部 100 多个法术都能转为攻击箭。
