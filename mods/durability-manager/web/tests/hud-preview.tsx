// Manual browser fixture using the real HUD receiver; excluded from the game build.
import { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from '../src/App';
import type { HudMessage } from '../src/hud';
import '../src/styles.css';
import '../src/workshop.css';
import '../src/arrows/arrows.css';

const examples: Omit<HudMessage, 'id' | 'durationMilliseconds'>[] = [
  { kind: 'weapon', title: '精灵长剑', detail: '右手武器 · 当前耐久', current: 782, maximum: 1000 },
  { kind: 'warning', title: '精灵长剑 · 耐久不足', detail: '请及时修复装备', current: 128, maximum: 1000 },
  { kind: 'warning', title: '武器损坏', detail: '精灵长剑已损坏并分解，回收材料已放入背包。' },
  { kind: 'weapon', title: '附有强效火焰与寒霜双重附魔的传奇龙骨双手巨剑', detail: '双手武器 · 当前耐久', current: 12345, maximum: 20000 },
];
let id = 0;
const equipped = [
  { id: '1:1', kind: 'weapon', title: '精灵长剑', detail: '右手', current: 782, maximum: 1000 },
  { id: '1:2', kind: 'warning', title: '精灵长剑', detail: '左手', current: 128, maximum: 1000 },
  { id: '2:1', kind: 'warning', title: '钢制护甲', detail: '低耐久', current: 25, maximum: 100 },
  { id: '3:1', kind: 'warning', title: '皮靴', detail: '低耐久', current: 16, maximum: 100 },
];
function showEquipped(items = equipped) {
  window.DurabilityManager?.setPanelVisible(false);
  window.DurabilityManager?.clearHud();
  window.DurabilityManager?.updateEquippedHud(items);
}
function show(index: number) {
  window.DurabilityManager?.setPanelVisible(false);
  window.DurabilityManager?.showHud({ ...examples[index], id: ++id, durationMilliseconds: 10000 });
}
function Preview() {
  useEffect(() => { showEquipped(); }, []);
  return <>
    <style>{`body { min-width: 0; min-height: 100vh; background: repeating-linear-gradient(120deg, transparent 0 90px, #ffffff04 90px 91px), linear-gradient(135deg, #575a53, #323934 55%, #626359); }
      .hud-preview-controls { position: fixed; top: 30px; left: 30px; color: #e5e5e0; font: 14px "Segoe UI", "Microsoft YaHei", sans-serif; }
      .hud-preview-controls p { color: #bdbfb8; }
      .hud-preview-controls button { padding: 8px 12px; margin: 0 8px 8px 0; border: 1px solid #ffffff40; border-radius: 2px; background: #0006; }
    `}</style>
    <div className="hud-preview-controls"><h2>装备耐久提示</h2><p>样式预览 · 常显装备列表 · 临时通知显示 10 秒</p>
      <button onClick={() => showEquipped()}>常显装备</button>
      <button onClick={() => showEquipped([...equipped, ...equipped.map(item => ({ ...item, id: `${item.id}:extra` }))])}>多件装备</button>
      <button onClick={() => showEquipped(equipped.slice(0, 2))}>修复护甲与靴子</button>
      <button onClick={() => showEquipped([])}>卸下全部装备</button>
      <button onClick={() => window.DurabilityManager?.clearHud()}>模拟读档清空</button>
      {['普通耐久', '低耐久警告', '损坏提示', '长名称'].map((label, index) => <button key={label} onClick={() => show(index)}>{label}</button>)}
    </div>
    <App />
  </>;
}
createRoot(document.getElementById('root')!).render(<Preview />);
