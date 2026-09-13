# Durability Manager

An SKSE + PrismaUI durability mod for Skyrim SE 1.5.97.

## Current foundation

- The 0.1.43 source adds the translucent workshop layout, inventory filters and reviewed manual recycling near a forge. It also builds as a module of [Equipment Workshop 1.0.0](../workshop/README.md), which combines this mod and Magic Arrows in one DLL and imports the old arrow queue without modifying old saves. Use that unified package for the combined experience; do not load it alongside the two standalone DLLs. Game acceptance remains pending.

- Version 0.1.42 adds staff wear on the player's SKSE spell-release action. `[Wear] StaffCastWear=1.0` sets the base cost (0.1–100); restart the game after editing the INI. The firing hand selects the exact worn instance, including two identical staves. Charging alone, other actors, empty-charge instances, ordinary spells and hit/damage ticks do not trigger this rule. Concentration uses release actions, with no ongoing per-second cost. Existing wear reduction, warnings, breakage and co-save persistence apply. Equipment details show the effective cost per staff release. Recipe-less staves can be repaired with 1–4 iron ingots according to missing durability. In-game verification is still required; see the staff checklist in `docs/architecture.md`.

- Version 0.1.41 removes the enhancement review's acknowledgement checkbox. The detail page still shows costs, success chance and failure consequences; an affordable valid offer can be confirmed directly with `尝试强化`. Cancellation, stale-offer checks, duplicate-submit protection and native payment validation are unchanged.

- Version 0.1.40 permits enhancement of equipped, independently tracked instances. Payment follows safe temporary unequip; success restores the original hand/slot when available, ordinary failure dismantles the unequipped item, and protected failure downgrades it without re-equipping. Ambiguous worn stacks are rejected without charging; occupied slots are never forcibly displaced. Every card now charges gold plus materials: `cost.baseGold` defaults to 100 and scales with current rank and tier (75 / 100 / 150 / 225 gold at +0). Recipe gold is merged into the displayed total. Seven card types have distinct colored fills and tier depth/borders. Native workshop click/result sounds can be disabled through settings or `EnableWorkshopSounds`. Co-save version and panel lifecycle are unchanged. Native rules and 33 web tests pass; equipment restoration and sound playback still require in-game testing. Back up custom INI/rules before installing both DLL and frontend together.

- Version 0.1.39 adds actual-cost labels to repair and enhancement buttons (`仅材料`, `N 金币`, or `N 金币 + 材料`), using the native Gold001 record flag rather than translated names. Prices and payment rules are unchanged. Card refresh fades old offers, waits for a matching native receipt, then reveals the three cards in sequence (~0.54 seconds minimum). Failure retains the offer and displays its reason; unknown outcomes never auto-retry. Update both DLL and frontend together.

- Version 0.1.38 places equipped instances first in the combined inventory/repair list while preserving the original order within each group. Sorting does not mutate the received state or change the selected instance; it is recalculated whenever equipment state is received.

- Version 0.1.37 displays current and maximum durability with one decimal place in the list, details, weapon HUD and enhancement previews (for example, `98.6 / 100.0`). HUD messages preserve fractional values. Internal durability, save precision and per-action wear-rate display are unchanged.

