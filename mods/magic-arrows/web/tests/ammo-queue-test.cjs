const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('mods/magic-arrows/web/app.js','utf8');
function extract(name){const start=source.indexOf('function '+name+'(');return source.slice(start,source.indexOf('\nfunction ',start+1));}
const calls=[],status={};const ctx={state:{ammoQueue:{available:true,enabled:true,ids:[1,2,3],limit:64}},send:(...x)=>calls.push(x),queuePanel(){},grid(){},$:()=>status};
vm.createContext(ctx);vm.runInContext(extract('queueIDs')+'\n'+extract('queueMove')+'\n'+extract('queueEdit'),ctx);
const arr=x=>Array.from(x);
assert.deepEqual(arr(ctx.queueMove([1,2,3],1,3)),[2,3,1]);
assert.deepEqual(arr(ctx.queueMove([1,2,3],3,1)),[3,1,2]);
assert.deepEqual(arr(ctx.queueMove([1,2,3],9,1)),[1,2,3]);
ctx.queueEdit([3,1,2,2]);assert.deepEqual(arr(ctx.state.ammoQueue.ids),[3,1,2]);assert.equal(calls.at(-1)[0],'queueEdit');assert.equal(calls.at(-1)[1].enabled,true);
ctx.queueEdit([3,2],false);assert.equal(calls.at(-1)[1].enabled,false);
ctx.queueEdit(Array.from({length:65},(_,i)=>i+1));assert.equal(calls.length,2);
ctx.state.ammoQueue.available=false;ctx.queueEdit([]);assert.equal(calls.length,2);
console.log('PASS: drag/button reorder semantics, add deduplication, removal, enable toggle, limit and unavailable bridge');
