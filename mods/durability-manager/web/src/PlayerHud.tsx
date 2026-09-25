import type { PlayerHudSnapshot } from './player-hud';

const combatStats = [
  ['fire', '火焰抗性', 'M12 2C14 8 20 9 19 15a7 7 0 0 1-14 0c0-3 2-5 4-7 0 4 2 5 3 5 2-3 1-7 0-11Z'],
  ['frost', '冰霜抗性', 'M12 2v20M3.3 7l17.4 10M3.3 17 20.7 7M9 4l3 3 3-3M9 20l3-3 3 3'],
  ['shock', '闪电抗性', 'm14 2-10 12h7l-1 8L21 9h-8l1-7Z'],
  ['magic', '魔法抗性', 'm12 2 9 4v6c-1 5-5 8-9 10-4-2-8-5-9-10V6l9-4Zm0 5-2 5 2 5 2-5-2-5Z'],
  ['poison', '毒素抗性', 'M7 17v4h10v-4c3-2 4-4 4-7a9 9 0 0 0-18 0c0 3 1 5 4 7Zm1-7h1m6 0h1m-4 3v2m-2 3v3m4-3v3'],
  ['disease', '疾病抗性', 'M12 2v4m0 12v4M2 12h4m12 0h4M5 5l3 3m8 8 3 3M5 19l3-3m8-8 3-3M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Zm-2 4h.1m4 2h.1m-3 3h.1'],
] as const;
const armorIcon = 'm8 3-6 4 3 5 3-2v11h8V10l3 2 3-5-6-4c-1 4-7 4-8 0Z';
const speedIcon = 'M6 2h8v9c0 2.5 1.5 4 4 4h2a3 3 0 0 1 3 3v2a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-3a3 3 0 0 1 3-3h2V2ZM1 19h22M6 7h8';

function Icon({ path }: { path: string }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={path} /></svg>;
}
const number = (value: number | null) => value === null ? '—' : Math.round(value).toLocaleString('en-US');

export function PlayerHud({ state }: { state: PlayerHudSnapshot }) {
  const progress = state.experience !== null && state.experienceNext !== null && state.experienceNext > 0
    ? Math.min(100, Math.max(0, state.experience / state.experienceNext * 100)) : 0;
  const time = state.gameMinutes === null ? '—' : `${Math.floor(state.gameMinutes / 60).toString().padStart(2, '0')}:${(state.gameMinutes % 60).toString().padStart(2, '0')}`;
  return <section className="player-hud" aria-label="角色状态">
    <div className="player-level" aria-label={`等级 ${state.level}，经验 ${number(state.experience)} / ${number(state.experienceNext)}`}>
      <svg viewBox="0 0 100 100" className="level-diamond" aria-hidden="true">
        <path className="level-fill" d="M50 7 93 50 50 93 7 50Z" />
        <path className="level-inner" d="M50 13 87 50 50 87 13 50Z" />
        <path className="level-track" d="M50 3 97 50 50 97 3 50Z" />
        <path className="level-progress" d="M50 3 97 50 50 97 3 50Z" pathLength="100" strokeDasharray={`${progress} 100`} />
        <text x="50" y="53" dominantBaseline="middle" textAnchor="middle">{state.level}</text>
      </svg>
      <span className="level-experience">{number(state.experience)} / {number(state.experienceNext)}</span>
    </div>
    <div className="player-readouts">
      <div className="player-combat-row">{combatStats.map(([key, label, path]) => <span className="player-stat" key={key} title={label} aria-label={`${label} ${number(state[key])}%`}>
        <Icon path={path} /><span>{number(state[key])}{state[key] !== null && <small>%</small>}</span>
      </span>)}</div>
      <div className="player-utility-row">
        <span className="player-stat" title="移动速度" aria-label={`移动速度 ${number(state.speed)}%`}><Icon path={speedIcon} /><span>{number(state.speed)}{state.speed !== null && <small>%</small>}</span></span>
        <span className="player-stat" title="护甲值" aria-label={`护甲值 ${number(state.armor)}`}><Icon path={armorIcon} /><span>{number(state.armor)}</span></span>
        <span className="player-stat" title="游戏时间" aria-label={`游戏时间 ${time}`}><Icon path="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v5l4 2" /><span>{time}</span></span>
        <span className={`player-stat${state.weight !== null && state.carryWeight !== null && state.weight > state.carryWeight ? ' overloaded' : ''}`} title="负重 / 上限" aria-label={`负重 ${number(state.weight)} / ${number(state.carryWeight)}`}><Icon path="m9 3 3 3 3-3M8 7h8c0 5 5 6 5 11 0 5-18 5-18 0 0-5 5-6 5-11Zm0 0h8" /><span>{number(state.weight)} <small>/ {number(state.carryWeight)}</small></span></span>
        <span className="player-stat" title="金币" aria-label={`金币 ${number(state.gold)}`}><Icon path="M3 6c0-4 18-4 18 0s-18 4-18 0Zm0 0v12c0 4 18 4 18 0V6M3 12c0 4 18 4 18 0" /><span>{number(state.gold)}</span></span>
      </div>
    </div>
  </section>;
}