- Version 0.1.36 adds a bordered green `✓ 已装备` badge in inventory rows and equipment details. It uses each item's existing extra-data worn state (including left-hand equipment), independently of selection, enchantment, and broken status. No save format or equipment behavior changes.

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
- An incoming physical hit damages one worn armor or clothing instance, selected by body coverage (body pieces are more likely than gloves or boots). Successful shield blocks damage the equipped shield instead; weapon-only blocks do not damage armor. Spells, jewelry, and self-inflicted hits are excluded. Incoming power attacks use a separate configurable multiplier.
- Armor and clothing without a usable forge or temper recipe receive a repair-only fallback instead of becoming permanently broken: armor uses iron ingots and clothing uses leather strips, scaled by the missing-durability band. Recipe-less items remain protected from automatic salvage destruction.
- The equipment detail panel displays the effective per-hit or per-shot durability cost after wear reduction. Unsupported equipment shows that a loss rule has not been enabled yet.
- Equipment state is tracked per carried item instance (`base FormID + ExtraUniqueID`) and saved in the SKSE co-save. Existing saves without Durability Manager records start safely at the default 100 / 100 state.
- At zero durability, ordinary equipment with a forge recipe is removed and returns half of that recipe's materials (at least one of each component). Quest items, recognized artifacts/unique items, protected enchanted items, and mod equipment without a usable recipe are unequipped and retained as broken; attempts to equip them again are rejected until they are repaired.
- Broken retained items remain visible in the panel's combined equipment/repair list. Artifact protection uses Skyrim's standard `DaedricArtifact` and `MagicDisallowEnchanting` keywords in addition to the quest-item flag.
- Opening the panel within 600 game units of a loaded standard forge, smelter, sharpening wheel, or armor workbench automatically enables repair and enhancement. No prior activation or two-minute unlock is required. The nearest eligible facility is shown in the header. Disabled/deleted/unloaded references, separate interiors and different worldspaces are excluded; adjacent loaded exterior cells are included. Actions revalidate proximity before payment. Skyrim's original crafting menus are unchanged.
- Damaged equipped items and retained broken items show their repair requirements together with the amount currently carried. The mod prefers the item's tempering recipe, falls back to another constructible-object recipe, and charges 25%, 50%, 75%, or 100% of its ingredient counts according to missing durability (at least one of each ingredient).
- Repair is a native, per-instance transaction: forge context, inventory ownership, current durability, recipe availability, and all ingredient counts are revalidated before materials are removed. A successful repair restores that exact item instance to its full current maximum durability.
- The workshop list now includes every carried weapon, armor piece, and zero-armor clothing item, not only currently equipped or broken equipment. Existing extra-data instances receive stable IDs; untouched identical copies are shown as one safe quantity group until one has been equipped and becomes an independently trackable instance.
- Selecting an independently tracked item at a forge drafts three cards from the seven agreed categories, filtered by equipment eligibility and kept distinct whenever at least three types apply. Tiers use `42% / 33% / 18% / 7%` weights for weak, standard, strong, and extreme offers, with tier-colored borders, bounded rolls, level-scaled benefit/cost previews, success chance, and live owned/required material counts.
- Card refresh starts at 80 gold and rises by 80 gold per paid refresh (the existing safety cap is 80000 gold). Each equipment instance retains its current draft and refresh counter across equipment selection, workstation reactivation, and leaving/returning to the forge. A resolved enhancement starts that item's next round at 80 gold; other items retain their offers. Drafts are session-only and reset on load/new game.
- Confirming an affordable card after acknowledging its risks removes its displayed materials and performs the native success roll. Success applies the bounded value to that exact item instance, increases its visible `+N` reinforcement rank, and drafts three new cards. The rank and accumulated values use the existing co-save record, so older saves remain compatible.
- Failed reinforcement dismantles an ordinary item instance and returns half of its forge-recipe materials. Quest items and recognized unique/artifact items are retained and lose one reinforcement rank instead; their accumulated numeric bonuses are reduced proportionally. The card footer states the applicable failure rule before selection.

Version 0.1.27 writes the reinforcement rank into each enhanced instance's native Skyrim display name, so inventory, equipment, barter, and other menus can show names such as `Steel Sword +22`. The name bridge stores both the original player-authored name and its last applied name in co-save record version 3, preventing repeated suffixes across upgrades and loads. A later player rename becomes the new baseline, and downgrading to `+0` restores the baseline. Version-1 and version-2 records remain readable and migrate when first synchronized. Quest/message-owned display names are preserved rather than forcibly overwritten.

Version 0.1.29 refines the enchantment replacement introduced in 0.1.28. The default pool now comes from enchantments actually referenced by playable, non-protected weapons/apparel, with explicit allow/deny rules and plugin exclusions. Restrictions are checked along the base-enchantment chain; invalid effects and wholly hidden effects are rejected. Records without an independent name use their visible effect name. The card shows each visible effect's native magnitude/duration and the source plugin. Tier ordering is a power estimate across different effects, not a guarantee of combat strength. Summermyst can participate through eligible equipment records; its effects have not yet been validated in-game in this workspace.

Enchantment replacement writes only while the item is unequipped. Since 0.1.40 the workshop handles temporary unequip and restoration automatically for supported independent instances, with checks before payment and mutation. Only the selected instance changes, its charge bonuses are reapplied, and the inventory is marked changed for saving. Protected/quest items remain excluded. There is no new co-save record version.

The packaged `DurabilityManager.rules.json` configures the six numeric card ranges, catalysts for all seven categories, late-game costs, and enchantment pool overrides. Costs continue above +50 with a quadratic tail, extra gold, and late materials; quantities no longer freeze at 9999. Requests beyond the signed 32-bit engine count limit are blocked rather than wrapped or silently capped. See [rule format and game test checklist](docs/enhancement-rules.md). New executable card mechanics and arbitrary scaled enchantment forms still require native development.

Version 0.1.30 filters maxed weight/speed/wear/charge categories before drafting; performance also respects its stored integer/runtime cap. If fewer than three categories remain, eligible categories may repeat with independently rolled values. Application revalidates eligibility before spending materials. Repair, equipped status and material ownership are live conditions so a remembered card is usable after repair/unequip/material collection. Per-instance session drafts prevent selection and workstation changes from providing free rerolls.

Durability and wear, performance, charge, weight, attack speed, native `+N` equipment names, and instance enchantment replacement now affect live game data for supported equipment. Skyrim's ordinary inventory row can still show an item's base weight; the mod panel shows the enhanced instance weight while encumbrance uses the reduced total.

