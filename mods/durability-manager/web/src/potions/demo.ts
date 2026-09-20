import type { PotionEffect, PotionState } from './types';
const effect = (id: number, name: string, trait: string, magnitude: number, duration = 0): PotionEffect => ({ id, name, traits: [trait], description: '', magnitude, duration, area: 0, hasMagnitude: true, hasDuration: duration > 0, harmful: trait === 'harmful' });
export const potionDemo: PotionState = { token: 1, message: '浏览器预览 · 使用只改变演示库存', items: [
  { id: 1, name: '极效治疗药水', count: 8, effects: [effect(101,'恢复生命','restore-health',150)] },
  { id: 2, name: '冒险者的调和药剂', count: 3, effects: [effect(101,'恢复生命','restore-health',75),effect(102,'抵抗火焰','resist-fire',35,60),effect(103,'强化负重','carry',20,300)] },
  { id: 3, name: '充沛魔力药水', count: 5, effects: [effect(104,'恢复法力','restore-magicka',100)] },
  { id: 4, name: '持久耐力药水', count: 6, effects: [effect(105,'恢复耐力','restore-stamina',80),effect(106,'耐力再生','regen-stamina',50,60)] },
  { id: 5, name: '元素守护药剂', count: 2, effects: [effect(102,'抵抗火焰','resist-fire',40,60),effect(107,'抵抗冰霜','resist-frost',40,60),effect(108,'抵抗闪电','resist-shock',40,60)] },
  { id: 6, name: '隐形药水', count: 1, effects: [{...effect(109,'隐形','invisibility',0,30),hasMagnitude:false}] },
  { id: 7, name: '战士的复合药剂', count: 4, effects: [effect(110,'强化单手','skill-0',25,60),effect(111,'强化生命','fortify-health',40,60),effect(112,'生命再生','regen-health',50,60),effect(113,'抵抗魔法','resist-magic',15,60),effect(114,'护甲强化','armor',25,60)] },
  { id: 8, name: '自制双效药水', count: 2, effects: [effect(101,'恢复生命','restore-health',30),effect(115,'损伤法力','harmful',10)] },
  { id: 9, name: '剧烈生命毒药', count: 4, poison: true, effects: [effect(116,'损伤生命','harmful',65)] },
  { id: 10, name: '枯竭毒药', count: 3, poison: true, effects: [effect(117,'损伤法力','harmful',50),effect(118,'损伤耐力','harmful',50)] },
  { id: 11, name: '麻痹毒药', count: 2, poison: true, effects: [{...effect(119,'麻痹','harmful',0,5),hasMagnitude:false}] },
].map(p => ({ ...p, weight: 0.5, value: 80 + p.id * 13, source: p.id === 2 || p.id === 8 ? '自制药水' : 'Skyrim.esm', usable: !('poison' in p && p.poison), reason: 'poison' in p && p.poison ? '请在游戏背包中为武器涂毒' : '' })) };
