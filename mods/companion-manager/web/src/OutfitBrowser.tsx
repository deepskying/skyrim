import {useMemo,useState} from "react";
import type {GameFollower,SelfCard} from "./bridge";
import {OutfitPanel,type OutfitTarget} from "./OutfitPanel";
import "./outfits.css";

type Props={
  self?:SelfCard;
  followers:GameFollower[];
  session?:string;
  selected?:OutfitTarget;
  onSelect:(id:string)=>void;
  onBack:()=>void;
  enabled:boolean;
  chance:number;
  mode:string;
  onEntryConsumed?:()=>void;
  notice?:{ok:boolean;message:string}|null;
  command:(op:string,data?:Record<string,unknown>)=>boolean;
};

type Card={id:string;name:string;status:string;count:number;self:boolean;away:boolean;level:number;meta:string;tone:string;home:string};

function followerStatus(f:GameFollower) {
  if(f.group==="party") return f.waiting?"等待中":"在队";
  return f.group==="registry"?"未入队":"附近";
}

// The wardrobe page keeps two levels: a card per companion (the player first) and, once a card is
// opened, that actor's saved-set list. Nothing else in the dashboard treats the player as a
// follower, so the player card is merged here instead of in the shared follower snapshot.
export function OutfitBrowser({self,followers,session,selected,onSelect,onBack,enabled,chance,mode,onEntryConsumed,notice,command}:Props){
  const [query,setQuery]=useState("");
  const cards=useMemo<Card[]>(()=>{
    const rows:Card[]=[];
    if(self) rows.push({id:self.id,name:self.name,status:"你自己",count:self.outfits?.presets.length??self.presetCount??0,self:true,away:false,level:self.level??0,meta:"武器、盾牌与弹药不入套装",tone:"self",home:""});
    for(const f of followers) rows.push({id:f.id,name:f.name,status:followerStatus(f),count:f.outfits?.presets.length??f.presetCount,self:false,away:f.group!=="party",level:f.level,meta:`${f.race} · ${f.role}`,tone:f.group==="party"?(f.waiting?"waiting":"party"):f.group==="registry"?"registry":"nearby",home:f.home==="未设置"?"未设置":f.home});
    const needle=query.trim().toLocaleLowerCase();
    return needle?rows.filter(r=>r.name.toLocaleLowerCase().includes(needle)||r.status.includes(needle)):rows;
  },[self,followers,query]);
  if(selected) return <div className="cm-outfits">
    <div className="cm-outfit-crumbs"><button type="button" className="cm-outfit-back" onClick={onBack}>← 全部伙伴</button><span>{selected.self?"你自己的衣橱":"伙伴衣橱"}</span></div>
    <OutfitPanel key={`${session}-${selected.id}-${mode}`} f={selected} enabled={enabled} chance={chance} mode={mode} onEntryConsumed={onEntryConsumed} notice={notice} command={command}/>
  </div>;
  return <div className="cm-outfits">
    <div className="cm-management-bar"><div><h2>每位伙伴的独立衣橱</h2><p>先选一位伙伴（或你自己），再保存、换上一整套穿搭。</p></div><input aria-label="搜索伙伴" placeholder="搜索伙伴…" value={query} onChange={e=>setQuery(e.target.value)}/></div>
    <div className="cm-outfit-grid">{cards.map(card=>{
      const unopened=!card.self&&card.away;
      return <button type="button" key={card.id} className={`cm-outfit-card ${card.tone}${card.self?" self":""}${unopened?" away":""}`} aria-label={`查看${card.name}的套装`} onClick={()=>onSelect(card.id)}>
        <span className="cm-outfit-card-top"><strong title={card.name}>{card.name}</strong>{card.level>0&&<span className="cm-level">Lv. {card.level}</span>}{card.self&&<span className="cm-outfit-tag">你</span>}</span>
        <span className="cm-outfit-home" title={card.home?`居所：${card.home}`:card.meta}>{card.home?`居所：${card.home}`:"武器、盾牌与弹药不入套装"}</span>
        <span className="cm-outfit-card-foot"><span className="cm-outfit-card-meta">{card.meta}</span><span className="cm-outfit-hint">点击查看穿搭</span></span>
      </button>;
    })}{!cards.length&&<p className="cm-empty" role="status">{followers.length||self?"没有找到匹配的伙伴":"先招募一位伙伴，即可调整穿搭。"}</p>}</div>
  </div>;
}
