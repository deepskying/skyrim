import type { Follower } from "./demo";
import {validOutfits,type Outfits} from "./outfits.ts";
import {armorTypes,validBehavior,validWardrobe,type BehaviorSettings,type WardrobeItem,type Automation,type ArmorType} from "./behavior.ts";

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
  outfits?:Outfits;
  wardrobe?:WardrobeItem[]; behavior?:BehaviorSettings; behaviorOverride?:boolean;
  carried?:number;capacity?:number;activity?:string;request?:string;
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
  savedOutfitChance?:number;
  opacity: number;
  font: number;
  distance: number;
  notifications: boolean;
  sandbox: boolean;
};
export type Snapshot = {
  automation?:Automation;
  version: 3;
  session: string;
  managerAvailable: boolean;
  settings: Settings;
  inventory: InventoryItem[];
  mode: "game";
  ready: boolean;
  followers: GameFollower[];
  // The player's own wardrobe card: a companion-shaped outfit payload without a member entry.
  self?: SelfCard;
  location: string;
  truncated: boolean;
};
export type SelfCard = {
  id: string;
  name: string;
  outfits?: Outfits;
  dead?: boolean;
  unavailable?: boolean;
  inCombat?: boolean;
  presetCount?: number;
};

declare global {
  interface Window {
    __companionPreview?: boolean;
    // Design-preview only: lets the HTTP page stand in for a Meridian renderer when the wear page
    // asks what state the 3D viewport is in. The game never reads it.
    __companionPreviewStatus?: string;
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
    (v.savedOutfitChance===undefined||(Number.isInteger(v.savedOutfitChance)&&Number(v.savedOutfitChance)>=0&&Number(v.savedOutfitChance)<=100))&&
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
    value.version !== 3 ||
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
    if(record(f)&&f.outfits!==undefined&&!validOutfits(f.outfits))return null;
    if(record(f)&&((f.wardrobe!==undefined&&!validWardrobe(f.wardrobe))||(f.behavior!==undefined&&!validBehavior(f.behavior))||
       ["carried","capacity"].some(k=>f[k]!==undefined&&(!number(f[k])||(f[k] as number)<0))||
       (f.behaviorOverride!==undefined&&typeof f.behaviorOverride!=="boolean")||
       ["activity","request"].some(k=>f[k]!==undefined&&typeof f[k]!=="string")))return null;
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
  if(value.automation!==undefined) {
    const a=value.automation;
    if(!record(a)||!validBehavior(a.defaults)||!number(a.playerCarried)||!number(a.playerCapacity)||!Array.isArray(a.history)||a.history.length>40||a.history.some(x=>typeof x!=="string"))return null;
  }
  if(value.self!==undefined) {
    const selfRow=value.self;
    if(!record(selfRow)||!formID(selfRow.id)||typeof selfRow.name!=="string"||
       (selfRow.outfits!==undefined&&!validOutfits(selfRow.outfits)))return null;
  }
  return value as unknown as Snapshot;
}

export type SnapshotRead = { snapshot: Snapshot | null; issues: string[] };

const MAX_ISSUES = 6;

const finiteNumber = (v: unknown): number | null =>
  typeof v === "number" && Number.isFinite(v) ? v : null;
const nonNegative = (v: unknown): number => {
  const n = finiteNumber(v);
  return n === null ? 0 : Math.max(0, n);
};
const wholeNumber = (v: unknown): number => {
  const n = nonNegative(v);
  return Number.isInteger(n) ? n : Math.round(n);
};
const numberPair = (v: unknown): [number, number] =>
  Array.isArray(v) && v.length === 2 ? [wholeNumber(v[0]), wholeNumber(v[1])] : [0, 0];
const text = (v: unknown, fallback = "") => (typeof v === "string" ? v : fallback);
const instanceKey = (v: unknown): string =>
  typeof v === "string" && /^[0-9A-F]{8}:[0-9A-F]{8}:[0-9A-F]{4}$/.test(v) ? v : "";
const field = (v: unknown, key: string) =>
  record(v) ? v[key] : undefined;

function uniqueByKey(items: unknown[], keyOf: (item: unknown) => string) {
  const seen = new Set<string>();
  const kept: unknown[] = [];
  for (const item of items) {
    const id = keyOf(item);
    if (!id || seen.has(id)) continue;
    seen.add(id);
    kept.push(item);
  }
  return kept;
}

function repairStats(value: unknown): unknown[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (s) =>
        record(s) && typeof s.name === "string" && finiteNumber(s.value) !== null,
    )
    .slice(0, 32);
}

