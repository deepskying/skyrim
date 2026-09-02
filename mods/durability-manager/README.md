# Durability Manager

An SKSE + PrismaUI durability mod for Skyrim SE 1.5.97.

## Current foundation

- **Shift+F** opens the PrismaUI panel; it can be rebound in the **配置** tab.
- The panel reads the player’s currently equipped weapons and armour, including quest and enchantment markers.
- The panel provides the agreed two tabs: **耐久状态** and **配置**.
- Low-durability threshold, weapon display duration, HUD-warning preference, enchanted-item breakage, and the panel hotkey are persisted in `SKSE/Plugins/DurabilityManager.ini`.
- The repair queue layout, material details, and forge-only hammer interaction are implemented in the Prisma view and ready for the native durability/forge bridge.

The native durability-loss hooks, per-instance co-save identity, break/salvage transaction, and forge activation hook deliberately remain separate from this UI/configuration foundation. They must be completed as one integrity-preserving slice so that enchanted and unique items are never incorrectly merged or destroyed.

## Install layout

```text
Data/SKSE/Plugins/DurabilityManager.dll
Data/SKSE/Plugins/DurabilityManager.ini
Data/PrismaUI/views/DurabilityManager/index.html
```

## Build

From `web`, run `pnpm install` once and then `pnpm run build`. From `native`, run:

```powershell
xmake f --skyrim_vr=n -m release
xmake build -y
```

Then run `packaging/package.ps1` to make the install-ready `release/Data` layout.
