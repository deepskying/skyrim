import { defaultBehavior } from "./behavior.ts";
// Two pieces match only when both carry the same enchantment at the same charge, so a saved set
// whose instance identity was re-issued never lands on another enchanted copy. Only recorded
// signatures count: a set saved before they existed has none and is never guessed at.
const sameEnchantment=(saved,item)=>(saved.enchant??0)===(item.enchant??0)&&((saved.enchant??0)===0||(saved.charge??0)===(item.charge??0));
function demoOutfits(){
 // [key,name,mask,equipped,enchant] - the enchanted copy carries the signature a saved set stores.
 const specs=[["00012E49:00000014:0002","皮甲",4,true],["00012E49:00000014:0003","皮甲（火焰抗性）",4,false,{enchant:0x0007A0F7,charge:200}],["0001BE1A:00000014:0004","弥光连体袍",132,false],["00013920:00000014:0005","白色高跟靴",128,true],["00013921:00000014:0006","黑色短靴",128,false],["0003B97C:00000014:0007","银项链",32,true]];
  // Random changes only ever wear favorites, so the demo keeps spare pieces favorited too.
  const items=specs.map(([key,name,mask,equipped,enchant],index)=>({key,name,mask,equipped,form:parseInt(key.slice(0,8),16),favorite:equipped||index===1||index===4,available:true,quest:false,hidden:false,...(enchant??{})}));
 return {items,pending:false,presets:[{id:1,name:"月下长袍",items:[structuredClone(items[2]),{key:"000877AA:00000014:0008",name:"翡翠戒指",mask:64,equipped:false,favorite:true,available:false,form:0x877aa}]}]};
}
export function fixture() {
  // The protection list mirrors native: what a saved outfit names, what the player handed over, and
  // what was pinned by hand. The fixture reads it off the wardrobe's locked rows.
  const collectOf=wardrobe=>({missing:0,items:wardrobe.filter(i=>i.favorite).map(i=>({key:i.key,form:parseInt(i.id,16),name:i.name,count:i.count,value:i.value,inventoryCategory:i.inventoryCategory,equipped:i.equipped,quest:i.quest,reasons:["手动锁定"]}))});
  const actorRow = (id, name, group, managed) => ({
    id,
    name,
    en: id,
    role: "盾卫",
    race: "诺德人",
    mark: "伴",
    tint: "mint",
    group,
    managed,
    outfits:demoOutfits(),
    behavior: {...defaultBehavior},behaviorOverride:false,carried:182,capacity:300,activity:"idle",request:"",
    wardrobe:[
      {key:"00012EB7:00000014:0001",id:"00012EB7",name:"铁剑",inventoryCategory:"weapons",count:1,value:25,weight:9,category:1,equipped:true,quest:false,favorite:false,equipment:true},
      {key:"00012E49:00000014:0002",id:"00012E49",name:"皮甲",inventoryCategory:"apparel",count:1,value:125,weight:6,category:2,equipped:true,quest:false,favorite:true,equipment:true,mask:4,armorRating:26,armorType:"light"},
      {key:"00012E49:00000014:0003",id:"00012E49",name:"皮甲（火焰抗性）",inventoryCategory:"apparel",count:1,value:420,weight:6,category:2,equipped:false,quest:false,favorite:false,equipment:true,mask:4,armorRating:26,armorType:"light",enchantment:"火焰抗性"},
      {key:"0001BE1A:00000000:0000",id:"0001BE1A",name:"精致服装",inventoryCategory:"apparel",count:2,value:55,weight:1,category:2,equipped:false,quest:false,favorite:true,equipment:true,mask:132,armorRating:2,armorType:"clothing"},
      {key:"0003B97C:00000000:0000",id:"0003B97C",name:"银项链",inventoryCategory:"apparel",count:1,value:120,weight:.5,category:4,equipped:false,quest:false,favorite:false,equipment:true,mask:32,armorRating:0,armorType:"jewelry"},
      {key:"0005ACE4:00000000:0000",id:"0005ACE4",name:"铁锭",inventoryCategory:"misc",count:12,value:7,weight:1,category:128,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0003EADD:00000000:0000",id:"0003EADD",name:"治疗药剂",inventoryCategory:"potions",count:5,value:36,weight:.5,category:16,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"00064B2F:00000000:0000",id:"00064B2F",name:"苹果派",inventoryCategory:"food",count:3,value:5,weight:.5,category:16,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0000000F:00000000:0000",id:"0000000F",name:"金币",inventoryCategory:"misc",count:320,value:1,weight:0,category:8,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"000965A2:00000000:0000",id:"000965A2",name:"火球术卷轴",inventoryCategory:"scrolls",count:2,value:100,weight:.5,category:0,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"000727DF:00000000:0000",id:"000727DF",name:"蓝山花",inventoryCategory:"ingredients",count:8,value:2,weight:.1,category:32,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0001AFC4:00000000:0000",id:"0001AFC4",name:"法术书：治疗术",inventoryCategory:"books",count:1,value:50,weight:1,category:64,equipped:false,quest:false,favorite:true,equipment:false},
      {key:"000A7B33:00000000:0000",id:"000A7B33",name:"住宅钥匙",inventoryCategory:"keys",count:1,value:0,weight:0,category:0,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0001397D:00000000:0000",id:"0001397D",name:"铁箭",inventoryCategory:"weapons",count:30,value:1,weight:0,category:128,equipped:false,quest:false,favorite:false,equipment:false},
      // Two more worn/held pieces the wear page lists on top of the outfit payload above.
      {key:"0001396B:00000014:0004",id:"0001396B",name:"铁质护腕",inventoryCategory:"apparel",count:1,value:20,weight:2,category:2,equipped:true,quest:false,favorite:false,equipment:true,mask:8,armorRating:10,armorType:"heavy"},
      {key:"00012EB6:00000000:0000",id:"00012EB6",name:"铁盾",inventoryCategory:"apparel",count:1,value:60,weight:12,category:2,equipped:false,quest:false,favorite:false,equipment:true,mask:512,armorRating:20.4,armorType:"heavy"},
      // The helmet the companion looted: the engine auto-equips it, and the headwear rule is what
      // takes it back off. 0x1002 is how this load order writes an iron helmet (hair + circlet).
      {key:"00012E4D:00000014:0003",id:"00012E4D",name:"铁制头盔",inventoryCategory:"apparel",count:1,value:60,weight:5,category:2,equipped:false,quest:false,favorite:false,equipment:true,mask:0x1002,armorRating:15,armorType:"heavy"},
    ],
    limited: !managed,
    canRecruit: !managed,
    reason: "",
    canRaise: managed,
    originalMax: 50,
    presetCount: 0,
    dead: false,
    unavailable: false,
    level: 34,
    waiting: false,
    passive: false,
    sandbox: true,
    leash: true,
    essential: true,
    raised: managed && group === "party",
    inCombat: false,
    detailsTruncated: false,
    distance: group === "registry" ? null : 12,
    home: "未设置",
    location: "雪漫 · 桥接测试",
    health: [240, 300],
    magicka: [0, 0],
    stamina: [180, 200],
    levelCap: managed && group === "party" ? 300 : 50,
    attributes: [
      { name: "护甲值", value: 215 },
      { name: "负重上限", value: 300 },
      { name: "移动速度倍率", value: 100 },
    ],
    skills: [
      { name: "单手", value: 60 },
      { name: "毁灭", value: 40 },
      { name: "恢复", value: 35 },
    ],
    resistances: [
      { name: "火焰", value: 25 },
      { name: "冰霜", value: -10 },
      { name: "闪电", value: 0 },
    ],
    spells: [
      {
        id: "00012FCC",
        name: "火舌术",
        description:
          "喷出烈焰，每秒造成 8 点火焰伤害。燃烧的目标受到额外伤害。",
        school: "毁灭系",
        cost: 14,
        enabled: true,
      },
    ],
   gear: [
      {
        id: "00012EB7",
        name: "铁剑",
        slot: "武器",
        count: 1,
        equipped: true,
        quest: false,
      },
      {
        id: "00012E49",
        name: "皮甲",
        slot: "护甲",
        count: 2,
        equipped: false,
        quest: false,
      },
    ],
  });
  const actor=(id,name,group,managed)=>{const row=actorRow(id,name,group,managed);return {...row,collect:collectOf(row.wardrobe)};};
  return {
    version: 4,
    automation:{defaults:{...defaultBehavior},history:[],playerCarried:220,playerCapacity:300},
    mode: "game",
    session: "fixture-save-1",
    ready: true,
    managerAvailable: true,
    location: "雪漫 · 桥接测试",
    truncated: false,
    settings: {
      savedOutfitChance:70,
      opacity: 82,
      font: 16,
      distance: 1,
      notifications: true,
      sandbox: true,
    },
    followers: [
      actor("000A2C94", "莱迪亚", "party", true),
      actor("00013485", "离队同伴", "registry", true),
      actor("00013486", "附近旅人", "nearby", false),
      actor("00013487", "附近同伴", "nearby", false),
    ],
    inventory: [
      {
        id: "000A26F1",
        name: "法术书：快速治疗",
        spellId: "0002F3B8",
        spellName: "快速治疗",
        description:
          '<font face="$HandwrittenFont">恢复之道始于专注。阅读本书以掌握快速治疗。</font>',
        spellDescription: "恢复施法者 50 点生命值。",
        school: "恢复系",
        cost: 73,
        count: 2,
        quest: false,
        equipped: false,
      },
      {
        id: "00012EB7",
        name: "铁剑",
        spellId: "",
        spellName: "",
        count: 2,
        quest: false,
        equipped: false,
      },
    ],
  };
}

// Mirrors the native headwear rule so the browser preview answers the way the game does: the head
// (30) and circlet (42) slots are hats, while hair (31), ears (43) and a whole robe that merely
// includes a hood are not. This load order writes an iron helmet as 0x1002 (hair + circlet).
const helmetSlots=(1<<(30-30))|(1<<(42-30)),robeBodySlot=1<<(32-30);
const isHeadwear=row=>Number.isInteger(row.mask)&&(row.mask&helmetSlots)!==0&&(row.mask&robeBodySlot)===0;
const allowsHelmet=f=>(f.behavior?.helmet)??true;
const unequipHeadwear=f=>{for(const i of f.wardrobe)if(i.equipped&&isHeadwear(i))i.equipped=false;};

// Browser-only simulation. Native integration is validated separately in Skyrim.
export function simulate(s, r) {
  if (r.session !== s.session) return { ok: false, message: "存档已变化" };
  const f = s.followers.find((f) => f.id === r.actorId);
  const ok = (message) => ({ ok: true, message });
  if(f&&r.command==='exchangeSupplies')return ok('游戏中将打开现有物品交换界面（界面预览）');
  if(r.command==="behaviorDefaults") {
    s.automation.defaults=structuredClone(r.settings);
    for(const a of s.followers)if(!a.behaviorOverride)a.behavior=structuredClone(r.settings);
    // The rule takes a helmet off at once, so the preview shows the same thing the game does.
    for(const a of s.followers)if(!allowsHelmet(a))unequipHeadwear(a);
    return ok("全队规则已保存（模拟）");
  }
  if (r.command === "settings") {
    s.settings[r.key] = r.value;
    return ok("设置已保存到当前存档（模拟）");
  }
  if (r.command === "group") {
    s.followers
      .filter((x) => x.managed && x.group === "party")
      .forEach((x) => {
        if (r.action !== "summon") x.waiting = r.action === "wait";
        else x.distance = 0;
      });
    return ok("队伍指令完成（模拟）");
  }
  if (!f) return { ok: false, message: "人物不存在" };
  if (r.command !== "adopt" && r.command !== "recruit" && !f.managed)
    return { ok: false, message: "请先纳入同行管理" };
  if(["saveNamedOutfit","removeNamedOutfit","applyNamedOutfit","outfitPart","changeOutfit","unequipOutfitPart","toggleWear"].includes(r.command)) {
    if(f.dead||f.unavailable||f.inCombat||f.group!=="party"||f.outfits.pending)return {ok:false,message:"同伴当前无法换装"};
    // The wear page works on the inventory rows, not on the outfit payload: one click is one
    // equip or unequip, armor replaces whatever occupies its slots, and quest gear stays on.
    if(r.command==="toggleWear") {
      const i=f.wardrobe.find(x=>x.key===r.itemKey);
      if(!i||i.inventoryCategory!=="apparel"||!Number.isInteger(i.mask)||i.mask<=0)return {ok:false,message:"物品已变化"};
      if(!i.equipped&&!allowsHelmet(f)&&isHeadwear(i))return {ok:false,message:"已禁止这位伙伴佩戴头盔：可在「行为管理 → 自动穿搭」里允许"};
      if(i.equipped) {
        if(i.quest)return {ok:false,message:"任务装备不能卸下"};
        i.equipped=false;
      } else {
        for(const old of f.wardrobe) {
          if(!old.equipped||!Number.isInteger(old.mask)||!(old.mask&i.mask))continue;
          if(old.quest)return {ok:false,message:"该部位被任务装备占用，无法更换"};
          old.equipped=false;
        }
        i.equipped=true;
      }
      return ok("穿脱操作已完成（模拟）");
    }
    const d=f.outfits;
    const wear=i=>{for(const old of d.items)if(old.mask&i.mask)old.equipped=false;i.equipped=true;};
    if(r.command==="unequipOutfitPart") {
      const i=d.items.find(i=>i.key===r.itemKey);
      if(!Number.isInteger(r.slot)||r.slot<30||r.slot>61||r.slot===39||!i||!i.equipped||i.quest||!(i.mask&2**(r.slot-30)))return {ok:false,message:"装备受保护或已不在当前槽位穿戴"};
      i.equipped=false;
    } else if(r.command==="removeNamedOutfit") {
      const index=d.presets.findIndex(p=>p.id===r.presetId);
      if(!Number.isInteger(r.presetId)||index<0)return {ok:false,message:"套装不存在"};
      d.presets.splice(index,1);
    } else if(r.command==="saveNamedOutfit") {
      const name=typeof r.name==="string"?r.name.trim():"";
      if(!name||name.length>30||d.presets.some(p=>p.name===name))return {ok:false,message:"套装名称无效或重复"};
      if(d.presets.length>=64)return {ok:false,message:"套装数量已达上限"};
      const worn=d.items.filter(i=>i.equipped);if(!worn.length)return {ok:false,message:"没有服饰"};
      worn.forEach(i=>i.favorite=true);
      // The signature is written for plain pieces too, so a set saved from now on is never mistaken
      // for one saved before signatures existed.
      d.presets.push({id:Math.max(0,...d.presets.map(p=>p.id))+1,name,
        items:worn.map(i=>({...structuredClone(i),enchant:i.enchant??0,charge:i.charge??0}))});
    } else {
      let keys=[];
      const protectedMask=d.items.filter(i=>i.quest&&i.equipped).reduce((mask,i)=>mask|i.mask,0);
      if(r.command==="outfitPart") {
        if(!Number.isInteger(r.slot)||r.slot<30||r.slot>61||r.slot===39)return {ok:false,message:"槽位无效"};
        // A named piece stays a direct manual pick; the random button draws on favorites only.
        const pool=d.items.filter(i=>i.available&&!i.quest&&!i.equipped&&!(i.mask&protectedMask)&&(i.mask&(2**(r.slot-30)))&&(r.itemKey?i.key===r.itemKey:i.favorite));
        if(!pool.length)return {ok:false,message:"没有可替换服饰"};keys=[pool[Math.floor(Math.random()*pool.length)].key];
      } else if(r.command==="applyNamedOutfit") {
        const preset=d.presets.find(p=>p.id===r.presetId);if(!preset)return {ok:false,message:"套装不存在"};
        // A set names instances: while an instance is still there it is used as saved. When its
        // identity was re-issued (a temper round trip duplicates it), the same base form with the
        // same enchantment signature stands in - never a differently enchanted copy. A spare copy
        // is what the set puts on; a worn one only satisfies the set, and naming it is what stops
        // the request from stripping the piece it is already wearing.
        const chosen=new Set();
        for(const saved of preset.items){
          const match=x=>saved.enchant!==undefined&&x.available&&x.form===saved.form&&sameEnchantment(saved,x);
          const i=d.items.find(x=>x.key===saved.key)??d.items.find(x=>match(x)&&!x.equipped)??d.items.find(match);
          if(!i||chosen.has(i.key))continue;
          chosen.add(i.key);keys.push(i.key);
        }
        // A saved set is a whole outfit: the request first takes off whatever the set does not name.
        for(const i of d.items) if(i.equipped&&!i.quest&&!keys.includes(i.key)) i.equipped=false;
      } else if(d.presets.length&&Math.random()*100<(s.settings.savedOutfitChance??70))keys=d.presets[Math.floor(Math.random()*d.presets.length)].items.map(i=>i.key);
      else {let occupied=protectedMask;for(const i of d.items.filter(i=>i.favorite&&i.available&&!i.quest&&!i.equipped).sort(()=>Math.random()-.5)){if(!(occupied&i.mask)){keys.push(i.key);occupied|=i.mask;}}}
      for(const key of keys){const i=d.items.find(i=>i.key===key);if(i&&i.available&&!i.quest&&!(i.mask&protectedMask))wear(i);}
    }
    for(const p of d.presets)for(const saved of p.items){const i=d.items.find(i=>i.key===saved.key);saved.available=!!i?.available;saved.equipped=!!i?.equipped;saved.favorite=!!i?.favorite;}
    return ok("穿搭操作已完成（模拟）");
  }
  switch (r.command) {
    case "favorite": {
      const item=f.wardrobe.find(i=>i.key===r.itemKey);
      if(!item)return {ok:false,message:"物品已变化"};
      item.favorite=r.value;break;
    }
    case "unprotect": {
      // The protection list is what the collection page edits: dropping the entry is what lets the
      // piece be sold again, exactly like the native command.
      const item=f.wardrobe.find(i=>i.key===r.itemKey);
      if(!item)return {ok:false,message:"这件装备不在保护清单中，请刷新后重试"};
      item.favorite=false;item.locked=false;
      if(f.collect)f.collect={...f.collect,items:f.collect.items.filter(i=>i.key!==r.itemKey)};
      break;
    }
    case "behavior":
      f.behaviorOverride=!r.inherit;f.behavior=structuredClone(r.inherit?s.automation.defaults:r.settings);
      if(!allowsHelmet(f))unequipHeadwear(f);
      break;
    case "deferRequest":f.request="";break;
    case "changeOutfit": {
      // Preview fixtures model body clothing and accessories as separate slots.
      // Native selection uses the actual armor slot masks and only ever wears favorites.
      const selected=[2,4].flatMap(category=>{
        if(f.wardrobe.some(i=>i.category===category&&i.quest&&i.equipped))return [];
        const pool=f.wardrobe.filter(i=>i.category===category&&!i.quest&&i.favorite);
        const choice=pool.find(i=>!i.equipped)??pool[0];return choice?[choice]:[];
      });
      if(!selected.some(i=>!i.equipped))return {ok:false,message:"没有可替换的服饰"};
      for(const choice of selected){
        for(const i of f.wardrobe)if(i.category===choice.category&&!i.quest)i.equipped=false;
        choice.equipped=true;
      }
      f.request="";break;
    }
    case "wardrobeTake": {
      const keys=new Set(),plan=[];
      let weight=0;
      for(const item of r.items) {
        const i=f.wardrobe.find(x=>x.key===item.key);
        if(!i||i.quest||i.equipped||keys.has(item.key)||!Number.isInteger(item.count)||item.count<1||item.count>i.count)return {ok:false,message:"物品或数量已变化"};
        keys.add(item.key);weight+=i.weight*item.count;plan.push([i,item.count]);
      }
      if(weight+s.automation.playerCarried>s.automation.playerCapacity)return {ok:false,message:"玩家剩余负重不足"};
      for(const [i,count] of plan)i.count-=count;
      f.wardrobe=f.wardrobe.filter(i=>i.count>0);s.automation.playerCarried+=weight;f.carried-=weight;f.request="";break;
    }
    case "adopt":
    case "recruit":
      if (f.dead || f.unavailable || (!f.managed && !f.canRecruit) ||
          (f.managed && f.group === "party"))
        return { ok: false, message: "此人物暂时不能招募" };
      if (!f.managed && s.followers.filter((x) => x.managed).length >= 64)
        return { ok: false, message: "64 位名册已满" };
      if (r.command === "adopt" && (f.managed || f.group !== "party" || !f.canRecruit))
        return { ok: false, message: "无法纳入管理" };
      if (r.command === "recruit" && !f.managed && f.group === "party")
        return { ok: false, message: "请使用纳入管理" };
      f.managed = true;
      f.limited = false;
      f.canRecruit = false;
      f.canRaise = true;
      f.group = "party";
      f.raised = f.levelCap !== null && f.originalMax > 0;
      f.canRaise = f.raised;
      if (f.raised) f.levelCap = Math.max(300, f.originalMax);
      break;
    case "dismiss":
      f.group = "registry";
      break;
    case "forget":
      s.followers = s.followers.filter((x) => x !== f);
      break;
    case "summon":
      f.distance = 0;
      break;
    case "wait":
      f.waiting = r.value;
      break;
    case "sandbox":
    case "leash":
    case "passive":
      f[r.command] = r.value;
      break;
    case "protection":
      f.essential = r.value;
      break;
    case "levelCap":
      f.raised = r.value;
      f.levelCap = r.value ? Math.max(300, f.originalMax) : f.originalMax;
      break;
    case "home":
      f.home = r.clear ? "未设置" : s.location;
      break;
    case "spell":
      f.spells.find((x) => x.id === r.entityId).enabled = r.value;
      break;
    case "teach": {
      const book = s.inventory.find((x) => x.id === r.entityId);
      if (
        !book ||
        book.count < 1 ||
        f.spells.some((x) => x.id === book.spellId)
      )
        return { ok: false, message: "法术书不可用或已经掌握" };
      book.count--;
      f.spells.push({
        id: book.spellId,
        name: book.spellName,
        school: book.school,
        cost: book.cost,
        description: book.spellDescription,
        enabled: true,
      });
      break;
    }
    case "equip":
      f.gear.find((x) => x.id === r.entityId).equipped = r.value;
      break;
    case "saveOutfit":
      f.outfit = f.gear.filter((x) => x.equipped).map((x) => x.id);
      f.presetCount = f.outfit.length;
      break;
    case "applyOutfit":
      f.gear.forEach((x) => (x.equipped = f.outfit.includes(x.id)));
      break;
    case "transfer": {
      const from = r.give ? s.inventory : f.gear,
        to = r.give ? f.gear : s.inventory;
      const item = from.find((x) => x.id === r.entityId);
      if (!item || item.count < r.count || r.count < 1)
        return { ok: false, message: "数量不足" };
      item.count -= r.count;
      const target = to.find((x) => x.id === item.id);
      if (target) target.count += r.count;
      else
        to.push({
          ...item,
          count: r.count,
          slot: "物品",
          spellId: "",
          spellName: "",
        });
      break;
    }
    default:
      return { ok: false, message: "未知指令" };
  }
  return ok("操作已完成（模拟）");
}
