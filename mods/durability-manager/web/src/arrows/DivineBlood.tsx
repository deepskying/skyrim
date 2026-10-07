import { useEffect, useId, useRef, useState } from 'react';
import type { WorkshopAction } from '../bridge';
import { nextArrowRequest } from './useArrowBridge';
import type { ArrowState } from './types';

export function DivinePoolStar({ souls, alchemy, capacity }: { souls: number; alchemy: number; capacity: number }) {
  const id = useId().replace(/:/g, '');
  const ratio = (points: number) => capacity > 0 ? Math.max(0, Math.min(1, points / capacity)) : 0;
  return <svg className="divine-pool-star" viewBox="0 0 280 280" aria-label="灵魂与炼金六芒星">
    <defs>
      <filter id={`${id}-glow`} x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" /></filter>
    </defs>
    <circle className="divine-star-orbit" cx="140" cy="140" r="123" />
    <circle className="divine-star-orbit inner" cx="140" cy="140" r="113" />
    <g role="progressbar" aria-label="灵魂池" aria-valuemin={0} aria-valuemax={capacity} aria-valuenow={souls}>
      <polygon className="divine-triangle-track soul" points="140,28 237,196 43,196" />
      <polygon className="divine-triangle-progress soul glow" points="140,28 237,196 43,196" pathLength={100} strokeDasharray="100 100" strokeDashoffset={100 * (1-ratio(souls))} filter={`url(#${id}-glow)`} aria-hidden="true" />
      <polygon className="divine-triangle-progress soul" points="140,28 237,196 43,196" pathLength={100} strokeDasharray="100 100" strokeDashoffset={100 * (1-ratio(souls))} />
    </g>
    <g role="progressbar" aria-label="炼金池" aria-valuemin={0} aria-valuemax={capacity} aria-valuenow={alchemy}>
      <polygon className="divine-triangle-track alchemy" points="140,252 43,84 237,84" />
      <polygon className="divine-triangle-progress alchemy glow" points="140,252 43,84 237,84" pathLength={100} strokeDasharray="100 100" strokeDashoffset={100 * (1-ratio(alchemy))} filter={`url(#${id}-glow)`} aria-hidden="true" />
      <polygon className="divine-triangle-progress alchemy" points="140,252 43,84 237,84" pathLength={100} strokeDasharray="100 100" strokeDashoffset={100 * (1-ratio(alchemy))} />
    </g>
    {[ [140,28], [237,84], [237,196], [140,252], [43,196], [43,84] ].map(([x,y],i)=><circle key={i} className={`divine-star-node ${i%2===0?'soul':'alchemy'}`} cx={x} cy={y} r="5" aria-hidden="true" />)}
  </svg>;
}

