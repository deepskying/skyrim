import type { CardType, EnhancementCard, EnhancementTier, EquipmentItem } from './types';

export const cardLabels: Record<CardType, string> = {
  performance: '性能强化', weight: '重量强化', speed: '攻速强化', durability: '耐久强化', wear: '耐磨强化', charge: '充能强化', enchantment: '附魔替换',
};
export const cardIcons: Record<CardType, string> = {
  performance: '⚔', weight: '◒', speed: '↯', durability: '⛨', wear: '⛓', charge: '✦', enchantment: '☽',
};
const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
const string = (value: unknown) => typeof value === 'string' ? value : '';
const count = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? Math.floor(value) : undefined;

/** Treat the native bridge as untrusted input: malformed cards must never crash the whole panel. */
export function normalizeCards(value: unknown): EnhancementCard[] {
  if (!Array.isArray(value)) return [];
  const ids = new Set<string>();
  return value.flatMap((entry) => {
    if (!record(entry) || !string(entry.id) || ids.has(string(entry.id)) || !string(entry.equipmentId) ||
      !Object.prototype.hasOwnProperty.call(cardLabels, string(entry.type)) || !['微弱', '标准', '强效', '极强'].includes(string(entry.tier))) return [];
    ids.add(string(entry.id));
    let invalid = false;
    const preview = Array.isArray(entry.preview) ? entry.preview.flatMap((row) => {
      if (!record(row) || !string(row.label) || !string(row.before) || !string(row.after)) { invalid = true; return []; }
      return [{ label: string(row.label), before: string(row.before), after: string(row.after) }];
    }) : [];
    const materials = Array.isArray(entry.materials) ? entry.materials.flatMap((row) => {
      if (!record(row)) { invalid = true; return []; }
      const required = count(row.required), owned = count(row.owned);
      if (!string(row.name) || required === undefined || required === 0 || owned === undefined) { invalid = true; return []; }
      return [{ name: string(row.name), required, owned }];
    }) : [];
    const chance = count(entry.successChance);
    const blockedReason = string(entry.blockedReason) ||
      (invalid || !preview.length || !materials.length || chance === undefined || chance > 100 ? '卡片数据不完整，请重新打开面板' :
        materials.some((row) => row.owned < row.required) ? '材料不足' : undefined);
    return [{ id: string(entry.id), equipmentId: string(entry.equipmentId), type: entry.type as CardType, tier: entry.tier as EnhancementTier,
      title: string(entry.title), description: string(entry.description), value: string(entry.value), successChance: Math.min(100, chance ?? 0),
      preview, materials, blockedReason }];
  });
}

// Changes to the offer, cost, item or protection invalidate an already-open confirmation.
export function confirmationKey(item: EquipmentItem, card: EnhancementCard) {
  return JSON.stringify([item, card]);
}

export function failureDescription(item: EquipmentItem) {
  return item.quest || item.unique
    ? `失败不会分解此装备；等级降至 +${Math.max(0, item.enhancementLevel - 1)}，已有强化加值按比例回退。`
    : '失败会分解这件装备，该装备实例及其强化、附魔将丢失；可用的分解材料按现有配方返还。';
}
