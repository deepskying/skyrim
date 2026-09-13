import type { Dispatch, SetStateAction } from 'react';
import type { PanelState, Settings } from './types';
import type { WorkshopAction } from './bridge';

export function GeneralSettings({ state, draft, setDraft, send }: { state: PanelState; draft: Settings; setDraft: Dispatch<SetStateAction<Settings>>; send: WorkshopAction }) {
  const binding = state.settings.hotkey;
  const parts = [binding.ctrl && 'Ctrl', binding.shift && 'Shift', binding.alt && 'Alt', binding.key].filter(Boolean);
  return <>
    <div className="section-heading settings-heading"><div><p>GENERAL SETTINGS</p><h2>通用设置</h2></div><span className="settings-status">调整即时预览，保存后保留</span></div>
    <div className="settings-common"><div><h3>工坊快捷键</h3><p>{state.capturingHotkey ? '按下新的组合键，Esc 取消。' : '所有工坊栏目共用，录入后自动保存。'}</p></div><div className="hotkey-combo">{parts.map((part, i) => <span key={String(part)}>{i > 0 && <i>+</i>}<kbd>{part}</kbd></span>)}</div><button className="capture-button" onClick={() => send(state.capturingHotkey ? 'cancelHotkeyCapture' : 'beginHotkeyCapture')}>{state.capturingHotkey ? '取消等待' : '修改工坊快捷键'}</button></div>
    <section className="settings-card general-settings-card">
      <label className="setting range-setting"><span className="setting-icon">Aa</span><span className="setting-copy"><h3>界面字号</h3><p>统一调整装备养护、魔法箭和设置页的文字大小。</p></span><span className="range-control"><output>{draft.uiFontScale ?? 100}<small>%</small></output><input aria-label="界面字号" type="range" min="80" max="130" step="5" value={draft.uiFontScale ?? 100} onChange={e => setDraft({ ...draft, uiFontScale: Number(e.target.value) })} /><span className="range-labels"><span>80%</span><span>标准 100%</span><span>130%</span></span></span></label>
      <label className="setting range-setting"><span className="setting-icon">◐</span><span className="setting-copy"><h3>界面透明度</h3><p>数值越高，越容易透过背景看到游戏画面。文字和图标保持清晰。</p></span><span className="range-control"><output>{draft.uiTransparency ?? 16}<small>%</small></output><input aria-label="界面透明度" type="range" min="0" max="60" step="1" value={draft.uiTransparency ?? 16} onChange={e => setDraft({ ...draft, uiTransparency: Number(e.target.value) })} /><span className="range-labels"><span>不透明</span><span>背景透明度</span><span>60%</span></span></span></label>
      <label className="setting toggle-setting"><span className="setting-icon">♪</span><span className="setting-copy"><h3>工坊操作音效</h3><p>启用已支持的按钮点击、修复和强化结果音效。</p></span><span className="toggle-control"><input aria-label="工坊操作音效" type="checkbox" checked={draft.enableWorkshopSounds} onChange={e => setDraft({ ...draft, enableWorkshopSounds: e.target.checked })} /><span className="toggle-track"><i /></span><b>{draft.enableWorkshopSounds ? '已启用' : '已关闭'}</b></span></label>
      <footer className="setting-actions"><button type="button" onClick={() => setDraft({ ...draft, uiFontScale: 100, uiTransparency: 16, enableWorkshopSounds: true })}>恢复默认外观与音效</button><button type="button" onClick={() => setDraft({ ...draft, uiFontScale: state.settings.uiFontScale, uiTransparency: state.settings.uiTransparency, enableWorkshopSounds: state.settings.enableWorkshopSounds })}>还原已保存设置</button><button className="save" type="button" onClick={() => send('saveGeneralSettings', { uiFontScale: draft.uiFontScale ?? 100, uiTransparency: draft.uiTransparency ?? 16, enableWorkshopSounds: draft.enableWorkshopSounds })}>保存通用设置</button></footer>
    </section>
  </>;
}
