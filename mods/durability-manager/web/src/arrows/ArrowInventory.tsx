import { useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState } from './types';
import { moveQueue } from './rules';
export function ArrowInventory({ state, action }: { state: ArrowState; action: WorkshopAction }) {
  const [search, setSearch] = useState(''), [filter, setFilter] = useState('all');
  const [dragged, drag] = useState<number>();
  const q = state.ammoQueue, ids = q?.ids ?? [];
  const items = state.arrows.filter(a => a.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()) && (filter === 'all' || (filter === 'normal' ? a.family === 'normal' : a.family !== 'normal')));
  const edit = (next: number[], enabled = q?.enabled ?? false) => action('queueEdit', { ids: [...new Set(next)], enabled });
  return <div className="arrow-inventory">
    <section className="arrow-queue"><header><div><small>YOUR FIRING ORDER</small><h2>使用队列 <span>{ids.length} / {q?.limit ?? 64}</span></h2></div><div className="arrow-controls"><label><input type="checkbox" checked={q?.enabled ?? false} disabled={!q?.available} onChange={e => edit(ids, e.target.checked)} />队列优先</label><button disabled={!q?.available || !ids.some(id => state.arrows.some(a => a.id === id && a.count > 0 && a.usable !== false))} onClick={() => action('queueStart')}>从队首开始</button></div></header>
      <div className="arrow-queue-items">{ids.map((id, index) => { const a = state.arrows.find(a => a.id === id) ?? q?.items?.find(a => a.id === id); return <article key={id} draggable onDragStart={() => drag(id)} onDragEnd={() => drag(undefined)} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (dragged !== undefined) edit(moveQueue(ids, dragged, id)); drag(undefined); }}><small>{index + 1} · {a?.equipped ? '使用中' : a?.count ? '等待使用' : '缺货 · 跳过'}</small><b>{a?.name ?? '来源缺失的箭矢'}</b><span>×{a?.count ?? 0}</span><div><button aria-label={`前移${a?.name}`} disabled={!index} onClick={() => edit(moveQueue(ids, id, ids[index - 1]))}>←</button><button aria-label={`后移${a?.name}`} disabled={index === ids.length - 1} onClick={() => edit(moveQueue(ids, id, ids[index + 1]))}>→</button><button aria-label={`移除${a?.name}`} onClick={() => edit(ids.filter(x => x !== id))}>×</button></div></article>; })}{!ids.length && <p className="arrow-muted">将常用箭矢加入队列，持弓时优先使用队首，耗尽后自动切换。</p>}</div>
    </section>
    <div className="arrow-toolbar"><div className="workshop-tabs">{[['all', '全部'], ['normal', '普通'], ['magic', '魔法']].map(([id, name]) => <button key={id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{name}</button>)}</div><input aria-label="搜索箭矢" placeholder="搜索背包中的箭矢…" value={search} onChange={e => setSearch(e.target.value)} /></div>
    <section className="arrow-inventory-grid" aria-label="箭矢网格">{items.map(a => <article key={a.id} className={`arrow-grid-card ${a.equipped ? 'selected' : ''}`}>
      <header className="arrow-card-stats"><span className="arrow-damage" aria-label={`物理伤害 ${Math.round(a.damage)}`} title="物理伤害">⚔ {Math.round(a.damage)}</span><strong aria-label={`库存 ${a.count}`}>×{a.count}</strong></header>
      <div className="arrow-card-body"><span className={`arrow-sigil ${a.family}`}>➶</span><div><b title={a.name}>{a.name}</b><small>{a.bolt ? '弩矢' : a.family === 'normal' ? '普通箭' : '魔法箭'}{a.equipped ? ' · 已装备' : ''}</small></div></div>
      {a.usable === false && <small>原法术或基材不可用</small>}
      <div className="arrow-card-actions"><button className="arrow-primary" aria-label={`装备${a.name}`} disabled={a.equipped || a.usable === false || !a.count} onClick={() => action('equip', { id: a.id })}>{a.equipped ? '当前已装备' : '装备箭矢'}</button>
        {ids.includes(a.id) ? <small className="arrow-queued">✓ 已在使用队列</small> : <button className="arrow-card-enqueue" aria-label={`将${a.name}加入使用队列`} disabled={!q?.available || a.bolt || a.usable === false || !a.count || ids.length >= (q?.limit ?? 64)} onClick={() => edit([...ids, a.id], ids.length ? q?.enabled : true)}>＋ 加入队列</button>}
      </div>
    </article>)}{!items.length && <p className="arrow-muted">没有符合条件的箭矢。</p>}</section>
    <p className="arrow-muted">装备箭矢时工坊会关闭，以便角色完成装备动作。</p>
  </div>;
}
