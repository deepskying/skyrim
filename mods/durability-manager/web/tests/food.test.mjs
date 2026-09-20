import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
function source(name) { return ts.transpileModule(readFileSync(new URL(`../src/potions/${name}.ts`, import.meta.url),'utf8'), {compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText; }
const url = text => `data:text/javascript;base64,${Buffer.from(text).toString('base64')}`;
const rules = url(source('rules'));
const {foodCategory,matchesFood,foodDemo} = await import(url(source('food').replace("'./rules'", JSON.stringify(rules))));
test('food category uses exact keywords, prioritizes drinks and avoids guessing translated names', () => {
  assert.equal(foodCategory({keywords:['VendorItemFood','VendorItemFoodAlcohol']}).type,'drink');
  assert.equal(foodCategory({keywords:['FoodTypeSoup','VendorItemFood']}).label,'汤／炖菜');
  assert.equal(foodCategory({name:'蜜酒'}).type,'other');
  assert.equal(foodCategory({keywords:['UnknownFoodSoup']}).type,'other');
});
test('one food can match several effects while belonging to a single base category', () => {
  const soup=foodDemo.items[0];
  for (const f of ['all','food','health','stamina']) assert.equal(matchesFood(soup,f),true);
  for (const f of ['drink','other','magicka']) assert.equal(matchesFood(soup,f),false);
  assert.equal(matchesFood(foodDemo.items[6],'buff'),true);
  assert.equal(matchesFood(foodDemo.items[7],'other'),true);
});

test('eight food silhouettes follow subtype and unknown food retains a neutral icon', () => {
  const expected = {FoodTypeSoup:'soup',VendorItemDrink:'drink',VendorItemFoodAlcohol:'wine',FoodTypeVegetable:'vegetable',FoodTypeFruit:'fruit',FoodTypeCandy:'candy',FoodTypeMeat:'meat',FoodTypeBread:'bread'};
  for (const [keyword, icon] of Object.entries(expected)) assert.equal(foodCategory({keywords:['VendorItemFood',keyword]}).icon,icon);
  assert.equal(foodCategory({keywords:['VendorItemFood'],name:'酒味糖果'}).icon,'other');
  assert.equal(foodCategory({keywords:[]}).icon,'other');
  assert.equal(foodCategory({keywords:['VendorItemDrink','VendorItemFoodAlcohol']}).icon,'wine');
});

test('audited mod keywords and overlapping tags select the specific prepared food', () => {
  for (const [keywords, icon] of [
    [['VendorItemFood','VendorItemDrinkAlcohol'],'wine'],
    [['OCF_AlchDrink','OCF_AlchDrink_Milk'],'drink'],
    [['VendorItemFoodMeat','MAG_FoodTypeStew'],'soup'],
    [['AlaxFoodApple','AlaxFoodPie'],'pastry'],
    [['OCF_AlchFood_Treat','OCF_AlchFood_Baked'],'pastry'],
    [['VendorItemFoodMeat','OCF_AlchFood_Seafood'],'fish'],
    [['VendorItemFoodCooked','VendorItemFoodEgg'],'egg'],
    [['AlaxFoodCheeseWheel'],'cheese'],
    [['VendorItemFoodFat'],'ingredient'],
    [['VendorItemFood','MAG_FoodTypeDrugs'],'other'],
  ]) assert.equal(foodCategory({keywords}).icon,icon);
  const dough={source:'Update.esm',localId:0xCCA123,keywords:['VendorItemFoodPastry','VendorItemFoodRaw']};
  assert.equal(foodCategory(dough).icon,'ingredient');
  assert.equal(foodCategory({...dough,source:'Unrelated.esp'}).icon,'pastry');
  assert.equal(foodCategory({...dough,localId:123}).icon,'pastry');
});
