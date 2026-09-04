import { useEffect, useMemo, useState } from 'react';
import { demoState } from './demo';
import type { CardType, EquipmentItem, MaterialRequirement, PanelState, Settings } from './types';

type Tab = 'workshop' | 'settings';
type HudMessage = { id: number; kind: 'weapon' | 'warning'; title: string; detail: string; durationMilliseconds: number; current?: number; maximum?: number };

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
  version: '0.1.21',
  equipped: [], repairQueue: [], capturingHotkey: false,
  forge: { active: false, station: '', refreshCost: 0, refreshes: 0, cards: [] },
  settings: { hotkey: { key: 'F', keyCode: 0x21, shift: true, ctrl: false, alt: false }, lowDurabilityThreshold: 30, weaponDisplaySeconds: 3, enableLowDurabilityWarning: true, allowEnchantedItemsToBreak: true },
};

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null;
}

function finiteNumber(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function optionalFiniteNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function text(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function flag(value: unknown, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function normalizeMaterials(value: unknown): MaterialRequirement[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => {
    if (!isRecord(entry)) return [];
    const name = text(entry.name);
    const required = Math.max(0, Math.floor(finiteNumber(entry.required, 0)));
    const owned = Math.max(0, Math.floor(finiteNumber(entry.owned, 0)));
    return name && required > 0 ? [{ name, required, owned }] : [];
  });
}

function normalizeEquipment(value: unknown, index: number): EquipmentItem | undefined {
  if (!isRecord(value)) return undefined;
  const category = value.category === 'weapon' || value.category === 'armor' || value.category === 'clothing'
    ? value.category
    : 'clothing';
  return {
    id: text(value.id, `unknown:${index}`),
    name: text(value.name, '未命名装备'),
    slot: text(value.slot, '未知槽位'),
    category,
    current: finiteNumber(value.current, 0),
    maximum: Math.max(1, finiteNumber(value.maximum, 100)),
    enhancementLevel: Math.max(0, finiteNumber(value.enhancementLevel, 0)),
    damage: optionalFiniteNumber(value.damage),
    armor: optionalFiniteNumber(value.armor),
    weight: Math.max(0, finiteNumber(value.weight, 0)),
    attackSpeed: optionalFiniteNumber(value.attackSpeed),
    wearRate: optionalFiniteNumber(value.wearRate),
    wearRateLabel: text(value.wearRateLabel, '尚未启用'),
    wearReduction: optionalFiniteNumber(value.wearReduction),
    enchantment: text(value.enchantment) || undefined,
    enchanted: flag(value.enchanted),
    enchantmentReplaceable: flag(value.enchantmentReplaceable),
    quest: flag(value.quest),
    unique: flag(value.unique),
    broken: flag(value.broken),
    repairable: flag(value.repairable),
    repairMaterials: normalizeMaterials(value.repairMaterials),
  };
}

function normalizeState(value: unknown): PanelState {
  if (!isRecord(value)) return emptyState;
  const rawSettings = isRecord(value.settings) ? value.settings : {};
  const rawHotkey = isRecord(rawSettings.hotkey) ? rawSettings.hotkey : {};
  const rawForge = isRecord(value.forge) ? value.forge : {};
  const equipped = Array.isArray(value.equipped)
    ? value.equipped.map(normalizeEquipment).filter((item): item is EquipmentItem => item !== undefined)
    : [];
  const repairQueue = Array.isArray(value.repairQueue)
    ? value.repairQueue.map(normalizeEquipment).filter((item): item is EquipmentItem => item !== undefined)
    : [];
  return {
    version: text(value.version, emptyState.version),
    equipped,
    repairQueue,
    capturingHotkey: flag(value.capturingHotkey),
    message: text(value.message) || undefined,
    forge: {
      active: flag(rawForge.active),
      station: text(rawForge.station),
      refreshCost: Math.max(0, finiteNumber(rawForge.refreshCost, 0)),
      refreshes: Math.max(0, finiteNumber(rawForge.refreshes, 0)),
      cards: Array.isArray(rawForge.cards) ? rawForge.cards as PanelState['forge']['cards'] : [],
    },
    settings: {
      hotkey: {
        key: text(rawHotkey.key, emptyState.settings.hotkey.key),
        keyCode: finiteNumber(rawHotkey.keyCode, emptyState.settings.hotkey.keyCode),
        shift: flag(rawHotkey.shift),
        ctrl: flag(rawHotkey.ctrl),
        alt: flag(rawHotkey.alt),
      },
      lowDurabilityThreshold: finiteNumber(rawSettings.lowDurabilityThreshold, emptyState.settings.lowDurabilityThreshold),
      weaponDisplaySeconds: finiteNumber(rawSettings.weaponDisplaySeconds, emptyState.settings.weaponDisplaySeconds),
      enableLowDurabilityWarning: flag(rawSettings.enableLowDurabilityWarning, emptyState.settings.enableLowDurabilityWarning),
      allowEnchantedItemsToBreak: flag(rawSettings.allowEnchantedItemsToBreak, emptyState.settings.allowEnchantedItemsToBreak),
    },
  };
}

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

function hotkeyParts(settings: Settings) {
  const binding = settings.hotkey;
  return [binding.ctrl && 'Ctrl', binding.shift && 'Shift', binding.alt && 'Alt', binding.key].filter((part): part is string => Boolean(part));
}

function itemIcon(item: EquipmentItem) {
  if (item.category === 'weapon') return '⚔';
  if (item.slot.includes('盾')) return '⛨';
  return item.category === 'armor' ? '◈' : '◇';
}

function MaterialList({ materials }: { materials: MaterialRequirement[] }) {
  return <div className="materials">{materials.map((material, index) => <span className={material.owned < material.required ? 'missing' : ''} key={`${material.name}-${index}`}>{material.name}<b>{material.owned} / {material.required}</b></span>)}</div>;
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
      receiveState: (next) => {
        const normalized = normalizeState(next);
        setState(normalized);
        setDraft(normalized.settings);
      },
      setPanelVisible,
      showHud: (message) => {
        if (hudTimer) window.clearTimeout(hudTimer);
        setHud(message);
        hudTimer = window.setTimeout(() => { setHud(undefined); send('hudHidden', { id: message.id }); }, message.durationMilliseconds);
      },
    };
    send('ready', { version: emptyState.version });
    return () => { if (hudTimer) window.clearTimeout(hudTimer); delete window.DurabilityManager; };
  }, []);

  const visibleEquipment = useMemo(() => {
    const equippedIds = new Set(state.equipped.map((item) => item.id));
    return [...state.equipped, ...state.repairQueue.filter((item) => !equippedIds.has(item.id))];
  }, [state.equipped, state.repairQueue]);
  const selected = useMemo(() => visibleEquipment.find((item) => item.id === selectedId) ?? visibleEquipment[0], [selectedId, visibleEquipment]);
  const hasRepairMaterials = Boolean(selected?.repairMaterials.every((material) => material.owned >= material.required));
  const canRepair = Boolean(selected?.repairable && state.forge.active && hasRepairMaterials);
  const selectedWearRate = optionalFiniteNumber(selected?.wearRate);

  const hudPercentage = hud?.maximum && hud.current !== undefined ? Math.max(0, Math.min(100, hud.current / hud.maximum * 100)) : undefined;

  return <>{hud && <aside className={`durability-hud ${hud.kind}`} aria-live="polite"><span className="hud-rune">{hud.kind === 'warning' ? '!' : 'ᛏ'}</span><div className="hud-copy"><b>{hud.title}</b>{hudPercentage !== undefined && <><div className="hud-value"><strong>{hud.current} / {hud.maximum}</strong><span>{Math.round(hudPercentage)}%</span></div><div className="hud-track" role="progressbar" aria-label="当前耐久" aria-valuemax={hud.maximum} aria-valuemin={0} aria-valuenow={hud.current}><i style={{ width: `${hudPercentage}%` }} /></div></>}<span className="hud-detail">{hud.detail}</span></div></aside>}{panelVisible && <main className="forge-shell">
    <header className="forge-header">
      <div className="brand"><span className="brand-rune">ᛏ</span><div><p>{state.forge.active ? `${state.forge.station} · EQUIPMENT WORKSHOP` : 'SKYRIM FORGE LEDGER'}</p><h1>{state.forge.active ? '装备工坊' : '装备耐久'}</h1></div></div>
      <nav className="tabs" aria-label="装备耐久分页"><button className={tab === 'workshop' ? 'active' : ''} onClick={() => setTab('workshop')} type="button">⌁ 装备</button><button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')} type="button">⚙ 配置</button></nav>
      <span className={`forge-context ${state.forge.active ? 'active' : ''}`}>{state.forge.active ? '⚒ 可修复与强化' : '按快捷键查看状态'}</span>
      <button className="close" onClick={() => send('close')} title="关闭 (Esc)" type="button">×</button>
    </header>

    {tab === 'workshop' ? <section className="workshop-layout">
      <aside className="equipment-list"><div className="list-heading"><div><p>EQUIPMENT</p><h2>装备与损坏物品</h2></div><span>{visibleEquipment.length} 件</span></div>
        <div className="list-scroll">{visibleEquipment.map((item) => <button className={`equipment-row ${selected?.id === item.id ? 'selected' : ''} ${item.broken ? 'broken' : ''}`} key={item.id} onClick={() => setSelectedId(item.id)} type="button"><span className="item-icon">{itemIcon(item)}</span><span className="row-main"><b>{item.name} {item.enhancementLevel > 0 && <em>+{item.enhancementLevel}</em>}</b><small>{item.broken ? '已损坏 · 等待修复' : item.slot} · 耐久 {item.current}/{item.maximum}</small><i><i style={{ width: `${percentage(item)}%` }} /></i></span>{item.enchanted && <span className="enchanted">✦</span>}</button>)}{!visibleEquipment.length && <p className="empty">尚未发现装备或损坏物品。</p>}</div>
      </aside>

      {selected ? <section className="equipment-detail"><div className="detail-title"><div><p>{selected.slot.toUpperCase()}</p><h2>{selected.name} {selected.enhancementLevel > 0 && <span>+{selected.enhancementLevel}</span>}</h2></div><div className={`condition ${selected.broken ? 'broken' : percentage(selected) < state.settings.lowDurabilityThreshold ? 'warning' : ''}`}>{selected.broken ? '已破损' : `${Math.round(percentage(selected))}%`}</div></div>
        <div className="detail-tags"><span>{selected.category === 'weapon' ? '武器' : selected.category === 'armor' ? '护甲' : '服装'}</span>{selected.enchanted && <span>✦ 已附魔</span>}{selected.unique && <span>唯一物品</span>}{selected.quest && <span>任务物品</span>}</div>
        <div className="stat-grid"><div><small>耐久</small><b>{selected.current} <span>/ {selected.maximum}</span></b></div>{selected.category === 'weapon' && <div><small>攻击</small><b>{selected.damage ?? 0}</b></div>}{selected.category === 'armor' && <div><small>防御</small><b>{selected.armor ?? 0}</b></div>}<div><small>重量</small><b>{selected.weight.toFixed(1)}</b></div>{selected.category === 'weapon' && <div><small>攻速</small><b>{(selected.attackSpeed ?? 0).toFixed(2)}×</b></div>}<div className="wear-stat"><small>耐久损耗</small><b>{selectedWearRate === undefined ? '—' : `-${selectedWearRate.toFixed(2)}`}<span>{selectedWearRate === undefined ? ' 尚未启用' : ` / ${selected.wearRateLabel}`}</span></b>{selectedWearRate !== undefined && <i>耐磨减免 {Math.round((selected.wearReduction ?? 0) * 100)}%</i>}</div></div>
        <div className="detail-bar"><i style={{ width: `${percentage(selected)}%` }} /></div>
        <section className="enchantment-info"><small>当前附魔</small><b>{selected.enchantment ?? '无'}</b>{!selected.enchantmentReplaceable && <span>此物品不可替换附魔</span>}</section>
        <section className="action-strip"><div className="repair-summary"><p>修复装备</p>{selected.current >= selected.maximum ? <small>耐久已满</small> : selected.repairMaterials.length ? <MaterialList materials={selected.repairMaterials} /> : <small>没有找到可用的锻造或强化配方</small>}</div><button disabled={!canRepair} onClick={() => send('repair', { id: selected.id })} type="button">{!state.forge.active ? '需锻造设施' : !selected.repairable ? '无法修复' : !hasRepairMaterials ? '材料不足' : '⚒ 修复'}</button></section>
        {state.forge.active ? <section className="card-area"><div className="card-heading"><div><p>ENHANCEMENT DRAFT</p><h3>选择本次强化</h3></div><button onClick={() => send('refreshEnhancements', { id: selected.id })} type="button">↻ 刷新 · {state.forge.refreshCost} 金币</button></div><div className="enhancement-cards">{state.forge.cards.map((card) => <article className={`enhancement-card ${card.type} tier-${card.tier}`} key={card.id}><header><span>{cardIcons[card.type]}</span><small>{cardLabels[card.type]}</small><b>{card.tier}</b></header><h4>{card.title}</h4><strong>{card.value}</strong><p>{card.description}</p><MaterialList materials={card.materials} /><footer><span>成功率 {card.successChance}%</span><button disabled={Boolean(card.blockedReason)} onClick={() => send('applyEnhancement', { cardId: card.id, equipmentId: selected.id })} type="button">{card.blockedReason ?? '选择强化'}</button></footer></article>)}</div></section> : <p className="forge-hint">使用锻造熔炉、冶炼熔炉、砂轮或护甲工作台后，可在两分钟内于附近打开装备工坊。</p>}
      </section> : <section className="detail-empty">选择一件装备以查看详情。</section>}
    </section> : <section className="settings-page">
      <div className="section-heading settings-heading"><div><p>MOD SETTINGS</p><h2>界面与耐久提示</h2></div><span className="settings-status"><i />保存后立即生效</span></div>
      <div className="settings-layout">
        <section className="settings-card">
          <header className="settings-group-title"><span>ᛏ</span><div><p>HUD FEEDBACK</p><h3>战斗提示</h3></div></header>
          <label className="setting range-setting">
            <span className="setting-icon warning-icon">!</span>
            <span className="setting-copy"><small>WARNING THRESHOLD</small><h3>低耐久预警阈值</h3><p>耐久首次低于该比例时，在 HUD 中显示一次醒目预警。</p></span>
            <span className="range-control"><output>{draft.lowDurabilityThreshold}<small>%</small></output><input aria-label="低耐久预警阈值" max="99" min="1" onChange={(event) => setDraft({ ...draft, lowDurabilityThreshold: Number(event.target.value) })} type="range" value={draft.lowDurabilityThreshold} /><span className="range-labels"><span>1%</span><span>危险线</span><span>99%</span></span></span>
          </label>
          <label className="setting range-setting">
            <span className="setting-icon duration-icon">◷</span>
            <span className="setting-copy"><small>DISPLAY DURATION</small><h3>武器提示显示时长</h3><p>装备、切换或拔出武器时，耐久浮窗在屏幕上停留的时间。</p></span>
            <span className="range-control"><output>{draft.weaponDisplaySeconds.toFixed(1)}<small> 秒</small></output><input aria-label="武器提示显示时长" max="10" min="0.5" onChange={(event) => setDraft({ ...draft, weaponDisplaySeconds: Number(event.target.value) })} step="0.5" type="range" value={draft.weaponDisplaySeconds} /><span className="range-labels"><span>0.5 秒</span><span>显示时间</span><span>10 秒</span></span></span>
          </label>
          <label className="setting toggle-setting">
            <span className="setting-icon notification-icon">⌁</span>
            <span className="setting-copy"><small>LOW DURABILITY ALERT</small><h3>启用低耐久 HUD 预警</h3><p>关闭后仍会记录耐久，但不会弹出低耐久提示。</p></span>
            <span className="toggle-control"><input checked={draft.enableLowDurabilityWarning} onChange={(event) => setDraft({ ...draft, enableLowDurabilityWarning: event.target.checked })} type="checkbox" /><span className="toggle-track"><i /></span><b>{draft.enableLowDurabilityWarning ? '已启用' : '已关闭'}</b></span>
          </label>
          <footer className="setting-actions"><span>配置将写入 <code>DurabilityManager.ini</code></span><button className="save" onClick={() => send('saveSettings', draft)} type="button">保存配置</button></footer>
        </section>
        <aside className="settings-aside">
          <section className={`hotkey-card ${state.capturingHotkey ? 'capturing' : ''}`}>
            <header><span>⌨</span><div><p>PANEL HOTKEY</p><h3>面板快捷键</h3></div></header>
            <div className="hotkey-combo">{hotkeyParts(draft).map((part, index) => <span key={`${part}-${index}`}>{index > 0 && <i>+</i>}<kbd>{part}</kbd></span>)}</div>
            <button className="capture-button" onClick={() => send(state.capturingHotkey ? 'cancelHotkeyCapture' : 'beginHotkeyCapture')} type="button">{state.capturingHotkey ? '取消等待' : '修改快捷键'}</button>
            <small>{state.capturingHotkey ? '请按下新的组合键，Esc 可取消。' : '修改后会自动保存，无需再次点击保存配置。'}</small>
          </section>
          <section className="settings-note"><span>i</span><div><h3>提示规则</h3><p>拔出武器提示和低耐久预警互不冲突；阈值只影响低耐久预警。</p></div></section>
        </aside>
      </div>
    </section>}
    <footer className="panel-footer"><span>{state.message || `按 ${hotkeyLabel(state.settings)} 可随时查看耐久状态。`}</span><small>Durability Manager · v{state.version}</small></footer>
  </main>}</>;
}
