export type Page = 'inventory' | 'magic' | 'hotkeys';

export type HotkeyAction = 'open' | 'favorite' | 'activate' | 'pageToggle' | 'search';

export type HotkeyBinding = {
  action: HotkeyAction;
  key: string;
  keyCode: number;
  shift: boolean;
  ctrl: boolean;
  alt: boolean;
};

export type ItemCategory = 'favorites' | 'all' | 'weapons' | 'armor' | 'potions' | 'scrolls' | 'food' | 'ingredients' | 'misc';
export type MagicCategory = 'favorites' | 'all' | 'destruction' | 'alteration' | 'illusion' | 'restoration' | 'conjuration' | 'shouts' | 'powers' | 'status';

export type InventoryItem = {
  id: number;
  name: string;
  category: Exclude<ItemCategory, 'favorites' | 'all'>;
  icon: string;
  count: number;
  weight: number;
  value: number;
  favorited: boolean;
  equipped: boolean;
  enchanted: boolean;
  quest: boolean;
  description?: string;
  statLabel?: string;
  statValue?: number;
  equippedValue?: number;
  statDelta?: number;
  enchantments?: Array<{
    name: string;
    magnitude?: number;
    duration?: number;
  }>;
};

export type MagicItem = {
  id: number;
  name: string;
  category: Exclude<MagicCategory, 'favorites' | 'all'>;
  icon: string;
  cost?: number;
  cooldown?: number;
  favorited: boolean;
  equipped: boolean;
  active?: boolean;
  description?: string;
};

export type PanelState = {
  inventory: InventoryItem[];
  magic: MagicItem[];
  player: {
    gold: number;
    weight: number;
    weightMax: number;
  };
  hotkeys?: HotkeyBinding[];
  capturingAction?: HotkeyAction | null;
  message?: string;
};
