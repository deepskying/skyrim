import {useEffect,useRef,useState} from "react";
import type {GameFollower} from "./bridge";
import {outfitSlots,slotDescription,slotName,type OutfitItem} from "./outfits";
import "./outfits.css";
type Props={f:GameFollower;enabled:boolean;chance:number;mode:string;onEntryConsumed?:()=>void;notice?:{ok:boolean;message:string}|null;command:(op:string,data?:Record<string,unknown>)=>boolean};
export function OutfitPanel({f,enabled,chance,mode,onEntryConsumed,notice,command}:Props){
 const [tab,setTab]=useState(mode==="part"?"part":"all"),[slot,setSlot]=useState(32),[preset,setPreset]=useState(0),[name,setName]=useState(""),[error,setError]=useState("");
 const dialog=useRef<HTMLDialogElement>(null),removeDialog=useRef<HTMLDialogElement>(null),input=useRef<HTMLInputElement>(null),submitted=useRef<string|null>(null);
 const data=f.outfits,items=data?.items??[],presets=data?.presets??[],worn=items.filter(i=>i.equipped);
 const usable=enabled&&!f.dead&&!f.unavailable&&!f.inCombat&&f.group==="party"&&!data?.pending&&!!data;
 const act=(op:string,payload:Record<string,unknown>={})=>command(op,{actorId:f.id,...payload});
 const openSave=()=>{let n=presets.length+1;while(presets.some(p=>p.name===`${f.name} · 套装 ${n}`))n++;setName(`${f.name} · 套装 ${n}`);setError("");submitted.current=null;dialog.current?.showModal();requestAnimationFrame(()=>input.current?.select());};
 const entryConsumed=useRef(false);
 useEffect(()=>{if(mode==="save"&&data&&enabled&&!entryConsumed.current){entryConsumed.current=true;openSave();onEntryConsumed?.();}},[mode,data,enabled]);
 useEffect(()=>{if(submitted.current&&notice&&!notice.ok){setError(notice.message);submitted.current=null;}},[notice]);
 useEffect(()=>{if(submitted.current&&presets.some(p=>p.name===submitted.current)){const saved=presets.find(p=>p.name===submitted.current)!;setPreset(saved.id);setTab("all");dialog.current?.close();submitted.current=null;}},[presets]);
 const picked=presets.find(p=>p.id===preset),listing=picked?.items??worn;
 useEffect(()=>{if(preset&&!picked)setPreset(0);},[preset,picked]);
 const protectedMask=worn.filter(i=>i.quest).reduce((a,i)=>a|i.mask,0);
 const inSlot=(i:OutfitItem)=>outfitSlots(i.mask).includes(slot);
 const candidates=items.filter(i=>inSlot(i)&&!i.equipped&&i.available);
 const slotItems=[...worn.filter(inSlot),...candidates];
 const details=(i:OutfitItem)=><small>{outfitSlots(i.mask).length>1&&<span className="cm-outfit-tag">多槽位</span>}{slotDescription(i.mask)}</small>;
 return <div className="cm-outfits">
  <div className="cm-outfit-toolbar"><div className="tabs"><button className={tab==="all"?"active":""} onClick={()=>setTab("all")}>整套随机</button><button className={tab==="part"?"active":""} onClick={()=>setTab("part")}>指定部位</button></div><button disabled={!usable||!worn.length||presets.length>=64} onClick={openSave}>保存当前套装</button></div>
  {tab==="all"?<><p>随机规则：{chance}% 已保存套装 · {100-chance}% 重新组合；可在全局设置修改。</p>
   <div className="cm-outfit-presets"><button className={!picked?"active":""} aria-pressed={!picked} onClick={()=>setPreset(0)}><small>正在穿戴</small><strong>当前套装</strong><small>{worn.length} 件服饰</small></button>{presets.map(p=><button key={p.id} className={preset===p.id?"active":""} aria-pressed={preset===p.id} onClick={()=>setPreset(p.id)}><small>已保存 · {f.name}</small><strong>{p.name}</strong><small>{p.items.length} 件服饰</small></button>)}</div>
   <h3>{picked?.name??"当前套装"}</h3><div className="cm-outfit-list">{listing.map((i,index)=><div className="cm-outfit-row" key={`${i.key}-${index}`}><span>{slotName(outfitSlots(i.mask)[0])}</span><div><strong>{i.name}</strong>{details(i)}</div><small>{i.equipped?"穿戴中":!i.available?"库存缺失 · 跳过":i.favorite?"★ 已收藏":"库存中"}{i.hidden&&" · 普通库存未显示"}</small></div>)}</div>
   {!listing.length&&<div className="cm-empty">{data?"当前没有可保存的服饰。":"正在获取穿搭数据。"}</div>}
   <div className="cm-outfit-toolbar"><button className="primary" disabled={!usable} onClick={()=>act(picked?"applyNamedOutfit":"changeOutfit",picked?{presetId:picked.id}:{})}>{picked?"使用此套装":"随机一套"}</button>{picked&&<button disabled={!usable} onClick={()=>removeDialog.current?.showModal()}>移除当前套装</button>}<p>{picked?"缺失物品跳过；多槽位装备仍会替换其占用部位。":"没有已保存套装时，始终重新组合。"}</p></div>
  </>:<><p>全部 32 个槽位 · 亮色边框表示已穿戴 · 盾牌不参与穿搭</p><div className="cm-outfit-slots">{Array.from({length:32},(_,i)=>i+30).map(s=>{const count=items.filter(i=>outfitSlots(i.mask).includes(s)&&i.available&&!i.equipped&&!i.quest&&!(i.mask&protectedMask)).length;const equipped=worn.some(i=>outfitSlots(i.mask).includes(s));return <button key={s} disabled={s===39} className={`${s===slot?"active":""} ${equipped?"is-worn":""}`} aria-pressed={s===slot} onClick={()=>setSlot(s)}><small>{s}</small><span>{slotName(s)}</span><small>{s===39?"不参与":`${equipped?"已穿戴 · ":""}${count} 件可换`}</small></button>;})}</div>
   <h3>{slotName(slot)} · 装备 <small>{worn.some(inSlot)?"亮色边框为当前穿戴":"当前未穿戴"}</small></h3>
   <div className="cm-slot-equipment-grid">{slotItems.map(i=>{
    const blocked=!!i.quest||(!i.equipped&&!!(i.mask&protectedMask));
    const content=<><small className="cm-slot-equipment-status">{i.equipped?"已穿戴":"可替换服饰"}{i.favorite&&" · ★ 已收藏"}</small><strong>{i.name}</strong>{details(i)}{i.hidden&&<small>未出现在普通库存 · 已识别为当前穿戴</small>}{blocked?<small>受保护或与受保护部位冲突</small>:outfitSlots(i.mask).length>1&&<small>{i.equipped?"卸下将同时腾出：":"穿戴将影响："}{slotDescription(i.mask)}</small>}</>;
    return <article className={`cm-slot-equipment-card ${i.equipped?"is-worn":""}`} key={i.key}>{i.equipped?<><div className="cm-slot-equipment-body">{content}</div><button className="cm-slot-unequip" disabled={!usable||blocked} onClick={()=>act("unequipOutfitPart",{slot,itemKey:i.key})}>卸下装备</button></>:<button className="cm-slot-equipment-body" disabled={!usable||blocked} onClick={()=>act("outfitPart",{slot,itemKey:i.key})}>{content}<small>点击穿戴</small></button>}</article>;
   })}</div>{!slotItems.length&&<div className="cm-empty">此槽位没有装备。</div>}
   <div className="cm-outfit-toolbar"><button className="primary" disabled={!usable||!candidates.some(i=>!i.quest&&!(i.mask&protectedMask))} onClick={()=>act("outfitPart",{slot})}>随机更换此部位</button><p>多槽位装备会一并替换所占部位。</p></div>
  </>}
  {data?.pending&&<p role="status">正在确认换装，请稍候……</p>}
  <dialog ref={removeDialog} className="cm-outfit-dialog" aria-labelledby="cm-outfit-remove-title"><h3 id="cm-outfit-remove-title">移除保存的套装</h3><p>移除「{picked?.name}」？当前穿戴和收藏不会改变。</p><div className="button-row"><button onClick={()=>removeDialog.current?.close()}>取消</button><button disabled={!usable||!picked} onClick={()=>{if(picked&&act("removeNamedOutfit",{presetId:picked.id}))removeDialog.current?.close();}}>移除当前套装</button></div></dialog>
  <dialog ref={dialog} className="cm-outfit-dialog" aria-labelledby="cm-outfit-save-title"><form onSubmit={e=>{e.preventDefault();const clean=name.trim();if(!clean){setError("请输入套装名称");return;}if(presets.some(p=>p.name===clean)){setError("已有同名套装，请换个名称");return;}if(act("saveNamedOutfit",{name:clean})){submitted.current=clean;setError("保存结果会在主面板显示；成功后此窗口自动关闭。");}}}><h3 id="cm-outfit-save-title">保存当前套装</h3><label>套装名称<input ref={input} autoFocus maxLength={30} required value={name} onChange={e=>setName(e.target.value)}/></label><p>{f.name} · {worn.length} 件服饰。保存物品列表，并全部加入收藏；不包含武器、盾牌和弹药。</p>{error&&<p role="status">{error}</p>}<div className="button-row"><button type="button" onClick={()=>dialog.current?.close()}>取消</button><button className="primary" disabled={!usable||!worn.length}>保存并收藏</button></div></form></dialog>
 </div>;
}
