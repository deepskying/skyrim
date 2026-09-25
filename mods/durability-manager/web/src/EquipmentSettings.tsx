import type { Dispatch, SetStateAction } from 'react';
import type { PanelState, Settings } from './types';
import type { WorkshopAction } from './bridge';
import { hudOffsets, normalizeHudPosition } from './hud';
export function EquipmentSettings({ draft, setDraft, send }: { state: PanelState; draft: Settings; setDraft: Dispatch<SetStateAction<Settings>>; send: WorkshopAction }) {
  const position = normalizeHudPosition(draft);
  const preview = hudOffsets(position, 320, 180, 92, 40);
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
          <label className="setting range-setting">
            <span className="setting-icon">↔</span><span className="setting-copy"><h3>浮窗水平位置</h3><p>距屏幕右侧的距离；数值越大，越靠左。</p></span>
            <span className="range-control"><output>{position.hudRightPercent}<small>%</small></output><input aria-label="浮窗水平位置" type="range" min="0" max="100" step="0.5" value={position.hudRightPercent} onChange={e => setDraft({ ...draft, hudRightPercent: Number(e.target.value) })} /><span className="range-labels"><span>靠右</span><span>靠左</span></span></span>
          </label>
          <label className="setting range-setting">
            <span className="setting-icon">↕</span><span className="setting-copy"><h3>浮窗垂直位置</h3><p>距屏幕底部的距离；数值越大，越靠上。</p></span>
            <span className="range-control"><output>{position.hudBottomPercent}<small>%</small></output><input aria-label="浮窗垂直位置" type="range" min="0" max="100" step="0.5" value={position.hudBottomPercent} onChange={e => setDraft({ ...draft, hudBottomPercent: Number(e.target.value) })} /><span className="range-labels"><span>靠下</span><span>靠上</span></span></span>
          </label>
          <footer className="setting-actions"><button className="save" type="button" onClick={() => setDraft({ ...draft, hudRightPercent: 100, hudBottomPercent: 2 })}>恢复默认位置</button><button className="save" onClick={() => send('saveSettings', { ...position, lowDurabilityThreshold: draft.lowDurabilityThreshold, weaponDisplaySeconds: draft.weaponDisplaySeconds, enableLowDurabilityWarning: draft.enableLowDurabilityWarning, allowEnchantedItemsToBreak: draft.allowEnchantedItemsToBreak })} type="button">保存配置</button></footer>
        </section>
        <aside className="settings-aside">
          <section className="hud-position-preview"><h3>浮窗位置预览</h3><div className="hud-preview-screen" role="img" aria-label={`浮窗位置示意：距右侧 ${position.hudRightPercent}%，距底部 ${position.hudBottomPercent}%`}><span>游戏画面</span><div className="hud-preview-item" style={{ right: `${preview.right / 3.2}%`, bottom: `${preview.bottom / 1.8}%` }}><b>◇ 21 · 角色状态</b><span>钢剑 · 80 / 100</span><i /></div></div><p>示意预览；实际位置会按浮窗大小限制在屏幕内。角色状态、耐久列表和临时提示一起移动，保存后生效。</p></section>
          <section className="settings-note"><span>i</span><div><h3>提示规则</h3><p>武器收起后仍显示耐久；其他装备低于阈值时加入，卸下或修复后移除。</p></div></section>
        </aside>
      </div>
</>;
}
