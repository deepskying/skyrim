# 下一代 UI 平台评估与架构规划（2026-09-25）

面向"用自有物品清单替换 SkyUI"这个长期工程，本文回答三件事：
MeridianUI 的架构是否合理、要不要独立设计、如果要独立设计该怎么做。

---

## 0. 结论摘要

1. **MeridianUI 的架构是合理的**，而且是这套生态里少有的"真把硬问题解过一遍"的实现：
   离屏浏览器 + 三种传输回退 + 全局焦点仲裁 + `mod://` 资源托管 + 钩子级生命周期 + NIF 预览 + 60 个测试。
2. **现在不建议推倒重写**。你要撞的坑基本都在它已经趟过的 2.4 万行里；我们刚亲历的一个例子——
   "共享纹理不可用"这一处兜底缺失，就花了一轮日志定位 + 一次源码补丁 + 一次游戏内验证。
3. **该独立设计的是上层**：数据模型、交互、设计系统、桥接协议、模块化与测试——这些才是"自己的物品清单"的资产；
   下层先用 Meridian 当"窗口系统"，但**必须通过你自己的 adapter 隔离**，让将来替换下层只改一层。
4. **真正要自研下层只有 4 个触发条件**（见 §5），任一成立再启动，且先用 §9 的垂直切片验证，而不是直接重写。
5. **许可不是主要掣肘**：消费它的 API（MIT 头文件 + 运行期加载）你的模组可以自选许可；
   只有"fork 实现并分发"才受 GPL-3 约束（需连带源码）——我们这次处理 Meridian 补丁的方式就是按这条边界做的。

---

## 1. 事实基线（全部来自本机代码与运行日志）

| 项目 | 数值 |
| --- | --- |
| 源码规模 | `src` 共 209 个 cpp/h，约 **24.3k 行**；`UIPlatform` 独占 175 文件 / **20.0k 行** |
| 主要模块（行数） | Render 6,869（50 文件）、Controllers 2,916、CEF 2,010、Menus 1,630、Services 1,522、MeridianUIAPI 1,382、JS 499、Hooks 431、Input 433、Scheme 462、Config 331 |
| 测试 | `tests/` 下 **60 个 C++ 测试文件** + CTest 门禁 + 运行期 gate 文档 |
| 发布体积 | `dist\Release\Data` **399.7 MB**（其中 `libcef.dll` 285 MB） |
| 浏览器内核 | CEF 152.0.6（`cef-prebuilt` port）+ 独立子进程 `MeridianCEFSubprocess.exe` |
| 公开 API | 18 个头文件，**MIT**，扩展独立版本：View/1、RenderLayer/1、NifView/1、NifScene/1–4、Input/1 |
| 加载方式 | 运行期 `GetModuleHandleW("MeridianUI.dll")` + `QueryMeridianExtension`，消费者**不静态链接** |
| 许可 | 实现 = **GPL-3.0-or-later + Modding/Linking 例外**；API 头 = MIT；CEF = BSD 系 |
| 构建 | vcpkg + CMake presets，本机首次配置+编译约 10 分钟（含 CEF 下载） |
| 本机实测 | 浏览器层探测失败自动降级 SyncCopy ✅；NIF 预览因缺少同类兜底失败 ❌（已补丁修复） |

### 1.1 分层结构（读代码得到的实际分层）

```
UIPlugin (208 行)          SKSE 入口：SKSEPlugin_Load → 加载 UIPlatform
└─ UIPlatform (20.0k 行)
   ├─ Hooks        Present / 输入分发 / 关机 / 光标菜单钩子
   ├─ Menus        菜单集成、焦点菜单、光标
   ├─ Render       合成器、浏览器传输(RingBuffer/SyncCopy/CpuUpload)、NIF 渲染器、NIF 提取、纹理加载
   ├─ CEF          浏览器宿主、客户端、离屏渲染
   ├─ Controllers  各扩展 API 的实现(View/RenderLayer/NifView/NifScene/Input)
   ├─ Services     CEF 服务、输入服务、手柄、语言切换
   ├─ Scheme       mod:// 资源协议（固定主机 + 路径穿越拒绝）
   ├─ Config       MeridianUI.ini 覆盖
   └─ MeridianUIAPI 对外 MIT 头文件（扩展 API 的稳定面）
```

---

## 2. 架构评估：合理的地方

1. **扩展 API 是"进程内微内核"模型**：18 个 MIT 头 + 运行期 Query 加载 + 每个扩展独立版本号 +
   `structSize` 前向兼容规则（平台按 `min(caller, own)` 拷贝并补默认值）。
   结果：平台升级不需要消费者重新编译，消费者也不需要链接 GPL 实现。这个设计比多数 SKSE UI 插件干净。
