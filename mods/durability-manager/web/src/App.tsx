import { useEffect, useMemo, useState } from 'react';
import { demoState } from './demo';
import type { EquipmentItem, PanelState, Settings } from './types';

type Tab = 'durability' | 'settings';

declare global {
  interface Window {
    DurabilityManager?: { receiveState: (next: PanelState) => void };
    durabilityManagerAction?: (data: string) => void;
  }
}

const emptyState: PanelState = {
  equipped: [], repairQueue: [], atForge: false, capturingHotkey: false,
  settings: { hotkey: { key: 'F', keyCode: 0x21, shift: true, ctrl: false, alt: false }, lowDurabilityThreshold: 30, weaponDisplaySeconds: 3, enableLowDurabilityWarning: true, allowEnchantedItemsToBreak: true },
};

function send(type: string, data: Record<string, unknown> = {}) {
  window.durabilityManagerAction?.(JSON.stringify({ type, ...data }));
}

function percentage(item: EquipmentItem) {
  return item.maximum > 0 ? Math.max(0, Math.min(100, item.current / item.maximum * 100)) : 0;
}

function stateFor(item: EquipmentItem, threshold: number) {
  if (item.broken) return 'broken';
  if (percentage(item) < threshold) return 'warning';
  return 'healthy';
}

function hotkeyLabel(settings: Settings) {
  const binding = settings.hotkey;
  return [binding.ctrl && 'Ctrl', binding.shift && 'Shift', binding.alt && 'Alt', binding.key].filter(Boolean).join(' + ');
}

