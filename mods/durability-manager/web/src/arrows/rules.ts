import type { ArrowState, Material, Selection, Spell } from './types';
// Native limits: one quantity box holds at most 999, one batch (and one queue entry) at
// most 10000 arrows. The panel mirrors them so a rejected order never reaches the game.
export const craftInputMax = 999;
export const craftBatchMax = 10000;
export function matchingMaterials(materials: Material[], spell?: Spell) {
  const family = spell?.adapter?.family ?? 'fire';
  const rank = (kind: string) => kind === 'potion' ? 0 : kind === 'poison' ? 1 : 2;
  return materials.map(m => ({ ...m, units: m.charges?.[family] ?? (family === 'fire' ? m.units ?? 0 : 0) }))
    .filter(m => m.count > 0 && m.units > 0 && ['potion', 'poison', 'ingredient'].includes(m.kind))
    .sort((a, b) => rank(a.kind) - rank(b.kind) || b.units - a.units || a.name.localeCompare(b.name, 'zh-CN') || a.id - b.id);
}
export function materialHighlight(materials: Material[], spell?: Spell): 'potion' | 'ingredient' | '' {
  if (!spell?.craftable) return '';
  const matches = matchingMaterials(materials, spell);
  const charge = Math.max(1, spell.adapter?.charge ?? 10);
  if (matches.reduce((total, material) => total + material.count * material.units, 0) < charge) return '';
  if (matches.some(material => material.kind === 'potion' || material.kind === 'poison')) return 'potion';
  return matches.some(material => material.kind === 'ingredient') ? 'ingredient' : '';
}
export function selectionKey(selection: Selection) { return JSON.stringify(selection); }
export function craftingAccessError(state: ArrowState, normal: boolean) {
  if (state.loaded && state.craftingAccess?.[normal ? 'normal' : 'magic']) return '';
  return normal ? '请靠近锻造炉、冶炼炉、磨刀石或护甲工作台后制作普通箭矢。' : '请靠近附魔台后制作魔法箭。';
}
export function matchesCraftReply(request: { id: number; key: string; type: string } | undefined, key: string, reply: ArrowState['workshopReply']) {
  return !!request && !!reply && request.key === key && reply.requestID === request.id && reply.type === request.type;
}
export function planCraft(state: ArrowState, selection: Selection) {
  const spell = state.spells.find(s => s.id === selection.spell);
  const materials = matchingMaterials(state.materials, spell);
  const base = state.arrows.filter(a => spell?.adapter?.runtime ? a.runtimeBase : a.fireballBase);
  const target = selection.bases.reduce((n, b) => n + b.count, 0);
  const charge = Math.max(1, spell?.adapter?.charge ?? 10);
  const energy = selection.materials.reduce((n, m) => n + (materials.find(x => x.id === m.id)?.units ?? 0) * m.count, 0);
  const total = Math.max(0, Math.min(target, Math.floor(energy / charge)));
  const gold = total * (spell?.adapter?.gold ?? 5), mana = total * (spell?.adapter?.mana ?? 12);
  let error = !spell?.craftable ? '请选择可制作的法术' : !target ? '请选择基材箭矢和数量' : target > craftBatchMax ? `每次最多制作 ${craftBatchMax} 支` : '';
  const validStacks = (stacks: Selection['bases'], inventory: { id: number; count: number }[], limit: number) => new Set(stacks.map(s => s.id)).size === stacks.length && stacks.every(s => Number.isInteger(s.count) && s.count > 0 && s.count <= Math.min(limit, inventory.find(x => x.id === s.id)?.count ?? 0));
  if (!validStacks(selection.bases, base, craftInputMax) || !validStacks(selection.materials, materials, craftInputMax)) error = '库存或数量已变化，请调整选择';
  if (!error && !total) error = '请添加对应药水或炼金材料充能';
  if (!error && state.resources && gold > state.resources.gold) error = '金币不足';
  // Queued crafting pays magicka one arrow at a time, so it never blocks the start button.
  // The co-save and the per-spell ceiling are the only hard gates left.
  if (!error && state.orders?.available === false) error = '队列保存组件不可用，无法开始制作';
  const queued = state.orders?.entries.find(entry => entry.spell === selection.spell)?.remaining ?? 0;
  if (!error && queued + total > (state.orders?.limit ?? craftBatchMax)) error = '该法术的排队数量已达上限';
  return { spell, materials, base, target, total, charge, energy, gold, mana, error };
}
export function moveQueue(ids: number[], from: number, to: number) {
  const result = [...ids], i = result.indexOf(from), j = result.indexOf(to);
  if (i < 0 || j < 0) return result;
  result.splice(i, 1); result.splice(j, 0, from); return result;
}
