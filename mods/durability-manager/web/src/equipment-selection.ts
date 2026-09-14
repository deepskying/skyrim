export function adjacentEquipment(ids: string[], selected: string | undefined, direction: number) {
  if (!ids.length) return undefined;
  const index = ids.indexOf(selected ?? '');
  return ids[Math.max(0, Math.min(ids.length - 1, index < 0 ? 0 : index + Math.sign(direction)))];
}
