import { resourceSegments } from './quantity';
export function ResourceMeter({ name, current, cost }: { name: string; current?: number; cost: number }) {
  const r = resourceSegments(current, cost);
  const format = (n: number) => Number(n.toFixed(1)).toLocaleString('zh-CN');
  return <section className={`craft-resource ${r.shortage > 0 ? 'insufficient' : ''}`}>
    <header><b>{name}</b><span>当前 {r.known ? format(r.held) : '—'}</span></header>
    <div className="resource-segments" role="meter" aria-label={`${name}制作后剩余`} aria-valuemin={0} aria-valuemax={Math.max(1, r.held)} aria-valuenow={r.remaining} aria-valuetext={r.known ? `剩余 ${format(r.remaining)}，消耗 ${format(r.spending)}${r.shortage ? `，不足 ${format(r.shortage)}` : ''}` : '等待库存数据'}>
      <span className="resource-kept" style={{ width: `${r.remainingPercent}%` }} /><span className="resource-used" style={{ width: `${r.spendingPercent}%` }} />
    </div><div className="resource-key"><span>剩余 {r.known ? format(r.remaining) : '—'}</span><span>消耗 {format(r.spending)}</span></div>
    {r.shortage > 0 && <p className="resource-shortage">还差 {format(r.shortage)} {name}</p>}
  </section>;
}
