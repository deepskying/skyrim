export type Spell = {
  id: number;
  name: string;
  school: string;
  cost: number;
};

export type Follower = {
  id: number;
  name: string;
  className: string;
  level: number;
  levelScaling: {
    playerScaled: boolean;
    multiplier: number;
    currentMax: number;
    originalMax: number;
    targetMax: number;
    enabled: boolean;
    canToggle: boolean;
  };
  maxMagicka: number;
  resources: {
    health: Resource;
    magicka: Resource;
    stamina: Resource;
  };
  spells: Spell[];
};

export type Resource = {
  current: number;
  max: number;
};

export type Tome = Spell & {
  spellId: number;
  spellName: string;
  count: number;
  value: number;
  description: string;
};

export type PanelState = {
  followers: Follower[];
  tomes: Tome[];
  message?: string;
};