function repairSpells(value: unknown): unknown[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const spells: unknown[] = [];
  for (const s of value) {
    const id = field(s, "id");
    if (!record(s) || !formID(id) || seen.has(id)) continue;
    seen.add(id);
    spells.push({
      id,
      name: text(field(s, "name")),
      school: text(field(s, "school")),
      description: text(field(s, "description")),
      cost: nonNegative(field(s, "cost")),
      enabled:
        typeof field(s, "enabled") === "boolean" ? field(s, "enabled") : true,
    });
    if (spells.length >= 512) break;
  }
  return spells;
}

function repairGear(value: unknown): unknown[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const gear: unknown[] = [];
  for (const g of value) {
    const id = field(g, "id");
    if (!record(g) || !formID(id) || seen.has(id)) continue;
    seen.add(id);
    gear.push({
      id,
      name: text(field(g, "name")),
      slot: text(field(g, "slot")),
      count: wholeNumber(field(g, "count")),
      equipped: field(g, "equipped") === true,
      quest: field(g, "quest") === true,
    });
    if (gear.length >= 512) break;
  }
  return gear;
}

// The wear page reads native armor fields that older or partly broken payloads may miss. A bad
// value is dropped rather than blanking the whole row, so the item stays usable.
function repairWearFields(row: unknown, note: (text: string) => void): unknown {
  if (!record(row)) return row;
  const out: Record<string, unknown> = { ...row };
  let dropped = 0;
  const drop = (key: string) => {
    if (out[key] === undefined) return;
    delete out[key];
    dropped++;
  };
  if (out.mask !== undefined) {
    const mask = finiteNumber(out.mask);
    if (mask === null || !Number.isInteger(mask) || mask <= 0 || mask > 0xffffffff) drop("mask");
  }
  if (out.armorRating !== undefined) {
    const rating = finiteNumber(out.armorRating);
    if (rating === null || rating < 0) drop("armorRating");
    else out.armorRating = Math.min(100000, rating);
  }
  if (out.armorType !== undefined && !armorTypes.includes(out.armorType as ArmorType))
    drop("armorType");
  if (
    out.enchantment !== undefined &&
    (typeof out.enchantment !== "string" || out.enchantment.length > 4096)
  )
    drop("enchantment");
  if (dropped > 0) note("伙伴装备的部分数值无法读取，已按安全值显示。");
  return out;
}

function repairWardrobe(value: unknown, note: (text: string) => void): unknown[] {
  if (!Array.isArray(value)) return [];
  const repaired = value.map((row) => repairWearFields(row, note));
  const rows = uniqueByKey(
    repaired.filter((row) => record(row) && validWardrobe([row])),
    (row) => instanceKey(field(row, "key")),
  );
  const dropped = value.length - rows.length;
  if (dropped > 0)
    note(`伙伴库存里有 ${dropped} 条重复或异常的记录已跳过。`);
  return rows.slice(0, 512);
}