export function DivineBloodPage({ state, action, active }: { state: ArrowState; action: WorkshopAction; active: boolean }) {
  const blood = state.divineBlood, soul = state.soulPool;
  const [key, setKey] = useState('health');
  const [selected, setSelected] = useState<Record<number,number>>({});
  const [gemCounts, setGemCounts] = useState<Record<number,number>>({});
  const [pending, setPending] = useState<number>();
  const busy = useRef(false);
  useEffect(() => {
    setSelected({}); setGemCounts({}); setPending(undefined); busy.current = false;
    if (active) action('page', { page: 'divine' });
  }, [active, action]);
  useEffect(() => { setSelected({}); }, [blood?.epoch]);
  useEffect(() => {
    if (!pending || state.workshopReply?.type !== 'divineCraft' || state.workshopReply.requestID !== pending) return;
    if (state.workshopReply.ok) setSelected({});
    setPending(undefined); busy.current = false;
  }, [state.workshopReply, pending]);
  const card = blood?.cards.find(c => c.key === key);
  const materials = blood?.materials.filter(m => (m.points[key] ?? 0) > 0) ?? [];
  const points = materials.reduce((sum,m) => sum + (selected[m.id] ?? 0) * m.points[key], 0);
  const capacity = soul?.capacity ?? 0;
  const valid = materials.every(m => Number.isInteger(selected[m.id] ?? 0) && (selected[m.id] ?? 0) >= 0 && (selected[m.id] ?? 0) <= m.count)
    && Object.keys(selected).every(id => !(selected[Number(id)] > 0) || materials.some(m => m.id === Number(id)));
  const output = card && valid && points <= capacity ? Math.min(Math.floor(points/card.alchemyCost), Math.floor((soul?.points ?? 0)/card.soulCost)) : 0;
  const canCraft = !!blood?.available && !!state.craftingAccess?.alchemy && output > 0 && !pending;
  function craft() {
    if (!canCraft || !card || !blood || busy.current) return;
    busy.current = true;
    const requestID = nextArrowRequest(); setPending(requestID);
    action('divineCraft', { requestID, epoch: blood.epoch, key, alchemyCost: card.alchemyCost, soulCost: card.soulCost, output,
      materials: materials.filter(m => (selected[m.id] ?? 0) > 0).map(m => ({ id:m.id, count:selected[m.id], pointsPerItem:m.points[key] })) });
  }
  return <section className="arrows-page divine-page" hidden={!active}>
    {!blood?.available && <p className="arrow-status">神血插件或灵魂池尚未就绪，请启用模组并重新读档。</p>}
    <p className="divine-select-hint">选择神血 · 共 {blood?.cards.length ?? 0} 种，滚动卡片可查看更多 <button disabled={!!pending} onClick={() => action('refresh')}>同步背包</button></p>
    <div className="divine-cards" aria-label="选择需要炼制的神血">{blood?.cards.map(c => <button key={c.key} disabled={!!pending} className={`divine-card${c.key === key ? ' active' : ''}`} aria-pressed={c.key === key} onClick={() => { setKey(c.key); setSelected({}); }}>
      <img src={`divine-blood/${c.key}.png`} alt="" /><div><b>{c.name}</b><span>{c.gain}</span><small>持有 {c.owned} · 已吸收 {c.absorbed}</small></div>
    </button>)}</div>
    <section className="divine-ritual" aria-label="神血炼制双池">
      <div className="divine-ritual-heading"><span>DIVINE TRANSMUTATION</span><h2>{card?.name ?? '选择神血'}</h2><p>{card?.gain}</p></div>
      <DivinePoolStar souls={soul?.points ?? 0} alchemy={points} capacity={capacity} />
      <div className="divine-pool-readouts">
        <div className="soul"><span><i />灵魂池</span><strong>{soul?.points ?? 0}<small> / {capacity}</small></strong><p>每份 {card?.soulCost ?? '—'} 点 · 保留余量</p></div>
        <div className="alchemy"><span><i />炼金池</span><strong>{points}<small> / {capacity}</small></strong><p>每份 {card?.alchemyCost ?? '—'} 点 · 成功后清空</p></div>
      </div>
    </section>
    <div className="divine-pools">
      <section className="arrow-card divine-soul-materials"><header><div><small>SOUL OFFERINGS</small><h2>灵魂石</h2></div><span className="divine-material-symbol">△</span></header>
        <p className="arrow-muted">选择灵魂石与数量，注入时立即消耗，点数存入共用灵魂池。</p>
        <div className="divine-materials">{soul?.deposit.map(g => {
          const max=Math.max(0,Math.min(g.count,g.room)), count=Math.min(max,gemCounts[g.id] ?? 1);
          return <div key={g.id}><span>{g.name}<small className="divine-material-badges"><span>持有 {g.count}</span><span>每颗 +{g.points} 点</span></small></span><input type="number" min={0} max={max} step={1} disabled={!blood?.available || !!pending || max===0} value={count} aria-label={`${g.name}数量`} onChange={e=>setGemCounts(s=>({...s,[g.id]:Math.min(max,Math.max(0,Math.floor(Number(e.target.value)||0)))}))} /><button className="divine-deposit" disabled={!blood?.available || !!pending || count<1} onClick={() => action('soulDeposit',{id:g.id,count})}>注入 <small>+{count*g.points}</small></button></div>;
        })}</div>
        {!soul?.deposit.length && <p className="arrow-muted">背包中没有可存入的充满灵魂石。</p>}
      </section>
      <section className="arrow-card divine-alchemy-materials"><header><div><small>ALCHEMY OFFERINGS</small><h2>炼金材料</h2></div><span className="divine-material-symbol">▽</span></header>
        <p className="arrow-muted">点数按材料对应效果的强度换算。当前仅选择材料；切换神血或退出会清空选择，炼制成功才消耗。</p>
        {key === 'shout_rec' && <p className="arrow-muted">接受龙吼冷却、魔力恢复材料。</p>}{key === 'speed_mult' && <p className="arrow-muted">接受移动速度、体力材料。</p>}{key === 'damage_resist' && <p className="arrow-muted">接受护甲、格挡材料。</p>}
        <div className="divine-materials">{materials.map(m => <label key={m.id}><span>{m.name}<small className="divine-material-badges"><span>持有 {m.count}</span><span>每个 +{m.points[key]} 点</span></small></span><input type="number" min={0} max={Math.min(m.count,Math.floor((capacity-points+(selected[m.id] ?? 0)*m.points[key])/m.points[key]))} step={1} disabled={!!pending} value={selected[m.id] ?? 0} aria-label={`${m.name}数量`} onChange={e => {const max=Math.max(0,Math.min(m.count,Math.floor((capacity-points+(selected[m.id] ?? 0)*m.points[key])/m.points[key])));const count=Math.min(max,Math.max(0,Math.floor(Number(e.target.value)||0)));setSelected(s=>({...s,[m.id]:count}));}} /></label>)}</div>
        {!materials.length && <p className="arrow-muted">没有适用于当前神血的炼金材料。</p>}
        <button disabled={!!pending || points === 0} onClick={() => setSelected({})}>清空选择</button>
      </section>
    </div>
    {!state.craftingAccess?.alchemy && <p className="arrow-status">请靠近炼金台后炼制神之血。</p>}
    {!valid && <p className="arrow-status">材料库存已变化，请重新选择。</p>}
    {state.message && <p className="arrow-status" role="status">{state.message}</p>}
    <section className="divine-result"><h2>可炼制 <strong>{output}</strong> 份</h2><p className="arrow-muted">消耗所选材料（{points} 点）与 {output*(card?.soulCost ?? 0)} 点灵魂。炼制成功后炼金池清空{output > 0 && points > output*(card?.alchemyCost ?? 0) ? `，舍弃 ${points-output*(card?.alchemyCost ?? 0)} 点余量` : ''}。</p><small>每吸收同类神血 10 份，基础费用增加 10%。</small><button className="divine-craft-button" disabled={!canCraft} onClick={craft}><span aria-hidden="true">✧</span>{pending ? '炼制中…' : `炼制 ${output} 份`}<span aria-hidden="true">✧</span></button></section>
  </section>;
}
