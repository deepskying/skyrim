// The equipment HUD shows the soul pool readout so capacity changes are visible without
// opening the workshop panel. Malformed rows are dropped instead of clamped.
export type SoulPoolHudSnapshot = { enabled: boolean; points: number; capacity: number; tier: number };
const whole = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? Math.floor(value) : undefined;
export function normalizeSoulPoolHud(value: unknown): SoulPoolHudSnapshot | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  if (raw.enabled !== true) return { enabled: false, points: 0, capacity: 0, tier: 0 };
  const points = whole(raw.points), capacity = whole(raw.capacity), tier = whole(raw.tier);
  if (points === undefined || capacity === undefined || capacity <= 0 || tier === undefined || tier < 0) return undefined;
  return { enabled: true, points: Math.max(0, Math.min(capacity, points)), capacity, tier };
}
