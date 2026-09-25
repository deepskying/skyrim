# Inventory Manager

Inventory Manager 0.2.0-meridian is an experimental Meridian UI panel for the player inventory and magic lists, targeting Skyrim SE 1.5.97.

Requires Meridian UI 1.5.0, matching SKSE64, and Address Library. Other mods may continue to require PrismaUI; keep it installed for those mods. This plugin queries PrismaUI only to avoid opening while an existing Prisma panel owns focus.

This is the first migration prototype, not a claim of completed in-game validation. See [TESTING.md](TESTING.md).

## Current controls

- **Shift+D** — open or close the panel (configurable in `packaging/InventoryManager.ini`).
- **Alt** — switch inventory and magic tabs (configurable in **快捷键配置**).
- **Left / Right** or **A / D** — switch category.
- **Up / Down** or **W / S** — switch selected row.
- **F** — toggle the selected item's favorite state.
- **Enter** or a left mouse click — equip the selected weapon, armor, scroll, spell, or shout; use a potion or food item.
- **/** — focus search.
- **Esc** — close.

## Shortcut configuration

The third top-level tab, **快捷键配置**, can rebind the panel, favorite, default-action, list-type toggle, and search shortcuts. Click **重新绑定**, then press a key combination. The setting takes effect immediately and is persisted in `InventoryManager.ini`.

WASD and arrow navigation remain fixed so the panel always has a safe way to navigate. Supported bindings are letters, numbers, F1–F12, Tab, Enter, Space, and Slash.

## Install layout

The final package must place files at these locations:

```text
Data/SKSE/Plugins/InventoryManager.dll
Data/SKSE/Plugins/InventoryManager.ini
Data/MeridianUI/inventorymanager/index.html
```

The compiled `web/dist` contents belong in `Data/MeridianUI/inventorymanager/`.

## Build and package

From `web`, run `pnpm install` once and then `pnpm run build`. From `native`, run `xmake f --skyrim_vr=n -m release` followed by `xmake build -y`.

After both builds, run this from the repository root to create an install-ready `packaging/release/meridian/Data` tree:

```powershell
.\mods\inventory-manager\packaging\package.ps1
```

The generated `InventoryManager-0.2.0-meridian.zip` can be installed in MO2 or Vortex. Disable the older InventoryManager package in the chosen profile, because both versions use the same DLL/ESP names.

For this workspace's MO2 installation, `packaging/install-local.ps1` creates a separate `物品清单-Meridian测试` profile and a separate test mod. It keeps the source profile and older mod folders unchanged, enables Meridian, disables old InventoryManager entries only in the test profile, and copies the latest local save/co-save for isolated testing. It refuses to overwrite an existing test profile or mod.

## First implementation scope

- The inventory page reads the player's items, actual count, weight, value, favorite/equipped/enchanted/quest markers, and the agreed categories.
- The magic page reads base and learned spells, dragon shouts, powers, passive abilities, and live active effects. Schools are classified from the game data.
- Magic favorites and spell/shout equipping use Skyrim's native managers. Inventory favorites, equipping, using, and dismantling are available through their native game systems. Equipment state is refreshed again on the following frame so the UI reflects Skyrim's final slot-conflict result.

## 面板能力

启用随包提供的 `InventoryManager.esp`（ESL 标记），进入新游戏或成功读档后自动获得「打开物品管理」。在魔法菜单的能力分类中装备，按能力键释放；可以加入收藏。能力零消耗、无每日次数限制，与现有快捷键打开同一个面板。各模组独立安装，无需额外 Papyrus 脚本。

如只使用快捷键，将 `SKSE/Plugins/InventoryManager.ini` 的 `[PanelPower] Enabled=0`，下次读档会移除该能力；改回 `1` 后读档可恢复。更新安装时请同时更新 DLL 和 ESP，并在 MO2 右侧插件列表启用 ESP。

## Model preview prototype

- Weapon and armor selections show their world/inventory NIF in the right-hand viewport. Armor uses the player's sex-specific world model, with the other sex as fallback; this is not actor try-on.
- Drag with the left mouse button to rotate, use the wheel to zoom, and choose 重置视角 to reset.
- Loading, failed, missing and unsupported models keep a readable icon fallback. Magic and other categories retain their existing details.
- Geometry comes from Meridian's separate native GPU surface, positioned over a reserved HTML rectangle. The surface does not intercept input; Chromium owns the pointer controls. The remaining details scroll independently.
- All CEF requests are copied and queued onto Skyrim's task thread. Closing the panel or beginning a load clears the model, invalidating pending native loads. Reopening requests a fresh preview.
- The migration uses `Meridian.View/1`, `Meridian.RenderLayer/1`, and `Meridian.NifView/1`. Public headers are pinned under `native/src/MeridianUIAPI`.
- Inventory rows still aggregate by base FormID. Instance-specific enchantments/tempering and complete actor rendering are outside this prototype. Base record texture-swap fidelity also requires further work; the first preview passes a NIF path.
- Meridian focus coordination covers Meridian consumers. The one-way Prisma focus check here does not establish shared focus ownership across the two frameworks; test coexistence in game.
