const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const source=fs.readFileSync('mods/magic-arrows/web/app.js','utf8');
const handler=source.split('\n').find(x=>x.includes("d.querySelectorAll('[data-add-material]')"));
const limits=source.match(/const craftInputMax=(\d+),craftBatchMax=(\d+);/);
function scenario({target=10,units=25,stock=20,start=0,otherEnergy=0,busy=false,expected}){
 const button={dataset:{addMaterial:'7'}};const selection=new Map(start?[[7,start]]:[]);let quotes=0;
 const material={id:7,units,count:stock};
 const context={craftInputMax:Number(limits[1]),craftBatchMax:Number(limits[2]),d:{querySelectorAll:()=>[button]},Number,Math,ingredientSelection:selection,craftBusy:busy,usableMaterials:()=>[material],previewPlan:()=>({target,perArrow:10,energy:otherEnergy+(selection.get(7)||0)*units}),scheduleQuote:()=>++quotes};
 vm.runInNewContext(handler,context);button.onclick();assert.equal(selection.get(7)||0,expected);assert.equal(material.count,stock,'selection must not debit inventory');
 const before=selection.get(7)||0;button.onclick();assert.equal(selection.get(7)||0,before,'repeat click must not overfill');
 return quotes;
}
assert.equal(scenario({expected:4}),1);
scenario({stock:2,expected:2}); // partial output is allowed
scenario({start:1,otherEnergy:30,expected:3}); // other materials already contributed
scenario({units:30,expected:4}); // final whole ingredient rounds up
scenario({target:0,expected:0});
scenario({busy:true,expected:0});
scenario({start:4,expected:4});
scenario({stock:0,expected:0});
console.log('PASS: 8 material fill cases; no premature inventory debit or repeated-click overfill');
