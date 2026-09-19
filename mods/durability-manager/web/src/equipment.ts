// Stable partition: preserve instance identities and order within each group.
export function equippedFirst<T extends { equipped: boolean }>(items: readonly T[]): T[] {
  return [...items.filter((item) => item.equipped), ...items.filter((item) => !item.equipped)];
}

// Keep worn equipment in its existing order; prioritize repairs by remaining ratio.
export function maintenanceOrder<T extends { equipped: boolean; current: number; maximum: number }>(items: readonly T[]): T[] {
  const ratio = (item: T) => item.maximum > 0 ? Math.max(0, Math.min(1, item.current / item.maximum)) : 0;
  return [
    ...items.filter(item => item.equipped),
    ...items.filter(item => !item.equipped).sort((a, b) => ratio(a) - ratio(b)),
  ];
}
