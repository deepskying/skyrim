import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { demoState } from './demo';
import { Icon } from './icon';
import type { HotkeyAction, HotkeyBinding, InventoryItem, ItemCategory, MagicCategory, MagicItem, Page, PanelState } from './types';

type Row = InventoryItem | MagicItem;
type SortKey = 'name' | 'count' | 'weight' | 'value' | 'stat' | 'type';
type NavigationDirection = 'left' | 'right' | 'up' | 'down';

type NativeBridge = {
  receiveState?: (next: PanelState) => void;
  togglePage?: () => void;
  toggleFavorite?: () => void;
  navigate?: (direction: NavigationDirection) => void;
  focusSearch?: () => void;
};

declare global {
  interface Window {
    InventoryManager?: NativeBridge;
    inventoryManagerAction?: (data: string) => void;
  }
}

const inventoryCategories: { id: ItemCategory; label: string; icon: string }[] = [
  { id: 'favorites', label: '收藏', icon: 'favorite' }, { id: 'all', label: '所有', icon: 'all' },
  { id: 'weapons', label: '武器', icon: 'weapon' }, { id: 'armor', label: '护甲', icon: 'armor' },
  { id: 'potions', label: '药水', icon: 'potion' }, { id: 'scrolls', label: '卷轴', icon: 'scroll' },
  { id: 'food', label: '食物', icon: 'food' }, { id: 'ingredients', label: '炼金', icon: 'ingredient' }, { id: 'misc', label: '杂项', icon: 'misc' },
];

const magicCategories: { id: MagicCategory; label: string; icon: string }[] = [
  { id: 'favorites', label: '收藏', icon: 'favorite' }, { id: 'all', label: '所有', icon: 'all' },
  { id: 'destruction', label: '毁灭系', icon: 'destruction' }, { id: 'alteration', label: '变化系', icon: 'alteration' },
  { id: 'illusion', label: '幻术系', icon: 'illusion' }, { id: 'restoration', label: '恢复系', icon: 'restoration' },
  { id: 'conjuration', label: '召唤系', icon: 'conjuration' }, { id: 'shouts', label: '龙吼', icon: 'shout' }, { id: 'powers', label: '特殊能力', icon: 'power' }, { id: 'status', label: '状态', icon: 'status' },
];

const hotkeyLabels: Record<HotkeyAction, { title: string; description: string }> = {
  open: { title: '唤起面板', description: '在游戏中打开或关闭物品清单。' },
  favorite: { title: '切换收藏', description: '收藏或取消收藏当前选中的物品。' },
  activate: { title: '执行默认操作', description: '装备、使用当前选中的项目。' },
  pageToggle: { title: '切换清单类型', description: '在背包清单和魔法清单之间切换。' },
  search: { title: '搜索', description: '将光标置入物品搜索框。' },
};

const directInputCodes: Record<string, number> = {
  Escape: 0x01, Digit1: 0x02, Digit2: 0x03, Digit3: 0x04, Digit4: 0x05, Digit5: 0x06, Digit6: 0x07, Digit7: 0x08, Digit8: 0x09, Digit9: 0x0A, Digit0: 0x0B,
  Tab: 0x0F, KeyQ: 0x10, KeyW: 0x11, KeyE: 0x12, KeyR: 0x13, KeyT: 0x14, KeyY: 0x15, KeyU: 0x16, KeyI: 0x17, KeyO: 0x18, KeyP: 0x19, AltLeft: 0x38, AltRight: 0xB8,
  KeyA: 0x1E, KeyS: 0x1F, KeyD: 0x20, KeyF: 0x21, KeyG: 0x22, KeyH: 0x23, KeyJ: 0x24, KeyK: 0x25, KeyL: 0x26, Enter: 0x1C,
  KeyZ: 0x2C, KeyX: 0x2D, KeyC: 0x2E, KeyV: 0x2F, KeyB: 0x30, KeyN: 0x31, KeyM: 0x32, Slash: 0x35, Space: 0x39,
  F1: 0x3B, F2: 0x3C, F3: 0x3D, F4: 0x3E, F5: 0x3F, F6: 0x40, F7: 0x41, F8: 0x42, F9: 0x43, F10: 0x44, F11: 0x57, F12: 0x58,
};

