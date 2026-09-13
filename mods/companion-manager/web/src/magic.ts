import type { GameFollower, InventoryItem, Snapshot } from "./bridge";

// Render book text as plain text, never as game-provided HTML.
export function plainDescription(value?: string): string {
  return (value ?? "")
    .replace(/<\s*br\s*\/?\s*>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .trim();
}
export function teachingBlock(
  s: Snapshot | null,
  f: GameFollower | undefined,
  book: InventoryItem,
  busy: boolean,
): string {
  if (!s?.ready) return "请先进入游戏存档";
  if (!s.managerAvailable)
    return "请在 MO2 右侧启用 CompanionManager.esp，重新启动游戏";
  if (busy) return "上一条操作正在处理";
  if (!f) return "请先选择同伴";
  if (f.dead || f.unavailable) return "人物目前不可操作，请稍后刷新";
  if (!f.managed)
    return f.canRecruit
      ? "请先点击上方「纳入同行管理」，随后即可传授"
      : f.reason || "此人物目前无法纳入同行管理";
  if (book.quest) return "任务法术书不能消耗";
  if (book.count < 1) return "背包中已没有这本法术书";
  if (!book.spellId) return "这本书不包含可传授的普通法术";
  if (f.spells.some((spell) => spell.id === book.spellId))
    return "该角色已掌握此法术（包括已禁用的法术）";
  return "";
}
