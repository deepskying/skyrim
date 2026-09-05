import type { MaterialRequirement } from './types';

export function costLabel(materials: readonly MaterialRequirement[]): string {
  if (!materials.length || materials.some((row) => typeof row.isGold !== 'boolean')) return '费用见材料清单';
  const gold = materials.filter((row) => row.isGold).reduce((sum, row) => sum + row.required, 0);
  if (!Number.isSafeInteger(gold) || gold < 0) return '费用见材料清单';
  const other = materials.some((row) => !row.isGold);
  return gold > 0 ? `${gold} 金币${other ? ' + 材料' : ''}` : '仅材料';
}

export function missingCost(materials: readonly MaterialRequirement[]): string | undefined {
  if (materials.some((row) => row.isGold && row.owned < row.required)) return '金币不足';
  if (materials.some((row) => row.owned < row.required)) return '材料不足';
  return undefined;
}
