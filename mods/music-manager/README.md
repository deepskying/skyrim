# 天际音乐管理器 / Music Manager 0.2.0

Skyrim SE **1.5.97** 的独立 SKSE 模组。默认 Shift+M 打开或关闭 Prisma UI 面板，快捷键可在配置面板修改；音乐在独立线程持续播放，关闭面板不影响播放。不需要 ESP、固定曲目编号或手动转码。

## 使用

- 将 MP3 放入 `Data/Music/MusicManager` 下对应的中文环境文件夹，保留原文件名。也支持 FLAC、WAV 和子文件夹。
- 游戏中 **Shift+M → 重新扫描**。面板提供搜索、试听、暂停、下一首、音量、单曲禁用和打开文件夹。
- 对应分类没有可用音乐时，默认回退到「通用」；通用也为空则保持安静。可以在设置中关闭回退。
- 音乐面板本身**不暂停游戏**，方便试听。默认随游戏暂停音乐，可在配置中关闭；回主菜单、读档、死亡时停止独立播放。
- 默认野外白天为 06:00–20:00，其余为夜晚；战斗优先于位置，龙战优先于普通战斗；酒馆和住宅优先于所在城市。
- 默认普通环境稳定 2 秒后切换，脱离战斗稳定 3 秒后切换；普通过渡 1.2 秒，进入战斗 0.35 秒。随机歌单每轮不重复，跨轮避免紧邻重复。

## 配置面板

按 **Shift+M → 右上角齿轮** 打开配置面板。

- **播放设置**：空歌单回退、随游戏暂停、跟随游戏主音量、普通与战斗淡入淡出、场景切换与脱离战斗等待、白天开始与结束时间。
- **快捷键**：选择 A–Z 或 F1–F12，可组合 Shift、Ctrl、Alt。保存后立即使用新快捷键，页脚提示同步更新。Esc 保留用于返回。
- 空歌单回退勾选后立即保存；其他项目点击对应的「保存」按钮后生效，重新启动游戏仍会保留。「填入默认值」只填写表单，需要再保存。
- 白天开始必须早于结束；支持 0–24 的整日白天。普通淡入淡出范围 0–10 秒，战斗为 0–5 秒，两项等待时间为 0–15 秒。

## 本地 DCS 迁移

四套 DCS 资源被只读导入到 `packaging/migration`。同一槽位优先使用 MP3，然后 FLAC、WAV、XWM；XWM 解码转为 FLAC，避免再进行有损编码。发现实际为 M4A/AAC 的假 `.mp3` 文件时，同样转为 FLAC。原始 MO2 文件均保留。

同分类按源文件 SHA-256 去重。同名迁移文件附加短哈希，防止 DCS 各子目录里的 `Explore01` 等互相覆盖；以后添加的歌曲不要求重命名。DCS 的 ANY 野外音乐同时加入白天和夜晚。End/Finale 短音单独保留在迁移目录的「待整理短音」，不当作完整 BGM 播放。`migration-report.json` 记录所有来源、格式备选、目标和去重结果。

| 分类 | 迁移播放条目 |
|---|---:|
| 野外白天 | 412 |
| 野外夜晚 | 351 |
| 城镇 | 34 |
| 地牢 | 150 |
| 普通战斗 | 214 |
| 龙战 | 4 |
| 酒馆 / 住宅 / 通用 | 0 |

合计 **1,165 个播放条目**，并非 1,165 首独立歌曲。源资源没有可归入酒馆、住宅和通用的曲目，这三个文件夹留空供添加。

## 依赖与安装

- Skyrim SE 1.5.97、对应 SKSE64、Address Library、Prisma UI。
- 发行 ZIP 只包含程序、界面及空文件夹，不包含个人音乐。
- `packaging/install-local.ps1` 将程序与迁移音乐复制到独立 MO2 模组，并从 `-std-` 创建「音乐管理器-测试」配置。测试配置启用新模组、停用 DCS 核心和四套旧资源，并复制最新的 ESS/SKSE 存档一对；原配置不修改。
- 在 MO2 配置下拉框选择「音乐管理器-测试」，通过 SKSE 启动，再按 Shift+M。若 MO2 未刷新新配置，关闭后重新打开 MO2。
- 本地安装器在 INI 中写入实际音乐目录，使面板的「打开文件夹」在 MO2 外的资源管理器中也能正常工作。
- 切回 `-std-` 可恢复原音乐配置。不要在游戏运行时卸载 DLL。

## 配置与实现边界

`SKSE/Plugins/MusicManager.ini`：`[Library] Path=` 留空使用 Data/Music/MusicManager，亦可指定绝对路径。中文路径的 INI 使用 UTF-16。旧的 `[Hotkey] ScanCode=0x32` 作为首次启动的 Shift 组合默认值保留兼容。

同目录的 `MusicManager.settings.json` 自动保存音量、接管开关、空列表回退、禁用曲目和 `playback` 播放参数。`MusicManager.hotkey.json` 保存新的组合快捷键，优先于 INI。MO2 可能将首次创建的设置文件放入 overwrite；这是正常的虚拟文件系统行为。

接管通过游戏默认 Music Sound Category 的衰减实现，不改玩家的音乐音量滑块、不改其他声音类别。独立播放器默认跟随游戏主音量，自己的音量通过本面板调节。关闭接管、加载存档、死亡或识别到剧情音乐时恢复原类别衰减。

剧情优先基于游戏默认死亡/成功/升级/清理音乐类型及 `MusicManager.rules.json` 内的 EditorID 和前缀。**它不能自动保证识别所有第三方剧情配乐**；可将对应 MusicType EditorID 加入 `storyEditorIDs`。未知新地点依赖地点关键词与父级地点；未标注类型的室内地点使用通用分类。

当前完成了编译、离线播放服务验证和浏览器 UI 检查。**尚未在 Skyrim 进程中验证实际音量接管、Prisma 焦点、游戏内位置识别和剧情切换**；独立测试配置用于这一步。

## 构建与验证

```powershell
# 在 web 目录
npm run check
npm run build
# 在 native 目录，要求 Visual Studio 2022 与 xmake
xmake f -p windows -a x64 -m release -y
xmake build -y MusicManager
xmake build -y MusicRulesTests
xmake build -y MusicSettingsTests
xmake build -y MusicAudioTests
xmake build -y MusicServiceTests
# 规则测试；音频测试参数为要扫描的音乐目录
build/windows/x64/release/MusicRulesTests.exe
build/windows/x64/release/MusicSettingsTests.exe
build/windows/x64/release/MusicAudioTests.exe ../packaging/migration/Data/Music/MusicManager
# 服务测试使用全新的输出目录；不输出实际声音，也不删除已有目录
build/windows/x64/release/MusicServiceTests.exe ../packaging/validation/service-new
```

音频测试逐个使用正式播放器的 miniaudio 解码器打开并读取开头 1,024 帧，验证格式和中文路径；不等同于整首试听。服务测试验证环境优先级、暂停冻结、剧情让行、加载重置、回退、禁用、重新扫描、播放配置即时生效和持久化。设置测试覆盖范围校验、昼夜边界、自定义切换等待、快捷键映射及精确组合匹配。

miniaudio **0.11.23** 源码随附于 `native/vendor`，许可证见 `LICENSE.miniaudio`。Windows 音频由原生引擎播放，网页仅用于管理，不依赖浏览器自动播放策略。
