import { useEffect, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState } from './types';
import { SoulGemIcon } from './SoulGemIcon';

// The pool banks every soul the player or a follower captures, and the panel is the only
// way back out: points plus gold buy filled gems the vanilla enchanting table accepts.
// Requirements stay inline so the upgrade card does not grow a row per material.
export function SoulPoolPage({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const pool = state.soulPool;
  const gems = pool?.gems ?? [];
  const [level, setLevel] = useState(0);
  const [count, setCount] = useState(1);
  const choice = gems.find(gem => gem.level === level) ?? gems.find(gem => gem.can > 0) ?? gems[0];
  const maximum = Math.max(0, choice?.can ?? 0);
  useEffect(() => { setCount(current => Math.max(1, Math.min(current, Math.max(1, maximum)))); }, [maximum]);
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
        <div className="soul-requirements" role="list">
          <span className="soul-requirements-label">扩容需求</span>
          {pool.materials.map(material => {
            const missing = Math.max(0, material.count - material.owned);
            return <span key={material.id} role="listitem" className={`soul-requirement${missing ? '' : ' met'}`}
              title={`${material.name}：${material.owned} / ${material.count}`}>
              {material.name}<b>×{material.count}</b>{missing > 0 && <i>缺 {missing}</i>}
            </span>;
          })}
          {(() => {
            const missing = Math.max(0, pool.upgradeGold - pool.gold);
            return <span role="listitem" className={`soul-requirement gold${missing ? '' : ' met'}`} title={`金币：${pool.gold} / ${pool.upgradeGold}`}>
              金币<b>×{pool.upgradeGold}</b>{missing > 0 && <i>缺 {missing}</i>}
            </span>;
          })()}
        </div>
        <button className="arrow-primary" disabled={!ready} onClick={() => action('soulUpgrade')}>扩容到 {pool.capacity + 10} 点</button>
      </section>
      <section className="arrow-card">
        <header><div><small>WITHDRAW</small><h2>兑换灵魂石</h2></div><span className="soul-tier">点数 + 金币</span></header>
        <p className="arrow-muted">先挑一张候选卡片，再拖下面的滑条决定数量；换回来的填好灵魂石直接进背包，附魔台与武器充能照原版使用。</p>
        <div className="soul-gem-cards" role="radiogroup" aria-label="兑换候选">
          {pool.gems.map(gem => {
            const selected = gem === choice;
            return <button key={gem.level} type="button" role="radio" aria-checked={selected} disabled={gem.can < 1}
              className={`soul-gem-card${selected ? ' selected' : ''}`}
              onClick={() => { setLevel(gem.level); setCount(1); }}>
              <SoulGemIcon />
              <b>{gem.name}</b>
              <small>{gem.points} 点 + {gem.gold} 金币</small>
              <em>{gem.can > 0 ? `可兑 ${gem.can}` : '不足'}</em>
            </button>;
          })}
        </div>
        <div className={`soul-gem-slider${maximum < 1 ? ' locked' : ''}`}>
          <div className="soul-gem-slider-head"><span>{choice ? choice.name : '灵魂石'} · 兑换数量</span><b>{maximum > 0 ? `${count} / ${maximum}` : '—'}</b></div>
          <input type="range" min={1} max={Math.max(1, maximum)} step={1} value={Math.min(count, Math.max(1, maximum))} disabled={maximum < 1}
            onChange={event => setCount(Math.max(1, Math.min(Number(event.target.value), Math.max(1, maximum))))} aria-label="兑换数量" />
        </div>
        <button className="arrow-primary soul-gem-action" disabled={maximum < 1}
          onClick={() => action('soulConvert', { level: choice.level, count })}>
          {maximum < 1 ? '点数或金币不足' : `兑换 ${count} 颗`}
        </button>
      </section>
      <section className="arrow-card">
        <header><div><small>DEPOSIT</small><h2>存入灵魂石</h2></div><span className="soul-tier">{pool.points} / {pool.capacity}</span></header>
        {pool.deposit.length === 0 ? <p className="arrow-muted">背包里没有可以存入的填好灵魂石。</p> :
          <div className="soul-gem-list">{pool.deposit.map(entry => <article key={entry.id}>
            <span><SoulGemIcon />{entry.name} ×{entry.count}</span>
            <small>每颗 {entry.points} 点 · 本次可存 {Math.min(entry.count, entry.room)}</small>
            <div><button disabled={entry.room < 1} onClick={() => action('soulDeposit', { id: entry.id, count: Math.min(entry.count, entry.room) })}>存入 {Math.min(entry.count, entry.room)}</button></div>
          </article>)}</div>}
      </section>
    </div>
  </section>;
}
