import type { Follower } from "./demo";

export type InventoryItem = {
  description?: string;
  spellDescription?: string;
  school?: string;
  cost?: number;
  id: string;
  name: string;
  count: number;
  quest: boolean;
  equipped: boolean;
  spellId: string;
  spellName: string;
};
export type GameFollower = Omit<Follower, "gear"> & {
  managed: boolean;
  canRecruit: boolean;
  reason: string;
  canRaise: boolean;
  originalMax: number;
  presetCount: number;
  dead: boolean;
  unavailable: boolean;
  attributes?: { name: string; value: number }[];
  skills: { name: string; value: number }[];
  resistances: { name: string; value: number }[];
  gear: (Follower["gear"][number] & {
    id: string;
    count: number;
    quest: boolean;
  })[];
};
export type Settings = {
  opacity: number;
  font: number;
  distance: number;
  notifications: boolean;
  sandbox: boolean;
};
export type Snapshot = {
  version: 2;
  session: string;
  managerAvailable: boolean;
  settings: Settings;
  inventory: InventoryItem[];
  mode: "game";
  ready: boolean;
  followers: GameFollower[];
  location: string;
  truncated: boolean;
};

declare global {
  interface Window {
    __companionPreview?: boolean;
    companionRequest?: (payload: string) => void;
    __companionSnapshot?: unknown;
  }
}

const record = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
const number = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v) && v >= 0;
const pair = (v: unknown) =>
  Array.isArray(v) && v.length === 2 && v.every(number);

const formID = (v: unknown): v is string =>
  typeof v === "string" && /^[0-9A-F]{8}$/.test(v) && v !== "00000000";
const stats = (v: unknown) =>
  Array.isArray(v) &&
  v.length <= 32 &&
  v.every(
    (s) =>
      record(s) &&
      typeof s.name === "string" &&
      typeof s.value === "number" &&
      Number.isFinite(s.value),
  );
function validSettings(v: unknown) {
  return (
    record(v) &&
    [
      ["opacity", 55, 96],
      ["font", 14, 18],
      ["distance", 0, 2],
    ].every(
      ([k, lo, hi]) =>
        typeof v[k] === "number" &&
        Number.isInteger(v[k]) &&
        (v[k] as number) >= Number(lo) &&
        (v[k] as number) <= Number(hi),
    ) &&
    typeof v.notifications === "boolean" &&
    typeof v.sandbox === "boolean"
  );
}
function validInventory(items: unknown[]) {
  const ids = new Set<string>();
  return items.every((i) => {
    if (
      !record(i) ||
      !formID(i.id) ||
      ids.has(i.id) ||
      typeof i.name !== "string" ||
      !number(i.count) ||
      !Number.isInteger(i.count) ||
      typeof i.quest !== "boolean" ||
      typeof i.equipped !== "boolean" ||
      !(i.spellId === "" || formID(i.spellId)) ||
      typeof i.spellName !== "string" ||
      ["description", "spellDescription", "school"].some(
        (k) => i[k] !== undefined && typeof i[k] !== "string",
      ) ||
      (i.cost !== undefined && !number(i.cost))
    )
      return false;
    ids.add(i.id);
    return true;
  });
}

