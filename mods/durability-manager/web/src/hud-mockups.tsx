// Dev-only page (vite build only reads index.html): open /hud-mockups.html for a bolder set
// of full bottom-left HUD directions. Each panel carries the same data: character core
// (level, XP, six resistances, armour/speed/clock/weight/gold), craft queue, soul pool and
// equipment durability.
import { StrictMode, type CSSProperties, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';

const stats = { level: 21, experience: 321, experienceNext: 600, resist: [['火焰', 0], ['冰霜', 50], ['闪电', 0], ['魔法', 25], ['毒素', 0], ['疾病', 0]] as const, armor: 1875, speed: 100, gameMinutes: 953, weight: 851, carryWeight: 800, gold: 44735 };
const queue = [{ name: '奥术箭·火球术', label: '12', total: 12, remaining: 12, family: '#eca979' }, { name: '奥术箭·冰锥术', label: '1.5K', total: 4500, remaining: 1500, family: '#84cadb' }];
const pool = { points: 12, capacity: 20, tier: 1 };
const equipped = [{ slot: '右手', name: '寒汐·处女', current: 27, maximum: 100 }, { slot: '左手', name: '月光之刃', current: 86, maximum: 100 }];
const clock = `${String(Math.floor(stats.gameMinutes / 60)).padStart(2, '0')}:${String(stats.gameMinutes % 60).padStart(2, '0')}`;
const integer = new Intl.NumberFormat('en-US');
const number: CSSProperties = { fontVariantNumeric: 'tabular-nums' };

// ---------------------------------------------------------------------------
// E - instrument bar: a radial core, a hexagon radar for the resistances, and two
// stacked readouts. Everything in one row, no list of rows.
function CoreRadar() {
  const accent = '#a9e6d2';
  const radarCenter = 62, radarRadius = 46;
  const point = (index: number, ratio: number) => {
    const angle = -Math.PI / 2 + index * Math.PI / 3;
    return [radarCenter + Math.cos(angle) * radarRadius * ratio, radarCenter + Math.sin(angle) * radarRadius * ratio];
  };
  const polygon = (ratio: number) => stats.resist.map((_, index) => point(index, ratio).map(value => value.toFixed(1)).join(',')).join(' ');
  const shape = stats.resist.map(([, value], index) => point(index, Math.max(.08, value / 50)).map(value => value.toFixed(1)).join(',')).join(' ');
  const xp = stats.experience / stats.experienceNext;
  const poolRatio = pool.points / pool.capacity;
  return <div id="style-e" style={{ width: 600, display: 'flex', alignItems: 'stretch', gap: 0, borderRadius: 16, border: '1px solid #9fd8c42e', background: 'linear-gradient(150deg,#101c21f7,#070c0ef7)', boxShadow: '0 14px 32px #00000080, inset 0 1px 0 #ffffff14', color: '#e8f1ee', fontFamily: '"Segoe UI","Microsoft YaHei",sans-serif', textShadow: '0 1px 3px #000', overflow: 'hidden' }}>
    <div style={{ position: 'relative', width: 132, display: 'grid', placeItems: 'center', background: 'radial-gradient(circle at 35% 30%, #9fd8c41f, transparent 70%)' }}>
      <svg viewBox="0 0 120 120" width={112} height={112}>
        <circle cx="60" cy="60" r="46" fill="#0a1418" stroke="#9fd8c426" strokeWidth="1" />
        <circle cx="60" cy="60" r="46" fill="none" stroke={accent} strokeWidth="6" strokeLinecap="round" pathLength={100} strokeDasharray={`${xp * 100} 100`} transform="rotate(-90 60 60)" />
        <circle cx="60" cy="60" r="36" fill="none" stroke="#9fd8c41f" strokeWidth="1" />
        <text x="60" y="58" textAnchor="middle" fill="#ffffff" fontSize="38" style={number}>{stats.level}</text>
        <text x="60" y="80" textAnchor="middle" fill="#9fb0ac" fontSize="12" style={number}>{stats.experience}/{stats.experienceNext}</text>
      </svg>
    </div>
    <div style={{ position: 'relative', width: 168, display: 'grid', placeItems: 'center', borderLeft: '1px solid #ffffff14' }}>
      <svg viewBox="0 0 124 124" width={140} height={140}>
        {[.35, .7, 1].map(ratio => <polygon key={ratio} points={polygon(ratio)} fill="none" stroke="#9fd8c41f" strokeWidth="1" />)}
        {stats.resist.map((_, index) => { const [x, y] = point(index, 1); return <line key={index} x1="62" y1="62" x2={x} y2={y} stroke="#9fd8c41a" />; })}
        <polygon points={shape} fill="#9fd8c42e" stroke={accent} strokeWidth="2" />
        {stats.resist.map(([name, value], index) => { const [x, y] = point(index, 1.28); return <text key={name} x={x} y={y + 4} textAnchor="middle" fill={value ? '#cfeee3' : '#7f918c'} fontSize="11">{name}{value}</text>; })}
      </svg>
    </div>
    <div style={{ flex: 1, display: 'grid', alignContent: 'center', gap: 12, padding: '16px 18px', borderLeft: '1px solid #ffffff14' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, fontSize: 12 }}>
        {[['护甲', integer.format(stats.armor)], ['移速', `${stats.speed}%`], ['时刻', clock], ['负重', `${stats.weight}/${stats.carryWeight}`], ['金币', integer.format(stats.gold)]].map(([name, value]) => <span key={name}><span style={{ opacity: .6 }}>{name} </span><b style={{ ...number, color: '#dcf2ea' }}>{value}</b></span>)}
      </div>
      <div style={{ display: 'flex', gap: 10 }}>
        {queue.map(entry => <span key={entry.name} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12 }}>
          <svg viewBox="0 0 100 100" width={30} height={30}><path d="M50 3 97 50 50 97 3 50Z" fill="#0d222a" stroke={entry.family} strokeWidth="2" /><path d="M50 3 97 50 50 97 3 50Z" fill="none" stroke={entry.family} strokeWidth="5" pathLength={100} strokeDasharray={`${entry.remaining / entry.total * 100} 100`} /><text x="50" y="54" textAnchor="middle" dominantBaseline="middle" fill="#eaf6f2" fontSize="30">{entry.label}</text></svg>
          <span style={{ opacity: .82 }}>{entry.name}</span>
        </span>)}
      </div>
      <div style={{ display: 'grid', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', fontSize: 12 }}><span>灵魂池</span><small style={{ marginLeft: 8, opacity: .6 }}>{pool.tier} 级 · 上限 {pool.capacity}</small><b style={{ ...number, marginLeft: 'auto', color: accent }}>{pool.points} / {pool.capacity}</b></div>
        <div style={{ height: 9, background: '#0a141a', border: '1px solid #9fd8c426', borderRadius: 999, overflow: 'hidden' }}><i style={{ display: 'block', height: '100%', width: `${poolRatio * 100}%`, background: `linear-gradient(90deg,#6bbf9f,${accent})` }} /></div>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {equipped.map(item => <div key={item.slot} style={{ display: 'flex', alignItems: 'center', gap: 9, fontSize: 12 }}>
          <span style={{ width: 92, opacity: .68 }}>{item.slot} {item.name}</span>
          <div style={{ flex: 1, height: 5, background: '#0a141a', border: '1px solid #ffffff14', borderRadius: 999, overflow: 'hidden' }}><i style={{ display: 'block', height: '100%', width: `${item.current}%`, background: item.current < 40 ? 'linear-gradient(90deg,#c98b63,#ecc19a)' : 'linear-gradient(90deg,#6bbf9f,#a9e6d2)' }} /></div>
          <b style={{ ...number, color: item.current < 40 ? '#e8b98d' : '#d8ece5', width: 62, textAlign: 'right' }}>{item.current.toFixed(1)}</b>
        </div>)}
      </div>
    </div>
  </div>;
}

// ---------------------------------------------------------------------------
// F - angled tech: clipped corners, scanlines, monospace digits, hazard stripes.
function Angled() {
  const accent = '#7fe6d5';
  const mono = 'Consolas,"Cascadia Mono",monospace';
  const clip = 'polygon(0 0, calc(100% - 30px) 0, 100% 30px, 100% 100%, 26px 100%, 0 calc(100% - 26px))';
  return <div id="style-f" style={{ width: 600, position: 'relative', color: '#dff3ef', fontFamily: mono, textShadow: '0 0 6px #000' }}>
    <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(140deg,${accent}80,#0e2a2a00 55%)`, clipPath: clip }} />
    <div style={{ position: 'relative', margin: 2, padding: '14px 18px 16px', background: 'repeating-linear-gradient(0deg,#0a1417f2,#0a1417f2 3px,#0c181bf2 3px,#0c181bf2 6px)', clipPath: clip }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ position: 'relative', width: 64, height: 58, display: 'grid', placeItems: 'center', clipPath: 'polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%)', background: '#0f2b2b', border: `1px solid ${accent}66` }}>
          <b style={{ ...number, fontSize: 28, color: '#ffffff' }}>{stats.level}</b>
          <i style={{ position: 'absolute', inset: 3, clipPath: 'polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%)', border: `1px solid ${accent}33` }} />
        </div>
        <div style={{ display: 'grid', gap: 6, flex: 1 }}>
          <div style={{ display: 'flex', gap: 12, fontSize: 12, letterSpacing: 1 }}>
            {stats.resist.map(([name, value]) => <span key={name} style={{ color: value ? accent : '#6f8580' }}>{name}<b style={{ ...number, color: value ? '#eafff9' : '#7d918c' }}>{String(value).padStart(2, '0')}</b></span>)}
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: 12 }}>
            {[['ARM', integer.format(stats.armor)], ['SPD', `${stats.speed}`], ['T', clock], ['W', `${stats.weight}/${stats.carryWeight}`], ['G', integer.format(stats.gold)]].map(([name, value]) => <span key={name} style={{ color: '#8fb0aa' }}>{name} <b style={{ ...number, color: '#dff3ef' }}>{value}</b></span>)}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#8fb0aa' }}>
            XP<div style={{ flex: 1, height: 4, background: '#08110f', border: `1px solid ${accent}33` }}><i style={{ display: 'block', height: '100%', width: `${stats.experience / stats.experienceNext * 100}%`, background: accent }} /></div>{stats.experience}/{stats.experienceNext}
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 13, paddingTop: 11, borderTop: `1px solid ${accent}26`, fontSize: 12 }}>
        <span style={{ letterSpacing: 2, color: accent }}>QUEUE</span>
        {queue.map(entry => <span key={entry.name} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <svg viewBox="0 0 100 100" width={30} height={30}><path d="M50 4 96 50 50 96 4 50Z" fill="#0b1a1c" stroke={entry.family} strokeWidth="3" /><path d="M50 4 96 50 50 96 4 50Z" fill="none" stroke={entry.family} strokeWidth="7" pathLength={100} strokeDasharray={`${entry.remaining / entry.total * 100} 100`} /><text x="50" y="55" textAnchor="middle" dominantBaseline="middle" fill="#eaf6f2" fontSize="30">{entry.label}</text></svg>
          <span style={{ color: '#a8c4be' }}>{entry.name}</span>
        </span>)}
      </div>
      <div style={{ marginTop: 12, fontSize: 12 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', letterSpacing: 2 }}>
          <span style={{ color: accent }}>SOUL POOL</span>
          <small style={{ marginLeft: 10, color: '#8fb0aa' }}>TIER {pool.tier} / CAP {pool.capacity}</small>
          <b style={{ ...number, marginLeft: 'auto', color: '#eafff9' }}>{pool.points} / {pool.capacity}</b>
        </div>
        <div style={{ display: 'flex', gap: 3, marginTop: 7 }}>
          {Array.from({ length: 20 }, (_, index) => <i key={index} style={{ flex: 1, height: 8, background: index < pool.points ? accent : '#08110f', border: `1px solid ${index < pool.points ? accent : accent + '22'}`, boxShadow: index < pool.points ? `0 0 6px ${accent}66` : 'none' }} />)}
        </div>
      </div>
      <div style={{ display: 'grid', gap: 9, marginTop: 12 }}>
        {equipped.map(item => <div key={item.slot} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
          <span style={{ width: 108, color: '#a8c4be' }}>{item.slot} {item.name}</span>
          <div style={{ flex: 1, height: 7, background: item.current < 40 ? 'repeating-linear-gradient(45deg,#2a1a12,#2a1a12 5px,#3a2418 5px,#3a2418 10px)' : '#08110f', border: `1px solid ${item.current < 40 ? '#c98b6366' : accent + '26'}` }}><i style={{ display: 'block', height: '100%', width: `${item.current}%`, background: item.current < 40 ? 'repeating-linear-gradient(45deg,#e0a880,#e0a880 5px,#f3d0b3 5px,#f3d0b3 10px)' : accent }} /></div>
          <b style={{ ...number, color: item.current < 40 ? '#e8b98d' : '#eafff9' }}>{item.current.toFixed(1)}%</b>
        </div>)}
      </div>
    </div>
  </div>;
}

// ---------------------------------------------------------------------------
// G - ink scroll: paper, brush stroke, a red seal, vertical caption.
function InkScroll() {
  const ink = '#2f2a25';
  const Heading = ({ children }: { children: ReactNode }) => <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '12px 0 6px' }}>
    <b style={{ fontSize: 15, letterSpacing: 4 }}>{children}</b>
    <i style={{ flex: 1, height: 2, background: `linear-gradient(90deg,${ink}66,${ink}00)` }} />
  </div>;
  return <div id="style-g" style={{ width: 600, display: 'flex', color: ink, background: 'radial-gradient(circle at 20% 15%,#f6efdd,#e3d8bd 60%,#d6c9aa)', borderRadius: 4, border: '1px solid #9a8460', boxShadow: '0 12px 28px #00000073', fontFamily: '"KaiTi","Songti SC",Georgia,serif', overflow: 'hidden' }}>
    <svg viewBox="0 0 80 320" width={54} height="100%" preserveAspectRatio="none" style={{ flex: '0 0 auto' }}>
      <path d="M40 0c14 40-16 68 2 108s-18 74 2 116-10 70 4 96h-46c-8-40 14-70-2-112s18-72-2-110 12-70-2-98z" fill="#2f2a25" opacity=".9" />
      <text x="26" y="160" fill="#efe6d2" fontSize="18" textAnchor="middle" style={{ writingMode: 'vertical-rl' as never }}>灵 魂 池</text>
    </svg>
    <div style={{ flex: 1, padding: '14px 18px 16px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <svg viewBox="0 0 100 100" width={58} height={58}><path d="M50 4 96 50 50 96 4 50Z" fill="#efe6d2" stroke={ink} strokeWidth="3" /><text x="50" y="56" textAnchor="middle" dominantBaseline="middle" fill={ink} fontSize="30" style={number}>{stats.level}</text></svg>
        <div style={{ display: 'grid', gap: 6, flex: 1, fontSize: 13 }}>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>{stats.resist.map(([name, value]) => <span key={name}>{name} <b style={number}>{value}%</b></span>)}</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', opacity: .85 }}>{[['护甲', integer.format(stats.armor)], ['速度', `${stats.speed}%`], ['时刻', clock], ['负重', `${stats.weight}/${stats.carryWeight}`], ['金币', integer.format(stats.gold)]].map(([name, value]) => <span key={name}>{name} <b style={number}>{value}</b></span>)}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>经验 {stats.experience}/{stats.experienceNext}<div style={{ flex: 1, height: 6, background: '#cbbb98', border: `1px solid ${ink}33` }}><i style={{ display: 'block', height: '100%', width: `${stats.experience / stats.experienceNext * 100}%`, background: '#5f5a4a' }} /></div></div>
        </div>
        <div style={{ width: 42, height: 42, border: '3px solid #a8402f', color: '#a8402f', display: 'grid', placeItems: 'center', fontSize: 22, fontWeight: 700 }}>魂</div>
      </div>
      <Heading>制作队列</Heading>
      <div style={{ display: 'flex', gap: 20 }}>
        {queue.map(entry => <div key={entry.name} style={{ display: 'grid', gap: 4, justifyItems: 'center', fontSize: 13 }}>
          <svg viewBox="0 0 100 100" width={40} height={40}><path d="M50 4 96 50 50 96 4 50Z" fill="#efe6d2" stroke={ink} strokeWidth="2" /><path d="M50 4 96 50 50 96 4 50Z" fill="none" stroke="#7a6f57" strokeWidth="5" pathLength={100} strokeDasharray={`${entry.remaining / entry.total * 100} 100`} /><text x="50" y="55" textAnchor="middle" dominantBaseline="middle" fill={ink} fontSize="28">{entry.label}</text></svg>
          {entry.name}
        </div>)}
      </div>
      <Heading>灵魂池</Heading>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
        <div style={{ flex: 1, height: 12, background: '#cbbb98', border: `1px solid ${ink}44`, borderRadius: 2, overflow: 'hidden' }}><i style={{ display: 'block', height: '100%', width: `${pool.points / pool.capacity * 100}%`, background: 'linear-gradient(90deg,#4c4638,#7f8f6d)' }} /></div>
        <b style={number}>{pool.points} / {pool.capacity}</b><span style={{ opacity: .7, fontSize: 12 }}>{pool.tier} 级上限</span>
      </div>
      <Heading>当前装备耐久</Heading>
      {equipped.map(item => <div key={item.slot} style={{ display: 'grid', gap: 5, marginBottom: 7, fontSize: 13 }}>
        <div style={{ display: 'flex' }}><span>{item.slot} {item.name}</span><b style={{ ...number, marginLeft: 'auto', color: item.current < 40 ? '#a8402f' : ink }}>{item.current.toFixed(1)} / {item.maximum.toFixed(1)}</b></div>
        <div style={{ height: 8, background: '#cbbb98', border: `1px solid ${ink}33` }}><i style={{ display: 'block', height: '100%', width: `${item.current}%`, background: item.current < 40 ? '#a8402f' : '#5f7a5a' }} /></div>
      </div>)}
    </div>
  </div>;
}

// ---------------------------------------------------------------------------
// H - editorial: huge numbers, tiny captions, colour bands instead of chrome.
function Editorial() {
  const accent = '#8fe0c8';
  const Row = ({ name, value, unit, size = 30, color = '#f2fbf8' }: { name: string; value: string; unit?: string; size?: number; color?: string }) => <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
    <b style={{ ...number, fontSize: size, lineHeight: 1, color }}>{value}</b>
    {unit && <small style={{ fontSize: 11, letterSpacing: 2, color: '#8fa8a2' }}>{unit}</small>}
    <small style={{ marginLeft: 'auto', fontSize: 11, letterSpacing: 2, color: '#8fa8a2' }}>{name}</small>
  </div>;
  return <div id="style-h" style={{ width: 600, padding: '0 0 2px', color: '#f2fbf8', background: 'linear-gradient(160deg,#0b1418f7,#05090af7)', borderTop: `2px solid ${accent}`, fontFamily: '"Segoe UI","Microsoft YaHei",sans-serif', textShadow: '0 1px 3px #000', boxShadow: '0 14px 30px #00000080' }}>
    <div style={{ display: 'grid', gridTemplateColumns: '132px 1fr', gap: 20, padding: '16px 20px 14px' }}>
      <div>
        <Row name="等级" value={String(stats.level)} size={54} />
        <div style={{ marginTop: 8, height: 4, background: '#0a1418', border: '1px solid #8fe0c826' }}><i style={{ display: 'block', height: '100%', width: `${stats.experience / stats.experienceNext * 100}%`, background: accent }} /></div>
        <small style={{ display: 'block', marginTop: 6, fontSize: 11, color: '#8fa8a2' }}>经验 {stats.experience} / {stats.experienceNext}</small>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 22px', alignContent: 'start' }}>
        {stats.resist.map(([name, value]) => <Row key={name} name={name} value={`${value}%`} size={22} color={value ? '#e9fff7' : '#7e9892'} />)}
      </div>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 1, background: '#ffffff12', borderTop: '1px solid #ffffff12' }}>
      {[['护甲', integer.format(stats.armor)], ['移速', `${stats.speed}%`], ['时刻', clock], ['负重', `${stats.weight}/${stats.carryWeight}`], ['金币', integer.format(stats.gold)]].map(([name, value]) => <div key={name} style={{ background: '#08100f', padding: '10px 12px' }}>
        <small style={{ display: 'block', fontSize: 10, letterSpacing: 2, color: '#8fa8a2' }}>{name}</small>
        <b style={{ ...number, fontSize: 18 }}>{value}</b>
      </div>)}
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 20px 12px' }}>
      <div style={{ display: 'flex', gap: 16 }}>
        {queue.map(entry => <div key={entry.name} style={{ display: 'grid', gap: 3 }}>
          <b style={{ ...number, fontSize: 26, color: entry.family, lineHeight: 1 }}>{entry.label}</b>
          <small style={{ fontSize: 10, letterSpacing: 1, color: '#8fa8a2' }}>{entry.name}</small>
        </div>)}
      </div>
      <div style={{ flex: 1, display: 'grid', gap: 5 }}>
        <div style={{ display: 'flex', alignItems: 'baseline' }}><small style={{ fontSize: 11, letterSpacing: 2, color: '#8fa8a2' }}>灵魂池 · {pool.tier} 级上限</small><b style={{ ...number, marginLeft: 'auto', fontSize: 22, color: accent }}>{pool.points} / {pool.capacity}</b></div>
        <div style={{ height: 10, background: '#0a1418', border: '1px solid #8fe0c826' }}><i style={{ display: 'block', height: '100%', width: `${pool.points / pool.capacity * 100}%`, background: `linear-gradient(90deg,#5fb99b,${accent})` }} /></div>
      </div>
    </div>
    {equipped.map(item => <div key={item.slot} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '4px 12px', padding: '10px 20px', background: item.current < 40 ? 'linear-gradient(90deg,#e0a88026,transparent)' : 'linear-gradient(90deg,#8fe0c814,transparent)', borderTop: '1px solid #ffffff10' }}>
      <small style={{ fontSize: 11, letterSpacing: 1, color: '#9fb8b2' }}>{item.slot} {item.name}</small>
      <b style={{ ...number, fontSize: 20, color: item.current < 40 ? '#e8b98d' : '#e9fff7' }}>{item.current.toFixed(0)}<small style={{ fontSize: 11, color: '#8fa8a2' }}> / {item.maximum.toFixed(0)}</small></b>
      <div style={{ gridColumn: '1 / -1', height: 5, background: '#0a1418' }}><i style={{ display: 'block', height: '100%', width: `${item.current}%`, background: item.current < 40 ? 'linear-gradient(90deg,#c98b63,#ecc19a)' : `linear-gradient(90deg,#5fb99b,${accent})` }} /></div>
    </div>)}
  </div>;
}

