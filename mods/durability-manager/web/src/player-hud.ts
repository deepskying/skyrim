export type PlayerHudSnapshot = {
  level: number;
  experience: number | null; experienceNext: number | null;
  fire: number | null; frost: number | null; shock: number | null; magic: number | null;
  poison: number | null; disease: number | null; armor: number | null; speed: number | null;
  gold: number | null; weight: number | null; carryWeight: number | null; gameMinutes: number | null;
};

// null means unavailable; keep negative resistance values (vulnerabilities).
export function normalizePlayerHud(value: unknown): PlayerHudSnapshot | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  const read = (key: string) => typeof raw[key] === 'number' && Number.isFinite(raw[key]) ? raw[key] as number : null;
  const level = read('level');
  if (level === null || level < 1) return undefined;
  const positive = (key: string) => { const n = read(key); return n === null ? null : Math.max(0, n); };
  const minutes = positive('gameMinutes');
  return { level: Math.floor(level), experience: positive('experience'), experienceNext: positive('experienceNext'),
    fire: read('fire'), frost: read('frost'), shock: read('shock'), magic: read('magic'),
    poison: read('poison'), disease: read('disease'), armor: read('armor'), speed: read('speed'),
    gold: positive('gold'), weight: positive('weight'), carryWeight: positive('carryWeight'),
    gameMinutes: minutes === null ? null : Math.floor(minutes) % 1440 };
}
