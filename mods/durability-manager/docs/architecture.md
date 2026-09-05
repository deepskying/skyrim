# Durability Manager architecture

## State ownership

| State | Owner | Persistence |
| --- | --- | --- |
| Hotkey, warning threshold, HUD preference, display duration | Native plugin | `DurabilityManager.ini` |
| Card ranges/materials, cost curve, enchantment pool overrides | Native plugin, loaded at DataLoaded | `DurabilityManager.rules.json` |
| Equipment state: reinforcement rank, current/max durability, permanent card effects, stat/name bridge baselines and protection flags | Native plugin | SKSE co-save |
| Current forge station, selected equipment and three drafted cards | Native plugin | Session only |
| UI selection and active tab | Prisma view | Session only |

Durability and reinforcement must be recorded against a stable **item-instance identity**, never solely a base FormID. A base FormID is shared by every steel sword, while an enchanted sword, a renamed sword, and a unique sword may need distinct state. The current persisted record is versioned and consists of `ItemKey`, reinforcement rank, durability values, permanent numeric card results, and runtime bridge state. The `ItemKey` is backed by Skyrim extra-data / a generated persistent ID, with form-ID resolution during co-save load. Replacement enchantments are written to Skyrim's native per-instance `ExtraEnchantment`, so Skyrim persists the selected form with the item and the co-save layout does not need to duplicate that reference.

## Card contract

Each generated card is data, never frontend behaviour: `{ type, tier, rolledValue, enchantmentFormID, enchantmentCharge, enchantmentPower, successChance, requiredMaterials }`. The seven initial types are `performance`, `weight`, `speed`, `durability`, `wear`, `charge`, and `enchantment`. Type determines eligibility and hard limits; tier (`微弱`, `标准`, `强效`, `极强`) determines the random-value subrange and the card border treatment. Enchantment offers resolve a concrete compatible loaded form when drafted. The native side validates the item, resource counts, selected enchantment, success roll, and every stat limit before applying a card.

`DraftLedger<ItemKey, EnhancementCardState>` owns the three cards and refresh count for each visited instance. Forge access/selection is separate: clearing station context never erases this ledger. A paid refresh replaces only that item's draft; a resolved enhancement replaces it with a new round and resets its fee. Destruction removes its entry. Load/revert/new-game clears the session ledger without touching Prisma APIs. This does not prevent rerolls by loading an earlier save; draft persistence is not part of the current co-save format.

Eligibility reads current accumulated bonuses and actual charge capacity before type selection. Capped categories cannot occupy new draft slots; if fewer than three types are eligible, remaining types may repeat. Cached offers are validated again for changed eligibility at display/payment time. Broken/equipped/material-owned conditions are calculated live instead of being saved in `blockedReason` at draft time. No free reroll is granted merely by repairing or changing equipment.

## Gameplay rules

Enchantment ranking overrides resolve at DataLoaded by plugin-local FormID or EditorID. The closest rule along the base-enchantment chain wins as a complete entry. Its optional power replaces the whole effect score; its optional tier restricts the offer to one tier. Unspecified effects use flag-aware scoring; SoulTrap has a bounded utility score. Candidate scores are computed before sorting. Empty fixed-tier buckets fall back by the standard tier weights to an available bucket, and all economic fields use the final tier. No enchantment form/effect magnitudes are edited by ranking.

