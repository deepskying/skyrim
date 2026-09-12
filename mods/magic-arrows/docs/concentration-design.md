# 持续型箭矢：源码研究与实现边界

## 本机 Marc 附带源码的证据

只读检查 `玩法改进-奥术弓手-Marc🟨/source/scripts/MarcArcaneArrowCast.psc`：
- TryCast 第 26 行按首个效果的 Delivery 分流，没有禁止 Concentration。
- 第 27–32 行把施法对象移到玩家与目标之间靠近目标的位置，并非严格等于命中坐标。
- 第 34–38 行 RemoteCast 的起点是 self，归属为 player，目标是自身或 targetObject。
- 第 40–44 行扣除玩家魔法值、设置冷却、Wait(1.0) 后解除 castLocked；这里没有显式的持续施法终止控制，不能把这个等待值认定为通用施法时长。
- OnLoad 在自身位置 PlaceAtMe 创建 Hazard，完成处理后 Delete 自身。
- `MarcArcaneArrowCastDirect.psc` 对 TargetActor 使用 DoCombatSpellApply。
- `MarcRemoteCaster.psc` 只有脚本声明，没有持续计时实现。
这些是附带源码静态证据，尚未对 PEX 与源码一致性或游戏内的持续表现作验证。本项目没有复制 Marc 脚本或资源进发行包。

## 早期方案（历史记录，当前实现见 0.7.0）

瞬发箭与持续箭分别处理。持续箭命中后保存世界位置、命中法线、入射方向、实际射手及封存参数，建立有期限的临时施法点。
第一阶段建议固定世界位置，朝命中目标或经过碰撞检查的方向释放。对地面命中、墙面命中、目标移动分别测试，避免零向量、穿墙或喷射进碰撞体。喷射型与地面范围型分开适配，不能简单把所有原法术转成范围伤害。
时长可以先以 3 秒作为实验参数；不是当前功能或已确定平衡数值。制作成本应包含完整时段的充能，战斗阶段不再扣射手魔法值。
开始、更新与停止使用可验证的引擎施法生命周期或专用效果适配器，禁止通过每帧重放整条原法术模拟持续伤害。停止后清理音效、粒子、临时引用与关联计时；读档、换场景、施法点卸载也必须处理。
为实际射手归属（含随从）保留有效引用/句柄，不能沿用 Marc 的 Game.GetPlayer()。设置同时存在的施法点数量和总时长上限，数值待实测。
斗篷、自身增益、复活、召唤仍需专门规则；支持持续引导不代表这些自动开放。

## 0.2.2 已实现

候选初筛允许 FireAndForget 和 Concentration，保留 Delivery、所有子效果类型检查和未知效果待适配规则。主法术或任一子效果为 Concentration 时，返回 releaseMode=sustained。网格显示持续型标记，详情写明执行层未实现，参考施法费用不代表完整持续时段费用。确认制作仍禁用。
原生 DLL 编译通过、前端 JS 语法检查通过；浏览器示例检查持续型候选出现及说明正确。游戏内命中持续施放仍未实现或验证。

## 0.7.0 已接入执行层

采用非角色施法器的一次原生调用，由游戏自身负责持续更新。每次命中创建两个带本模组专用基表的临时 XMarkerHeading：施法源沿入射方向退开 12–64 单位，瞄准点位于命中坐标。二者固定在世界中。传实际射手给 CastSpellImmediate 的 blameActor，不改原法术记录，不使用角色的手部施法器，也不反复调用 CastSpellImmediate 或额外手动调用 UpdateImpl。

PlayerCharacter::Update 虚表 0xAD 保留已有回调，追加 3 秒模拟时间计时。暂停不递减，到期、射手无效/死亡、单元卸载或施法器清空原法术时调用 InterruptCast(false)，禁用并删除两引用。最多 16 组，同时第 17 组到来时结束最早一组。队列只留引用句柄，不跨帧保存 MagicCaster 指针。

专用空 FLST 0xE01 保存当前施法源和瞄准点的临时引用；每次变化清空本列表的已添加数组和计数，再添加存活的引用并标记变化。该列表没有插件原始成员，不触及 0xD00–0xDFF 的成品身份。PreLoad 清理旧世界，PostLoad/NewGame 丢弃旧句柄并清理载入列表中的本模组标记。读档不续播短时持续效果。实际 ESS 对动态引用的保存和清理时序尚待实机验收。

### 本机 1.5.97 静态核对

通过本机 Address Library 解码地址，用 capstone 只读反汇编 SkyrimSE.exe；未改动游戏二进制。分析工具及文本输出位于 build，不进入发行包。仅支持已核对的 1.5.97，其他版本不开启钩子。

- TESObjectREFR::GetMagicCaster：ID 19284，0x14028EA00。获取 ExtraMagicCaster，不存在时调用 NonActorMagicCaster 构造函数并挂到引用。
- NonActorMagicCaster::CastSpellImmediate：ID 33900，0x140559D40。保存 blameActor 句柄，调用基类即时施法；对 Aimed＋Concentration 将引用注册到管理器 ID 33906。
- MagicCaster::FindTargets：ID 33632，0x14054CD10。在原法术有效时设置状态 6（Casting）。基类即时施法 ID 33626 先设置 currentSpell 再调用此函数。
- 管理器更新 ID 33910，0x14055A320。解析登记的引用、读取已有 ExtraMagicCaster、调用 MagicCaster::UpdateImpl ID 33622；后者维护持续施法的 projectileTimer。插件不重复执行该更新。
- InterruptCast ID 33630 调用 FinishCast ID 33657，后者结束关联持续投射物并清空 currentSpell 和状态。插件随后禁用/删除标记；视觉淡出仍由引擎处理。
- 本地头文件对 NonActorMagicCaster 的 GetCasterStatsObject/GetCasterAsActor 注释不准确：实际虚表槽 0x0B 返回源引用，0x0C 解析 blameActor 句柄。以上归属设计依据实际函数与参数，不依赖“return 0”的头文件注释。

这些证据确认所调用接口的路径，不能证明场景碰撞、伤害、保存时序或第三方脚本已经游戏验证。

### 准入与测试

持续箭支持普通 Aimed＋Concentration 法术，主投射物为喷射、锥形或光束；每个效果检查施法方式与原型。原版 Flames、Frostbite、Sparks 的磁盘记录结构符合这一范围；仍以游戏当前覆盖后的记录作最终判断。无条件独立多投射物、斗篷、自身、召唤、复活等继续排除；条件附加效果的完整行为需实测。

当前时长固定 3 秒，制作时先把参考施法费用乘 3，再应用已有金币、魔法值和充能公式及上限。成品名标记“持续3秒封存”，装备卡片和制作页均显示时长。

已通过原生构建、模拟时间/暂停/精确到期/长帧/无效上下文/上限/三秒费用测试，以及浏览器模拟报价制作流程。真实伤害、原施法终止后音效和粒子、连续命中、墙面/地面方向、随从归属、保存后重新载入不留幽灵施法点仍未验收。