2. **关注点分离到位**：渲染、浏览器、菜单、钩子、协议、配置各成目录，
   `Render` 独占 1/3 代码量也符合"难的地方在渲染"这个事实。
3. **焦点与输入是被认真处理过的**：全局唯一焦点持有者、输入吞掉避免游戏同时响应、
   Alt-Tab 时清理修饰键、释放焦点恢复原版光标（CHANGELOG 1.2.0/1.2.1 记录了对 flicker、elevated MO2 等真实问题的修复）。
4. **传输层有抽象且有回退**：RingBuffer（共享键控纹理）/ SyncCopy / CpuUpload，
   浏览器层会在探测失败时自动降级（本机日志实测：`RingBuffer ... unsupported ... SyncCopy fallback enabled`）。
5. **资源托管有安全模型**：`mod://<mod>/<path>` 固定主机、拒绝远程/`file://`/跨模组/穿越，404 节流。
6. **测试与运行期 gate 分离**：60 个测试 + `docs/testing/*_RUNTIME_GATE.md` 明确区分
   "自动化通过"与"真机通过"，这一点比大多数个人模组专业。
7. **子进程隔离 CEF**：崩溃面被限制在 `MeridianCEFSubprocess.exe`，主进程可回收。

---

## 3. 架构评估：风险与掣肘

| # | 风险 | 证据 / 说明 | 影响 |
| --- | --- | --- | --- |
| R1 | **它是"被钩住的 overlay"，不是库** | Hooks+Menus+Input 约 2.5k 行，钩 Present/输入/关机 | 任何 D3D11 注入层（ENB、上采样、overlay）都可能冲突 |
| R2 | **能力探测与回退不是全局一致的** | 浏览器层用 `SupportsSharedKeyedTransport()` 降级，NIF 层没有 → 本机 0 shapes 全失败 | 同类疏漏会周期性出现，需要你自己兜住 |
| R3 | 发布体积 400 MB | `libcef.dll` 285 MB | 包体/更新成本；Nexus 分发不友好 |
| R4 | 单作者 + GPL-3 实现 | `LICENSING.md` / `EXCEPTIONS.md` | 上游节奏不可控；fork 分发需连带源码 |
| R5 | **前端层几乎为零** | `src/UIPlatform/Web` 仅 499 行 bridge 辅助，无组件库/状态/路由 | 工程质量完全由你负责（同时也是自由） |
| R6 | 多 UI 平台共存 | 生态里还有 PrismaUI、SkyUI(SWF)，焦点/输入需跨框架守卫 | 过渡期复杂度高 |
| R7 | 版本/运行期耦合 | CommonLibSSE-NG 绑定，SE 1.5.97 / AE 1.6.1170 已验证，VR 不支持 | 换运行时要等上游或自己补 |

---

## 4. 许可的真实边界（"掣肘"到底有多大）

- **消费 API**：只用 `MeridianUIAPI/*.h`（MIT）+ 运行期 `QueryMeridianExtension` 加载，
  不链接、不复制实现代码 → 你的模组**可以自选许可**（现状：随从管理 / 物品清单都是这么做的）。
- **修改实现并分发**：例如我们这次的 NIF 兜底补丁，产出的是"修改后的 MeridianUI.dll"，
  该 DLL 受 GPL-3 约束，分发时必须提供对应源码。
  **我们的处理方式**：补丁留在独立分支/仓库（`codex/game-device-nif-fallback`），
  归档补丁文件 + 二进制，不把它混进你的模组仓库；要发布就发布那个分支。
- `EXCEPTIONS.md` 里的 Modding Exception 是给"Meridian 与 Skyrim/SKSE/驱动链接"用的，
  **不覆盖"你的模组与 Meridian 实现链接"**——但因为走的是 API 边界，你本来也不需要那条例外。
- 结论：GPL **不阻止**你把物品清单做成自己的闭源/自选许可模组；它只要求"改过的平台 DLL"开源。

---

## 5. 要不要独立设计：分层归属 + 触发条件

把问题从"要不要重写 Meridian"换成"哪一层是资产、哪一层是商品"：

| 层 | 归属 | 说明 |
| --- | --- | --- |
| 数据模型 / 交互 / 视觉 / 中文体验 / 排序搜索 / 性能策略 | **你的资产** | 全部自己设计，独立于平台 |
| 桥接协议 / 前端框架 / 组件库 / 测试体系 | **你的资产** | 现在几乎是空白，最值得投入 |
| 表面与传输 / 输入与焦点 / 生命周期 / 资源托管 / NIF 渲染 | **商品（先用 Meridian）** | 自己写要重踩全部坑 |

