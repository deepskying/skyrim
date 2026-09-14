import type { EquipmentItem } from './types';
import { EquippedBadge } from './EquippedBadge';
import { formatDurability } from './format';
import './enhancement-grid.css';

export function EquipmentEnhancementGrid({ items, total, search, filter, setSearch, setFilter, available, onSelect }: {
  items: EquipmentItem[]; total: number; search: string; filter: string;
  setSearch: (value: string) => void; setFilter: (value: string) => void;
  available: boolean; onSelect: (id: string) => void;
}) {
  return <section className="enhancement-inventory">
    <div className="list-heading"><div><p>CHOOSE YOUR EQUIPMENT</p><h2>选择强化装备</h2></div><span>{items.length} / {total} 件</span></div>
    <div className="equipment-tools"><input aria-label="搜索强化装备" placeholder="搜索装备名称…" value={search} onChange={e => setSearch(e.target.value)} /><div>{[['all', '全部'], ['weapon', '武器'], ['armor', '护甲'], ['clothing', '衣物'], ['worn', '已装备']].map(([id, label]) => <button type="button" key={id} aria-pressed={filter === id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div></div>
    {!available && <p className="forge-hint">当前角色状态不可操作，请载入游戏后重试。</p>}
    <div className="enhancement-equipment-grid">
      {items.map(item => <button type="button" className={`enhancement-equipment-card${item.broken ? ' broken' : ''}`} key={item.id} disabled={!available || item.broken} onClick={() => onSelect(item.id)} aria-label={`${item.name}，${item.broken ? '请先修复装备' : '选择强化方案'}`}>
        <span className="enhancement-equipment-top"><EquippedBadge equipped={item.equipped} /><b>+{item.enhancementLevel}</b></span>
        <span className="enhancement-equipment-icon" aria-hidden="true">{item.category === 'weapon' ? '⚔' : item.slot.includes('盾') ? '⛨' : item.category === 'armor' ? '◈' : '◇'}</span>
        <strong title={item.name}>{item.name}</strong>
        <span className="enhancement-equipment-meta">{item.slot}{item.quantity > 1 && ` · ×${item.quantity}`}{item.enchanted && ' · ✦ 附魔'}</span>
        <span className="enhancement-equipment-durability"><span>耐久</span><b>{formatDurability(item.current)} / {formatDurability(item.maximum)}</b></span>
        <span className="enhancement-equipment-track"><i style={{ width: `${Math.max(0, Math.min(100, item.current / Math.max(1, item.maximum) * 100))}%` }} /></span>
        <span className="enhancement-equipment-action">{item.broken ? '请先修复装备' : !available ? '当前不可操作' : '选择强化方案 →'}</span>
      </button>)}
    </div>
    {!items.length && <p className="empty">没有符合条件的装备。</p>}
  </section>;
}
