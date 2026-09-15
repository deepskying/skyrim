import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './fixture.mjs';
import {inventoryCategories,inventoryMatches,categoryCounts,itemCategory} from '../src/inventory.ts';
import {validWardrobe,selectionTotals} from '../src/behavior.ts';

test('exact categories separate food from potions and arrows from miscellaneous without changing behavior masks',()=>{
 const items=fixture().followers[0].wardrobe;
 assert.ok(validWardrobe(items));
 const names=cat=>items.filter(i=>inventoryMatches(i,cat,'',false)).map(i=>i.name);
 assert.deepEqual(names('food'),['苹果派']);
 assert.deepEqual(names('potions'),['治疗药剂']);
 assert.deepEqual(names('weapons'),['铁剑','铁箭']);
 assert.ok(names('apparel').includes('银项链'));
 assert.deepEqual(names('misc'),['铁锭','金币']);
 for(const cat of ['scrolls','ingredients','books','keys'])assert.equal(names(cat).length,1);
 assert.equal(items.find(i=>i.name==='铁箭').category,128);
 const counts=categoryCounts(items,'',false);
 assert.equal(inventoryCategories.filter(c=>c.id!=='all').reduce((sum,c)=>sum+counts[c.id],0),items.length);
 assert.equal(counts.all,items.length); // stacks count once, not per arrow/coin
});
test('category, search and locking combine; hidden selections still count toward the transfer',()=>{
 const items=fixture().followers[0].wardrobe;
 const armor=items.find(i=>i.name==='皮甲'),food=items.find(i=>i.name==='苹果派');
 food.favorite=true;
 assert.deepEqual(items.filter(i=>inventoryMatches(i,'apparel','  皮甲 ',true)),[armor]);
 const counts=categoryCounts(items,'苹果',true);
 assert.equal(counts.food,1);assert.equal(counts.all,1);assert.equal(counts.potions,0);
 const selected={[armor.key]:1,[food.key]:2};
 const totals=selectionTotals(items,selected);
 items.filter(i=>inventoryMatches(i,'food','',true));
 assert.deepEqual(selectionTotals(items,selected),totals);
 assert.equal(totals.count,3);
});
test('unknown category is rejected and old snapshots remain readable without name-based guesses',()=>{
 const item=fixture().followers[0].wardrobe[0];
 assert.equal(validWardrobe([{...item,inventoryCategory:'invalid'}]),false);
 assert.equal(validWardrobe([{...item,inventoryCategory:'all'}]),false);
 const old={...item};delete old.inventoryCategory;
 assert.ok(validWardrobe([old]));assert.equal(itemCategory(old),'weapons');
 assert.equal(itemCategory({...old,category:16,name:'未知饮料'}),'misc');
});
