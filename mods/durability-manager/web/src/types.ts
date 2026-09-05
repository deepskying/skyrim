export type EnhancementTier = '微弱' | '标准' | '强效' | '极强';
export type CardType = 'performance' | 'weight' | 'speed' | 'durability' | 'wear' | 'charge' | 'enchantment';

export type MaterialRequirement = { name: string; required: number; owned: number; isGold?: boolean };

export type RefreshResult = { requestId: string; equipmentId: string; success: boolean; goldSpent: number; message: string };

export type EquipmentItem = {
  // Native emits the stable `baseFormID:uniqueID` instance key. It must not
  // be reduced to a base FormID: players can own several copies of one item.
  id: string;
  name: string;
  slot: string;
  category: 'weapon' | 'armor' | 'clothing';
  equipped: boolean;
  quantity: number;
  current: number;
  maximum: number;
  enhancementLevel: number;
  damage?: number;
  armor?: number;
  weight: number;
  attackSpeed?: number;
  chargeCurrent?: number;
  chargeCapacity?: number;
  chargeBonus?: number;
  /** Effective durability cost of one supported action, after wear reduction. */
  wearRate?: number | null;
  wearRateLabel?: string;
  wearReduction?: number;
  enchantment?: string;
  enchanted: boolean;
  enchantmentReplaceable: boolean;
  quest: boolean;
  unique: boolean;
  broken: boolean;
  repairable: boolean;
  repairMaterials: MaterialRequirement[];
};

export type EnhancementCard = {
  id: string;
  /** Exact native instance owning this offer; prevents stale cards during selection changes. */
  equipmentId: string;
  preview: { label: string; before: string; after: string }[];
  type: CardType;
  tier: EnhancementTier;
  title: string;
  description: string;
  value: string;
  successChance: number;
  materials: MaterialRequirement[];
  blockedReason?: string;
};

export type ForgeState = {
  active: boolean;
  station: string;
  gold: number;
  refreshCost: number;
  refreshes: number;
  cards: EnhancementCard[];
};

export type Settings = {
  hotkey: { key: string; keyCode: number; shift: boolean; ctrl: boolean; alt: boolean };
  lowDurabilityThreshold: number;
  weaponDisplaySeconds: number;
  enableLowDurabilityWarning: boolean;
  enableWorkshopSounds: boolean;
  allowEnchantedItemsToBreak: boolean;
};

export type PanelState = {
  refreshResult?: RefreshResult;
  version: string;
  equipped: EquipmentItem[];
  repairQueue: EquipmentItem[];
  forge: ForgeState;
  settings: Settings;
  capturingHotkey: boolean;
  message?: string;
};
