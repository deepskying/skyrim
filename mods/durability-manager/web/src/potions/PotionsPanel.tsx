import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { send } from '../bridge';
import { FoodIcon } from './FoodIcon';
import { foodCategory, foodDemo, matchesFood } from './food';
import { potionDemo } from './demo';
import { effectDescription, effectTone, effectTraits, nextPotionIndex, normalizePotions } from './rules';
import type { Potion, PotionState } from './types';
import './potions.css';

declare global { interface Window { WorkshopPotions?: { receive: (value: unknown) => void; key: (key: string) => void } } }
let sequence = 0;
function Bottle() {
  return <svg className="potion-bottle" viewBox="0 0 80 100" aria-hidden="true">
    <path className="bottle-liquid" d="M17 62h46l2 9c2 11-6 16-25 16s-27-5-25-16Z" />
    <path className="bottle-outline" d="M30 24v17L16 62c-4 6-6 12-3 18 3 7 11 10 27 10s24-3 27-10c3-6 1-12-3-18L50 41V24Z" />
    <rect className="bottle-cap" x="28" y="14" width="24" height="10" rx="3" />
  </svg>;
}
export function PotionsPanel({ pageKeyboard, food = false }: { pageKeyboard: boolean; food?: boolean }) {
  const noun = food ? '食物' : '药水';
  const action = food ? '食用一份' : '饮用一瓶';
  const [state, setState] = useState<PotionState>(import.meta.env.DEV ? (food ? foodDemo : potionDemo) : { items: [], token: 0, message: '正在读取药水…' });
  const [search, setSearch] = useState(''), [filter, setFilter] = useState('all');
  const [selectedId, select] = useState<number>();
  const [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false);
  const [notice, setNotice] = useState('');
  const pending = useRef<number>(), lastUse = useRef(0), timer = useRef<number>();
  const grid = useRef<HTMLDivElement>(null), buttons = useRef(new Map<number, HTMLButtonElement>());
  const previousIndex = useRef(0), handler = useRef<(key: string) => boolean>(() => false);
  const items = state.items.filter(p => `${p.name} ${p.effects.map(e => e.name).join(' ')}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()) && (food ? matchesFood(p, filter) : (filter === 'all' || (filter === 'poison' ? p.poison === true : !p.poison && effectTraits(p).some(t => t.tone === filter)))));
  const selected = items.find(p => p.id === selectedId) ?? items[Math.min(previousIndex.current, Math.max(0, items.length - 1))];
  useLayoutEffect(() => {
    if (selected) { previousIndex.current = items.indexOf(selected); if (selected.id !== selectedId) select(selected.id); }
  }, [items, selected, selectedId]);
  useEffect(() => {
    window.WorkshopPotions = { receive: value => {
      const next = normalizePotions(value); if (!next) return;
      setState(old => next.token >= old.token ? next : old);
      if (pending.current !== undefined && next.reply?.requestID === pending.current) {
        pending.current = undefined; window.clearTimeout(timer.current); setBusy(false); setUncertain(false); setNotice(next.message);
      }
    }, key: key => { handler.current(key); } };
    if (!import.meta.env.DEV) send('potionPage', { active: true, food });
    return () => { window.clearTimeout(timer.current); delete window.WorkshopPotions; if (!import.meta.env.DEV) send('potionPage', { active: false, food }); };
  }, []);
  const waitForReply = (id: number) => {
    pending.current = id; setBusy(true); setUncertain(false); window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { setUncertain(true); setNotice('尚未收到游戏结果，请同步背包确认；不会自动重复饮用。'); }, 8000);
  };
  const drink = (potion: Potion) => {
    const now = Date.now();
    if (pending.current !== undefined || now - lastUse.current < 450 || potion.poison || !potion.usable || !state.token) return;
    select(potion.id); lastUse.current = now; setNotice(`正在${food ? '食用' : '饮用'}…`);
    const id = ++sequence; waitForReply(id);
    if (import.meta.env.DEV) {
      setState(old => ({ ...old, token: old.token + 1, items: old.items.map(p => p.id === potion.id ? { ...p, count: p.count - 1 } : p).filter(p => p.count > 0) }));
      pending.current = undefined; window.clearTimeout(timer.current); setBusy(false); setNotice(`预览：已使用${food ? '一份' : '一瓶'}${potion.name}，未写入游戏。`);
    } else send('potionUse', { id: potion.id, token: state.token, requestID: id });
  };
  const refresh = () => {
    if (busy && !uncertain) return;
    if (import.meta.env.DEV) { setNotice('演示库存已同步。'); return; }
    const id = ++sequence; waitForReply(id); send('potionRefresh', { requestID: id });
  };
  handler.current = key => {
    const target = document.activeElement;
    if (target?.matches('input,textarea,select') || target?.closest('[contenteditable="true"]')) return false;
    if (key === 'Enter' || key === ' ') {
      if (target?.closest('button') && !target.matches('.potion-card')) return false;
      if (selected) drink(selected); return true;
    }
    if (!key.startsWith('Arrow') || !selected) return false;
    const cards = [...(grid.current?.querySelectorAll<HTMLButtonElement>('.potion-card') ?? [])];
    const columns = Math.max(1, cards.filter(c => Math.abs(c.offsetTop - (cards[0]?.offsetTop ?? 0)) < 2).length);
    const index = nextPotionIndex(items.indexOf(selected), items.length, columns, key);
    const next = items[index]; if (next) { select(next.id); buttons.current.get(next.id)?.focus({ preventScroll: true }); buttons.current.get(next.id)?.scrollIntoView({ block: 'nearest', inline: 'nearest' }); }
    return true;
  };
  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.shiftKey || event.metaKey || event.isComposing) return;
      if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Enter',' '].includes(event.key)) return;
      if (event.target instanceof Element && event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
      if (!import.meta.env.DEV && !pageKeyboard) { event.preventDefault(); return; }
      if (event.repeat && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); return; }
      if (handler.current(event.key)) event.preventDefault();
    };
    const keyup = (event: KeyboardEvent) => { if (event.key === ' ' && event.target instanceof Element && event.target.matches('.potion-card')) event.preventDefault(); };
    window.addEventListener('keydown',keydown); window.addEventListener('keyup',keyup);
    return () => { window.removeEventListener('keydown',keydown); window.removeEventListener('keyup',keyup); };
  }, [pageKeyboard]);
  const selectedTraits = selected ? effectTraits(selected) : [];
  return <section className="potions-panel" aria-label={`${noun}背包`}>
    <div className="potions-toolbar"><div><span className="potions-eyebrow">{food ? 'YOUR PROVISIONS' : 'YOUR APOTHECARY'}</span><h2>随身{noun} <small>{items.length} 种</small></h2></div><div className="potions-tools"><input aria-label={`搜索${noun}`} placeholder={`搜索${noun}或效果…`} value={search} onChange={e => { setSearch(e.target.value); previousIndex.current = 0; }} /><button disabled={busy && !uncertain} onClick={refresh}>↻ 同步背包</button></div></div>
    <div className="potion-filters" aria-label={`${noun}筛选`}>{(food ? [['all','全部'],['food','食物'],['drink','饮料'],['other','其他'],['health','生命'],['magicka','法力'],['stamina','体力'],['buff','增益']] : [['all','全部'],['health','生命'],['magicka','法力'],['stamina','耐力'],['resist','抗性'],['skill','增益'],['utility','其他'],['harmful','含负面效果'],['poison','毒药']]).map(([key,label]) => <button key={key} aria-pressed={filter === key} className={filter === key ? 'active' : ''} onClick={() => { setFilter(key); previousIndex.current = 0; }}>{label}</button>)}</div>
    <div className="potions-layout"><div ref={grid} className="potions-grid" role="group" aria-label={`${noun}卡片`}>{items.map(p => {
      const tags = effectTraits(p), tone = p.poison ? 'poison' : tags.find(t => t.tone !== 'harmful')?.tone ?? 'utility';
      return <button type="button" key={p.id} ref={node => { if (node) buttons.current.set(p.id,node); else buttons.current.delete(p.id); }} className={`potion-card ${food ? 'food-card' : ''} ${p.id === selected?.id ? 'selected' : ''}`} data-tone={tone} aria-label={`${p.name}，${p.count} ${food ? '份' : '瓶'}${p.usable ? `，点击${action}` : `，${p.reason}`}`} aria-pressed={p.id === selected?.id} aria-disabled={busy || !p.usable} tabIndex={p.id === selected?.id ? 0 : -1} onMouseMove={() => { if (p.id !== selected?.id) select(p.id); }} onFocus={() => select(p.id)} onClick={e => { if (e.detail > 1) return; drink(p); }}>
        <span className="potion-count">×{p.count}</span>{food ? <FoodIcon kind={foodCategory(p).icon} /> : <Bottle />}<b>{p.name}</b>{food && <span className="food-subtype">{foodCategory(p).label}</span>}{!p.usable && <span className="potion-card-reason">{p.reason}</span>}
      </button>;
    })}{!items.length && <p className="potions-empty">{state.token ? `没有符合条件的${noun}。` : '正在读取背包…'}</p>}</div>
    <aside className="potion-detail" aria-label={`${noun}详情`}>{selected ? <><span className="potions-eyebrow">{food ? 'FOOD DETAILS' : 'POTION DETAILS'}</span><h2>{selected.name}</h2><p className="potion-source">{selected.source}</p><div className="potion-detail-tags">{selectedTraits.map(t => <span key={t.id} className={t.tone}><i>{t.icon}</i>{t.name}</span>)}</div><div className="potion-facts"><span>库存 <b>{selected.count}</b></span><span>重量 <b>{selected.weight.toFixed(1)}</b></span><span>价值 <b>{selected.value}</b></span></div><h3>{selected.poison ? '毒药效果' : `${noun}效果`}</h3><div className="potion-effect-list">{selected.effects.map((e,i) => <article key={`${e.id}-${i}`} data-tone={effectTone(e)}><b>{e.harmful ? '! ' : ''}{e.name}</b>{effectDescription(e) && <p>{effectDescription(e)}</p>}<div>{e.hasMagnitude && <span>强度 <strong>{Number(e.magnitude.toFixed(2))}</strong></span>}{e.hasDuration && <span>持续 <strong>{e.duration ? `${e.duration} 秒` : '即时'}</strong></span>}{e.area > 0 && <span>范围 {e.area}</span>}</div>{e.conditional && <small>生效条件由游戏判定</small>}</article>)}{!selected.effects.length && <p>没有可显示的效果说明。</p>}</div><p className="potion-detail-note">显示{noun}基础效果，实际强度由游戏及角色加成决定。</p>{!selected.usable && <p className="potion-unavailable">{selected.reason}</p>}</> : <p className="potions-empty">悬浮或用方向键选择{noun}以查看详情。</p>}</aside></div>
    <footer className="potions-footer"><p>{selected?.poison ? '悬浮查看 · 方向键选择 · 请在游戏背包中为武器涂毒' : `悬浮查看 · 方向键选择 · 点击 / Enter / 空格${action}`}</p><p role="status">{notice || state.message || '使用后保持工坊打开。'}</p></footer>
  </section>;
}
