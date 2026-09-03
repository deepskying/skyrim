import { useEffect, useMemo, useState } from 'react';
import { demoState } from './demo';
import type { CardType, EnhancementCard, EquipmentItem, PanelState, Settings } from './types';

type Tab = 'workshop' | 'settings';
type HudMessage = { id: number; kind: 'weapon' | 'warning'; title: string; detail: string; durationMilliseconds: number };

declare global {
  interface Window {
    DurabilityManager?: {
      receiveState: (next: PanelState) => void;
      setPanelVisible: (visible: boolean) => void;
      showHud: (message: HudMessage) => void;
    };
    durabilityManagerAction?: (data: string) => void;
  }
}

const emptyState: PanelState = {
  equipped: [], repairQueue: [], capturingHotkey: false,
  forge: { active: false, station: '', refreshCost: 0, refreshes: 0, cards: [] },
  settings: { hotkey: { key: 'F', keyCode: 0x21, shift: true, ctrl: false, alt: false }, lowDurabilityThreshold: 30, weaponDisplaySeconds: 3, enableLowDurabilityWarning: true, allowEnchantedItemsToBreak: true },
};

const cardLabels: Record<CardType, string> = {
  performance: '性能强化', weight: '重量强化', speed: '攻速强化', durability: '耐久强化', wear: '耐磨强化', charge: '充能强化', enchantment: '附魔替换',
};

const cardIcons: Record<CardType, string> = {
  performance: '⚔', weight: '◒', speed: '↯', durability: '⛨', wear: '⛓', charge: '✦', enchantment: '☽',
};

function send(type: string, data: Record<string, unknown> = {}) {
  window.durabilityManagerAction?.(JSON.stringify({ type, ...data }));
}

function percentage(item: EquipmentItem) {
  return item.maximum > 0 ? Math.max(0, Math.min(100, item.current / item.maximum * 100)) : 0;
}

function hotkeyLabel(settings: Settings) {
  const binding = settings.hotkey;
  return [binding.ctrl && 'Ctrl', binding.shift && 'Shift', binding.alt && 'Alt', binding.key].filter(Boolean).join(' + ');
}

function itemIcon(item: EquipmentItem) {
  if (item.category === 'weapon') return '⚔';
  if (item.slot.includes('盾')) return '⛨';
  return item.category === 'armor' ? '◈' : '◇';
}

function MaterialList({ card }: { card: EnhancementCard }) {
  return <div className="materials">{card.materials.map((material) => <span className={material.owned < material.required ? 'missing' : ''} key={material.name}>{material.name}<b>{material.owned} / {material.required}</b></span>)}</div>;
}

