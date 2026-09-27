import { useEffect, useState } from 'react';
import { craftOrderHudLimit, type CraftOrderSnapshot } from './craft-hud';

// A full ring means the batch is untouched; it leaves the diamond as arrows are crafted.
export function CraftOrderHud({ orders }: { orders?: CraftOrderSnapshot }) {
  const [viewportHeight, setViewportHeight] = useState(() => window.innerHeight);
  useEffect(() => {
    const resize = () => setViewportHeight(window.innerHeight);
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);
  if (!orders?.entries.length) return null;
  const visible = orders.entries.slice(0, craftOrderHudLimit(viewportHeight));
  const hidden = orders.entries.length - visible.length;
  return <section className={`craft-order-hud${orders.paused ? ' paused' : ''}`} aria-label="制作队列">
    <header><span>制作队列</span><small>{orders.entries.length} 种法术{orders.paused ? ` · ${orders.reason || '已暂停'}` : ''}</small></header>
    <div className="craft-order-diamonds">
      {visible.map(entry => <article className={entry.family} key={entry.spell} aria-label={`${entry.name}，剩余 ${entry.remaining} / ${entry.total}`}>
        <svg viewBox="0 0 100 100" className="order-square" aria-hidden="true">
          <rect className="order-fill" x="11" y="11" width="78" height="78" rx="9" />
          <rect className="order-track" x="4" y="4" width="92" height="92" rx="10" />
          <rect className="order-progress" x="4" y="4" width="92" height="92" rx="10" pathLength="100" strokeDasharray={`${Math.round(entry.progress * 1000) / 10} 100`} />
          <text x="50" y="53" dominantBaseline="middle" textAnchor="middle">{entry.label}</text>
        </svg>
        <span className="order-name" title={entry.name}>{entry.name}</span>
      </article>)}
      {hidden > 0 && <span className="craft-order-more" aria-label={`另有 ${hidden} 种法术排队`}>+{hidden}</span>}
    </div>
  </section>;
}
