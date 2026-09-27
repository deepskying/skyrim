import { useEffect, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState } from './types';
import { SoulGemIcon } from './SoulGemIcon';

type UpgradePlan = NonNullable<ArrowState['soulPool']>['options'][number];
// The pool banks every soul the player or a follower captures, and the panel is the only
// way back out: points plus gold buy filled gems the vanilla enchanting table accepts.
// Requirements stay inline so the upgrade card does not grow a row per material.
export function SoulPoolPage({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const pool = state.soulPool;
  const gems = pool?.gems ?? [];
  const [counts, setCounts] = useState<Record<number, number>>({});
  const wanted = (gem: { level: number; can: number }) => Math.max(0, Math.min(counts[gem.level] ?? 0, Math.max(0, gem.can)));
  const totalGems = gems.reduce((sum, gem) => sum + wanted(gem), 0);
  const totalPoints = gems.reduce((sum, gem) => sum + wanted(gem) * gem.points, 0);
  const totalGold = gems.reduce((sum, gem) => sum + wanted(gem) * gem.gold, 0);
  if (!pool) return <section className="arrows-page" hidden={!active}><p className="arrow-status">灵魂池数据尚未同步，请重新读档。</p></section>;
  const ratio = pool.capacity > 0 ? Math.max(0, Math.min(1, pool.points / pool.capacity)) : 0;
  const plans = pool.options ?? [];
  // Every plan costs the same gold and the same kind/quantity budget; only the materials differ,
  // so a plan is affordable the moment its own list is covered.
  const planLabel = (index: number) => `方案${['甲', '乙', '丙', '丁'][index] ?? index + 1}`;
  const planReady = (plan: UpgradePlan) => plan.materials.length > 0 && plan.materials.every(material => material.owned >= material.count) && pool.gold >= pool.upgradeGold;
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
        <header><div><small>NEXT TIER</small><h2>灵魂池扩容</h2></div><span className="soul-tier">上限 {pool.capacity + 10} 点</span></header>
        <p className="arrow-muted">每一级给出两套方案：材料种类数、每种数量与金币完全相同，只有材料本身不同，可以挑一套更好凑齐的。需求随角色存档保存，读完存档不会改变；扩容成功后才会重新随机下一级。</p>
        <div className="soul-plans" role="list">
          {plans.map(plan => {
            const ready = planReady(plan);
            return <article key={plan.id} role="listitem" className={`soul-plan${ready ? ' ready' : ''}`}>
              <header><b>{planLabel(plan.id)}</b><span>{plan.materials.length} 种材料 · {pool.upgradeGold} 金币</span></header>
              <div className="soul-requirements" role="list">
                {plan.materials.map(material => {
                  const missing = Math.max(0, material.count - material.owned);
                  return <span key={material.id} role="listitem" className={`soul-requirement${missing ? '' : ' met'}`}
                    title={`${material.name}：已有 ${material.owned}，需要 ${material.count}\n来源：${material.source}`}>
                    <span className="soul-requirement-label">{material.name}<b>{material.owned}/{material.count}</b></span>
                    <small className="soul-requirement-source">{material.source}</small>
                  </span>;
                })}
                {(() => {
                  const missing = Math.max(0, pool.upgradeGold - pool.gold);
                  return <span role="listitem" className={`soul-requirement gold${missing ? '' : ' met'}`} title={`金币：${pool.gold} / ${pool.upgradeGold}`}>
                    金币<b>{pool.gold}/{pool.upgradeGold}</b>
                  </span>;
                })()}
              </div>
              <button className="arrow-primary soul-plan-action" disabled={!ready}
                onClick={() => action('soulUpgrade', { option: plan.id })}>
                {plan.materials.length === 0 ? '本级别暂无可用材料' : ready ? `按${planLabel(plan.id)}扩容` : '材料或金币不足'}
              </button>
            </article>;
          })}
        </div>
      </section>
      <section className="arrow-card">
        <header><div><small>WITHDRAW</small><h2>兑换灵魂石</h2></div><span className="soul-tier">点数 + 金币</span></header>
        <p className="arrow-muted">在每张卡片下方的输入框里填写想兑换的颗数，可以一次挑多种；换回来的填好灵魂石直接进背包，附魔台与武器充能照原版使用。</p>
        <div className="soul-gem-cards" role="group" aria-label="兑换候选">
          {pool.gems.map(gem => {
            const value = wanted(gem);
            return <article key={gem.level} className={`soul-gem-card${value > 0 ? ' selected' : ''}${gem.can < 1 ? ' locked' : ''}`}>
              <SoulGemIcon />
              <b>{gem.name}</b>
              <small>{gem.points} 点 + {gem.gold} 金币</small>
              <em>{gem.can > 0 ? `可兑 ${gem.can}` : '点数或金币不足'}</em>
              <input type="number" min={0} max={Math.max(0, gem.can)} value={value} disabled={gem.can < 1}
                aria-label={`${gem.name} 兑换数量`}
                onChange={event => {
                  const next = Math.max(0, Math.min(Number(event.target.value.replace(/[^0-9]/g, '')) || 0, Math.max(0, gem.can)));
                  setCounts(current => ({ ...current, [gem.level]: next }));
                }} />
            </article>;
          })}
        </div>
        <div className="soul-gem-summary"><span>共 {totalGems} 颗 · 消耗 {totalPoints} 点灵魂</span><b>{totalGold} 金币</b></div>
        <button className="arrow-primary soul-gem-action" disabled={totalGems < 1}
          onClick={() => { action('soulConvert', { items: gems.map(gem => ({ level: gem.level, count: wanted(gem) })).filter(item => item.count > 0) }); setCounts({}); }}>
          {totalGems < 1 ? '请填写兑换数量' : `兑换 ${totalGems} 颗 · 消耗 ${totalGold} 金币`}
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
