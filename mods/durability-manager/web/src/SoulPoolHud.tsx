import type { SoulPoolHudSnapshot } from './soul-hud';

// Sits above the crafting queue: ten notches, one per tenth of the pool, so the fill reads
// at a glance while the number keeps showing the capacity an upgrade changes.
export function SoulPoolHud({ pool }: { pool?: SoulPoolHudSnapshot }) {
  if (!pool?.enabled) return null;
  const ratio = Math.max(0, Math.min(1, pool.points / pool.capacity));
  const filled = pool.points > 0 ? Math.max(1, Math.round(ratio * 10)) : 0;
  return <section className="soul-pool-hud" aria-label={`灵魂池 ${pool.points} / ${pool.capacity}`}>
    <header><span>灵魂池</span><small>{pool.tier} 级上限</small><b>{pool.points} / {pool.capacity}</b></header>
    <div className="soul-pool-segments" role="progressbar" aria-label="灵魂池容量" aria-valuemin={0} aria-valuemax={pool.capacity} aria-valuenow={pool.points}>
      {Array.from({ length: 10 }, (_, index) => <i key={index} className={index < filled ? 'on' : ''} />)}
    </div>
  </section>;
}
