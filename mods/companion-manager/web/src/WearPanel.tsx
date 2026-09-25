import {useEffect,useMemo,useRef,useState,type KeyboardEvent as ReactKeyboardEvent} from "react";
import type {GameFollower} from "./bridge";
import {armorTypeNames} from "./behavior";
import {canToggle,nextSelection,searchWear,wearIcon,wearOutcome,wearRows,wearSlotNames,type WearRow} from "./wear";
import {ModelPreview} from "./ModelPreview";
import "./outfits.css";

type Props={f:GameFollower;enabled:boolean;pending:boolean;command:(op:string,data?:Record<string,unknown>)=>boolean};

// The wear page lists the companion's whole apparel half at once - no slot grid, no category tabs -
// and turns one click into one equip or unequip. Hovering and the arrow keys only move the preview;
// nothing is sent until the player clicks a row or presses Enter on it.
export function WearPanel({f,enabled,pending,command}:Props){
  const rows=useMemo(()=>wearRows(f.wardrobe),[f.wardrobe]);
  const [query,setQuery]=useState(""),[selectedKey,setSelectedKey]=useState(""),[hovered,setHovered]=useState("");
  // The 3D model follows the preview slowly on purpose: sweeping the mouse across the list must not
  // queue one nif load per row, while the attribute pane can answer instantly.
  const [modelId,setModelId]=useState("");
  const list=useRef<HTMLDivElement>(null);
  const shown=useMemo(()=>searchWear(rows,query),[rows,query]);
  const usable=enabled&&!f.dead&&!f.unavailable&&!f.inCombat&&f.group==="party"&&!pending;
  const blocked=(row:WearRow)=>!usable||!canToggle(row);
  const toggle=(row:WearRow|undefined)=>{if(row&&!blocked(row))command("toggleWear",{actorId:f.id,itemKey:row.key});};
  useEffect(()=>{
    if(!shown.some(row=>row.key===selectedKey))setSelectedKey(shown.length?shown[0].key:"");
  },[shown,selectedKey]);
  useEffect(()=>{
    list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({block:"nearest"});
  },[selectedKey]);
  // Hovering previews without committing; leaving the list falls back to the selected row.
  const preview=shown.find(row=>row.key===hovered)??shown.find(row=>row.key===selectedKey)??shown[0];
  const outcome=preview?wearOutcome(rows,preview):null;
  const delta=outcome?outcome.delta:0;
  useEffect(()=>{
    const timer=window.setTimeout(()=>setModelId(preview?.id??""),180);
    return ()=>window.clearTimeout(timer);
  },[preview?.id]);
  // Using the keyboard takes the preview back from the pointer, so the highlighted row and the
  // row Enter acts on never disagree.
  const move=(step:number)=>{
    setHovered("");
    if(!shown.length)return;
    const index=shown.findIndex(row=>row.key===selectedKey);
    setSelectedKey(shown[nextSelection(index,shown.length,step)].key);
  };
  const onKey=(e:ReactKeyboardEvent)=>{
    if(e.repeat||e.nativeEvent.isComposing)return;
    if(e.key==="ArrowDown"){e.preventDefault();move(1);}
    else if(e.key==="ArrowUp"){e.preventDefault();move(-1);}
    else if(e.key==="Home"){e.preventDefault();setHovered("");if(shown.length)setSelectedKey(shown[0].key);}
    else if(e.key==="End"){e.preventDefault();setHovered("");if(shown.length)setSelectedKey(shown[shown.length-1].key);}
    else if(e.key==="Enter"){e.preventDefault();toggle(preview);}
  };
  return <div className="cm-wear">
    <div className="cm-wear-list-pane">
      <div className="cm-wear-search">
        <input aria-label="搜索随从装备" placeholder="搜索装备…" value={query} onChange={e=>setQuery(e.target.value)}
          onKeyDown={e=>{if(e.key!=="ArrowDown"&&e.key!=="ArrowUp")return;e.preventDefault();list.current?.focus();move(e.key==="ArrowDown"?1:-1);}}/>
        <small>{shown.length} / {rows.length} 件服饰</small>
      </div>
      <div className="cm-wear-list" role="listbox" aria-label="随从装备" tabIndex={0} ref={list} onKeyDown={onKey} onMouseLeave={()=>setHovered("")}>
        <div className="cm-wear-head" aria-hidden="true"><span>名称</span><span>数量</span><span>重量</span><span>价值</span></div>
        {shown.map(row=>{const icon=wearIcon(row);return <div key={row.key} role="option" aria-selected={row.key===selectedKey} aria-disabled={blocked(row)}
          className={`cm-wear-row${row.equipped?" is-worn":""}${row.favorite?" is-favorite":""}${preview?.key===row.key?" is-preview":""}`}
          onMouseEnter={()=>setHovered(row.key)} onClick={()=>{setSelectedKey(row.key);toggle(row);}}>
          <span className="cm-wear-name"><i className={`cm-wear-icon is-${icon.tone}`} aria-hidden="true">{icon.glyph}</i><strong>{row.name}</strong>{row.equipped&&<small className="cm-wear-badge">已穿戴</small>}{row.quest&&<small className="cm-wear-badge is-quest">任务</small>}{row.favorite&&<small className="cm-wear-badge is-favorite" aria-label="已收藏">★</small>}</span>
          <span>{row.count}</span><span>{row.weight.toFixed(1)}</span><span>{row.value}</span>
        </div>;})}
      </div>
      {!rows.length&&<div className="cm-empty">{f.wardrobe?"这位伙伴没有可穿脱的服饰。":"正在获取伙伴库存数据。"}</div>}
      {!!rows.length&&!shown.length&&<div className="cm-empty">没有匹配「{query.trim()}」的服饰。</div>}
    </div>
    <div className="cm-wear-detail">
      <ModelPreview actorId={f.id} id={modelId}/>
      {preview&&outcome?<>
        <div className="cm-wear-info">
        <div className="cm-wear-title"><h3><i className={`cm-wear-icon is-${wearIcon(preview).tone}`} aria-hidden="true">{wearIcon(preview).glyph}</i><span className="cm-wear-title-name">{preview.name}</span></h3><div className="cm-wear-title-actions"><small className={preview.equipped?"is-worn":""}>{preview.equipped?"已穿戴":"库存中"}{preview.quest?" · 任务装备":""}{preview.favorite?" · ★ 已收藏":""}</small><button className="primary" disabled={blocked(preview)} onClick={()=>toggle(preview)}>{preview.equipped?"卸下":"穿上"}</button></div></div>
        <div className="cm-wear-stats">
          <div className={delta>0?"up":delta<0?"down":""}><small>{outcome.action==="wear"?"穿上后护甲":"卸下后护甲"}</small>
            <strong>{outcome.next}{delta!==0&&<span>{delta>0?` (+${delta})`:` (${delta})`}</span>}</strong></div>
          <div><small>当前护甲</small><strong>{outcome.current}</strong></div>
          <div><small>重量</small><strong>{preview.weight.toFixed(1)}</strong></div>
          <div><small>价值</small><strong>{preview.value}</strong></div>
          <div><small>数量</small><strong>{preview.count}</strong></div>
        </div>
        <dl className="cm-wear-facts">
          <div><dt>部位</dt><dd>{wearSlotNames(preview).join("、")}</dd></div>
          <div><dt>类型</dt><dd>{preview.armorType?armorTypeNames[preview.armorType]:"未标注"}</dd></div>
          {preview.enchantment&&<div><dt>附魔</dt><dd>{preview.enchantment}</dd></div>}
          {!!outcome.replaced.length&&<div><dt>将换下</dt><dd>{outcome.replaced.map(row=>row.name).join("、")}</dd></div>}
          <div className="cm-wear-hint"><dt>操作</dt><dd>{preview.equipped&&preview.quest?"任务装备不能卸下。":usable?(preview.equipped?"点击右侧按钮或按 Enter 卸下，悬停其它服饰即可预览对比。":"点击右侧按钮或按 Enter 穿上；同名物品只影响选中那件。"):"当前无法穿脱，仅预览；请先让伙伴脱离战斗并待在身边。"}</dd></div>
        </dl>
        </div>
      </>:<div className="cm-empty">左侧没有可预览的服饰。</div>}
    </div>
  </div>;
}
