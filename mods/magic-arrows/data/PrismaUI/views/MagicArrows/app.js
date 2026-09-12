(() => {
'use strict';
const $=id=>document.getElementById(id);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const colors={normal:'#9ca8b5',ice:'#55caff',shock:'#94aeff',poison:'#9afc48',wind:'#55e7b0',water:'#36d6e6',earth:'#d59a53',dark:'#a77cdd',arcane:'#f075da',fire:'#ff8b32',blood:'#ff4c69',holy:'#f0cc72',soul:'#b29afa'};
const labels={normal:'普通弹药',ice:'冰 · 霜晶箭',shock:'电 · 雷棱箭',poison:'毒 · 蛇牙箭',wind:'风 · 旋翼箭',water:'水 · 碧波箭',earth:'土 · 岩锥箭',dark:'暗 · 影镰箭',arcane:'奥术 · 奥术箭',fire:'火 · 火焰箭',blood:'嗜血 · 外观试作',holy:'圣辉 · 外观试作',soul:'星魂 · 外观试作'};
let state={version:'0.9.9',nativeEscape:true,arrows:[],spells:[],materials:[],recipes:[],loaded:false,hotkey:{key:'W',shift:true,ctrl:false,alt:false}};
let page='equipment',filter='all',search='',selected=0,mode='magic',spell=0,recipe=0;
let normalBatches=1,normalSearch='';
let equipPending=0;
let queueDrag=0;
let modalOpen=false,quoteTimer=0,quoteVersion=0,acceptedQuote=null,quoteBusy=false,craftBusy=false,quoteError='';
let spellFilter='candidate',spellSearch='';const batches=new Map();const ingredientSelection=new Map();
let readySent=false;const demo=new URLSearchParams(location.search).get('demo')==='1';
function bindingLabel(h){return [h.ctrl&&'Ctrl',h.shift&&'Shift',h.alt&&'Alt',h.key].filter(Boolean).join(' + ');}
function send(type,data={}){
    if(demo){demoAction(type,data);return;}
    if(typeof window.magicArrowsAction==='function')window.magicArrowsAction(JSON.stringify({type,...data}));
    else $('status').textContent='尚未连接游戏，请从 MO2 启动后重试。';
}
function releaseDescription(a){const route=a?.castRoute,continuous=a?.releaseMode==='sustained';return route==='actor'?`需命中角色，${continuous?'对命中角色持续释放 3 秒':'对命中角色施放法术'}；射向地面不触发。`:route==='area'?'在命中点释放范围法术。':route==='location'?`在命中位置${continuous?'持续施放 3 秒':'施放完整法术'}。`:continuous?'从命中点持续施放完整法术 3 秒。':'从命中点释放完整法术。';}
function arrow(family){
    const head=family==='soul'?'<path d="M156 22 Q170 5 192 18 M156 38 Q170 55 192 42"/>':family==='holy'?'<ellipse cx="158" cy="30" rx="3" ry="11"/>':'';
    return `<svg aria-hidden="true" viewBox="0 0 210 60" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M15 30H198M16 30L33 19 48 30 33 41Z"/><path d="M166 23L200 30 166 37 173 30Z" fill="currentColor" fill-opacity=".25"/>${head}${family==='blood'?'<path d="M47 30Q70 20 90 30T132 30T164 30"/>':''}</svg>`;
}
function header(){
    const texts={equipment:['YOUR QUIVER','箭矢装备','整理你的箭矢，为下一次冒险做好准备。'],craft:['THE WORKSHOP','箭矢制作','选择法术与基材，查看箭矢制作所需信息。'],settings:['PREFERENCES','工坊设置','按照你的习惯，调整工坊的唤起方式。']}[page];
    ['eyebrow','title','subtitle'].forEach((k,i)=>$(k).textContent=texts[i]);
    document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
    $('binding-label').textContent=bindingLabel(state.hotkey);
    $('connection').textContent=demo?'浏览器预览':state.loaded?'已连接游戏':'等待游戏数据';
}
function render(){header();if(page==='equipment')equipment();else if(page==='craft')craft();else settings();}
function queueIDs(){return state.ammoQueue?.ids||[];}
function queueAdd(id){const ids=queueIDs();queueEdit([...ids,id],ids.length?!!state.ammoQueue?.enabled:true);}
function queueMove(ids,from,to){const next=[...ids],index=next.indexOf(from),target=next.indexOf(to);if(index<0||target<0||index===target)return next;next.splice(index,1);next.splice(target,0,from);return next;}
function queueEdit(ids,enabled=!!state.ammoQueue?.enabled){
    if(!state.ammoQueue?.available)return;
    const unique=[...new Set(ids)];if(unique.length>(state.ammoQueue.limit||64)){$('status').textContent='队列最多 64 种箭矢';return;}
    state.ammoQueue={...state.ammoQueue,ids:unique,enabled};queuePanel();grid();send('queueEdit',{ids:unique,enabled});
}
function queuePanel(){
    const root=$('ammo-queue');if(!root)return;
    const q=state.ammoQueue||{},ids=queueIDs();
    const items=ids.map(id=>state.arrows.find(a=>a.id===id)||q.items?.find(a=>a.id===id)||{id,name:'来源缺失的箭矢',count:0,usable:false});
    root.innerHTML=`<div class="queue-heading"><div><h2>使用队列 <span>${ids.length} / ${q.limit||64}</span></h2><p>持弓优先队首 · 耗尽自动移除 · 拖拽排序</p></div><div class="queue-controls"><label><input id="queue-enabled" type="checkbox" ${q.enabled?'checked':''} ${q.available?'':'disabled'}>队列优先</label><button id="queue-start" class="primary" ${q.available&&items.some(a=>a.count>0&&a.usable!==false)?'':'disabled'}>从队首开始</button></div></div><div class="queue-list" role="list">${items.map((a,i)=>`<div class="queue-item ${a.equipped?'is-current':''} ${a.count<=0?'is-empty':''}" role="listitem" draggable="true" data-queue-item="${a.id}"><div class="queue-item-top"><span class="queue-position">${i+1} <span aria-hidden="true">⠿</span></span><span class="inventory-stock">×${a.count}</span></div><b>${escape(a.name)}</b><div class="queue-item-bottom"><span>${a.equipped?'使用中':a.usable===false?'不可用 · 跳过':a.count<=0?'缺货 · 跳过':'等待使用'}</span><div><button data-queue-up="${a.id}" aria-label="前移${escape(a.name)}" ${i?'':'disabled'}>←</button><button data-queue-down="${a.id}" aria-label="后移${escape(a.name)}" ${i<ids.length-1?'':'disabled'}>→</button><button data-queue-remove="${a.id}" aria-label="移除${escape(a.name)}">×</button></div></div></div>`).join('')||'<div class="queue-empty">点击下方箭矢的「＋ 加入队列」，安排使用顺序。</div>'}</div>${q.finished?'<p class="queue-finished">队列已用尽，请添加新的箭矢。</p>':''}`;
    $('queue-enabled').onchange=e=>queueEdit(ids,e.target.checked);
    $('queue-start').onclick=()=>{$('queue-start').disabled=true;send('queueStart');};
    root.querySelectorAll('[data-queue-remove]').forEach(b=>b.onclick=()=>queueEdit(ids.filter(id=>id!==Number(b.dataset.queueRemove))));
    for(const [key,step] of [['queueUp',-1],['queueDown',1]])root.querySelectorAll(key==='queueUp'?'[data-queue-up]':'[data-queue-down]').forEach(b=>b.onclick=()=>{const id=Number(b.dataset[key]),i=ids.indexOf(id);queueEdit(queueMove(ids,id,ids[i+step]));});
    root.querySelectorAll('[data-queue-item]').forEach(item=>{
        item.ondragstart=e=>{if(e.target.closest('button')){e.preventDefault();return;}queueDrag=Number(item.dataset.queueItem);e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',String(queueDrag));item.classList.add('dragging');};
        item.ondragover=e=>{if(queueDrag){e.preventDefault();e.dataTransfer.dropEffect='move';item.classList.add('drop-target');}};
        item.ondragleave=()=>item.classList.remove('drop-target');
        item.ondrop=e=>{e.preventDefault();const id=queueDrag;queueDrag=0;if(id)queueEdit(queueMove(ids,id,Number(item.dataset.queueItem)));};
        item.ondragend=()=>{queueDrag=0;root.querySelectorAll('.dragging,.drop-target').forEach(x=>x.classList.remove('dragging','drop-target'));};
    });
}
function equipment(){
    $('content').innerHTML=`<section id="ammo-queue" class="ammo-queue" aria-label="箭矢使用队列"></section><div class="toolbar"><div class="pills">${[['all','全部'],['normal','普通'],['magic','魔法']].map(([id,title])=>`<button data-filter="${id}" class="${filter===id?'active':''}">${title}</button>`).join('')}</div><input id="search" class="search" aria-label="搜索箭矢" placeholder="搜索箭矢…" value="${escape(search)}"></div><div class="summary"><span>库存 <b>${state.arrows.length}</b> 类</span><span>共 <b>${state.arrows.reduce((n,a)=>n+a.count,0)}</b> 支</span></div><div class="inventory-layout"><div id="grid" class="grid"></div><aside id="detail" class="detail"></aside></div>`;
    $('search').addEventListener('input',e=>{search=e.target.value;grid();});
    document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;equipment();});queuePanel();grid();
}
function grid(){
    const items=state.arrows.filter(a=>(filter==='all'||(filter==='normal'?a.family==='normal':a.family!=='normal'))&&a.name.toLowerCase().includes(search.toLowerCase()));
    $('grid').innerHTML=items.length?items.map(a=>`<div class="inventory-item"><button class="card inventory-card ${a.family==='normal'?'normal':''} ${a.equipped?'is-equipped':''}" data-arrow="${a.id}" aria-pressed="${!!a.equipped}" ${equipPending?'disabled':''} style="--arrow:${colors[a.family]||colors.normal}"><div class="inventory-card-top"><span class="type-badge ${a.family==='normal'?'mundane':'enchanted'}">${a.family==='normal'?'普通':a.usable===false?'封存 · 失效':a.adapter?.runtime?(a.adapter.releaseMode==='sustained'?'持续 3 秒封存':'原法术封存'):a.spellBound?'固定适配':'魔法 · 试作'}${a.bolt?'弩矢':'箭'}</span><span class="inventory-stock" title="库存 ${a.count} 支" aria-label="库存 ${a.count} 支">×${a.count}</span></div><div class="visual">${arrow(a.family)}</div><div class="card-body"><h3>${escape(a.name)}</h3><div class="meta"><span>${a.bolt?'弩矢':a.family==='normal'?'普通箭':'魔法箭'}</span>${a.equipped?'<span class="tag">已装备</span>':''}</div></div></button><button class="queue-add" data-queue-add="${a.id}" ${a.bolt||a.usable===false||a.count<=0||!state.ammoQueue?.available||queueIDs().includes(a.id)?'disabled':''}>${queueIDs().includes(a.id)?'已加入队列':'＋ 加入队列'}</button></div>`).join(''):`<div class="empty">${state.loaded?'没有符合条件的箭矢':'正在等待库存数据'}<br><small>${state.loaded?'可在右侧补充十二种外观试作箭。':'请从游戏中打开面板。'}</small></div>`;
    document.querySelectorAll('[data-arrow]').forEach(b=>b.onclick=()=>{selected=Number(b.dataset.arrow);detail();equipArrow(selected);});
    document.querySelectorAll('[data-queue-add]').forEach(b=>b.onclick=()=>queueAdd(Number(b.dataset.queueAdd)));detail();
}
function equipArrow(id){
    const a=state.arrows.find(a=>a.id===id);
    if(equipPending||!state.loaded||!a||a.count<=0||a.usable===false||a.equipped)return;
    if(!demo&&typeof window.magicArrowsAction!=='function'){$('status').textContent='尚未连接游戏';return;}
    equipPending=id;document.querySelectorAll('[data-arrow]').forEach(b=>b.disabled=true);
    $('status').textContent='正在关闭面板并装备箭矢…';send('equip',{id});
}
function detail(){
    const a=state.arrows.find(x=>x.id===selected);
    $('detail').innerHTML=a?`<div class="visual" style="--arrow:${colors[a.family]};color:${colors[a.family]}">${arrow(a.family)}</div><h2>${escape(a.name)}</h2><p>${labels[a.family]||labels.normal}</p><dl><dt>库存数量</dt><dd>${a.count}</dd><dt>基础物理伤害</dt><dd>${Number(a.damage).toFixed(0)}</dd><dt>使用武器</dt><dd>${a.bolt?'弩':'弓'}</dd></dl>${a.usable===false?'<p>原法术或基材引用不可用，这组箭已暂停使用，物品没有被删除。</p>':a.spellBound&&a.adapter?.runtime?`<p>${releaseDescription(a.adapter)}归属实际射手。</p>`:a.spellBound?`<p>命中点释放${escape(labels[a.family]||'元素')}效果，基础伤害 ${a.adapter?.damage||40}，范围 ${a.adapter?.radius||320}。普通弓即可使用；这是固定适配效果。</p>`:a.family!=='normal'?'<p>当前是发光外观试作箭，尚未封存法术。</p>':''}<p class="equip-state">${a.usable===false?'来源缺失或不兼容':a.equipped?'当前已装备':'点击卡片直接装备，面板会自动关闭。'}</p>`:'<h2>选择箭矢即可装备</h2><p>点击卡片直接装备，面板随后关闭；再次打开可查看已装备高亮。</p>';
    $('detail').innerHTML+=`<div class="supply"><p>外观测试补给<br>免费将十二种试作箭补足至各 100 支。</p><button id="supply" ${state.loaded?'':'disabled'}>补充试作箭</button></div>`;
    $('supply').onclick=()=>send('supply');
}
function options(items,value,placeholder){return `<option value="0">${placeholder}</option>`+items.map(x=>`<option value="${x.id}" ${x.id===value?'selected':''}>${escape(x.name)}${x.count!==undefined?' ×'+x.count:''}</option>`).join('');}
function craft(){
    $('content').innerHTML=`<div class="toolbar"><div class="pills"><button data-mode="magic" class="${mode==='magic'?'active':''}">魔法箭矢</button><button data-mode="normal" class="${mode==='normal'?'active':''}">普通箭矢</button></div></div>${mode==='magic'?'<div class="notice">符合条件的已学法术可直接封存。持续型箭在命中点施放 3 秒；加入材料充能后，按实际产量确认制作。</div>':''}<p class="muted">封存身份：${state.runtimeSlots?`${state.runtimeSlots.capacity-state.runtimeSlots.free} / ${state.runtimeSlots.capacity} 组${state.runtimeSlots.ready?'':' · 尚未就绪'}`:'等待游戏数据'}。同一法术与基材重复制作可继续叠加。</p><div id="craft-body"></div>`;
    document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;state.quote=null;state.normalQuote=null;craft();send('workshopMode',{mode});});
    if(mode==='magic'){
        $('craft-body').innerHTML=`<div class="magic-workshop"><section><div class="toolbar"><div class="pills">${[['candidate','可制作'],['review','待适配'],['excluded','暂不支持']].map(([id,name])=>`<button data-spell-filter="${id}" class="${spellFilter===id?'active':''}">${name} ${state.spells.filter(s=>eligibility(s).status===id).length}</button>`).join('')}</div><input id="spell-search" class="search" placeholder="搜索法术或来源模组…" aria-label="搜索法术" value="${escape(spellSearch)}"></div><p class="muted">“可制作”只显示已支持的法术，其余分类列出尚未支持的法术及原因。</p><div id="spell-grid" class="grid spell-grid"></div></section></div>`;
        document.querySelectorAll('[data-spell-filter]').forEach(b=>b.onclick=()=>{spellFilter=b.dataset.spellFilter;spell=0;state.quote=null;craft();});
        $('spell-search').oninput=e=>{spellSearch=e.target.value;spellGrid();};spellGrid();
    }else normalWorkshop();
}
function normalWorkshop(){
    $('craft-body').innerHTML=`<div class="notice">便携工坊沿用锻造台配方的材料与条件；不额外收取金币或魔法值，不增加锻造经验。特殊工作台配方请在原工作台制作。</div><div class="workshop-layout"><section><input id="normal-search" class="search" placeholder="搜索普通箭或配方来源…" aria-label="搜索普通箭" value="${escape(normalSearch)}"><div id="normal-grid" class="grid spell-grid"></div></section><aside id="normal-detail" class="detail craft-detail"></aside></div>`;
    $('normal-search').oninput=e=>{normalSearch=e.target.value;normalGrid();};normalGrid();
}
function normalGrid(){
    const items=state.recipes.filter(r=>`${r.name} ${r.source||''}`.toLowerCase().includes(normalSearch.toLowerCase()));
    $('normal-grid').innerHTML=items.map(r=>`<button class="card ${recipe===r.id?'selected':''}" data-recipe="${r.id}"><div class="visual">${arrow('normal')}</div><div class="card-body"><h3>${escape(r.name)}</h3><p class="spell-source">${escape(r.source||'来源未提供')}</p><div class="meta"><span>${r.craftable?'可制作':escape(r.reason||'暂不可制作')}</span><span>每批 ${r.yield} 支</span></div></div></button>`).join('')||'<div class="empty">未找到普通箭锻造台配方</div>';
    document.querySelectorAll('[data-recipe]').forEach(b=>b.onclick=()=>{recipe=Number(b.dataset.recipe);normalBatches=1;state.normalQuote=null;normalGrid();});normalDetail();
}
function normalDetail(){
    const r=state.recipes.find(x=>x.id===recipe);
    if(!r){$('normal-detail').innerHTML='<h2>选择普通箭配方</h2><p>查看每批产出、材料与当前可制作批数。</p>';return;}
    const q=state.normalQuote?.recipe===recipe&&state.normalQuote?.batches===normalBatches?state.normalQuote:null;
    $('normal-detail').innerHTML=`<h2>${escape(r.name)}</h2><p>${escape(r.source||'')} · 每批 ${r.yield} 支</p><div class="recipe-items">${r.ingredients.map(i=>`<div><span>${escape(i.name)}</span><span class="${i.have<i.need*normalBatches?'warn':''}">${i.have} / ${i.need*normalBatches}</span></div>`).join('')}</div><p>材料显示：可用库存 / 本次所需</p>${r.conditions?.length?`<div class="recipe-conditions"><h3>配方条件</h3>${r.conditions.map(c=>`<p class="${c.met?'condition-met':'warn'}">${c.met?'✓':'○'} ${escape(c.name)} · ${c.met?'已满足':'未满足'}${c.orNext?'（或下一项）':''}</p>`).join('')}</div>`:!r.reason||r.ingredients.length?'<p class="condition-met">无额外天赋／任务条件</p>':''}${r.reason?`<div class="notice">${escape(r.reason)}</div>`:''}<label class="field">制作批数<input id="normal-batches" type="number" min="1" max="${Math.max(1,r.maxBatches||0)}" step="1" value="${normalBatches}" ${r.craftable?'':'disabled'}></label><p>本次获得 ${normalBatches*r.yield} 支；当前最多 ${r.maxBatches||0} 批</p><button id="normal-quote" class="wide" ${r.craftable&&Number.isInteger(normalBatches)&&normalBatches>0&&normalBatches<=r.maxBatches?'':'disabled'}>计算费用</button>${q?`<div class="notice"><p>消耗：${q.ingredients.map(i=>`${escape(i.name)} ×${i.count}`).join('，')}</p><p>获得：${escape(q.name)} ×${q.total}</p></div><button id="normal-confirm" class="primary wide">确认制作 ${q.total} 支</button>`:'<p>点击确认前不会扣除材料。</p>'}`;
    $('normal-batches').onchange=e=>{const n=Number(e.target.value);normalBatches=Number.isInteger(n)&&n>0?Math.min(n,Math.max(1,r.maxBatches||0)):1;state.normalQuote=null;normalDetail();};
    $('normal-quote').onclick=()=>{$('normal-quote').disabled=true;send('normalQuote',{recipe,batches:normalBatches});};
    if($('normal-confirm'))$('normal-confirm').onclick=()=>{$('normal-confirm').disabled=true;send('normalCraft',{token:q.token});};
}

