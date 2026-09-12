# Sky Backgrounds 0.2.1

上古卷轴 5 SE 主菜单与加载背景管理器。主菜单每套效果放在一个文件夹中，每次通过 SKSE 启动时等概率随机选择一套。另有独立的加载画面库和桌面预览窗口。不依赖 PrismaUI；主菜单功能不需要 ESP，加载画面功能使用 sky-backgrounds-loading.esp。

首版针对 Skyrim SE **1.5.97**，需要匹配的 SKSE64，以及 Microsoft Visual C++ 2015–2022 x64 运行库。安装包不包含背景作品，现有资源的迁移和筛选另行进行。空资源库保持原有主菜单。

## 安装与目录

使用 MO2 安装 `packaging/sky-backgrounds-0.2.1-mo2.zip`。压缩包根目录直接是 Data 的内容，不要额外套一层 Data。

```text
MO2/mods/MainMenuManager/
├─ SKSE/Plugins/
│  ├─ MainMenuManager.dll
│  └─ MainMenuManager.json
└─ MainMenuManager/
   ├─ backgrounds/
   │  ├─ 雪山晨曦/
   │  │  ├─ theme.json                  可选名称与启用状态
   │  │  ├─ preview.jpg                 可选，供人工浏览或将来的管理界面使用
   │  │  └─ Data/
   │  │     ├─ meshes/interface/logo/logo.nif
   │  │     ├─ textures/interface/objects/mainmenuwallpaper.dds
   │  │     ├─ meshes/interface/intmenufogparticles.nif   可选
   │  │     └─ Music/Special/mus_maintheme.xwm            可选
   │  └─ 极光之夜/
   │     └─ Data/...
   └─ tools/New-ImageTheme.ps1
```

从游戏可见的 `Data/MainMenuManager/backgrounds` 扫描，不写死 MO2 安装位置。Windows 中文路径受支持。只扫描一级主题；一个文件夹只放一套效果，安装器中的 V1/V2 应分别整理为主题。BSA 须先提取，首版不读取包内主题。

每套必须有 `Data/meshes/interface/logo/logo.nif` 和至少一个 DDS，并保留模型引用的全部纹理及原始相对路径。管理器只复制以下资源：

- `meshes/interface/logo/logo.nif`、`logo01ae.nif`。
- `meshes/interface/intmenufogparticles.nif`。
- `textures/` 下的 `.dds`。
- `Music/Special/mus_maintheme.xwm` 或 `.wav`，同套不能两者并存。

其余文件跳过并记录。资源头验证可以发现损坏签名或明显格式错误，但不替代 NIF/纹理引用检查及游戏内验证。单套上限为 1 GiB、2048 个资源；目录联接和符号链接不受支持。

`theme.json` 可省略（默认使用文件夹名称、启用）：

```json
{ "name": "雪山晨曦", "enabled": true }
```

添加文件夹后下次启动参与随机；相邻两次允许抽到同一套。移走文件夹、添加空的 `disabled.txt`、设置 `enabled: false`，或把文件夹名改成下划线开头，都可移出随机池。关闭游戏后再调整资源。`_example` 是禁用的目录示例。

## 自己生成的新图片

普通 PNG/JPG 需要配套主菜单模型，不能只改后缀为 DDS。附带离线工具：以一套已验证的静态背景为模板，保留模型/效果/音乐，把自己的图片转换成 DDS，再生成一个新主题。

模板必须使用 `textures/interface/objects/mainmenuwallpaper.dds`，且 `logo.nif` 引用该路径。工具不含第三方模板；以后整理资源时可选定一套适合自己分辨率的模板。

```powershell
.\tools\New-ImageTheme.ps1 `
  -ImagePath 'D:\我的图片\极光.png' `
  -TemplateDirectory 'D:\背景模板\静态16比9' `
  -OutputDirectory 'D:\背景库\极光之夜' `
  -Name '极光之夜'
```

把输出文件夹放进 `backgrounds`，或把输出路径直接指向其中一个尚不存在的新文件夹。工具不覆盖已有主题，不改模板。图片按模板尺寸居中裁剪，保持比例；输出为无压缩 BGRA DDS（4K 约 32 MiB），同时生成预览图。不需要 Python 或额外图片转换器，使用 Windows PowerShell/.NET System.Drawing。导入失败留下 `disabled.txt`，半成品不会参与随机。

