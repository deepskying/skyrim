# 修改版副本声明 / Modified copy notice

**本目录不是官方发行版，而是修改过的 Meridian UI 1.5.0 源码。**

| 项 | 值 |
| --- | --- |
| 上游 | https://github.com/heathbrownkeyworks/MeridianUI |
| 基础版本 | `5707877322c85a1bd1c2e3309487f266d0647ca9`（Release 1.5.0） |
| 修改日期 | 2026-09-25 |
| 修改内容 | ① NIF 预览在跨设备共享纹理不可用时改用游戏设备渲染（`src/UIPlatform/Render/NifPreviewRenderer.cpp` 一处条件，补丁见 `patches/`）；② 新增本声明与 `FORK-NOTES.md` 的其余说明。除此之外与 1.5.0 源码一致。 |
| 许可 | 实现部分 **GPL-3.0-or-later + EXCEPTIONS.md 的额外许可**；`src/UIPlatform/MeridianUIAPI/*.h` 为 **MIT**。完整文本见 `LICENSE`、`LICENSING.md`、`THIRD_PARTY_NOTICES.md`、`LICENSES/`。 |

Meridian UI 是 `GPL-3.0-or-later`（含附加许可）。本副本随其许可文件一并分发；
若要把**编译产物**发给他人，按 GPL-3 提供对应源码即可——本目录就是该对应源码。

## 维护与基线

| 项 | 值 |
| --- | --- |
| 本副本所在 | `skyrim/mods/meridian-ui`（本仓库，纳入版本管理） |
| 用于同步上游的克隆 | `C:\Users\linos\Desktop\github\MeridianUI`（保留 git 历史与构建目录） |
| 上游同步分支 | `codex/game-device-nif-fallback`，补丁提交 `60c78fb` |
| vcpkg 克隆 HEAD | `079cc332295fdf4f9e6d486827be14f0ca407b96` |
| vcpkg 基线 | `9e593bb18ea69cc5095e012465dcd675a822ed0d`（`vcpkg-configuration.json`） |

## 本地补丁清单

### 1. `60c78fb` NIF 预览在共享纹理不可用时改用游戏设备

- 文件：`src/UIPlatform/Render/NifPreviewRenderer.cpp`（`InitializeGraphics` 一处条件）
- 原因：`RenderDevice::Create` 已经探测出共享键控纹理不可用（`SupportsSharedKeyedTransport()` 为 false），
  浏览器层据此降级 SyncCopy，但 NIF 预览仍初始化 `FrameTransport`，于是本机每次预览
  `scene composition failed ... (0 shapes skipped)`，面板显示"模型加载失败"。
- 改法：探测不可用时改用游戏设备延迟上下文（DXVK 已在用的路径，`SubmitDeferredFrame` 以
  `ExecuteCommandList(commands, TRUE)` 恢复游戏管线状态），全程不需要共享句柄。
- 验证：本机 ENB 开启下实测通过（`MeridianUI.log` 出现新增回退日志，`scene composition failed` 归零）。

## 构建（可复现）

```powershell
# 前置：Visual Studio 2022（含 C++ 桌面工作负载）、git、vcpkg 克隆
# 在本目录（mods/meridian-ui）执行；build/ 已被 .gitignore 忽略，不会进仓库
$env:VCPKG_ROOT = "C:\Users\linos\Desktop\github\vcpkg"
cmake --preset release -DBUILD_TESTING=OFF -DMERIDIAN_ENABLE_SIGNING=OFF -DENABLE_LTO=OFF
cmake --build build/release --config Release --parallel 16
# 产物：build/release/dist/Release/Data/MeridianUI/MeridianUI.dll
```

需要 VS x64 工具链环境（`vcvars64.bat`），且 `VCPKG_ROOT` 要在 VS 环境之后重新设置：
Developer PowerShell / VsDevCmd 会把 `VCPKG_ROOT` 指到 VS 自带的 vcpkg，从而换掉工具链与全部依赖 ABI。
首次配置会下载 CEF 二进制包（约 250 MB）并构建依赖，约 10 分钟。

## 继续修改时的做法（避免自己和上游越走越远）

1. **每个改动一个提交**，只改必要处；能写成"探测 × 回退"这种通用形式就不要写成只对本机生效的特例。
2. 上游发新版时：`git fetch` → 在新 tag 上新建分支 → `git cherry-pick` 或 `git am` 本地补丁 →
   重跑构建与真机验证。补丁越小，这一步越省事。
3. **不要把模组业务代码混进本目录**：这里只放平台源码（GPL-3）。你自己的模组代码留在
   `mods/<模组名>/`，通过 MIT 的 `MeridianUIAPI` 头文件 + 运行期加载使用平台，
   这样两边的许可边界始终干净（同一仓库、不同许可，各自带自己的 LICENSE）。
4. 修改 `MeridianUIAPI/*.h`（MIT 部分）时要保留原版权与许可声明。
5. 改动后重跑平台自带测试（`-DBUILD_TESTING=ON`）与真机 gate 清单：
   浏览器面板显示、输入与 Alt-Tab、焦点抢占、读档/新档/关机、NIF 预览。
6. 补丁与二进制留档：`patches/` 下存上游可 `git am` 的补丁；本机归档目录
   `MO2\companion-manager-backups\meridian-nif-fix-1.5.0\`（含官方原 DLL 与自编译 DLL）。

## 与官方版的关系

官方发布是签名构建，本地构建未签名且可用 `-DENABLE_LTO=OFF` 换取更快的编译；
行为等价但二进制不同。安装时把 `dist\Release\Data\MeridianUI\MeridianUI.dll` 覆盖到
`MO2\mods\基础模组-MeridianUI\MeridianUI\MeridianUI.dll`；还原官方版从上面的归档目录复制回即可。
