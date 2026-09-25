export type BehaviorSettings = {
  loot:boolean;corpses:boolean;ground:boolean;containers:boolean;radius:number;
  minValue:number;minRatio:number;categories:number;sell:boolean;outfits:boolean;
  outfitHours:number;requests:boolean;
};
export const defaultBehavior:BehaviorSettings={loot:true,corpses:true,ground:true,containers:false,radius:40,minValue:20,minRatio:5,categories:255,sell:true,outfits:true,outfitHours:12,requests:true};
export const categories:[number,string,string][]=[[1,"武器","⚔"],[2,"护甲 / 服装","♜"],[4,"首饰","◇"],[8,"金币 / 宝石 / 灵魂石","◈"],[16,"药剂 / 食物","◉"],[32,"材料","❧"],[64,"书籍","▤"],[128,"杂物 / 箭矢","▧"]];
import { inventoryCategories, type ItemCategory } from "./inventory.ts";
export type ArmorType="light"|"heavy"|"jewelry"|"clothing"|"other";
// mask/armorRating/armorType/enchantment come from the native armor record and drive the wear page;
// rows for anything that is not armor simply leave them out.
export type WardrobeItem={key:string;id:string;name:string;count:number;value:number;weight:number;category:number;inventoryCategory?:ItemCategory;equipped:boolean;quest:boolean;favorite:boolean;equipment:boolean;
  mask?:number;armorRating?:number;armorType?:ArmorType;enchantment?:string};
export const armorTypes:ArmorType[]=["light","heavy","jewelry","clothing","other"];
export const armorTypeNames:Record<ArmorType,string>={light:"轻甲",heavy:"重甲",jewelry:"首饰",clothing:"服装",other:"其他"};
export type Automation={defaults:BehaviorSettings;history:string[];playerCarried:number;playerCapacity:number};
export function validBehavior(v:unknown):v is BehaviorSettings {
  if(!v||typeof v!=="object")return false;
  const x=v as Record<string,unknown>;
  return ["loot","corpses","ground","containers","sell","outfits","requests"].every(k=>typeof x[k]==="boolean")&&
    ([["radius",5,60],["minValue",0,10000],["minRatio",0,1000],["categories",0,255],["outfitHours",1,72]] as const).every(([k,lo,hi])=>typeof x[k]==="number"&&Number.isInteger(x[k])&&x[k]>=lo&&x[k]<=hi);
}
export function validWardrobe(v:unknown):v is WardrobeItem[] {
  if(!Array.isArray(v)||v.length>512)return false;
  const seen=new Set();
  return v.every(x=>{
    if(!x||typeof x!=="object"||typeof x.key!=="string"||!/^[0-9A-F]{8}:[0-9A-F]{8}:[0-9A-F]{4}$/.test(x.key)||seen.has(x.key)||
       typeof x.id!=="string"||!/^[0-9A-F]{8}$/.test(x.id)||typeof x.name!=="string"||
       !["equipped","quest","favorite","equipment"].every(k=>typeof x[k]==="boolean")||
       !["weight","value","count","category"].every(k=>typeof x[k]==="number"&&Number.isFinite(x[k])&&x[k]>=0)||!Number.isInteger(x.count))return false;
    if(x.inventoryCategory!==undefined&&!inventoryCategories.some(c=>c.id!=="all"&&c.id===x.inventoryCategory))return false;
    if(x.mask!==undefined&&(!Number.isInteger(x.mask)||x.mask<=0||x.mask>0xffffffff))return false;
    if(x.armorRating!==undefined&&(typeof x.armorRating!=="number"||!Number.isFinite(x.armorRating)||x.armorRating<0||x.armorRating>100000))return false;
    if(x.armorType!==undefined&&!armorTypes.includes(x.armorType))return false;
    if(x.enchantment!==undefined&&(typeof x.enchantment!=="string"||x.enchantment.length>4096))return false;
    seen.add(x.key);return true;
  });
}
export function selectionTotals(items:WardrobeItem[],selected:Record<string,number>) {
  return items.reduce((total,i)=>{const count=selected[i.key]??0;return {weight:total.weight+i.weight*count,value:total.value+i.value*count,count:total.count+count};},{weight:0,value:0,count:0});
}