## 预览与筛选窗口

双击 `MainMenuManager/开屏背景管理器.exe`。这是独立的 Windows 桌面窗口，使用系统已有的 .NET Framework，不需要启动游戏、Python 或浏览器服务。

- 左侧浏览缩略图，右侧查看大图；双击缩略图可放大，Esc 返回。
- 搜索名称或目录编号；分类可以切换可用、待确认、已停用、已删除。
- Ctrl / Shift 多选；点击“删除选中”或按 Delete，会把整个主题移动到同级的 `deleted-backgrounds`，立即移出随机池。
- “撤销删除”或 Ctrl+Z 恢复最近一次删除；“已删除”分类支持选中后恢复，重新打开程序仍可恢复。
- 恢复时遇到同名目录会保留两边，不覆盖。原始迁移来源、旧模组和 BSA 均不受影响。删除/恢复要求 Skyrim 已退出。
- 此处删除是可恢复的移除，不会释放磁盘空间；没有提供永久删除按钮。

窗口读取主题内的 `preview.jpg` 或 `theme.json` 的 previews 列表；如果同目录有 `preview-large.jpg`，大图优先使用它。没有预览图的主题仍能管理。迁移库已额外生成 279 张高分辨率预览。普通 DDS 的空白边仍按纹理原样显示；预览不模拟模型动画、烟雾和音乐。

## 与旧模组及 MO2 配合

### 独立加载背景库（0.2）

```text
MainMenuManager/
├─ backgrounds/                       主菜单，每次启动选一套
├─ loading-backgrounds/               读档 / 过门 / 快速旅行画面
│  ├─ _system/                        插件模板、来源与校验记录
│  └─ 001_画面编号/
│     ├─ theme.json                   名称、enabled、预览信息
│     ├─ records.bin                  原始 LSCR 与对应 STAT 记录
│     ├─ assets.json                  模型/贴图路径、大小、SHA-256
│     ├─ preview.jpg / preview-large.jpg
│     └─ Data/meshes/...、textures/...
└─ deleted-loading-backgrounds/       加载画面的独立可恢复删除区
```

窗口顶部切换“主菜单背景”和“加载背景”。加载画面保留原 ESP 的显示条件、文字和位置设置，由游戏在加载时选择，不会每次启动固定一张。未覆盖游戏或其他模组的全部加载画面。

删除、恢复加载主题会自动重新生成模组根目录的 `sky-backgrounds-loading.esp`，保留原 FormID，只输出启用主题的 LSCR/STAT。同步失败会回滚本次目录移动。游戏运行时禁止应用。手动添加/移走完整主题或修改 `enabled` 后，点击“同步加载库”，下次启动生效。退出程序后筛选结果仍保存在目录和 ESP 中。

首次导入将所需 NIF/DDS 复制至模组根目录的 meshes/textures，供游戏读取。已移除主题的部署副本保留，以便恢复及避免中断时缺失资源；可恢复删除不会释放空间。原模组资源保持原样。外部修改已部署文件或生成的 ESP 时，管理器拒绝覆盖。主菜单库与加载库各自拥有独立删除区。

当前适配本地 `界面模组-加载屏幕-v1.3 Main Files`：主文件只含 Skyrim.esm 主依赖和独立 LSCR/STAT 记录。新的加载主题必须有独立 FormID、完整配套资源与清单；不支持把普通图片直接放入或任意 ESP 合并。安装包不附第三方记录/图片；首次本地导入使用开发工具 `tools/migrate_loading_backgrounds.py`，生成预览时需要 Pillow，桌面管理器日常使用不需要 Python。

确认导入后，在 MO2 保持 `sky-backgrounds-loading.esp` 勾选，停用旧加载模组及 `SDLoadingScreens.esp`，避免重复加载两套记录。原记录编号保留；0.2.1 将生成插件改为统一的 sky- 系列命名。加载功能无需修改主菜单 DLL。实机读档、过门显示仍需验证，图片预览不模拟 NIF 显示变换。

