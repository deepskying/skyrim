const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('mods/magic-arrows/web/app.js','utf8');
function extract(name){const start=source.indexOf('function '+name+'(');const end=source.indexOf('\nfunction ',start+1);return source.slice(start,end<0?source.length:end);}
const batches=new Map(),stock=[{id:1,count:10},{id:2,count:120}],checkbox={checked:true};
const ctx={batches,baseArrows:()=>stock,document:{querySelector:()=>checkbox},Number,Math,String};
vm.createContext(ctx);vm.runInContext(extract('quantityLimit')+'\n'+extract('normalizeBaseInput'),ctx);
function input(id,value,commit=false){const x={dataset:{quantity:String(id)},value};ctx.normalizeBaseInput(x,commit);return x;}
assert.equal(input(1,'999').value,'10');assert.equal(batches.get(1),10);
assert.equal(input(2,'150').value,'90');assert.equal([...batches.values()].reduce((a,b)=>a+b),100);
assert.equal(input(1,'-5').value,'1');assert.equal(input(1,'3.8').value,'3');
assert.equal(input(1,'').value,'');assert.equal(batches.get(1),0);assert.equal(input(1,'',true).value,'1');
stock[0].count=0;assert.equal(input(1,'8',true).disabled,true);assert.equal(checkbox.checked,false);assert(!batches.has(1));
let closedDialogs=0,closedPanels=0;const esc={modalOpen:true,$:()=>null,closeDialog(){thisNotUsed=0;esc.modalOpen=false;closedDialogs++;},send:()=>closedPanels++,state:{nativeEscape:false,hotkey:{key:'W',shift:true,ctrl:false,alt:false}},demo:false};
vm.createContext(esc);vm.runInContext(extract('escapeLayer')+'\n'+source.slice(source.indexOf('function closeKey('),source.indexOf("document.addEventListener('keydown',closeKey")),esc);
function key(overrides={}){return {key:'Escape',code:'Escape',type:'keydown',repeat:false,preventDefault(){},stopPropagation(){},...overrides};}
esc.closeKey(key());assert.equal(closedDialogs,1);assert.equal(closedPanels,0);
esc.closeKey(key({type:'keyup'}));esc.closeKey(key({repeat:true}));assert.equal(closedPanels,0);
esc.closeKey(key());assert.equal(closedPanels,1);
esc.state.nativeEscape=true;esc.modalOpen=true;esc.closeKey(key());assert.equal(closedDialogs,1);esc.escapeLayer();assert.equal(closedDialogs,2);esc.closeKey(key({type:'keyup'}));assert.equal(closedPanels,1);esc.escapeLayer();assert.equal(closedPanels,2);
console.log('PASS: stock/per-batch clamp, empty editing/blur, depleted stock, Escape layers, repeat/key-up/native-DOM dedup');
