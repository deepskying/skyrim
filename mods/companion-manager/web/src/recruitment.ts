import type { GameFollower, Snapshot } from "./bridge";

export function recruitmentCandidates(snapshot: Snapshot | null, query: string) {
  const search = query.trim().toLowerCase();
  return (snapshot?.followers ?? []).filter((actor) =>
    !actor.managed && (actor.group === "nearby" || actor.group === "party") &&
    `${actor.name} ${actor.race} ${actor.id}`.toLowerCase().includes(search),
  ).sort((a, b) => Number(b.canRecruit) - Number(a.canRecruit) ||
    (a.distance ?? Infinity) - (b.distance ?? Infinity) || a.id.localeCompare(b.id));
}

export function recruitmentBlock(snapshot: Snapshot | null, actor: GameFollower, busy: boolean): string {
  if (!snapshot?.ready) return "请先进入游戏存档";
  if (!snapshot.managerAvailable) return "管理系统未就绪，请确认 CompanionManager.esp 已启用";
  if (busy) return "上一条操作正在处理";
  if (actor.managed) return "已纳入管理";
  if (snapshot.followers.filter((a) => a.managed).length >= 64) return "64 位名册已满，请先释放一位同伴";
  if (actor.dead || actor.unavailable) return "人物目前不可操作";
  if (!actor.canRecruit) return actor.reason || "此人物暂时不能招募";
  return "";
}