- The first time an equipped item participates, the plugin assigns or reuses Skyrim's `ExtraUniqueID`; the resulting `base FormID + unique ID` key is saved in the SKSE co-save. A save without this record simply starts each item at its default state.
- Successful player melee hits consume the equipped weapon's type-specific base wear. Power attacks multiply that cost; misses, bashes, unarmed attacks, bound weapons, and hits caused by other actors are ignored. Warhammers are distinguished from battleaxes through the standard `WeapTypeWarhammer` keyword.
- Bows lose configured wear only after a completed `TESPlayerBowShotEvent` (cancelled draws cost nothing); crossbows use their separate configured base cost. Bound weapons are excluded. Wear-reduction is applied after the base cost and is clamped by the configured global cap.
- When the player receives a physical `TESHitEvent`, one worn non-jewelry armor/clothing instance is selected by slot coverage and loses its configured base wear. A blocked hit targets a worn shield only; a weapon-only block causes no armor wear. Staff/spell and self-inflicted hits are ignored. Incoming power attacks apply the armor-specific multiplier.
- Ordinary non-unique equipment at zero durability is removed and converted into half of the best matching forge recipe, with at least one of each component returned. Equipment without a usable recipe is retained rather than silently destroyed.
- `AllowEnchantedItemsToBreak` defaults to `true`: when enabled, ordinary enchanted equipment follows the same break-and-salvage rule; when disabled, it becomes `broken` instead.
- Quest equipment and items carrying Skyrim's standard `DaedricArtifact` or `MagicDisallowEnchanting` keyword always become `broken`; they are unequipped and cannot be used until repaired, regardless of the enchanted-item setting.
- Broken retained items are collected from their persistent instance IDs into `repairQueue`, so they remain selectable after being unequipped. Zero-durability records loaded from older saves enter the same resolution path after load.
- Repair costs are calculated by missing-durability band and recipe material, then shown before consuming anything.
- Recipe-less armor and clothing use a repair-only fallback (iron ingots or leather strips) so the new incoming-hit wear cannot create permanently unusable equipment; they are still retained rather than auto-salvaged at zero.
- Numeric enhancement cards consume their displayed materials before the native roll. Success stores the bounded value and increments the exact instance's rank. Ordinary failure removes only that instance and returns half of its forge-recipe materials; quest and recognized unique items remain and lose one rank with proportional bonus reduction.
- Performance uses the instance's native `ExtraHealth` temper factor. The plugin records the vanilla temper baseline and its last applied value, so later grindstone/workbench or third-party deltas are folded into that baseline without baking in the mod's previous contribution a second time.
- Charge capacity uses the instance's native `ExtraEnchantment` charge value. Capacity changes preserve the weapon's current charge percentage and never modify the shared base enchantment form.
- Weight reduction is summed from matching `ExtraUniqueID` instances and subtracted from freshly recalculated player inventory and worn-armor weight caches. Container and equipment events queue a next-frame resynchronization, avoiding shared base-form edits.
- Attack speed is synchronized per hand through `weaponSpeedMult` and `leftWeaponSpeedMult`. The bridge remembers its previous target and removes only its own prior bonus when the graph has not been externally changed; a changed graph value is accepted as the new baseline. The saved card value is capped at +1.00.
- Reinforcement rank is written to the instance's `ExtraTextDisplayData` as `baseline +N`. The bridge persists the player-authored baseline and its last applied value, so upgrades replace the suffix, external renames become a new baseline, and `+0` restores the name. Quest/message-owned display data is never forcibly replaced.
- Enchantment candidates are collected once from playable, non-protected weapon/apparel definitions plus configured allow entries. Candidate and base-enchantment IDs/plugin exclusions, finite valid effects, visible effects, and all ancestor worn restrictions are validated per item. This is a conservative pool, not proof that every third-party scripted effect is generic; a deny list remains necessary for exceptions. Tiers estimate relative strength from native effect data. The exact form is stored in the session card. Unequipping is required before payment and mutation; success writes `ExtraEnchantment`, marks the inventory changed, and rebases/reapplies the saved charge bonus. The next equip activates the new effect.
- JSON rule overrides are parsed atomically; malformed configurations use built-in defaults and produce a log error. Missing material records block the affected draft rather than silently removing costs. Growth continues after +50 using doubles; conversion to the engine's signed 32-bit material count is checked before casting and adding requirements. Overflow blocks the draft.
- Co-save record version 3 adds the display-name bridge strings and initialized flag. Version-1 and version-2 records are accepted as explicit migration paths; their current native data becomes the relevant bridge baseline before saved effects are synchronized.
- HUD warnings fire on a threshold crossing with a cooldown, rather than once per hit.

## Event flow

```text
successful player melee hit
  -> resolve equipped item instance
  -> verify source is a supported non-bound melee weapon
  -> subtract type-specific wear (power-attack multiplier when applicable)
  -> warn once when crossing threshold
  -> zero: break or salvage
  -> save item state to co-save
  -> push refreshed data to PrismaUI when open

completed bow / crossbow shot
  -> resolve the equipped item instance
  -> ignore bound weapons and cancelled draws
  -> subtract configured base wear after wear-reduction cap
  -> persist state through the next SKSE co-save

incoming physical hit on player
  -> ignore spells, staffs, jewelry, and self-inflicted hits
  -> blocked: select the worn shield; no shield means no armor wear
  -> unblocked: select one worn armor/clothing instance by coverage weight
  -> subtract configured wear after that instance's wear-reduction cap
  -> zero: reuse the existing unequip, protection, salvage, and repair path

weapon equip / switch / `weaponDraw` animation
  -> resolve the player's equipped weapon
  -> queue left/right attack-speed and player-weight synchronization
  -> show non-blocking HUD card with current / maximum durability
  -> if it is below the configured threshold, show the one-time low-durability warning

activate forge
  -> remember the workstation for two minutes while the player stays nearby
  -> close the original crafting menu, then open PrismaUI with the panel hotkey
  -> show all carried equipment and full selected-item details
  -> draft three eligible enhancement-card previews
  -> refresh consumes 80, 160, 240... gold and replaces all three cards
  -> user repairs, or enters the full-width enhancement page
  -> compare native before/after rows, select one card, review costs and failure risk
  -> explicit acknowledgement enables the confirm button (cancel costs nothing)
  -> validate material inventory, outcome and limits again
  -> consume displayed materials and roll natively
  -> success: apply the bounded numeric result or selected instance enchantment, then increase rank
  -> failure: dismantle ordinary equipment, or downgrade protected equipment
  -> refresh panel state; persist the changed instance in the next co-save
```

