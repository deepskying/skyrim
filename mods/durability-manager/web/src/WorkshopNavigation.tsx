export type Tab = 'workshop' | 'enhancement' | 'arrows' | 'settings';
const entries: { id: Tab; icon: string; name: string }[] = [
  { id: 'workshop', icon: '◈', name: '装备养护' }, { id: 'enhancement', icon: '⚒', name: '装备强化' },
  { id: 'arrows', icon: '➶', name: '魔法箭' }, { id: 'settings', icon: '⚙', name: '工坊设置' },
];
export function WorkshopNavigation({ tab, forge, arrows, onChange }: { tab: Tab; forge: boolean; arrows: boolean; onChange: (tab: Tab) => void }) {
  return <aside className="workshop-rail"><div className="workshop-brand"><span>⚒</span><b>装备工坊</b><small>EQUIPMENT WORKSHOP</small></div><nav aria-label="工坊导航">{entries.filter(entry => entry.id !== 'arrows' || arrows).map(entry => <button key={entry.id} className={tab === entry.id ? 'active' : ''} onClick={() => onChange(entry.id)}><span>{entry.icon}</span>{entry.name}</button>)}</nav><div className="workshop-rail-foot"><i />{forge ? '锻造设施可用' : '随身装备管理'}<small>装备 · 强化 · 回收 · 魔法箭</small></div></aside>;
}
