import { useEffect, useRef, useState } from 'react';
import { cardIcons, cardLabels, confirmationKey, failureDescription } from './enhancement';
import { costLabel, missingCost } from './cost';
import { createRefreshTransition, type RefreshView } from './refresh';
import type { EnhancementCard, EquipmentItem, ForgeState, MaterialRequirement, RefreshResult } from './types';

let refreshSequence = 0;

export function MaterialList({ materials }: { materials: MaterialRequirement[] }) {
  return <div className="materials">{materials.map((material, index) => <span className={material.owned < material.required ? 'missing' : ''} key={`${material.name}-${index}`}>{material.name}<b>{material.owned} / {material.required}</b></span>)}</div>;
}

function Comparison({ card }: { card: EnhancementCard }) {
  return <table className="enhancement-comparison"><caption>成功后的变化</caption><thead><tr><th>属性</th><th>当前</th><th>强化后</th></tr></thead><tbody>{card.preview.map((row, index) => <tr key={index}><th scope="row">{row.label}</th><td>{row.before}</td><td>{row.after}</td></tr>)}</tbody></table>;
}

export function EnhancementPage({ item, forge, revision, refreshResult, backLabel = '返回装备详情', onBack, onAction }: {
  item: EquipmentItem; forge: ForgeState; revision: number; refreshResult?: RefreshResult; backLabel?: string; onBack: () => void;
  onAction: (type: string, data: Record<string, unknown>) => void;
}) {
  const [review, setReview] = useState<{ id: string; key: string }>();
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState<RefreshView>({ phase: 'idle', message: '' });
  const [transition] = useState(() => createRefreshTransition(setRefresh, {
    now: () => Date.now(), set: (callback, delay) => window.setTimeout(callback, delay), clear: (id) => window.clearTimeout(id),
  }));
  const refreshing = refresh.phase !== 'idle';
  const locked = busy || refreshing;
  const submitted = useRef(false);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const cards = forge.cards.filter((card) => card.equipmentId === item.id);
  const offer = cards.find((card) => card.id === review?.id);
  const reviewed = offer && !offer.blockedReason && confirmationKey(item, offer) === review?.key ? offer : undefined;
  const displayedCards = refreshing ? refresh.cards ?? cards : cards;

  useEffect(() => () => transition.dispose(), [transition]);
  useEffect(() => { transition.receive(refreshResult, forge.cards.filter((card) => card.equipmentId === item.id)); }, [transition, refreshResult, forge.cards, item.id]);
  useEffect(() => { submitted.current = false; setBusy(false); }, [revision]);
  useEffect(() => { if (review) cancelButton.current?.focus(); }, [review]);
  useEffect(() => {
    if (review && !reviewed) setReview(undefined);
  }, [review, reviewed]);

  const dispatch = (type: string, data: Record<string, unknown>) => {
    if (submitted.current || transition.isPending()) return;
    submitted.current = true;
    setBusy(true);
    setReview(undefined);
    onAction(type, data);
  };

  return <section className="enhancement-page">
    <header className="enhancement-heading"><button type="button" disabled={locked && refresh.phase !== 'timeout'} onClick={() => { onAction('playWorkshopClick', {}); onBack(); }}>← {backLabel}</button><div><p>ENHANCEMENT WORKSHOP</p><h2>{item.name} <span>+{item.enhancementLevel}</span></h2></div><span>{item.quest || item.unique ? '受保护 · 失败降级' : '普通装备 · 失败分解'}</span></header>
    <p className="enhancement-help">三选一，每次只应用一张卡片。查看变化后再确认；取消不会消耗金币或材料，也不会更换卡片。已装备物品会临时卸下，成功后恢复原槽位。</p>
    <div className="card-heading"><div><h3>本轮强化方案</h3><p>已刷新 {forge.refreshes} 次 · 持有 {forge.gold} 金币</p></div><button disabled={locked || !cards.length || Boolean(reviewed) || forge.gold < forge.refreshCost} onClick={() => {
      if (busy || transition.isPending()) return;
      const requestId = `refresh-${Date.now()}-${++refreshSequence}`;
      if (transition.start(requestId, item.id, cards)) onAction('refreshEnhancements', { id: item.id, requestId });
    }} type="button">{refreshing ? '↻ 刷新中…' : `↻ 更换三张卡 · ${forge.refreshCost} 金币${forge.gold < forge.refreshCost ? '（金币不足）' : ''}`}</button></div>
    {refresh.message && <p className={`refresh-feedback ${refresh.failed ? 'failed' : ''}`} role="status" aria-live="polite">{refresh.message}</p>}
    {reviewed ? <section className="enhancement-review" aria-labelledby="review-title">
      <header><p>最后确认 · {reviewed.tier} / {cardLabels[reviewed.type]}</p><h3 id="review-title">{reviewed.title} · {item.name} +{item.enhancementLevel}</h3></header>
      <Comparison card={reviewed} />
      <p>{reviewed.description}</p>
      <h4>本次消耗 <small>持有 / 需要</small></h4><MaterialList materials={reviewed.materials} />
      <div className="enhancement-risk"><strong>成功率 {reviewed.successChance}% · 失败率 {100 - reviewed.successChance}%</strong><p>{failureDescription(item)}</p><p>成功或失败都会消耗上列金币和材料。{reviewed.type === 'enchantment' && '成功后原附魔被整体覆盖，不能通过本面板恢复；成功后自动恢复原装备槽位；恢复失败时请手动装备。'}</p></div>
      <footer><button ref={cancelButton} onClick={() => setReview(undefined)} type="button">取消，返回卡片</button><button className="confirm-enhancement" disabled={locked || Boolean(missingCost(reviewed.materials))} onClick={() => {
        if (reviewed && !locked && !missingCost(reviewed.materials)) dispatch('applyEnhancement', { equipmentId: item.id, cardId: reviewed.id });
      }} type="button">尝试强化 · {costLabel(reviewed.materials)}</button></footer>
    </section> : <div className={`enhancement-cards refresh-${refresh.phase}`} aria-busy={refreshing}>{displayedCards.map((card) => <article className={`enhancement-card ${card.type} tier-${card.tier}`} key={`${refresh.phase === 'revealing' ? refreshResult?.requestId : 'card'}-${card.id}`}>
      <header><span>{cardIcons[card.type]}</span><small>{cardLabels[card.type]}</small><b>{card.tier}</b></header><h4>{card.title}</h4><strong>{card.value}</strong><p>{card.description}</p>
      <Comparison card={card} /><h5>本次材料 · 持有 / 需要</h5><MaterialList materials={card.materials} />
      <footer><span>成功率 {card.successChance}%<small>失败：{item.quest || item.unique ? '降级' : '分解'}</small></span><button disabled={locked || Boolean(card.blockedReason) || Boolean(missingCost(card.materials))} onClick={() => { if (transition.isPending()) return; onAction('playWorkshopClick', {}); setReview({ id: card.id, key: confirmationKey(item, card) }); }} type="button">{missingCost(card.materials) ?? card.blockedReason ?? '查看并确认'} · {costLabel(card.materials)}</button></footer>
    </article>)}</div>}
    {busy && <p className="card-loading" role="status">正在等待游戏处理，请勿重复操作……</p>}
    {!cards.length && <p className="card-loading">正在同步所选装备的强化卡片……</p>}
    <p className="enhancement-help">预览为成功后的本模组数值。攻击 / 防御不包含技能、药水与其他模组的最终结算；攻速上限为武器基础速度的 2 倍。每次耐久损耗以对应普通动作计。</p>
  </section>;
}
