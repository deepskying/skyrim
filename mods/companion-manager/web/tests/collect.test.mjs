import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture,simulate} from '../src/preview-data.mjs';
import {readSnapshot} from '../src/bridge.ts';
const run=(s,command,data={})=>simulate(s,{session:s.session,actorId:s.followers[0].id,command,...data});

test('the protection list carries the locked gear with its reason, and unprotect drops it',()=>{
  const s=fixture(),f=s.followers[0];
  // Locked gear is what keeps a piece off the market, so the page reads the same rows.
  assert.ok(f.collect.items.length>0);
  const item=f.collect.items.find(i=>i.inventoryCategory==="apparel");
  assert.deepEqual(item.reasons,["手动锁定"]);
  assert.equal(f.wardrobe.find(i=>i.key===item.key).favorite,true);
  assert.ok(run(s,'unprotect',{itemKey:item.key}).ok);
  assert.equal(f.collect.items.some(i=>i.key===item.key),false);
  assert.equal(f.wardrobe.find(i=>i.key===item.key).favorite,false);
  assert.equal(run(s,'unprotect',{itemKey:'00000000:00000000:0000'}).ok,false);
  assert.ok(readSnapshot(s).snapshot);
});

test('a malformed protection row is dropped instead of blanking the page',()=>{
  const s=fixture();
  const broken=structuredClone(s);
  broken.followers[0].collect.items[0].reasons="套装";
  const read=readSnapshot(broken);
  assert.ok(read.snapshot);
  assert.ok(read.issues.some(text=>text.includes("保护清单")));
  const bad=structuredClone(s);
  bad.followers[0].collect.items[0].key="not-a-key";
  assert.ok(readSnapshot(bad).snapshot);
});
