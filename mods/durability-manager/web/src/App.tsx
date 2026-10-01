import { createRecyclingCapture, recyclingKeyLabel } from './recycling-hotkey';
import { send } from './bridge';
import { GeneralSettings } from './GeneralSettings';
import { EquipmentSettings } from './EquipmentSettings';
import { WorkshopNavigation, type Tab } from './WorkshopNavigation';
import { SoulPoolPage } from './arrows/SoulPool';
import { useArrowBridge } from './arrows/useArrowBridge';
import { ArrowWorkshop } from './arrows/ArrowWorkshop';
import { ArrowSettings } from './arrows/ArrowSettings';
import { adjacentEquipment } from './equipment-selection';
import { matchesShortcut } from './shortcut';
import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react';
import { demoState } from './demo';
import type { EquipmentItem, MaterialRequirement, PanelState, Settings } from './types';
import { EnhancementPage, MaterialList } from './EnhancementPage';
import { normalizeCards } from './enhancement';
import { createHudReceiver, normalizeEquippedHud, type EquippedHudItem, type HudMessage } from './hud';
import { EquippedHud } from './EquippedHud';
import { CraftOrderHud } from './CraftOrderHud';
import { normalizeCraftOrders, type CraftOrderSnapshot } from './craft-hud';
import { normalizeSoulPoolHud, type SoulPoolHudSnapshot } from './soul-hud';
import { SoulPoolHud } from './SoulPoolHud';
import { PlayerHud } from './PlayerHud';
import { normalizePlayerHud, type PlayerHudSnapshot } from './player-hud';
import './hud.css';
import { HudFrame } from './HudFrame';
import { normalizeHudPosition } from './hud';
import { EquippedBadge } from './EquippedBadge';
import { formatDurability } from './format';
import { equippedFirst, maintenanceOrder } from './equipment';
import { costLabel, missingCost } from './cost';
import { normalizeRefreshResult } from './refresh';


declare global {
  interface Window {
    DurabilityManager?: {
      receiveState: (next: PanelState) => void;
      setPanelVisible: (visible: boolean) => void;
      showHud: (message: unknown) => void;
      updateEquippedHud: (items: unknown) => void;
      updatePlayerHud: (state: unknown) => void;
      updateCraftOrders: (orders: unknown) => void;
      updateSoulPool: (pool: unknown) => void;
      clearHud: () => void;
      updateHudPosition: (position: unknown) => void;
      reportReady: () => void;
      escape: () => void;
      openArrows: () => void;
      navigateEquipment: (direction: number) => void;
    };
    durabilityManagerAction?: (data: string) => void;
  }
}

