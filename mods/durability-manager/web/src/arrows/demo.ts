import type { ArrowState } from './types';
export const arrowDemo: ArrowState = {
  loaded: true, resources: { gold: 850, magicka: 220 }, alchemy: 35,
  ammoQueue: { available: true, enabled: true, ids: [21, 10], limit: 64 },
  followers: { available: true, consumeMagicArrows: true },
  arrows: [
    { id: 21, name: '火球术 · 封存箭', family: 'fire', count: 24, damage: 12, equipped: true, spellBound: true, adapter: { runtime: true, releaseMode: 'instant', castRoute: 'area' } },
    { id: 22, name: '冰风暴 · 封存箭', family: 'ice', count: 16, damage: 12, spellBound: true, adapter: { runtime: true, releaseMode: 'instant' } },
    ...['铁箭', '钢箭', '精灵箭', '矮人箭'].map((name, i) => ({ id: 10 + i, name, family: 'normal', count: 48 + i * 12, damage: 8 + i * 2, runtimeBase: true, fireballBase: true })),
  ],
  spells: [
    { id: 101, name: '火球术', source: 'Skyrim.esm', craftable: true, adapter: { runtime: true, family: 'fire', charge: 10, mana: 12, gold: 5, castRoute: 'area' }, eligibility: { status: 'candidate', reasons: ['在命中位置释放范围法术'] } },
    { id: 102, name: '冰风暴', source: 'Skyrim.esm', craftable: true, adapter: { runtime: true, family: 'ice', charge: 12, mana: 16, gold: 6 }, eligibility: { status: 'candidate', reasons: ['从命中位置释放冰风暴'] } },
    { id: 103, name: '烈焰术', source: 'Skyrim.esm', craftable: true, adapter: { runtime: true, family: 'fire', charge: 8, mana: 10, gold: 4, releaseMode: 'sustained' }, eligibility: { status: 'candidate', reasons: ['从命中点持续施放 3 秒'] } },
    { id: 104, name: '烈焰斗篷', source: 'Skyrim.esm', craftable: false, eligibility: { status: 'excluded', reasons: ['自身施法，不支持封存'] } },
  ],
  materials: [
    { id: 201, name: '抗火药水', kind: 'potion', count: 4, charges: { fire: 50 } },
    { id: 202, name: '自制抗火药水', kind: 'potion', count: 3, charges: { fire: 35 } },
    { id: 203, name: '火盐', kind: 'ingredient', count: 8, charges: { fire: 10 } },
    { id: 204, name: '抗冰药水', kind: 'potion', count: 3, charges: { ice: 50 } },
  ],
  recipes: [{ id: 301, name: '铁箭', source: 'Dawnguard.esm', yield: 24, craftable: true, maxBatches: 4, ingredients: [{ name: '铁锭', need: 1, have: 4 }, { name: '木柴', need: 1, have: 8 }] }],
};
