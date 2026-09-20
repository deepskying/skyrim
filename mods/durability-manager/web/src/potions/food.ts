import type { Potion, PotionState } from './types';
import { effectTraits } from './rules';
// Exact keyword identifiers only; display names are never used to guess a category.
export type FoodIconKind = 'soup' | 'drink' | 'wine' | 'vegetable' | 'fruit' | 'candy' | 'meat' | 'bread' | 'cheese' | 'fish' | 'pastry' | 'ingredient' | 'egg' | 'other';
// Ordered from specific prepared dishes to ingredients and broad fallback tags.
// Aliases audited against the enabled CACO, Gourmet, Food Expansion and OCF records/KID rules.
const categories: [string[], string, string, FoodIconKind][] = [
  [['VendorItemDrinkAlcohol','VendorItemDrinkAlcoholModerate','VendorItemDrinkAlcoholStrong','MAG_FoodTypeAle','OCF_AlchDrinkAlcohol','VendorItemFoodAlcohol','FoodTypeWine','VendorItemWine','VendorItemBeer'], 'drink','酒类','wine'],
  [['VendorItemDrinkMilk','OCF_AlchDrink_Milk','OCF_AlchDrink_MilkRaw'], 'drink','牛奶','drink'],
  [['VendorItemDrinkWater','OCF_AlchDrink_Water','OCF_AlchDrink_WaterRaw'], 'drink','水','drink'],
  [['OCF_AlchDrink_Tea'], 'drink','茶','drink'],
  [['OCF_AlchDrink_Coffee'], 'drink','咖啡','drink'],
  [['OCF_AlchDrink_Juice'], 'drink','果汁','drink'],
  [['VendorItemDrink','VendorItemDrinkNonAlcohol','OCF_AlchDrinkSoft','OCF_AlchDrink'], 'drink','饮料','drink'],
  [['VendorItemFoodStew','VendorItemFoodStewComplex','MAG_FoodTypeStew','MAG_FoodTypeStewHot','MAG_FoodTypeSoup','OCF_AlchFood_Stew','FoodTypeSoup'], 'food','汤／炖菜','soup'],
  [['VendorItemFoodDryGoods','VendorItemFoodFat','OCF_AlchFood_Ingredient','OCF_AlchFood_IngredientDry','OCF_AlchFood_IngredientWet','OCF_AlchFood_IngredientRaw'], 'food','烹饪原料','ingredient'],
  [['VendorItemFoodPastry','VendorItemFoodPastryLarge','MAG_FoodTypeDessert','OCF_AlchFood_Baked','AlaxFoodCake','AlaxFoodBreadCake','AlaxFoodCookie','AlaxFoodWaffle','AlaxFoodPie','AlaxFoodPorkPie','AlaxFoodCroissant','AlaxFoodHopias'], 'food','糕点／甜品','pastry'],
  [['VendorItemFoodBread','MAG_FoodTypeBread','OCF_AlchFood_Bread','AlaxFoodBaguette','AlaxFoodBread','AlaxFoodBreadRoll','AlaxFoodHalfBread','FoodTypeBread'], 'food','面包','bread'],
  [['VendorItemFoodCheese','MAG_FoodTypeCheese','OCF_AlchFood_Cheese','AlaxFoodCheeseWheel','AlaxFoodCheeseWedge','AlaxFoodCheeseHalfWheel','FoodTypeCheese'], 'food','奶酪','cheese'],
  [['VendorItemFoodFish','VendorItemFoodSeafood','MAG_FoodTypeFish','OCF_AlchFood_Fish','OCF_AlchFood_Seafood','OCF_AlchFood_FishRaw','OCF_AlchFood_SeafoodRaw','AlaxFoodCookedFish','AlaxFoodRawFish'], 'food','鱼／海鲜','fish'],
  [['VendorItemFoodEgg','OCF_AlchFood_Egg','OCF_AlchFood_EggRaw'], 'food','鸡蛋','egg'],
  [['VendorItemFoodMeat','VendorItemFoodMeatSmall','MAG_FoodTypeMeat','OCF_AlchFood_Meat','OCF_AlchFood_MeatSmall','OCF_AlchFood_MeatRaw','AlaxFoodCookedMeat','AlaxFoodRawMeat','AlaxFoodCookedLeg','AlaxFoodSausage','FoodTypeMeat'], 'food','肉类','meat'],
  [['VendorItemFoodFruit','MAG_FoodTypeFruit','OCF_AlchFood_Fruit','AlaxFoodApple','AlaxFoodAppleBitten','AlaxFoodGrapes','AlaxFoodPear','AlaxFoodStrawberry','AlaxFoodBlueberry','AlaxFoodApricot','AlaxFoodBlackberry','AlaxFoodCherry','AlaxFoodPeach','FoodTypeFruit'], 'food','水果','fruit'],
  [['VendorItemFoodVegetable','MAG_FoodTypeVegetable','OCF_AlchFood_Vegetable','AlaxFoodBeetroot','AlaxFoodButternut','AlaxFoodCarrot','AlaxFoodCucumber','AlaxFoodGinger','AlaxFoodGourd','AlaxFoodGreenBellPepper','AlaxFoodPotato','AlaxFoodPumpkin','AlaxFoodPurpleCarrot','AlaxFoodRadish','AlaxFoodRedBellPepper','AlaxFoodSweetPotato','AlaxFoodTurmeric','AlaxFoodTurnip','AlaxFoodArtichoke','AlaxFoodRedCabbage','AlaxFoodTomato','AlaxFoodGourdSlice','AlaxFoodGingerSlice','AlaxFoodPickle','FoodTypeVegetable'], 'food','蔬菜','vegetable'],
  [['OCF_AlchFood_Treat','FoodTypeCandy'], 'food','糖果／甜食','candy'],
  [['VendorItemFoodRaw'], 'food','生食','other'],
  [['VendorItemFoodCooked'], 'food','熟食','other'],
  [['VendorItemFoodPreserved'], 'food','腌制食品','other'],
  [['VendorItemFood','VendorItemFoodUncooked','VendorItemFoodPrepared','OCF_AlchFood','OCF_AlchFood_Meal'], 'food','食物','other'],
];
const normalizedCategories = categories.map(([names,type,label,icon]) => ({names:names.map(n => n.toLowerCase()),type,label,icon}));
export function foodCategory(p: Potion) {
  const keys = new Set((p.keywords ?? []).map(k => k.toLowerCase()));
  // Audited CACO dough is tagged Pastry + Raw, but is a cooking ingredient.
  if (p.localId === 0xCCA123 && p.source?.toLowerCase() === 'update.esm' && keys.has('vendoritemfoodpastry') && keys.has('vendoritemfoodraw'))
    return {type:'food',label:'烹饪原料',icon:'ingredient' as FoodIconKind};
  // Gourmet drugs are flagged Food in some overrides; do not call them ordinary food/drink.
  if (keys.has('mag_foodtypedrugs') || keys.has('mag_vendoritemdrugs') || keys.has('ocf_alchdrug'))
    return {type:'other',label:'特殊消耗品',icon:'other' as FoodIconKind};
  const match = normalizedCategories.find(({names}) => names.some(name => keys.has(name)));
  return {type:match?.type ?? 'other',label:match?.label ?? '其他',icon:match?.icon ?? 'other' as FoodIconKind};
}
export function matchesFood(p: Potion, filter: string) {
  if (filter === 'all') return true;
  if (['food','drink','other'].includes(filter)) return foodCategory(p).type === filter;
  return effectTraits(p).some(t => filter === 'buff'
    ? ['skill','resist'].includes(t.tone) || (t.tone === 'utility' && !t.id.startsWith('effect-'))
    : t.tone === filter);
}
const fx = (id: number, name: string, trait: string, magnitude: number, duration = 0) => ({ id,name,traits:[trait],description:'',magnitude,duration,area:0,hasMagnitude:true,hasDuration:duration > 0,harmful:false });
export const foodDemo: PotionState = { token:1, message:'浏览器预览 · 使用只改变演示库存', items:[
  {id:201,name:'蔬菜汤',count:4,keywords:['VendorItemFoodStew','VendorItemFood'],effects:[fx(1,'恢复生命','regen-health',1,720),fx(2,'恢复体力','regen-stamina',1,720)]},
  {id:202,name:'面包',count:6,keywords:['MAG_FoodTypeBread','VendorItemFood'],effects:[fx(3,'恢复生命','restore-health',2)]},
  {id:203,name:'烤鹿肉',count:3,keywords:['VendorItemFoodMeat','VendorItemFoodCooked'],effects:[fx(3,'恢复生命','restore-health',5)]},
  {id:204,name:'苹果',count:5,keywords:['AlaxFoodApple','VendorItemFood'],effects:[fx(3,'恢复生命','restore-health',2)]},
  {id:205,name:'蜜酒',count:3,keywords:['VendorItemDrinkAlcohol'],effects:[fx(4,'恢复体力','restore-stamina',20)]},
  {id:206,name:'魔力饮品（演示）',count:2,keywords:['VendorItemDrink'],effects:[fx(5,'恢复法力','restore-magicka',15)]},
  {id:207,name:'抗寒炖菜（演示）',count:1,keywords:['VendorItemFoodStew'],effects:[fx(6,'冰霜抗性','resist-frost',15,60)]},
  {id:208,name:'未知类型食品（演示）',count:2,keywords:[],effects:[]},
  {id:209,name:'胡萝卜（演示）',count:4,keywords:['VendorItemFoodVegetable','VendorItemFood'],effects:[fx(3,'恢复生命','restore-health',1)]},
  {id:210,name:'蜂蜜糖（演示）',count:3,keywords:['OCF_AlchFood_Treat','VendorItemFood'],effects:[fx(4,'恢复体力','restore-stamina',5)]},
  {id:211,name:'奶酪（演示）',count:3,keywords:['VendorItemFoodCheese'],effects:[fx(3,'恢复生命','restore-health',3)]},
  {id:212,name:'烤鱼（演示）',count:2,keywords:['VendorItemFoodFish','VendorItemFoodCooked'],effects:[fx(3,'恢复生命','restore-health',5)]},
  {id:213,name:'浆果派（演示）',count:2,keywords:['AlaxFoodPie'],effects:[fx(4,'恢复体力','restore-stamina',5)]},
  {id:214,name:'面粉（演示）',count:5,keywords:['VendorItemFoodDryGoods'],effects:[]},
  {id:215,name:'水煮蛋（演示）',count:2,keywords:['VendorItemFoodEgg'],effects:[fx(3,'恢复生命','restore-health',2)]},
].map(p => ({...p,weight:.5,value:8,source:'演示数据',usable:true,reason:''})) };
