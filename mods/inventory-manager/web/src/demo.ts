import type { PanelState } from './types';

export const demoState: PanelState = {
  player: { gold: 2847, weight: 263, weightMax: 320 },
  message: 'Shift+D opens this panel. Alt changes between inventory and magic.',
  inventory: [
    { id: 1, name: 'Glass Sword of Frost', category: 'weapons', icon: 'weapon', count: 1, weight: 8, value: 780, favorited: true, equipped: true, enchanted: true, quest: false },
    { id: 2, name: 'Elven Armor', category: 'armor', icon: 'armor', count: 1, weight: 4, value: 225, favorited: false, equipped: true, enchanted: false, quest: false },
    { id: 3, name: 'Potion of Vigorous Healing', category: 'potions', icon: 'potion', count: 8, weight: 0.5, value: 79, favorited: true, equipped: false, enchanted: false, quest: false },
    { id: 4, name: 'Scroll of Fireball', category: 'scrolls', icon: 'scroll', count: 3, weight: 0.5, value: 231, favorited: false, equipped: false, enchanted: false, quest: false },
    { id: 5, name: 'Venison Stew', category: 'food', icon: 'food', count: 5, weight: 1, value: 8, favorited: false, equipped: false, enchanted: false, quest: false },
    { id: 6, name: 'Blue Mountain Flower', category: 'ingredients', icon: 'ingredient', count: 19, weight: 0.1, value: 2, favorited: false, equipped: false, enchanted: false, quest: false },
    { id: 7, name: 'The Horn of Jurgen Windcaller', category: 'misc', icon: 'misc', count: 1, weight: 0, value: 0, favorited: false, equipped: false, enchanted: false, quest: true },
  ],
  magic: [
    { id: 101, name: 'Firebolt', category: 'destruction', icon: 'destruction', cost: 25, favorited: true, equipped: true, description: 'A blast of fire that does 25 points of damage.' },
    { id: 102, name: 'Oakflesh', category: 'alteration', icon: 'alteration', cost: 40, favorited: false, equipped: false, description: 'Improves the caster’s armor rating for 60 seconds.' },
    { id: 103, name: 'Muffle', category: 'illusion', icon: 'illusion', cost: 144, favorited: false, equipped: false, description: 'Silences movement for 180 seconds.' },
    { id: 104, name: 'Fast Healing', category: 'restoration', icon: 'restoration', cost: 73, favorited: true, equipped: false, description: 'Heals the caster 50 points.' },
    { id: 105, name: 'Conjure Flame Atronach', category: 'conjuration', icon: 'conjuration', cost: 129, favorited: false, equipped: false, description: 'Summons a Flame Atronach for 60 seconds.' },
    { id: 106, name: 'Unrelenting Force', category: 'shouts', icon: 'shout', cooldown: 30, favorited: true, equipped: false, description: 'Your voice is raw power, pushing aside anything or anyone who stands in your path.' },
    { id: 107, name: 'Highborn', category: 'powers', icon: 'power', cooldown: 86400, favorited: false, equipped: false, description: 'Regenerate magicka faster for 60 seconds.' },
    { id: 108, name: 'Well Rested', category: 'status', icon: 'status', active: true, favorited: false, equipped: false, description: 'Skills improve 10% faster.' },
  ],
};
