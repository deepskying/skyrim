# Durability Manager

An SKSE + PrismaUI durability mod for Skyrim SE 1.5.97.

## Current foundation

- **Shift+F** opens the PrismaUI panel; it can be rebound in the **配置** tab.
- The panel reads the player’s currently equipped weapons and armour, including quest and enchantment markers.
- The panel provides the agreed two tabs: **耐久状态** and **配置**. The settings tab uses a full-width card layout with clearly labelled sliders, a custom warning switch, current hotkey keycaps, and inline hotkey rebinding.
- Drawing, equipping, or switching to a weapon shows a non-blocking HUD card with large current / maximum durability numbers, percentage, and a high-contrast progress track. The display duration is configurable.
- A low-durability HUD warning fires once when an equipped weapon is below the configured threshold; it becomes eligible again after returning above the threshold.
- The Prisma view uses the proven direct lifecycle: create and hide it once at `DataLoaded`, then show and focus it directly from the panel hotkey.
- Save transitions reset only the plugin's local visibility flags. They never invoke, hide, focus, destroy, or recreate the Prisma view while Skyrim is loading; any stale focus is normalized on the next explicit panel open.
- Native panel data is normalized at the browser boundary. Unsupported wear rates are omitted, legacy `null` values are treated as unavailable, and a React error boundary reports unexpected render failures instead of silently removing the entire panel.
- Low-durability threshold, weapon display duration, HUD-warning preference, enchanted-item breakage, melee/ranged wear values, and the panel hotkey are persisted in `SKSE/Plugins/DurabilityManager.ini`.
- A melee weapon loses durability only after the player successfully hits a target. Base wear is `0.35` for daggers, `0.50` for swords, `0.65` for war axes, `0.80` for maces and greatswords, `0.95` for battleaxes, and `1.10` for warhammers; power attacks use a configurable `1.60×` multiplier. Bashes, unarmed attacks, bound weapons, misses, and attacks performed by other actors are excluded.
- A bow loses durability only when Skyrim emits a completed `TESPlayerBowShotEvent`: drawing then cancelling costs nothing. Bows lose `1.0` by default; crossbows lose `2.0`; bound weapons are excluded. Wear-reduction effects apply after the base cost and are capped at 70% by default.
- The equipment detail panel displays the effective per-hit or per-shot durability cost after wear reduction. Unsupported equipment shows that a loss rule has not been enabled yet.
- Equipment state is tracked per carried item instance (`base FormID + ExtraUniqueID`) and saved in the SKSE co-save. Existing saves without Durability Manager records start safely at the default 100 / 100 state.
- The repair queue layout, material details, and forge-only hammer interaction are implemented in the Prisma view and ready for the native durability/forge bridge.

Armor loss, zero-durability break or salvage transactions, and forge activation remain separate from the current weapon-wear slice. Those systems will build on the same per-instance key and co-save state before any item can be removed or altered.

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
