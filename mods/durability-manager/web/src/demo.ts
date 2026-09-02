import type { PanelState } from './types';

export const demoState: PanelState = {
  atForge: true,
  capturingHotkey: false,
  message: '已进入锻炉修复模式。选择带有锤子图标的装备查看材料。',
  settings: {
    hotkey: { key: 'F', keyCode: 0x21, shift: true, ctrl: false, alt: false },
    lowDurabilityThreshold: 30,
    weaponDisplaySeconds: 3,
    enableLowDurabilityWarning: true,
    allowEnchantedItemsToBreak: true,
  },
  equipped: [
    { id: 1, name: '附魔钢剑', slot: '右手武器', current: 18, maximum: 100, enchanted: true, quest: false, broken: false, repairable: true, material: '钢锭', materialCount: 2 },
    { id: 2, name: '钢制胸甲', slot: '胸甲', current: 105, maximum: 120, enchanted: false, quest: false, broken: false, repairable: true, material: '钢锭', materialCount: 1 },
    { id: 3, name: '矮人头盔', slot: '头盔', current: 0, maximum: 85, enchanted: false, quest: false, broken: true, repairable: true, material: '矮人金属锭', materialCount: 3 },
  ],
  repairQueue: [
    { id: 1, name: '附魔钢剑', slot: '右手武器', current: 18, maximum: 100, enchanted: true, quest: false, broken: false, repairable: true, material: '钢锭', materialCount: 2 },
    { id: 3, name: '矮人头盔', slot: '头盔', current: 0, maximum: 85, enchanted: false, quest: false, broken: true, repairable: true, material: '矮人金属锭', materialCount: 3 },
  ],
};
