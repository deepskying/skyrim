import type { EquippedHudItem } from './hud';
import { formatDurability } from './format';
import { useEffect, useState } from 'react';

export function EquippedHud({ items }: { items: EquippedHudItem[] }) {
  // Reserve space above the list for a temporary break/warning notification.
  const rowsForHeight = () => Math.max(1, Math.min(6, Math.floor((window.innerHeight * .82 - 180) / 88)));
  const [rows, setRows] = useState(rowsForHeight);
  useEffect(() => {
    const resize = () => setRows(rowsForHeight());
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);
  if (!items.length) return null;
  return <section className="equipped-hud-grid" aria-label="当前装备耐久" style={{ gridTemplateRows: `repeat(${Math.min(rows, items.length)}, auto)` }}>
    {items.map((item) => <article className={`durability-hud equipped-hud-item ${item.kind}`} key={item.id}>
      <div className="hud-copy">
        <div className="equipped-hud-heading"><b className="hud-title" title={item.title}>{item.title}</b><span>{item.detail}</span></div>
        <div className="hud-value"><strong>{formatDurability(item.current)} <small>/ {formatDurability(item.maximum)}</small></strong><span>{Math.round(item.current / item.maximum * 100)}%</span></div>
        <div className="hud-track" role="progressbar" aria-label={`${item.title}耐久`} aria-valuemin={0} aria-valuemax={item.maximum} aria-valuenow={item.current}><i style={{ width: `${item.current / item.maximum * 100}%` }} /></div>
      </div>
    </article>)}
  </section>;
}