function eligibility(s){
    const info=s.eligibility||{status:'review',reasons:['尚无筛选结果，请更新插件并重启游戏']};
    // Fail closed for older or inconsistent native snapshots: a structural
    // candidate without the final craftable flag must not enter the craftable tab.
    return {...info,status:s.craftable===true?'candidate':info.status==='excluded'?'excluded':'review'};
}
function spellGrid(){
    const names={candidate:'可制作',review:'待适配',excluded:'暂不支持'};
    const items=state.spells.filter(s=>eligibility(s).status===spellFilter&&`${s.name} ${s.source||''}`.toLowerCase().includes(spellSearch.toLowerCase()));
    $('spell-grid').innerHTML=items.map(s=>`<button class="card spell-card ${spell===s.id?'selected':''}" data-spell="${s.id}"><span class="spell-sigil" aria-hidden="true">✧</span><div class="card-body"><h3>${escape(s.name)}</h3><p class="spell-source">${escape(s.source||'来源未提供')}</p><div class="meta"><span>${eligibility(s).releaseMode==='sustained'?'持续型 · ':''}${s.craftable?'可制作':names[eligibility(s).status]||'待适配'}${s.adapter?.castRoute==='actor'?' · 需命中角色':s.adapter?.castRoute==='area'?' · 落点范围':''}</span></div></div></button>`).join('')||'<div class="empty">没有符合条件的已学法术<br><small>可以查看其他筛选页了解排除原因。</small></div>';
    document.querySelectorAll('[data-spell]').forEach(b=>b.onclick=()=>{spell=Number(b.dataset.spell);batches.clear();ingredientSelection.clear();acceptedQuote=null;quoteError='';modalOpen=true;spellGrid();scheduleQuote();});craftDetail();
}
function selectedSpell(){return state.spells.find(s=>s.id===spell);}
function baseArrows(){const s=selectedSpell();return state.arrows.filter(a=>a.count>0&&(s?.adapter?.runtime?a.runtimeBase:a.fireballBase));}
function usableMaterials(){const a=selectedSpell()?.adapter;return state.materials.map(m=>({...m,units:m.charges?.[a?.family||'fire']??(a?.family&&a.family!=='fire'?0:m.units)})).filter(m=>m.units>0&&m.count>0);}
function magicSelection(){return {spell,bases:[...batches].map(([id,count])=>({id,count})),materials:[...ingredientSelection].map(([id,count])=>({id,count}))};}
function closeDialog(){
    modalOpen=false;clearTimeout(quoteTimer);++quoteVersion;quoteBusy=false;craftBusy=false;acceptedQuote=null;quoteError='';
    const d=$('magic-dialog');if(d){d.close();d.remove();}
    document.querySelector(`[data-spell="${spell}"]`)?.focus();
}
function craftDetail(){
    if(!modalOpen)return;
    if($('magic-dialog')){updateMagicSummary();return;}
    const s=selectedSpell();if(!s){closeDialog();return;}
    const d=document.createElement('dialog');d.id='magic-dialog';d.setAttribute('aria-labelledby','magic-dialog-title');
    d.innerHTML=`<div class="magic-dialog-head"><h2 id="magic-dialog-title">${escape(s.name)}</h2><button id="dismiss-magic" aria-label="关闭制作清单">×</button></div>${s.craftable?`<div id="unit-costs" class="unit-costs">${unitCostsMarkup(s.adapter)}</div><div class="magic-dialog-body"><section><p class="material-hint">${releaseDescription(s.adapter)}</p><h3>基材箭矢 <span id="magic-total"></span></h3><p class="material-hint">数量为制作上限，多种基材按勾选顺序使用。</p><div class="magic-list">${baseArrows().map(a=>`<div class="magic-item"><label><input type="checkbox" data-base="${a.id}"><span>${escape(a.name)}<small>库存 ${a.count} · 本次 <b data-base-use="${a.id}">0</b></small></span></label><input type="number" data-quantity="${a.id}" aria-label="${escape(a.name)}数量" min="1" max="${Math.min(100,a.count)}" step="1" value="1" disabled></div>`).join('')||'<p>没有可用的基材箭矢。</p>'}</div></section><section class="charge-section"><div class="charge-heading"><h3>材料充能</h3><strong id="charge-value"></strong></div><div id="charge-bar" class="charge-bar" role="meter" aria-label="已添加材料充能" aria-valuemin="0" aria-valuemax="1" aria-valuenow="0"><span></span></div><p id="charge-output" class="charge-output"></p><div class="material-pool">${usableMaterials().map(m=>`<button class="material-card" data-add-material="${m.id}" aria-label="添加${escape(m.name)}"><span class="material-card-heading"><b>${escape(m.name)}</b><span class="material-stock" data-material-stock="${m.id}" title="剩余可添加 ${m.count} 份">×${m.count}</span></span><span>每份 +${m.units} 充能</span></button>`).join('')||'<p>没有已发现适用功效的炼金材料。</p>'}</div><h3 class="basket-heading">待消耗材料</h3><div id="material-basket" class="material-basket"></div><p id="charge-excess" class="material-hint"></p></section></div><div class="magic-costs">${resourceMeter('mana','法力值')}${resourceMeter('gold','金币')}</div><div class="magic-dialog-foot"><p id="magic-error" role="status"></p><button id="confirm-craft" class="primary" disabled>确认制作</button></div>`:`<div class="magic-dialog-body unsupported"><p>${eligibility(s).reasons.map(escape).join('<br>')}</p></div>`}`;
    document.body.append(d);d.showModal();$('dismiss-magic').onclick=closeDialog;
    d.addEventListener('cancel',e=>e.preventDefault());
    d.querySelectorAll('[data-base]').forEach(input=>input.onchange=()=>{const id=Number(input.dataset.base);const n=d.querySelector(`[data-quantity="${id}"]`);n.disabled=!input.checked;if(input.checked)normalizeBaseInput(n,true);else batches.delete(id);scheduleQuote();});
    d.querySelectorAll('[data-quantity]').forEach(input=>{input.oninput=()=>{normalizeBaseInput(input);scheduleQuote();};input.onblur=()=>{const before=batches.get(Number(input.dataset.quantity));normalizeBaseInput(input,true);if(before!==batches.get(Number(input.dataset.quantity)))scheduleQuote();};});
    d.querySelectorAll('[data-add-material]').forEach(button=>button.onclick=()=>{const id=Number(button.dataset.addMaterial);const m=usableMaterials().find(m=>m.id===id);const n=ingredientSelection.get(id)||0;if(craftBusy||!m||n>=Math.min(10000,m.count))return;const p=previewPlan(),needed=Math.max(0,p.target*p.perArrow-p.energy);const add=Math.min(Math.max(0,Math.min(10000,m.count)-n),Math.ceil(needed/m.units));if(!Number.isFinite(add)||add<=0)return;ingredientSelection.set(id,n+add);scheduleQuote();});
    $('material-basket')?.addEventListener('click',e=>{const button=e.target.closest('[data-remove-material]');if(!button||craftBusy)return;const id=Number(button.dataset.removeMaterial),n=ingredientSelection.get(id)||0;if(n>1)ingredientSelection.set(id,n-1);else ingredientSelection.delete(id);scheduleQuote();});
    if($('confirm-craft'))$('confirm-craft').onclick=()=>{
        if(!acceptedQuote||quoteBusy||craftBusy)return;
        const q=acceptedQuote;craftBusy=true;updateMagicSummary();
        send('craft',{token:q.token,runtime:!!q.runtime,requestID:quoteVersion});
    };
    updateMagicSummary();
}
function quantityLimit(id){
    const stock=baseArrows().find(a=>a.id===id)?.count||0;
    const others=[...batches].reduce((sum,[key,n])=>sum+(key!==id&&Number.isFinite(n)?n:0),0);
    return Math.max(0,Math.min(stock,100-others));
}
function normalizeBaseInput(input,commit=false){
    const id=Number(input.dataset.quantity),limit=quantityLimit(id);input.max=String(limit);
    if(!limit){batches.delete(id);input.value='1';input.disabled=true;const box=document.querySelector(`[data-base="${id}"]`);if(box)box.checked=false;return;}
    if(input.value===''&&!commit){batches.set(id,0);return;}
    const raw=Number(input.value),n=Math.min(limit,Math.max(1,Number.isFinite(raw)?Math.floor(raw):1));
    input.value=String(n);batches.set(id,n);
}
function unitCostsMarkup(a){
    const icon=path=>`<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
    const entries=[['charge','充能',a?.charge??10,icon('<path d="m13 2-8 12h6l-1 8 9-13h-7z"/>')],['mana','法力',a?.mana??12,icon('<path d="M12 2C9 7 5 10 5 15a7 7 0 0 0 14 0c0-5-4-8-7-13Z"/>')],['gold','金币',a?.gold??5,icon('<circle cx="12" cy="12" r="9"/><path d="M15 8h-4a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9m3-10v12"/>')]];
    return `<span class="unit-cost-caption">每支消耗</span>${entries.map(([key,label,value,svg])=>`<span class="unit-cost unit-${key}" title="每支${label} ${value}" aria-label="每支${label} ${value}">${svg}<b>${value}</b><small>${label}</small></span>`).join('')}`;
}
function previewPlan(){
    const a=selectedSpell()?.adapter;let target=0,error='',energy=0;const arrows=baseArrows(),materials=usableMaterials(),used=new Map(),baseUse=new Map();
    for(const [id,count] of batches){const stock=arrows.find(x=>x.id===id)?.count??0;if(!Number.isInteger(count)||count<1||count>stock)error='请填写有效的箭矢数量';target+=Number.isFinite(count)?count:0;}
    if(target>100)error='每次最多制作 100 支';
    for(const [id,count] of ingredientSelection){const m=materials.find(x=>x.id===id);if(!m||!Number.isInteger(count)||count<1||count>Math.min(m.count,10000)){error='待消耗材料库存不足，请减少数量';continue;}energy+=count*m.units;used.set(id,count);}
    const perArrow=a?.charge??10,total=Math.max(0,Math.min(target,Math.floor(energy/perArrow)));
    let remaining=total;for(const [id,count] of batches){const take=Math.min(remaining,count);baseUse.set(id,take);remaining-=take;}
    const cost={gold:total*(a?.gold??5),mana:total*(a?.mana??12)};
    if(!error&&!target)error='请选择基材箭矢和数量';
    if(!error&&!total)error=`请添加材料，至少需要 ${perArrow} 充能制作 1 支`;
    if(!error&&state.resources&&cost.mana>state.resources.magicka)error='当前法力不足';
    if(!error&&state.resources&&cost.gold>state.resources.gold)error='金币不足';
    return {total,target,energy,perArrow,cost,used,baseUse,error};
}
function resourceMeter(id,label){
    return `<div class="resource-cost"><div class="resource-heading"><span>${label}</span><span id="magic-${id}-current"></span></div><div id="magic-${id}-bar" class="resource-bar" role="meter" aria-label="${label}制作后剩余" aria-valuemin="0" aria-valuemax="1" aria-valuenow="0"><span class="resource-remaining"></span><span class="resource-spending"></span></div><div class="resource-legend"><span class="remaining-label" id="magic-${id}-remaining"></span><span class="spending-label" id="magic-${id}"></span></div><p id="magic-${id}-shortage" class="resource-shortage" hidden></p></div>`;
}
function updateResourceMeter(id,current,required){
    const known=Number.isFinite(current),held=known?Math.max(0,current):0,need=Math.max(0,required),remaining=Math.max(0,held-need);
    const format=n=>Number(n.toFixed(1)).toLocaleString('zh-CN');
    const bar=$(`magic-${id}-bar`);
    bar.querySelector('.resource-remaining').style.width=`${held>0?100*remaining/held:0}%`;
    bar.querySelector('.resource-spending').style.width=`${held>0?100*Math.min(need,held)/held:0}%`;
    bar.setAttribute('aria-valuemax',Math.max(1,held));bar.setAttribute('aria-valuenow',remaining);
    bar.setAttribute('aria-valuetext',known?`当前 ${format(held)}，消耗 ${format(need)}，剩余 ${format(remaining)}${need>held?'，不足 '+format(need-held):''}`:'等待当前资源数据');
    $(`magic-${id}-current`).textContent=`当前 ${known?format(held):'—'}`;
    $(`magic-${id}-remaining`).textContent=`剩余 ${known?format(remaining):'—'}`;
    $(`magic-${id}`).textContent=`消耗 ${format(need)}`;
    const warning=$(`magic-${id}-shortage`);warning.hidden=!known||need<=held;warning.textContent=warning.hidden?'':`还差 ${format(need-held)}`;
}
function updateMagicSummary(){
    if(!$('magic-mana'))return;
    const p=previewPlan(),q=acceptedQuote;
    if($('unit-costs'))$('unit-costs').innerHTML=unitCostsMarkup(selectedSpell()?.adapter);
    const total=q?.total??p.total;
    $('magic-total').textContent=`· 计划 ${p.target} 支`;
    updateResourceMeter('mana',state.resources?.magicka,q?.magicka??p.cost.mana);
    updateResourceMeter('gold',state.resources?.gold,q?.gold??p.cost.gold);
    const baseUse=q?new Map((q.bases??q.outputs).map(b=>[b.id,b.count])):p.baseUse;
    document.querySelectorAll('[data-base-use]').forEach(el=>el.textContent=baseUse.get(Number(el.dataset.baseUse))??0);
    const capacity=p.target*p.perArrow,energy=q?.suppliedCharge??p.energy;
    $('charge-value').textContent=`${energy} / ${capacity}`;
    const bar=$('charge-bar');bar.querySelector('span').style.width=`${capacity>0?Math.min(100,100*energy/capacity):0}%`;
    bar.setAttribute('aria-valuemax',Math.max(1,capacity,energy));bar.setAttribute('aria-valuenow',energy);bar.setAttribute('aria-valuetext',`${energy} 充能，目标 ${capacity}，可制作 ${total} 支`);
    $('charge-output').textContent=`可制作 ${total} / ${p.target} 支 · 每支 ${p.perArrow} 充能`;
    const materials=usableMaterials();
    document.querySelectorAll('[data-add-material]').forEach(button=>{const id=Number(button.dataset.addMaterial),m=materials.find(m=>m.id===id),n=ingredientSelection.get(id)||0;button.disabled=craftBusy||!m||n>=Math.min(m.count,10000)||!p.target||p.energy>=capacity;const remaining=Math.max(0,(m?.count||0)-n),badge=button.querySelector('[data-material-stock]');badge.textContent=`×${remaining}`;badge.title=`剩余可添加 ${remaining} 份`;button.setAttribute('aria-label',`添加${m?.name||'材料'}，剩余可添加 ${remaining} 份`);});
    $('material-basket').innerHTML=[...ingredientSelection].map(([id,n])=>`<div class="basket-row"><span>${escape(state.materials.find(m=>m.id===id)?.name||'材料')} <b>× ${n}</b></span><button data-remove-material="${id}" aria-label="移除一份${escape(state.materials.find(m=>m.id===id)?.name||'材料')}" ${craftBusy?'disabled':''}>−</button></div>`).join('')||'<p>点击一种材料，按库存尽量补满所需充能。</p>';
    const excess=Math.max(0,energy-total*p.perArrow);
    $('charge-excess').textContent=excess&&total?`余量 ${excess} 充能不会保留，可用 − 调整材料。`:'确认前不会扣除材料，可用 − 撤回。';
    $('magic-error').textContent=quoteError||p.error||(quoteBusy?'正在更新清单…':'');
    $('confirm-craft').disabled=!q||!!p.error||quoteBusy||craftBusy;
    $('confirm-craft').textContent=craftBusy?'正在制作…':`确认制作 ${total} / ${p.target} 支`;
    $('magic-dialog').querySelectorAll('input').forEach(input=>{
        input.disabled=craftBusy||(input.hasAttribute('data-quantity')&&!batches.has(Number(input.dataset.quantity)));
    });
}
function scheduleQuote(){
    clearTimeout(quoteTimer);++quoteVersion;acceptedQuote=null;quoteError='';quoteBusy=false;
    if(!modalOpen||!selectedSpell()?.craftable){updateMagicSummary();return;}
    const p=previewPlan();
    // Still ask the game for an authoritative resource refresh on shortage; only
    // malformed selections are withheld. No resource mutation happens during a quote.
    const valid=batches.size&&ingredientSelection.size&&p.target<=100&&p.total>0&&[...batches.values()].every(n=>Number.isInteger(n)&&n>0);
    if(valid){quoteBusy=true;const requestID=quoteVersion;quoteTimer=setTimeout(()=>{if(!modalOpen||requestID!==quoteVersion)return;send('quote',{...magicSelection(),runtime:!!selectedSpell()?.adapter?.runtime,requestID});},220);}
    updateMagicSummary();
}

function settings(){
    const h=state.hotkey;const keys=[...'ABCDEFGHIJKLMNOPQRSTUVWXYZ',...Array.from({length:12},(_,i)=>'F'+(i+1))];
    $('content').innerHTML=`<div class="settings"><section class="section-box"><h2>唤起面板快捷键</h2><p>在游戏中打开面板；面板打开时，再按一次关闭。字母键需搭配修饰键，避免影响行走。</p><div class="key-row"><select id="key" aria-label="快捷键主键">${keys.map(k=>`<option ${k===h.key?'selected':''}>${k}</option>`).join('')}</select>${['shift','ctrl','alt'].map(k=>`<label><input type="checkbox" id="${k}" ${h[k]?'checked':''}>${k==='ctrl'?'Ctrl':k==='alt'?'Alt':'Shift'}</label>`).join('')}</div><div class="buttons"><button class="primary" id="save">保存快捷键</button><button id="reset">恢复 Shift + W</button></div></section><section class="section-box"><h2>能力入口 · 打开魔法箭工坊</h2><p>${state.powerAvailable?'已找到能力记录。读取存档或开始新游戏时自动加入「魔法 → 能力」。装备后按龙吼／能力键施放，可收藏、无魔法值消耗。':'尚未找到能力记录，请确认 MagicArrows.esp 已启用，并重新启动游戏。'}</p></section><section class="section-box"><h2>随从魔法箭消耗</h2><p>开启后，队友使用本模组封存箭或固定适配箭时按射击数量消耗，射空也消耗。已由游戏扣除的数量会计入，普通箭和外观试作箭沿用游戏规则。</p><label><input type="checkbox" id="follower-consume" ${(state.followers?.consumeMagicArrows??true)?'checked':''} ${state.followers?.available?'':'disabled'}>按射击数量消耗魔法箭</label><p>关闭后沿用游戏及其他模组的消耗规则。随从不需要掌握被封存的法术。此设置不改变友伤或随从自行选择箭矢的行为。</p><button id="save-followers" ${state.followers?.available?'':'disabled'}>保存随从设置</button></section><section class="section-box"><h2>当前版本</h2><p>0.9.9 · 炼金术每级减少 0.5% 材料充能需求，100 级最多减少 50%，向上取整且每支至少 1 点；法力和金币不受此减耗影响。Esc 优先关闭制作弹窗，再关闭面板。</p></section></div>`;
    $('save-followers').onclick=()=>{const consumeMagicArrows=$('follower-consume').checked;$('save-followers').disabled=true;send('followerSettings',{consumeMagicArrows});};
    $('save').onclick=()=>send('settings',{key:$('key').value,shift:$('shift').checked,ctrl:$('ctrl').checked,alt:$('alt').checked});
    $('reset').onclick=()=>send('settings',{key:'W',shift:true,ctrl:false,alt:false});
}
window.MagicArrows={closeDialog,escape:escapeLayer,receiveState(next){
    state=next;readySent=true;equipPending=0;
    if(modalOpen&&!craftBusy){let changed=false;document.querySelectorAll('[data-quantity]').forEach(input=>{const id=Number(input.dataset.quantity);if(!batches.has(id))return;const before=batches.get(id);normalizeBaseInput(input);changed||=before!==batches.get(id);});if(changed)scheduleQuote();}
    const reply=next.workshopReply;
    if(modalOpen&&reply&&reply.requestID===quoteVersion){
        if(reply.type==='quote'){quoteBusy=false;acceptedQuote=reply.ok?next.quote:null;quoteError=reply.ok?'':reply.error||'无法计算制作清单';}
        if(reply.type==='craft'){craftBusy=false;if(reply.ok)closeDialog();else{acceptedQuote=null;quoteError=reply.error||'制作失败，请重新选择材料';}}
    }
    render();$('status').textContent=next.message||'库存已同步';
}};
document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{closeDialog();page=b.dataset.page;render();send('page',{page});});
$('refresh').onclick=()=>send('refresh');$('close').onclick=()=>{closeDialog();send('close');};
function escapeLayer(){
    if(modalOpen||$('magic-dialog'))closeDialog();else send('close',{reason:'escape'});
}
function closeKey(e){
    const h=state.hotkey;const code=e.code||'';const key=code.startsWith('Key')?code.slice(3):(code||String(e.key||'').toUpperCase());
    const escapeKey=e.key==='Escape'||e.key==='Esc'||code==='Escape'||e.keyCode===27;
    const hotkey=key===h.key&&e.shiftKey===h.shift&&e.ctrlKey===h.ctrl&&e.altKey===h.alt;
    if(escapeKey||hotkey){
        e.preventDefault();e.stopPropagation();
        if(e.repeat||e.type==='keyup')return;
        // In game the native key-down is the sole Escape authority. DOM events
        // only suppress dialog defaults, avoiding two closes from one press.
        if(escapeKey){if(!state.nativeEscape||demo)escapeLayer();}
        else send('close',{reason:'hotkey'});
    }
}
document.addEventListener('keydown',closeKey,true);
document.addEventListener('keyup',e=>{if(e.key==='Escape'||e.key==='Esc'||e.code==='Escape'||e.keyCode===27){e.preventDefault();e.stopPropagation();}},true);
function demoAction(type,data){
    if(type==='inspect')return;
    if(type==='normalQuote'||type==='normalCraft'){$('status').textContent='浏览器示例不扣材料；请在游戏内计算真实费用';return;}
    if(type==='quote'){quoteBusy=false;quoteError='浏览器示例不扣资源，请在游戏内确认制作';render();return;}
    if(type==='craft'){$('status').textContent='浏览器示例不能制作';return;}
    if(type==='close'){$('status').textContent='预览模式：游戏内此操作会关闭面板';return;}
    if(type==='followerSettings'){state.followers={available:true,consumeMagicArrows:data.consumeMagicArrows};}
    if(type==='settings'){if(!data.shift&&!data.ctrl&&!data.alt&&data.key.length===1){$('status').textContent='字母快捷键至少需要一个修饰键';return;}state.hotkey=data;}
    if(type==='queueEdit'){state.ammoQueue={...state.ammoQueue,...data,available:true,items:[]};}
    if(type==='queueStart'){state.ammoQueue.enabled=true;const id=queueIDs().find(id=>state.arrows.some(a=>a.id===id&&a.count>0));if(id)state.arrows.forEach(a=>a.equipped=a.id===id);}
    if(type==='equip'){state.arrows.forEach(a=>a.equipped=a.id===data.id);equipPending=0;}
    if(type==='supply')state.arrows.filter(a=>a.family!=='normal'&&!a.spellBound).forEach(a=>a.count=Math.max(a.count,100));
    render();$('status').textContent='浏览器预览 · 操作未写入游戏';
}
render();
if(demo){document.body.classList.add('demo');state.loaded=true;state.powerAvailable=true;state.ammoQueue={available:true,enabled:false,ids:[],items:[],limit:64};
    state.arrows=[{id:1,name:'嗜血箭〔外观试作〕',family:'blood',count:100,damage:8,equipped:true},{id:2,name:'圣辉箭〔外观试作〕',family:'holy',count:100,damage:8},{id:3,name:'星魂箭〔外观试作〕',family:'soul',count:100,damage:8},...['铁箭','钢箭','精灵箭','矮人箭','魔族箭'].map((name,i)=>({id:10+i,name,family:'normal',count:24+i*18,damage:8+i*4,fireballBase:true}))];
    state.spells=[{id:101,name:'火球术',cost:95},{id:102,name:'冰风暴',cost:126},{id:103,name:'血液虹吸',cost:70}].map(s=>({...s,source:'Skyrim.esm',craftable:s.id===101,eligibility:{status:'candidate',reasons:['示例：通过结构初筛，仍需命中验证']}}));state.spells.push({id:106,name:'烈焰术',cost:14,source:'Skyrim.esm',eligibility:{status:'candidate',releaseMode:'sustained',reasons:['示例：持续型结构候选','命中点固定朝向，持续 3 秒；结构兼容时可制作']}},{id:104,name:'烈焰斗篷',cost:110,source:'Skyrim.esm',eligibility:{status:'excluded',reasons:['自身施法','包含斗篷效果']}},{id:105,name:'秘术印记',cost:80,source:'示例魔法模组.esp',eligibility:{status:'review',reasons:['脚本效果需要单独适配']}});state.materials=[{id:201,name:'龙舌兰',count:8,units:6},{id:202,name:'火盐',count:5,units:10}];state.recipes=[{id:301,name:'铁箭',yield:24,craftable:true,maxBatches:4,source:'Dawnguard.esm',ingredients:[{name:'铁锭',need:1,have:4},{name:'木柴',need:1,have:8}]}];selected=1;render();$('status').textContent='浏览器预览 · 示例数据';
}else{
    const timer=setInterval(()=>{if(!readySent&&typeof window.magicArrowsAction==='function'){readySent=true;send('ready');clearInterval(timer);}},100);
}
})();
