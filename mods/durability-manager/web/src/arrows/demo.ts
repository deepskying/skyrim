import type { ArrowState } from './types';
export const arrowDemo: ArrowState = {
  craftingAccess: { magic: true, normal: true },
  loaded: true, resources: { gold: 850, magicka: 220 }, alchemy: 35, materialGenericPercent: 50,
  ammoQueue: { available: true, enabled: true, ids: [21, 10], limit: 64 },
  followers: { available: true, consumeMagicArrows: true },
  soulPool: {
    available: true, enabled: true, points: 12, capacity: 20, tier: 1, absorbed: 37, upgradeGold: 1000, gold: 1850,
    materials: [{ id: 203, name: '火盐', count: 4, owned: 8 }, { id: 205, name: '死亡钟花', count: 6, owned: 5 }],
    gems: [
      { level: 1, name: '微型灵魂石（充满）', points: 1, gold: 60, id: 0x2E4E3, can: 12 },
      { level: 2, name: '小型灵魂石（充满）', points: 2, gold: 120, id: 0x2E4E5, can: 6 },
      { level: 3, name: '普通灵魂石（充满）', points: 3, gold: 250, id: 0x2E4F3, can: 4 },
      { level: 4, name: '大型灵魂石（充满）', points: 4, gold: 500, id: 0x2E4FB, can: 3 },
      { level: 5, name: '巨型灵魂石（充满）', points: 5, gold: 900, id: 0x2E4FF, can: 2 },
      { level: 6, name: '黑色灵魂石（充满）', points: 5, gold: 1500, id: 0x2E504, can: 1 },
    ],
    deposit: [{ id: 0x2E4F3, name: '普通灵魂石（充满）', count: 3, points: 3, room: 2 }],
  },
  arrows: [
    { id: 21, name: '火球术 · 封存箭', family: 'fire', count: 24, damage: 12, equipped: true, spellBound: true, adapter: { runtime: true, releaseMode: 'instant', castRoute: 'area' } },
    { id: 22, name: '冰风暴 · 封存箭', family: 'ice', count: 16, damage: 12, spellBound: true, adapter: { runtime: true, releaseMode: 'instant' } },
    ...[['shock', '雷棱箭'], ['poison', '蛇牙箭'], ['blood', '嗜血箭'], ['holy', '圣辉箭'], ['wind', '旋翼箭'], ['water', '碧波箭'], ['earth', '岩锥箭'], ['dark', '影镰箭'], ['soul', '星魂箭'], ['arcane', '奥术箭']].map(([family, name], i) => ({ id: 30 + i, name, family, count: 12 + i * 3, damage: 8, spellBound: true })),
    ...['铁箭', '钢箭', '精灵箭', '矮人箭'].map((name, i) => ({ id: 10 + i, name, family: 'normal', count: 48 + i * 12, damage: 8 + i * 2, runtimeBase: true, fireballBase: true })),
  ],
  spells: [
    { id: 101, name: '火球术', source: 'Skyrim.esm', craftable: true, adapter: { runtime: true, family: 'fire', material: '抗火／弱火／毁灭系', charge: 10, mana: 12, gold: 5, castRoute: 'area' }, eligibility: { status: 'candidate', reasons: ['在命中位置释放范围法术'] } },
    { id: 102, name: '冰风暴', source: 'Skyrim.esm', craftable: true, adapter: { runtime: true, family: 'ice', material: '抗冰／弱冰／毁灭系', charge: 12, mana: 16, gold: 6 }, eligibility: { status: 'candidate', reasons: ['从命中位置释放冰风暴'] } },
    { id: 103, name: '烈焰术', source: 'Skyrim.esm', craftable: true, adapter: { runtime: true, family: 'fire', material: '抗火／弱火／毁灭系', charge: 8, mana: 10, gold: 4, releaseMode: 'sustained' }, eligibility: { status: 'candidate', reasons: ['从命中点持续施放 3 秒'] } },
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