const caption: CSSProperties = { margin: '0 0 8px', fontSize: 13, letterSpacing: 1, color: '#9fb0ac' };

// Queue marker shapes side by side: the shipped diamond ring and the square trial.
function QueueShapes() {
  const rowStyle: CSSProperties = { display: 'flex', alignItems: 'flex-start', gap: 22, padding: '2px 0 6px' };
  const entryStyle: CSSProperties = { width: 76, textAlign: 'center' };
  const text: CSSProperties = { fill: '#f3eee3', fontFamily: 'Consolas,"Cascadia Mono",monospace', fontSize: 24, fontWeight: 600 };
  return <div style={{ display: 'grid', gap: 14, width: 600 }}>
    <div style={rowStyle}>
      <span style={{ fontSize: 13, letterSpacing: 1, width: 96, color: '#9fb0ac' }}>菱形（当前）</span>
      {queue.map(entry => <div key={entry.name} style={entryStyle}>
        <svg viewBox="0 0 100 100" width={54} height={54} style={{ display: 'block', margin: '0 auto' }}>
          <path d="M50 7 93 50 50 93 7 50Z" fill="rgba(0,0,0,.55)" />
          <path d="M50 3 97 50 50 97 3 50Z" fill="none" stroke="rgba(235,229,213,.22)" strokeWidth="3.5" />
          <path d="M50 3 97 50 50 97 3 50Z" fill="none" stroke={entry.family} strokeWidth="3.5" pathLength={100} strokeDasharray={`${entry.remaining / entry.total * 100} 100`} />
          <text x="50" y="53" textAnchor="middle" dominantBaseline="middle" style={text}>{entry.label}</text>
        </svg>
        <span style={{ fontSize: 11, opacity: .72, display: 'block', marginTop: 4 }}>{entry.name}</span>
      </div>)}
    </div>
    <div style={rowStyle}>
      <span style={{ fontSize: 13, letterSpacing: 1, width: 96, color: '#9fb0ac' }}>方形（试作）</span>
      {queue.map(entry => <div key={entry.name} style={entryStyle}>
        <svg viewBox="0 0 100 100" width={54} height={54} style={{ display: 'block', margin: '0 auto' }}>
          <rect x="11" y="11" width="78" height="78" fill="rgba(0,0,0,.55)" />
          <rect x="4" y="4" width="92" height="92" fill="none" stroke="rgba(235,229,213,.22)" strokeWidth="3.5" />
          <rect x="4" y="4" width="92" height="92" fill="none" stroke={entry.family} strokeWidth="3.5" pathLength={100} strokeDasharray={`${entry.remaining / entry.total * 100} 100`} />
          <text x="50" y="53" textAnchor="middle" dominantBaseline="middle" style={text}>{entry.label}</text>
        </svg>
        <span style={{ fontSize: 11, opacity: .72, display: 'block', marginTop: 4 }}>{entry.name}</span>
      </div>)}
    </div>
  </div>;
}

function Page() {
  return <div style={{ padding: 28, display: 'grid', gap: 34, background: '#04080a', minHeight: '100vh' }}>
    <div><p style={caption}>队列标记：菱形（当前）对比方形（试作）——外框描边显示剩余比例</p><QueueShapes /></div>
    <div><p style={caption}>E · 环形核心 + 六边形雷达：等级在环里，抗性画成雷达多边形</p><CoreRadar /></div>
    <div><p style={caption}>F · 切角硬朗：斜切边 + 扫描线 + 等宽数字，灵魂池二十格刻度，受损装备走警示斜纹</p><Angled /></div>
    <div><p style={caption}>G · 水墨卷轴：纸面 + 笔触 + 印章 + 竖排标题</p><InkScroll /></div>
    <div><p style={caption}>H · 大字号排版：巨型数字 + 微小标签 + 色带分区，没有外框</p><Editorial /></div>
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><Page /></StrictMode>);
