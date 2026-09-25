import { useEffect, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState, Quote, Selection } from './types';
import { craftBatchMax, craftInputMax, craftingAccessError, materialHighlight, planCraft } from './rules';
import { allocateBases, fillCharge, reconcileSelection, replaceStack } from './quantity';
import { QuantityInput } from './QuantityInput';
import { ResourceMeter } from './ResourceMeter';
import { ResourceIcon } from './ResourceIcon';
import { useCraftQuote } from './useCraftQuote';

export function MagicCrafting({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const [selection, setSelection] = useState<Selection>({ spell: 0, bases: [], materials: [] });
  const [search, setSearch] = useState(''), [filter, setFilter] = useState('candidate');
  const accessError = craftingAccessError(state, false);
  const plan = planCraft(state, selection);
  const tx = useCraftQuote<Quote>(state, action, false, { ...selection, runtime: !!plan.spell?.adapter?.runtime }, active && !plan.error);
  const { quote, busy, quoting, error } = tx;
  useEffect(() => {
    if (!active || busy) return;
    setSelection(previous => {
      const next = reconcileSelection(state, previous);
      return JSON.stringify(next) === JSON.stringify(previous) ? previous : next;
    });
  }, [state.arrows, state.spells, state.materials, active, busy]);
  const spells = state.spells.filter(s => (s.craftable ? 'candidate' : s.eligibility?.status === 'excluded' ? 'excluded' : 'review') === filter && `${s.name} ${s.source}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const baseUse = quote?.bases ?? allocateBases(selection.bases, plan.total);
  const ingredients = quote?.ingredients ?? selection.materials.map(m => ({ name: state.materials.find(x => x.id === m.id)?.name ?? '材料', count: m.count }));
  const total = quote?.total ?? plan.total;
  const excess = Math.max(0, plan.energy - total * plan.charge);
  const changeQuantity = (kind: 'bases' | 'materials', id: number, count: number) => setSelection(previous => ({ ...previous, [kind]: replaceStack(previous[kind], id, count) }));

  return <div className="magic-workbench">
    <div className="craft-recipe">
      <section className="craft-spell-section arrow-card" aria-label="选择法术">
        <header className="craft-section-heading"><div><small>法术配方</small><h2>{plan.spell?.name ?? '选择要封存的法术'}</h2></div><input aria-label="搜索法术" placeholder="搜索法术或来源…" value={search} onChange={e => setSearch(e.target.value)} /></header>
        <div className="craft-spell-filters">{[['candidate', '可制作'], ['review', '待适配'], ['excluded', '暂不支持']].map(([id, label]) => <button key={id} disabled={busy} aria-pressed={filter === id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div>
        <div className="craft-spell-shelf">{spells.map(s => {
          const highlight = materialHighlight(state.materials, s);
          return <button key={s.id} disabled={busy} aria-pressed={s.id === selection.spell} className={[s.id === selection.spell && 'selected', highlight && `material-${highlight}`].filter(Boolean).join(' ')} onClick={() => setSelection(previous => reconcileSelection(state, { ...previous, spell: s.id }))}><span>✧</span><div><b>{s.name}</b><small>{s.source}</small></div>{s.id === selection.spell && <i>✓</i>}</button>;
        })}{!spells.length && <p className="arrow-muted">没有符合条件的已学法术。</p>}</div>
        {plan.spell && <p className="craft-spell-description">{plan.spell.eligibility?.reasons.join('；') || '选择基材和充能材料后，即可确认制作。'}</p>}
      </section>
      <div className="craft-ingredients">
        <section className="craft-stock-card arrow-card" aria-label="箭矢用量">
          <header className="craft-section-heading"><div><small>基材</small><h2>箭矢用量</h2></div><span className="craft-selection-total">{plan.target}<small> / {craftBatchMax} 支</small></span></header>
          <p className="craft-stock-hint">直接输入数量，可混用多种箭矢。</p>
          <div className="craft-stock-list">{plan.spell?.craftable ? plan.base.map(a => {
            const count = selection.bases.find(b => b.id === a.id)?.count ?? 0;
            const maximum = Math.max(0, Math.min(a.count, craftInputMax, craftBatchMax - selection.bases.filter(b => b.id !== a.id).reduce((n, b) => n + b.count, 0)));
            return <article key={a.id} className={count ? 'selected' : ''}><div className="craft-item-info"><b>➶ {a.name}</b><small className="craft-stock-badge">库存 {a.count}</small></div><QuantityInput name={a.name} count={count} maximum={maximum} disabled={busy} onChange={n => changeQuantity('bases', a.id, n)} /></article>;
          }) : <p className="craft-empty">先在上方选择可制作的法术。</p>}{plan.spell?.craftable && !plan.base.length && <p className="craft-empty">背包中没有适用的箭矢。</p>}</div>
          <footer><button disabled={busy || !selection.bases.length} onClick={() => setSelection(previous => ({ ...previous, bases: [] }))}>清空箭矢</button><span>0 表示不使用</span></footer>
        </section>
        <section className="craft-stock-card arrow-card" aria-label="充能材料用量">
          <header className="craft-section-heading"><div><small>药水 · 原材料</small><h2>充能材料</h2></div><div className="craft-charge-actions">
            <button className="charge-fill" disabled={busy || !plan.spell?.craftable || !plan.target || plan.energy >= plan.target * plan.charge || !plan.materials.length} onClick={() => setSelection(previous => fillCharge(state, previous))}>补足充能</button>
            <button className="charge-fill" title="只用药水补足，不消耗毒药和原材料" disabled={busy || !plan.spell?.craftable || !plan.target || plan.energy >= plan.target * plan.charge || !plan.materials.some(m => m.kind === 'potion')} onClick={() => setSelection(previous => fillCharge(state, previous, true))}>补足药水</button>
            <button className="charge-clear" disabled={busy || !selection.materials.length} onClick={() => setSelection(previous => ({ ...previous, materials: [] }))}>清空材料</button>
          </div></header>
          <div className="craft-material-tools"><span>{plan.energy} / {plan.target * plan.charge} 充能</span>{!!plan.spell?.craftable && <span>接受：{plan.spell.adapter?.material ?? '任意数值型功效'}{state.materialGenericPercent ? `，其他数值型功效按 ${state.materialGenericPercent}% 计入` : ''}</span>}</div>
          <div className="craft-stock-list">{plan.spell?.craftable ? plan.materials.map(m => {
            const count = selection.materials.find(x => x.id === m.id)?.count ?? 0;
            const kind = m.kind === 'potion' ? '药水' : m.kind === 'poison' ? '毒药' : '原材料';
            return <article key={m.id} className={count ? 'selected' : ''}><div className="craft-item-info"><b>{m.name}</b><div className="craft-material-badges"><small className={`craft-stock-badge ${m.kind}`} title={`${kind} · 库存 ${m.count}`}>库存 {m.count}</small><small className="craft-charge-badge" title={`每份提供 ${m.units} 点充能`}>+{m.units} 充能</small></div></div><QuantityInput name={m.name} count={count} maximum={Math.min(craftInputMax, m.count)} disabled={busy} onChange={n => changeQuantity('materials', m.id, n)} /></article>;
          }) : <p className="craft-empty">选定法术后显示匹配的充能材料。</p>}{plan.spell?.craftable && !plan.materials.length && <p className="craft-empty">背包里没有可充能的药水或材料。本配方接受：{plan.spell.adapter?.material ?? '任意数值型功效'}。</p>}</div>
          <footer><span>补足充能按 药水→毒药→原材料，补足药水只消耗药水</span></footer>
        </section>
      </div>
    </div>

    <aside className="craft-summary arrow-card" aria-label="制作预览">
      <header><small>YOUR CREATION</small><h2>{quote?.outputs[0]?.name ?? (plan.spell ? `${plan.spell.name} · 封存箭` : '等待选择法术')}</h2><p><strong>{total}</strong> / 计划 {plan.target} 支</p></header>
      <div className="craft-summary-scroll">
        <section className="craft-unit-cost"><h3>每支消耗</h3><div>
          <span><ResourceIcon kind="gold" />金币<b>{plan.spell?.adapter?.gold ?? '—'}</b></span>
          <span><ResourceIcon kind="mana" />法力<b>{plan.spell?.adapter?.mana ?? '—'}</b></span>
          <span><ResourceIcon kind="charge" />充能<b>{plan.spell ? plan.charge : '—'}</b></span>
        </div></section>
        <ResourceMeter name="法力" kind="mana" current={state.resources?.magicka} cost={quote?.magicka ?? plan.mana} />
        <ResourceMeter name="金币" kind="gold" current={state.resources?.gold} cost={quote?.gold ?? plan.gold} />
        <ResourceMeter name="充能" kind="charge" current={quote?.suppliedCharge ?? plan.energy} cost={total * plan.charge} />
        <p className="arrow-muted">已选材料提供充能 · 计划需要 {plan.target * plan.charge}{plan.energy < plan.target * plan.charge ? `，还差 ${plan.target * plan.charge - plan.energy}` : ''}。{excess > 0 ? '多余充能不会保留。' : ''}</p>
        <section className="craft-receipt"><header><h3>消耗材料清单</h3><small>{quote ? '已核对' : '预估'}</small></header>{baseUse.map(b => <div key={`base-${b.id}`}><span>{state.arrows.find(a => a.id === b.id)?.name ?? '箭矢'}</span><b>×{b.count}</b></div>)}{ingredients.map((m, index) => <div key={`material-${index}`}><span>{m.name}</span><b>×{m.count}</b></div>)}{!baseUse.length && !ingredients.length && <p>选择箭矢和充能材料后，清单将在这里显示。</p>}</section>
      </div>
      <footer><p role="status">{accessError || error || plan.error || (quoting ? '正在核对库存与费用…' : quote ? '清单已核对，可以开始制作；开始后离开附魔台也会继续。' : '请重新核对清单。')}</p><button className="arrow-primary" disabled={!quote || busy || quoting || !!plan.error} onClick={tx.commit}>{busy ? '正在加入队列…' : `开始制作 ${total} 支`}</button><button className="recheck-quote" disabled={busy || !!plan.error || !!accessError} onClick={tx.refresh}>重新核对清单</button></footer>
    </aside>
  </div>;
}
