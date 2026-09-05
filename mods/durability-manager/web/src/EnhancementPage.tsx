import { useEffect, useRef, useState } from 'react';
import { cardIcons, cardLabels, confirmationKey, failureDescription } from './enhancement';
import type { EnhancementCard, EquipmentItem, ForgeState, MaterialRequirement } from './types';

export function MaterialList({ materials }: { materials: MaterialRequirement[] }) {
  return <div className="materials">{materials.map((material, index) => <span className={material.owned < material.required ? 'missing' : ''} key={`${material.name}-${index}`}>{material.name}<b>{material.owned} / {material.required}</b></span>)}</div>;
}

function Comparison({ card }: { card: EnhancementCard }) {
  return <table className="enhancement-comparison"><caption>成功后的变化</caption><thead><tr><th>属性</th><th>当前</th><th>强化后</th></tr></thead><tbody>{card.preview.map((row, index) => <tr key={index}><th scope="row">{row.label}</th><td>{row.before}</td><td>{row.after}</td></tr>)}</tbody></table>;
}

export function EnhancementPage({ item, forge, revision, onBack, onAction }: {
  item: EquipmentItem; forge: ForgeState; revision: number; onBack: () => void;
  onAction: (type: string, data: Record<string, unknown>) => void;
}) {
  const [review, setReview] = useState<{ id: string; key: string }>();
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitted = useRef(false);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const cards = forge.cards.filter((card) => card.equipmentId === item.id);
  const offer = cards.find((card) => card.id === review?.id);
  const reviewed = offer && !offer.blockedReason && confirmationKey(item, offer) === review?.key ? offer : undefined;

  useEffect(() => { submitted.current = false; setBusy(false); }, [revision]);
  useEffect(() => { if (review) cancelButton.current?.focus(); }, [review]);
  useEffect(() => {
    if (review && !reviewed) { setReview(undefined); setAcknowledged(false); }
  }, [review, reviewed]);

  const dispatch = (type: string, data: Record<string, unknown>) => {
    if (submitted.current) return;
    submitted.current = true;
    setBusy(true);
    setReview(undefined);
    setAcknowledged(false);
    onAction(type, data);
  };

  return <section className="enhancement-page">
    <header className="enhancement-heading"><button type="button" onClick={onBack}>← 返回装备详情</button><div><p>ENHANCEMENT WORKSHOP</p><h2>{item.name} <span>+{item.enhancementLevel}</span></h2></div><span>{item.quest || item.unique ? '受保护 · 失败降级' : '普通装备 · 失败分解'}</span></header>
    <p className="enhancement-help">三选一，每次只应用一张卡片。查看变化后再确认；取消不会消耗材料，也不会更换卡片。</p>
    <div className="card-heading"><div><h3>本轮强化方案</h3><p>已刷新 {forge.refreshes} 次 · 持有 {forge.gold} 金币</p></div><button disabled={busy || !cards.length || Boolean(reviewed) || forge.gold < forge.refreshCost} onClick={() => dispatch('refreshEnhancements', { id: item.id })} type="button">↻ 更换三张卡 · {forge.refreshCost} 金币</button></div>
    {reviewed ? <section className="enhancement-review" aria-labelledby="review-title">
      <header><p>最后确认 · {reviewed.tier} / {cardLabels[reviewed.type]}</p><h3 id="review-title">{reviewed.title} · {item.name} +{item.enhancementLevel}</h3></header>
      <Comparison card={reviewed} />
      <p>{reviewed.description}</p>
      <h4>本次消耗 <small>持有 / 需要</small></h4><MaterialList materials={reviewed.materials} />
      <div className="enhancement-risk"><strong>成功率 {reviewed.successChance}% · 失败率 {100 - reviewed.successChance}%</strong><p>{failureDescription(item)}</p><p>成功或失败都会消耗上列材料。{reviewed.type === 'enchantment' && '成功后原附魔被整体覆盖，不能通过本面板恢复；需重新装备生效。'}</p></div>
      <label className="risk-acknowledgement"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />我已了解材料消耗、失败后果{reviewed.type === 'enchantment' ? '及附魔覆盖规则' : ''}</label>
      <footer><button ref={cancelButton} onClick={() => { setReview(undefined); setAcknowledged(false); }} type="button">取消，返回卡片</button><button className="confirm-enhancement" disabled={!acknowledged || busy} onClick={() => {
        if (acknowledged && reviewed) dispatch('applyEnhancement', { equipmentId: item.id, cardId: reviewed.id });
      }} type="button">消耗材料并尝试强化</button></footer>
    </section> : <div className="enhancement-cards">{cards.map((card) => <article className={`enhancement-card ${card.type} tier-${card.tier}`} key={card.id}>
      <header><span>{cardIcons[card.type]}</span><small>{cardLabels[card.type]}</small><b>{card.tier}</b></header><h4>{card.title}</h4><strong>{card.value}</strong><p>{card.description}</p>
      <Comparison card={card} /><h5>本次材料 · 持有 / 需要</h5><MaterialList materials={card.materials} />
      <footer><span>成功率 {card.successChance}%<small>失败：{item.quest || item.unique ? '降级' : '分解'}</small></span><button disabled={busy || Boolean(card.blockedReason)} onClick={() => { setAcknowledged(false); setReview({ id: card.id, key: confirmationKey(item, card) }); }} type="button">{card.blockedReason ?? '查看并确认'}</button></footer>
    </article>)}</div>}
    {busy && <p className="card-loading" role="status">正在等待游戏处理，请勿重复操作……</p>}
    {!cards.length && <p className="card-loading">正在同步所选装备的强化卡片……</p>}
    <p className="enhancement-help">预览为成功后的本模组数值。攻击 / 防御不包含技能、药水与其他模组的最终结算；攻速上限为武器基础速度的 2 倍。每次耐久损耗以对应普通动作计。</p>
  </section>;
}
