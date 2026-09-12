# Peak Effect Loop Guard（效果自环防卡死）

针对 Skyrim SE **1.5.97** 的实验性 SKSE 原生插件。防止 `PeakValueModifierEffect::next` 指向自身时，一处效果遍历无限循环，导致死亡后重新读档黑屏。

## 来源与范围

2026-09-12 的现场转储确认：工作线程反复执行 `SkyrimSE.exe+0x55B0B7`，对象 `0x1ca77c0c2c0` 的 `next` 仍为自身。RTTI 为 `PeakValueModifierEffect`，关联 MysticismMagic.esp 的 `MAG_abFrostSlow` / `MAG_abFrostSlowEffect25`（寒霜缓速 / 降低速度）。这证明了本次循环机制，没有证明是谁创建自环。

插件对这一引擎遍历点生效，不限定 Mysticism 或某个加载序号。正常链和空链尾保持原行为；遇到直接自环时，只让本次遍历结束。保留原来的效果链指针、引用计数及法术，不写存档、不带 ESP、不移除减速。

**这是防挂起措施，不是效果状态修复。** 异常效果可能仍然存在或表现异常，未来可能再次拦截。它不解决多对象环（A→B→A）、无效指针、其他遍历点、下午出现的渲染卡死或所有黑屏问题。

## 安装与撤销

需要 Skyrim SE 1.5.97、对应 SKSE64；当前工程使用 CommonLibSSE-NG。无需 PrismaUI。只支持 1.5.97，不能用于 AE/VR。

1. 完全退出游戏。
2. 用 MO2 从 `PeakEffectLoopGuard-0.1.0.zip` 安装，并勾选独立模组。
3. 通过 SKSE 启动游戏。
4. 检查 `Documents/My Games/Skyrim Special Edition/SKSE/PeakEffectLoopGuard.log` 中的 `installed`。

撤销：退出游戏后取消勾选该模组。无需存档清理。不要把 DLL 注入已经卡住的进程。

## 验证

先保留原存档副本。在保持其他模组不变的情况下，重复原来的「读档 → 死亡 → 重新读档」步骤。日志出现 `Stopped ... direct self-loop traversals` 表示实际拦截到了自环；成功进入游戏后还应检查减速是否能正常消退。没有触发计数的一次成功，不能证明这个偶发问题已修复。

若黑屏仍发生，保留进程和本插件日志，再采集转储。计数大于零但仍卡死，也可能说明还有其他循环或问题。

## 实现与兼容

- 启动时校验运行时版本和连续12字节指令；不匹配则拒绝安装补丁并记录日志，避免覆盖已存在的同位置钩子。
- 只替换7字节 `mov rax,[rax+98h]`，保留原来的 `test/jne`。
- 正常路径增加自环比较；自环路径将遍历寄存器置零，而非改写对象。
- 保存并恢复 RDX，不调用游戏函数或分配内存。原 `TEST` 恢复后续分支所需标志位。
- 原子计数，独立报告线程每2秒检查计数变化，仅发生拦截时写日志。报告线程不读取游戏对象。
- 同一位置被其他插件后来覆盖仍可能使防护失效，需通过实际日志和转储验证。

## 构建与测试

在 `native` 目录运行 `xmake f -y -m release`，然后 `xmake build -y PeakEffectLoopGuard`。依赖沿用仓库 `reference/example-skse-plugin/lib/commonlibsse-ng`。

运行 `xmake build -y GuardCodeTests` 和 `xmake run GuardCodeTests`。测试直接执行生产代码生成器生成的x64机器码，覆盖正常/空链尾/自环、RDX与ZF、原始循环回跳、逐节点标志位、链不被修改及8线程共80000次并发计数。

安装包由 `packaging/package.ps1` 生成。编译及离线测试不能替代游戏内回归；初版交付时尚未验证真实死亡读档。