function repairOutfits(
  value: unknown,
  note: (text: string) => void,
): unknown | undefined {
  if (!record(value)) return undefined;
  const rawItems = Array.isArray(value.items) ? value.items : [];
  const items = uniqueByKey(rawItems, (i) => instanceKey(field(i, "key")));
  const rawPresets = Array.isArray(value.presets) ? value.presets : [];
  const presets = rawPresets.slice(0, 64).map((preset) => {
    if (!record(preset)) return preset;
    const saved = Array.isArray(preset.items) ? preset.items : [];
    return {
      ...preset,
      items: uniqueByKey(saved, (i) => instanceKey(field(i, "key"))).slice(0, 64),
    };
  });
  const repaired = {
    ...value,
    items: items.slice(0, 576),
    presets,
    pending: typeof value.pending === "boolean" ? value.pending : false,
  };
  if (rawItems.length !== items.length)
    note("伙伴穿搭里有重复或异常的服饰记录，已跳过。");
  if (!validOutfits(repaired)) {
    note("伙伴穿搭数据无法读取，已暂时隐藏该页签。");
    return undefined;
  }
  return repaired;
}

function repairFollower(
  row: unknown,
  note: (text: string) => void,
): unknown | null {
  if (!record(row)) return null;
  const id = row.id;
  if (typeof id !== "string" || !/^[0-9A-F]{8}$/.test(id)) return null;
  const group = row.group;
  if (!["party", "registry", "nearby"].includes(text(group))) return null;
  const managed =
    typeof row.managed === "boolean" ? row.managed : group === "registry";
  const out: Record<string, unknown> = {
    ...row,
    id,
    name: text(row.name, "未命名人物"),
    en: text(row.en, id),
    role: text(row.role, "未分类"),
    race: text(row.race, "未知种族"),
    mark: text(row.mark, "人"),
    tint: text(row.tint, "blue"),
    home: text(row.home, "未设置"),
    location: text(row.location, "未知位置"),
    managed,
    limited: !managed,
    canRecruit: row.canRecruit === true,
    canRaise: row.canRaise === true,
    dead: row.dead === true,
    unavailable: row.unavailable === true,
    reason: text(row.reason),
    originalMax: wholeNumber(row.originalMax),
    presetCount: wholeNumber(row.presetCount),
    level: wholeNumber(row.level),
    distance: row.distance === null ? null : nonNegative(row.distance),
    levelCap: row.levelCap === null ? null : nonNegative(row.levelCap),
    waiting: row.waiting === true,
    passive: row.passive === true,
    sandbox: row.sandbox === true,
    leash: row.leash === true,
    essential: row.essential === true,
    raised: row.raised === true,
    inCombat: row.inCombat === true,
    detailsTruncated: row.detailsTruncated === true,
    health: numberPair(row.health),
    magicka: numberPair(row.magicka),
    stamina: numberPair(row.stamina),
    skills: repairStats(row.skills),
    resistances: repairStats(row.resistances),
    attributes: repairStats(row.attributes),
    spells: repairSpells(row.spells),
    gear: repairGear(row.gear),
  };
  if (row.wardrobe !== undefined)
    out.wardrobe = repairWardrobe(row.wardrobe, note);
  if (row.outfits !== undefined) {
    const outfits = repairOutfits(row.outfits, note);
    if (outfits === undefined) delete out.outfits;
    else out.outfits = outfits;
  }
  if (row.behavior !== undefined) {
    if (validBehavior(row.behavior)) out.behavior = row.behavior;
    else {
      delete out.behavior;
      note("有伙伴的个人行为规则异常，已改回全队默认值。");
    }
  }
  if (row.behaviorOverride !== undefined && typeof row.behaviorOverride !== "boolean")
    delete out.behaviorOverride;
  for (const key of ["carried", "capacity"])
    if (out[key] !== undefined) out[key] = nonNegative(out[key]);
  for (const key of ["activity", "request"])
    if (out[key] !== undefined) out[key] = text(out[key]);
  return out;
}

