import type { Potion, PotionEffect, PotionState } from './types';
const traits: Record<string, [string, string, string]> = {
  'restore-health': ['♥', '恢复生命', 'health'], 'fortify-health': ['♥↑', '提升生命上限', 'health'], 'regen-health': ['♥↻', '生命再生', 'health'],
  'restore-magicka': ['✦', '恢复法力', 'magicka'], 'fortify-magicka': ['✦↑', '提升法力上限', 'magicka'], 'regen-magicka': ['✦↻', '法力再生', 'magicka'],
  'restore-stamina': ['ϟ', '恢复耐力', 'stamina'], 'fortify-stamina': ['ϟ↑', '提升耐力上限', 'stamina'], 'regen-stamina': ['ϟ↻', '耐力再生', 'stamina'],
  'resist-fire': ['火', '火焰抗性', 'resist'], 'resist-frost': ['❄', '冰霜抗性', 'resist'], 'resist-shock': ['雷', '闪电抗性', 'resist'],
  'resist-magic': ['◇', '魔法抗性', 'resist'], 'resist-poison': ['毒', '毒素抗性', 'resist'], 'resist-disease': ['疾', '疾病抗性', 'resist'],
  'cure-disease': ['✚', '治愈疾病', 'utility'], 'cure-poison': ['✚', '解毒', 'utility'],
  invisibility: ['◌', '隐形', 'utility'], 'night-eye': ['◉', '夜视', 'utility'], 'water-breathing': ['≈', '水下呼吸', 'utility'],
  carry: ['▣', '提升负重', 'utility'], speed: ['»', '移动速度', 'utility'], armor: ['⬡', '护甲强化', 'resist'], harmful: ['!', '负面效果', 'harmful'],
};
const skills = ['单手', '双手', '弓术', '格挡', '锻造', '重甲', '轻甲', '扒窃', '开锁', '潜行', '炼金', '口才', '变化', '召唤', '毁灭', '幻术', '恢复', '附魔'];
export function effectTraits(potion: Potion) {
  const result = new Map<string, { id: string; icon: string; name: string; tone: string }>();
  for (const effect of potion.effects) for (const key of effect.traits.length ? effect.traits : ['other']) {
    const skill = /^skill-(\d+)$/.exec(key);
    const info = traits[key] ?? (skill && skills[Number(skill[1])] ? ['↑', `${skills[Number(skill[1])]}强化`, 'skill'] : ['✧', effect.name, effect.harmful ? 'harmful' : 'utility']);
    const id = traits[key] || skill ? key : `effect-${effect.id}`;
    result.set(id, { id, icon: info[0], name: info[1], tone: info[2] });
  }
  return [...result.values()];
}
export function effectTone(effect: PotionEffect) {
  if (effect.harmful || effect.traits.includes('harmful')) return 'harmful';
  const elemental = effect.traits.find(key => ['resist-fire', 'resist-frost', 'resist-shock'].includes(key));
  if (elemental) return elemental;
  return effect.traits.map(key => traits[key]?.[2] ?? (/^skill-\d+$/.test(key) ? 'skill' : undefined)).find(Boolean) ?? 'utility';
}
export function effectDescription(effect: PotionEffect) {
  return effect.description.replace(/<mag>/gi, String(effect.magnitude)).replace(/<dur>/gi, String(effect.duration)).replace(/<area>/gi, String(effect.area)).replace(/<[^>]*>/g, '').trim();
}
export function nextPotionIndex(index: number, length: number, columns: number, key: string) {
  if (!length) return -1;
  index = Math.max(0, Math.min(length - 1, index)); columns = Math.max(1, columns);
  if (key === 'ArrowLeft') return index % columns ? index - 1 : index;
  if (key === 'ArrowRight') return index % columns < columns - 1 ? Math.min(index + 1, length - 1) : index;
  if (key === 'ArrowUp') return Math.max(0, index - columns);
  if (key === 'ArrowDown') return Math.min(length - 1, index + columns);
  return index;
}
export function normalizePotions(value: unknown): PotionState | undefined {
  if (!value || typeof value !== 'object') return;
  const v = value as PotionState;
  if (!Array.isArray(v.items) || !Number.isSafeInteger(v.token) || v.token < 1) return;
  const seen = new Set<number>();
  const items = v.items.filter(p => {
    if (!p || !Number.isInteger(p.id) || p.id < 1 || seen.has(p.id) || typeof p.name !== 'string' || !Number.isInteger(p.count) || p.count < 1 || !Array.isArray(p.effects)) return false;
    seen.add(p.id); return true;
  }).map(p => ({ ...p, keywords: Array.isArray(p.keywords) ? p.keywords.filter(k => typeof k === 'string') : [], poison: p.poison === true, usable: p.poison !== true && p.usable === true, reason: typeof p.reason === 'string' ? p.reason : '',
    weight: Number.isFinite(p.weight) ? p.weight : 0, value: Number.isFinite(p.value) ? p.value : 0,
    effects: p.effects.filter(e => e && typeof e.name === 'string' && Number.isInteger(e.id)).map(e => ({ ...e, traits: Array.isArray(e.traits) ? e.traits.filter(t => typeof t === 'string') : [], description: typeof e.description === 'string' ? e.description : '', magnitude: Number.isFinite(e.magnitude) ? e.magnitude : 0, duration: Number.isFinite(e.duration) ? e.duration : 0, area: Number.isFinite(e.area) ? e.area : 0 })) }));
  return { items, token: v.token, message: typeof v.message === 'string' ? v.message : '', reply: v.reply && Number.isSafeInteger(v.reply.requestID) ? { requestID: v.reply.requestID, ok: v.reply.ok === true } : undefined };
}