## Native/UI contract

### Compatibility cache (v0.1.33)

`enchantment_cache.h` defines an engine-independent, owner-locked LRU cache. Each key is a base equipment FormID; its entry includes an exact vector signature of weapon class/bound/fist flags and keyword FormIDs, an immutable shared vector of compatible ENCH FormIDs, creation time and an LRU position. No engine pointers, instance IDs, current enchantment, protection status, materials or card offers are retained. Immutable ID snapshots stay valid if another callback clears/evicts an entry; lookups resolve current engine objects before using them. Existing native checks still resolve and fully validate the chosen enchantment before payment and mutation.

Entries (including empty results) expire after five seconds from creation; cache hits never extend expiry. Runtime item-keyword/class edits invalidate the entry immediately. Foreign edits to enchantment effects or nested restriction lists may leave UI eligibility/candidate lists stale until expiry, but cannot bypass the uncached payment check. The cache does not promise immediate detection of arbitrary third-party hooks or dynamic record edits. Limits are 512 entries and 262144 combined signature/candidate IDs (approximately 1 MiB of stored ID payload, plus containers; caller-owned temporary snapshots are separate). Oversized results are returned without caching or flushing the working set. Least-recently-used entries are evicted to satisfy both bounds.

`HasCompatibleEnchantment` answers boolean UI/eligibility queries without allocating the full result-pointer vector; the full vector is only needed for drafting. Current instance enchantments are excluded after cache lookup, so replacing one copy's enchantment does not corrupt another copy's candidate set. Rules reload, pool rebuild, save transitions and serialization revert clear the cache under its own mutex, outside durability/draft locks; no Prisma APIs or serialization records are involved. Clear logs summarize hits, full scans, evictions, entry count and retained ID count; individual scans use debug logging.

`tests/enchantment_cache_tests.h` is run by `DurabilityRulesTests`: exact signatures, non-sliding TTL, empty-to-nonempty expiry, bounded LRU eviction, oversized bypass, resets, exception recovery and snapshot lifetime. A synthetic 5000-query / 20-base-item / 500-candidate workload asserts 20 scans and 4980 hits while checking candidate equality; this is a scan-count regression test, not a Skyrim FPS benchmark.

The view receives `{ equipped, repairQueue, forge, settings }`. Equipment rows include their visible combat stats, weight, enchantment, protection flags and reinforcement rank. `forge` contains the station context and the current three card offers. The native side remains authoritative and revalidates all requests. The UI never decides whether an item is protected, broken, repairable, affordable, eligible for a card, or allowed to replace its enchantment.

### Enhancement review (v0.1.32)

Each card now includes `equipmentId` (the exact `baseFormID:uniqueID`) and `preview: [{ label, before, after }]`, with display strings calculated natively. `SuccessfulCardSnapshot` is shared between the read-only projection and actual success mutation. Charge preview includes baseline rebasing and the 65535 capacity limit; performance shows both the ledger's base-plus-mod value and the capped native temper factor, not final perk-adjusted combat damage. No shared forms or co-save records are changed by previews.

The full-width page only displays offers belonging to its selected instance. Review is local UI state: clicking a card or cancelling sends no mutation request. Confirmation requires an unchecked-by-default acknowledgement; changes to the item, card, costs or protection invalidate it. A synchronous submit guard suppresses repeated clicks until a new native state arrives. Leaving the page, hiding the panel, losing workshop access, or losing the item clears review. Native request names and payment-time validations remain unchanged. No Prisma view lifecycle, serialization version or draft persistence changes were made.

Frontend helper regressions run with `node --test tests/*.test.mjs` from `web`. They cover malformed/null input, material gating, instance-bound cards, stale confirmations and protected-item failure wording. Browser demo verification covers page navigation, before/after tables, disabled confirmation, acknowledgement and cancellation. Real game testing is still required for native payment/outcomes, death/load and third-party enchantments.