**自研下层的 4 个触发条件**（任一成立再启动，且先做 §9 的垂直切片）：

1. 上游停止维护或拒绝必要修复，而你遇到无法绕过的阻塞；
2. 你需要它结构上不支持的能力（多窗口、屏幕空间特效、视频、复杂动画、非 CEF 渲染后端）；
3. 体积/许可成为硬约束（例如发布 <20 MB 独立包，或必须闭源分发修改版）；
4. 你要把"UI 平台"本身做成产品给别的作者用。

---

## 6. 目标架构（自下而上）

```
L5  3D / NIF 预览服务     select / layout / camera / status / clear，自带设备策略与回退链
L4  功能模块（feature）    inventory / wear / magic / companions …（互不 import，经 shell 注册表协作）
L3  前端核心 App Shell    React + TS + Vite：路由、状态、查询缓存、设计系统、i18n、错误边界
L2  桥接层               单通道 + 版本化 schema + 校验/修复 + requestId + 事件 + 背压
L1  平台适配层            Surface / Transport / Input / Assets / Lifecycle（当前实现 = Meridian）
L0  游戏集成层            SKSE 插件：数据→DTO、命令→动作、生命周期事件、注册视图
```

### L0 游戏集成（native）

- 只做四件事：**把游戏数据变成稳定 DTO**、**执行命令**、**广播生命周期事件**、**注册一个 View**。
- 禁止在这一层写业务 UI 逻辑；禁止直接 `#include` 平台头——统一走 L1 的 wrapper。

### L1 平台适配层（现在的 Meridian，未来的任何实现）

对上层只暴露你自己的四个概念：

| 接口 | 职责 | 失败语义 |
| --- | --- | --- |
| `Surface` | show/hide/rect/z/focus | 不可用 → 返回 false，UI 显示"面板不可用" |
| `Transport` | 把前端帧送进游戏帧 | **能力探测一次，全消费者共享**；每条路径都必须有回退 |
| `Input` | 键鼠 / 手柄 / 文本 / IME | 焦点丢失 → 主动清理修饰键 |
| `Assets` | `mod://` 或本地 server | 404 不崩、有节流日志 |

**硬规则（来自 R2 的教训）**：任何"能力位"必须被**所有**使用该能力的路径读取；
新增能力必须同时提供"不可用时怎么办"，并在 UI 上有对应文案。

### L2 桥接层（协议）

- 一条通道多种消息；每条消息带 `v`（协议版本）、`id`（requestId）、`type`、大小上限。
- 命令 = 请求/响应（`ok/message`）；状态 = 快照推送 + 订阅；禁止"每个面板一个全局变量"
  （现状：每个模组各自占用 `window.*Request`，未来应统一）。
- 前端**必须**做校验与修复（现在是 `bridge.ts` 的 `parseSnapshot/repairSnapshot`），坏数据只丢该条、不清空面板。
- 快照带 `version`，与前端严格比对；不一致时给出可读提示而不是白屏。

### L3 前端核心

- 技术栈：**React + TypeScript + Vite**（与你现有 4 个模组的 `web/` 一致），
  共享库建议放 `shared/ui/`（你已经有 `shared/iconfont`、`shared/panel-power` 的先例）。
- 拆成包：`ui-tokens`（设计令牌）、`ui-components`（物品卡/属性对比/列表/对话框）、
  `ui-bridge`（协议类型 + 客户端 + fixture 运行时）、`ui-platform-meridian`（L1 的前端半边）。
- 设计系统：暗色半透明规范、面板不透明度派生（你已有 `card-style.ts`）、间距/字号阶梯、中文字体与行高。
- i18n：以简体中文为主 + 语言表；文案集中在 tokens 包，避免散落在组件里。
- 性能预算：面板 60 fps、单帧绘制预算、CEF 绘制频率、纹理内存上限；大列表用虚拟滚动。
- 可测性：纯逻辑（筛选/排序/对比/协议）必须有单测；UI 用 Playwright 跑"HTTP fixture"回归
  （你现在的 `web/tests/*.browser.cjs` 已经是这个模式，值得固化成规范）。

### L4 功能模块

- 每个模组 = 一个 feature module，只依赖 `ui-*` 共享包，模块之间不互相 import。
- "物品卡 / 属性对比 / 装备预览 / 同伴选择器"这类跨模组复用的原子，全部下沉到 `ui-components`。

### L5 3D / 预览服务

- 设备策略固定为一条**回退链**：① 游戏设备延迟上下文（不需要共享句柄）→
  ② 私有设备 + 共享纹理 → ③ CPU 回读上传 → ④ 明确不支持（UI 给文案）。