export function App() {
  const [state, setState] = useState<PanelState>(import.meta.env.DEV ? demoState : emptyState);
  const [tab, setTab] = useState<Tab>('durability');
  const [selectedId, setSelectedId] = useState<number>();
  const [draft, setDraft] = useState<Settings>(state.settings);

  useEffect(() => {
    window.DurabilityManager = {
      receiveState: (next) => {
        setState(next);
        setDraft(next.settings);
      },
    };
    send('ready');
    return () => { delete window.DurabilityManager; };
  }, []);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') send('close');
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, []);

  const repairItems = useMemo(() => {
    const rows = [...state.repairQueue];
    for (const item of state.equipped) {
      if (item.current < item.maximum && !rows.some((row) => row.id === item.id)) rows.push(item);
    }
    return rows;
  }, [state.equipped, state.repairQueue]);
  const selected = repairItems.find((item) => item.id === selectedId) ?? repairItems[0];
  const lowCount = state.equipped.filter((item) => stateFor(item, state.settings.lowDurabilityThreshold) !== 'healthy').length;

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-rune">ᛏ</span><div><p>SKYRIM FORGE LEDGER</p><h1>装备耐久</h1></div></div>
      <nav className="tabs" aria-label="耐久面板分页">
        <button className={tab === 'durability' ? 'active' : ''} onClick={() => setTab('durability')} type="button">⌁ 耐久状态</button>
        <button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')} type="button">⚙ 配置</button>
      </nav>
      <div className={`forge-state ${state.atForge ? 'active' : ''}`}><span>⚒</span>{state.atForge ? '锻炉修复模式' : '状态查看模式'}</div>
      <button className="close" onClick={() => send('close')} title="关闭 (Esc)" type="button">×</button>
    </header>

    {tab === 'durability' ? <section className="durability-page">
      <div className="section-heading"><div><p>EQUIPPED GEAR</p><h2>当前装备</h2></div><span className={lowCount ? 'alert-count' : 'ok-count'}>{lowCount ? `${lowCount} 件需要注意` : '所有装备状态良好'}</span></div>
      <section className="equipment-grid">
        {state.equipped.map((item) => {
          const itemState = stateFor(item, state.settings.lowDurabilityThreshold);
          const value = percentage(item);
          return <article className={`equipment-card ${itemState}`} key={item.id}>
            <div className="card-top"><span className="slot">{item.slot}</span><span className="status">{item.broken ? '已破损' : `${Math.round(value)}%`}</span></div>
            <h3>{item.name}</h3><div className="durability-line"><b>{item.current}</b><span>/ {item.maximum}</span></div>
            <div className="bar"><i style={{ width: `${value}%` }} /></div>
            <div className="tags">{item.enchanted && <span>✦ 附魔</span>}{item.quest && <span>任务豁免</span>}{item.broken && <span>不可使用</span>}</div>
          </article>;
        })}
        {state.equipped.length === 0 && <p className="empty">尚未发现已装备的武器或护甲。</p>}
      </section>

      <section className="repair-section">
        <div className="section-heading"><div><p>REPAIR QUEUE</p><h2>待修复装备</h2></div><span>{state.atForge ? '选择装备以查看材料' : '前往锻炉后可修复'}</span></div>
        <div className="repair-layout">
          <div className="repair-list">
            {repairItems.map((item) => <button className={`repair-row ${selected?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setSelectedId(item.id)} type="button">
              <span className={`mini-bar ${stateFor(item, state.settings.lowDurabilityThreshold)}`}><i style={{ width: `${percentage(item)}%` }} /></span>
              <span><b>{item.name}</b><small>{item.slot} · {item.current} / {item.maximum}</small></span>
              {item.broken && <em>破损</em>}<span className="hammer">⚒</span>
            </button>)}
            {!repairItems.length && <p className="empty">没有耐久未满的装备。</p>}
          </div>
          <aside className="repair-detail">
            {selected ? <><p>REPAIR DETAILS</p><h3>{selected.name}</h3><div className="repair-numbers"><span>耐久</span><strong>{selected.current} / {selected.maximum}</strong><span>修复后</span><strong>{selected.maximum} / {selected.maximum}</strong></div>
              <div className="materials"><span>所需原材料</span><b>{selected.material ?? '待材料映射'} × {selected.materialCount ?? '—'}</b></div>
              <button className="repair-button" disabled={!state.atForge || !selected.repairable} onClick={() => send('repair', { id: selected.id })} type="button">⚒ {state.atForge ? '修复装备' : '需要锻炉'}</button>
              {!state.atForge && <small>在锻炉激活“修复装备”后，锤子功能才会启用。</small>}
            </> : <p className="empty">选择一件装备以查看修复详情。</p>}
          </aside>
        </div>
      </section>
    </section> : <section className="settings-page">
      <div className="section-heading"><div><p>MOD SETTINGS</p><h2>配置</h2></div><span>保存后立即生效</span></div>
      <section className="settings-card">
        <div className="setting"><div><h3>唤起快捷键</h3><p>在游戏中打开或关闭装备耐久面板。</p></div><div className="hotkey-control"><kbd>{state.capturingHotkey ? '请按下新快捷键…' : hotkeyLabel(draft)}</kbd><button onClick={() => send(state.capturingHotkey ? 'cancelHotkeyCapture' : 'beginHotkeyCapture')} type="button">{state.capturingHotkey ? '取消' : '重新绑定'}</button></div></div>
        <label className="setting range-setting"><div><h3>低耐久预警阈值 <b>{draft.lowDurabilityThreshold}%</b></h3><p>已装备物品低于此耐久时触发 HUD 预警。</p></div><input max="99" min="1" onChange={(event) => setDraft({ ...draft, lowDurabilityThreshold: Number(event.target.value) })} type="range" value={draft.lowDurabilityThreshold} /></label>
        <label className="setting range-setting"><div><h3>武器提示显示时长 <b>{draft.weaponDisplaySeconds.toFixed(1)} 秒</b></h3><p>装备或切换武器后，HUD 显示精确耐久的持续时间。</p></div><input max="10" min="0.5" onChange={(event) => setDraft({ ...draft, weaponDisplaySeconds: Number(event.target.value) })} step="0.5" type="range" value={draft.weaponDisplaySeconds} /></label>
        <label className="setting toggle-setting"><div><h3>启用低耐久 HUD 预警</h3><p>当耐久首次跌破阈值时显示预警，避免反复刷屏。</p></div><input checked={draft.enableLowDurabilityWarning} onChange={(event) => setDraft({ ...draft, enableLowDurabilityWarning: event.target.checked })} type="checkbox" /></label>
        <label className="setting toggle-setting"><div><h3>允许附魔装备破碎</h3><p>开启时，普通附魔装备归零后会破碎并返还材料；唯一装备始终保留为可修复的破损状态。</p></div><input checked={draft.allowEnchantedItemsToBreak} onChange={(event) => setDraft({ ...draft, allowEnchantedItemsToBreak: event.target.checked })} type="checkbox" /></label>
        <div className="setting-actions"><span>配置将保存到 <code>DurabilityManager.ini</code>。</span><button className="save" onClick={() => send('saveSettings', draft)} type="button">保存配置</button></div>
      </section>
    </section>}
    <footer>{state.message || `按 ${hotkeyLabel(state.settings)} 可随时查看耐久状态。`}</footer>
  </main>;
}
