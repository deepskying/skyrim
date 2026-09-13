import type { Dispatch, SetStateAction } from 'react';
import type { PanelState, Settings } from './types';
import { defaultDismantleHotkey, shortcutLabel } from './dismantle-shortcut';
import type { WorkshopAction } from './bridge';
export function EquipmentSettings({ state, draft, setDraft, send }: { state: PanelState; draft: Settings; setDraft: Dispatch<SetStateAction<Settings>>; send: WorkshopAction }) {
  const dismantleHotkey = state.settings.dismantleHotkey ?? defaultDismantleHotkey;
  return <>
      <div className="section-heading settings-heading"><div><p>MOD SETTINGS</p><h2>装备养护设置</h2></div><span className="settings-status"><i />保存后立即生效</span></div>
      <div className="settings-layout">
        <section className="settings-card">
          <header className="settings-group-title"><span>ᛏ</span><div><p>HUD FEEDBACK</p><h3>战斗提示</h3></div></header>
          <label className="setting range-setting">
            <span className="setting-icon warning-icon">!</span>
            <span className="setting-copy"><small>WARNING THRESHOLD</small><h3>低耐久预警阈值</h3><p>已穿戴装备低于该比例时常显；当前武器始终显示。</p></span>
            <span className="range-control"><output>{draft.lowDurabilityThreshold}<small>%</small></output><input aria-label="低耐久预警阈值" max="99" min="1" onChange={(event) => setDraft({ ...draft, lowDurabilityThreshold: Number(event.target.value) })} type="range" value={draft.lowDurabilityThreshold} /><span className="range-labels"><span>1%</span><span>危险线</span><span>99%</span></span></span>
          </label>
          <label className="setting range-setting">
            <span className="setting-icon duration-icon">◷</span>
            <span className="setting-copy"><small>DISPLAY DURATION</small><h3>临时提示显示时长</h3><p>控制低耐久弹出提示的停留时间，不影响装备耐久常显。</p></span>
            <span className="range-control"><output>{draft.weaponDisplaySeconds.toFixed(1)}<small> 秒</small></output><input aria-label="临时提示显示时长" max="10" min="0.5" onChange={(event) => setDraft({ ...draft, weaponDisplaySeconds: Number(event.target.value) })} step="0.5" type="range" value={draft.weaponDisplaySeconds} /><span className="range-labels"><span>0.5 秒</span><span>显示时间</span><span>10 秒</span></span></span>
          </label>
          <label className="setting toggle-setting">
            <span className="setting-icon notification-icon">⌁</span>
            <span className="setting-copy"><small>LOW DURABILITY ALERT</small><h3>启用低耐久 HUD 预警</h3><p>关闭后不再弹出一次性预警，低耐久装备仍会常显。</p></span>
            <span className="toggle-control"><input checked={draft.enableLowDurabilityWarning} onChange={(event) => setDraft({ ...draft, enableLowDurabilityWarning: event.target.checked })} type="checkbox" /><span className="toggle-track"><i /></span><b>{draft.enableLowDurabilityWarning ? '已启用' : '已关闭'}</b></span>
          </label>
          <footer className="setting-actions"><span>配置将写入 <code>DurabilityManager.ini</code></span><button className="save" onClick={() => send('saveSettings', { lowDurabilityThreshold: draft.lowDurabilityThreshold, weaponDisplaySeconds: draft.weaponDisplaySeconds, enableLowDurabilityWarning: draft.enableLowDurabilityWarning, allowEnchantedItemsToBreak: draft.allowEnchantedItemsToBreak })} type="button">保存配置</button></footer>
        </section>
        <aside className="settings-aside">
          <section className={`hotkey-card ${state.capturingDismantleHotkey ? 'capturing' : ''}`}>
            <header><span>⌨</span><div><p>DISMANTLE HOTKEY</p><h3>分解快捷键</h3></div></header>
            <div className="hotkey-combo"><kbd>{shortcutLabel(dismantleHotkey)}</kbd></div>
            <button className="capture-button" onClick={() => send(state.capturingDismantleHotkey ? 'cancelHotkeyCapture' : 'beginDismantleHotkeyCapture')}>{state.capturingDismantleHotkey ? '取消录入' : '录入分解快捷键'}</button>
            <small>{state.capturingDismantleHotkey ? '请按下组合键，Esc 取消。支持字母、F1–F12、Delete。' : '按键录入后自动保存；在分解页开启或关闭。'}</small>
          </section>
          <section className="settings-note"><span>i</span><div><h3>提示规则</h3><p>武器收起后仍显示耐久；其他装备低于阈值时加入，卸下或修复后移除。</p></div></section>
        </aside>
      </div>
</>;
}
