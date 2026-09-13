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
    raised: false,
    inCombat: false,
    detailsTruncated: false,
    distance: group === "registry" ? null : 12,
    home: "未设置",
    location: "雪漫 · 桥接测试",
    health: [240, 300],
    magicka: [0, 0],
    stamina: [180, 200],
    levelCap: 50,
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
    mode: "game",
    session: "fixture-save-1",
    ready: true,
    managerAvailable: true,
    location: "雪漫 · 桥接测试",
    truncated: false,
    settings: {
      opacity: 82,
      font: 15,
      distance: 1,
      notifications: true,
      sandbox: true,
    },
    followers: [
      actor("000A2C94", "莱迪亚", "party", true),
      actor("00013485", "离队同伴", "registry", true),
      actor("00013486", "附近旅人", "nearby", false),
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
    case "adopt":
    case "recruit":
      if (r.command === "adopt" && (f.managed || f.group !== "party" || !f.canRecruit))
        return { ok: false, message: "无法纳入管理" };
      f.managed = true;
      f.limited = false;
      f.canRecruit = false;
      f.canRaise = true;
      f.group = "party";
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
      f.levelCap = r.value ? 300 : 50;
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
