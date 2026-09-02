# Durability Manager architecture

## State ownership

| State | Owner | Persistence |
| --- | --- | --- |
| Hotkey, warning threshold, HUD preference, display duration | Native plugin | `DurabilityManager.ini` |
| Current/max durability and broken flag for each item instance | Native plugin | SKSE co-save |
| UI selection and active tab | Prisma view | Session only |

Durability must be recorded against a stable **item-instance identity**, never solely a base FormID. A base FormID is shared by every steel sword, while an enchanted sword, a renamed sword, and a unique sword may need distinct state. The future bridge therefore needs an instance key backed by Skyrim extra-data / a generated persistent ID, with form-ID resolution during co-save load.

## Gameplay rules

- Quest objects and configured artifacts are excluded before every durability mutation.
- Ordinary non-unique equipment at zero durability is removed and converted into a partial set of forge-recipe materials.
- `AllowEnchantedItemsToBreak` defaults to `true`: when enabled, ordinary enchanted equipment follows the same break-and-salvage rule; when disabled, it becomes `broken` instead.
- Unique equipment always becomes `broken`; it is unequipped and cannot be used until repaired, regardless of the enchanted-item setting.
- Repair costs are calculated by missing-durability band and recipe material, then shown before consuming anything.
- HUD warnings fire on a threshold crossing with a cooldown, rather than once per hit.

## Event flow

```text
attack / hit / equip
  -> resolve equipped item instance
  -> verify it participates
  -> subtract configured wear
  -> warn once when crossing threshold
  -> zero: break or salvage
  -> save item state to co-save
  -> push refreshed data to PrismaUI when open

activate forge
  -> choose “原版锻造” or “修复装备”
  -> open PrismaUI in forge context
  -> user selects hammer icon
  -> validate material inventory again
  -> remove materials, restore durability, update co-save
```

## Native/UI contract

The view receives `{ equipped, repairQueue, atForge, settings }`. Repair rows provide `material` and `materialCount`; the native side remains authoritative and revalidates all requests. The UI never decides whether an item is protected, broken, repairable, or affordable.
