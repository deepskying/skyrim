export type Section = "party" | "registry" | "nearby" | "settings";
export type Tab = "概况" | "行为" | "战斗" | "法术" | "装备" | "成长";
export type Spell = {
  description?: string;
  id?: string;
  name: string;
  school: string;
  cost: number;
  enabled: boolean;
};
export type Follower = {
  id: string;
  name: string;
  en: string;
  role: string;
  race: string;
  level: number;
  mark: string;
  tint: string;
  group: "party" | "registry" | "nearby";
  limited: boolean;
  waiting: boolean;
  passive: boolean;
  sandbox: boolean;
  leash: boolean;
  essential: boolean;
  distance: number | null;
  home: string;
  location: string;
  health: [number, number];
  magicka: [number, number];
  stamina: [number, number];
  spells: Spell[];
  gear: {
    id?: string;
    name: string;
    slot: string;
    equipped: boolean;
    count?: number;
  }[];
  raised: boolean;
  inCombat?: boolean;
  levelCap?: number | null;
  detailsTruncated?: boolean;
};
const base = {
  limited: false,
  waiting: false,
  passive: false,
  sandbox: true,
  leash: true,
  essential: true,
  home: "未设置",
  raised: false,
};
export const initialFollowers: Follower[] = [
  {
    ...base,
    id: "lydia",
    name: "莱迪亚",
    en: "LYDIA",
    role: "盾卫",
    race: "诺德人",
    level: 34,
    mark: "盾",
    tint: "blue",
    group: "party",
    distance: 8,
    location: "雪漫城 · 风宅附近",
    health: [312, 360],
    magicka: [72, 100],
    stamina: [185, 240],
    spells: [
      { name: "冰刺术", school: "毁灭系", cost: 30, enabled: true },
      { name: "治疗术", school: "恢复系", cost: 18, enabled: true },
    ],
    gear: [
      { name: "精钢剑", slot: "主手", equipped: true },
      { name: "精钢盾", slot: "副手", equipped: true },
      { name: "精钢盔甲", slot: "身体", equipped: true },
      { name: "狩猎弓", slot: "主手", equipped: false },
    ],
  },
  {
    ...base,
    id: "jzargo",
    name: "杰扎戈",
    en: "J’ZARGO",
    role: "战斗法师",
    race: "虎人",
    level: 32,
    mark: "焰",
    tint: "gold",
    group: "party",
    distance: 12,
    location: "雪漫城 · 风宅附近",
    health: [180, 210],
    magicka: [245, 280],
    stamina: [120, 150],
    spells: [
      { name: "火舌术", school: "毁灭系", cost: 14, enabled: true },
      { name: "闪电束", school: "毁灭系", cost: 35, enabled: true },
      { name: "石肤术", school: "变化系", cost: 80, enabled: false },
    ],
    gear: [
      { name: "学徒法袍", slot: "身体", equipped: true },
      { name: "精钢匕首", slot: "主手", equipped: true },
    ],
  },
  {
    ...base,
    id: "aela",
    name: "艾拉",
    en: "AELA",
    role: "游侠",
    race: "诺德人",
    level: 36,
    mark: "弓",
    tint: "mint",
    group: "party",
    distance: 19,
    location: "雪漫城 · 集市",
    health: [260, 290],
    magicka: [80, 80],
    stamina: [245, 280],
    spells: [],
    gear: [
      { name: "精灵弓", slot: "主手", equipped: true },
      { name: "古诺德护甲", slot: "身体", equipped: true },
    ],
  },
  {
    ...base,
    id: "serana",
    name: "瑟拉娜",
    en: "SERANA",
    role: "吸血鬼法师",
    race: "诺德人",
    level: 38,
    mark: "月",
    tint: "violet",
    group: "party",
    limited: true,
    distance: 6,
    location: "雪漫城 · 风宅附近",
    health: [280, 280],
    magicka: [190, 240],
    stamina: [140, 170],
    spells: [
      { name: "吸血术", school: "毁灭系", cost: 12, enabled: true },
      { name: "亡者复生", school: "召唤系", cost: 50, enabled: true },
    ],
    gear: [{ name: "吸血鬼皇家护甲", slot: "身体", equipped: true }],
  },
  {
    ...base,
    id: "faendal",
    name: "法恩达尔",
    en: "FAENDAL",
    role: "弓箭手",
    race: "木精灵",
    level: 20,
    mark: "林",
    tint: "mint",
    group: "registry",
    distance: 2100,
    home: "河木镇",
    location: "河木镇",
    health: [180, 180],
    magicka: [60, 60],
    stamina: [150, 150],
    spells: [],
    gear: [{ name: "狩猎弓", slot: "主手", equipped: true }],
  },
  {
    ...base,
    id: "uthgerd",
    name: "不屈者乌斯盖德",
    en: "UTHGERD",
    role: "重装战士",
    race: "诺德人",
    level: 30,
    mark: "剑",
    tint: "gold",
    group: "nearby",
    distance: 42,
    location: "雪漫城 · 旗帜母马",
    health: [300, 300],
    magicka: [50, 50],
    stamina: [200, 200],
    spells: [],
    gear: [{ name: "精钢巨剑", slot: "主手", equipped: true }],
  },
];
