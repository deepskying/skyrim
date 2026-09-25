## 1.8.15（2026-09-25）列表更扁、预览自动撑满

- 反馈：① 左侧列表滚动容易把面板一起滚上去、看不到预览；② 预览区仍偏小，希望用 flex 自动撑满；③ 列表项去掉背景与圆角；④ 类型图标放大，「已穿戴/收藏」不要再挤在图标下面，改到名称后面。
- 高度链（②③ 的根因与修法）：面板内容区是 flex 子项（`.cm-management{flex:1;min-height:0;overflow:auto}`），原先「随从装备」页没有把它接满，内容比容器高 38–64px，于是滚轮滚的是面板、预览被压到最小高。现改为 `.cm-management-outfits`（GameApp 给穿搭区块加的类）→ `.cm-outfits` → `.cm-wear` 逐级 `display:flex;flex:1;min-height:0`，列表 `flex:1;min-height:0;overflow:auto` 并加 `overscroll-behavior:contain`；实测面板 `scrollHeight === clientHeight`（812/812）、列表内部滚动 (543/541)、滚轮后页面 `scrollTop` 与面板 `scrollTop` 均为 0。
- 预览：`.cm-preview`/`.cm-preview-viewport` 由固定高度改成 `flex:1 1 0%`（下限 200px，窄屏 240px），并把「穿上/卸下」按钮移到标题行右侧（`.cm-wear-title-actions`）、操作提示并入事实条、属性卡由 `auto-fit` 改为一排 5 列——腾出的高度全部给预览。实测同一视口下预览由 252px 提升到 298px（无「将换下」行时），面板变高时随之增长。
- 列表项：行背景改回 `transparent`、去圆角（收藏行仍保留淡蓝 `rgba(122,176,226,.22)`），类型图标 `font-size` 1.15em → 1.55em；「已穿戴」徽章与收藏 ★ 从图标下方移到名称后同一行（`.cm-wear-tags` 结构删除，改为名称单元格内的 `.cm-wear-badge`）。
- 验证：`npm test` 55 项通过；`npm run build`（含 `tsc --noEmit`）通过；浏览器回归新增断言——普通行 `background-color` 为 `rgba(0, 0, 0, 0)` 且 `border-radius: 0px`、`.cm-wear-tags` 计 0、图标 `font-size ≥ 20px`、已穿戴徽章与 ★ 位于名称之后、列表 `overscroll-behavior: contain` 且滚轮后页面与面板 `scrollTop` 均为 0、预览不被裁切且随面板变高而增长（1440×1500 对比 1440×1000）；原有断言（2px 行距、收藏淡蓝底、图标字体与 `E83A` 盾牌码点、`previewSelect/Layout/Camera/Clear`）继续通过。
- 游戏内待复测：滚轮划过左栏只滚列表；预览区在 1440p 下是否足够大、拖拽/滚轮手感；行无底色后的可读性与收藏行标记是否清楚；名称后徽章的换行表现（超长物品名）。

## 1.8.14（2026-09-25）装备预览取景与列表间距

- 反馈：① 装备预览的展示区域太小；② 列表项之间希望有 2px 间距；③ 已收藏的列表项给淡蓝色背景；④ 移除「手动调整」页签；⑤ 左侧列表没有占满剩余空间。
- 根因（平台侧，不是容器尺寸）：Meridian 的 NIF 取景把模型包围球半径下限钳在 `1.0`——小于 1 单位的网格（戒指、项链，以及按"米"级导出的掉落模型）被按半径 1 取景，模型缩在视口正中（截图实测约占高度 16%，正常取景应约 80%）。已在 `mods/meridian-ui` 应用本地补丁 `patches/0002`（半径只留 `0.05f` 防退化下限，取景公式与半径>1 的模型行为不变），用 `build-local.ps1` 重新构建并替换 MO2 里的 `MeridianUI.dll`（归档 `MO2\companion-manager-backups\meridian-nif-fix-1.5.0\`）。
- 前端：`.cm-wear-list` 改为纵向 flex + `gap:2px` + 透明底，行自带 `var(--card-bg)` 与圆角，去掉行下边框；`.cm-wear-head` 保持吸顶并加 `z-index`；`.cm-wear-list-pane` 改为纵向 flex 且列表 `flex:1;min-height:0`（去掉 56vh 上限，窄屏仍保留 40vh），左栏因此与右栏等高、内部滚动；`.cm-wear-row.is-favorite` 淡蓝底 `rgba(122,176,226,.22)`，`is-favorite:hover` 与 `is-favorite.is-preview` 各加深一档，避免与 hover/选中态冲突。
- 面板结构：`OutfitPanel` 删除「手动调整」页签与整页部位网格（含槽位状态、装备卡片、随机更换此部位按钮以及随之不再使用的 `slot`/`candidates`/`protectedMask`/`inSlot` 等状态）；`mode==="part"` 的入口改为落到「随从装备」页，旧原生端仍能正常打开。
- 类型图标：`wear.ts` 新增纯函数 `wearIcon(row)`——先判部位（39 盾牌、30 头部、33 手部、35 项链、36 戒指），再按 `armorType` 落到护甲/服装/首饰/兜底；重甲与轻甲共用护甲字形、用 `is-heavy`/`is-light` 区分颜色。字形取自 `shared/iconfont`（与物品清单同源，码点 shield `E83A`、armor `E61D`、robe `EC54`、necklace `EA3F`、ring `E636`、helmet `E971`、gloves `E6C3`、box `E65F`），字体文件复制到 `web/src/fonts/` 并由 `outfits.css` 的 `@font-face` 以**相对路径**引用——Vite 会把它作为资源打进 `dist/assets/iconfont-*.woff2|woff|ttf`，因此 `mod://` 与开发服务器下都能解析（不像绝对 `/fonts/` 依赖主机根路径）。
- 验证：`npm test` 56 项通过（新增 `wearIcon` 映射与码点断言）；`npm run build`（含 `tsc --noEmit`）通过，产物含 `assets/iconfont-*.woff2|woff|ttf`；浏览器回归改写并 PASS——部位页断言替换为「不再存在『手动调整』页签、工具栏只剩 2 个页签、`part` 入口打开随从装备页」，新增收藏行断言（`.cm-wear-row.is-favorite` 计 2 条、计算背景色含 `122, 176, 226`）、列表高度断言（≥400px）与图标断言（每行 1 枚、详情标题 1 枚、铁盾行用 `E83A`、字体族含 `cm-iconfont`、`document.fonts.check` 为真）；预览相关断言（`row-gap === "2px"`、视口 ≥300px、`previewSelect`/`previewLayout`/`previewCamera`/`previewClear`）继续通过。原生侧无改动（平台补丁单独构建验证：`NifPreviewRenderer.obj` 与 DLL 时间戳晚于源码改动）。
- 游戏内待复测：戒指/盾牌/服装在预览里是否填满视口、拖拽与滚轮缩放手感是否合适；列表 2px 间距、收藏淡蓝底、表头吸顶、左栏是否填满高度；确认「手动调整」页签已消失且没有别处入口依赖它。

## 1.8.13（2026-09-25）新增「随从装备」页（第一轮列表 / 属性 / 穿脱，第二轮 3D 预览）

