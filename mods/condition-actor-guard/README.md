# Condition Actor Guard（条件函数空 Actor 防护）

针对 Skyrim SE **1.5.97** 的实验性 SKSE 原生插件。防止「只有 Actor 才有意义」的条件函数在**非 Actor 目标**上被求值时解引用空指针而崩溃。

## 来源与范围

2026-09-28 20:40 的崩溃日志（`涅菲` 在沃尔基哈城堡外战斗）确认了这条路径：

- 崩溃指令为 `mov r9, [rbx+0x38]`，`rbx = 0`，读取地址 `0x38`。
- 该指令位于 `SkyrimSE.exe+0x608AF0`，它把第一个参数当作 `Actor` 使用，**没有空指针判断**。
- 调用者是条件函数表第 **569** 号 `IsBlocking` 的处理器 `SkyrimSE.exe+0x2DB880`：它先做 `cmp byte [rcx+0x1a], 0x3E`（`TESForm::formType` 是否为 Actor），不是 Actor 时把空指针原样传下去。
- 现场对象是 Darkstorm.esp 的 `_VBM_VoidClawsStagger`（"马尔卡斯的三条纹"，0x7B00081E），它**唯一**的条件就是 `IsBlocking == 0`；同一条记录里的锥形投射物 `_VBM_VoidClawsProjL` 命中了非 Actor 的容器「棺材」（Dawnguard.esm 0x000EB093）。

即：BOSS 的锥形法术把带 `IsBlocking` 条件的 Stagger 效果套到棺材上，引擎在棺材上求值 `IsBlocking` 时空指针崩溃。原版 Skyrim.esm 没有 `IsBlocking` 条件，所以这条路径平时不会暴露；但当前加载顺序里有 38 条 MGEF 带该条件（含 `Dragonborn.esm` 的 `DLC2dunKarstaagKnockbackEffect`、`EldenSkyrim.esp`、`MarshLeviathans.esp`、`Feathered Tyrannosaurids.esp`、`Natura.esp` 等）。

插件只改写**条件函数表里的处理器指针**，不写代码字节、不改动任何记录、不接触存档。

## 防护范围

下表每个处理器都有一段同样的缺陷：把 `formType == 0x3E` 判定后的 Actor 指针（可能是空）直接交给只接受 Actor 的代码。RVA 与索引均按 1.5.97 二进制核对过，运行时不匹配就拒绝替换并写日志。

| 索引 | 条件函数 | 处理器 RVA | 非 Actor 目标上的表现 |
| --- | --- | --- | --- |
| 0 | `GetWantBlocking` | `0x2DB780` | `mov eax, [rbp+0xc4]` 空指针读 |
| 286 | `IsSneaking` | `0x2DB520` | `lea rcx, [rdi+0xb8]` 后调用，空指针读 |
| 287 | `IsRunning` | `0x2DB610` | `mov rcx, rdi` 后调用，空指针读 |
| 568 | `IsSprinting` | `0x2DB6C0` | `lea rcx, [rdi+0xb8]` 后调用，空指针读 |
| 569 | `IsBlocking` | `0x2DB880` | `mov rcx, rbp` 后调用 `0x608AF0`，本次崩溃 |
| 676 | `GetCurrentShoutVariation` | `0x2DEF90` | `mov rcx, [rsi+0xf0]` 空指针读 |

## 行为

- **目标是 Actor**：完全走原函数，行为与未安装时逐字节一致。
- **目标不是 Actor（容器、投射物、杂物等）或为空**：插件先把结果值写成 `0.0`，再让条件函数返回 `false`。引擎把 `false` 解释为「该条件无法对当前目标求值」，于是条件判定为**不成立**，效果不会被加到非 Actor 上，也就不会再走到空指针。
- 这是一条**策略**而非还原原意：`IsBlocking`/`IsSneaking` 之类在容器上没有语义，判定为「不成立」比「假装的 0 值」更安全——后者会让 `IsBlocking == 0` 这类条件在棺材上成立，效果照样会被套上去。
- 代价是：对非 Actor 目标，这些条件不再有任何「值」。就本次崩溃而言，BOSS 爪击不会再把眩晕效果加到棺材上。Actor 之间的判定不受影响。

## 安装与撤销

需要 Skyrim SE 1.5.97、对应 SKSE64；当前工程使用 CommonLibSSE-NG。无需 PrismaUI。只支持 1.5.97，不能用于 AE/VR。

1. 完全退出游戏。
2. 用 MO2 从 `ConditionActorGuard-0.1.0.zip` 安装，并勾选独立模组（放在加载顺序任意位置即可，它不改记录）。
3. 通过 SKSE 启动游戏。
4. 检查 `Documents/My Games/Skyrim Special Edition/SKSE/ConditionActorGuard.log` 中的 `installed` 与各条 `guarded handler` 行。

撤销：退出游戏后取消勾选该模组。不需要存档清理。

## 验证

先在棺材旁复现原崩溃（沃尔基哈城堡外，让 BOSS 放黑暗风暴的爪击法术）。拦截发生时日志会出现 `guarded N non-actor evaluation(s)`；计数为 0 表示这次没有触发该路径，不能说明问题不存在。

日志中每个条件函数一条 `guarded handler`。若某条变成 `expected handler ... found ...`，说明二进制或已有钩子与预期不符，该条被跳过而未替换。

## 实现与兼容

- 引擎每次求值都从条件函数表读取处理器指针（`SkyrimSE.exe+0x445B2F`），因此只替换指针即可，函数体一个字节都不动。
- 表项布局：`基址 + 0x1DB8930 + 0x50 * 索引`，处理器指针在 `+0x20`。替换前逐项核对原指针等于表中的 RVA，不匹配就保留原样。
- 钩子本身只做一次 `formType` 读取和一个原子计数，不写日志、不分配内存、不调用游戏函数。
- 只在 1.5.97 上安装；不匹配则拒绝加载。同一表项若已被其他插件替换，本插件不会覆盖它。
- 计数由独立线程每 2 秒检查一次，仅在发生变化时写日志；读档前后各汇报一次累计值。

## 限制

- 这是崩溃防护，不是数据修复：Darkstorm.esp 的 `_VBM_VoidClawsStagger` 仍然带着那条 `IsBlocking` 条件，只是不再在非 Actor 上求值。
- 仅覆盖上表六个已知处理器。其他插件若新增同类条件函数，需要重新核对表项后再扩展。
- 不处理多对象循环、无效指针或其他求值路径。

## 构建与测试

在 `native` 目录运行 `xmake f -y -m release`，然后 `xmake build -y ConditionActorGuard`。依赖沿用仓库 `reference/example-skse-plugin/lib/commonlibsse-ng`。

运行 `xmake build -y GuardCodeTests` 和 `xmake run GuardCodeTests`。测试直接执行生产代码导出的钩子：非 Actor 与空目标被短路、结果值与参数原样传递、Actor 走原函数、每个槽位各自计数。编译及离线测试不能替代游戏内回归。

安装包由 `packaging/package.ps1` 生成。