const emptyState: PanelState = {
  version: '2.3.33',
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
    unified: flag(value.unified),
    pageKeyboard: flag(value.pageKeyboard),
    equipped,
    repairQueue,
    capturingHotkey: flag(value.capturingHotkey),
    capturingRecyclingHotkey: flag(value.capturingRecyclingHotkey),
    savingRecyclingHotkey: flag(value.savingRecyclingHotkey),
    message: text(value.message) || undefined,
    refreshResult: normalizeRefreshResult(value.refreshResult),
    forge: {
      active: flag(rawForge.active),
      enhancementAvailable: flag(rawForge.enhancementAvailable, flag(rawForge.active)),
      station: text(rawForge.station),
      gold: Math.max(0, finiteNumber(rawForge.gold, 0)),
      refreshCost: Math.max(0, finiteNumber(rawForge.refreshCost, 0)),
      refreshes: Math.max(0, finiteNumber(rawForge.refreshes, 0)),
      cards: normalizeCards(rawForge.cards),
    },
    settings: {
      recyclingHotkey: isRecord(rawSettings.recyclingHotkey) ? {
        enabled: flag(rawSettings.recyclingHotkey.enabled, true), holdToRecycleStack: flag(rawSettings.recyclingHotkey.holdToRecycleStack, true), legacyDetected: flag(rawSettings.recyclingHotkey.legacyDetected),
        available: flag(rawSettings.recyclingHotkey.available), label: text(rawSettings.recyclingHotkey.label),
        keyCode: optionalFiniteNumber(rawSettings.recyclingHotkey.keyCode), safetyCode: optionalFiniteNumber(rawSettings.recyclingHotkey.safetyCode),
      } : { available: false },
      hotkey: {
        key: text(rawHotkey.key, emptyState.settings.hotkey.key),
        keyCode: finiteNumber(rawHotkey.keyCode, emptyState.settings.hotkey.keyCode),
        shift: flag(rawHotkey.shift),
        ctrl: flag(rawHotkey.ctrl),
        alt: flag(rawHotkey.alt),
      },
      uiFontScale: Math.max(80, Math.min(130, finiteNumber(rawSettings.uiFontScale, 100))),
      uiTransparency: Math.max(0, Math.min(60, finiteNumber(rawSettings.uiTransparency, 16))),
      ...normalizeHudPosition(rawSettings),
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
  const [hudPosition, setHudPosition] = useState(() => normalizeHudPosition({}));
  const [equippedHud, setEquippedHud] = useState<EquippedHudItem[]>([]);
  const [playerHud, setPlayerHud] = useState<PlayerHudSnapshot>();
  const [craftOrders, setCraftOrders] = useState<CraftOrderSnapshot>();
  const [soulPool, setSoulPool] = useState<SoulPoolHudSnapshot>();
  useEffect(() => {
    if (!import.meta.env.DEV || !new URLSearchParams(window.location.search).has('hud-preview')) return;
    setPanelVisible(false);
    setPlayerHud(normalizePlayerHud({ level: 21, experience: 321, experienceNext: 600,
      fire: 0, frost: 50, shock: 0, magic: 25, poison: 0, disease: 0, armor: 1875, speed: 100,
      gold: 44735, weight: 851, carryWeight: 800, gameMinutes: 953 }));
    setEquippedHud([
      { id: 'preview:right', kind: 'warning', title: '寒汐·处女', detail: '右手', current: 27, maximum: 100 },
      { id: 'preview:left', kind: 'weapon', title: '月光之刃', detail: '左手', current: 86, maximum: 100 },
    ]);
    setCraftOrders(normalizeCraftOrders({ paused: false, entries: [
      { spell: 1, name: '奥术箭·火球术', family: 'fire', total: 12, remaining: 12, label: '12' },
      { spell: 2, name: '奥术箭·冰锥术', family: 'ice', total: 4500, remaining: 1500, label: '1.5K' },
    ] }));
    setSoulPool(normalizeSoulPoolHud({ enabled: true, points: 12, capacity: 20, tier: 1 }));
  }, []);
  const escapeAction = useRef<() => void>(() => {});
  const navigateAction = useRef<(direction: number) => boolean>(() => false);
  const focusSelection = useRef(false);
  const rows = useRef(new Map<string, HTMLButtonElement>());
  escapeAction.current = () => {
    if (state.capturingHotkey || state.capturingRecyclingHotkey) send('cancelHotkeyCapture');
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
        const normalized = normalizeState(next);
        setState((previous) => ({ ...normalized, refreshResult: normalized.refreshResult ?? previous.refreshResult }));
        setRevision((previous) => previous + 1);
        setDraft(normalized.settings);
        setHudPosition(normalizeHudPosition(normalized.settings));
      },
      setPanelVisible: (visible) => {
        setPanelVisible(visible);
        if (!visible) setEnhancingId(undefined);
      },
      showHud: hudReceiver.receive,
      updateHudPosition: position => setHudPosition(normalizeHudPosition(position)),
      updateEquippedHud: (items) => { const next = normalizeEquippedHud(items); if (next) setEquippedHud(next); },
      updatePlayerHud: value => { const next = normalizePlayerHud(value); if (next) setPlayerHud(next); },
      updateCraftOrders: value => { const next = normalizeCraftOrders(value); if (next) setCraftOrders(next); },
      updateSoulPool: value => { const next = normalizeSoulPoolHud(value); if (next) setSoulPool(next); },
      clearHud: () => { hudReceiver.clear(); setEquippedHud([]); setPlayerHud(undefined); setCraftOrders(undefined); },
      reportReady: () => send('ready', { version: emptyState.version }),
      escape: () => escapeAction.current(),
      openArrows: () => { setTab('arrows'); setEnhancingId(undefined); },
      navigateEquipment: (direction) => { navigateAction.current(direction); },
    };
    send('ready', { version: emptyState.version });
    return () => { hudReceiver.dispose(); delete window.DurabilityManager; };
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    window.durabilityManagerAction = (raw) => {
      const q = JSON.parse(raw);
      if (q.type === 'saveSettings') setHudPosition(normalizeHudPosition(q));
      setState((prev) => {
        if (q.type === 'saveSettings') {
          const position = normalizeHudPosition(q);
          return { ...prev, settings: { ...prev.settings, ...position, lowDurabilityThreshold: q.lowDurabilityThreshold, weaponDisplaySeconds: q.weaponDisplaySeconds, enableLowDurabilityWarning: q.enableLowDurabilityWarning }, message: '装备养护设置已保存。' };
        }
        if (q.type === 'saveGeneralSettings') return { ...prev, settings: { ...prev.settings, uiFontScale: q.uiFontScale, uiTransparency: q.uiTransparency, enableWorkshopSounds: q.enableWorkshopSounds }, message: '通用设置已保存。' };
        if (q.type === 'beginHotkeyCapture') return { ...prev, capturingHotkey: true, capturingRecyclingHotkey: false };
        if (q.type === 'beginRecyclingHotkeyCapture') return { ...prev, capturingHotkey: false, capturingRecyclingHotkey: true };
        if (q.type === 'setRecyclingEnabled' || q.type === 'setRecyclingStackEnabled') return { ...prev, settings: { ...prev.settings, recyclingHotkey: { ...prev.settings.recyclingHotkey, available: true, [q.type === 'setRecyclingEnabled' ? 'enabled' : 'holdToRecycleStack']: q.enabled } } };
        if (q.type === 'saveRecyclingHotkey') return { ...prev, capturingRecyclingHotkey: false, settings: { ...prev.settings, recyclingHotkey: { ...prev.settings.recyclingHotkey, available: true, keyCode: q.keyCode, safetyCode: q.safetyCode, label: q.keyCode === q.safetyCode ? recyclingKeyLabel(q.keyCode) : `${recyclingKeyLabel(q.safetyCode)} + ${recyclingKeyLabel(q.keyCode)}` } }, message: '预览：回收快捷键已更新。' };
        if (q.type === 'cancelHotkeyCapture') return { ...prev, capturingHotkey: false, capturingRecyclingHotkey: false };
        if (q.type === 'previewCapturePanel') return { ...prev, capturingHotkey: false, settings: { ...prev.settings, hotkey: { ...prev.settings.hotkey, ...q } } };
        if (q.type === 'selectEquipment') return { ...prev, forge: { ...prev.forge, cards: demoState.forge.cards.map(card => ({ ...card, equipmentId: q.id })) } };
        return prev;
      });
    };
    return () => { delete window.durabilityManagerAction; };
  }, []);

  const visibleEquipment = useMemo(() => {
    const equippedIds = new Set(state.equipped.map((item) => item.id));
    return equippedFirst([...state.equipped, ...state.repairQueue.filter((item) => !equippedIds.has(item.id))]);
  }, [state.equipped, state.repairQueue]);
  const orderedEquipment = useMemo(() => tab === 'workshop' ? maintenanceOrder(visibleEquipment) : visibleEquipment, [tab, visibleEquipment]);
  const filteredEquipment = orderedEquipment.filter((item) => (filter === 'all' || item.category === filter || filter === 'worn' && item.equipped) && item.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const selected = useMemo(() => filteredEquipment.find((item) => item.id === selectedId) ?? filteredEquipment[0], [selectedId, filteredEquipment]);
  const hasRepairMaterials = Boolean(selected?.repairMaterials.every((material) => material.owned >= material.required));
  const canRepair = Boolean(selected?.repairable && state.forge.active && hasRepairMaterials);
  const selectedWearRate = optionalFiniteNumber(selected?.wearRate);
  const canEnhance = state.forge.enhancementAvailable ?? state.forge.active;
  const enhancing = visibleEquipment.find((item) => item.id === enhancingId);
  const isEditing = () => !!document.activeElement?.closest('input, textarea, select, [contenteditable="true"]');
  const chooseEquipment = (id: string) => {
    focusSelection.current = true;
    setSelectedId(id);
  };
  navigateAction.current = (direction) => {
    if (!panelVisible || tab !== 'workshop' || enhancingId || state.capturingHotkey || isEditing()) return false;
    const id = adjacentEquipment(filteredEquipment.map((item) => item.id), selected?.id, direction);
    if (!id) return false;
    chooseEquipment(id);
    return true;
  };
  useEffect(() => {
    if (!focusSelection.current || !selectedId) return;
    const row = rows.current.get(selectedId);
    if (row) { row.focus({ preventScroll: true }); row.scrollIntoView({ block: 'nearest' }); focusSelection.current = false; }
  }, [selectedId, tab]);
  useEffect(() => {
    if (!import.meta.env.DEV && !state.pageKeyboard) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (state.capturingRecyclingHotkey) return;
      if (state.capturingHotkey) {
        event.preventDefault();
        if (event.key === 'Escape') send('cancelHotkeyCapture');
        else if (!event.repeat && !event.isComposing && /^(Key[A-Z]|F([1-9]|1[0-2])|Delete)$/.test(event.code)) {
          const key = event.code.startsWith('Key') ? event.code.slice(3) : event.code;
          send(state.pageKeyboard ? 'captureHotkeyFromPage' : 'previewCapturePanel', { key, shift: event.shiftKey, ctrl: event.ctrlKey, alt: event.altKey });
        }
        return;
      }
      if (state.pageKeyboard && !event.repeat && (event.key === 'Escape' || matchesShortcut(event, { ...state.settings.hotkey, enabled: true }))) { event.preventDefault(); escapeAction.current(); return; }
      if (!event.shiftKey && !event.ctrlKey && !event.altKey && !event.isComposing && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
        if (navigateAction.current(event.key === 'ArrowUp' ? -1 : 1)) event.preventDefault();
        return;
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [state.capturingRecyclingHotkey, state.capturingHotkey, state.pageKeyboard, state.settings.hotkey, tab]);

  useEffect(() => {
    if (!state.capturingRecyclingHotkey || (!import.meta.env.DEV && !state.pageKeyboard)) return;
    const capture = createRecyclingCapture();
    let submitted = false;
    const record = (event: KeyboardEvent) => {
      event.preventDefault();
      if (submitted || event.repeat || event.isComposing) return;
      if (event.code === 'Escape') { submitted = true; send('cancelHotkeyCapture'); return; }
      const result = capture(event.code, event.type === 'keydown');
      if (result === 'invalid') { setState(previous => ({ ...previous, message: '不支持该组合，请使用字母、F1–F12、Delete、Space 或左右修饰键，最多搭配一个修饰键。' })); return; }
      if (result) { submitted = true; send('saveRecyclingHotkey', result); }
    };
    const cancelOnBlur = () => send('cancelHotkeyCapture');
    window.addEventListener('keydown', record); window.addEventListener('keyup', record); window.addEventListener('blur', cancelOnBlur);
    return () => { window.removeEventListener('keydown', record); window.removeEventListener('keyup', record); window.removeEventListener('blur', cancelOnBlur); };
  }, [state.capturingRecyclingHotkey, state.pageKeyboard]);

  useEffect(() => {
    if (!enhancing) setEnhancingId(undefined);
  }, [enhancing]);

  useEffect(() => {
    if (tab !== 'settings' && (state.capturingHotkey || state.capturingRecyclingHotkey)) send('cancelHotkeyCapture');
  }, [tab, state.capturingHotkey, state.capturingRecyclingHotkey]);

  useEffect(() => {
    if (!selected) return;
    if (selectedId !== selected.id) setSelectedId(selected.id);
    send('selectEquipment', { id: selected.id });
  }, [canEnhance, selected?.id]);

  const hudPercentage = hud?.maximum && hud.current !== undefined ? Math.max(0, Math.min(100, hud.current / hud.maximum * 100)) : undefined;

  return <>{!panelVisible && <HudFrame position={hudPosition}>{hud && <aside className={`durability-hud ${hud.kind}`} aria-live="polite">
    <svg className="hud-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {hud.kind === 'warning'
        ? <><path d="m12 3 10 18H2L12 3Z" /><path d="M12 9v5m0 3v.1" /></>
        : <><path d="m14 3 7-1-1 7-10 10-5-5L14 3Z" /><path d="m7 12 5 5M3 13l8 8m-4-4-4 4m-1-1 2 2" /></>}
    </svg>
    <div className="hud-copy">
      <b className="hud-title">{hud.title}</b>
      {hudPercentage !== undefined && <>
        <div className="hud-value">
          <strong>{formatDurability(hud.current)} <small>/ {formatDurability(hud.maximum)}</small></strong>
          <span>{Math.round(hudPercentage)}%</span>
        </div>
        <div className="hud-track" role="progressbar" aria-label="当前耐久" aria-valuemax={hud.maximum} aria-valuemin={0} aria-valuenow={hud.current}>
          <i style={{ width: `${hudPercentage}%` }} />
        </div>
      </>}
      {hud.detail && <span className="hud-detail">{hud.detail}</span>}
    </div>
  </aside>}{(playerHud || !!craftOrders?.entries.length || equippedHud.length > 0 || soulPool?.enabled) && <div className="character-hud-panel">{playerHud && <PlayerHud state={playerHud} />}<SoulPoolHud pool={soulPool} /><CraftOrderHud orders={craftOrders} /><EquippedHud items={equippedHud} hasNotification={!!hud} /></div>}</HudFrame>}{panelVisible && <main className={`forge-shell${tab === 'arrows' || tab === 'soul' ? ' arrows-active' : ''}`} style={{ '--workshop-font-scale': (draft.uiFontScale ?? 100) / 100, '--workshop-background-alpha': 1 - (draft.uiTransparency ?? 16) / 100 } as CSSProperties}>
    <WorkshopNavigation tab={tab} forge={state.forge.active} arrows={!!state.unified || import.meta.env.DEV} onChange={next => { setTab(next); setEnhancingId(undefined); send('cancelHotkeyCapture'); }} /><div className="workshop-workspace">
    <header className="forge-header"><div><p className="workshop-eyebrow">{tab === 'soul' ? 'SOUL POOL' : tab === 'arrows' ? 'MAGIC ARROWS' : tab === 'settings' ? 'YOUR PREFERENCES' : 'YOUR EQUIPMENT'}</p><h1>{tab === 'soul' ? '灵魂池' : tab === 'arrows' ? '魔法箭工坊' : tab === 'settings' ? '工坊设置' : '每一次冒险，都值得悉心准备。'}</h1><p className="workshop-subtitle">{tab === 'settings' ? '按你的习惯，设置工坊操作与提示。' : tab === 'soul' ? '吸魂自动入池，兑换成灵魂石后照常交给附魔台。' : tab === 'arrows' ? '整理箭矢，封存法术，为下一次冒险做好准备。' : '查看装备状态，修复磨损，探索新的强化。'}</p></div><div className="workshop-header-actions"><span className={`forge-context ${(enhancing ? canEnhance : state.forge.active) ? 'active' : ''}`}>{enhancing ? (canEnhance ? '附魔台／锻造设备可用' : '需靠近附魔台或锻造设备') : state.forge.active ? `⚒ ${state.forge.station}` : '附近无锻造设施'}</span><button className="close" onClick={() => send('close')} aria-label="关闭面板" type="button">×</button></div></header>

    <ArrowWorkshop state={arrows.state} action={arrows.action} active={panelVisible && tab === 'arrows'} />
    <SoulPoolPage state={arrows.state} action={arrows.action} active={panelVisible && tab === 'soul'} />
    <div className="equipment-pane" hidden={tab === 'arrows' || tab === 'soul' || tab === 'settings'}>
    {enhancing ? <EnhancementPage key={enhancing.id} item={enhancing} forge={state.forge} revision={revision} refreshResult={state.refreshResult} backLabel="返回装备详情" onBack={() => setEnhancingId(undefined)} onAction={send} /> : <section className="workshop-layout">
      <aside className="equipment-list"><div className="list-heading"><div><p>INVENTORY EQUIPMENT</p><h2>背包装备</h2></div><span>{visibleEquipment.length} 件</span></div>
        <div className="equipment-tools"><input aria-label="搜索装备" placeholder="搜索装备名称…" value={search} onChange={(e) => setSearch(e.target.value)} /><div>{[['all','全部'],['weapon','武器'],['armor','护甲'],['clothing','衣物'],['worn','已装备']].map(([id,label]) => <button key={id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}</div></div>
        <div className="list-scroll">{filteredEquipment.map((item) => <button className={`equipment-row ${selected?.id === item.id ? 'selected' : ''} ${item.broken ? 'broken' : ''}`} key={item.id} ref={(node) => { if (node) rows.current.set(item.id, node); else rows.current.delete(item.id); }} aria-pressed={selected?.id === item.id} onClick={() => chooseEquipment(item.id)} type="button"><span className="item-icon">{itemIcon(item)}</span><span className="row-main"><b>{item.name} {item.enhancementLevel > 0 && <em>+{item.enhancementLevel}</em>} {item.quantity > 1 && <em>×{item.quantity}</em>}</b><small>{item.broken ? '已损坏 · 等待修复' : item.slot} · 耐久 {formatDurability(item.current)}/{formatDurability(item.maximum)}</small><i><i style={{ width: `${percentage(item)}%` }} /></i></span><span className="row-status"><EquippedBadge equipped={item.equipped} />{item.enchanted && <span className="enchanted" title="已附魔">✦</span>}</span></button>)}{!filteredEquipment.length && <p className="empty">没有符合条件的装备。</p>}</div>
      </aside>

      {selected ? <section className="equipment-detail"><div className="detail-title"><div><p>{selected.slot.toUpperCase()}</p><h2>{selected.name} {selected.enhancementLevel > 0 && <span>+{selected.enhancementLevel}</span>}</h2></div><div className={`condition ${selected.broken ? 'broken' : percentage(selected) < state.settings.lowDurabilityThreshold ? 'warning' : ''}`}>{selected.broken ? '已破损' : `${Math.round(percentage(selected))}%`}</div></div>
        <div className="detail-tags"><EquippedBadge equipped={selected.equipped} /><span>{selected.category === 'weapon' ? '武器' : selected.category === 'armor' ? '护甲' : '服装'}</span>{selected.enchanted && <span>✦ 已附魔</span>}{selected.unique && <span>唯一物品</span>}{selected.quest && <span>任务物品</span>}</div>
        <div className="stat-grid"><div><small>耐久</small><b>{formatDurability(selected.current)} <span>/ {formatDurability(selected.maximum)}</span></b></div>{selected.category === 'weapon' && <div><small>攻击</small><b>{selected.damage ?? 0}</b></div>}{selected.category === 'armor' && <div><small>防御</small><b>{selected.armor ?? 0}</b></div>}<div><small>重量</small><b>{selected.weight.toFixed(1)}</b></div>{selected.category === 'weapon' && <div><small>攻速</small><b>{(selected.attackSpeed ?? 0).toFixed(2)}×</b></div>}{selected.chargeCapacity !== undefined && <div><small>附魔充能</small><b>{Math.round(selected.chargeCurrent ?? selected.chargeCapacity)} <span>/ {Math.round(selected.chargeCapacity)}</span></b>{(selected.chargeBonus ?? 0) > 0 && <i>容量强化 +{Math.round((selected.chargeBonus ?? 0) * 100)}%</i>}</div>}<div className="wear-stat"><small>耐久损耗</small><b>{selectedWearRate === undefined ? '—' : `-${selectedWearRate.toFixed(2)}`}<span>{selectedWearRate === undefined ? ' 尚未启用' : ` / ${selected.wearRateLabel}`}</span></b>{selectedWearRate !== undefined && <i>耐磨减免 {Math.round((selected.wearReduction ?? 0) * 100)}%</i>}{selected.movementWearRate !== undefined && <i>移动 −{selected.movementWearRate.toFixed(3)} / 1,000 距离单位</i>}</div></div>
        <div className="detail-bar"><i style={{ width: `${percentage(selected)}%` }} /></div>
        <section className="enchantment-info"><small>当前附魔</small><b>{selected.enchantment ?? '无'}</b>{!selected.enchantmentReplaceable && <span>此物品不可替换附魔</span>}</section>
        <section className="action-cards">
          <article className={"action-card repair" + (canRepair ? "" : " blocked")}>
            <header><span className="action-card-icon">⚒</span><div><p>修复</p><small>{selected.current >= selected.maximum ? '耐久已满，无需修复' : !state.forge.active ? '需靠近锻造设施' : '恢复耐久，消耗材料'}</small></div></header>
            <div className="action-card-body">{selected.current >= selected.maximum ? <small>耐久已满</small> : selected.repairMaterials.length ? <MaterialList materials={selected.repairMaterials} /> : <small>没有找到可用的锻造或强化配方</small>}</div>
            <button disabled={!canRepair} onClick={() => send('repair', { id: selected.id })} type="button">{!state.forge.active ? '需锻造设施' : !selected.repairable ? '无法修复' : !hasRepairMaterials ? missingCost(selected.repairMaterials) ?? '材料不足' : '⚒ 修复'}{selected.repairable && <> · {costLabel(selected.repairMaterials)}</>}</button>
          </article>
          <article className={"action-card enhance" + (selected.broken ? " blocked" : "")}>
            <header><span className="action-card-icon">✦</span><div><p>强化</p><small>{selected.broken ? '装备已损坏，请先修复' : '查看并挑选强化方案'}</small></div></header>
            <div className="action-card-body"><small>可随时查看方案；强化和刷新需要靠近附魔台或锻造设备。</small></div>
            <button disabled={selected.broken} onClick={() => { send('playWorkshopClick'); setEnhancingId(selected.id); }} type="button">{selected.broken ? '请先修复装备' : '✦ 进入强化'}</button>
          </article>
        </section>
      </section> : <section className="detail-empty">选择一件装备以查看详情。</section>}
    </section>}
    </div>
    <section className="settings-page" hidden={tab !== 'settings'}>
      <div className="workshop-tabs settings-tabs" role="tablist" aria-label="设置分类"><button role="tab" aria-selected={settingsTab === 'general'} className={settingsTab === 'general' ? 'active' : ''} onClick={() => { setSettingsTab('general'); send('cancelHotkeyCapture'); }}>通用设置</button><button role="tab" aria-selected={settingsTab === 'equipment'} className={settingsTab === 'equipment' ? 'active' : ''} onClick={() => { setSettingsTab('equipment'); send('cancelHotkeyCapture'); }}>装备养护</button>{(state.unified || import.meta.env.DEV) && <button role="tab" aria-selected={settingsTab === 'arrows'} className={settingsTab === 'arrows' ? 'active' : ''} onClick={() => { setSettingsTab('arrows'); send('cancelHotkeyCapture'); }}>魔法箭</button>}</div>
      <div hidden={settingsTab !== 'general'}><GeneralSettings state={state} draft={draft} setDraft={setDraft} send={send} /></div>
      <div hidden={settingsTab !== 'equipment'}><EquipmentSettings state={state} draft={draft} setDraft={setDraft} send={send} /></div>
      <ArrowSettings state={arrows.state} action={arrows.action} active={panelVisible && tab === 'settings' && settingsTab === 'arrows'} />
    </section>
    <footer className="panel-footer"><span>{tab === 'arrows' || tab === 'soul' || tab === 'settings' && settingsTab === 'arrows' ? `按 ${hotkeyLabel(state.settings)} 打开或关闭工坊。` : state.message || `按 ${hotkeyLabel(state.settings)} 可随时打开工坊。`}</span><small>{state.unified ? 'Equipment Workshop' : 'Durability Manager'} · v{state.version}</small></footer>
  </div></main>}</>;
}
