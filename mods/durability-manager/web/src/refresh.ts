import type { EnhancementCard, RefreshResult } from './types';

export function normalizeRefreshResult(value: unknown): RefreshResult | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const row = value as Record<string, unknown>;
  if (typeof row.requestId !== 'string' || !row.requestId || row.requestId.length > 128 ||
    typeof row.equipmentId !== 'string' || !row.equipmentId || typeof row.success !== 'boolean' ||
    typeof row.goldSpent !== 'number' || !Number.isSafeInteger(row.goldSpent) || row.goldSpent < 0 ||
    typeof row.message !== 'string') return undefined;
  return { requestId: row.requestId, equipmentId: row.equipmentId, success: row.success, goldSpent: row.goldSpent, message: row.message };
}

export type RefreshView = {
  phase: 'idle' | 'waiting' | 'revealing' | 'timeout';
  cards?: EnhancementCard[];
  message: string;
  failed?: boolean;
};

// The controller never sends an action or charges gold. Only a matching native receipt can complete it.
export function createRefreshTransition(show: (view: RefreshView) => void, timers: {
  now: () => number; set: (callback: () => void, delay: number) => number; clear: (id: number) => void;
}) {
  let pending: { requestId: string; equipmentId: string; cards: EnhancementCard[]; started: number; received: boolean } | undefined;
  let generation = 0;
  const handles = new Set<number>();
  const clear = () => { for (const id of handles) timers.clear(id); handles.clear(); };
  const later = (callback: () => void, delay: number) => {
    const token = generation;
    const id = timers.set(() => { handles.delete(id); if (token === generation) callback(); }, delay);
    handles.add(id);
  };
  return {
    start(requestId: string, equipmentId: string, cards: EnhancementCard[]) {
      if (pending) return false;
      generation++;
      pending = { requestId, equipmentId, cards: [...cards], started: timers.now(), received: false };
      show({ phase: 'waiting', cards: pending.cards, message: '正在刷新卡片，请勿重复操作……' });
      later(() => {
        if (pending && !pending.received) show({ phase: 'timeout', cards: pending.cards, failed: true,
          message: '尚未收到游戏结果，未自动重试。请等待或关闭后重新打开面板核对金币与卡片。' });
      }, 10000);
      return true;
    },
    receive(result: RefreshResult | undefined, cards: EnhancementCard[]) {
      if (!pending || pending.received || !result || result.requestId !== pending.requestId || result.equipmentId !== pending.equipmentId) return;
      pending.received = true;
      clear();
      if (!result.success) {
        const previous = pending.cards;
        pending = undefined;
        generation++;
        show({ phase: 'idle', cards: previous, failed: true, message: result.message || '刷新失败，卡片未更换。' });
        return;
      }
      const next = [...cards];
      const message = `已刷新 · 消耗 ${result.goldSpent} 金币`;
      later(() => {
        show({ phase: 'revealing', cards: next, message });
        later(() => { pending = undefined; show({ phase: 'idle', message }); }, 400);
      }, Math.max(0, 140 - (timers.now() - pending.started)));
    },
    isPending: () => Boolean(pending),
    dispose() { generation++; clear(); pending = undefined; },
  };
}
