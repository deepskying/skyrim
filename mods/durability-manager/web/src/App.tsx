import { send } from './bridge';
import { GeneralSettings } from './GeneralSettings';
import { EquipmentSettings } from './EquipmentSettings';
import { WorkshopNavigation, type Tab } from './WorkshopNavigation';
import { useArrowBridge } from './arrows/useArrowBridge';
import { ArrowWorkshop } from './arrows/ArrowWorkshop';
import { ArrowSettings } from './arrows/ArrowSettings';
import { afterDismantle, adjacentEquipment } from './equipment-selection';
import { DismantlePanel } from './DismantlePanel';
import { defaultDismantleHotkey, matchesShortcut, shortcutAllowed } from './dismantle-shortcut';
import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react';
import { demoState } from './demo';
import type { EquipmentItem, MaterialRequirement, PanelState, Settings } from './types';
import { EnhancementPage, MaterialList } from './EnhancementPage';
import { normalizeCards } from './enhancement';
import { createHudReceiver, type HudMessage } from './hud';
import { EquippedBadge } from './EquippedBadge';
import { formatDurability } from './format';
import { equippedFirst } from './equipment';
import { costLabel, missingCost } from './cost';
import { normalizeRefreshResult } from './refresh';


declare global {
  interface Window {
    DurabilityManager?: {
      receiveState: (next: PanelState) => void;
      setPanelVisible: (visible: boolean) => void;
      showHud: (message: unknown) => void;
      escape: () => void;
      openArrows: () => void;
      navigateEquipment: (direction: number) => void;
      directDismantle: (event: { sequence: string; id: string }) => void;
    };
    durabilityManagerAction?: (data: string) => void;
  }
}

const emptyState: PanelState = {
  version: '0.1.43',
  equipped: [], repairQueue: [], capturingHotkey: false,
  forge: { active: false, station: '', gold: 0, refreshCost: 0, refreshes: 0, cards: [] },
  settings: { hotkey: { key: 'A', keyCode: 0x1E, shift: true, ctrl: false, alt: false }, lowDurabilityThreshold: 30, weaponDisplaySeconds: 3, enableLowDurabilityWarning: true, enableWorkshopSounds: true, allowEnchantedItemsToBreak: true },
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
    return name && required > 0 ? [{ name, required, owned, isGold: typeof entry.isGold === 'boolean' ? entry.isGold : undefined }] : [];
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
    equipped: flag(value.equipped),
    quantity: Math.max(1, Math.floor(finiteNumber(value.quantity, 1))),
    current: finiteNumber(value.current, 0),
    maximum: Math.max(1, finiteNumber(value.maximum, 100)),
    enhancementLevel: Math.max(0, finiteNumber(value.enhancementLevel, 0)),
    damage: optionalFiniteNumber(value.damage),
    armor: optionalFiniteNumber(value.armor),
    weight: Math.max(0, finiteNumber(value.weight, 0)),
    attackSpeed: optionalFiniteNumber(value.attackSpeed),
    chargeCurrent: optionalFiniteNumber(value.chargeCurrent),
    chargeCapacity: optionalFiniteNumber(value.chargeCapacity),
    chargeBonus: optionalFiniteNumber(value.chargeBonus),
    wearRate: optionalFiniteNumber(value.wearRate),
    wearRateLabel: text(value.wearRateLabel, '尚未启用'),
    wearReduction: optionalFiniteNumber(value.wearReduction),
    movementWearRate: optionalFiniteNumber(value.movementWearRate),
    enchantment: text(value.enchantment) || undefined,
    enchanted: flag(value.enchanted),
    enchantmentReplaceable: flag(value.enchantmentReplaceable),
    quest: flag(value.quest),
    unique: flag(value.unique),
    broken: flag(value.broken),
    repairable: flag(value.repairable),
    repairMaterials: normalizeMaterials(value.repairMaterials),
    dismantleBlocked: text(value.dismantleBlocked),
  };
}