// Validate the entire snapshot before replacing displayed data. Native IDs are stable
// within this loaded save; names are presentation only and must never identify commands.
export function parseSnapshot(value: unknown): Snapshot | null {
  if (
    !record(value) ||
    value.version !== 2 ||
    typeof value.session !== "string" ||
    !value.session ||
    value.session.length > 128 ||
    typeof value.managerAvailable !== "boolean" ||
    !validSettings(value.settings) ||
    !Array.isArray(value.inventory) ||
    value.inventory.length > 512 ||
    !validInventory(value.inventory) ||
    value.mode !== "game" ||
    typeof value.ready !== "boolean" ||
    typeof value.location !== "string" ||
    typeof value.truncated !== "boolean" ||
    !Array.isArray(value.followers) ||
    value.followers.length > 128
  )
    return null;
  const ids = new Set<string>();
  for (const f of value.followers) {
    if (
      !record(f) ||
      ![
        "id",
        "name",
        "en",
        "role",
        "race",
        "mark",
        "tint",
        "home",
        "location",
      ].every((k) => typeof f[k] === "string") ||
      !/^[0-9A-F]{8}$/.test(f.id as string) ||
      ids.has(f.id as string) ||
      !["party", "registry", "nearby"].includes(f.group as string) ||
      typeof f.limited !== "boolean" ||
      !["managed", "canRecruit", "canRaise", "dead", "unavailable"].every(
        (k) => typeof f[k] === "boolean",
      ) ||
      f.limited === f.managed ||
      (f.group === "registry" && !f.managed) ||
      typeof f.reason !== "string" ||
      !number(f.originalMax) ||
      !number(f.presetCount) ||
      !stats(f.skills) ||
      (f.attributes !== undefined && !stats(f.attributes)) ||
      !stats(f.resistances) ||
      ![
        "waiting",
        "passive",
        "sandbox",
        "leash",
        "essential",
        "raised",
        "inCombat",
        "detailsTruncated",
      ].every((k) => typeof f[k] === "boolean") ||
      !number(f.level) ||
      !(f.distance === null || number(f.distance)) ||
      !(f.levelCap === null || number(f.levelCap)) ||
      !pair(f.health) ||
      !pair(f.magicka) ||
      !pair(f.stamina) ||
      !Array.isArray(f.spells) ||
      f.spells.length > 512 ||
      !Array.isArray(f.gear) ||
      f.gear.length > 512
    )
      return null;
    ids.add(f.id as string);
    const spellIds = new Set<string>();
    for (const s of f.spells) {
      if (
        !record(s) ||
        !formID(s.id) ||
        spellIds.has(s.id) ||
        typeof s.name !== "string" ||
        typeof s.school !== "string" ||
        !number(s.cost) ||
        (s.description !== undefined && typeof s.description !== "string") ||
        typeof s.enabled !== "boolean"
      )
        return null;
      spellIds.add(s.id);
    }
    const gearIds = new Set<string>();
    for (const g of f.gear) {
      if (
        !record(g) ||
        !formID(g.id) ||
        gearIds.has(g.id) ||
        typeof g.name !== "string" ||
        typeof g.slot !== "string" ||
        typeof g.equipped !== "boolean" ||
        !Number.isInteger(g.count) ||
        !number(g.count) ||
        typeof g.quest !== "boolean"
      )
        return null;
      gearIds.add(g.id);
    }
  }
  return value as unknown as Snapshot;
}

export function isGameLocation(protocol: string, search: string) {
  return (
    protocol === "mod:" || new URLSearchParams(search).get("runtime") === "game"
  );
}

export function send(payload: Record<string, unknown>): boolean {
  if (typeof window.companionRequest !== "function") return false;
  try {
    window.companionRequest(JSON.stringify(payload));
    return true;
  } catch {
    return false;
  }
}

export function request(type: "refresh" | "close"): boolean {
  return send({ type });
}

export function percent(value: number, maximum: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(maximum) || maximum <= 0)
    return 0;
  return Math.max(0, Math.min(100, (value / maximum) * 100));
}

export function closeKey(
  e: Pick<
    KeyboardEvent,
    | "key"
    | "code"
    | "shiftKey"
    | "ctrlKey"
    | "altKey"
    | "metaKey"
    | "repeat"
    | "isComposing"
  >,
  editing: boolean,
) {
  if (e.repeat || e.isComposing) return false;
  return (
    e.key === "Escape" ||
    (!editing &&
      e.code === "KeyF" &&
      e.shiftKey &&
      !e.ctrlKey &&
      !e.altKey &&
      !e.metaKey)
  );
}
