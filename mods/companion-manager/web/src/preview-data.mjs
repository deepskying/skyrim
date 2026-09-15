import { defaultBehavior } from "./behavior.ts";
export function fixture() {
  const actor = (id, name, group, managed) => ({
    id,
    name,
    en: id,
    role: "盾卫",
    race: "诺德人",
    mark: "伴",
    tint: "mint",
    group,
    managed,
    behavior: {...defaultBehavior},behaviorOverride:false,carried:182,capacity:300,activity:"idle",request:"",
    wardrobe:[
      {key:"00012EB7:00000014:0001",id:"00012EB7",name:"铁剑",inventoryCategory:"weapons",count:1,value:25,weight:9,category:1,equipped:true,quest:false,favorite:false,equipment:true},
      {key:"00012E49:00000014:0002",id:"00012E49",name:"皮甲",inventoryCategory:"apparel",count:1,value:125,weight:6,category:2,equipped:true,quest:false,favorite:true,equipment:true},
      {key:"00012E49:00000014:0003",id:"00012E49",name:"皮甲（火焰抗性）",inventoryCategory:"apparel",count:1,value:420,weight:6,category:2,equipped:false,quest:false,favorite:false,equipment:true},
      {key:"0001BE1A:00000000:0000",id:"0001BE1A",name:"精致服装",inventoryCategory:"apparel",count:2,value:55,weight:1,category:2,equipped:false,quest:false,favorite:true,equipment:true},
      {key:"0003B97C:00000000:0000",id:"0003B97C",name:"银项链",inventoryCategory:"apparel",count:1,value:120,weight:.5,category:4,equipped:false,quest:false,favorite:false,equipment:true},
      {key:"0005ACE4:00000000:0000",id:"0005ACE4",name:"铁锭",inventoryCategory:"misc",count:12,value:7,weight:1,category:128,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0003EADD:00000000:0000",id:"0003EADD",name:"治疗药剂",inventoryCategory:"potions",count:5,value:36,weight:.5,category:16,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"00064B2F:00000000:0000",id:"00064B2F",name:"苹果派",inventoryCategory:"food",count:3,value:5,weight:.5,category:16,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0000000F:00000000:0000",id:"0000000F",name:"金币",inventoryCategory:"misc",count:320,value:1,weight:0,category:8,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"000965A2:00000000:0000",id:"000965A2",name:"火球术卷轴",inventoryCategory:"scrolls",count:2,value:100,weight:.5,category:0,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"000727DF:00000000:0000",id:"000727DF",name:"蓝山花",inventoryCategory:"ingredients",count:8,value:2,weight:.1,category:32,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0001AFC4:00000000:0000",id:"0001AFC4",name:"法术书：治疗术",inventoryCategory:"books",count:1,value:50,weight:1,category:64,equipped:false,quest:false,favorite:true,equipment:false},
      {key:"000A7B33:00000000:0000",id:"000A7B33",name:"住宅钥匙",inventoryCategory:"keys",count:1,value:0,weight:0,category:0,equipped:false,quest:false,favorite:false,equipment:false},
      {key:"0001397D:00000000:0000",id:"0001397D",name:"铁箭",inventoryCategory:"weapons",count:30,value:1,weight:0,category:128,equipped:false,quest:false,favorite:false,equipment:false},
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
  return {
    version: 2,
    automation:{defaults:{...defaultBehavior},history:[],playerCarried:220,playerCapacity:300},
    mode: "game",
    session: "fixture-save-1",
    ready: true,
    managerAvailable: true,
    location: "雪漫 · 桥接测试",
    truncated: false,
    settings: {
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

// Browser-only simulation. Native integration is validated separately in Skyrim.
export function simulate(s, r) {
  if (r.session !== s.session) return { ok: false, message: "存档已变化" };
  const f = s.followers.find((f) => f.id === r.actorId);
  const ok = (message) => ({ ok: true, message });
  if(f&&r.command==='exchangeSupplies')return ok('游戏中将打开现有物品交换界面（界面预览）');
  if(r.command==="behaviorDefaults") {
    s.automation.defaults=structuredClone(r.settings);
    for(const a of s.followers)if(!a.behaviorOverride)a.behavior=structuredClone(r.settings);
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
  switch (r.command) {
    case "favorite": {
      const item=f.wardrobe.find(i=>i.key===r.itemKey);
      if(!item)return {ok:false,message:"物品已变化"};
      item.favorite=r.value;break;
    }
    case "behavior":
      f.behaviorOverride=!r.inherit;f.behavior=structuredClone(r.inherit?s.automation.defaults:r.settings);break;
    case "deferRequest":f.request="";break;
    case "changeOutfit": {
      const choices=f.wardrobe.filter(i=>i.favorite&&i.category===2&&!i.quest);
      if(!choices.length)return {ok:false,message:"请先收藏一件服装"};
      for(const i of f.wardrobe)if(i.category===2)i.equipped=false;
      choices[choices.length-1].equipped=true; f.request="outfit";break;
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
