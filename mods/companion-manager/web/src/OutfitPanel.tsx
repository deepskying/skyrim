import {useEffect,useRef,useState} from "react";
import {focusWardrobe,type GameFollower} from "./bridge";
import "./outfits.css";

type Props={f:GameFollower;enabled:boolean;chance:number;mode:string;onEntryConsumed?:()=>void;notice?:{ok:boolean;message:string}|null;command:(op:string,data?:Record<string,unknown>)=>boolean};

// 伙伴穿搭 keeps only what the compact overlay cannot do: save the current outfit, wear a saved
// set in one click and delete one. The per-item wear page lives in the compact overlay the
// dialogue opens, so this dashboard has no tabs at all - opening it always lands on the saved sets.
export function OutfitPanel({f,enabled,chance,mode,onEntryConsumed,notice,command}:Props){
 const [name,setName]=useState(""),[error,setError]=useState("");
 const dialog=useRef<HTMLDialogElement>(null),input=useRef<HTMLInputElement>(null),submitted=useRef<string|null>(null);
 const data=f.outfits,items=data?.items??[],presets=data?.presets??[],worn=items.filter(i=>i.equipped);
 const usable=enabled&&!f.dead&&!f.unavailable&&!f.inCombat&&f.group==="party"&&!data?.pending&&!!data;
 const act=(op:string,payload:Record<string,unknown>={})=>command(op,{actorId:f.id,...payload});
 const openSave=()=>{let n=presets.length+1;while(presets.some(p=>p.name===`${f.name} · 套装 ${n}`))n++;setName(`${f.name} · 套装 ${n}`);setError("");submitted.current=null;dialog.current?.showModal();requestAnimationFrame(()=>input.current?.select());};
 const entryConsumed=useRef(false);
 // Ask native for this companion's inventory payload while the panel is open, and release it on
 // the way out so other pages get the full snapshot back.
 useEffect(()=>{focusWardrobe(f.id);return()=>{focusWardrobe("");};},[f.id]);
 useEffect(()=>{if(mode==="save"&&data&&enabled&&!entryConsumed.current){entryConsumed.current=true;openSave();onEntryConsumed?.();}},[mode,data,enabled]);
 useEffect(()=>{if(submitted.current&&notice&&!notice.ok){setError(notice.message);submitted.current=null;}},[notice]);
 useEffect(()=>{if(submitted.current&&presets.some(p=>p.name===submitted.current)){dialog.current?.close();submitted.current=null;}},[presets]);
 return <div className="cm-outfits">
  <div className="cm-outfit-toolbar"><p>点击卡片直接换上整套（先换下当前服饰，任务装备与角色皮肤保留）；卡片右上角的 ✕ 删除该套装。逐件穿脱请用对话里的「调整穿搭」。随机规则 {chance}% 已保存套装 · {100-chance}% 从收藏重新组合，供对话与定时换装使用。</p><button disabled={!usable||!worn.length||presets.length>=64} onClick={openSave}>保存当前套装</button></div>
  <div className="cm-outfit-presets">{presets.map(p=><div className="cm-outfit-preset" key={p.id}>
   <button className="cm-outfit-preset-body" disabled={!usable} onClick={()=>act("applyNamedOutfit",{presetId:p.id})}><small>已保存 · {f.name}</small><strong>{p.name}</strong><small>{p.items.length} 件服饰 · 点击换上</small></button>
   <button type="button" className="cm-outfit-preset-delete" disabled={!usable} title="删除这个套装" aria-label={`删除套装 ${p.name}`} onClick={()=>act("removeNamedOutfit",{presetId:p.id})}>✕</button>
  </div>)}</div>
  {!presets.length&&<div className="cm-empty">{data?"还没有保存的套装：点右上角「保存当前套装」把现在的穿搭存下来。":"正在获取穿搭数据。"}</div>}
  {data?.pending&&<p role="status">正在确认换装，请稍候……</p>}
  <dialog ref={dialog} className="cm-outfit-dialog" aria-labelledby="cm-outfit-save-title"><form onSubmit={e=>{e.preventDefault();const clean=name.trim();if(!clean){setError("请输入套装名称");return;}if(presets.some(p=>p.name===clean)){setError("已有同名套装，请换个名称");return;}if(act("saveNamedOutfit",{name:clean})){submitted.current=clean;setError("保存结果会在主面板显示；成功后此窗口自动关闭。");}}}><h3 id="cm-outfit-save-title">保存当前套装</h3><label>套装名称<input ref={input} autoFocus maxLength={30} required value={name} onChange={e=>setName(e.target.value)}/></label><p>{f.name} · {worn.length} 件服饰。保存物品列表，并全部加入收藏；不包含武器、盾牌和弹药。</p>{error&&<p role="status">{error}</p>}<div className="button-row"><button type="button" onClick={()=>dialog.current?.close()}>取消</button><button className="primary" disabled={!usable||!worn.length}>保存并收藏</button></div></form></dialog>
 </div>;
}
