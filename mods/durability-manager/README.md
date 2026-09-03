# Durability Manager

An SKSE + PrismaUI durability mod for Skyrim SE 1.5.97.

## Current foundation

- **Shift+F** opens the PrismaUI panel; it can be rebound in the **配置** tab.
- The panel reads the player’s currently equipped weapons and armour, including quest and enchantment markers.
- The panel provides the agreed two tabs: **耐久状态** and **配置**.
- Drawing, equipping, or switching to a weapon shows a non-blocking HUD card with large current / maximum durability numbers, percentage, and a high-contrast progress track. The display duration is configurable.
- A low-durability HUD warning fires once when an equipped weapon is below the configured threshold; it becomes eligible again after returning above the threshold.
- Prisma initialization is separated from view creation: the interface and input hooks load at `DataLoaded`, while a fresh render surface is created only after `PostLoadGame` or `NewGame`. Reloading a save destroys the pre-transition surface and recreates the view after the game world is ready.
- The React panel is synchronously mounted when opened, then waits for two browser animation frames before reporting that it has painted. Native focus and game pause are applied only after that handshake. Focus uses Prisma's `disableFocusMenu` mode so Skyrim 1.5.97 does not replace the rendered page while opening `PrismaUI_FocusMenu`.
- Low-durability threshold, weapon display duration, HUD-warning preference, enchanted-item breakage, ranged-shot wear values, and the panel hotkey are persisted in `SKSE/Plugins/DurabilityManager.ini`.
- A bow loses durability only when Skyrim emits a completed `TESPlayerBowShotEvent`: drawing then cancelling costs nothing. Bows lose `1.0` by default; crossbows lose `2.0`; bound weapons are excluded. Wear-reduction effects apply after the base cost and are capped at 70% by default.
- The equipment detail panel displays the effective per-shot durability cost (after wear reduction) for bows and crossbows. Other equipment shows that a loss rule has not been enabled yet, rather than implying a made-up rate.
- Equipment state is tracked per carried item instance (`base FormID + ExtraUniqueID`) and saved in the SKSE co-save. Existing saves without Durability Manager records start safely at the default 100 / 100 state.
- The repair queue layout, material details, and forge-only hammer interaction are implemented in the Prisma view and ready for the native durability/forge bridge.

Melee/armor loss, zero-durability break or salvage transactions, and forge activation remain separate from this ranged-wear slice. Those systems will build on the same per-instance key and co-save state before any item can be removed or altered.

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
