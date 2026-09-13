import type { ArrowState, Selection, Stack } from './types';
import { matchingMaterials } from './rules';

export function clampQuantity(value: number, maximum: number) {
  return Math.max(0, Math.min(Math.max(0, Math.floor(maximum)), Number.isFinite(value) ? Math.floor(value) : 0));
}
export function replaceStack(items: Stack[], id: number, count: number) {
  return count > 0 ? items.some(x => x.id === id) ? items.map(x => x.id === id ? { id, count } : x) : [...items, { id, count }] : items.filter(x => x.id !== id);
}
export function allocateBases(items: Stack[], total: number) {
  let remaining = Math.max(0, total);
  return items.flatMap(item => { const count = Math.min(item.count, remaining); remaining -= count; return count > 0 ? [{ id: item.id, count }] : []; });
}
/** Keeps compatible choices, removes depleted stacks, and enforces the native limits. */
export function reconcileSelection(state: ArrowState, selection: Selection): Selection {
  const spell = state.spells.find(s => s.id === selection.spell);
  if (!spell?.craftable) return { spell: selection.spell, bases: [], materials: [] };
  const stock = state.arrows.filter(a => a.usable !== false && (spell.adapter?.runtime ? a.runtimeBase : a.fireballBase));
  let remaining = 100;
  const seen = new Set<number>();
  const bases = selection.bases.flatMap(b => {
    if (seen.has(b.id) || seen.size >= 32) return [];
    seen.add(b.id);
    const count = clampQuantity(b.count, Math.min(remaining, stock.find(a => a.id === b.id)?.count ?? 0));
    remaining -= count;
    return count > 0 ? [{ id: b.id, count }] : [];
  });
  seen.clear();
  const available = matchingMaterials(state.materials, spell);
  const materials = selection.materials.flatMap(m => {
    if (seen.has(m.id) || seen.size >= 128) return [];
    seen.add(m.id);
    const count = clampQuantity(m.count, Math.min(10000, available.find(a => a.id === m.id)?.count ?? 0));
    return count > 0 ? [{ id: m.id, count }] : [];
  });
  return { spell: selection.spell, bases, materials };
}
export function resourceSegments(current: number | undefined, cost: number) {
  const known = typeof current === 'number' && Number.isFinite(current);
  const held = known ? Math.max(0, current) : 0;
  const spending = Math.max(0, Number.isFinite(cost) ? cost : 0);
  const remaining = Math.max(0, held - spending);
  return { known, held, spending, remaining, shortage: known ? Math.max(0, spending - held) : 0,
    remainingPercent: held > 0 ? remaining / held * 100 : 0,
    spendingPercent: held > 0 ? Math.min(held, spending) / held * 100 : 0 };
}

/** Adds just enough compatible charge, preserving the user's selected materials. */
export function fillCharge(state: ArrowState, selection: Selection): Selection {
  const next = reconcileSelection(state, selection);
  const spell = state.spells.find(s => s.id === next.spell);
  if (!spell?.craftable) return next;
  const available = matchingMaterials(state.materials, spell);
  const charge = Math.max(1, spell.adapter?.charge ?? 10);
  const target = next.bases.reduce((n, b) => n + b.count, 0) * charge;
  let missing = target - next.materials.reduce((n, m) => n + m.count * (available.find(a => a.id === m.id)?.units ?? 0), 0);
  for (const material of available) {
    if (missing <= 0) break;
    const count = next.materials.find(m => m.id === material.id)?.count ?? 0;
    if (!count && next.materials.length >= 128) continue;
    const add = clampQuantity(Math.ceil(missing / material.units), Math.min(10000, material.count) - count);
    if (add > 0) { next.materials = replaceStack(next.materials, material.id, count + add); missing -= add * material.units; }
  }
  return next;
}
