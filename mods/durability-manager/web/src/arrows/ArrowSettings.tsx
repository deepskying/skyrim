import { useEffect } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState } from './types';
export function ArrowSettings({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  useEffect(() => { if (active) action('page', { page: 'settings' }); }, [active, action]);
  return <div className="arrow-settings" hidden={!active}>
    <section className="arrow-card"><small>FOLLOWER AMMUNITION</small><h2>随从魔法箭消耗</h2><p>队友使用封存箭或固定适配箭时按射击数量消耗，射空也计入。随从无需掌握封存的法术。</p><label className="arrow-setting-toggle"><input aria-label="随从魔法箭按射击消耗" type="checkbox" checked={state.followers?.consumeMagicArrows ?? true} disabled={!state.followers?.available} onChange={e => action('followerSettings', { consumeMagicArrows: e.target.checked })} />按射击数量消耗魔法箭</label><p className="arrow-muted">修改后自动保存。普通箭沿用游戏规则；关闭后交由游戏及其他模组决定。</p></section>
    <section className="arrow-card"><small>AMMUNITION PRIORITY</small><h2>箭矢使用队列</h2><label className="arrow-setting-toggle"><input aria-label="启用箭矢队列优先" type="checkbox" checked={state.ammoQueue?.enabled ?? false} disabled={!state.ammoQueue?.available} onChange={e => action('queueEdit', { ids: state.ammoQueue?.ids ?? [], enabled: e.target.checked })} />持弓时优先使用队列中的箭矢</label><p className="arrow-muted">在「魔法箭 → 箭矢装备」调整顺序。队列和开关随角色存档保存。</p></section>
    <section className="arrow-card"><small>ALCHEMICAL CRAFTING</small><h2>炼金与充能</h2><p>药水、毒药与已发现功效的原材料均可为对应类型的魔法箭充能。炼金术每级降低 0.5% 充能需求，最多降低 50%；法力与金币费用保持不变。</p><p className="arrow-muted">整个工坊共用上方的面板快捷键。原有魔法箭能力入口会打开本页所属的统一工坊。</p></section>
    <p role="status" className="arrow-status">{state.message}</p>
  </div>;
}
