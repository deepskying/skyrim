import type { WardrobeItem } from "./behavior.ts";
import { itemCategory } from "./inventory.ts";
import { outfitSlots, slotName } from "./outfits.ts";

// The wear page lists the apparel half of the follower's inventory - everything SkyUI shows under
// apparel, jewelry and shields included - and needs nothing but the row's own armor data.
export type WearRow = WardrobeItem & { mask: number };

export const wearRows = (items: WardrobeItem[] | undefined): WearRow[] =>
  (items ?? []).filter(
    (i): i is WearRow =>
      itemCategory(i) === "apparel" && typeof i.mask === "number" && i.mask > 0,
  );

export function searchWear(rows: WearRow[], query: string): WearRow[] {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return rows;
  return rows.filter((row) => row.name.toLocaleLowerCase().includes(needle));
}

export const wearSlots = (row: WearRow) => outfitSlots(row.mask);
export const wearSlotNames = (row: WearRow) => wearSlots(row).map(slotName);

export const clampIndex = (index: number, length: number) => {
  if (length <= 0) return -1;
  return Math.max(0, Math.min(length - 1, index));
};

// Arrow keys walk the list without wrapping, and an untouched list starts at its first row.
export function nextSelection(index: number, length: number, delta: number) {
  if (length <= 0) return -1;
  if (index < 0) return 0;
  return clampIndex(index + delta, length);
}

export type WearOutcome = {
  action: "wear" | "takeOff";
  current: number;
  next: number;
  delta: number;
  replaced: WearRow[];
};

// What the click will actually do: a piece that is on comes off, a piece that is off goes on and
// takes off whatever occupied its slots. The armor value is the total of everything worn after
// that action, so the number the player reads is the number they will end up with. Ratings arrive
// as floats (they include fractional enchantment and perk contributions); the page shows whole
// points, and delta is derived from the rounded pair so the three numbers always add up.
export function wearOutcome(rows: WearRow[], item: WearRow): WearOutcome {
  const worn = rows.filter((row) => row.equipped && row.key !== item.key);
  const total = rows.reduce(
    (sum, row) => sum + (row.equipped ? (row.armorRating ?? 0) : 0),
    0,
  );
  const current = Math.round(total);
  if (item.equipped) {
    const next = Math.round(total - (item.armorRating ?? 0));
    return { action: "takeOff", current, next, delta: next - current, replaced: [] };
  }
  const replaced = worn.filter((row) => (row.mask & item.mask) !== 0);
  const next = Math.round(
    total -
      replaced.reduce((sum, row) => sum + (row.armorRating ?? 0), 0) +
      (item.armorRating ?? 0),
  );
  return { action: "wear", current, next, delta: next - current, replaced };
}

// Native answers every status poll with one of these; "empty" is the page's own state for a list
// with nothing selected, and each one has exactly one message the player can act on.
export type PreviewStatus="empty"|"loading"|"ready"|"unsupported"|"failed"|"unavailable";
export const previewLabels:Record<PreviewStatus,string>={
  empty:"选择左侧的服饰预览模型",
  loading:"正在加载模型…",
  ready:"拖动旋转 · 滚轮缩放",
  unsupported:"此物品暂不支持模型预览",
  failed:"模型加载失败",
  unavailable:"模型预览未连接",
};
export const previewLabel=(status:string):string=>
  previewLabels[status as PreviewStatus]??previewLabels.loading;

// Quest gear stays on: the page may put it on but never take it off, exactly like the native
// command, which refuses to unequip anything the game protects.
export const canToggle = (row: WearRow) => !(row.equipped && row.quest);
