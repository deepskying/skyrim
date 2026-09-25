import { useCallback, useEffect, useState } from 'react';
import { sendArrowAction, type WorkshopAction } from '../bridge';
import { arrowDemo } from './demo';
import { planCraft } from './rules';
import { allocateBases } from './quantity';
import type { ArrowState, Selection } from './types';
declare global { interface Window { MagicArrows?: { receiveState: (state: ArrowState) => void } } }
const empty: ArrowState = { loaded: false, arrows: [], spells: [], materials: [], recipes: [] };
// Browser-only fixture for reviewing the out-of-range crafting messages.
const previewState: ArrowState = import.meta.env.DEV && new URLSearchParams(window.location.search).get('stations') === 'none'
  ? { ...arrowDemo, craftingAccess: { magic: false, normal: false } } : arrowDemo;
let requestSequence = 0;
export const nextArrowRequest = () => ++requestSequence;
export function useArrowBridge() {
  const [state, setState] = useState<ArrowState>(import.meta.env.DEV ? previewState : empty);
  useEffect(() => {
    window.MagicArrows = { receiveState: next => setState(previous => ({ ...next,
      // Native inventory snapshots contain only the active crafting catalogue.
      spells: next.page === 'craft' && next.mode === 'magic' ? next.spells : previous.spells,
      materials: next.page === 'craft' && next.mode === 'magic' ? next.materials : previous.materials,
      recipes: next.page === 'craft' && next.mode === 'normal' ? next.recipes : previous.recipes,
    })) };
    if (!import.meta.env.DEV) sendArrowAction('ready');
    return () => { delete window.MagicArrows; };
  }, []);
  const action: WorkshopAction = useCallback((type, data = {}) => {
    if (!import.meta.env.DEV) { sendArrowAction(type, data); return; }
    setState(prev => {
      const next = { ...prev, workshopReply: null, message: '浏览器预览 · 操作未写入游戏' };
      if (type === 'page') return { ...next, page: String(data.page) };
      if (type === 'workshopMode') return { ...next, mode: String(data.mode), quote: null, normalQuote: null };
      if (type === 'cancelCraft') return { ...next, quote: null, normalQuote: null };
      if (type === 'followerSettings') return { ...next, followers: { available: true, consumeMagicArrows: !!data.consumeMagicArrows } };
      if (type === 'queueEdit') return { ...next, ammoQueue: { ...prev.ammoQueue!, ids: data.ids as number[], enabled: !!data.enabled } };
      if (type === 'equip' || type === 'queueStart') {
        const id = type === 'equip' ? Number(data.id) : prev.ammoQueue?.ids[0];
        const arrow = prev.arrows.find(a => a.id === id);
        if (!arrow || arrow.usable === false || arrow.count <= 0) return next;
        let queue = prev.ammoQueue;
        if (type === 'equip' && !arrow.bolt) {
          if (!queue?.available) return { ...next, message: '队列保存组件不可用，无法将箭矢设为队首' };
          const ids = queue.ids.filter(x => prev.arrows.some(a => a.id === x && a.count > 0 && a.usable !== false));
          queue = { ...queue, ids: [arrow.id, ...ids.filter(x => x !== arrow.id)].slice(0, queue.limit), enabled: true, finished: false };
        } else if (type === 'queueStart' && queue) queue = { ...queue, enabled: true, finished: false };
        return { ...next, ammoQueue: queue, arrows: prev.arrows.map(a => ({ ...a, equipped: a.id === id })) };
      }
      const requestID = Number(data.requestID);
      if (type === 'quote') {
        const selection = { spell: data.spell, bases: data.bases, materials: data.materials } as Selection;
        const p = planCraft(prev, selection);
        return { ...next, workshopReply: { type, requestID, ok: !p.error, error: p.error }, quote: p.error ? null : {
          token: requestID, runtime: !!data.runtime, selection, total: p.total, gold: p.gold, magicka: p.mana, suppliedCharge: p.energy,
          bases: allocateBases(selection.bases, p.total), ingredients: selection.materials.map(m => ({ name: prev.materials.find(x => x.id === m.id)!.name, count: m.count })),
          outputs: [{ name: `${p.spell!.name} · 封存箭`, count: p.total }],
        } };
      }
      if (type === 'normalQuote') {
        const r = prev.recipes.find(r => r.id === data.recipe), n = Number(data.batches);
        const ok = !!r?.craftable && Number.isInteger(n) && n > 0 && n <= r.maxBatches;
        return { ...next, workshopReply: { type, requestID, ok, error: ok ? '' : '配方或数量不可用' }, normalQuote: ok ? { token: requestID, recipe: r!.id, batches: n, name: r!.name, total: n * r!.yield, ingredients: r!.ingredients.map(i => ({ name: i.name, count: i.need * n })) } : null };
      }
      if (type === 'craft' || type === 'normalCraft') return { ...next, workshopReply: { type, requestID, ok: false, error: '浏览器预览不扣资源，请在游戏内确认制作' } };
      return next;
    });
  }, []);
  return { state, action };
}
