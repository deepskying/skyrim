import type { PanelState } from './types';

export const demoState: PanelState = {
  version: '2.3.21',
  unified: true,
  capturingHotkey: false,
  message: '可随时查看强化方案；强化和刷新需靠近附魔台或锻造设备。',
  settings: {
    recyclingHotkey: { available: true, keyCode: 184, safetyCode: 184, label: '右 Alt' },
    hotkey: { key: 'A', keyCode: 0x1E, shift: true, ctrl: false, alt: false },
    lowDurabilityThreshold: 30,
    weaponDisplaySeconds: 3,
    enableLowDurabilityWarning: true,
    enableWorkshopSounds: true,
    allowEnchantedItemsToBreak: true,
  },
  forge: {
    enhancementAvailable: new URLSearchParams(window.location.search).get('stations') !== 'none', active: false, station: '锻造熔炉', gold: 1234, refreshCost: 80, refreshes: 0,
    cards: [
      { id: 'performance-strong', equipmentId: '1:32768', preview: [{ label: '强化等级', before: '+4', after: '+5' }, { label: '攻击（基础+本模组）', before: '18', after: '25' }], type: 'performance', tier: '强效', title: '千锤刃缘', description: '反复锻打刃缘，提高武器的基础杀伤。', value: '攻击 +7', successChance: 78, materials: [{ isGold: true, name: '金币', required: 272, owned: 1234 }, { isGold: false, name: '钢锭', required: 4, owned: 12 }, { isGold: false, name: '皮革条', required: 2, owned: 7 }] },
      { id: 'wear-standard', equipmentId: '1:32768', preview: [{ label: '强化等级', before: '+4', after: '+5' }, { label: '耐磨减免', before: '4%', after: '8%' }, { label: '每次耐久损耗', before: '0.96', after: '0.92' }], type: 'wear', tier: '标准', title: '韧性铆钉', description: '加固受力部位，降低战斗中的耐久损耗。', value: '耐久损耗 -4%', successChance: 88, materials: [{ isGold: true, name: '金币', required: 182, owned: 1234 }, { isGold: false, name: '钢锭', required: 2, owned: 12 }, { isGold: false, name: '强化核心', required: 1, owned: 1 }] },
      { id: 'enchant-extreme', equipmentId: '1:32768', preview: [{ label: '强化等级', before: '+4', after: '+5' }, { label: '附魔（整体替换）', before: '火焰伤害', after: '混沌伤害 · 极效' }, { label: '充能容量', before: '1400', after: '5040' }], type: 'enchantment', tier: '极强', title: '奥术重铸', description: '替换当前附魔。唯一与任务物品不可使用。', value: '混沌伤害 · 极效', successChance: 54, materials: [{ isGold: true, name: '金币', required: 408, owned: 1234 }, { isGold: false, name: '特大灵魂石（充满）', required: 1, owned: 0 }, { isGold: false, name: '虚空盐', required: 2, owned: 3 }], blockedReason: '缺少：特大灵魂石（充满）' },
    ],
  },
  equipped: [
    { id: '1:32768', name: '附魔钢弓', slot: '右手武器', category: 'weapon', equipped: true, quantity: 1, current: 18, maximum: 100, enhancementLevel: 4, damage: 18, weight: 10, attackSpeed: 1, chargeCurrent: 1120, chargeCapacity: 1400, chargeBonus: 0.4, wearRate: 0.96, wearRateLabel: '每次成功射击', wearReduction: 0.04, enchantment: '火焰伤害', enchanted: true, enchantmentReplaceable: true, quest: false, unique: false, broken: false, repairable: true, repairMaterials: [{ isGold: false, name: '钢锭', required: 2, owned: 12 }, { isGold: false, name: '皮革条', required: 1, owned: 7 }] },
    { id: '2:32769', name: '钢制胸甲', slot: '胸甲', category: 'armor', equipped: false, quantity: 1, current: 105, maximum: 120, enhancementLevel: 1, armor: 34, weight: 35, wearRate: 1, wearRateLabel: '每次被物理命中并抽中部位', wearReduction: 0, enchanted: false, enchantmentReplaceable: true, quest: false, unique: false, broken: false, repairable: true, repairMaterials: [{ isGold: false, name: '钢锭', required: 1, owned: 12 }] },
  ],
  repairQueue: [
    { id: '3:32770', name: '夜莺头盔', slot: '头盔', category: 'armor', equipped: false, quantity: 1, current: 0, maximum: 85, enhancementLevel: 8, armor: 18, weight: 2, enchantment: '幻术法术消耗降低', enchanted: true, enchantmentReplaceable: false, quest: true, unique: true, broken: true, repairable: true, repairMaterials: [{ isGold: false, name: '乌木锭', required: 3, owned: 2 }] },
  ],
};
