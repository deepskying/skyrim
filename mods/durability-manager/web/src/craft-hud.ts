// Queued magic arrow crafting, as reported by the native craft_order state. The HUD keeps
// one diamond per spell: the ring traces the share still to craft, the count sits inside.
export type CraftOrderEntry = {
  spell: number; name: string; label: string;
  total: number; remaining: number; progress: number; family: string;
};
export type CraftOrderSnapshot = { entries: CraftOrderEntry[]; paused: boolean; reason: string };

// The twelve arrow model families drive the diamond tint; anything else falls back to arcane.
const families = new Set(['fire', 'ice', 'shock', 'poison', 'blood', 'holy', 'wind', 'water', 'earth', 'dark', 'soul', 'arcane']);
const whole = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? Math.floor(value) : undefined;
const text = (value: unknown) => typeof value === 'string' && value ? value : undefined;

// Malformed rows are dropped instead of clamped: a batch without a positive size cannot
// describe a ring, and the native side is the only writer of the remaining counts.
export function normalizeCraftOrders(value: unknown): CraftOrderSnapshot | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  if (!Array.isArray(raw.entries)) return undefined;
  const entries: CraftOrderEntry[] = [];
  const seen = new Set<number>();
  for (const row of raw.entries) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) continue;
    const entry = row as Record<string, unknown>;
    const spell = whole(entry.spell), total = whole(entry.total), remaining = whole(entry.remaining);
    if (spell === undefined || spell <= 0 || seen.has(spell) || total === undefined || remaining === undefined) continue;
    if (total <= 0 || remaining < 0 || remaining > total) continue;
    seen.add(spell);
    const family = text(entry.family);
    entries.push({ spell, total, remaining, progress: remaining / total,
      family: family && families.has(family) ? family : 'arcane',
      name: text(entry.name) ?? '魔法箭', label: text(entry.label) ?? String(remaining) });
  }
  return { entries, paused: raw.paused === true, reason: text(raw.reason) ?? '' };
}

// One wrapped row of diamonds stays readable, so shorter screens show fewer spells and
// report the rest as a count instead of pushing the durability list off the bottom edge.
export function craftOrderHudLimit(viewportHeight: number) {
  if (!Number.isFinite(viewportHeight) || viewportHeight <= 0) return 8;
  if (viewportHeight < 800) return 4;
  return viewportHeight < 1000 ? 6 : 8;
}
