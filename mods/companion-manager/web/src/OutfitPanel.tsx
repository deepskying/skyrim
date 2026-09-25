import {useEffect,useRef,useState} from "react";
import {focusWardrobe,type GameFollower} from "./bridge";
import {outfitSlots,slotDescription,slotName,type OutfitItem} from "./outfits";
import {WearPanel} from "./WearPanel";
import "./outfits.css";
type Props={f:GameFollower;enabled:boolean;chance:number;mode:string;onEntryConsumed?:()=>void;notice?:{ok:boolean;message:string}|null;command:(op:string,data?:Record<string,unknown>)=>boolean};
export function OutfitPanel({f,enabled,chance,mode,onEntryConsumed,notice,command}:Props){
 // The manual slot page was removed in 1.8.14; an entry that still asks for it ("part") lands on
 // the wear page, which covers the same ground with a flat list.
 const [tab,setTab]=useState(mode==="wear"||mode==="part"?"wear":"all"),[preset,setPreset]=useState(0),[name,setName]=useState(""),[error,setError]=useState("");
 const dialog=useRef<HTMLDialogElement>(null),removeDialog=useRef<HTMLDialogElement>(null),input=useRef<HTMLInputElement>(null),submitted=useRef<string|null>(null);
 const data=f.outfits,items=data?.items??[],presets=data?.presets??[],worn=items.filter(i=>i.equipped);
 const usable=enabled&&!f.dead&&!f.unavailable&&!f.inCombat&&f.group==="party"&&!data?.pending&&!!data;
 // The wear page reads the inventory rows instead of the outfit payload, so a broken saved set
 // never hides it; the pending flag still comes from the shared confirmation map.
 const wearPending=!!data?.pending;
 const act=(op:string,payload:Record<string,unknown>={})=>command(op,{actorId:f.id,...payload});
 const openSave=()=>{let n=presets.length+1;while(presets.some(p=>p.name===`${f.name} · 套装 ${n}`))n++;setName(`${f.name} · 套装 ${n}`);setError("");submitted.current=null;dialog.current?.showModal();requestAnimationFrame(()=>input.current?.select());};
 // Clicking a saved set wears it right away; the selection only drives the preview list below.
 const applyPreset=(id:number)=>{setPreset(id);if(usable)act("applyNamedOutfit",{presetId:id});};
 const entryConsumed=useRef(false);
  // Ask native for this companion's inventory payload while the panel is open, and release it on
  // the way out so other pages get the full snapshot back.
  useEffect(()=>{focusWardrobe(f.id);return()=>{focusWardrobe("");};},[f.id]);
 useEffect(()=>{if(mode==="save"&&data&&enabled&&!entryConsumed.current){entryConsumed.current=true;openSave();onEntryConsumed?.();}},[mode,data,enabled]);
 useEffect(()=>{if(submitted.current&&notice&&!notice.ok){setError(notice.message);submitted.current=null;}},[notice]);
 useEffect(()=>{if(submitted.current&&presets.some(p=>p.name===submitted.current)){const saved=presets.find(p=>p.name===submitted.current)!;setPreset(saved.id);setTab("all");dialog.current?.close();submitted.current=null;}},[presets]);
 const picked=presets.find(p=>p.id===preset),listing=picked?.items??worn;
 useEffect(()=>{if(preset&&!picked)setPreset(0);},[preset,picked]);
 const details=(i:OutfitItem)=><small>{outfitSlots(i.mask).length>1&&<span className="cm-outfit-tag">多槽位</span>}{slotDescription(i.mask)}</small>;
 return <div className="cm-outfits">
  <div className="cm-outfit-toolbar"><div className="tabs"><button className={tab==="all"?"active":""} onClick={()=>setTab("all")}>整套随机</button><button className={tab==="wear"?"active":""} onClick={()=>setTab("wear")}>随从装备</button></div><button disabled={!usable||!worn.length||presets.length>=64} onClick={openSave}>保存当前套装</button></div>
  {tab==="wear"?<WearPanel f={f} enabled={enabled} pending={wearPending} command={command}/>:<><p>随机规则：{chance}% 已保存套装 · {100-chance}% 从收藏重新组合；可在全局设置修改。</p>
   <div className="cm-outfit-presets"><button className={!picked?"active":""} aria-pressed={!picked} onClick={()=>setPreset(0)}><small>正在穿戴</small><strong>当前套装</strong><small>{worn.length} 件服饰</small></button>{presets.map(p=><button key={p.id} className={preset===p.id?"active":""} aria-pressed={preset===p.id} onClick={()=>applyPreset(p.id)}><small>已保存 · {f.name}</small><strong>{p.name}</strong><small>{p.items.length} 件服饰 · 点击换上</small></button>)}</div>
   <h3>{picked?.name??"当前套装"}</h3><div className="cm-outfit-list">{listing.map((i,index)=><div className="cm-outfit-row" key={`${i.key}-${index}`}><span>{slotName(outfitSlots(i.mask)[0])}</span><div><strong>{i.name}</strong>{details(i)}</div><small>{i.equipped?"穿戴中":!i.available?"库存缺失 · 跳过":i.favorite?"★ 已收藏":"库存中"}{i.hidden&&" · 普通库存未显示"}</small></div>)}</div>
   {!listing.length&&<div className="cm-empty">{data?"当前没有可保存的服饰。":"正在获取穿搭数据。"}</div>}
   <div className="cm-outfit-toolbar"><button className="primary" disabled={!usable} onClick={()=>act("changeOutfit")}>随机一套</button>{picked&&<button disabled={!usable} onClick={()=>removeDialog.current?.showModal()}>移除当前套装</button>}<p>{picked?`点击套装卡片直接换上整套：先换下当前服饰（任务装备与角色皮肤保留），缺失的实例跳过、对应部位保持空着。${usable?"":"当前无法换装，仅预览。"}`:"点击套装卡片直接换上整套；随机一套只使用已收藏服饰，没有已保存套装时始终重新组合。"}</p></div>
  </>}
  {data?.pending&&<p role="status">正在确认换装，请稍候……</p>}
  <dialog ref={removeDialog} className="cm-outfit-dialog" aria-labelledby="cm-outfit-remove-title"><h3 id="cm-outfit-remove-title">移除保存的套装</h3><p>移除「{picked?.name}」？当前穿戴和收藏不会改变。</p><div className="button-row"><button onClick={()=>removeDialog.current?.close()}>取消</button><button disabled={!usable||!picked} onClick={()=>{if(picked&&act("removeNamedOutfit",{presetId:picked.id}))removeDialog.current?.close();}}>移除当前套装</button></div></dialog>
  <dialog ref={dialog} className="cm-outfit-dialog" aria-labelledby="cm-outfit-save-title"><form onSubmit={e=>{e.preventDefault();const clean=name.trim();if(!clean){setError("请输入套装名称");return;}if(presets.some(p=>p.name===clean)){setError("已有同名套装，请换个名称");return;}if(act("saveNamedOutfit",{name:clean})){submitted.current=clean;setError("保存结果会在主面板显示；成功后此窗口自动关闭。");}}}><h3 id="cm-outfit-save-title">保存当前套装</h3><label>套装名称<input ref={input} autoFocus maxLength={30} required value={name} onChange={e=>setName(e.target.value)}/></label><p>{f.name} · {worn.length} 件服饰。保存物品列表，并全部加入收藏；不包含武器、盾牌和弹药。</p>{error&&<p role="status">{error}</p>}<div className="button-row"><button type="button" onClick={()=>dialog.current?.close()}>取消</button><button className="primary" disabled={!usable||!worn.length}>保存并收藏</button></div></form></dialog>
 </div>;
}