// Native output is repaired before validation: one odd value, duplicate identity or oversized
// list must never blank the panel. Everything dropped is reported so the cause stays visible.
function repairSnapshot(value: unknown, note: (text: string) => void): unknown {
  if (!record(value)) return value;
  const out: Record<string, unknown> = { ...value };
  if (Array.isArray(out.inventory)) {
    const items = out.inventory.filter(
      (item) => record(item) && validInventory([item]),
    );
    if (items.length !== out.inventory.length)
      note(
        `背包里有 ${out.inventory.length - items.length} 条重复或异常的记录已跳过。`,
      );
    out.inventory = items.slice(0, 512);
  }
  if (record(out.settings)) {
    const raw = out.settings;
    const bounded = (key: string, lo: number, hi: number, fallback: number) => {
      const current = raw[key];
      if (
        typeof current === "number" &&
        Number.isInteger(current) &&
        current >= lo &&
        current <= hi
      )
        return current;
      const fixed = Math.min(hi, Math.max(lo, Math.round(nonNegative(current))));
      note(`界面设置 ${key} 数值异常，已按安全值显示。`);
      return current === undefined ? fallback : fixed;
    };
    const chance = raw.savedOutfitChance;
    const savedOutfitChance =
      chance === undefined
        ? undefined
        : typeof chance === "number" &&
            Number.isInteger(chance) &&
            chance >= 0 &&
            chance <= 100
          ? chance
          : (note("整套随机概率异常，已恢复默认值。"), 70);
    out.settings = {
      savedOutfitChance,
      opacity: bounded("opacity", 55, 96, 82),
      font: bounded("font", 14, 18, 16),
      distance: bounded("distance", 0, 2, 1),
      notifications: raw.notifications === true,
      sandbox: raw.sandbox !== false,
    };
  }
  if (out.self !== undefined) {
    const row = out.self;
    if (!record(row) || !formID(row.id)) {
      delete out.self;
      note("玩家穿搭数据异常，已隐藏玩家卡片。");
    } else {
      const fixed: Record<string, unknown> = {
        ...row,
        name: text(row.name, "你"),
        dead: row.dead === true,
        unavailable: row.unavailable === true,
        inCombat: row.inCombat === true,
        presetCount: wholeNumber(row.presetCount),
      };
      if (row.outfits !== undefined) {
        const outfits = repairOutfits(row.outfits, note);
        if (outfits === undefined) delete fixed.outfits;
        else fixed.outfits = outfits;
      }
      out.self = fixed;
    }
  }
  if (Array.isArray(out.followers)) {
    const before = out.followers;
    const seen = new Set<string>();
    const rows: unknown[] = [];
    let dropped = 0;
    for (const row of before) {
      const fixed = repairFollower(row, note);
      const id = field(fixed, "id");
      if (!fixed || typeof id !== "string" || seen.has(id)) {
        dropped++;
        continue;
      }
      seen.add(id);
      rows.push(fixed);
    }
    out.followers = rows.slice(0, 128);
    if (dropped > 0) note(`已跳过 ${dropped} 名数据异常或重复的人物。`);
    else if (before.length > 128) note("人物较多，只显示前 128 位。");
  }
  if (record(out.automation)) {
    const automation = out.automation;
    if (!validBehavior(automation.defaults)) {
      delete out.automation;
      note("全队行为默认值异常，已暂停自动行为显示。");
    } else {
      const history = Array.isArray(automation.history)
        ? automation.history.filter((entry) => typeof entry === "string")
        : [];
      out.automation = {
        ...automation,
        history: history.slice(0, 40),
        playerCarried: nonNegative(automation.playerCarried),
        playerCapacity: nonNegative(automation.playerCapacity),
      };
    }
  }
  return out;
}

// Reads a native snapshot for display: repair, validate, and report what was skipped.
export function readSnapshot(value: unknown): SnapshotRead {
  const issues: string[] = [];
  const note = (message: string) => {
    if (issues.length < MAX_ISSUES && !issues.includes(message)) issues.push(message);
  };
  const snapshot = parseSnapshot(repairSnapshot(value, note));
  if (!snapshot && record(value)) {
    issues.unshift("游戏数据无法解析，请更新完整安装包后重试。");
    issues.length = Math.min(issues.length, MAX_ISSUES);
  }
  return { snapshot, issues };
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

// Item panels name the companion whose inventory they are showing. Native then only builds that
// one companion's wardrobe/outfit payload, which is the expensive half of a snapshot; an empty id
// restores the full snapshot.
export function focusWardrobe(actorId: string): boolean {
  return send({ type: "focus", actorId });
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
