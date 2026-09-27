import type { SoulPoolHudSnapshot } from './soul-hud';

// Sits under the durability rows: the fill is the stored points, the number is the capacity
// that an upgrade in the workshop panel changes.
export function SoulPoolHud({ pool }: { pool?: SoulPoolHudSnapshot }) {
  if (!pool?.enabled) return null;
  const ratio = Math.max(0, Math.min(1, pool.points / pool.capacity));
  return <section className="soul-pool-hud" aria-label={`灵魂池 ${pool.points} / ${pool.capacity}`}>
    <header><span>灵魂池</span><small>{pool.tier} 级上限</small><b>{pool.points} / {pool.capacity}</b></header>
    <div className="hud-track soul-pool-track" role="progressbar" aria-label="灵魂池容量" aria-valuemin={0} aria-valuemax={pool.capacity} aria-valuenow={pool.points}>
      <i style={{ width: `${ratio * 100}%` }} />
    </div>
  </section>;
}
