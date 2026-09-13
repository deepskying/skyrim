import { useEffect, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState, Quote, Selection } from './types';
import { planCraft } from './rules';
import { allocateBases, reconcileSelection, replaceStack } from './quantity';
import { QuantitySlider } from './QuantitySlider';
import { ResourceMeter } from './ResourceMeter';
import { useCraftQuote } from './useCraftQuote';

const steps = ['选择法术', '选择箭矢', '材料充能'];
export function MagicCrafting({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const [selection, setSelection] = useState<Selection>({ spell: 0, bases: [], materials: [] });
  const [step, setStep] = useState(0), [search, setSearch] = useState(''), [filter, setFilter] = useState('candidate');
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
  const canAdvance = [true, !!plan.spell?.craftable, !!plan.spell?.craftable && plan.target > 0 && plan.target <= 100];
  const shownStep = canAdvance[step] ? step : canAdvance[1] ? 1 : 0;
  const spells = state.spells.filter(s => (s.craftable ? 'candidate' : s.eligibility?.status === 'excluded' ? 'excluded' : 'review') === filter && `${s.name} ${s.source}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const baseUse = quote?.bases ?? allocateBases(selection.bases, plan.total);
  const ingredients = quote?.ingredients ?? selection.materials.map(m => ({ name: state.materials.find(x => x.id === m.id)?.name ?? '材料', count: m.count }));
  const total = quote?.total ?? plan.total;
  const excess = Math.max(0, plan.energy - total * plan.charge);
  const changeQuantity = (kind: 'bases' | 'materials', id: number, count: number) => setSelection(previous => ({ ...previous, [kind]: replaceStack(previous[kind], id, count) }));

  return <div className="magic-wizard">
    <section className="wizard-selector arrow-card">
      <nav className="craft-stepper" aria-label="制作步骤">{steps.map((name, index) => <button key={name} aria-current={shownStep === index ? 'step' : undefined} className={shownStep === index ? 'current' : shownStep > index ? 'complete' : ''} disabled={busy || !canAdvance[index]} onClick={() => setStep(index)}><span>{shownStep > index ? '✓' : String(index + 1).padStart(2, '0')}</span><b>{name}</b></button>)}</nav>
      <div className="wizard-heading"><div><small>STEP {shownStep + 1} OF 3</small><h2>{steps[shownStep]}</h2></div><span>{shownStep === 0 ? plan.spell?.name ?? '从已学法术中选择' : shownStep === 1 ? `已选 ${plan.target} / 100 支` : `${plan.energy} / ${plan.target * plan.charge} 充能`}</span></div>
      <div className="wizard-body">
        {shownStep === 0 && <>
          <div className="arrow-toolbar"><div className="workshop-tabs">{[['candidate', '可制作'], ['review', '待适配'], ['excluded', '暂不支持']].map(([id, label]) => <button key={id} disabled={busy} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div><input aria-label="搜索法术" placeholder="搜索法术或来源…" value={search} onChange={e => setSearch(e.target.value)} /></div>
          <div className="arrow-spells">{spells.map(s => <button key={s.id} disabled={busy} aria-pressed={s.id === selection.spell} className={s.id === selection.spell ? 'selected' : ''} onClick={() => setSelection(previous => reconcileSelection(state, { ...previous, spell: s.id }))}><span>✧</span><b>{s.name}</b><small>{s.source}</small></button>)}{!spells.length && <p className="arrow-muted">没有符合条件的已学法术。</p>}</div>
          {plan.spell && <p className="spell-explanation">{plan.spell.eligibility?.reasons.join('；')}</p>}
        </>}
        {shownStep === 1 && <>
          <p className="arrow-muted">拖动滑块或输入数量。0 表示不使用，多种基材按选择顺序消耗。</p>
          <div className="wizard-quantities">{plan.base.map(a => {
            const count = selection.bases.find(b => b.id === a.id)?.count ?? 0;
            const maximum = Math.max(0, Math.min(a.count, 100 - selection.bases.filter(b => b.id !== a.id).reduce((n, b) => n + b.count, 0)));
            return <article key={a.id} className={count ? 'has-quantity' : ''}><header><span className="quantity-icon">➶</span><div><b>{a.name}</b><small>库存 {a.count} 支</small></div><strong>{count} 支</strong></header><QuantitySlider name={a.name} count={count} maximum={maximum} disabled={busy} onChange={n => changeQuantity('bases', a.id, n)} /></article>;
          })}{!plan.base.length && <p className="arrow-muted">背包中没有适用的基材箭矢。</p>}</div>
        </>}
        {shownStep === 2 && <>
          <div className="wizard-charge"><progress aria-label="材料充能" value={Math.min(plan.energy, plan.target * plan.charge)} max={Math.max(1, plan.target * plan.charge)} /><p>可制作 <b>{total} / {plan.target}</b> 支 · 每支 {plan.charge} 充能</p></div>
          <p className="arrow-muted">药水优先，其次毒药与原材料；数量为 0 时不会消耗。</p>
          <div className="wizard-quantities">{plan.materials.map(m => {
            const count = selection.materials.find(x => x.id === m.id)?.count ?? 0, maximum = Math.min(10000, m.count);
            const add = Math.min(maximum - count, Math.max(0, Math.ceil((plan.target * plan.charge - plan.energy) / m.units)));
            const kind = m.kind === 'potion' ? '药水' : m.kind === 'poison' ? '毒药' : '原材料';
            return <article key={m.id} className={count ? 'has-quantity' : ''}><header><span className={`quantity-icon ${m.kind}`}>{m.kind === 'ingredient' ? '✧' : '◇'}</span><div><b>{m.name}</b><small>{kind} · 库存 {m.count} · 每份 +{m.units} 充能</small></div><button aria-label={`用${m.name}补足充能`} disabled={busy || add <= 0} onClick={() => changeQuantity('materials', m.id, count + add)}>补足</button></header><QuantitySlider name={m.name} count={count} maximum={maximum} disabled={busy} onChange={n => changeQuantity('materials', m.id, n)} /></article>;
          })}{!plan.materials.length && <p className="arrow-muted">没有匹配功效的药水、毒药或已发现功效的原材料。</p>}</div>
        </>}
      </div>
      <footer className="wizard-navigation"><button disabled={shownStep === 0 || busy} onClick={() => setStep(shownStep - 1)}>← 上一步</button><span>{shownStep === 2 ? excess > 0 ? `多余 ${excess} 充能不会保留` : '确认前不会消耗任何资源' : '返回修改时会保留兼容的选择'}</span>{shownStep < 2 && <button className="arrow-primary" disabled={busy || !canAdvance[shownStep + 1]} onClick={() => setStep(shownStep + 1)}>下一步 →</button>}</footer>
    </section>

    <aside className="wizard-preview arrow-card" aria-label="制作预览">
      <header><small>YOUR CREATION</small><h2>{quote?.outputs[0]?.name ?? (plan.spell ? `${plan.spell.name} · 封存箭` : '等待选择法术')}</h2><p><strong>{total}</strong> / 计划 {plan.target} 支</p></header>
      <div className="wizard-preview-scroll">
        <section className="craft-unit-cost"><h3>每支消耗</h3><div><span>金币<b>{plan.spell?.adapter?.gold ?? '—'}</b></span><span>法力<b>{plan.spell?.adapter?.mana ?? '—'}</b></span><span>充能<b>{plan.spell ? plan.charge : '—'}</b></span></div></section>
        <ResourceMeter name="法力" current={state.resources?.magicka} cost={quote?.magicka ?? plan.mana} />
        <ResourceMeter name="金币" current={state.resources?.gold} cost={quote?.gold ?? plan.gold} />
        <ResourceMeter name="充能" current={quote?.suppliedCharge ?? plan.energy} cost={total * plan.charge} />
        <p className="arrow-muted">已选材料提供充能 · 计划需要 {plan.target * plan.charge}{plan.energy < plan.target * plan.charge ? `，还差 ${plan.target * plan.charge - plan.energy}` : ''}。{excess > 0 ? '多余充能不会保留。' : ''}</p>
        <section className="wizard-receipt"><header><h3>消耗材料清单</h3><small>{quote ? '已核对' : '预估'}</small></header>{baseUse.map(b => <div key={`base-${b.id}`}><span>{state.arrows.find(a => a.id === b.id)?.name ?? '箭矢'}</span><b>×{b.count}</b></div>)}{ingredients.map((m, index) => <div key={`material-${index}`}><span>{m.name}</span><b>×{m.count}</b></div>)}{!baseUse.length && !ingredients.length && <p>选择箭矢和充能材料后，清单将在这里显示。</p>}</section>
      </div>
      <footer><p role="status">{error || plan.error || (quoting ? '正在核对库存与费用…' : quote ? '清单已核对，可以确认制作。' : '请重新核对清单。')}</p><button className="arrow-primary" disabled={shownStep !== 2 || !quote || busy || quoting || !!plan.error} onClick={tx.commit}>{busy ? '正在制作…' : `确认制作 ${total} 支`}</button><button className="recheck-quote" disabled={busy || !!plan.error} onClick={tx.refresh}>重新核对清单</button></footer>
    </aside>
  </div>;
}
