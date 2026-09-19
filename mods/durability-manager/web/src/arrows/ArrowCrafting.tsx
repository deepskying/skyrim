import { useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState, NormalQuote } from './types';
import { useCraftQuote } from './useCraftQuote';
import { craftingAccessError } from './rules';
export { MagicCrafting } from './MagicCrafting';

export function NormalCrafting({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const [recipe, select] = useState(0), [count, setCount] = useState(1), [search, setSearch] = useState('');
  const r = state.recipes.find(r => r.id === recipe);
  const accessError = craftingAccessError(state, true);
  const valid = !accessError && !!r?.craftable && count > 0 && Number.isInteger(count) && count <= r.maxBatches;
  const tx = useCraftQuote<NormalQuote>(state, action, true, { recipe, batches: count }, active && valid);
  return <div className="arrow-columns"><section className="arrow-card"><h2>普通箭矢配方</h2><p className="arrow-muted">需要附近有铁匠设备，沿用锻造台材料与条件，无需额外金币或法力。</p><input aria-label="搜索普通箭配方" placeholder="搜索配方…" value={search} onChange={e => setSearch(e.target.value)} /><div className="arrow-item-list">{state.recipes.filter(r => `${r.name} ${r.source}`.includes(search)).map(r => <button key={r.id} className={`arrow-row ${recipe === r.id ? 'selected' : ''}`} disabled={tx.busy} onClick={() => { select(r.id); setCount(1); }}><span className="arrow-sigil">➶</span><span><b>{r.name}</b><small>{r.craftable ? `每批 ${r.yield} 支` : r.reason ?? '暂不可制作'}</small></span></button>)}</div></section><aside className="arrow-card arrow-inspector">{r ? <><small>RECIPE DETAILS</small><h2>{r.name}</h2><p>{r.source}</p>{r.ingredients.map((i, n) => <p key={n}>{i.name} · {i.have} / {i.need * count}</p>)}{r.conditions?.map((c, n) => <p key={n}>{c.met ? '✓' : '○'} {c.name}{c.orNext ? '（或下一项）' : ''}</p>)}<p>{r.reason}</p><label>制作批数<input aria-label="普通箭制作批数" type="number" value={count} min="1" max={Math.max(1, r.maxBatches)} disabled={tx.busy || !r.craftable} onChange={e => setCount(Math.max(1, Math.min(r.maxBatches, Math.floor(Number(e.target.value) || 1))))} /></label><h3>获得 {count * r.yield} 支</h3><p role="status">{accessError || tx.error || (tx.quoting ? '正在核对配方…' : valid ? '确认前不会消耗材料。' : '当前材料或配方条件不足。')}</p><button className="arrow-primary" disabled={!tx.quote || tx.busy || !valid} onClick={tx.commit}>{tx.busy ? '正在制作…' : '确认制作'}</button><button disabled={!valid || tx.busy} onClick={tx.refresh}>重新核对清单</button></> : <p>选择一项配方查看材料和制作数量。</p>}</aside></div>;
}
