import type { WorkshopAction } from '../bridge';
import type { ArrowState } from './types';

// The pool banks every soul the player or a follower captures, and the panel is the only
// way back out: points plus gold buy filled gems the vanilla enchanting table accepts.
export function SoulPoolPage({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const pool = state.soulPool;
  if (!pool) return <section className="arrows-page" hidden={!active}><p className="arrow-status">灵魂池数据尚未同步，请重新读档。</p></section>;
  const ratio = pool.capacity > 0 ? Math.max(0, Math.min(1, pool.points / pool.capacity)) : 0;
  const ready = pool.materials.every(material => material.owned >= material.count) && pool.gold >= pool.upgradeGold;
  return <section className="arrows-page soul-page" hidden={!active}>
    <section className="arrow-card soul-meter-card">
      <header><div><small>SOUL POOL</small><h2>灵魂池</h2></div><span className="soul-tier">{pool.tier} 级 · 上限 {pool.capacity}</span></header>
      <div className="soul-meter" role="progressbar" aria-valuemin={0} aria-valuemax={pool.capacity} aria-valuenow={pool.points}>
        <div className="soul-meter-fill" style={{ width: `${ratio * 100}%` }} />
        <b>{pool.points} / {pool.capacity}</b>
      </div>
      <p className="arrow-muted">你是或随从的每一次吸魂都会汇入这里；池满后回到原版吸魂，只填充背包里的空灵魂石。累计吸收 {pool.absorbed} 点。</p>
      {!pool.enabled && <p className="arrow-muted">灵魂池已在 MagicArrows.ini 的 [SoulPool] 中关闭。</p>}
    </section>
    <div className="soul-columns">
      <section className="arrow-card">
        <header><div><small>NEXT TIER</small><h2>灵魂池扩容</h2></div><span className="soul-tier">上限 +10</span></header>
        <p className="arrow-muted">扩容材料在本次随机后随角色存档保存，读完存档不会改变；扩容成功后才会重新随机下一级需求。</p>
        <ul className="soul-requirements">
          {pool.materials.map(material => <li key={material.id} className={material.owned >= material.count ? 'met' : ''}><span>{material.name}</span><b>{material.owned} / {material.count}</b></li>)}
          <li className={pool.gold >= pool.upgradeGold ? 'met' : ''}><span>金币</span><b>{pool.gold} / {pool.upgradeGold}</b></li>
        </ul>
        <button className="arrow-primary" disabled={!ready} onClick={() => action('soulUpgrade')}>扩容到 {pool.capacity + 10} 点</button>
      </section>
      <section className="arrow-card">
        <header><div><small>WITHDRAW</small><h2>兑换灵魂石</h2></div><span className="soul-tier">点数 + 金币</span></header>
        <p className="arrow-muted">换回来的填好灵魂石直接进背包，附魔台与武器充能照原版使用。</p>
        <div className="soul-gem-list">
          {pool.gems.map(gem => <article key={gem.level} className={gem.can > 0 ? '' : 'locked'}>
            <span>{gem.name}</span>
            <small>{gem.points} 点 · {gem.gold} 金币 · 可兑 {gem.can}</small>
            <div><button disabled={gem.can < 1} onClick={() => action('soulConvert', { level: gem.level, count: 1 })}>兑换 1</button>
              <button disabled={gem.can < 1} onClick={() => action('soulConvert', { level: gem.level, count: gem.can })}>全部 {gem.can}</button></div>
          </article>)}
        </div>
      </section>
      <section className="arrow-card">
        <header><div><small>DEPOSIT</small><h2>存入灵魂石</h2></div><span className="soul-tier">{pool.points} / {pool.capacity}</span></header>
        {pool.deposit.length === 0 ? <p className="arrow-muted">背包里没有可以存入的填好灵魂石。</p> :
          <div className="soul-gem-list">{pool.deposit.map(entry => <article key={entry.id}>
            <span>{entry.name} ×{entry.count}</span>
            <small>每颗 {entry.points} 点 · 本次可存 {Math.min(entry.count, entry.room)}</small>
            <div><button disabled={entry.room < 1} onClick={() => action('soulDeposit', { id: entry.id, count: Math.min(entry.count, entry.room) })}>存入 {Math.min(entry.count, entry.room)}</button></div>
          </article>)}</div>}
      </section>
    </div>
  </section>;
}
