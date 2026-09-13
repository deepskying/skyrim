const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const source=fs.readFileSync('mods/magic-arrows/web/app.js','utf8');
const functions=source.split('\n').filter(line=>/^function (materialRank|materialKindLabel|usableMaterials)\(/.test(line)).join('\n');
const materials=[
 {id:1,name:'ingredient',kind:'ingredient',count:5,charges:{fire:100}},
 {id:2,name:'weak potion',kind:'potion',count:2,charges:{fire:20}},
 {id:3,name:'strong potion',kind:'potion',count:3,charges:{fire:60}},
 {id:4,name:'poison',kind:'poison',count:1,charges:{fire:30}},
 {id:5,name:'unmatched',kind:'potion',count:1,charges:{arcane:50}},
 {id:6,name:'empty',kind:'potion',count:0,charges:{fire:100}},
 {id:7,name:'food',kind:'food',count:5,charges:{fire:100}},
];
const context={state:{materials},selectedSpell:()=>({adapter:{family:'fire'}})};
vm.createContext(context);vm.runInContext(functions,context);
const result=context.usableMaterials();
assert.deepEqual(Array.from(result,m=>m.id),[3,2,4,1]);
assert.equal(context.materialKindLabel(result[0]),'药水');
assert.equal(context.materialKindLabel(result[2]),'毒药');
assert.equal(context.materialKindLabel(result[3]),'原材料');
assert.deepEqual(materials.map(m=>m.id),[1,2,3,4,5,6,7]);
context.selectedSpell=()=>({adapter:{family:'arcane'}});
assert.deepEqual(Array.from(context.usableMaterials(),m=>m.id),[5]);
console.log('PASS: potions first, potency ordering, matching families, empty/food exclusion, no mutation');
