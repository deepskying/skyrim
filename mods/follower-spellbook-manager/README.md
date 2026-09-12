# Follower Spellbook Manager

An SKSE + Prisma UI mod for Skyrim Special Edition 1.5.97. It lets the player inspect loaded followers' spells and teach them spell tomes from the player's inventory.

## Current behavior

- Press **Shift+S** to open or close the panel. The hotkey is configurable through `SKSE/Plugins/FollowerSpellbookManager.ini`.
- Click the close button or press **Esc** to close the panel from any page.
- Open to a grid of loaded player teammates. Each card shows the follower's class, level, and live health, magicka, and stamina bars before opening the detail page.
- Player-scaled followers show their current level cap on the roster card. Their detail page can raise that cap to the configured target and later restore the original value; fixed-level followers are left unchanged.
- The responsive panel uses 90% of the available viewport and a translucent blue-green theme.
- View that follower's castable spells in an independently scrolling grid, with each card showing the calculated cost and its share of the follower's maximum magicka.
- Enable or disable individual follower spells from each spell card. Disabled spells remain visible for restoration, and their state is stored in the SKSE co-save.
- Filter the list by magic school.
- Browse spell tomes in an independently scrolling grid. Each card shows its stack count, gold value, school, and calculated magicka cost.
- Hover or focus a tome to preview the game's localized spell description in the details area below; click it to select it for teaching.
- Teach the selected spell tome to the current follower.
- The tome is removed only after `Actor::AddSpell` succeeds.
- Each successful teaching is also stored in the SKSE co-save. On a later load, the plugin resolves the saved FormIDs and reapplies any tracked spell that a current player teammate is missing.

## Runtime requirements

- Skyrim SE 1.5.97 and the matching SKSE64 build
- Address Library for SKSE Plugins
- Media Keys Fix SKSE
- Prisma UI

The current MO2 profile already contains these requirements. The mod is deliberately not copied into MO2 until its native DLL has compiled and been tested.

## Hotkey configuration

After installing the mod, edit `SKSE/Plugins/FollowerSpellbookManager.ini` in its MO2 mod folder, then restart the game. The default is Shift+S:

```ini
[Hotkey]
Key=S
Shift=true
Ctrl=false
Alt=false

[LevelScaling]
MaxLevel=300
```

`Key` accepts A–Z, 0–9, F1–F12, Esc, Tab, Enter, Space, or a DirectInput scan code such as `0x1F`. Set a modifier to `true` when it must be held. For example, Ctrl+Alt+M is `Key=M`, `Ctrl=true`, `Alt=true`, `Shift=false`. `LevelScaling.MaxLevel` accepts 1–1000 and defaults to 300.

## Build

1. Ensure the `reference/` directory contains the Prisma UI example repositories and their submodules.
2. In `web/`, run `npm install` followed by `npm run build`.
3. In `native/`, run `xmake build -y`.

The web build produces the Prisma view. The native build produces the SKSE plugin DLL. A later packaging step combines them under the MO2 mod directory structure.

## 面板能力

启用随包提供的 `FollowerSpellbookManager.esp`（ESL 标记），进入新游戏或成功读档后自动获得「打开随从法术」。在魔法菜单的能力分类中装备，按能力键释放；可以加入收藏。能力零消耗、无每日次数限制，与现有快捷键打开同一个面板。各模组独立安装，无需额外 Papyrus 脚本。

如只使用快捷键，将 `SKSE/Plugins/FollowerSpellbookManager.ini` 的 `[PanelPower] Enabled=0`，下次读档会移除该能力；改回 `1` 后读档可恢复。更新安装时请同时更新 DLL 和 ESP，并在 MO2 右侧插件列表启用 ESP。
