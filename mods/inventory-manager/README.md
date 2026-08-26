# Inventory Manager

The Inventory Manager is a lightweight PrismaUI panel for the player inventory and magic lists.

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
Data/PrismaUI/views/InventoryManager/index.html
```

The compiled `web/dist` contents belong in `Data/PrismaUI/views/InventoryManager/`.

## Build and package

From `web`, run `pnpm install` once and then `pnpm run build`. From `native`, run `xmake f --skyrim_vr=n -m release` followed by `xmake build -y`.

After both builds, run this from the repository root to create an install-ready `packaging/release/Data` tree:

```powershell
.\modules\inventory-manager\packaging\package.ps1
```

The generated `release` directory can be installed as one mod in MO2 or Vortex.

## First implementation scope

- The inventory page reads the player's items, actual count, weight, value, favorite/equipped/enchanted/quest markers, and the agreed categories.
- The magic page reads base and learned spells, dragon shouts, powers, passive abilities, and live active effects. Schools are classified from the game data.
- Magic favorites and spell/shout equipping use Skyrim's native managers. Inventory favorites, equipping, using, and dismantling are available through their native game systems. Equipment state is refreshed again on the following frame so the UI reflects Skyrim's final slot-conflict result.