- 服务只暴露 `select/layout/camera/status/clear`，前端不做设备判断。

---

## 7. 与 SkyUI / PrismaUI 共存的过渡策略

- **SkyUI 不只是界面**：它同时是 MCM 规范、收藏菜单、物品分类/排序、制作界面的承载者，
  大量 mod 依赖 MCM（或 MCM Helper）。"替换 SkyUI"必须显式决定：
  继续兼容 MCM 接口、还是迁移到自己的设置体系、还是先并存。
- 建议路径：**先并存**（自有面板 + 热键/对话进入）→ 覆盖物品/装备主路径 → 最后才谈顶替 SkyUI 本体。
- 焦点仲裁：Meridian 只管自己；与 PrismaUI、原版菜单的互斥需要你自己的守卫
  （现状：物品清单 TESTING.md 里已记录"Prisma 占焦时拒绝"，应抽成共享能力）。

---

## 8. 风险登记表（节选）

| 风险 | 触发信号 | 缓解 |
| --- | --- | --- |
| 上游变动/停更 | 新版 Meridian 与你补丁冲突 | 固定版本 + 补丁集 + adapter 隔离；已归档补丁与二进制 |
| D3D11 注入层冲突 | 探测失败日志、画面异常 | 能力探测 + 全路径回退 + 前端状态文案 |
| 体积 400 MB | 分发/更新成本 | 评估 WebView2/Ultralight 探针（§9） |
| GPL 分发 | 发布修改版平台 | 发布对应源码（独立分支），模组本体走 MIT API 边界 |
| 多平台共存 | 输入/焦点互抢 | 共享焦点守卫 + 跨框架契约测试 |
| CEF 崩溃 | 面板白屏/子进程死亡 | 子进程隔离 + 状态上报 + 自动重启策略 |

---

## 9. 如果自研：最小垂直切片（建议 2–3 周，不是重写）

只做"一个窗口 + 一页 React"，目标是**把最大风险一次性打掉**：

1. **渲染**：CEF OSR 或 WebView2 视觉承载，把一个 React 页面渲染进 D3D11 的一小块矩形；
2. **环境**：在 ENB + 上采样 + 你的预设下稳定工作（本机刚踩过这个坑）；
3. **输入**：键鼠、文本输入、Alt-Tab、修饰键、焦点抢占、与 Prisma 共存；
4. **生命周期**：读档 / 新档 / 关机 / 子进程回收；
5. **指标**：包体、启动耗时、稳态内存、帧时间，与 Meridian 对照。

验收标准：以上 5 项在真机上连续通过 3 次会话无异常，且实现量（含调试）不超过 3 人周。
通过 → 再谈逐步替换下层；不通过 → 说明 Meridian 的价值就在这些脏活里，把精力放回上层。

---

## 10. 路线图

| 阶段 | 交付 | 验收 |
| --- | --- | --- |
| P0 冻结与盘点（现状） | 固定 Meridian 版本 + 补丁集 + 能力探测 + adapter 雏形 | 补丁可重复构建与回滚；能力探测结果进入 UI 状态 |
| P1 前端共享层 | `shared/ui/`（tokens/components/bridge/fixture）并把现有面板迁移过去 | 现有 4 个面板功能不变、测试全绿、包体不增 |
| P2 物品清单垂直切片 | 数据模型 + 搜索/筛选/排序 + 虚拟滚动 + 与 SkyUI 并存 | 真机 60 fps、万级物品列表可交互、浏览器回归覆盖 |
| P3 顶替 SkyUI 交互入口 | 热键/对话/装备栏入口 + MCM 依赖方案 | 依赖 MCM 的 mod 行为不回归（列清单逐项验证） |
| P4 下层决策点 | §5 的触发条件 + §9 探针结论 | 明确"继续用 Meridian / 替换下层"并记录理由 |

---

## 11. 附：本次评估的事实来源

- `C:\Users\linos\Desktop\github\MeridianUI`（v1.5.0 源码，commit `5707877`）：
  `README.md`、`CHANGELOG.md`、`LICENSING.md`、`EXCEPTIONS.md`、`docs/MeridianUI-AuthorGuide.md`、
  `src/UIPlatform/**`、`src/UIPlugin/main.cpp`、`vcpkg.json`、`CMakePresets.json`
- 本机运行日志：`MeridianUI.log`、`CompanionManager.log`（2026-09-25 会话）
- 本次补丁：分支 `codex/game-device-nif-fallback`（commit `60c78fb`），
  归档 `MO2\companion-manager-backups\meridian-nif-fix-1.5.0\`
