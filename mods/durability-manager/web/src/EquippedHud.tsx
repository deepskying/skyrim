import type { EquippedHudItem } from './hud';
import { formatDurability } from './format';
import { useEffect, useState } from 'react';

// Reserve room for the level/readouts, an optional temporary notice, and a
// remaining-count footer. The frame itself is clamped to the game viewport.
export function equippedHudCapacity(viewportHeight: number, hasNotification: boolean) {
  const usableHeight = Math.max(0, viewportHeight * .96 - (hasNotification ? 320 : 160));
  return Math.floor(usableHeight / 46);
}

export function EquippedHud({ items, hasNotification = false }: { items: EquippedHudItem[]; hasNotification?: boolean }) {
  const [viewportHeight, setViewportHeight] = useState(() => window.innerHeight);
  useEffect(() => {
    const resize = () => setViewportHeight(window.innerHeight);
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);
  if (!items.length) return null;
  const visible = items.slice(0, equippedHudCapacity(viewportHeight, hasNotification));
  const hidden = items.length - visible.length;
  return <section className="equipped-hud-grid" aria-label="当前装备耐久">
    {visible.map((item) => <article className={`durability-hud equipped-hud-item ${item.kind}`} key={item.id}>
      <div className="hud-copy">
        <div className="equipped-hud-heading"><span>{item.detail}</span><b className="hud-title" title={item.title}>{item.title}</b><strong>{formatDurability(item.current)} <small>/ {formatDurability(item.maximum)}</small></strong></div>
        <div className="hud-track" role="progressbar" aria-label={`${item.title}耐久`} aria-valuemin={0} aria-valuemax={item.maximum} aria-valuenow={item.current}><i style={{ width: `${item.current / item.maximum * 100}%` }} /></div>
      </div>
    </article>)}
    {hidden > 0 && <span className="equipped-hud-remaining" aria-label={`另有 ${hidden} 件装备耐久未显示`}>另有 {hidden} 件装备</span>}
  </section>;
}
