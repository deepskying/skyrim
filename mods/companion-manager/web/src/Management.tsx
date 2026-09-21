import { useEffect,useState } from "react";
import type { Snapshot,GameFollower } from "./bridge";
import { categories,defaultBehavior,selectionTotals,validBehavior,type BehaviorSettings } from "./behavior";
import { inventoryCategories,itemCategory,inventoryMatches,categoryCounts,type InventoryCategory } from "./inventory";
import { CompanionPicker } from "./CompanionPicker";
type Props={snapshot:Snapshot|null;enabled:boolean;wardrobe:boolean;initialActor:string;command:(op:string,data?:Record<string,unknown>)=>boolean};
const jobNames:Record<string,string>={idle:"自由安排",loot:"搜集战利品",sell:"前往商家交易",carry:"准备交接物品",outfit:"征求穿搭建议"};
export function Management({snapshot:s,enabled,wardrobe,initialActor,command}:Props) {
  const followers=s?.followers.filter(f=>f.managed)??[];
  const [actorId,setActorId]=useState(initialActor),[tab,setTab]=useState("通用设置");
  const f=followers.find(f=>f.id===actorId)??(wardrobe?followers[0]:undefined);
  const [query,setQuery]=useState(""),[filter,setFilter]=useState<InventoryCategory>("all"),[lockedOnly,setLockedOnly]=useState(false),[taking,setTaking]=useState(false),[selected,setSelected]=useState<Record<string,number>>({});
  useEffect(()=>{setActorId(initialActor);},[initialActor]);
  useEffect(()=>{setSelected({});setTaking(false);},[f?.id,s?.session]);
  const config=f?.behavior??s?.automation?.defaults??defaultBehavior;
  const [draft,setDraft]=useState<BehaviorSettings>(config);
  useEffect(()=>{setDraft(config);},[JSON.stringify(config),actorId,s?.session]);
  const usable=enabled&&!!f&&!f.dead&&!f.unavailable;
  const act=(op:string,data:Record<string,unknown>={})=>f&&command(op,{actorId:f.id,...data});
  const items=f?.wardrobe??[];
  const shown=items.filter(i=>inventoryMatches(i,filter,query,lockedOnly));
  const counts=categoryCounts(items,query,lockedOnly);
  const totals=selectionTotals(items,selected),room=(s?.automation?.playerCapacity??0)-(s?.automation?.playerCarried??0);
  const invalidSelection=Object.entries(selected).some(([key,count])=>!Number.isInteger(count)||count<1||!items.some(i=>i.key===key&&i.count>=count&&!i.quest&&!i.equipped));
  const toggle=(key:keyof BehaviorSettings,label:string,note:string)=><label className="cm-auto-switch"><span><strong>{label}</strong><small>{note}</small></span><input type="checkbox" checked={!!draft[key]} disabled={!enabled} onChange={e=>setDraft({...draft,[key]:e.target.checked})}/></label>;
  const number=(key:keyof BehaviorSettings,label:string,min:number,max:number,unit:string)=><label className="cm-auto-number">{label}<span><input type="number" aria-label={label} min={min} max={max} disabled={!enabled} value={Number(draft[key])} onChange={e=>setDraft({...draft,[key]:Number(e.target.value)})}/>{unit}</span></label>;
  return <section className="cm-management">
    <div className="cm-management-bar"><div><h2>{wardrobe?"每位伙伴的随身库存":"让同伴按自己的习惯行动"}</h2><p>{wardrobe?(taking?"点击物品卡片选择或取消取走，右上角显示选中状态。":"点击卡片切换锁定。★ 锁定物品不会出售，锁定服饰可参与自动穿搭。"):"全队规则统一设置，也可以为伙伴保留个人偏好。"}</p></div>
      {wardrobe?<CompanionPicker key={s?.session} followers={followers} value={f?.id??""} onChange={setActorId}/>:<select aria-label="选择管理伙伴" value={f?.id??""} onChange={e=>setActorId(e.target.value)}>
        {!wardrobe&&<option value="">全队默认</option>}{followers.map(a=><option key={a.id} value={a.id}>{a.name}{a.group==="registry"?" · 已离队":""}</option>)}
      </select>}
    </div>
    {f&&<div className="cm-management-summary"><strong>{f.name}</strong><span>负重 {(f.carried??0).toFixed(1)} / {(f.capacity??0).toFixed(0)}</span><span>{jobNames[f.activity??"idle"]}</span><span>{f.behaviorOverride?"个人规则":"沿用全队规则"}</span></div>}
    {wardrobe?<>
      {!f?<div className="cm-empty">先招募一位伙伴，即可查看库存。</div>:<>
      <nav className="cm-inventory-categories" aria-label="库存分类">{inventoryCategories.map(c=><button key={c.id} className={filter===c.id?"active":""} aria-pressed={filter===c.id} onClick={()=>setFilter(c.id)}><span aria-hidden="true">{c.icon}</span><span>{c.label}</span><small aria-label={`${counts[c.id]}组物品`}>{counts[c.id]}</small></button>)}</nav>
      <div className="cm-wardrobe-toolbar"><input aria-label="搜索库存" placeholder="搜索装备或物品…" value={query} onChange={e=>setQuery(e.target.value)}/><button className={lockedOnly?"cm-locked-filter active":"cm-locked-filter"} aria-pressed={lockedOnly} onClick={()=>setLockedOnly(!lockedOnly)}>★ 仅看已锁定</button>
        <button disabled={!usable||f.inCombat} onClick={()=>act("exchangeSupplies")}>交换物资</button><button disabled={!usable} onClick={()=>{setTaking(!taking);setSelected({});}}>{taking?"取消取物":"挑选物品取走"}</button>
      </div>
      {f.request&&<div className="cm-management-summary">{f.request==="carry"?"伙伴希望你帮忙分担物品。":"伙伴想听听你的穿搭建议。"}<button disabled={!usable} onClick={()=>act("deferRequest")}>稍后再说</button></div>}
      <p className="cm-inventory-result">{inventoryCategories.find(c=>c.id===filter)?.label} · {shown.length} 组物品{taking&&" · 切换分类会保留已选物品"}</p>
      <div className="cm-wardrobe-grid">{shown.map(i=>{
        const category=inventoryCategories.find(c=>c.id===itemCategory(i))!;
        const takeable=!i.quest&&!i.equipped&&i.count>0;
        const picked=takeable&&!!selected[i.key];
        const togglePick=()=>setSelected(old=>{const next={...old};if(next[i.key])delete next[i.key];else next[i.key]=1;return next;});
        return <article className={`cm-wardrobe-card ${i.favorite?"favorite":""} ${i.equipped?"equipped":""} ${taking&&picked?"selected":""} ${taking&&!takeable?"unavailable":""}`} key={i.key}>
          <button className="cm-wardrobe-main" disabled={!usable||(taking&&!takeable)}
            aria-label={taking?(takeable?`${picked?"取消选择":"选择取走"}${i.name}`:`${i.name}，不可取走`):`${i.favorite?"取消锁定":"锁定"}${i.name}`}
            aria-pressed={taking?(takeable?picked:undefined):i.favorite}
            title={taking?(takeable?"点击卡片选择或取消取走":"正在穿戴或受保护，无法取走"):"点击切换锁定；堆叠物品按整组保护，不会自动出售"}
            onClick={()=>taking?togglePick():act("favorite",{itemKey:i.key,value:!i.favorite})}>
            <div className="cm-wardrobe-emblem">{category.icon}
              {taking?(takeable&&<span className={`cm-take-mark ${picked?"checked":""}`} aria-hidden="true">{picked?"✓":""}</span>):<span className="cm-favorite-mark" aria-label={i.favorite?"已锁定":"未锁定"}>{i.favorite?"★":"☆"}</span>}
            </div>
            <h3>{i.name}{i.equipped&&<> <span className="cm-equipped-badge">已装备</span></>}</h3><p>{category.label} · ×{i.count}</p>
            <div className="cm-wardrobe-stats"><span>价值 {i.value}</span><span>重量 {i.weight.toFixed(1)}</span></div>
            <div className="cm-wardrobe-tags">{i.quest&&<span>受保护</span>}{i.favorite&&<span>★ 已锁定 · 不出售</span>}{taking&&!takeable&&<span>不可取走</span>}</div>
          </button>
          {taking&&picked&&i.count>1&&<label className="cm-wardrobe-take">取走数量<input type="number" aria-label={`${i.name}取走数量`} min={1} max={i.count} disabled={!usable} value={selected[i.key]} onChange={e=>setSelected({...selected,[i.key]:Number(e.target.value)})}/></label>}
        </article>;
      })}</div>
      {!shown.length&&<div className="cm-empty">没有符合条件的物品。</div>}
      {taking&&<div className="cm-take-summary"><div>已选 {totals.count} 件 · 总价值 {totals.value} · 重量 {totals.weight.toFixed(1)}<p>玩家负重：{(s?.automation?.playerCarried??0).toFixed(1)} → {((s?.automation?.playerCarried??0)+totals.weight).toFixed(1)} / {s?.automation?.playerCapacity??0}</p></div><button className="primary" disabled={!usable||!totals.count||invalidSelection||totals.weight>room} onClick={()=>{if(act("wardrobeTake",{items:Object.entries(selected).map(([key,count])=>({key,count}))}))setSelected({});}}>{totals.weight>room?"剩余负重不足":"确认取走"}</button></div>}
      </>}
    </>:<>
      <div className="tabs cm-management-tabs">{["通用设置","拾取行为","售卖行为","自动穿搭","主动对话","活动记录"].map(t=><button key={t} className={tab===t?"active":""} onClick={()=>setTab(t)}>{t}</button>)}</div>
      {tab==="通用设置"?<General f={f} followers={followers} enabled={enabled} command={command}/>:tab==="活动记录"?<div className="panel cm-activity-log">{s?.automation?.history?.length?s.automation.history.map((text,i)=><p key={i}>{text}</p>):<p>尚无活动记录。</p>}</div>:<div className="panel cm-auto-settings">
        {tab==="拾取行为"&&<>{toggle("loot","战后自动拾取","走近并朝向目标后拾取；遭遇敌袭立即取消。")}{toggle("corpses","敌方尸体","仅本次战斗中识别的敌人，不搜刮队友。")}{toggle("ground","地面物品","仅无主物品，排除玩家主动丢下的物品。")}{toggle("containers","无主容器","跳过有主、上锁和任务物品。")}{number("radius","搜索范围",5,60,"米")}{number("minValue","最低价值",0,10000,"金币")}{number("minRatio","最低价值重量比",0,1000,"")}<h3>物品筛选</h3><div className="cm-category-options">{categories.map(([bit,label])=><label key={bit}><input type="checkbox" disabled={!enabled} checked={!!(draft.categories&bit)} onChange={e=>setDraft({...draft,categories:e.target.checked?draft.categories|bit:draft.categories&~bit})}/>{label}</label>)}</div><p>拾取前重新核对负重；不能超载。金币、宝石和灵魂石不受价值门槛限制。</p></>}
        {tab==="售卖行为"&&<>{toggle("sell","到店自动售卖","伙伴靠近营业中的商家后交易，玩家正在交易时会等待。")}<p>未锁定物品按商家收购范围出售；锁定、穿戴中及任务物品受到保护。商家金币不足时部分出售，收入归伙伴所有。</p><p>成交价根据伙伴口才计算，不使用玩家专属交易加成。完成后显示金币收入。</p></>}
        {tab==="自动穿搭"&&<>{toggle("outfits","自动调整穿搭","非战斗闲暇时，按全局概率选用已保存套装或从锁定服饰重新组合。")}{number("outfitHours","换装间隔",1,72,"游戏小时")}<p>重新组合时仅使用锁定服饰；武器、盾牌和弹药不参与穿搭。</p></>}
        {tab==="主动对话"&&<>{toggle("requests","主动征求建议与交接","负重接近上限且玩家有余量时请求交接；换装后可征求穿搭建议。") }<p>伙伴走近后以文字询问，选择「好的」打开对应伙伴的库存；「稍后再说」至少 5 分钟内不再打扰。语音暂未启用。</p></>}
        <div className="button-row"><button className="primary" disabled={!enabled||!validBehavior(draft)} onClick={()=>command(f?"behavior":"behaviorDefaults",{...(f?{actorId:f.id}:{}),settings:draft})}>{f?"保存个人规则":"保存全队默认"}</button>{f&&<button disabled={!enabled||!f.behaviorOverride} onClick={()=>act("behavior",{inherit:true})}>恢复沿用全队</button>}</div>
      </div>}
    </>}
  </section>;
}
function General({f,followers,enabled,command}:{f?:GameFollower;followers:GameFollower[];enabled:boolean;command:Props["command"]}) {
  const targets=f?[f]:followers.filter(x=>x.group==="party");
  const [message,setMessage]=useState("");
  const execute=(op:string,data:Record<string,unknown>={})=>{
    if(!f){setMessage("请先选择一位伙伴来修改个人行动设置。");return;}
    command(op,{actorId:f.id,...data});
  };
  return <div className="panel cm-auto-settings"><h3>{f?`${f.name}的行动安排`:`全队 · ${targets.length} 位在队伙伴`}</h3>
    {!f?<><p>选择伙伴可调整自由活动、自动跟上、战斗偏好和死亡保护。</p><div className="button-row"><button disabled={!enabled} onClick={()=>command("group",{action:"follow"})}>全队跟随</button><button disabled={!enabled} onClick={()=>command("group",{action:"wait"})}>全队等待</button></div></>:<>
      {([['wait','原地等待',f.waiting],['sandbox','自由活动',f.sandbox],['leash','自动跟上',f.leash],['passive','避免交战',f.passive],['protection','死亡保护',f.essential]] as const).map(([op,label,value])=><label className="cm-auto-switch" key={op}><strong>{label}</strong><input type="checkbox" checked={value} disabled={!enabled||f.dead||f.unavailable||(op==='wait'&&f.group!=='party')} onChange={e=>execute(op,{value:e.target.checked})}/></label>)}
      <div className="button-row"><button disabled={!enabled||f.dead} onClick={()=>execute("summon")}>召回身边</button><button disabled={!enabled||f.dead} onClick={()=>execute(f.group==="party"?"dismiss":"recruit")}>{f.group==="party"?"解散随从":"重新入队"}</button>{(f.group==="registry"||f.dead)&&<button disabled={!enabled} onClick={()=>execute("forget")}>释放名册记录</button>}</div>
      <p>等待或离队的伙伴不参加自动拾取和售卖。居所在伙伴概览顶部设置。</p>
    </>}{message&&<p>{message}</p>}</div>;
}
