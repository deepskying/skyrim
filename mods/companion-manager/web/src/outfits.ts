export type OutfitItem={key:string;form:number;name:string;mask:number;equipped:boolean;favorite:boolean;available:boolean;quest?:boolean;hidden?:boolean};
export type OutfitPreset={id:number;name:string;items:OutfitItem[]};
export type Outfits={items:OutfitItem[];presets:OutfitPreset[];pending:boolean};
const names:Record<number,string>={30:"头部",31:"头发",32:"身体",33:"手部",34:"前臂",35:"项链",36:"戒指",37:"脚部",38:"小腿",39:"盾牌",40:"尾部",41:"长发",42:"头环",43:"耳部"};
export const slotName=(slot:number)=>names[slot]??`槽位 ${slot}`;
export const outfitSlots=(mask:number)=>Array.from({length:32},(_,i)=>i+30).filter(s=>(mask&(2**(s-30)))!==0);
export const slotDescription=(mask:number)=>outfitSlots(mask).map(slotName).join("、");
export function validOutfits(value:unknown):value is Outfits {
 if(!value||typeof value!=="object")return false;
 const v=value as Outfits;
 const validItem=(i:OutfitItem)=>!!i&&typeof i.key==="string"&&/^[0-9A-F]{8}:[0-9A-F]{8}:[0-9A-F]{4}$/.test(i.key)&&
  typeof i.name==="string"&&i.name.length<=4096&&Number.isInteger(i.form)&&i.form>=0&&i.form<=0xffffffff&&
  Number.isInteger(i.mask)&&i.mask>0&&i.mask<=0xffffffff&&[i.available,i.equipped,i.favorite].every(x=>typeof x==="boolean")&&
  (i.quest===undefined||typeof i.quest==="boolean")&&(i.hidden===undefined||typeof i.hidden==="boolean");
 return typeof v.pending==="boolean"&&Array.isArray(v.items)&&v.items.length<=576&&v.items.every(validItem)&&
  Array.isArray(v.presets)&&v.presets.length<=64&&new Set(v.presets.map(p=>p?.id)).size===v.presets.length&&v.presets.every(p=>
   !!p&&Number.isInteger(p.id)&&p.id>0&&typeof p.name==="string"&&p.name.length<=120&&Array.isArray(p.items)&&p.items.length<=64&&p.items.every(validItem));
}
