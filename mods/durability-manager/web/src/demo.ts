import type { PanelState } from './types';

export const demoState: PanelState = {
  version: '0.1.10',
  capturingHotkey: false,
  message: '锻造熔炉 · 装备工坊。选择装备后查看其完整状态。',
  settings: {
    hotkey: { key: 'F', keyCode: 0x21, shift: true, ctrl: false, alt: false },
    lowDurabilityThreshold: 30,
    weaponDisplaySeconds: 3,
    enableLowDurabilityWarning: true,
    allowEnchantedItemsToBreak: true,
  },
  forge: {
    active: true, station: '锻造熔炉', refreshCost: 80, refreshes: 0,
    cards: [
      { id: 'performance-strong', type: 'performance', tier: '强效', title: '千锤刃缘', description: '反复锻打刃缘，提高武器的基础杀伤。', value: '攻击 +7', successChance: 78, materials: [{ name: '钢锭', required: 4, owned: 12 }, { name: '皮革条', required: 2, owned: 7 }] },
      { id: 'wear-standard', type: 'wear', tier: '标准', title: '韧性铆钉', description: '加固受力部位，降低战斗中的耐久损耗。', value: '耐久损耗 -4%', successChance: 88, materials: [{ name: '钢锭', required: 2, owned: 12 }, { name: '强化核心', required: 1, owned: 1 }] },
      { id: 'enchant-extreme', type: 'enchantment', tier: '极强', title: '奥术重铸', description: '替换当前附魔。唯一与任务物品不可使用。', value: '混沌伤害 · 极效', successChance: 54, materials: [{ name: '特大灵魂石（充满）', required: 1, owned: 0 }, { name: '虚空盐', required: 2, owned: 3 }], blockedReason: '缺少：特大灵魂石（充满）' },
    ],
  },
  equipped: [
    { id: '1:32768', name: '附魔钢弓', slot: '右手武器', category: 'weapon', current: 18, maximum: 100, enhancementLevel: 4, damage: 18, weight: 10, attackSpeed: 1, wearRate: 0.96, wearRateLabel: '每次成功射击', wearReduction: 0.04, enchantment: '火焰伤害', enchanted: true, enchantmentReplaceable: true, quest: false, unique: false, broken: false, repairable: true, material: '钢锭', materialCount: 2 },
    { id: '2:32769', name: '钢制胸甲', slot: '胸甲', category: 'armor', current: 105, maximum: 120, enhancementLevel: 1, armor: 34, weight: 35, enchanted: false, enchantmentReplaceable: true, quest: false, unique: false, broken: false, repairable: true, material: '钢锭', materialCount: 1 },
    { id: '3:32770', name: '夜莺头盔', slot: '头盔', category: 'armor', current: 0, maximum: 85, enhancementLevel: 8, armor: 18, weight: 2, enchantment: '幻术法术消耗降低', enchanted: true, enchantmentReplaceable: false, quest: true, unique: true, broken: true, repairable: true, material: '乌木锭', materialCount: 3 },
  ],
  repairQueue: [],
};