function normalizeState(value: unknown): PanelState {
  if (!isRecord(value)) return emptyState;
  const rawSettings = isRecord(value.settings) ? value.settings : {};
  const rawHotkey = isRecord(rawSettings.hotkey) ? rawSettings.hotkey : {};
  const rawDismantleHotkey = isRecord(rawSettings.dismantleHotkey) ? rawSettings.dismantleHotkey : {};
  const rawForge = isRecord(value.forge) ? value.forge : {};
  const equipped = Array.isArray(value.equipped)
    ? value.equipped.map(normalizeEquipment).filter((item): item is EquipmentItem => item !== undefined)
    : [];
  const repairQueue = Array.isArray(value.repairQueue)
    ? value.repairQueue.map(normalizeEquipment).filter((item): item is EquipmentItem => item !== undefined)
    : [];
  return {
    version: text(value.version, emptyState.version),
    unified: flag(value.unified),
    dismantleQuote: isRecord(value.dismantleQuote) && typeof value.dismantleQuote.token === 'string' && typeof value.dismantleQuote.id === 'string' ? {
      token: value.dismantleQuote.token, id: value.dismantleQuote.id, name: text(value.dismantleQuote.name),
      equipped: flag(value.dismantleQuote.equipped), materials: normalizeMaterials(value.dismantleQuote.materials),
    } : undefined,
    equipped,
    repairQueue,
    capturingHotkey: flag(value.capturingHotkey),
    capturingDismantleHotkey: flag(value.capturingDismantleHotkey),
    dismantleResult: isRecord(value.dismantleResult) && typeof value.dismantleResult.id === 'string' && typeof value.dismantleResult.token === 'string' ? { id: value.dismantleResult.id, token: value.dismantleResult.token } : undefined,
    message: text(value.message) || undefined,
    refreshResult: normalizeRefreshResult(value.refreshResult),
    forge: {
      active: flag(rawForge.active),
      station: text(rawForge.station),
      gold: Math.max(0, finiteNumber(rawForge.gold, 0)),
      refreshCost: Math.max(0, finiteNumber(rawForge.refreshCost, 0)),
      refreshes: Math.max(0, finiteNumber(rawForge.refreshes, 0)),
      cards: normalizeCards(rawForge.cards),
    },
    settings: {
      dismantleHotkey: {
        key: text(rawDismantleHotkey.key, 'D'), shift: flag(rawDismantleHotkey.shift, true),
        ctrl: flag(rawDismantleHotkey.ctrl), alt: flag(rawDismantleHotkey.alt), enabled: flag(rawDismantleHotkey.enabled, true),
      },
      hotkey: {
        key: text(rawHotkey.key, emptyState.settings.hotkey.key),
        keyCode: finiteNumber(rawHotkey.keyCode, emptyState.settings.hotkey.keyCode),
        shift: flag(rawHotkey.shift),
        ctrl: flag(rawHotkey.ctrl),
        alt: flag(rawHotkey.alt),
      },
      uiFontScale: Math.max(80, Math.min(130, finiteNumber(rawSettings.uiFontScale, 100))),
      uiTransparency: Math.max(0, Math.min(60, finiteNumber(rawSettings.uiTransparency, 16))),
      lowDurabilityThreshold: finiteNumber(rawSettings.lowDurabilityThreshold, emptyState.settings.lowDurabilityThreshold),
      weaponDisplaySeconds: finiteNumber(rawSettings.weaponDisplaySeconds, emptyState.settings.weaponDisplaySeconds),
      enableLowDurabilityWarning: flag(rawSettings.enableLowDurabilityWarning, emptyState.settings.enableLowDurabilityWarning),
      enableWorkshopSounds: flag(rawSettings.enableWorkshopSounds, true),
      allowEnchantedItemsToBreak: flag(rawSettings.allowEnchantedItemsToBreak, emptyState.settings.allowEnchantedItemsToBreak),
    },
  };
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

export function App() {
  const arrows = useArrowBridge();
  const [settingsTab, setSettingsTab] = useState('general');
  const [state, setState] = useState<PanelState>(import.meta.env.DEV ? demoState : emptyState);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [tab, setTab] = useState<Tab>('workshop');
  const [selectedId, setSelectedId] = useState<string>();
  const [enhancingId, setEnhancingId] = useState<string>();
  const [revision, setRevision] = useState(0);
  const [draft, setDraft] = useState<Settings>(state.settings);
  const [panelVisible, setPanelVisible] = useState(import.meta.env.DEV);
  const [hud, setHud] = useState<HudMessage>();
  const escapeAction = useRef<() => void>(() => {});
  const directAction = useRef<(event: { sequence: string; id: string }) => boolean>(() => false);
  const directPending = useRef(false);
  const navigateAction = useRef<(direction: number) => boolean>(() => false);
  const selectionOrder = useRef<string[]>([]);
  const handledResult = useRef<string>();
  const focusSelection = useRef(false);
  const rows = useRef(new Map<string, HTMLButtonElement>());
  escapeAction.current = () => {
    if (state.capturingHotkey || state.capturingDismantleHotkey) send('cancelHotkeyCapture');
    else if (state.dismantleQuote) send('cancelDismantle');
    else if (enhancingId) setEnhancingId(undefined);
    else send('close');
  };

  useEffect(() => {
    const hudReceiver = createHudReceiver(setHud, (id) => send('hudHidden', { id }), {
      set: (callback, delay) => window.setTimeout(callback, delay),
      clear: (id) => window.clearTimeout(id),
    });
    window.DurabilityManager = {
      receiveState: (next) => {
        directPending.current = false;
        const normalized = normalizeState(next);
        setState((previous) => ({ ...normalized, refreshResult: normalized.refreshResult ?? previous.refreshResult }));
        setRevision((previous) => previous + 1);
        setDraft(normalized.settings);
      },
      setPanelVisible: (visible) => {
        setPanelVisible(visible);
        if (!visible) setEnhancingId(undefined);
      },
      showHud: hudReceiver.receive,
      escape: () => escapeAction.current(),
      openArrows: () => { setTab('arrows'); setEnhancingId(undefined); },
      navigateEquipment: (direction) => { navigateAction.current(direction); },
      directDismantle: (event) => { directAction.current(event); },
    };
    send('ready', { version: emptyState.version });
    return () => { hudReceiver.dispose(); delete window.DurabilityManager; };
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    let nextToken = 0;
    window.durabilityManagerAction = (raw) => {
      const q = JSON.parse(raw);

      directPending.current = false;
      setState((prev) => {
        if (q.type === 'saveGeneralSettings') return { ...prev, settings: { ...prev.settings, uiFontScale: q.uiFontScale, uiTransparency: q.uiTransparency, enableWorkshopSounds: q.enableWorkshopSounds }, message: '通用设置已保存。' };
        if (q.type === 'beginDismantleHotkeyCapture' || q.type === 'beginHotkeyCapture') return { ...prev, capturingHotkey: q.type === 'beginHotkeyCapture', capturingDismantleHotkey: q.type === 'beginDismantleHotkeyCapture' };
        if (q.type === 'cancelHotkeyCapture') return { ...prev, capturingHotkey: false, capturingDismantleHotkey: false };
        if (q.type === 'setDismantleHotkeyEnabled') return { ...prev, settings: { ...prev.settings, dismantleHotkey: { ...(prev.settings.dismantleHotkey ?? defaultDismantleHotkey), enabled: q.enabled } } };
        if (q.type === 'saveDismantleHotkey' || q.type === 'previewCapturePanel') {
          if (q.type === 'previewCapturePanel') {
            if (matchesShortcut({ key: q.key, shiftKey: q.shift, ctrlKey: q.ctrl, altKey: q.alt, repeat: false }, prev.settings.dismantleHotkey ?? defaultDismantleHotkey)) return { ...prev, message: '快捷键不能与直接分解相同。' };
            return { ...prev, capturingHotkey: false, settings: { ...prev.settings, hotkey: { ...prev.settings.hotkey, ...q } } };
          }
          if (matchesShortcut({ key: prev.settings.hotkey.key, shiftKey: prev.settings.hotkey.shift, ctrlKey: prev.settings.hotkey.ctrl, altKey: prev.settings.hotkey.alt, repeat: false }, { ...q, enabled: true })) return { ...prev, message: '快捷键不能与面板开关键相同。' };
          return { ...prev, capturingDismantleHotkey: false, settings: { ...prev.settings, dismantleHotkey: { key: q.key, shift: q.shift, ctrl: q.ctrl, alt: q.alt, enabled: q.enabled } }, message: '直接分解快捷键已保存。' };
        }
        if (q.type === 'directDismantle' || q.type === 'dismantle' && prev.dismantleQuote?.token === q.token) {
          const item = [...prev.equipped, ...prev.repairQueue].find((x) => x.id === (q.type === 'directDismantle' ? q.id : prev.dismantleQuote?.id));
          if (!prev.forge.active || !item || item.quest || item.unique || item.dismantleBlocked) return prev;
          const removeOne = (items: EquipmentItem[]) => items.flatMap((x) => x.id !== item.id ? [x] : x.quantity > 1 ? [{ ...x, quantity: x.quantity - 1 }] : []);
          return { ...prev, equipped: removeOne(prev.equipped), repairQueue: removeOne(prev.repairQueue), dismantleResult: { token: String(++nextToken), id: item.id }, dismantleQuote: undefined, message: `预览：已直接分解 1 件「${item.name}」，回收钢锭 ×2、皮革条 ×1。` };
        }
        if (q.type === 'cancelDismantle') return { ...prev, dismantleQuote: undefined };
        if (q.type === 'quoteDismantle') {
          const item = [...prev.equipped, ...prev.repairQueue].find((x) => x.id === q.id);
          if (!item || item.quest || item.unique) return { ...prev, message: '任务或唯一装备不可分解。' };
          return { ...prev, dismantleQuote: { token: String(++nextToken), id: item.id, name: item.name, equipped: item.equipped,
            materials: [{ name: '钢锭', required: 2, owned: 12 }, { name: '皮革条', required: 1, owned: 7 }] } };
        }
        return prev;
      });
    };
    return () => { delete window.durabilityManagerAction; };
  }, []);

  const visibleEquipment = useMemo(() => {
    const equippedIds = new Set(state.equipped.map((item) => item.id));
    return equippedFirst([...state.equipped, ...state.repairQueue.filter((item) => !equippedIds.has(item.id))]);
  }, [state.equipped, state.repairQueue]);
  const filteredEquipment = visibleEquipment.filter((item) => (filter === 'all' || item.category === filter || filter === 'worn' && item.equipped) && item.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const selected = useMemo(() => filteredEquipment.find((item) => item.id === selectedId) ?? filteredEquipment[0], [selectedId, filteredEquipment]);
  const hasRepairMaterials = Boolean(selected?.repairMaterials.every((material) => material.owned >= material.required));
  const canRepair = Boolean(selected?.repairable && state.forge.active && hasRepairMaterials);
  const selectedWearRate = optionalFiniteNumber(selected?.wearRate);
  const enhancing = visibleEquipment.find((item) => item.id === enhancingId);
  const dismantleHotkey = state.settings.dismantleHotkey ?? defaultDismantleHotkey;
  const equipmentAction = (type: string, data: Record<string, unknown> = {}) => {
    if (type === 'dismantle' || type === 'directDismantle') selectionOrder.current = filteredEquipment.map((item) => item.id);
    send(type, data);
  };
  const isEditing = () => !!document.activeElement?.closest('input, textarea, select, [contenteditable="true"], .dismantle-shortcut-settings');
  const chooseEquipment = (id: string) => {
    focusSelection.current = true;
    setSelectedId(id);
    send('cancelDismantle');
  };
  navigateAction.current = (direction) => {
    if (!panelVisible || (tab === 'settings' || tab === 'arrows') || enhancingId || state.capturingHotkey || state.capturingDismantleHotkey || directPending.current || isEditing()) return false;
    const id = adjacentEquipment(filteredEquipment.map((item) => item.id), selected?.id, direction);
    if (!id) return false;
    chooseEquipment(id);
    return true;
  };
  useEffect(() => {
    const result = state.dismantleResult;
    if (!result || handledResult.current === result.token) return;
    handledResult.current = result.token;
    focusSelection.current = true;
    setSelectedId(afterDismantle(selectionOrder.current, result.id, filteredEquipment.map((item) => item.id)));
  }, [state.dismantleResult]);
  useEffect(() => {
    if (!focusSelection.current || !selectedId) return;
    const row = rows.current.get(selectedId);
    if (row) { row.focus({ preventScroll: true }); row.scrollIntoView({ block: 'nearest' }); focusSelection.current = false; }
  }, [selectedId, state.dismantleResult, tab]);
  directAction.current = (event) => {
    const editing = isEditing() || !!state.capturingHotkey || !!state.capturingDismantleHotkey;
    if (!dismantleHotkey.enabled || !shortcutAllowed({ visible: panelVisible, page: tab, forge: state.forge.active, editing, busy: directPending.current,
      protectedItem: !!(selected?.quest || selected?.unique || selected?.dismantleBlocked), selectedId: selected?.id, eventId: event.id })) return false;
    directPending.current = true;
    equipmentAction('directDismantle', { id: event.id, sequence: event.sequence });
    return true;
  };
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (state.capturingHotkey || state.capturingDismantleHotkey) {
        event.preventDefault();
        if (event.key === 'Escape') send('cancelHotkeyCapture');
        else if (!event.repeat && !event.isComposing && /^(Key[A-Z]|F([1-9]|1[0-2])|Delete)$/.test(event.code)) {
          const key = event.code.startsWith('Key') ? event.code.slice(3) : event.code;
          send(state.capturingDismantleHotkey ? 'saveDismantleHotkey' : 'previewCapturePanel', { key, shift: event.shiftKey, ctrl: event.ctrlKey, alt: event.altKey, enabled: dismantleHotkey.enabled });
        }
        return;
      }
      if (!event.shiftKey && !event.ctrlKey && !event.altKey && !event.isComposing && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
        if (navigateAction.current(event.key === 'ArrowUp' ? -1 : 1)) event.preventDefault();
        return;
      }
      if (matchesShortcut(event, dismantleHotkey) && directAction.current({ id: selected?.id ?? '', sequence: String(event.timeStamp) })) event.preventDefault();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [dismantleHotkey, selected?.id, state.capturingHotkey, state.capturingDismantleHotkey]);

  useEffect(() => {
    if (!state.forge.active || !enhancing) setEnhancingId(undefined);
  }, [state.forge.active, enhancing]);

  useEffect(() => {
    if (tab !== 'settings' && (state.capturingHotkey || state.capturingDismantleHotkey)) send('cancelHotkeyCapture');
  }, [tab, state.capturingHotkey, state.capturingDismantleHotkey]);

  useEffect(() => {
    if (!selected) return;
    if (selectedId !== selected.id && !state.dismantleResult) setSelectedId(selected.id);
    if (state.forge.active) send('selectEquipment', { id: selected.id });
  }, [state.forge.active, selected?.id]);

  const hudPercentage = hud?.maximum && hud.current !== undefined ? Math.max(0, Math.min(100, hud.current / hud.maximum * 100)) : undefined;

  return <>{hud && <aside className={`durability-hud ${hud.kind}`} aria-live="polite"><span className="hud-rune">{hud.kind === 'warning' ? '!' : 'ᛏ'}</span><div className="hud-copy"><b>{hud.title}</b>{hudPercentage !== undefined && <><div className="hud-value"><strong>{formatDurability(hud.current)} / {formatDurability(hud.maximum)}</strong><span>{Math.round(hudPercentage)}%</span></div><div className="hud-track" role="progressbar" aria-label="当前耐久" aria-valuemax={hud.maximum} aria-valuemin={0} aria-valuenow={hud.current}><i style={{ width: `${hudPercentage}%` }} /></div></>}<span className="hud-detail">{hud.detail}</span></div></aside>}{panelVisible && <main className="forge-shell" style={{ '--workshop-font-scale': (draft.uiFontScale ?? 100) / 100, '--workshop-background-alpha': 1 - (draft.uiTransparency ?? 16) / 100 } as CSSProperties}>
    <WorkshopNavigation tab={tab} forge={state.forge.active} arrows={!!state.unified || import.meta.env.DEV} onChange={next => { setTab(next); setEnhancingId(undefined); send('cancelDismantle'); send('cancelHotkeyCapture'); }} /><div className="workshop-workspace">
    <header className="forge-header"><div><p className="workshop-eyebrow">{tab === 'arrows' ? 'MAGIC ARROWS' : tab === 'dismantle' ? 'SALVAGE WORKSHOP' : tab === 'settings' ? 'YOUR PREFERENCES' : 'YOUR EQUIPMENT'}</p><h1>{tab === 'arrows' ? '魔法箭工坊' : tab === 'dismantle' ? '分解与回收' : tab === 'settings' ? '工坊设置' : '每一次冒险，都值得悉心准备。'}</h1><p className="workshop-subtitle">{tab === 'settings' ? '按你的习惯，设置工坊操作与提示。' : tab === 'arrows' ? '整理箭矢，封存法术，为下一次冒险做好准备。' : tab === 'dismantle' ? '让闲置的装备，继续为下一次冒险效力。' : '查看装备状态，修复磨损，探索新的强化。'}</p></div><div className="workshop-header-actions"><span className={`forge-context ${state.forge.active ? 'active' : ''}`}>{state.forge.active ? `⚒ ${state.forge.station}` : '附近无锻造设施'}</span><button className="close" onClick={() => send('close')} aria-label="关闭面板" type="button">×</button></div></header>

    <ArrowWorkshop state={arrows.state} action={arrows.action} active={panelVisible && tab === 'arrows'} />
    <div className="equipment-pane" hidden={tab === 'arrows' || tab === 'settings'}>
    {enhancing && state.forge.active ? <EnhancementPage key={enhancing.id} item={enhancing} forge={state.forge} revision={revision} refreshResult={state.refreshResult} onBack={() => setEnhancingId(undefined)} onAction={send} /> : <section className="workshop-layout">
      <aside className="equipment-list"><div className="list-heading"><div><p>INVENTORY EQUIPMENT</p><h2>背包装备</h2></div><span>{visibleEquipment.length} 件</span></div>
        <div className="equipment-tools"><input aria-label="搜索装备" placeholder="搜索装备名称…" value={search} onChange={(e) => setSearch(e.target.value)} /><div>{[['all','全部'],['weapon','武器'],['armor','护甲'],['clothing','衣物'],['worn','已装备']].map(([id,label]) => <button key={id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div></div>
        <div className="list-scroll">{filteredEquipment.map((item) => <button className={`equipment-row ${selected?.id === item.id ? 'selected' : ''} ${item.broken ? 'broken' : ''}`} key={item.id} ref={(node) => { if (node) rows.current.set(item.id, node); else rows.current.delete(item.id); }} aria-pressed={selected?.id === item.id} onClick={() => chooseEquipment(item.id)} type="button"><span className="item-icon">{itemIcon(item)}</span><span className="row-main"><b>{item.name} {item.enhancementLevel > 0 && <em>+{item.enhancementLevel}</em>} {item.quantity > 1 && <em>×{item.quantity}</em>}</b><small>{item.broken ? '已损坏 · 等待修复' : item.slot} · 耐久 {formatDurability(item.current)}/{formatDurability(item.maximum)}</small><i><i style={{ width: `${percentage(item)}%` }} /></i></span><span className="row-status"><EquippedBadge equipped={item.equipped} />{item.enchanted && <span className="enchanted" title="已附魔">✦</span>}</span></button>)}{!filteredEquipment.length && <p className="empty">没有符合条件的装备。</p>}</div>
      </aside>

      {selected ? tab === 'dismantle' ? <DismantlePanel key={selected.id} item={selected} quote={state.dismantleQuote} active={state.forge.active} hotkey={dismantleHotkey} onAction={equipmentAction} /> : <section className="equipment-detail"><div className="detail-title"><div><p>{selected.slot.toUpperCase()}</p><h2>{selected.name} {selected.enhancementLevel > 0 && <span>+{selected.enhancementLevel}</span>}</h2></div><div className={`condition ${selected.broken ? 'broken' : percentage(selected) < state.settings.lowDurabilityThreshold ? 'warning' : ''}`}>{selected.broken ? '已破损' : `${Math.round(percentage(selected))}%`}</div></div>
        <div className="detail-tags"><EquippedBadge equipped={selected.equipped} /><span>{selected.category === 'weapon' ? '武器' : selected.category === 'armor' ? '护甲' : '服装'}</span>{selected.enchanted && <span>✦ 已附魔</span>}{selected.unique && <span>唯一物品</span>}{selected.quest && <span>任务物品</span>}</div>
        <div className="stat-grid"><div><small>耐久</small><b>{formatDurability(selected.current)} <span>/ {formatDurability(selected.maximum)}</span></b></div>{selected.category === 'weapon' && <div><small>攻击</small><b>{selected.damage ?? 0}</b></div>}{selected.category === 'armor' && <div><small>防御</small><b>{selected.armor ?? 0}</b></div>}<div><small>重量</small><b>{selected.weight.toFixed(1)}</b></div>{selected.category === 'weapon' && <div><small>攻速</small><b>{(selected.attackSpeed ?? 0).toFixed(2)}×</b></div>}{selected.chargeCapacity !== undefined && <div><small>附魔充能</small><b>{Math.round(selected.chargeCurrent ?? selected.chargeCapacity)} <span>/ {Math.round(selected.chargeCapacity)}</span></b>{(selected.chargeBonus ?? 0) > 0 && <i>容量强化 +{Math.round((selected.chargeBonus ?? 0) * 100)}%</i>}</div>}<div className="wear-stat"><small>耐久损耗</small><b>{selectedWearRate === undefined ? '—' : `-${selectedWearRate.toFixed(2)}`}<span>{selectedWearRate === undefined ? ' 尚未启用' : ` / ${selected.wearRateLabel}`}</span></b>{selectedWearRate !== undefined && <i>耐磨减免 {Math.round((selected.wearReduction ?? 0) * 100)}%</i>}{selected.movementWearRate !== undefined && <i>移动 −{selected.movementWearRate.toFixed(3)} / 1,000 距离单位</i>}</div></div>
        <div className="detail-bar"><i style={{ width: `${percentage(selected)}%` }} /></div>
        <section className="enchantment-info"><small>当前附魔</small><b>{selected.enchantment ?? '无'}</b>{!selected.enchantmentReplaceable && <span>此物品不可替换附魔</span>}</section>
        <section className="action-strip"><div className="repair-summary"><p>修复装备</p>{selected.current >= selected.maximum ? <small>耐久已满</small> : selected.repairMaterials.length ? <MaterialList materials={selected.repairMaterials} /> : <small>没有找到可用的锻造或强化配方</small>}</div><button disabled={!canRepair} onClick={() => send('repair', { id: selected.id })} type="button">{!state.forge.active ? '需锻造设施' : !selected.repairable ? '无法修复' : !hasRepairMaterials ? missingCost(selected.repairMaterials) ?? '材料不足' : '⚒ 修复'}{selected.repairable && <> · {costLabel(selected.repairMaterials)}</>}</button></section>
        {state.forge.active ? <section className="action-strip enhancement-entry"><div><p>卡片强化</p><small>已检测到附近的锻造设施，无需先操作工作台。进入强化页查看方案与材料代价。</small></div><button disabled={selected.broken} onClick={() => { send('playWorkshopClick'); setEnhancingId(selected.id); }} type="button">{selected.broken ? '请先修复装备' : '✦ 进入强化'}</button></section> : <p className="forge-hint">靠近锻造熔炉、冶炼熔炉、砂轮或护甲工作台后，重新打开面板即可直接修复或强化，无需先操作设施。</p>}
      </section> : <section className="detail-empty">选择一件装备以查看详情。</section>}
    </section>}
    </div>
    <section className="settings-page" hidden={tab !== 'settings'}>
      <div className="workshop-tabs settings-tabs" role="tablist" aria-label="设置分类"><button role="tab" aria-selected={settingsTab === 'general'} className={settingsTab === 'general' ? 'active' : ''} onClick={() => { setSettingsTab('general'); send('cancelHotkeyCapture'); }}>通用设置</button><button role="tab" aria-selected={settingsTab === 'equipment'} className={settingsTab === 'equipment' ? 'active' : ''} onClick={() => { setSettingsTab('equipment'); send('cancelHotkeyCapture'); }}>装备养护</button>{(state.unified || import.meta.env.DEV) && <button role="tab" aria-selected={settingsTab === 'arrows'} className={settingsTab === 'arrows' ? 'active' : ''} onClick={() => { setSettingsTab('arrows'); send('cancelHotkeyCapture'); }}>魔法箭</button>}</div>
      <div hidden={settingsTab !== 'general'}><GeneralSettings state={state} draft={draft} setDraft={setDraft} send={send} /></div>
      <div hidden={settingsTab !== 'equipment'}><EquipmentSettings state={state} draft={draft} setDraft={setDraft} send={send} /></div>
      <ArrowSettings state={arrows.state} action={arrows.action} active={panelVisible && tab === 'settings' && settingsTab === 'arrows'} />
    </section>
    <footer className="panel-footer"><span>{tab === 'arrows' || tab === 'settings' && settingsTab === 'arrows' ? `按 ${hotkeyLabel(state.settings)} 打开或关闭工坊。` : state.message || `按 ${hotkeyLabel(state.settings)} 可随时打开工坊。`}</span><small>{state.unified ? 'Equipment Workshop' : 'Durability Manager'} · v{state.version}</small></footer>
  </div></main>}</>;
}
