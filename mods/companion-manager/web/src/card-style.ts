// Card surfaces must stay translucent: the player watches the companion behind the window while
// dressing them, so a card only needs enough tint for text contrast. The alpha follows the
// panel-opacity preference inside bounds that stay readable and never become opaque.
export function cardAlpha(opacityPercent: number): number {
  const value = (Number.isFinite(opacityPercent) ? opacityPercent : 82) / 100 - 0.26;
  // Rounded so the generated CSS colour stays stable and readable in logs.
  return Math.round(Math.min(0.72, Math.max(0.34, value)) * 100) / 100;
}

export function cardStrongAlpha(alpha: number): number {
  return Math.min(0.9, alpha + 0.22);
}

// The follower grid and the wardrobe grid must read the same way, so both derive the card tone from
// the same party state. `party` means following, `waiting` is a companion parked where they were
// told to stay, `registry` is a dismissed record, `nearby` covers everyone we do not manage yet and
// `dead` keeps a subdued card for a corpse that still holds a roster record.
export type FollowerTone = "party" | "waiting" | "registry" | "nearby" | "dead";

export type FollowerState = {
  tone: FollowerTone;
  /** Short label for the corner badge. */
  badge: string;
  /** The wording the card footer has always used. */
  status: string;
};

export function followerState(f: {
  dead?: boolean;
  managed?: boolean;
  group?: string;
  waiting?: boolean;
  canRecruit?: boolean;
}): FollowerState {
  if (f.dead) return { tone: "dead", badge: "已死亡", status: "已死亡" };
  if (f.managed && f.group === "registry")
    return { tone: "registry", badge: "已离队", status: "已离队" };
  if (f.managed)
    return f.waiting
      ? { tone: "waiting", badge: "等待中", status: "原地等待" }
      : { tone: "party", badge: "同行中", status: "正在同行" };
  return f.canRecruit
    ? { tone: "nearby", badge: "待纳入", status: "待纳入管理" }
    : { tone: "nearby", badge: "外部", status: "外部随从" };
}
