const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('mods/magic-arrows/web/app.js','utf8');
const statement=source.split('\n').find(line=>line.includes('const baseUse=q?'));
function consumption(q,p={baseUse:new Map()}){return vm.runInNewContext(statement+'\nbaseUse;',{q,p,Map});}
const actual=consumption({bases:[{id:101,count:5},{id:102,count:2}],outputs:[{id:999,count:7}]});
assert.equal(actual.get(101),5);assert.equal(actual.get(102),2);assert(!actual.has(999));
assert.equal(consumption({outputs:[{id:101,count:7}]}).get(101),7);
assert.equal(consumption(null,{baseUse:new Map([[101,3]])}).get(101),3);
console.log('PASS: one merged output retains separate authoritative base consumption; legacy quotes and pending preview supported');
