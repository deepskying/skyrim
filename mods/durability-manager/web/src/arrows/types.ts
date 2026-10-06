export type Stack = { id: number; count: number };
export type Adapter = { runtime?: boolean; family?: string; material?: string; charge?: number; mana?: number; gold?: number; releaseMode?: string; castRoute?: string };
export type Arrow = { id: number; name: string; count: number; damage: number; family: string; equipped?: boolean; usable?: boolean; bolt?: boolean; runtimeBase?: boolean; fireballBase?: boolean; spellBound?: boolean; adapter?: Adapter };
export type Spell = { id: number; name: string; source: string; craftable: boolean; adapter?: Adapter; eligibility?: { status: string; reasons: string[] } };
export type Material = { id: number; name: string; kind: string; count: number; units?: number; charges?: Record<string, number> };
export type Recipe = { id: number; name: string; source: string; yield: number; craftable: boolean; reason?: string; maxBatches: number; ingredients: { name: string; need: number; have: number }[]; conditions?: { name: string; met: boolean; orNext?: boolean }[] };
export type Selection = { spell: number; bases: Stack[]; materials: Stack[] };
export type Quote = { token: number; runtime?: boolean; selection: Selection; total: number; gold: number; magicka: number; suppliedCharge: number; ingredients: { name: string; count: number }[]; outputs: { name: string; count: number }[]; bases: Stack[] };
export type NormalQuote = { token: number; recipe: number; batches: number; total: number; name: string; ingredients: { name: string; count: number }[] };
export type SoulPool = {
  available: boolean; enabled: boolean; points: number; capacity: number; tier: number; absorbed: number;
  upgradeGold: number; upgradeGain: number; gold: number;
  // Two interchangeable plans per tier: same kind count, quantity and gold, different materials.
  // Every material carries the plugin that provides it, so a rare one can be traced back.
  options: { id: number; materials: { id: number; name: string; source: string; count: number; owned: number }[] }[];
  gems: { level: number; name: string; points: number; gold: number; id: number; can: number }[];
  deposit: { id: number; name: string; count: number; points: number; room: number }[];
};
export type ArrowState = {
  // Queued crafting orders, as reported by the native craft_order state.
  orders?: { entries: { spell: number; name: string; spellName?: string; label: string; total: number; remaining: number; progress: number; family?: string; manaPerArrow?: number }[]; paused?: boolean; reason?: string; limit?: number; pauseInCombat?: boolean; available?: boolean };
  craftingAccess?: { magic: boolean; normal: boolean };
  loaded: boolean; page?: string; mode?: string; message?: string;
  arrows: Arrow[]; spells: Spell[]; materials: Material[]; recipes: Recipe[];
  resources?: { gold: number; magicka: number }; alchemy?: number;
  // Weight of numeric effects that match no family, as configured in MagicArrows.ini.
  materialGenericPercent?: number;
  ammoQueue?: { available: boolean; enabled: boolean; ids: number[]; items?: Arrow[]; limit: number; finished?: boolean };
  followers?: { available: boolean; consumeMagicArrows: boolean };
  soulPool?: SoulPool;
  quote?: Quote | null; normalQuote?: NormalQuote | null;
  workshopReply?: { type: string; requestID: number; ok: boolean; error?: string } | null;
};
