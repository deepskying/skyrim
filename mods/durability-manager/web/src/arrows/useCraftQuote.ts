import { useEffect, useRef, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import type { ArrowState, NormalQuote, Quote } from './types';
import { nextArrowRequest } from './useArrowBridge';
import { matchesCraftReply } from './rules';

/** Correlates native receipts; changing a selection invalidates its previous token. */
export function useCraftQuote<T extends Quote | NormalQuote>(state: ArrowState, action: WorkshopAction, normal: boolean, selection: Record<string, unknown>, active: boolean) {
  const key = JSON.stringify(selection), quoteType = normal ? 'normalQuote' : 'quote', craftType = normal ? 'normalCraft' : 'craft';
  const [accepted, setAccepted] = useState<{ key: string; quote: T }>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [quoting, setQuoting] = useState(false);
  const [retry, setRetry] = useState(0);
  const pending = useRef<{ id: number; key: string; type: string }>();
  const submitted = useRef(false);
  useEffect(() => {
    pending.current = undefined; setAccepted(undefined); setError(''); setBusy(false); submitted.current = false;
    setQuoting(active);
    if (!active) return;
    const id = nextArrowRequest();
    const timer = window.setTimeout(() => {
      pending.current = { id, key, type: quoteType };
      action(quoteType, { ...JSON.parse(key), requestID: id });
    }, 220);
    return () => { window.clearTimeout(timer); pending.current = undefined; };
  }, [key, active, retry, action, quoteType]);
  useEffect(() => {
    const reply = state.workshopReply, request = pending.current;
    if (!reply || !matchesCraftReply(request, key, reply)) return;
    pending.current = undefined; setQuoting(false); setBusy(false); submitted.current = false;
    if (reply.type === quoteType) {
      const quote = (normal ? state.normalQuote : state.quote) as T | undefined;
      if (reply.ok && quote) { setAccepted({ key, quote }); setError(''); }
      else { setAccepted(undefined); setError(reply.error || '无法计算制作清单'); }
    } else {
      setAccepted(undefined); setError(reply.ok ? '制作完成，成品已加入背包。' : reply.error || '制作未完成，请重新核对清单');
    }
  }, [state.workshopReply, state.quote, state.normalQuote, key, normal, quoteType]);
  const quote = active && accepted?.key === key ? accepted.quote : undefined;
  const commit = () => {
    if (!quote || busy || submitted.current || quoting) return;
    submitted.current = true; setBusy(true);
    const id = nextArrowRequest(); pending.current = { id, key, type: craftType };
    action(craftType, { token: quote.token, runtime: 'runtime' in quote && !!quote.runtime, requestID: id });
  };
  return { quote, error, busy, quoting, commit, refresh: () => setRetry(n => n + 1) };
}
