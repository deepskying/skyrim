import { useEffect, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState } from './types';
import { ArrowInventory } from './ArrowInventory';
import { MagicCrafting, NormalCrafting } from './ArrowCrafting';
export function ArrowWorkshop({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const [page, setPage] = useState('equipment');
  useEffect(() => {
    if (!active) return;
    action('page', { page: page === 'equipment' ? 'equipment' : 'craft' });
    if (page !== 'equipment') action('workshopMode', { mode: page });
    return () => action('cancelCraft');
  }, [active, page, action]);
  return <section className="arrows-page" hidden={!active}>
    <div className="arrow-toolbar"><div className="workshop-tabs" role="tablist" aria-label="魔法箭栏目">{[['equipment', '箭矢装备'], ['magic', '制作魔法箭'], ['normal', '制作普通箭']].map(([id, title]) => <button key={id} role="tab" aria-selected={page === id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}>{title}</button>)}</div>{page !== 'equipment' && <p className={`craft-station-notice ${state.craftingAccess?.[page === 'normal' ? 'normal' : 'magic'] ? 'available' : 'unavailable'}`} role="status">{state.craftingAccess?.[page === 'normal' ? 'normal' : 'magic'] ? (page === 'normal' ? '附近铁匠设备可用。' : '附近附魔台可用。') : (page === 'normal' ? '请靠近铁匠设备后制作：锻造炉、冶炼炉、磨刀石或护甲工作台。' : '请靠近附魔台后制作魔法箭。')}</p>}<button onClick={() => action('refresh')}>↻ 同步背包</button></div>
    <div hidden={page !== 'equipment'}><ArrowInventory state={state} action={action} /></div>
    <div hidden={page !== 'magic'}><MagicCrafting state={state} action={action} active={active && page === 'magic'} /></div>
    <div hidden={page !== 'normal'}><NormalCrafting state={state} action={action} active={active && page === 'normal'} /></div>
    <p className="arrow-status" role="status">{state.message || (state.loaded ? '背包数据已同步。' : '等待游戏加载…')}</p>
  </section>;
}
