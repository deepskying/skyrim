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
- An incoming physical hit damages one worn armor or clothing instance, selected by body coverage (body pieces are more likely than gloves or boots). Successful shield blocks damage the equipped shield instead; weapon-only blocks do not damage armor. Spells, jewelry, and self-inflicted hits are excluded. Incoming power attacks use a separate configurable multiplier.
- Armor and clothing without a usable forge or temper recipe receive a repair-only fallback instead of becoming permanently broken: armor uses iron ingots and clothing uses leather strips, scaled by the missing-durability band. Recipe-less items remain protected from automatic salvage destruction.
- The equipment detail panel displays the effective per-hit or per-shot durability cost after wear reduction. Unsupported equipment shows that a loss rule has not been enabled yet.
- Equipment state is tracked per carried item instance (`base FormID + ExtraUniqueID`) and saved in the SKSE co-save. Existing saves without Durability Manager records start safely at the default 100 / 100 state.
- At zero durability, ordinary equipment with a forge recipe is removed and returns half of that recipe's materials (at least one of each component). Quest items, recognized artifacts/unique items, protected enchanted items, and mod equipment without a usable recipe are unequipped and retained as broken; attempts to equip them again are rejected until they are repaired.
- Broken retained items remain visible in the panel's combined equipment/repair list. Artifact protection uses Skyrim's standard `DaedricArtifact` and `MagicDisallowEnchanting` keywords in addition to the quest-item flag.
- Activating a standard forge, smelter, sharpening wheel, or armor workbench unlocks the equipment workshop for two minutes while the player remains within 600 game units. This does not replace or interrupt Skyrim's crafting menu; after closing the original menu, the normal panel hotkey opens the workshop.
- Damaged equipped items and retained broken items show their repair requirements together with the amount currently carried. The mod prefers the item's tempering recipe, falls back to another constructible-object recipe, and charges 25%, 50%, 75%, or 100% of its ingredient counts according to missing durability (at least one of each ingredient).
- Repair is a native, per-instance transaction: forge context, inventory ownership, current durability, recipe availability, and all ingredient counts are revalidated before materials are removed. A successful repair restores that exact item instance to its full current maximum durability.
- The workshop list now includes every carried weapon, armor piece, and zero-armor clothing item, not only currently equipped or broken equipment. Existing extra-data instances receive stable IDs; untouched identical copies are shown as one safe quantity group until one has been equipped and becomes an independently trackable instance.
- Selecting an independently tracked item at a forge drafts three cards from the seven agreed categories, filtered by equipment eligibility and kept distinct whenever at least three types apply. Tiers use `42% / 33% / 18% / 7%` weights for weak, standard, strong, and extreme offers, with tier-colored borders, bounded rolls, level-scaled benefit/cost previews, success chance, and live owned/required material counts.
- Card refresh starts at 80 gold and rises by 80 gold per paid refresh (the existing safety cap is 80000 gold). Each equipment instance retains its current draft and refresh counter across equipment selection, workstation reactivation, and leaving/returning to the forge. A resolved enhancement starts that item's next round at 80 gold; other items retain their offers. Drafts are session-only and reset on load/new game.
- Confirming an affordable card after acknowledging its risks removes its displayed materials and performs the native success roll. Success applies the bounded value to that exact item instance, increases its visible `+N` reinforcement rank, and drafts three new cards. The rank and accumulated values use the existing co-save record, so older saves remain compatible.
- Failed reinforcement dismantles an ordinary item instance and returns half of its forge-recipe materials. Quest items and recognized unique/artifact items are retained and lose one reinforcement rank instead; their accumulated numeric bonuses are reduced proportionally. The card footer states the applicable failure rule before selection.

Version 0.1.27 writes the reinforcement rank into each enhanced instance's native Skyrim display name, so inventory, equipment, barter, and other menus can show names such as `Steel Sword +22`. The name bridge stores both the original player-authored name and its last applied name in co-save record version 3, preventing repeated suffixes across upgrades and loads. A later player rename becomes the new baseline, and downgrading to `+0` restores the baseline. Version-1 and version-2 records remain readable and migrate when first synchronized. Quest/message-owned display names are preserved rather than forcibly overwritten.

Version 0.1.29 refines the enchantment replacement introduced in 0.1.28. The default pool now comes from enchantments actually referenced by playable, non-protected weapons/apparel, with explicit allow/deny rules and plugin exclusions. Restrictions are checked along the base-enchantment chain; invalid effects and wholly hidden effects are rejected. Records without an independent name use their visible effect name. The card shows each visible effect's native magnitude/duration and the source plugin. Tier ordering is a power estimate across different effects, not a guarantee of combat strength. Summermyst can participate through eligible equipment records; its effects have not yet been validated in-game in this workspace.

Enchantment replacement requires the item to be unequipped, with the requirement checked again before payment. Equip it after a successful replacement to apply its new effects. Only the selected instance changes, its charge bonuses are reapplied, and the inventory is marked changed for saving. Protected/quest items remain excluded. There is no new co-save record version.

The packaged `DurabilityManager.rules.json` configures the six numeric card ranges, catalysts for all seven categories, late-game costs, and enchantment pool overrides. Costs continue above +50 with a quadratic tail, extra gold, and late materials; quantities no longer freeze at 9999. Requests beyond the signed 32-bit engine count limit are blocked rather than wrapped or silently capped. See [rule format and game test checklist](docs/enhancement-rules.md). New executable card mechanics and arbitrary scaled enchantment forms still require native development.

Version 0.1.30 filters maxed weight/speed/wear/charge categories before drafting; performance also respects its stored integer/runtime cap. If fewer than three categories remain, eligible categories may repeat with independently rolled values. Application revalidates eligibility before spending materials. Repair, equipped status and material ownership are live conditions so a remembered card is usable after repair/unequip/material collection. Per-instance session drafts prevent selection and workstation changes from providing free rerolls.

Durability and wear, performance, charge, weight, attack speed, native `+N` equipment names, and instance enchantment replacement now affect live game data for supported equipment. Skyrim's ordinary inventory row can still show an item's base weight; the mod panel shows the enhanced instance weight while encumbrance uses the reduced total.

Version 0.1.31 improves utility enchantment ranking: hidden helpers and no-magnitude/no-duration fields no longer inflate scores, and SoulTrap effects use a bounded capture-window score. `enchantments.ranking` supports whole-enchantment score overrides and fixed tiers, including inheritance from base-enchantment rules. Fixed tiers constrain offers without bypassing compatibility; if a rolled tier has no candidates, an available tier is chosen before computing costs, success chance and charge. The preview labels soul-trap duration as its capture window. These rankings do not modify actual effects or provide automatic recognition of arbitrary third-party scripts.

## Install layout

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
