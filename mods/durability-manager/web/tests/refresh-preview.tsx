// Development-only manual fixture, not an entry point of the packaged game UI.
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from '../src/App';
import { demoState } from '../src/demo';
import '../src/styles.css';

let mode = 'success';
let requestCount = 0;
let state = structuredClone(demoState);
const goldRow = state.forge.cards[0].materials.find((row) => row.isGold);
if (goldRow) goldRow.name = 'Septims'; // Currency detection must not depend on the localized name.
let report = (_count: number) => {};
window.durabilityManagerAction = (raw) => {
  const action = JSON.parse(raw);
  if (action.type === 'ready' || action.type === 'selectEquipment') {
    window.DurabilityManager?.receiveState(state);
  } else if (action.type === 'refreshEnhancements') {
    report(++requestCount);
    const selectedMode = mode;
    if (selectedMode === 'silence') return;
    const cost = state.forge.refreshCost;
    window.setTimeout(() => {
      const success = selectedMode !== 'failure';
      if (success) {
        state = { ...state, forge: { ...state.forge, gold: state.forge.gold - cost, refreshes: state.forge.refreshes + 1,
          refreshCost: cost + 80, cards: state.forge.cards.map((card) => ({ ...card, id: `${card.id}-new`,
            materials: card.materials.map((row) => row.isGold ? { ...row, owned: state.forge.gold - cost } : row) })) } };
      }
      window.DurabilityManager?.receiveState({ ...state, refreshResult: {
        requestId: action.requestId, equipmentId: action.id, success, goldSpent: success ? cost : 0,
        message: success ? `已支付 ${cost} 金币` : '刷新失败：附近没有可用的锻造设施。本次未扣费。',
      } });
    }, selectedMode === 'delayed' ? 3000 : 0);
  }
};
function Preview() {
  const [count, setCount] = useState(0);
  report = setCount;
  return <><div style={{ position: 'fixed', top: 0, left: 0, zIndex: 999, background: '#fff', color: '#111', padding: 6 }}>
    模拟游戏测试，不操作真实金币 · 刷新请求 {count} 次 · <select aria-label="模拟结果" defaultValue={mode} onChange={(event) => { mode = event.target.value; }}>
      <option value="success">立即成功（同类型卡）</option><option value="delayed">延迟 3 秒成功</option>
      <option value="failure">失败不扣费</option><option value="silence">无回包（超时）</option>
    </select></div><App /></>;
}
createRoot(document.getElementById('root')!).render(<Preview />);