Version 0.1.31 improves utility enchantment ranking: hidden helpers and no-magnitude/no-duration fields no longer inflate scores, and SoulTrap effects use a bounded capture-window score. `enchantments.ranking` supports whole-enchantment score overrides and fixed tiers, including inheritance from base-enchantment rules. Fixed tiers constrain offers without bypassing compatibility; if a rolled tier has no candidates, an available tier is chosen before computing costs, success chance and charge. The preview labels soul-trap duration as its capture window. These rankings do not modify actual effects or provide automatic recognition of arbitrary third-party scripts.

## Install layout

Version 0.1.35 replaces the activation-based workshop unlock with on-demand nearby-facility detection. Detection runs when collecting panel state and validating actions, without background polling; the normal panel pauses the game, and moving closer is reflected when reopening it. It uses the existing four crafting keywords and 600-unit 3D radius; mod-added facilities using those keywords can participate. Distance is geometric, not a line-of-sight or pathfinding test. Existing item drafts survive leaving/re-entering the radius. The v0.1.34 gold/HUD fixes are included. Build, native location/radius tests and eleven web/regression checks pass; discovery and behavior still require in-game verification.

Version 0.1.34 fixes the panel-open crash identified in the 2026-09-05 v0.1.33 crash log (`DurabilityManager.dll+006C4A6`). Both panel gold display and paid card refresh now resolve the fixed `Gold001` record (FormID `0x0000000F`) and count it using `GetItemCount`, bypassing this bundled CommonLib's unsafe `GetGoldAmount` / default-object lookup path. Missing player/gold records safely report zero; refresh still validates and removes the same gold record. The frontend now validates HUD messages before display or timer changes, rejects malformed IDs/kinds, sanitizes text/progress/duration and ignores stale timer callbacks after replacement/unmount. Save format, enhancement rules, compatibility cache and Prisma view lifecycle are unchanged. Native build, rule tests and nine web/regression checks pass; opening the panel and paying for a refresh still need verification in the user's game.

Version 0.1.33 adds a bounded, session-only enchantment compatibility cache shared by copies of the same base equipment. Keyword/weapon-class changes invalidate the entry immediately; entries expire five seconds after creation (hits do not extend that deadline). The cache retains at most 512 equipment entries and 262144 combined signature/candidate IDs, evicting least-recently-used entries. Current enchantment exclusion, quest/unique protection, worn status and material counts remain per-instance/live. Payment and enchantment mutation still run the original complete compatibility check, never trusting cached eligibility as authority. Load/new-game/revert and rules/pool rebuilds clear the cache without calling Prisma. Native tests include a synthetic 5000-query workload with 20 full scans and unchanged candidate results; actual in-game performance still needs measurement.

Version 0.1.32 moves enhancement into a dedicated full-width page opened from equipment details. Cards include native before/after comparisons, owned/required materials, success chance and failure rules. An explicit review and unchecked risk acknowledgement are required before applying a card; cancelling costs nothing. Card data is normalized defensively, bound to the exact equipment instance and invalidated for review when the item or offer changes. The existing Prisma lifecycle and save format are unchanged. This stage has build, helper-test and browser-demo verification; game-runtime validation remains pending.

```text
Data/SKSE/Plugins/DurabilityManager.dll
Data/SKSE/Plugins/DurabilityManager.ini
Data/SKSE/Plugins/DurabilityManager.rules.json
Data/PrismaUI/views/DurabilityManager/index.html
```

## Build

From `web`, run `pnpm install` once and then `pnpm run build`. From `native`, run:

```powershell
xmake f --skyrim_vr=n -m release
xmake build -y
```

Then run `packaging/package.ps1` to make the install-ready `release/Data` layout.

Rule-only verification (no Skyrim runtime required), from `native`:

```powershell
xmake build -y DurabilityRulesTests
.\build\windows\x64\release\DurabilityRulesTests.exe ..\packaging\DurabilityManager.rules.json
```

## 面板能力

启用随包提供的 `DurabilityManager.esp`（ESL 标记），进入新游戏或成功读档后自动获得「打开装备维护」。在魔法菜单的能力分类中装备，按能力键释放；可以加入收藏。能力零消耗、无每日次数限制，与现有快捷键打开同一个面板。各模组独立安装，无需额外 Papyrus 脚本。

如只使用快捷键，将 `SKSE/Plugins/DurabilityManager.ini` 的 `[PanelPower] Enabled=0`，下次读档会移除该能力；改回 `1` 后读档可恢复。更新安装时请同时更新 DLL 和 ESP，并在 MO2 右侧插件列表启用 ESP。

能力只提供面板入口，强化操作仍受现有工作台条件限制。

## 统一工坊 1.0.5 环境磨损

新增有害魔法和游戏命中事件报告的陷阱磨损，同源连续命中每秒限一次；脚步距离累计结算鞋靴 0.02、身体装备 0.005 / 1,000 游戏单位，支持耐磨减免。新参数在 [Wear]，详见 ../workshop/README.md 的覆盖范围与限制。
