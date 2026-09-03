# Durability Manager architecture

## State ownership

| State | Owner | Persistence |
| --- | --- | --- |
| Hotkey, warning threshold, HUD preference, display duration | Native plugin | `DurabilityManager.ini` |
| Equipment state: reinforcement rank, current/max durability, permanent card effects and protection flags | Native plugin | SKSE co-save |
| Current forge station, selected equipment and three drafted cards | Native plugin | Session only |
| UI selection and active tab | Prisma view | Session only |

Durability and reinforcement must be recorded against a stable **item-instance identity**, never solely a base FormID. A base FormID is shared by every steel sword, while an enchanted sword, a renamed sword, and a unique sword may need distinct state. The persisted record is versioned and consists of `ItemKey`, reinforcement rank, durability values, permanent card results, and optional replacement-enchantment reference. The `ItemKey` is backed by Skyrim extra-data / a generated persistent ID, with form-ID resolution during co-save load.

## Card contract

Each generated card is data, never frontend behaviour: `{ type, tier, rolledValue, successChance, requiredMaterials }`. The seven initial types are `performance`, `weight`, `speed`, `durability`, `wear`, `charge`, and `enchantment`. Type determines eligibility and hard limits; tier (`微弱`, `标准`, `强效`, `极强`) determines the random-value subrange and the card border treatment. The native side validates the item, resource counts, success roll, and every stat limit before applying a card.

## Gameplay rules

- The first time an equipped item participates, the plugin assigns or reuses Skyrim's `ExtraUniqueID`; the resulting `base FormID + unique ID` key is saved in the SKSE co-save. A save without this record simply starts each item at its default state.
- Bows lose configured wear only after a completed `TESPlayerBowShotEvent` (cancelled draws cost nothing); crossbows use their separate configured base cost. Bound weapons are excluded. Wear-reduction is applied after the base cost and is clamped by the configured global cap.
- Quest and unique-item breakage rules will be enforced by the future zero-durability transaction. The current ranged-shot hook is non-destructive and only changes the tracked durability value.
- Ordinary non-unique equipment at zero durability is removed and converted into a partial set of forge-recipe materials.
- `AllowEnchantedItemsToBreak` defaults to `true`: when enabled, ordinary enchanted equipment follows the same break-and-salvage rule; when disabled, it becomes `broken` instead.
- Unique equipment always becomes `broken`; it is unequipped and cannot be used until repaired, regardless of the enchanted-item setting.
- Repair costs are calculated by missing-durability band and recipe material, then shown before consuming anything.
- HUD warnings fire on a threshold crossing with a cooldown, rather than once per hit.

## Event flow

```text
attack / hit
  -> resolve equipped item instance
  -> verify it participates
  -> subtract configured wear
  -> warn once when crossing threshold
  -> zero: break or salvage
  -> save item state to co-save
  -> push refreshed data to PrismaUI when open

completed bow / crossbow shot
  -> resolve the equipped item instance
  -> ignore bound weapons and cancelled draws
  -> subtract configured base wear after wear-reduction cap
  -> persist state through the next SKSE co-save

weapon equip / switch / `weaponDraw` animation
  -> resolve the player's equipped weapon
  -> show non-blocking HUD card with current / maximum durability
  -> if it is below the configured threshold, show the one-time low-durability warning

activate forge
  -> choose “原版锻造” or “装备工坊”
  -> open PrismaUI in forge context
  -> show a selectable equipment list and full selected-item details
  -> draft three validated enhancement cards; refresh consumes escalating gold
  -> user repairs or selects one card
  -> validate material inventory, outcome and limits again
  -> apply repair/enhancement result, update co-save
```

## Native/UI contract

The view receives `{ equipped, repairQueue, forge, settings }`. Equipment rows include their visible combat stats, weight, enchantment, protection flags and reinforcement rank. `forge` contains the station context and the current three card offers. The native side remains authoritative and revalidates all requests. The UI never decides whether an item is protected, broken, repairable, affordable, eligible for a card, or allowed to replace its enchantment.