export function App() {
  const [state, setState] = useState<PanelState>(import.meta.env.DEV ? demoState : emptyState);
  const [tab, setTab] = useState<Tab>('workshop');
  const [selectedId, setSelectedId] = useState<string>();
  const [draft, setDraft] = useState<Settings>(state.settings);
  const [panelVisible, setPanelVisible] = useState(import.meta.env.DEV);
  const [hud, setHud] = useState<HudMessage>();

  useEffect(() => {
    let hudTimer: number | undefined;
    window.DurabilityManager = {
      receiveState: (next) => { setState(next); setDraft(next.settings); },
      setPanelVisible,
      showHud: (message) => {
        if (hudTimer) window.clearTimeout(hudTimer);
        setHud(message);
        hudTimer = window.setTimeout(() => { setHud(undefined); send('hudHidden', { id: message.id }); }, message.durationMilliseconds);
      },
    };
    send('ready');
    return () => { if (hudTimer) window.clearTimeout(hudTimer); delete window.DurabilityManager; };
  }, []);

  const selected = useMemo(() => state.equipped.find((item) => item.id === selectedId) ?? state.equipped[0], [selectedId, state.equipped]);
  const canRepair = Boolean(selected?.repairable && selected.current < selected.maximum && state.forge.active);

  return <>{hud && <aside className={`durability-hud ${hud.kind}`} aria-live="polite"><span className="hud-rune">{hud.kind === 'warning' ? '!' : 'ᛏ'}</span><div><b>{hud.title}</b><span>{hud.detail}</span></div></aside>}{panelVisible && <main className="forge-shell">
    <header className="forge-header">
      <div className="brand"><span className="brand-rune">ᛏ</span><div><p>{state.forge.active ? `${state.forge.station} · EQUIPMENT WORKSHOP` : 'SKYRIM FORGE LEDGER'}</p><h1>{state.forge.active ? '装备工坊' : '装备耐久'}</h1></div></div>
      <nav className="tabs" aria-label="装备耐久分页"><button className={tab === 'workshop' ? 'active' : ''} onClick={() => setTab('workshop')} type="button">⌁ 装备</button><button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')} type="button">⚙ 配置</button></nav>
      <span className={`forge-context ${state.forge.active ? 'active' : ''}`}>{state.forge.active ? '⚒ 可修复与强化' : '按快捷键查看状态'}</span>
      <button className="close" onClick={() => send('close')} title="关闭 (Esc)" type="button">×</button>
    </header>

    {tab === 'workshop' ? <section className="workshop-layout">
      <aside className="equipment-list"><div className="list-heading"><div><p>EQUIPMENT</p><h2>已装备物品</h2></div><span>{state.equipped.length} 件</span></div>
        <div className="list-scroll">{state.equipped.map((item) => <button className={`equipment-row ${selected?.id === item.id ? 'selected' : ''} ${item.broken ? 'broken' : ''}`} key={item.id} onClick={() => setSelectedId(item.id)} type="button"><span className="item-icon">{itemIcon(item)}</span><span className="row-main"><b>{item.name} {item.enhancementLevel > 0 && <em>+{item.enhancementLevel}</em>}</b><small>{item.slot} · 耐久 {item.current}/{item.maximum}</small><i><i style={{ width: `${percentage(item)}%` }} /></i></span>{item.enchanted && <span className="enchanted">✦</span>}</button>)}{!state.equipped.length && <p className="empty">尚未发现已装备的物品。</p>}</div>
      </aside>

      {selected ? <section className="equipment-detail"><div className="detail-title"><div><p>{selected.slot.toUpperCase()}</p><h2>{selected.name} {selected.enhancementLevel > 0 && <span>+{selected.enhancementLevel}</span>}</h2></div><div className={`condition ${selected.broken ? 'broken' : percentage(selected) < state.settings.lowDurabilityThreshold ? 'warning' : ''}`}>{selected.broken ? '已破损' : `${Math.round(percentage(selected))}%`}</div></div>
        <div className="detail-tags"><span>{selected.category === 'weapon' ? '武器' : selected.category === 'armor' ? '护甲' : '服装'}</span>{selected.enchanted && <span>✦ 已附魔</span>}{selected.unique && <span>唯一物品</span>}{selected.quest && <span>任务物品</span>}</div>
        <div className="stat-grid"><div><small>耐久</small><b>{selected.current} <span>/ {selected.maximum}</span></b></div>{selected.category === 'weapon' && <div><small>攻击</small><b>{selected.damage ?? 0}</b></div>}{selected.category === 'armor' && <div><small>防御</small><b>{selected.armor ?? 0}</b></div>}<div><small>重量</small><b>{selected.weight.toFixed(1)}</b></div>{selected.category === 'weapon' && <div><small>攻速</small><b>{(selected.attackSpeed ?? 0).toFixed(2)}×</b></div>}<div className="wear-stat"><small>耐久损耗</small><b>{selected.wearRate === undefined ? '—' : `-${selected.wearRate.toFixed(2)}`}<span>{selected.wearRate === undefined ? ' 尚未启用' : ` / ${selected.wearRateLabel}`}</span></b>{selected.wearRate !== undefined && <i>耐磨减免 {Math.round((selected.wearReduction ?? 0) * 100)}%</i>}</div></div>
        <div className="detail-bar"><i style={{ width: `${percentage(selected)}%` }} /></div>
        <section className="enchantment-info"><small>当前附魔</small><b>{selected.enchantment ?? '无'}</b>{!selected.enchantmentReplaceable && <span>此物品不可替换附魔</span>}</section>
        <section className="action-strip"><div><p>修复装备</p><small>{selected.current >= selected.maximum ? '耐久已满' : selected.material ? `需要 ${selected.material} × ${selected.materialCount}` : '材料映射待配置'}</small></div><button disabled={!canRepair} onClick={() => send('repair', { id: selected.id })} type="button">⚒ 修复</button></section>
        {state.forge.active ? <section className="card-area"><div className="card-heading"><div><p>ENHANCEMENT DRAFT</p><h3>选择本次强化</h3></div><button onClick={() => send('refreshEnhancements', { id: selected.id })} type="button">↻ 刷新 · {state.forge.refreshCost} 金币</button></div><div className="enhancement-cards">{state.forge.cards.map((card) => <article className={`enhancement-card ${card.type} tier-${card.tier}`} key={card.id}><header><span>{cardIcons[card.type]}</span><small>{cardLabels[card.type]}</small><b>{card.tier}</b></header><h4>{card.title}</h4><strong>{card.value}</strong><p>{card.description}</p><MaterialList card={card} /><footer><span>成功率 {card.successChance}%</span><button disabled={Boolean(card.blockedReason)} onClick={() => send('applyEnhancement', { cardId: card.id, equipmentId: selected.id })} type="button">{card.blockedReason ?? '选择强化'}</button></footer></article>)}</div></section> : <p className="forge-hint">前往锻造熔炉、砂轮或工作台进入装备工坊，查看修复与强化选项。</p>}
      </section> : <section className="detail-empty">选择一件装备以查看详情。</section>}
    </section> : <section className="settings-page"><div className="section-heading"><div><p>MOD SETTINGS</p><h2>配置</h2></div><span>保存后立即生效</span></div><section className="settings-card"><label className="setting range-setting"><div><h3>低耐久预警阈值 <b>{draft.lowDurabilityThreshold}%</b></h3><p>首次低于该耐久时显示 HUD 预警。</p></div><input max="99" min="1" onChange={(event) => setDraft({ ...draft, lowDurabilityThreshold: Number(event.target.value) })} type="range" value={draft.lowDurabilityThreshold} /></label><label className="setting range-setting"><div><h3>武器提示显示时长 <b>{draft.weaponDisplaySeconds.toFixed(1)} 秒</b></h3><p>装备、切换或拔刀时显示精确耐久。</p></div><input max="10" min="0.5" onChange={(event) => setDraft({ ...draft, weaponDisplaySeconds: Number(event.target.value) })} step="0.5" type="range" value={draft.weaponDisplaySeconds} /></label><label className="setting toggle-setting"><div><h3>启用低耐久 HUD 预警</h3><p>耐久低于阈值时显示一次预警。</p></div><input checked={draft.enableLowDurabilityWarning} onChange={(event) => setDraft({ ...draft, enableLowDurabilityWarning: event.target.checked })} type="checkbox" /></label><div className="setting-actions"><span>配置将保存到 <code>DurabilityManager.ini</code>。</span><button className="save" onClick={() => send('saveSettings', draft)} type="button">保存配置</button></div></section></section>}
    <footer className="panel-footer">{state.message || `按 ${hotkeyLabel(state.settings)} 可随时查看耐久状态。`}</footer>
  </main>}</>;
}
