const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('mods/magic-arrows/web/app.js','utf8');
const page=fs.readFileSync('mods/magic-arrows/web/index.html','utf8');
function extract(name){const start=source.indexOf('function '+name+'(');const end=source.indexOf('\nfunction ',start+1);return source.slice(start,end<0?source.length:end);}
const root={innerHTML:''};
const ctx={state:{orders:{available:true,limit:10000,paused:true,reason:'战斗中暂停',entries:[{spell:5,name:'火焰箭·火球术',family:'fire',total:12,remaining:3,label:'3'}]}},$:id=>id==='craft-orders'?root:null,escape:s=>String(s)};
vm.createContext(ctx);
vm.runInContext(extract('queuedForSpell')+'\n'+extract('orderCapacity')+'\n'+extract('craftOrders'),ctx);
assert.equal(ctx.queuedForSpell(5),3);
assert.equal(ctx.queuedForSpell(6),0);
assert.equal(ctx.orderCapacity(),10000);
ctx.craftOrders();
assert.match(root.innerHTML,/制作队列/);
assert.match(root.innerHTML,/火焰箭·火球术/);
assert.match(root.innerHTML,/剩余 3 \/ 12/);
assert.match(root.innerHTML,/战斗中暂停/);
assert.match(root.innerHTML,/data-order-family="fire"/);
ctx.state.orders.entries=[];ctx.craftOrders();assert.equal(root.innerHTML,'');
ctx.state.orders.entries=[{spell:5,name:'火球术',total:1,remaining:1}];ctx.craftOrders();
assert.doesNotMatch(root.innerHTML,/data-order-family=/);
assert.doesNotMatch(root.innerHTML,/undefined/);
ctx.state.orders={available:false};assert.equal(ctx.orderCapacity(),10000);

// The confirm button buys a queued order, never an immediate craft, and magicka on hand
// must not gate it: the queue pays one arrow at a time while the player keeps playing.
assert.match(source,/send\('orderStart',\{\.\.\.magicSelection\(\),runtime:!!q\.runtime,requestID:quoteVersion\}\)/);
assert.doesNotMatch(source,/send\('craft'/);
assert.doesNotMatch(source,/当前法力不足/);
assert.match(source,/reply\.type==='orderStart'/);
assert.match(source,/queued\+total>orderCapacity\(\)/);
assert.match(source,/state\.orders\?\.available===false/);
assert.match(source,/version:'1\.0\.0'/);
assert.match(page,/1\.0\.0 · 魔法箭工坊/);
assert.doesNotMatch(source,/0\.9\.9/);
assert.doesNotMatch(page,/0\.9\.9/);
const docs=fs.readFileSync('mods/magic-arrows/docs/craft-order.md','utf8');
assert.match(docs,/10000/);
const pack=fs.readFileSync('mods/magic-arrows/source/package_install.py','utf8');
assert.match(pack,/version=1\.0\.0/);
assert.match(pack,/MagicArrows-1\.0\.0-MO2\.zip/);
assert.match(pack,/docs\/craft-order\.md/);
console.log('PASS: queued start payload, queue list with family tint and pause reason, ceiling and co-save gates, 1.0.0 metadata');
