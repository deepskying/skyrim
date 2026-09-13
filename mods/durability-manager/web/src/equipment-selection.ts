/** Prefer the preceding surviving row in the order visible before dismantling. */
export function afterDismantle(before: string[], removed: string, remaining: string[]) {
  const index = before.indexOf(removed);
  const available = new Set(remaining);
  for (let i = index - 1; i >= 0; --i) if (available.has(before[i])) return before[i];
  for (let i = Math.max(0, index + 1); i < before.length; ++i) if (available.has(before[i])) return before[i];
  return remaining[0];
}

export function adjacentEquipment(ids: string[], selected: string | undefined, direction: number) {
  if (!ids.length) return undefined;
  const index = ids.indexOf(selected ?? '');
  return ids[Math.max(0, Math.min(ids.length - 1, index < 0 ? 0 : index + Math.sign(direction)))];
}
