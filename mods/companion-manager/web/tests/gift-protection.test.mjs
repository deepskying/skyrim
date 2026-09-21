import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../native/src/activities.inc',import.meta.url),'utf8');
test('sale candidate and commit both protect pending player gifts; all consumables excluded',()=>{
 const buys=source.slice(source.indexOf('bool Buys('),source.indexOf('int SalePrice('));
 assert.match(buys,/row.item->As<RE::AlchemyItem>\(\)/);
 for(const entry of ['bool HasSale(', 'void Sell(']){
  const body=source.slice(source.indexOf(entry),source.indexOf(entry)+220);
  assert.match(body,/pendingGiftLocks.contains/);
 }
});
test('only player-to-managed-companion equipment transfers auto-lock after the event',()=>{
 const event=source.slice(source.indexOf('ProcessEvent(const RE::TESContainerChangedEvent*'));
 assert.match(event,/oldContainer==0x14&&e->newContainer&&e->itemCount>0/);
 assert.match(event,/members.contains\(e->newContainer\)/);
 assert.match(event,/item->As<RE::TESObjectWEAP>\(\).*item->As<RE::TESObjectARMO>\(\)/);
 assert.match(event,/stamp!=epoch/);
 assert.ok(event.indexOf('++pendingGiftLocks')<event.indexOf('tasks->AddTask'));
 const gifts=source.slice(source.indexOf('void LockPlayerGift('),source.indexOf('class ActivityEvents'));
 assert.match(gifts,/std::count_if\(rows.begin\(\),rows.end\(\),exact\)==1/);
 assert.match(gifts,/favorites.push_back\(row.key\)/);
 assert.match(gifts,/represented<Count\(actor,item\)/);
});
test('locked equipment remains in outfit selection and manual unlock is retained',()=>{
 assert.match(source,/candidates.push_back\(\{i,.*row.favorite,row.equipped\}\)/);
 assert.match(source,/else if\(!value&&old!=list.end\(\)\) list.erase\(old\)/);
});
