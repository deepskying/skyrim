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
        <svg viewBox="0 0 100 100" className="order-diamond" aria-hidden="true">
          <path className="order-fill" d="M50 7 93 50 50 93 7 50Z" />
          <path className="order-track" d="M50 3 97 50 50 97 3 50Z" />
          <path className="order-progress" d="M50 3 97 50 50 97 3 50Z" pathLength="100" strokeDasharray={`${Math.round(entry.progress * 1000) / 10} 100`} />
          <text x="50" y="53" dominantBaseline="middle" textAnchor="middle">{entry.label}</text>
        </svg>
        <span className="order-name" title={entry.name}>{entry.name}</span>
      </article>)}
      {hidden > 0 && <span className="craft-order-more" aria-label={`另有 ${hidden} 种法术排队`}>+{hidden}</span>}
    </div>
  </section>;
}
