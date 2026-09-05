import { useEffect, useMemo, useState } from 'react';
import { demoState } from './demo';
import type { EquipmentItem, MaterialRequirement, PanelState, Settings } from './types';
import { EnhancementPage, MaterialList } from './EnhancementPage';
import { normalizeCards } from './enhancement';
import { createHudReceiver, type HudMessage } from './hud';

type Tab = 'workshop' | 'settings';

declare global {
  interface Window {
    DurabilityManager?: {
      receiveState: (next: PanelState) => void;
      setPanelVisible: (visible: boolean) => void;
      showHud: (message: unknown) => void;
    };
    durabilityManagerAction?: (data: string) => void;
  }
}

const emptyState: PanelState = {
  version: '0.1.35',
  equipped: [], repairQueue: [], capturingHotkey: false,
  forge: { active: false, station: '', gold: 0, refreshCost: 0, refreshes: 0, cards: [] },
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
      gold: Math.max(0, finiteNumber(rawForge.gold, 0)),
      refreshCost: Math.max(0, finiteNumber(rawForge.refreshCost, 0)),
      refreshes: Math.max(0, finiteNumber(rawForge.refreshes, 0)),
      cards: normalizeCards(rawForge.cards),
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

export function App() {
  const [state, setState] = useState<PanelState>(import.meta.env.DEV ? demoState : emptyState);
  const [tab, setTab] = useState<Tab>('workshop');
  const [selectedId, setSelectedId] = useState<string>();
  const [enhancingId, setEnhancingId] = useState<string>();
  const [revision, setRevision] = useState(0);
  const [draft, setDraft] = useState<Settings>(state.settings);
  const [panelVisible, setPanelVisible] = useState(import.meta.env.DEV);
  const [hud, setHud] = useState<HudMessage>();

  useEffect(() => {
    const hudReceiver = createHudReceiver(setHud, (id) => send('hudHidden', { id }), {
      set: (callback, delay) => window.setTimeout(callback, delay),
      clear: (id) => window.clearTimeout(id),
    });
    window.DurabilityManager = {
      receiveState: (next) => {
        const normalized = normalizeState(next);
        setState(normalized);
        setRevision((previous) => previous + 1);
        setDraft(normalized.settings);
      },
      setPanelVisible: (visible) => {
        setPanelVisible(visible);
        if (!visible) setEnhancingId(undefined);
      },
      showHud: hudReceiver.receive,
    };
    send('ready', { version: emptyState.version });
    return () => { hudReceiver.dispose(); delete window.DurabilityManager; };
  }, []);

  const visibleEquipment = useMemo(() => {
    const equippedIds = new Set(state.equipped.map((item) => item.id));
    return [...state.equipped, ...state.repairQueue.filter((item) => !equippedIds.has(item.id))];
  }, [state.equipped, state.repairQueue]);
  const selected = useMemo(() => visibleEquipment.find((item) => item.id === selectedId) ?? visibleEquipment[0], [selectedId, visibleEquipment]);
  const hasRepairMaterials = Boolean(selected?.repairMaterials.every((material) => material.owned >= material.required));
  const canRepair = Boolean(selected?.repairable && state.forge.active && hasRepairMaterials);
  const selectedWearRate = optionalFiniteNumber(selected?.wearRate);
  const enhancing = visibleEquipment.find((item) => item.id === enhancingId);

  useEffect(() => {
    if (!state.forge.active || !enhancing) setEnhancingId(undefined);
  }, [state.forge.active, enhancing]);

  useEffect(() => {
    if (!selected) return;
    if (selectedId !== selected.id) setSelectedId(selected.id);
    if (state.forge.active) send('selectEquipment', { id: selected.id });
  }, [state.forge.active, selected?.id]);

  const hudPercentage = hud?.maximum && hud.current !== undefined ? Math.max(0, Math.min(100, hud.current / hud.maximum * 100)) : undefined;

  return <>{hud && <aside className={`durability-hud ${hud.kind}`} aria-live="polite"><span className="hud-rune">{hud.kind === 'warning' ? '!' : 'ᛏ'}</span><div className="hud-copy"><b>{hud.title}</b>{hudPercentage !== undefined && <><div className="hud-value"><strong>{hud.current} / {hud.maximum}</strong><span>{Math.round(hudPercentage)}%</span></div><div className="hud-track" role="progressbar" aria-label="当前耐久" aria-valuemax={hud.maximum} aria-valuemin={0} aria-valuenow={hud.current}><i style={{ width: `${hudPercentage}%` }} /></div></>}<span className="hud-detail">{hud.detail}</span></div></aside>}{panelVisible && <main className="forge-shell">
    <header className="forge-header">
      <div className="brand"><span className="brand-rune">ᛏ</span><div><p>{state.forge.active ? `${state.forge.station} · EQUIPMENT WORKSHOP` : 'SKYRIM FORGE LEDGER'}</p><h1>{state.forge.active ? '装备工坊' : '装备耐久'}</h1></div></div>
      <nav className="tabs" aria-label="装备耐久分页"><button className={tab === 'workshop' ? 'active' : ''} onClick={() => { setTab('workshop'); setEnhancingId(undefined); }} type="button">⌁ 装备</button><button className={tab === 'settings' ? 'active' : ''} onClick={() => { setTab('settings'); setEnhancingId(undefined); }} type="button">⚙ 配置</button></nav>
      <span className={`forge-context ${state.forge.active ? 'active' : ''}`}>{state.forge.active ? `⚒ 附近：${state.forge.station}` : '附近无可用锻造设施'}</span>
      <button className="close" onClick={() => send('close')} title="关闭 (Esc)" type="button">×</button>
    </header>

    {tab === 'workshop' ? enhancing && state.forge.active ? <EnhancementPage key={enhancing.id} item={enhancing} forge={state.forge} revision={revision} onBack={() => setEnhancingId(undefined)} onAction={send} /> : <section className="workshop-layout">
      <aside className="equipment-list"><div className="list-heading"><div><p>INVENTORY EQUIPMENT</p><h2>背包装备</h2></div><span>{visibleEquipment.length} 件</span></div>
        <div className="list-scroll">{visibleEquipment.map((item) => <button className={`equipment-row ${selected?.id === item.id ? 'selected' : ''} ${item.broken ? 'broken' : ''}`} key={item.id} onClick={() => setSelectedId(item.id)} type="button"><span className="item-icon">{itemIcon(item)}</span><span className="row-main"><b>{item.name} {item.enhancementLevel > 0 && <em>+{item.enhancementLevel}</em>} {item.quantity > 1 && <em>×{item.quantity}</em>}</b><small>{item.broken ? '已损坏 · 等待修复' : `${item.equipped ? '已装备 · ' : ''}${item.slot}`} · 耐久 {item.current}/{item.maximum}</small><i><i style={{ width: `${percentage(item)}%` }} /></i></span>{item.enchanted && <span className="enchanted">✦</span>}</button>)}{!visibleEquipment.length && <p className="empty">背包中没有可用的武器或装备。</p>}</div>
      </aside>

      {selected ? <section className="equipment-detail"><div className="detail-title"><div><p>{selected.slot.toUpperCase()}</p><h2>{selected.name} {selected.enhancementLevel > 0 && <span>+{selected.enhancementLevel}</span>}</h2></div><div className={`condition ${selected.broken ? 'broken' : percentage(selected) < state.settings.lowDurabilityThreshold ? 'warning' : ''}`}>{selected.broken ? '已破损' : `${Math.round(percentage(selected))}%`}</div></div>
        <div className="detail-tags"><span>{selected.category === 'weapon' ? '武器' : selected.category === 'armor' ? '护甲' : '服装'}</span>{selected.enchanted && <span>✦ 已附魔</span>}{selected.unique && <span>唯一物品</span>}{selected.quest && <span>任务物品</span>}</div>
        <div className="stat-grid"><div><small>耐久</small><b>{selected.current} <span>/ {selected.maximum}</span></b></div>{selected.category === 'weapon' && <div><small>攻击</small><b>{selected.damage ?? 0}</b></div>}{selected.category === 'armor' && <div><small>防御</small><b>{selected.armor ?? 0}</b></div>}<div><small>重量</small><b>{selected.weight.toFixed(1)}</b></div>{selected.category === 'weapon' && <div><small>攻速</small><b>{(selected.attackSpeed ?? 0).toFixed(2)}×</b></div>}{selected.chargeCapacity !== undefined && <div><small>附魔充能</small><b>{Math.round(selected.chargeCurrent ?? selected.chargeCapacity)} <span>/ {Math.round(selected.chargeCapacity)}</span></b>{(selected.chargeBonus ?? 0) > 0 && <i>容量强化 +{Math.round((selected.chargeBonus ?? 0) * 100)}%</i>}</div>}<div className="wear-stat"><small>耐久损耗</small><b>{selectedWearRate === undefined ? '—' : `-${selectedWearRate.toFixed(2)}`}<span>{selectedWearRate === undefined ? ' 尚未启用' : ` / ${selected.wearRateLabel}`}</span></b>{selectedWearRate !== undefined && <i>耐磨减免 {Math.round((selected.wearReduction ?? 0) * 100)}%</i>}</div></div>
        <div className="detail-bar"><i style={{ width: `${percentage(selected)}%` }} /></div>
        <section className="enchantment-info"><small>当前附魔</small><b>{selected.enchantment ?? '无'}</b>{!selected.enchantmentReplaceable && <span>此物品不可替换附魔</span>}</section>
        <section className="action-strip"><div className="repair-summary"><p>修复装备</p>{selected.current >= selected.maximum ? <small>耐久已满</small> : selected.repairMaterials.length ? <MaterialList materials={selected.repairMaterials} /> : <small>没有找到可用的锻造或强化配方</small>}</div><button disabled={!canRepair} onClick={() => send('repair', { id: selected.id })} type="button">{!state.forge.active ? '需锻造设施' : !selected.repairable ? '无法修复' : !hasRepairMaterials ? '材料不足' : '⚒ 修复'}</button></section>
        {state.forge.active ? <section className="action-strip enhancement-entry"><div><p>卡片强化</p><small>已检测到附近的锻造设施，无需先操作工作台。进入强化页查看方案与材料代价。</small></div><button disabled={selected.broken} onClick={() => setEnhancingId(selected.id)} type="button">{selected.broken ? '请先修复装备' : '✦ 进入强化'}</button></section> : <p className="forge-hint">靠近锻造熔炉、冶炼熔炉、砂轮或护甲工作台后，重新打开面板即可直接修复或强化，无需先操作设施。</p>}
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
