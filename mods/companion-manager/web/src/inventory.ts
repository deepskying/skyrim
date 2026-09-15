import type { WardrobeItem } from "./behavior.ts";

export const inventoryCategories = [
  {id:"all",label:"全部",icon:"▦"},
  {id:"weapons",label:"武器",icon:"⚔"},
  {id:"apparel",label:"服装",icon:"♜"},
  {id:"potions",label:"药剂",icon:"◉"},
  {id:"scrolls",label:"卷轴",icon:"▱"},
  {id:"food",label:"食物",icon:"♨"},
  {id:"ingredients",label:"炼金材料",icon:"❧"},
  {id:"books",label:"书籍",icon:"▤"},
  {id:"keys",label:"钥匙",icon:"⚿"},
  {id:"misc",label:"杂物",icon:"◇"},
] as const;
export type InventoryCategory = typeof inventoryCategories[number]["id"];
export type ItemCategory = Exclude<InventoryCategory,"all">;
export function itemCategory(item:WardrobeItem):ItemCategory {
  // Older snapshots lack the exact form type. Do not guess food from its name.
  return item.inventoryCategory ?? ({1:"weapons",2:"apparel",4:"apparel",32:"ingredients",64:"books"} as Record<number,ItemCategory>)[item.category] ?? "misc";
}
export function inventoryMatches(item:WardrobeItem,category:InventoryCategory,query:string,locked:boolean) {
  return (category==="all"||itemCategory(item)===category)&&(!locked||item.favorite)&&
    item.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
}
export function categoryCounts(items:WardrobeItem[],query:string,locked:boolean) {
  return Object.fromEntries(inventoryCategories.map(c=>[c.id,items.filter(i=>inventoryMatches(i,c.id,query,locked)).length])) as Record<InventoryCategory,number>;
}
