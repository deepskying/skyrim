export type Spell = {
  id: number;
  name: string;
  school: string;
  cost: number;
};

export type Follower = {
  id: number;
  name: string;
  spells: Spell[];
};

export type Tome = Spell & {
  spellId: number;
  spellName: string;
  count: number;
};

export type PanelState = {
  followers: Follower[];
  tomes: Tome[];
  message?: string;
};
