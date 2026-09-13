import { useEffect, useRef, useState } from 'react';
import type { EquipmentItem, DismantleQuote } from './types';
import { defaultDismantleHotkey, shortcutLabel, type DismantleHotkey } from './dismantle-shortcut';

function ShortcutSettings({ binding, onAction }: { binding: DismantleHotkey; onAction: (type: string, data?: Record<string, unknown>) => void }) {
  return <div className="dismantle-shortcut-settings">
    <div><b>直接分解</b><kbd>{shortcutLabel(binding)}</kbd><label><input aria-label="启用快捷分解" type="checkbox" checked={binding.enabled} onChange={(e) => { onAction('setDismantleHotkeyEnabled', { enabled: e.target.checked }); e.target.blur(); }} />{binding.enabled ? '已启用' : '已关闭'}</label></div>
    <p>↑ ↓ 选择装备 · 按一次分解一件 · 在工坊设置中修改按键</p>
  </div>;
}

export function DismantlePanel({ item, quote, active, hotkey = defaultDismantleHotkey, onAction }: {
  item: EquipmentItem; quote?: DismantleQuote; active: boolean;
  hotkey?: DismantleHotkey;
  onAction: (type: string, data?: Record<string, unknown>) => void;
}) {
  const [busy, setBusy] = useState(false);
  const submitted = useRef(false);
  const review = quote?.id === item.id ? quote : undefined;
  const blocked = item.quest || item.unique ? '任务或唯一装备不可分解' : item.dismantleBlocked;
  useEffect(() => { setBusy(false); submitted.current = false; }, [quote?.token, item.id]);
  return <section className="equipment-detail dismantle-detail">
    <ShortcutSettings binding={hotkey} onAction={onAction} />
    <p className="workshop-eyebrow">RECOVER & REFORGE</p>
    <h2>让旧装备，成为新的材料。</h2>
    <p className="recycle-intro">分解一件随身装备，取回可用于修理与锻造的材料。</p>
    <div className="recycle-item"><span>⚒</span><div><h3>{item.name}{item.enhancementLevel > 0 && ` +${item.enhancementLevel}`}</h3><p>{item.slot} · 携带 {item.quantity} 件{item.equipped && ' · 当前已装备'}</p></div></div>
    {!active ? <p className="recycle-note">靠近铁匠铺的锻造设施后，可预览回收材料。</p> : blocked ? <p className="recycle-note">{blocked}</p> : review ? <>
      <h3>本次回收</h3><div className="salvage-grid">{review.materials.map((m, i) => <div key={`${m.name}-${i}`}><span>◇</span><b>{m.name}</b><strong>+{m.required}</strong></div>)}</div>
      <p className="recycle-note">将永久移除 <b>1 件「{review.name}」</b>，附魔与强化也会消失。{review.equipped && '这件装备会先自动卸下。'}</p>
      <div className="recycle-actions"><button disabled={busy} onClick={() => onAction('cancelDismantle')}>取消</button><button className="recycle-confirm" disabled={busy} onClick={() => { if (submitted.current) return; submitted.current = true; setBusy(true); onAction('dismantle', { token: review.token }); }}>{busy ? '正在分解…' : '确认分解 1 件'}</button></div>
    </> : <><p className="recycle-note">先查看材料清单。预览不会消耗装备。</p><button className="recycle-preview" onClick={() => onAction('quoteDismantle', { id: item.id })}>预览回收材料 →</button></>}
  </section>;
}
