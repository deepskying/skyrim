// Stable partition: preserve instance identities and order within each group.
export function equippedFirst<T extends { equipped: boolean }>(items: readonly T[]): T[] {
  return [...items.filter((item) => item.equipped), ...items.filter((item) => !item.equipped)];
}