- 需求：新增一个「随从装备」页替代按部位网格浏览——左侧一条列表直接列出随从库存里的服饰（全部列出、不分分类），每行显示名称 / 数量 / 重量 / 价值，已穿戴的加特殊样式；右侧上半为 3D 预览、下半为属性，且属性显示与当前穿戴的对比（例如 护甲 41 (−3)）；悬停即预览、方向键移动选择并预览、点击或 Enter 切换穿戴；保留「按部位」页签，「整套随机」不变，对话第三条「调整穿搭」改为打开新页；不做存取物品。范围口径经确认为"SkyUI 装备列表里的东西"——护甲 / 服装 / 首饰 / 盾牌，武器与其它物品不进列表。分两轮落地：第一轮列表 + 属性 + 穿脱，第二轮 3D 预览。
- 原生数据：`WardrobeSnapshot` 为护甲记录补 `mask`（`GetSlotMask()`）、`armorRating`（`TESObjectARMO::GetArmorRating()`）、`armorType`（关键字 `ArmorLight` / `ArmorHeavy` / `ArmorJewelry` / `ArmorClothing` → `light` / `heavy` / `jewelry` / `clothing`，其余 `other`）与 `enchantment`（`TESEnchantableForm::formEnchanting` 名称），非护甲行不产生这些键；快照 `version` 2 → 3（`snapshot.cpp`）。
- 原生命令：新增 `toggleWear {itemKey}`（`outfit_presets.inc` 的 `ToggleWear`），与换装命令同一组可用性校验（在队同伴、非战斗、非剧情场景、3D 已加载、距离 600）；已穿戴 → 拒绝任务装备后 `UnequipObject`，未穿戴 → 先按槽位换下冲突的旧装备再 `EquipObject`；槽位被任务装备占用时抛错拒绝而不是硬脱。复用 `outfitChecks` 延迟确认：脱下用 `removing=true` 核对"确实不在身上"，换上把被替换件放进 `removed` 并核对"新件穿上、旧件换下"。
- 原生规则：`outfit_rules.h` 新增 `Toggleable`（可穿戴 = 可穿 + 占至少一个槽位，首饰与盾牌都算）、`ReplacedBySwap`、`SwapProtected`；`outfit_presets.inc` 里盾牌不再受 `OutfitArmor` 的排除影响，随机穿搭的既有规则不变。
- 前端：新增 `web/src/wear.ts`（列表过滤 / 搜索 / 方向键选择 / 护甲对比计算 / `canToggle`）与 `web/src/WearPanel.tsx`（左列表 + 右属性），`OutfitPanel` 增加第三个页签并在 `mode==="wear"` 时默认打开它，`GameApp` 的 `companion:wardrobe` 事件接受 `wear` 模式，`manager.cpp` 的对话模式 1 改为打开该页；`outfits.css` 增加该页布局（≥900px 双栏，窄屏单栏）。`behavior.ts` 的 `WardrobeItem` / `validWardrobe` 与 `bridge.ts` 的修复层同步新字段（坏值丢弃而不是丢弃整行），`preview-data.mjs` 补演示数据与 `toggleWear` 模拟。
- 原生预览：新增 `native/src/model_preview.h`（照 `inventory-manager` 的结构，改用 CompanionManager 的 owner/surface 名）：`Select(actorID,itemID)` 只接受 ARMO，模型取该随从 actor base 性别对应的 `worldModels[sex].GetModel()`、取不到时回退另一性别，没有世界模型则保持 `selected_=0`；`Layout` 校验矩形（上限 16384/8192）并在无效时隐藏渲染面；`Camera` 夹取 yaw/pitch(−85..85)/distance(0.25–4)；`Status` 用 `GetStatus` 把 RenderLayer 的可见性绑在"面板有焦点 + 布局有效 + Ready"上；`Clear()` 先 `SetVisible(false)` 再 `ClearModel`。`main.cpp` 把 `Meridian::UI::Settings` 提升为会话级对象（View / RenderLayer / NifView 三个扩展共用同一份），在 `kInputLoaded` 里查询两个扩展，`Close()`、读档、开新档都会清模型，并新增 `previewSelect` / `previewLayout` / `previewCamera` / `previewStatus` / `previewClear` 五个 UI 动作（未聚焦时一律只清不建，`previewStatus` 回 `companion:preview-status` 事件，回声带 `id` 与 `token`）。快照结构未变，因此桥接版本仍是 3。
- 预览规则：`state_rules.h` 新增纯函数 `FormIDFromHex`（8 位十六进制才解析，否则 0），`manager.cpp` 的 `ParseID` 改用它（行为不变），预览动作的 `id` / `actorId` 也走同一解析——非法 ID 只会清空预览，不会抛错。
- 前端预览：新增 `web/src/ModelPreview.tsx`——空视口上报 `previewLayout`、每 250ms 轮询 `previewStatus`、离开页面或切换物品时 `previewClear`，拖拽 / 滚轮发 `previewCamera`，「重置视角」回到 35/15/1。`WearPanel` 把预览放在属性上方，并把"跟随预览"延迟 180ms（鼠标扫过整列不会每个行都排一次 nif 加载，属性面板仍然即时响应）。五种状态文案做成 `wear.ts` 的纯函数 `previewLabel`（未连接 / 不支持 / 加载失败 / 正在加载 / 拖动提示），没有选中项时显示"选择左侧的服饰预览模型"。原生日志新增失败行 `Wear preview failed: item=... path=...`（同一物品只记一次），配合 MeridianUI.log 即可定位是渲染器还是文件的问题。
- 预览运行时：`previewRuntime.ts` 在 HTTP 预览页里回应 `previewStatus`（默认 `unavailable`，可用 `window.__companionPreviewStatus` 覆盖），供浏览器回归覆盖各状态文案——游戏内不读这个开关。
- 首轮游戏内实测反馈（2026-09-25，用户截图）：① 护甲对比显示成 `729.6899909973145` 这种浮点原值 → 面板改为整数显示（`wearOutcome` 先取整两个总数、增减由两者相减，保证三个数字自洽），`preview-data.mjs` 把铁盾改成 20.4 这种非整数评分并在浏览器回归里断言面板不出现小数；② 3D 视口显示「模型加载失败」→ 查 `CompanionManager.log` + `MeridianUI.log` 定位为**渲染器环境问题,不是本模组**：请求路径全部正确排队（`NifViewAPIController: queued '<真实路径>' for surface 1`，含 vanilla `Armor\Falmer\FalmerCuirass_GO.nif`），但 Meridian 在原生 D3D11 上用"游戏设备 ← 私有设备"的共享纹理传帧，该机器的游戏设备创建共享纹理直接失败（`RenderDevice: shared keyed-texture probe CreateTexture2D failed (0x80070057)`、`FrameTransport: slot texture creation failed (0x80070057)`、`NifPreviewRenderer: cross-device frame transport initialization failed`），于是 `NifPreviewRenderer: scene composition failed ... (0 shapes skipped)`、状态恒为 Failed。同一探测失败也已让浏览器面板里的 RingBuffer 回退到 SyncCopy（所以 UI 正常显示），但 NIF 预览在原生 D3D11 上没有回退路径，`[Compatibility] BrowserTransport` 只作用于浏览器传输、不作用于 NIF 传帧，因此本模组侧无从规避。
- 验证：ESP 结构测试 8 项通过（ESP / Papyrus 未改动，对话仍复用 `CMOutfitPartTopic` 的模式 1）；原生 Release DLL 构建通过，8 个测试目标直接运行 exit=0（outfit-state-test 新增 `Toggleable` / `ReplacedBySwap` / `SwapProtected` 边界，含盾牌槽位；state-rules-test 新增 `FormIDFromHex` 合法 / 非法输入边界，并用一次故意的假断言实测 exit=-1073740791 确认 CHECK 未被 NDEBUG 吃掉，随后复原）；网页 54 项测试通过（新增 8 项：列表只含服饰、搜索、方向键边界、护甲对比、任务装备保护、`toggleWear` 换装与保护、字段校验与修复、预览文案唯一性）与 TypeScript / Vite 构建通过；浏览器回归 `tests/outfit-dialogue.browser.cjs` PASS（新增：模式 `wear` 打开新页、列表只有 6 件服饰且不含武器药剂、已穿戴行 2 条、悬停切换预览与对比数值、盾牌 `+20` 且无"将换下"、方向键选中 + Enter 换装、点击穿上银项链、搜索 2 件 / 0 件 / 复原；3D 视口：`previewSelect` 带正确的 actorId 与 base form、`previewLayout` 尺寸为正、拖拽发出 `previewCamera`、`ready`/`unsupported`/`unavailable` 三种文案与「重置视角」的启用状态、切页发出 `previewClear`）。
- 游戏内待复测（只能在游戏里看画面）：新页列表与游戏内实际服饰是否一致（含首饰与盾牌）；悬停预览与点击穿脱是否按槽位替换、任务装备是否拒绝卸下；护甲对比数值与角色面板的实际护甲变化是否吻合（本轮已按整数口径修好显示）；3D 视口是否正好压在预留区域内（不盖住列表与属性）、模型朝向 / 缩放是否合适、拖拽旋转与滚轮缩放是否顺手；没有世界模型的物品是否显示「此物品暂不支持模型预览」、未安装 Meridian NifView 时是否显示「模型预览未连接」；关闭面板或切到别的页签后渲染面是否消失（不留悬浮图层）。
- 模型预览的排查过程（2026-09-25 续）：先用一个临时 D3D11 探测程序在本机独立进程里复现 Meridian 需要的能力（在 AMD 集显与 NVIDIA RTX 4070 SUPER 上各创建 `R8G8B8A8` + `SHARED`、`SHARED_KEYEDMUTEX`、`SHARED_KEYEDMUTEX|NTHANDLE` 纹理），**全部返回 S_OK**——所以驱动与系统层面没有问题，失败只发生在游戏进程内，属于进程内注入层改写设备行为。
- 注入层清点：MO2 的 `ENB-预设-古色之城` 自带一份 `d3d11.dll`，但它在 `-std-`、`-back-`、`物品清单-Meridian测试`、`音乐管理器-测试`、`sex` 五个档案里都是禁用状态，且未安装 Root Builder，因此实际生效的 ENB 只有游戏根目录那份 `SkyrimSE\d3d11.dll`（ENBSeries 0.5.0.5）。已把它临时改名为 `d3d11.dll.enb-off-preview-test` 做单变量 A/B（恢复：把名字改回 `d3d11.dll`）。
- ENB A/B 的实际结果（2026-09-25 12:01）：关掉 ENB 后启动时 `KIENBExtender.dll` 报"Import dependency missing from: d3d11.dll"（预期，ENB Extender 挂在 ENB 的代理上），点"否"继续后进程跑了 2:44 闪退。崩溃签名见 `crash-2026-09-25-12-01-16.log`：`EXCEPTION_ACCESS_VIOLATION` at `VCRUNTIME140.dll+001DC3E vmovdqa [rcx+0xE0], ymm4`，相关对象是 `NiSkinInstance` / `NiSkinPartition` / `BSTriShape` / `BSLightingShader` / `BSShaderAccumulator`（引擎蒙皮几何拷贝），栈里 **没有任何 CompanionManager.dll 或 MeridianUI.dll 帧**，崩溃日志的 SKSE 插件表里也没有 `KIENBExtender`（证实那次确实没加载）。该进程 GPU 显存 10.00/10.97 GB（约 91%）。用户近 12 天另有 7 次崩溃且签名各不相同（`EquipmentWorkshop.dll`、`NPCSpellVariance.dll`、`std::bad_function_call`、多处 `SkyrimSE.exe` 内部），因此无法把这次归因于关 ENB，但也**没有**取得"预览在无 ENB 时可用"的证据：`MeridianUI.log` 每次启动都会覆盖，11:58 那次会话的记录已被 12:01:56 的新启动冲掉。已把 `d3d11.dll` 原名恢复、ENB 回到生效状态，并停止继续用"关 ENB"这条路验证预览。
- 结论与后续：3D 预览维持现状——本机上 MeridianUI 的共享纹理传帧不可用，面板会如实显示「模型加载失败」，其余功能不受影响；若将来把 D3D11 层换成 DXVK（目录里已有 `d3d11_dxvkasync1_10_3.dll`），Meridian 的 NIF 预览走游戏设备路径、不需要共享纹理，无需改代码即可用，代价是 ENB 不可用。可选的下一步只有：换成 DXVK 方案，或把 Meridian 日志反馈给上游。
- 最终解决（2026-09-25 12:20，用户实测通过）：改为**自编译一份打了补丁的 MeridianUI 1.5.0**，不动 ENB、不动 DXVK。根因是 Meridian 自己的疏漏——`RenderDevice::Create` 已经探测出共享纹理不可用（`SupportsSharedKeyedTransport()` 为 false，浏览器层据此降级成 SyncCopy），但 `NifPreviewRenderer::InitializeGraphics` 只按 `gameDeviceNifRendering`（`dxvk && !wine`）选择路径，仍走 `FrameTransport`，于是必然 0 形状。补丁只有一处条件：探测到共享纹理不可用时，改用**游戏设备上的延迟上下文**（DXVK 已经在用的那条路，`SubmitDeferredFrame` 以 `ExecuteCommandList(commands, TRUE)` 恢复游戏管线状态），全程不需要共享句柄。源码分支 `codex/game-device-nif-fallback`（commit `60c78fb`），补丁与自编译 DLL 归档在 `MO2\companion-manager-backups\meridian-nif-fix-1.5.0\`，官方原 DLL 备份在 `...\meridian-official-1.5.0\MeridianUI.dll`。
- 实测证据（`MeridianUI.log` 12:18–12:19 会话）：设备仍报 `RingBuffer browser transport is unsupported on this game adapter`（环境未变、ENB 在跑），随后 `NifPreviewRenderer: shared-keyed transport unsupported on this game device; rendering on the game device` 出现一次，`scene composition failed` 由每模型一条变为 **0 条**；`CompanionManager.log` 里 `Wear preview requested` 8 次、`Wear preview failed` 0 次。注意：这份自编译 Meridian 影响所有 Meridian 消费方（随从管理 / 装备工坊 / 物品清单），官方更新 Meridian 后需要重新应用该补丁。

## 1.8.12（2026-09-25）穿搭对话升级为三条一级选项

- 需求：把「穿搭调整」里的条目提升为一级对话——①随机套装（只在已保存套装里随机，无套装时提示）②保存当前套装 ③调整穿搭（本轮仍是打开面板，装备预览后续再做）。
- ESP：`source/build_plugin.py` 去掉父话题（原 0xB01「穿搭调整」DIAL 与 0xB02 INFO 及其 TCLT 子话题结构），改为三条独立顶级分支：`0xB00→随机套装(0xB01/0xB02, CMRandomOutfitTopic)`、`0xB04→保存当前套装(0xB10/0xB11, CMOutfitSaveTopic)`、`0xB08→调整穿搭(0xB12/0xB13, CMOutfitPartTopic)`；每条分支 `DNAM=1`、`SNAM` 指向自己的话题，话题 `BNAM` 指向自己的分支，INFO 条件沿用 4 条作用域条件。旧 0xB14/0xB15（整套随机子项）不再产生。
- 原生：新增 `outfit::HasSavedSet` / `SavedSetPick` 规则与 `Result::NoSavedSets`（消息「还没有保存的套装：请先在伙伴穿搭面板保存一套」）及 `RandomSavedOutfit`（无套装直接返回 `NoSavedSets`，不做重新组合）；`CMDialogue.RandomOutfit` 改名 `RandomSavedOutfit`，对话模式 0 走新函数；面板「随机一套」与定时换装仍用 `RandomNamedOutfit`（70/30）。
- 脚本：`CMDialogue.psc` 与 `CMRandomOutfitTopic.psc` 同步改为 `RandomSavedOutfit`，Papyrus 5 个脚本 0 错误 0 警告。
- 验证：ESP 结构测试 8 项通过（新增：三条独立分支/话题/INFO 与标题顺序、无 TCLT、VMAD 字节结构、片段脚本调用 `RandomSavedOutfit`、脚本中不再存在 `RandomOutfit`）；原生 8 个测试目标 exit=0（outfit-state-test 新增 `HasSavedSet`/`SavedSetPick` 边界与 `NoSavedSets` 消息区分）；网页 46 项测试与构建通过。
- 游戏内待复测：与已纳入管理的在队同伴对话，二级菜单不再出现，直接看到三条；连点「随机套装」应在已保存套装之间轮换，且**不会**出现从收藏重新组合的搭配；删光已保存套装后点该条应只提示"还没有保存的套装"；「保存当前套装」与「调整穿搭」行为与之前一致。三条的显示顺序以实际为准（当前按 PNAM 50/49/48 与记录顺序排列）。

## 1.8.11（2026-09-25）点击套装卡片直接换整套

- 需求：面板里点其他套装的卡片直接换整套，不必再点下方的「使用此套装」。
- 前端：`OutfitPanel` 新增 `applyPreset(id)`——选中该套装并在可用时立即提交 `applyNamedOutfit`；套装卡片第三行改为「N 件服饰 · 点击换上」，卡片点击直接换装；移除「使用此套装」按钮，工具条保留「随机一套」与「移除当前套装」，提示文案随选中状态更新（不可用时提示"当前无法换装，仅预览"）；「当前套装」卡片仍只做预览。
- 验证：浏览器实测（预览页 + 临时 Playwright）：断言页面已无「使用此套装」按钮；单击「月下长袍」卡片后，原先的皮甲 / 白色高跟靴 / 银项链全部换下，只剩套装里的弥光连体袍，符合 1.8.10 的整套替换语义。网页 46 项测试与 TypeScript / Vite 构建通过（本改动不涉及原生与 ESP）。
- 游戏内待复测：点击套装卡片应立即换装并出现换装确认提示；战斗中点击只切换预览并提示无法换装。

## 1.8.10（2026-09-25）使用套装改为整套替换

- 反馈：使用已保存套装时不会清空其他槽位，换装后是「套装 + 先前装备」的混合状态。
- 原生：新增规则 `outfit::StripBeforeWear`（是套装部件、非任务/皮肤、且套装未指名才脱下）与 `StripCandidates`；`WearSet` 增加剥离列表参数，先清 `ExtraCannotWear` 再 `UnequipObject`，然后才穿套装；`OutfitCheck` 增加 `removed` 列表,`CheckOutfits` 同时核对"该穿的穿上、该脱的脱掉"（`Outfit final ... removed=N`）；`WearSet` 在"没有要穿的、也没有要脱的"时返回 `Unchanged`。`ApplyNamedOutfit` 仅对玩家/对话请求（manual）传入剥离列表：自动定时换装保持不脱旧装备，避免部件缺失时把无人看管的同伴脱空。套装实例全部缺失时仍返回 `NoSelection` 且不做任何更改。
- 前端：面板「使用此套装」说明改为"先换下当前服饰（任务装备与角色皮肤保留）；库存缺失的实例跳过，对应部位保持空着"；`preview-data.mjs` 的 `applyNamedOutfit` 模拟同步为整套替换，并新增与修正测试：新增「applying a saved outfit takes off the pieces it does not name」（任务装备保留、套装未包含的部位脱下、缺失实例不留替代品），原「缺失实例不清空该槽位」的断言按新语义改为"替身也一并脱下、槽位留空"。
- 验证：原生 Release DLL 构建通过，8 个测试目标直接运行 exit=0（outfit-state-test 覆盖 StripBeforeWear 四类判定）；网页 46 项测试与 TypeScript / Vite 构建通过；ESP 未改动（结构测试 9 项仍通过）。
- 游戏内待复测：给同伴穿上一件套装未包含的戒指/头环 → 使用套装 → 该件应被换下、套装配不到的槽位应为空；任务装备（如任务头盔）应保持穿戴；日志应出现 `Outfit strip`、`Outfit dispatch` 与 `Outfit final ... removed=N`；定时自动换装不应脱掉旧装备。

## 1.8.9（2026-09-25）穿搭卡片透出角色

- 需求：调整穿搭时装备卡片是不透明底色，挡住了身后的随从，看不到换装效果。
- 前端：`GameApp` 新增 `--card-bg` / `--card-bg-strong` 变量（`web/src/card-style.ts`，按「面板不透明度」推导并夹在 0.34–0.72，永远不透明），`outfits.css` 的 `.cm-outfit-row`、`.cm-slot-equipment-card`、以及两处选中态底色改用它；卡片仍保留边框与已穿戴高亮，文字对比靠底色而非纯色实现。变量缺失时 CSS 回退到 `rgba(23,32,39,.55)`，设计预览页同样透出背景。
- 浏览器实测（临时安装 Playwright 1.49 + 系统 Edge，`npm run dev` 预览页）：`node tests/outfit-dialogue.browser.cjs` 通过；另用临时脚本复现"其他同伴走近导致快照重排"，面板目标保持莱迪亚不变，并读取到卡片计算样式为 `rgba(23,32,39,0.56)`（非不透明）。
- 顺手修正 `tests/outfit-dialogue.browser.cjs` 的一处 strict 模式定位（`dialog` 有两个，改用 `dialog[open]`），该脚本此前在本机无法运行，Playwright 可用后成为 1.8.8 选择固定与对话归属回归测试。
- 验证：网页 45 项测试通过（新增 `cardAlpha` 边界与"永不不透明"检查）、TypeScript / Vite 构建通过；浏览器回归脚本 PASS；原生 DLL 与 ESP 未改动，仅版本号同步。

## 1.8.8（2026-09-25）撤回部位对话菜单与固定面板目标

- 实测反馈：1.8.7 的平铺部位随机对话项体验不好；另外打开穿搭面板后，随从走开或其他人经过时面板里的目标同伴会自动变化。
- 撤回：`source/build_plugin.py` 恢复三项固定菜单（保存当前套装 / 手动调整 / 整套随机），TCLT 与优先级回到 0x01000B10/0x01000B12/0x01000B14，删除 13 组部位 DIAL/INFO、13 个 `CMOutfitSlot*` 全局变量、`GetGlobalValue` 条件、`CMOutfitSlotTopic.psc` 与同名 PEX；`CMDialogue` 去掉 `RandomOutfitPart`；原生删除 `RandomFavoritePart`、`FavoritePartCandidates`、槽位全局变量与 `MenuOpenCloseEvent` 同步、`dialogueOutfitSlot` 与模式 3，`outfit_rules.h` 去掉 `NamedSlots`/`EligibleFavoritePart`（保留 `SlotBit` 与 `EligibleFavoriteRow`）；package / install 脚本的必需文件列表回到五个 PEX。整套随机与面板随机只从收藏挑选的规则保留。
- 修复目标漂移：根因是原生快照按 (owned, teammate, 距离) 排序，`GameApp` 的衣橱/法术页与 `Management` 的伙伴库存页在未显式选人时取列表首项 `followers[0]`，同伴移动或他人靠近就换人，OutfitPanel 还带 `key` 随人数变化重挂载。新增 `web/src/companion-selection.ts` 的 `pinnedCompanionId`：已选同伴仍在名册时保持不变，快照为空时保留选择，只有离开名册才回落到第一位；两处组件改用 `useLayoutEffect` 固定选择，`CompanionPicker` 列表按姓名 + FormID 稳定排序。
- 验证：ESP 结构测试 9 项通过（新增「菜单只有三个固定选项、无 GLOB、无部位脚本」检查）；Papyrus 5 个脚本 0 错误 0 警告；原生 Release DLL 构建通过，8 个测试目标直接运行 exit=0；网页 44 项测试（新增选择固定 2 项）与 TypeScript / Vite 构建通过。
- 游戏内待复测：对话确认下级只有三项；打开衣橱/法术/伙伴库存面板后让同伴走动、引其他同伴靠近，确认面板目标不再变化，切换伙伴后仍能保持；确认部位换装只在面板里进行。

## 1.8.7（2026-09-25）对话换装菜单与收藏随机

- 需求：把「穿搭调整」下级菜单改成 保存当前套装 / 手动调整 / 整套随机 / 平铺的 13 个部位随机；部位随机只从收藏挑选，该部位没有可选收藏服饰时不显示这一项；整套随机的 30% 重新组合同样只从收藏挑选；面板页签名与「手动调整」统一。
- ESP：`source/build_plugin.py` 重建对话组，父 INFO 的 TCLT 顺序即菜单顺序（0x01000B10 保存、0x01000B12 手动调整、0x01000B14 整套随机、0x01000B20+ 逐槽位），13 个部位各一组 DIAL/INFO 并共用 `CMOutfitSlotTopic` 的 Fragment_0..12，另加 13 个浮点全局变量 `CMOutfitSlot30..43`（0x01000C00+i，初值 0）。部位 INFO 在原有 4 条作用域条件下追加 `GetGlobalValue(该槽位变量) == 1`。
- 原生：`outfit_rules.h` 新增 `SlotBit` / `EligibleFavoriteRow` / `EligibleFavoritePart` 与 13 槽位表；`outfit_presets.inc` 新增 `FavoritePartPool`、`PartMask`、`SlotLabel`、`RandomFavoritePart`，`ChangeOutfitPart` 改用它（带 itemKey 的明确点击不受收藏限制）；`ChangeOutfit` 的候选加入收藏条件；无候选提示改为指向收藏。`CMDialogue` 新增原生函数 `RandomOutfitPart(actor, slot)`，走既有的对话换装校验（非战斗、非剧情、3D 已加载、距离 600）。新增 `MenuOpenCloseEvent` 接收器与 Tick 内 0.5 秒节流的 `SyncOutfitSlotGlobals`，在对话打开和说话人变化时刷新槽位变量；读档时清零。
- 前端：`OutfitPanel` 页签「指定部位」→「手动调整」，部位随机的按钮禁用条件改为要求存在收藏候选，文案写明随机只使用收藏；设置页与行为管理页同步说明；`preview-data.mjs` 的模拟规则与演示数据同步为收藏制，并新增回归测试「random piece and whole-set changes draw on favorites only」。
- 测试工具修正：8 个原生规则测试目标此前用 `-UNDEBUG` 后又收到规则注入的 `-DNDEBUG`，`assert` 全部被编译掉，目标始终成功而不执行任何检查（用 `assert(1==2)` 探针实证）。新增 `tests/check.h` 的 `CHECK` 宏（与 NDEBUG 无关）并机械替换 8 个测试文件，`outfit-state-test` 补上 `/utf-8`；改为直接运行 exe 校验退出码后，8 个目标 exit=0 且探针能正确失败退出。
- 验证：ESP 结构测试 9 项通过（含槽位记录、共用脚本 fragment、`GetGlobalValue` 参数）；Papyrus 编译 6 个脚本 0 错误 0 警告；原生 Release DLL 构建通过，8 个测试目标直接运行 exit=0；网页 42 项测试与 TypeScript / Vite 构建通过。
- 游戏内待复测：与同伴对话确认二级菜单为 保存当前套装 / 手动调整 / 整套随机 加实际可换部位；日志出现 `Outfit slot gate slot=.. available=..`（收藏变化后应随之翻转）与 `Outfit slot request/dispatch`；对耳部、尾部等冷门槽位确认无收藏时该选项不显示；确认整套随机与面板随机按钮都不再穿上未收藏装备。

## 1.8.6（2026-09-24）战斗状态与队友停战

- 现场问题：随从战斗结束后仍保持交战状态、无法交互；随从之间偶发互殴（目前只见瑟拉娜）。
- 判定改为"真实战斗"：只有存在存活、已加载、敌对且在同区域近距离内的战斗目标才算交战（原生侧新增 `Fighting`）。快照 inCombat、自动行为调度、换装 / 取物 / 对话换装 / 自动跟上 / 招募原因全部改用同一判定，残留标志不再锁死界面。
- 原生守卫：Tick 每秒检查一次成员的战斗目标。目标是玩家或其他同伴 → 立即 `StopCombat()`（玩家本身不停战）并记录 `Combat guard friendly fire`（含双方 FormID、`GetFactionReaction`、`IsPlayerTeammate`、aggression）；没有存活敌对目标并持续 6 秒 → 记录 `Combat guard cleared stale combat` 并停战 + `EvaluatePackage()`。同一成员两次动作间隔至少 5 秒。
- 关系修复：入队与读档后，每 15 秒最多提交 4 对，经 Papyrus `CMController.AllyMembers` 把同时在队同伴两两设为关系等级 3（盟友），只升不降（4 为 Lover，会影响对话，故不使用）；成功写 `Companion allies set`，失败则稍后重试。
- 验证：原生 Release 编译通过；原生测试目标 8 个（新增 combat-guard-test，覆盖真实战斗、友军停战、宽限期清理、目标有效性、关系等级）全部 exit=0；Papyrus 编译 0 错误 0 警告；网页 41 项测试与构建通过。
- 游戏内待复测：打一场架结束后数秒内面板应恢复可交互，日志出现 `Combat guard cleared stale combat`；瑟拉娜与另一名同伴同队站立时日志应出现 `Companion allies set` 且不再互殴；若仍出现 friendly fire 记录，按日志中的 reaction / aggression 判断是否需要更强限制（例如把该成员的「避免交战」打开）。

## 1.8.5（2026-09-24）实例编号冲突

- 现场数据：娜拉 FE1A8813 的 77265226「古老的诺德护手」同时以 count=1（穿戴中）与 count=5（背包备用）出现，两条共用 ExtraUniqueID FE1A8813:0020；前端 validWardrobe 因键重复丢弃整份 255KB 快照，面板显示"等待游戏数据"。通过 Meridian CEF 调试端口读取面板内 window.__companionSnapshot 复核，14 名人物中仅此一处不合格。
- 原生：Wardrobe() 按物品记录已用编号，发现重复实例键时保留未穿戴那一条的编号，为穿戴副本分配新的可用编号（先取引擎计数器，取不到时扫描空位），并写 Wardrobe identity reassigned 日志；16 位编号耗尽时跳过该条并记录警告。装备/穿戴实例的键因此在快照内始终唯一。
- 前端：新增 readSnapshot 修复层，重复键折叠、非有限数值与不一致标记修正、超长数组截断、不可用人物行单独跳过，原因在状态栏与提示条列出；严格校验仍作用于修复后的数据，只有无法修复时才拒绝并说明原因。
- 验证：原生 Release 与 TypeScript / Vite 构建通过，outfit-state-test 覆盖身份让位规则与编号分配，网页 41 项测试通过（新增重复键折叠、坏行跳过、非有限数值修复、超长列表截断、不可修复快照 5 项）。
- 游戏内待复测：娜拉存档打开面板确认 14 名人物正常显示，日志出现 Wardrobe identity reassigned；对该护手的穿戴件与备用叠分别执行锁定、取走、指定部位穿戴，确认作用于正确的实例。

# 1.0.0 验证记录（2026-09-13）

- 原生 Release DLL 构建通过；input-rules-test 和 state-rules-test 通过。
- Papyrus CMController 编译：0 错误、0 警告。
- ESP 结构测试 4 项通过：ESL ID / 依赖、64 个可选别名与包引用、模式条件 / 自有任务归属、VMAD 与 PEX。
- TypeScript / Vite 构建通过，桥接自动测试 7 项通过。
- 浏览器使用明确标注“非游戏”的模拟桥接：验证法术禁用回执、教学新增法术并扣一本书且禁止重复教学、按数量转移并核对玩家背包、失败保留原状态、读档事件清空人物与禁用指令。检查 1280×720 布局。
- 未启动 Skyrim。实际招募脚本调度、AI 跟随 / 返家 / 等待、真实背包 ExtraDataList、Essential 与成长数值、人物 NIF、退出与读档持久化，需要按 README 清单游戏实测。

浏览器模拟用于检验页面与消息协议，不代表引擎行为已验证。


## 1.1.0（2026-09-13）

- 新增教学可用性测试：缺失 ESP、外部人物、任务书、数量不足、已掌握的禁用法术、等待中的指令；包含书本正文纯文本处理。网页测试共 11 项通过。
- 浏览器核对队伍卡片布局、点击进入属性 / 行为 / 魔法三个标签、法术书效果介绍和正文、可点击的教学确认、模拟学习扣书与重复教学禁用。
- 本机实际教学尚未复测：此前游戏日志确认 ESP 未加载，需要启用后重启游戏。

## 1.1.2（2026-09-13）

- 根因：引擎队友被列为 party，但没有本模组 member 记录；旧招募条件同时拒绝 IsPlayerTeammate，界面因 managed=false 锁住全部操作。新增显式 adopt 指令与详情顶部入口，通过条件检查及自有别名绑定后才开放操作；不清除外部任务别名。
- 原生 Release 构建及 state-rules-test 通过，覆盖既有队友允许登记、非队友任务包保护规则。网页构建及 12 项测试通过。
- 浏览器使用未登记的在队人物：接管成功→行为开关可用→等待回执→传授快速治疗→已知法术从 1 到 2、书从 2 到 1、重复教学禁用；概览设置居所后名称正确回显。
- 模拟引擎拒绝接管：失败提示显示、居所仍禁用、保留接管按钮以便重试。
- 实测 viewport 1118×938，面板 x=33.525、y=37.5、宽=1050.55、高=862.60；对应装备工坊的 inset:4vh 3vw（舍入差异小于 0.1px）。概览视觉检查通过。
- 游戏日志确认 1.1.1 已加载且不再报告 ESP 缺失。本轮没有启动游戏，1.1.2 的真实脚本绑定、AI 行动、教学扣书及居所持久化仍待游戏实测。

## 1.2.0（2026-09-13）

- 名册扩到 64 位，保留旧 0–31 人物 / 32–63 居所别名。新增 64–95 人物 / 96–127 居所；第 33 位逻辑槽 32 对应人物别名 64 和居所别名 96。
- 原生 Release、state-rules-test、Papyrus 编译（0 错误 / 0 警告）、ESP 5 项结构测试和网页 13 项测试通过。
- 用已发布 1.1.2 的 SHA-256 基准验证旧 64 个别名及旧 faction/packages 的内容完全相同；全部 128 个别名、64 个返家包的目标引用及 FormID 校验通过。
- 原生存档校验接受逻辑槽 0–63，拒绝 -1、64 及小数。网页支持 64 个已登记人物加外部候选，超过 128 条快照拒绝解析。
- 未启动游戏。旧存档升级后新增槽位的真实可用性、接管第 33/64 位、居所与名册保存读档仍待实测。

## 1.3.0（2026-09-13，新档版）

- 按新开存档的要求移除 32 位旧布局的分段映射及旧 ESP 字节兼容测试，改为人物 0–63、居所 64–127。本文此前的 1.2.0 记录仅为历史结果。
- 原生槽位规则遍历验证 64 个连续人物槽和对应居所，保留越界、数据类型与 FormID 校验。SKSE 状态记录格式更新为 2，不加载旧格式；保留新格式的保存、读档与表单重定位。
- Release DLL、Papyrus 编译（0 错误 / 0 警告）、原生规则测试、ESP 4 项结构测试和网页 13 项测试全部通过。
- 未启动游戏。新档实际招募、居所、法术及保存读档仍需游戏实测。

## 1.3.1（2026-09-13）

- 原生规则验证：当前在队记录首次启用、手动关闭经过 JSON 保存/载入后保留、重新入队再次默认启用、离队记录不自动变更、固定等级与无上限角色跳过、原上限 500 不降为 300。
- Release DLL 和前端构建通过，原生规则测试与网页 13 项测试通过；教学接管测试同时验证自动开启成长上限。
- 浏览器确认概览当前等级仍为 34、成长上限显示 300，开关默认开启。真实游戏成长数值仍需实测。

## 1.3.2（2026-09-13）

- 补齐「我的队伍 → 招募同伴」入口：搜索附近候选、纳入既有队友、显示拒绝原因，确认后发送目标 actorId；不修改原版 PlayerFollowerCount 或 DialogueFollower 别名。原版对话仍为原有单随从限制。
- 原生 Release 与 TypeScript / Vite 构建通过，网页 16 项测试通过，新增连续两人招募、原队友保留、重复拒绝、满 64 位（含离队）和跨存档请求拒绝测试。
- 浏览器模拟验证：连续招募附近旅人和附近同伴，队伍由 4 人增加至 6 人，候选列表移除已招募人物；引擎模拟拒绝时显示错误，队伍不增加。检查招募弹窗布局。
- 启动日志改读编译版本；旧日志中的硬编码 1.1.1 不能单独用于判断实际 DLL 版本。
- 尚未在 Skyrim 实测此次入口的真实招募、第二位 AI 跟随及存档读写。

## 1.4.0（2026-09-13）

- 新增原版人类随从对话自动交接。核对本机 Skyrim.esm / Creation Kit：DialogueFollower=000750BA、人类别名=0、动物别名=1、PlayerFollowerCount=000BCC98。原版 SetFollower 最后写入 count=1；不替换其脚本文件。
- 对话关闭后连续观察同一目标，先完成自有别名绑定与名册登记，再由 CMController 检查原版人类别名、计数属性、目标一致性及非解散状态。解除原版等待计时后释放别名、清空计数并保留 teammate；不调用 DismissFollower。窗口打开时自动刷新面板。
- 名册已满保留原版跟随；剧情 / 战斗暂缓；重复登记、满员但已有记录、未完成招募和对话未关闭的策略由 state-rules-test 验证。自动登记保留原等待状态；交接失败保留登记并延迟重试，读档更换会话后忽略旧回调。
- Release DLL、state-rules-test、TypeScript / Vite 和 16 项网页测试通过，ESP 4 项结构测试通过；Papyrus 编译 0 错误 / 0 警告。
- 本轮未启动 Skyrim。仍需游戏验证：依次对话招募两名普通随从，关闭对话等待交接提示，检查两人均在队且可跟随 / 等待 / 离队；保存读档后确认保留。独立剧情框架与动物不纳入自动交接范围。


## 1.5.0（2026-09-13）

- 新增行为管理与伙伴衣柜；人物详情移除行为标签，保留概览 / 魔法。行为管理包含通用、拾取、售卖、穿搭、主动提醒、活动记录；新规则有全队默认和个人覆盖。
- TypeScript / Vite 构建与 20 项网页测试通过。新增测试覆盖装备实例收藏隔离、重复实例标识拒绝、参数校验、个人规则继承、多选取物的超重 / 穿戴保护及数量结算。
- Release DLL 构建通过；activity-rules-test、state-rules-test、input-rules-test 通过。负重规则包含不足一件、零重量、已经超重、NaN，交易数量受真实商家预算约束，等待 / 战斗 / 场景阻止执行。
- Papyrus 编译 0 错误 / 0 警告，ESP 4 项结构测试通过。保留 64 人物与 64 居所别名，增加 64 个活动目标与对应的 AI 包，校验各别名引用、模式 100 条件与记录唯一性。
- 浏览器设计预览验证：收藏附魔皮甲的星标与边框回显；取走 3 铁锭后数量 12 → 9，伙伴负重 182 → 179，玩家负重 220 → 223；穿戴物品不能选取。搜索范围 0 时保存禁用，改 45 后可保存，全队规则在莱迪亚个人页面继承显示 45。检查五个菜单、状态栏版本和深色布局。
- 未启动 Skyrim。引擎库存实例持久化、AI 走位 / 拾取动作、商家实际结算、穿搭 / 战斗不切装及跨存档行为仍需以下游戏测试。浏览器模拟和编译通过不等于游戏验证。

### 游戏集中测试

1. 新版本全套 DLL / ESP / PEX / 网页加载，状态栏显示 1.5.0；通过对话招募两位普通随从，确认名册和行动控制仍正常。
2. 「伙伴衣柜」收藏需要保留的装备。同基础物品的不同附魔 / 强化版本分别切换收藏，穿戴和保存读档后收藏不丢失，物品数量不增加。金币、任务物品和穿戴标记正确。
3. 结束一场战斗后，观察走近 / 朝向 / 拾取过程；检查类别、价值、范围、部分堆叠与负重上限。玩家丢下的东西、有主物品、上锁容器与队友尸体保持不动。
4. 拾取途中重新进入战斗，确认停止取物并回到战斗；等待和离队人物不参与。让目标不可达，约 35 秒取消任务，不瞬移拾取。
5. 先在衣柜收藏保留装备，再进入营业的杂货店 / 铁匠铺。观察伙伴靠近和文字交谈，核对物品入商家库存、商家金币减少、伙伴金币增加，通知件数 / 收入相符；切换商品类别与低金币商家验证部分交易。不出售收藏、穿戴、任务及不可玩物品。
6. 玩家与商家交易时其他伙伴等待，多个伙伴依次出售。关闭个人售卖后不再出售，其他沿用全队的伙伴继续按默认规则。
7. 收藏两件冲突槽位服装后点击试换，检查实例与槽位；遇敌不恢复旧装备。自动穿搭按游戏小时发生，保存读档后计时保留。换下的装备按普通库存规则处理，收藏仍提供出售保护。
8. 伙伴负重接近上限、玩家有空间时收到请求；「好的」打开该伙伴衣柜，多选取物核算数量与负重。选择「稍后再说」五分钟内不再提示，途中敌袭中止。
9. 行动途中保存 → 读档，确认清理旧目标并重新安排；进入另一存档后个人规则、收藏与人物不串档。

安装记录：1.5.0 完整包 CompanionManager-1.5.0-fulltest-20260913-174357 已更新到本机 MO2 的原同行目录，逐文件 SHA-256 校验通过；旧版本备份位于 MO2/companion-manager-backups/20260913-174403。安装时 SkyrimSE 未运行，未更改 MO2 配置或提交 Git。


## 1.5.1（2026-09-13）

- 取物模式点击整张卡片选择 / 反选；右上角 30px 标记与卡片高亮同步，不可取走物品无选择标记。多件物品选中后提供数量输入，保留服务器端负重与穿戴 / 任务保护。
- 人物详情顶栏增加「解散随从」确认入口，名册详情对应「重新入队」；行为管理通用设置入口统一命名。解散保留名册、收藏和个人设置。
- 本机 Skyrim.esm 条件核对：DialogueFavorGenericFollowBranchTopic（000B0EE6）检查 CurrentFollowerFaction=0、PotentialFollowerFaction=1、PlayerFollowerCount；原版 SetFollower 通过别名添加当前随从阵营，清空别名会移除。DLL 对该入口和雇佣 / 重新雇佣入口（000BCC84、00104F1A、00104F1B）前置 GetPlayerTeammate=0 的 AND 条件；原有条件链保持不变，不把人物加回原版随从阵营。
- Release DLL、TypeScript / Vite 构建通过；网页 20 项测试通过。浏览器确认不可取走卡片的选择标记数量为 0，点击附魔皮甲选择 / 反选，取走 3 铁锭后库存 12 → 9、玩家负重 220 → 223。
- 游戏待复测：重新启动 SKSE，确认日志出现 Recruitment dialogue teammate guards installed；已在队 / 等待中的普通随从不再出现招募选项，解散后可重新招募，第二位新随从仍能通过对话招募。未运行游戏验证这些对话状态。


## 1.5.2（2026-09-13）

- 「伙伴衣柜」改为「伙伴库存」，卡片与筛选统一显示锁定状态。界面和原生 favorite 指令均移除仅装备可锁定的限制；沿用已有 favorites 持久化记录和售卖保护，不清空旧收藏。
- 药剂、食物、材料、杂物等库存记录都可锁定 / 解锁；堆叠记录整组保护。穿搭候选仍限定护甲 / 服饰，锁定其他物品不会加入换装。
- Release DLL、TypeScript / Vite 构建通过，21 项网页测试通过，新增药剂 / 食物 / 铁锭整组锁定与解锁测试，确认数量不变。
- 游戏待测：锁定一组药剂和食物后进对应商店，确认随从出售其他未锁定商品而保留锁定物品；保存读档检查状态仍在，解锁后允许出售。


## 1.6.1 移除饮食系统（2026-09-13）

- TypeScript / Vite、Release DLL、Papyrus 编译通过，网页 21 项测试与 ESP 5 项结构测试通过。ESP 不再包含水袋、配方或休息 AI 包。
- 清理测试执行实际 retired_needs.inc：验证 FormID 重映射、未加载人物延后处理、仅返还记录减益、资源当前值不增加、重复执行不重复返还、拒绝异常与重复数据。
- 游戏待测：加载 1.6.0 独立测试存档（保留原备份），检查魔力 / 体力上限与移动速度的本模组减益已解除；保存并重载后不会再次增加。原本休息的伙伴应保持等待，点击跟随后正常出发。
- 游戏待测：等待一天后不再消耗需求、食物或金币，不再出现饮食 / 休息请求；商店仅进行原有售卖，锁定食物仍被保留。水袋配方不再出现，旧自有水袋随物品记录移除。
- 浏览器检查：伙伴卡片每张三条资源进度条；侧栏与行为管理无饮食入口；概览、库存锁定与字体设置仍可使用。

界面调整验证：概览三个快捷按钮使用金橙 / 玫红 / 蓝绿配色；预览中等待与继续跟随双向切换成功，解散与设置居所确认框正确显示角色与操作，取消不改变人物。Web 构建与 21 项测试通过。

## 1.6.2 对话交易回归

- 本机 Skyrim.esm 的 17 条正常交易响应核对通过：均使用独立的 CurrentFollowerFaction == 1 条件，脚本均对 akSpeaker 调用 OpenInventory，不依赖单人招募别名。另有一条特殊响应 0002CCC5 调用 RemoveAllItems，明确排除。
- 对话条件测试直接执行修复函数，覆盖 32 组阵营 / 队友 / 语音 / 任务组合，拒绝已有 OR 链、反向、别名、全局值或目标切换条件，重复调用不会再次插入。原生五个测试目标显式启用 assert 并全部通过；Web 21 项测试与构建通过。
- 游戏待测：重新启动 SKSE，在队及等待中的已管理随从应出现交换物品选项，并能打开 SkyUI / 原版交换界面、双向转移。解散后不因同行名册而保留该选项；两位随从仍能依次对话招募。无需解散再招募来刷新修复。

## 1.6.3 界面加载

- 现场日志：22:55:19 Meridian ModSchemeHandler 对 assets/index-B5Mxqt5o.js 报 404，磁盘文件存在；游戏框架启动时间 22:53:40 早于界面复制时间 22:53:43。与游戏启动期间 MO2 映射未纳入新资源的情况吻合。
- 网页默认 html/runtime 为 game，底层透明无需依赖业务脚本初始化；仅 demo 模式显示浏览器预览背景。
- 安装前检查 SkyrimSE / skse64_loader 均已退出，完整复制并验证资源哈希。游戏待测：从 MO2 重新启动、打开面板，确认资源 404 消失，面板外可见游戏，面板内按不透明度混合显示。

## 1.6.4 主动询问崩溃（2026-09-14）

- 11:24:42 日志的主调用栈为 CompanionManager → Skyrim 51420+0x136 → 10979+0x43，R15 为 ActivityAnswer，非法地址为 0x2FE1AC81A。运行 DLL 与本地 1.6.3 DLL SHA256 均为 5EF5670796E31FD26C4D02F44264CA5471A2DAD2F220BEF644205B8364BF8E56。
- 对本机 SkyrimSE 1.5.97 反汇编确认：+08AB180（51420）从第六个参数开始逐项读取按钮指针直到空指针，+08AB2B1 将读取结果传入 BSString::Set_CStr；原调用缺少结束标记。该入口还会把第二个参数包装为函数指针回调（+08AC7E0 间接跳转），不能传 IMessageBoxCallback 对象。
- 新路径通过 UIMessageQueue 工厂创建 MessageBoxData，使用按钮数组与 BSTSmartPointer 回调。+08AB5C0（51422）的返回值确认代表是否接管消息；排队被拒绝时由本地释放。保留原版消息队列优先级检查。
- activity-prompt-test 执行生产消息构造代码，使用引擎接口替身验证两个中文按钮、文字所有权、确定 / 稍后响应传递、取消映射、回调寿命，以及队列拒绝 / 工厂失败 / 单例不可用时无泄漏。这不替代游戏内引擎验证。
- Release DLL 和 TypeScript / Vite 构建通过，六个原生测试目标（含新增 activity-prompt-test）和 21 项网页测试全部通过；git diff --check 通过。
- 游戏待复测：爱拉接近满负重且玩家有空余时，关闭面板等待求助，分别选择「好的」「稍后再说」及取消；打开对应伙伴库存且可继续取物。允许自动穿搭后同样验证建议询问。连续打开 / 关闭面板和保存读档后观察是否正常，日志应出现 Activity prompt actor=… kind=carry/outfit queued=true。

## 1.6.5 库存分类（2026-09-15）

- 分类顺序参考 SkyUI 的库存分类定义：https://github.com/schlangster/skyui/blob/master/src/Common/skyui/defines/Inventory.as 。新增 inventoryCategory 快照字段，保留拾取行为使用的 category 位掩码。
- Release DLL、TypeScript / Vite 构建通过，24 项网页测试通过。覆盖食物 / 药剂分离、箭矢 / 杂物分离、护甲 / 首饰归类、其余分类、组数计数、搜索与锁定交集、旧快照可读及未知类型拒绝。
- 浏览器：食物分类只显示苹果派，叠加仅看已锁定后正确为空；选中苹果派后切到药剂仍显示已选 1 件 / 0.5 负重。18px 字号下在 1280px 与 1048px 视口检查布局，分类文字无额外字号覆盖，按钮 scrollWidth 与 clientWidth 相等；测试后恢复视口。
- 游戏待测：重新启动 SKSE，进入伙伴库存逐类核对真实物品，重点检查药剂 / 食物、卷轴、钥匙和箭矢；确认锁定与跨类取物仍正常。


## 1.7.0 魔法与换装回归

- 从左侧进入魔法管理并选择正确伙伴；切换伙伴后清空法术搜索与学派筛选。
- 已知法术有消耗条，零法力、零消耗、消耗超过最大法力均正常显示；滑动开关发出禁用 / 恢复指令，忙碌时不可重复点击。教学确认绑定原伙伴，成功才扣一本书。
- 新存档和旧存档：同行在队 / 等待同伴有「随机换装」，离队 / 未管理 / 战斗人物没有该入口。无声响应结束后换装，连续点击不重复排队。
- 手动优先未穿戴服饰，其中优先锁定；没有锁定时从普通服饰选择。不得穿入槽位冲突装备、任务服装或不可玩服饰。
- 有可替换衣服时避开当前同优先级搭配；无可替换服饰时提示且不脱空身体、不增加物品。
- 对话后死亡、解散、远离、进入剧情 / 战斗，或请求未执行前读档：不得对过期人物执行换装。
- 换装后进战斗不恢复原装备；保存 / 读档不恢复战斗装备预留；库存「试换一套」与对话手动选择范围一致，定时自动换装仍只用锁定服饰。


## 1.7.1 对话初始化回归

- 结构测试必须验证对话任务包含 Has Dialogue Data、启动标志、无别名且独立于控制任务，DIAL / DLBR 指向同一对话任务。
- SEQ 任务清单必须与 ESP 中所有 Start Game Enabled 任务一致；包与安装验证必须拒绝缺失 SEQ 的输出。
- 升级既有 1.6.x / 1.7.0 存档，确认名册与别名不被重置；CMOutfitDialogueQuest 运行，随机换装入口对已管理在队同伴出现。
- 日志 Outfit dialogue 的 managed / teammate / modeFaction / questRunning / conditions 均应为 true，infos 应为 1；未纳入同行的队友保持不显示。
- 新存档确认 SEQ 初始化；手动 / 等待同伴换装按上述清单回归，战斗不切装按 1.7.2 清单回归。

## 1.7.2 移除战斗换装联动回归

- 加载带有 `casual=true`、`battleOutfit` 的旧存档：名册、收藏与换装计时保留；原战斗装备不再占用受保护槽位，允许同槽位备用服饰替换。
- 连续手动随机换装、库存「试换一套」与定时自动穿搭：不创建战斗装备预留；手动优先未穿戴、其次收藏；自动穿搭仍仅选择收藏服饰。
- 换装后进入 / 退出战斗，以及保存再读档：本模组不恢复旧穿搭；游戏或其他模组的自主装备行为另行核查。
- 换下的普通装备可以取走，符合出售规则时可自动出售；收藏、穿戴、任务及不可玩物品的既有保护继续生效。
- 原版战斗检测、战后拾取等其他行为继续正常工作。

## 1.7.3 人物概览按钮布局回归

- 在队人物概览顶部仅显示「等待」「解散」「设置居所」，三个按钮位于同一行；等待后「继续跟随」、离队后「重新入队」状态保持三列布局。
- 左侧魔法管理入口可正常打开，伙伴选择与法术操作正常。

## 1.7.5 手动换装回归

- 当前衣服已收藏、同槽位备用衣服未收藏：手动换装应尝试备用衣服；自动穿搭仍仅用收藏服饰。
- 多件未穿戴服饰同时可用：优先收藏，槽位不冲突；任务与不可玩服饰继续受保护。
- 无候选、槽位受保护、仅当前搭配、全部穿戴未确认及部分成功分别显示对应结果；已穿戴的旧物品不计作本次成功。
- 在修颜处通过对话与库存按钮各试一次，检查日志中的 Outfit request/item/equip/result；编译及规则测试不代替游戏内验证。

## 1.7.6 换装确认回归

- 请求后先提示正在确认；跨帧确认完成或 2 秒后报告成功、部分成功、未确认，确认期间连续点击不重复派发。
- 确认期间读档、解散、人物卸载：丢弃旧请求，不对过期人物执行装备操作。
- 修颜再次测试后查看 Outfit delayed/final/still worn/model 日志，核对实际穿戴与外观；不得仅凭编译通过认定游戏问题已解决。

## 1.7.7 连续换装回归

- 手动换装 A → B → A，确认每次同槽位服饰可替换，日志中新穿戴服饰 removalLocked=false。
- 旧存档中已穿戴普通服饰带 ExtraCannotWear：手动选中同槽位替代品时记录 Outfit unlock；无替代品、未穿戴、任务、不可玩服饰以及自动穿搭不清除已有锁。
- 收藏状态、物品数量、附魔与强化保持；读档后再次换装验证修复持久化。继续使用延迟确认判断穿戴结果。

## 1.7.8 招募交接回归

- 正常原版招募后退出对话，确认自动纳入且原版人类随从名额释放，再招募第二人。
- 已管理在队／已离队人物残留原版槽位：释放槽位并分别保留其状态，不把已离队且非队友的人物自动重新入队。
- 原版槽位为空且计数为 1：有本模组有效绑定时修复，缺少绑定时只记录；另一人物占用或计数为 2/负数时不得清零。
- 原版对话重新招募已登记离队人物：恢复在队并释放原版名额；面板解散占用原版槽位的人物先交接再结束队友状态。
- 对话期间、解散进行中、脚本属性被其他框架更换、读档／跨存档不得误清其他角色或动物槽位。
- 阿加莎、Aisha 依次验证；若仍拒绝，检查 Recruitment state 及交接提示，不能仅凭自动化测试认定存档已修复。

## 1.8.2 命名窗口生命周期与归属

- 从随从 A 的对话保存，检查默认名和提交归属均为 A；保存或取消后切换 B，不得自动重开。手动保存 B 时默认名属于 B；离开再进入穿搭不得自动弹出。
- 对话请求先到、目标随从快照后到时，保持等待，不允许用名册第一位随从替代。切换存档后旧请求失效。
- 身体/靴子穿戴多槽位服饰时两格同时有亮色边框和「已穿戴」文字；卸下后取消标亮，与当前选中格的背景区分。
- 浏览器自动回归：启动 `npm run dev -- --port 5187`，配置 `PLAYWRIGHT_MODULE` 为 Playwright 安装路径，执行 `node tests/outfit-dialogue.browser.cjs`。

## 1.8.1 穿搭独立导航与卸装

1. 左侧「伙伴穿搭」直接打开独立页面，伙伴库存不再嵌套穿搭页签。对话的指定部位与保存当前套装打开正确随从的独立面板。
2. 在指定部位卸下单槽位 / 多槽位服饰，检查影响范围、实际卸下状态和其他无关装备不变；空槽不显示卸下按钮。任务装备不可卸下，重复或失效请求被拒绝。
3. 卸下普通库存未显示的真实穿戴实例，确认未增减物品数量；若游戏自动穿回，应提示未完整确认，不可假报成功。
4. 套装装备网格放入长中文名和连续英文名，核对完整换行、不裁切，缺失与穿戴状态仍清晰。

## 1.8.0 衣橱、套装与二级对话

1. 加载完整安装包，从随从对话选择「穿搭调整」，确认父项不执行换装，二级只有整套随机、指定部位、保存当前套装。指定部位打开正确随从的穿搭部位页；保存打开该随从的默认名称输入框。
2. 选择身体 / 靴子槽位，确认同一多槽位装备同时可见且标明影响范围。点击直接穿戴与下方随机按钮都必须经穿戴确认；任务、不可玩装备与皮肤冲突不能被替换。
3. 保存当前套装，确认武器、盾牌、弹药排除，服饰全部收藏；同名命名被拒绝，取消不增加套装。换另一个随从后不出现前者的套装。
4. 选择当前套装只显示随机按钮；选择保存套装只显示使用按钮。暂时取走一件套装物品后使用，缺件槽位保持现有装备；同基础物品不同附魔不能被当作原实例。多槽位冲突允许替换它占用的部位。
5. 在设置中分别设为 0%、100%，验证重新组合 / 已保存套装两条路径；没有保存套装时即使 100% 也可重新组合。保存、退出、重进游戏后核对概率和各随从套装。修改加载顺序后核对实例重映射；卸载服饰来源插件后缺失条目不得指向别的插件物品。
6. 对库存未显示但真实穿戴的服饰，确认当前套装能显示标记、保存后收藏，且不改变物品数量或混入出售列表。换装确认期间禁止重复换装及保存。

自动验证：前端快照/模拟回归、原生部位与概率边界、ESP 链接和子对话脚本检查。浏览器验证真实 React 面板中的多槽位穿戴、命名保存、套装按钮切换、对话部位/保存事件；游戏内步骤仍需实测。

## 1.7.9 隐藏穿戴实例回归

- 修颜连续手动换装：查看 980636F9 的 Outfit raw worn，核对 inventoryCount、visible、removalLocked；若存在原始穿戴实例且受旧锁限制，应产生 Outfit unlock，备用身体衣服随后能被确认穿上。
- 旧随从隐藏靴子同样验证，不依赖任何特定 FormID；库存超过面板 512 条上限时，旧穿戴锁与受保护槽位仍被完整扫描。
- 隐藏任务、不可玩及皮肤记录保持保护；自动换装不得清除已有锁，无同槽位替代品时不得解锁。
- 换装前后物品数量、附魔、强化和收藏保持；没有真实穿戴实例、仅存在模型的条目只记录，不生成、删除或转移物品。
- 保存读档后再次换装；面板数量异常条目不因这次修复变成可出售／可取走的普通库存。