加载库的停用：可以把所有加载主题移至已删除并同步，此时生成的插件不含自定义画面；恢复主题可重新启用。不要删除 `_system`。主菜单 DLL 的停用/恢复流程见下文。

### 主菜单兼容与恢复

首次使用前，应禁用旧的 Main Menu Randomizer **插件**。如果旧模组同时包含要保留的基础资源，可以在 MO2 中隐藏其 `SKSE/Plugins/main_menu_randomizer.dll`，资源迁移则稍后处理。新管理器在可见 Data 中检测到该 DLL 或 `MainMenuRandomizer.dll` 时不改资源，日志说明冲突。

运行时通过 MO2 的虚拟 Data 写入资源。MO2 可能将已有路径的修改导向原提供模组，将新文件导向 overwrite；本模组不能保证全部输出都落在自己的安装文件夹。不要手动清空恢复记录或把它与所属资源分开移动。使用独立测试配置验证后再投入日常配置。

切换前先恢复上次覆盖的原文件，然后应用新主题，因此可选音乐、烟雾或额外纹理不会从上一套残留。原来仅存在于 BSA 的资源无需解包备份；恢复时移除本模组创建的松散覆盖，让游戏重新使用原有包内资源。

恢复记录、原文件备份和选中资源暂存位于游戏可见的 `Data/MainMenuManager/state`，不属于背景库。复制前写入日志式恢复清单；中途失败会尝试回滚，下次启动再次恢复。已被其他模组或用户修改的目标不会被自动覆盖，检测到 SHA-256 不匹配时停止并保留备份。每次正常恢复完成会清理对应备份。

**停用/卸载流程**：保持 DLL 启用，把 `SKSE/Plugins/MainMenuManager.json` 改为 `{"enabled": false}`，通过同一个 MO2 配置启动一次，检查日志中出现 `Disabled; previous resources restored`，退出后再禁用/卸载。直接删掉 DLL 会留下最后应用的松散资源。空背景库也会触发原资源恢复。

日志：SKSE 日志目录中的 `MainMenuManager.log`，通常位于 `Documents/My Games/Skyrim Special Edition/SKSE`。内容包括有效主题数量、选中主题、跳过原因、恢复结果及冲突。

## 开发与验证

使用 Visual Studio 2022 C++ 工具链和 xmake；复用仓库 `reference/example-skse-plugin/lib/commonlibsse-ng`。构建不会安装到游戏目录。

```powershell
cd native
xmake f -m release -y
xmake build -y MainMenuManager
xmake build -y MainMenuTests
xmake run MainMenuTests
cd ..
powershell -NoProfile -File tools/Test-ImageTheme.ps1
powershell -NoProfile -File browser/build.ps1
powershell -NoProfile -File packaging/package.ps1
```

原生测试覆盖目录识别、中文名称、随机池、切换后的可选资源恢复、空库、禁用、旧插件冲突、中断恢复、复制失败回滚、外部修改保护及恢复清单校验。测试仅使用 build 下的独立文件夹。

发布前的游戏内检查：在独立 MO2 配置放入两套有效主题，禁用旧随机插件，通过 SKSE 启动，确认日志与显示一致；多次重启检查选择；从有音乐/烟雾的主题切到不含对应资源的主题；最后测试关闭配置开关后的恢复。自动测试不能证明主菜单渲染、其他界面模组以及 MO2 文件重定向兼容性，当前版本仍需此项实机验证。

## 命名规范（0.2.1）

系列前缀为 `sky-`，模组标识为 `sky-backgrounds`，功能插件采用 `sky-<模组>-<功能>.esp`：本模组为 `sky-backgrounds-loading.esp`。MO2 显示名称为 `功能模组-开屏与加载动画-sky-backgrounds`。内部资源目录 `MainMenuManager` 和主菜单 DLL 的名称保持兼容。

从 0.2.0 升级时，先关闭游戏和管理器，备份并将新管理模组根目录中的 `SDLoadingScreens.esp` 重命名为 `sky-backgrounds-loading.esp`，再更新预览程序。在 MO2 取消旧插件并启用新插件；不要同时启用两个文件名。本次重命名面向新档，其他未使用新管理模组的 MO2 配置不做变更。
