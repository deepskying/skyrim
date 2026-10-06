// Development-only fixture for the largest material budget; excluded from the game build.
import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { SoulPoolPage } from '../src/arrows/SoulPool';
import { arrowDemo } from '../src/arrows/demo';
import '../src/styles.css';
import '../src/arrows/arrows.css';

function Preview() {
  const [gain, setGain] = useState(100);
  const kinds = Math.ceil(gain / 10);
  const pool = { ...arrowDemo.soulPool!, capacity: 173, upgradeGain: gain,
    options: [0, 1].map(id => ({ id, materials: Array.from({ length: kinds }, (_, index) => ({
      id: id * 100 + index, name: ['火盐', '死亡钟花', '巨魔脂肪', '苦鱼', '虚无盐', '霜盐', '夜茄', '蓝山花', '发光蘑菇', '紫山花'][index],
      source: index % 2 ? 'Complete Alchemy & Cooking Overhaul.esp' : 'Skyrim.esm',
      count: index + 1, owned: id === 1 ? 10 : 0,
    })) })) };
  return <main style={{ maxWidth: 1000, margin: '24px auto', padding: 16, color: '#d6eee3' }}>
    <label>预览容量增幅 <select value={gain} onChange={event => setGain(Number(event.target.value))}>
      {[1, 10, 11, 20, 21, 90, 91, 100].map(value => <option key={value}>{value}</option>)}
    </select></label>
    <SoulPoolPage state={{ ...arrowDemo, soulPool: pool }} action={() => {}} active />
  </main>;
}
createRoot(document.getElementById('root')!).render(<Preview />);