function hotkeyLabel(binding: HotkeyBinding) {
  return [binding.ctrl && 'Ctrl', binding.shift && 'Shift', binding.alt && 'Alt', binding.key].filter(Boolean).join(' + ');
}

function matchesHotkey(event: KeyboardEvent, binding: HotkeyBinding | undefined) {
  if (!binding || event.ctrlKey !== binding.ctrl || event.shiftKey !== binding.shift || event.altKey !== binding.alt) return false;
  return directInputCodes[event.code] === binding.keyCode;
}

function send(type: string, data: Record<string, unknown> = {}) {
  window.inventoryManagerAction?.(JSON.stringify({ type, ...data }));
}

function number(value: number, digits = 0) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value);
}

function sortValue(row: Row, key: SortKey): string | number {
  if (key === 'name') return row.name;
  if (key === 'count') return 'count' in row ? row.count : 0;
  if (key === 'weight') return 'weight' in row ? row.weight : 0;
  if (key === 'value') return 'value' in row ? row.value : ('cost' in row ? row.cost ?? 0 : 0);
  if (key === 'type') return row.category;
  return 'statValue' in row ? row.statValue ?? -1 : ('cooldown' in row ? row.cooldown ?? -1 : -1);
}

function VirtualRows({
  rows, selectedId, onSelect, onActivate, renderRow,
}: {
  rows: Row[];
  selectedId: number | undefined;
  onSelect: (row: Row) => void;
  onActivate: (row: Row) => void;
  renderRow: (row: Row, selected: boolean) => ReactNode;
}) {
  const rowHeight = 54;
  const overscan = 8;
  const [scrollTop, setScrollTop] = useState(0);
  const [height, setHeight] = useState(460);
  const viewport = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setHeight(element.clientHeight));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const first = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const last = Math.min(rows.length, Math.ceil((scrollTop + height) / rowHeight) + overscan);
  const visible = rows.slice(first, last);

  return (
    <div className="list-viewport" onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)} ref={viewport}>
      <div className="virtual-spacer" style={{ height: rows.length * rowHeight }}>
        <div className="virtual-items" style={{ transform: `translateY(${first * rowHeight}px)` }}>
          {visible.map((row) => (
            <button className={`list-row ${'count' in row ? 'inventory-row' : 'magic-row'} ${selectedId === row.id ? 'selected' : ''} ${'enchanted' in row && row.enchanted ? 'enchanted-row' : ''}`} key={row.id} onClick={() => onActivate(row)} onMouseEnter={() => onSelect(row)} type="button">
              {renderRow(row, selectedId === row.id)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function App() {
  const [state, setState] = useState<PanelState>(import.meta.env.DEV ? demoState : { inventory: [], magic: [], player: { gold: 0, weight: 0, weightMax: 0 }, hotkeys: [] });
  const [page, setPage] = useState<Page>('inventory');
  const [inventoryCategory, setInventoryCategory] = useState<ItemCategory>('all');
  const [magicCategory, setMagicCategory] = useState<MagicCategory>('all');
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<number>();
  const [dismantleConfirmId, setDismantleConfirmId] = useState<number>();
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortAscending, setSortAscending] = useState(true);
  const searchRef = useRef<HTMLInputElement>(null);
  const selectedRef = useRef<Row>();
  const pageRef = useRef<Page>('inventory');
  const navigateRef = useRef<(direction: NavigationDirection) => void>(() => {});

  useEffect(() => {
    window.InventoryManager = {
      receiveState: (next) => setState(next),
      togglePage: () => {
        setPage((current) => current === 'inventory' ? 'magic' : 'inventory');
        setSelectedId(undefined);
        setQuery('');
      },
      toggleFavorite: () => {
        const activePage = pageRef.current;
        const activeRow = selectedRef.current;
        if (!activeRow || (activePage === 'magic' && activeRow.category === 'status')) return;
        send('favorite', { id: activeRow.id, page: activePage });
      },
      navigate: (direction) => navigateRef.current(direction),
      focusSearch: () => searchRef.current?.focus(),
    };
    send('ready');
    return () => { delete window.InventoryManager; };
  }, []);

  const categories = page === 'inventory' ? inventoryCategories : magicCategories;
  const activeCategory = page === 'inventory' ? inventoryCategory : magicCategory;
  const allRows = page === 'inventory' ? state.inventory : state.magic;
  const rows = useMemo(() => allRows.filter((row) => {
    const categoryMatch = activeCategory === 'all' || (activeCategory === 'favorites' ? row.favorited : row.category === activeCategory);
    return categoryMatch && row.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
  }).sort((left, right) => {
    const leftValue = sortValue(left, sortKey);
    const rightValue = sortValue(right, sortKey);
    const result = typeof leftValue === 'string' && typeof rightValue === 'string' ? leftValue.localeCompare(rightValue, 'zh-CN') : Number(leftValue) - Number(rightValue);
    return sortAscending ? result : -result;
  }), [activeCategory, allRows, query, sortAscending, sortKey]);
  const selected = rows.find((row) => row.id === selectedId) ?? rows[0];
  const canManageMagic = (row: MagicItem) => row.category !== 'status';
  const canDismantle = (row: Row) => 'weight' in row && (row.category === 'weapons' || row.category === 'armor');
  const canActivateInventory = (row: Row) => 'weight' in row && ['weapons', 'armor', 'potions', 'scrolls', 'food'].includes(row.category);
  const selectedEnchantments = selected && 'enchantments' in selected ? selected.enchantments : undefined;
  const hotkey = (action: HotkeyAction) => state.hotkeys?.find((binding) => binding.action === action);
  const carryPercent = state.player.weightMax > 0 ? Math.min(100, Math.max(0, state.player.weight / state.player.weightMax * 100)) : 0;
  const carryState = state.player.weightMax > 0 && state.player.weight >= state.player.weightMax ? 'danger' : carryPercent >= 80 ? 'warning' : '';
  const statColumnLabel = activeCategory === 'weapons' ? '攻击' : activeCategory === 'armor' ? '防御' : '属性';
  const selectSort = (nextKey: SortKey) => {
    if (sortKey === nextKey) setSortAscending((value) => !value);
    else { setSortKey(nextKey); setSortAscending(nextKey === 'name'); }
  };
  const sortLabel = (label: string, key: SortKey) => <button className={sortKey === key ? 'sorted' : ''} onClick={() => selectSort(key)} type="button">{label}{sortKey === key && <small>{sortAscending ? '▲' : '▼'}</small>}</button>;

  useEffect(() => {
    selectedRef.current = selected;
    pageRef.current = page;
  }, [page, selected]);

  const selectPage = (next: Page) => {
    setPage(next);
    setSelectedId(undefined);
    setQuery('');
  };
  const cycleCategory = (direction: -1 | 1) => {
    const current = categories.findIndex((entry) => entry.id === activeCategory);
    const next = categories[(current + direction + categories.length) % categories.length].id;
    if (page === 'inventory') setInventoryCategory(next as ItemCategory);
    else setMagicCategory(next as MagicCategory);
    setSelectedId(undefined);
  };
  const selectRelative = (direction: -1 | 1) => {
    if (!rows.length) return;
    const current = Math.max(0, rows.findIndex((row) => row.id === selected?.id));
    setSelectedId(rows[(current + direction + rows.length) % rows.length].id);
  };
  navigateRef.current = (direction) => {
    if (page === 'hotkeys') return;
    if (direction === 'left') cycleCategory(-1);
    else if (direction === 'right') cycleCategory(1);
    else if (direction === 'up') selectRelative(-1);
    else selectRelative(1);
  };

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (event.repeat || state.capturingAction) return;
      const typing = event.target instanceof HTMLInputElement;
      if (event.key === 'Escape') { event.preventDefault(); send('close'); return; }
      if (typing) return;
      if (page === 'hotkeys') return;
      if (event.key === 'ArrowLeft' || event.code === 'KeyA') { event.preventDefault(); cycleCategory(-1); }
      else if (event.key === 'ArrowRight' || event.code === 'KeyD') { event.preventDefault(); cycleCategory(1); }
      else if (event.key === 'ArrowUp' || event.code === 'KeyW') { event.preventDefault(); selectRelative(-1); }
      else if (event.key === 'ArrowDown' || event.code === 'KeyS') { event.preventDefault(); selectRelative(1); }
      else if (matchesHotkey(event, hotkey('favorite')) && selected) { event.preventDefault(); send('favorite', { id: selected.id, page }); }
      else if (matchesHotkey(event, hotkey('activate')) && selected && (page === 'inventory' ? canActivateInventory(selected) : canManageMagic(selected as MagicItem))) { event.preventDefault(); send('activate', { id: selected.id, page }); }
      else if (matchesHotkey(event, hotkey('pageToggle'))) { event.preventDefault(); window.InventoryManager?.togglePage?.(); }
      else if (matchesHotkey(event, hotkey('search'))) { event.preventDefault(); searchRef.current?.focus(); }
    };
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, [page, rows, selected, state.capturingAction, state.hotkeys]);

  const categoryCount = (id: ItemCategory | MagicCategory) => allRows.filter((row) => id === 'all' || (id === 'favorites' ? row.favorited : row.category === id)).length;
  const meta = (row: InventoryItem | MagicItem) => {
    if ('weight' in row) return `${number(row.weight, 1)} 重量 · ${number(row.value)} 金币`;
    if (row.category === 'shouts' || row.category === 'powers') return row.cooldown ? `冷却 ${number(row.cooldown)} 秒` : '能力';
    if (row.category === 'status') return row.active ? '当前生效' : '状态';
    return `${number(row.cost ?? 0)} 魔力`;
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">ᛟ</span><div><p>SKYRIM LEDGER</p><h1>物品清单</h1></div></div>
        <nav className="page-tabs" aria-label="List type">
          <button className={page === 'inventory' ? 'active' : ''} onClick={() => selectPage('inventory')} type="button"><Icon name="misc" /> 背包清单</button>
          <button className={page === 'magic' ? 'active' : ''} onClick={() => selectPage('magic')} type="button"><Icon name="magic" /> 魔法清单</button>
          <button className={page === 'hotkeys' ? 'active' : ''} onClick={() => selectPage('hotkeys')} type="button"><span className="tab-symbol">⚙</span> 快捷键配置</button>
        </nav>
        <div className="global-stats" aria-label="Player resources">
          <span><Icon name="gold" /> {number(state.player.gold)}</span>
          <div className={`carry-stat ${carryState}`}>
            <span><Icon name="weight" /> 负重 {number(state.player.weight, 1)} / {number(state.player.weightMax, 1)}</span>
            <div aria-label="负重进度" className="carry-progress"><i style={{ width: `${carryPercent}%` }} /></div>
          </div>
        </div>
        <button className="close" onClick={() => send('close')} title="关闭 (Esc)" type="button"><Icon name="close" /></button>
      </header>

      {page !== 'hotkeys' && <aside className="categories" aria-label="Categories">
        {categories.map((category) => <button className={category.id === activeCategory ? 'active' : ''} key={category.id} onClick={() => {
          if (page === 'inventory') setInventoryCategory(category.id as ItemCategory);
          else setMagicCategory(category.id as MagicCategory);
          setSelectedId(undefined);
        }} type="button"><Icon name={category.icon} /><span>{category.label}</span><small>{categoryCount(category.id)}</small></button>)}
      </aside>}

      <section className={`body ${page === 'hotkeys' ? 'hotkey-body' : ''}`}>
        {page === 'hotkeys' ? <section className="hotkey-settings">
          <div className="hotkey-head"><div><p>CONTROLS</p><h2>快捷键配置</h2></div><span>设置会立即生效，并保存至 InventoryManager.ini。</span></div>
          <div className="hotkey-list">
            {(state.hotkeys ?? []).map((binding) => <article className={`hotkey-row ${state.capturingAction === binding.action ? 'listening' : ''}`} key={binding.action}>
              <div><h3>{hotkeyLabels[binding.action].title}</h3><p>{hotkeyLabels[binding.action].description}</p></div>
              <div className="hotkey-control"><kbd>{state.capturingAction === binding.action ? '请按下新快捷键…' : hotkeyLabel(binding)}</kbd>{state.capturingAction === binding.action ? <button onClick={() => send('cancelHotkeyCapture')} type="button">取消</button> : <button onClick={() => send('beginHotkeyCapture', { action: binding.action })} type="button">重新绑定</button>}</div>
            </article>)}
          </div>
          <p className="hotkey-note">导航固定使用方向键或 WASD；搜索框获得焦点时不会触发面板快捷键。</p>
        </section> : <>
        <section className={`content ${page} ${activeCategory}`}>
          <div className="content-head">
            <div><p>{page === 'inventory' ? 'CARRIED ITEMS' : 'KNOWN MAGIC'}</p><h2>{categories.find((category) => category.id === activeCategory)?.label}</h2></div>
            <label className="search"><Icon name="search" /><input onChange={(event) => setQuery(event.target.value)} placeholder="搜索  /" ref={searchRef} value={query} /></label>
          </div>
          {page === 'inventory' ? <div className="columns inventory-columns">{sortLabel('名称', 'name')}{sortLabel('重量', 'weight')}{sortLabel('价值', 'value')}{sortLabel(statColumnLabel, 'stat')}</div> : <div className="columns magic-columns">{sortLabel('名称', 'name')}{sortLabel('魔力', 'value')}{sortLabel('冷却', 'stat')}{sortLabel('类型', 'type')}</div>}
          <VirtualRows
            rows={rows}
            selectedId={selected?.id}
            onSelect={(row) => setSelectedId(row.id)}
            onActivate={(row) => {
              if (page === 'inventory' ? canActivateInventory(row) : canManageMagic(row as MagicItem)) send('activate', { id: row.id, page });
            }}
            renderRow={(row, isSelected) => <>
              <span className="row-icon"><Icon name={row.icon} /></span>
              <span className="row-name"><span className="row-title"><strong>{row.name}</strong>{'count' in row && row.count > 1 && <mark className="count-badge">×{row.count}</mark>}{row.equipped && <mark className="state-tag equipped"><Icon name="equipped" /> 已装备</mark>}{row.favorited && <mark className="state-tag favorite"><Icon name="favorite" /> 收藏</mark>}</span><small>{meta(row)}</small></span>
              <span className="row-meta row-weight">{'weight' in row ? number(row.weight, 1) : ('cost' in row ? number(row.cost ?? 0) : '—')}</span>
              <span className="row-meta row-value">{'value' in row ? number(row.value) : ('cooldown' in row && row.cooldown ? `${number(row.cooldown)} 秒` : '—')}</span>
              <span className="row-meta row-stat">{'statValue' in row && row.statLabel ? number(row.statValue ?? 0, 1) : ('category' in row ? (row.category === 'status' ? '状态' : '—') : '—')}</span>
              <span className="row-flags">{'enchanted' in row && row.enchanted && <Icon name="enchanted" />}{'quest' in row && row.quest && <Icon name="quest" />}{isSelected && <Icon name="right" />}</span>
            </>}
          />
          {rows.length === 0 && <p className="empty">这个分类中没有符合条件的项目。</p>}
        </section>

        <aside className="details">
          {selected ? <>
            <div className="detail-icon"><Icon name={selected.icon} /></div>
            <p className="detail-kicker">{page === 'inventory' ? '物品详情' : '魔法详情'}</p>
            <h3>{selected.name}</h3>
            {!selectedEnchantments?.length && <p className="detail-description">{'description' in selected && selected.description ? selected.description : '选择项目后可使用 Enter 执行默认动作，按 F 切换收藏。'}</p>}
            {selectedEnchantments && selectedEnchantments.length > 0 && <section className="enchantments"><p>附魔</p>{selectedEnchantments.map((effect, index) => <div className="enchantment" key={`${effect.name}-${index}`}><Icon name="enchanted" /><span>{effect.name}</span>{effect.magnitude !== undefined && <b>{number(effect.magnitude, 1)}</b>}{effect.duration !== undefined && <small>{number(effect.duration)} 秒</small>}</div>)}</section>}
            <div className="detail-stats">
              {'count' in selected && <div><span>数量</span><strong>×{selected.count}</strong></div>}
              {'weight' in selected && <><div><span>重量</span><strong>{number(selected.weight, 1)}</strong></div><div><span>价值</span><strong>{number(selected.value)}</strong></div></>}
              {'statLabel' in selected && selected.statLabel && <><div><span>{selected.statLabel}</span><strong className="stat-value">{number(selected.statValue ?? 0, 1)}</strong></div>{selected.equippedValue !== undefined && <div><span>当前装备</span><strong>{number(selected.equippedValue, 1)}</strong></div>}{selected.statDelta !== undefined && <div><span>装备变化</span><strong className={selected.statDelta > 0 ? 'stat-up' : selected.statDelta < 0 ? 'stat-down' : 'stat-even'}>{selected.statDelta > 0 ? '+' : ''}{number(selected.statDelta, 1)}</strong></div>}</>}
              {'cost' in selected && <div><span>魔力</span><strong>{number(selected.cost ?? 0)}</strong></div>}
              {'cooldown' in selected && selected.cooldown && <div><span>冷却</span><strong>{number(selected.cooldown)} 秒</strong></div>}
            </div>
            {(page === 'inventory' || canManageMagic(selected as MagicItem)) && <div className="detail-actions"><button onClick={() => send('favorite', { id: selected.id, page })} type="button"><Icon name="favorite" /> {selected.favorited ? '取消收藏' : '收藏'} (F)</button>{(page === 'inventory' ? canActivateInventory(selected) : canManageMagic(selected as MagicItem)) && <button className="primary" onClick={() => send('activate', { id: selected.id, page })} type="button">{page === 'magic' ? '装备' : selected.category === 'potions' || selected.category === 'food' ? '使用' : '装备'} (Enter)</button>}</div>}
            {page === 'inventory' && canDismantle(selected) && (dismantleConfirmId === selected.id ? <div className="dismantle-confirm"><p>确定分解一件{'enchanted' in selected && selected.enchanted ? '附魔' : ''}物品吗？将返还部分锻造材料。</p><div><button className="danger" onClick={() => { send('dismantle', { id: selected.id }); setDismantleConfirmId(undefined); }} type="button">确认分解</button><button onClick={() => setDismantleConfirmId(undefined)} type="button">取消</button></div></div> : <button className="dismantle" onClick={() => setDismantleConfirmId(selected.id)} type="button">分解一件物品</button>)}
          </> : <p className="empty">选择一项以查看详细信息。</p>}
        </aside>
        </>}
      </section>
      <footer>{state.message || '准备就绪。'}</footer>
    </main>
  );
}
