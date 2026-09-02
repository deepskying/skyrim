export type EquipmentItem = {
  id: number;
  name: string;
  slot: string;
  current: number;
  maximum: number;
  enchanted: boolean;
  quest: boolean;
  broken: boolean;
  repairable: boolean;
  material?: string;
  materialCount?: number;
};

export type Settings = {
  hotkey: { key: string; keyCode: number; shift: boolean; ctrl: boolean; alt: boolean };
  lowDurabilityThreshold: number;
  weaponDisplaySeconds: number;
  enableLowDurabilityWarning: boolean;
  allowEnchantedItemsToBreak: boolean;
};

export type PanelState = {
  equipped: EquipmentItem[];
  repairQueue: EquipmentItem[];
  atForge: boolean;
  settings: Settings;
  capturingHotkey: boolean;
  message?: string;
};
