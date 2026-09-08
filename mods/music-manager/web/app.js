'use strict';
const $ = id => document.getElementById(id);
const labels = [['explore_day','野外白天','☀'],['explore_night','野外夜晚','☾'],['town','城镇','⌂'],['tavern','酒馆','♧'],['home','住宅','◇'],['dungeon','地牢','♜'],['combat','普通战斗','⚔'],['dragon','龙战','♆'],['general','通用','♫']];
const descriptions = {explore_day:'阳光下的漫游，让音乐随旅途展开。',explore_night:'星空、营火与远方，陪伴夜色中的旅途。',town:'穿行街巷，在熟悉的城镇停留。',tavern:'卸下行囊，听一段温暖的旋律。',home:'回到属于自己的安静角落。',dungeon:'深入洞穴与古老遗迹。',combat:'拔出武器，让节奏跟随战斗。',dragon:'巨龙盘旋，迎接天空中的挑战。',general:'其他环境的备用歌单。'};
let state = {categories:labels.map(([id,label])=>({id,label,count:0})),tracks:[],scene:'explore_day',playlist:'',current:'',position:0,duration:0,volume:.5,enabled:true,fallback:true,paused:false,preview:false,status:'等待播放器',location:'',root:'',message:'正在读取音乐库…'};
const playbackDefaults={pauseWithGame:true,followMaster:true,fadeSeconds:1.2,combatFadeSeconds:.35,sceneDelay:2,combatExitDelay:3,dayStart:6,dayEnd:20};
const defaultHotkey={scanCode:50,shift:true,ctrl:false,alt:false,label:'Shift + M'};
const playbackFields={pauseWithGame:'pause-with-game',followMaster:'follow-master',fadeSeconds:'fade-seconds',combatFadeSeconds:'combat-fade-seconds',sceneDelay:'scene-delay',combatExitDelay:'combat-exit-delay',dayStart:'day-start',dayEnd:'day-end'};
const keyScans=[30,48,46,32,18,33,34,35,23,36,37,38,50,49,24,25,16,19,31,20,22,47,17,45,21,44];
const keyOptions=keyScans.map((scanCode,i)=>({scanCode,key:String.fromCharCode(65+i),code:'Key'+String.fromCharCode(65+i)}));
for(let i=1;i<=12;i++)keyOptions.push({scanCode:i<=10?58+i:i===11?87:88,key:'F'+i,code:'F'+i});
for(const k of keyOptions){const option=document.createElement('option');option.value=String(k.scanCode);option.textContent=k.key;$('hotkey-key').append(option);}
let playbackDirty=false,hotkeyDirty=false,pendingPlayback=null,pendingHotkey=null;
const equalFields=(a,b,keys)=>a&&b&&keys.every(k=>a[k]===b[k]);
function hotkeyLabel(h){return [h.ctrl?'Ctrl':'',h.shift?'Shift':'',h.alt?'Alt':'',keyOptions.find(k=>k.scanCode===h.scanCode)?.key||'M'].filter(Boolean).join(' + ');}
function readHotkey(){const h={scanCode:Number($('hotkey-key').value),shift:$('hotkey-shift').checked,ctrl:$('hotkey-ctrl').checked,alt:$('hotkey-alt').checked};return {...h,label:hotkeyLabel(h)};}
function fillPlayback(value){for(const [key,id]of Object.entries(playbackFields)){if(typeof playbackDefaults[key]==='boolean')$(id).checked=value[key];else $(id).value=String(value[key]);}}
function fillHotkey(h){$('hotkey-key').value=String(h.scanCode);for(const key of ['shift','ctrl','alt'])$('hotkey-'+key).checked=h[key];text('draft-hotkey',hotkeyLabel(h));}
function renderSettings(){
  const h=state.hotkey||defaultHotkey, p=state.playback||playbackDefaults;
  text('hotkey-hint',hotkeyLabel(h));text('current-hotkey',hotkeyLabel(h));
  if(pendingPlayback&&equalFields(p,pendingPlayback,Object.keys(playbackDefaults))){pendingPlayback=null;playbackDirty=false;text('playback-message','已保存并生效');}
  else if(pendingPlayback&&/^(操作失败|保存失败)/.test(state.message||'')){pendingPlayback=null;text('playback-message',state.message);$('playback-message').classList.add('invalid');}
  if(pendingHotkey&&equalFields(h,pendingHotkey,['scanCode','shift','ctrl','alt'])){pendingHotkey=null;hotkeyDirty=false;text('hotkey-message','已保存并生效：'+hotkeyLabel(h));}
  else if(pendingHotkey&&state.hotkeyMessage?.startsWith('快捷键未修改')){pendingHotkey=null;text('hotkey-message',state.hotkeyMessage);$('hotkey-message').classList.add('invalid');}
  if(!playbackDirty)fillPlayback(p);if(!hotkeyDirty)fillHotkey(h);
}
function selectSettingsTab(which){for(const tab of ['playback','hotkey']){const active=tab===which;$('tab-'+tab).setAttribute('aria-selected',String(active));$('tab-'+tab).tabIndex=active?0:-1;$('settings-'+tab).hidden=!active;}}
for(const tab of ['playback','hotkey']){$('tab-'+tab).onclick=()=>selectSettingsTab(tab);$('tab-'+tab).onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();const next=tab==='playback'?'hotkey':'playback';selectSettingsTab(next);$('tab-'+next).focus();}};}
$('playback-form').oninput=()=>{playbackDirty=true;pendingPlayback=null;$('playback-message').classList.remove('invalid');text('playback-message','有未保存的修改');};
$('hotkey-form').oninput=()=>{hotkeyDirty=true;pendingHotkey=null;text('draft-hotkey',hotkeyLabel(readHotkey()));text('hotkey-message','有未保存的修改');$('hotkey-message').classList.remove('invalid');};
$('playback-form').onsubmit=e=>{e.preventDefault();const value={};for(const [key,id]of Object.entries(playbackFields))value[key]=typeof playbackDefaults[key]==='boolean'?$(id).checked:Number($(id).value);if(value.dayStart>=value.dayEnd){text('playback-message','白天开始时间必须早于结束时间');$('playback-message').classList.add('invalid');return;}playbackDirty=true;pendingPlayback=value;$('playback-message').classList.remove('invalid');text('playback-message','正在保存…');send('configure',{value});};
$('hotkey-form').onsubmit=e=>{e.preventDefault();hotkeyDirty=true;pendingHotkey=readHotkey();$('hotkey-message').classList.remove('invalid');text('hotkey-message','正在保存…');send('hotkey',{value:pendingHotkey});};
$('playback-reset').onclick=()=>{playbackDirty=true;pendingPlayback=null;fillPlayback(playbackDefaults);text('playback-message','已填入默认值，点击保存后生效');};
$('hotkey-reset').onclick=()=>{hotkeyDirty=true;pendingHotkey=null;fillHotkey(defaultHotkey);text('hotkey-message','已填入 Shift + M，点击保存后生效');};
let selected = 'explore_day', query = '', listKey = '', nativeReceived = false, previousFocus;
const label = id => labels.find(c=>c[0]===id)?.[1] || '安静';
const text = (id, value) => { $(id).textContent = value; };
const time = value => `${Math.floor(Math.max(0,value || 0)/60)}:${String(Math.floor(Math.max(0,value || 0)%60)).padStart(2,'0')}`;
function send(type, extra = {}) {
  if (typeof window.musicManagerAction === 'function') window.musicManagerAction(JSON.stringify({type,...extra}));
  else if (!nativeReceived) demoAction(type, extra);
}
function render() {
  renderSettings();
  $('enabled').checked = state.enabled; $('fallback').checked = state.fallback;
  if (document.activeElement !== $('volume')) $('volume').value = String(Math.round(state.volume*100));
  text('volume-value',`${Math.round(state.volume*100)}%`);
  text('environment',label(state.scene)); text('location',state.location || '未知位置');
  text('mode',state.preview ? '试听中 · 结束后恢复环境播放' : state.playlist === 'general' && state.scene !== 'general' ? '当前使用通用歌单' : '按环境自动选歌');
  text('playlist-title', label(selected)); text('playlist-description', descriptions[selected]);
  text('play-status',state.status); text('root-path',state.root);
  const song = state.tracks.find(t=>t.id===state.current);
  text('now-title',song?.name || '尚未播放'); text('now-category',song ? `${label(song.category)} · ${state.preview ? '试听' : '随机播放'}` : '让天际拥有你的配乐');
  text('position',time(state.position)); text('duration',time(state.duration));
  $('progress-fill').style.width = `${Math.min(100,state.duration > 0 ? state.position/state.duration*100 : 0)}%`;
  text('pause',state.paused ? '▶' : 'Ⅱ'); $('pause').setAttribute('aria-label',state.paused ? '继续播放' : '暂停播放');
  $('pause').disabled = !state.enabled; $('next').disabled = !state.enabled;
  text('message',state.message || '音乐管理器已就绪');
  text('fallback-hint',state.fallback ? '此分类为空时播放「通用」，通用也为空则保持安静。' : '此分类没有可用音乐时，保持安静。');
  for (const button of $('categories').children) {
    const id = button.dataset.category;
    button.classList.toggle('selected',id===selected); button.setAttribute('aria-current',id===selected ? 'true' : 'false');
    button.querySelector('.count').textContent = state.categories.find(c=>c.id===id)?.count || 0;
  }
  const tracks = state.tracks.filter(t=>t.category===selected && t.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  text('track-count',`${tracks.length} 首歌曲`);
  const key = JSON.stringify([selected,query,state.current,tracks]);
  if (key === listKey) return;
  listKey = key;
  const container = $('tracks'), scroll = container.scrollTop;
  const focusId = document.activeElement?.dataset?.track, focusAction = document.activeElement?.dataset?.action;
  const fragment = document.createDocumentFragment();
  if (!tracks.length) {
    const empty = document.createElement('div'); empty.className = 'empty';
    const title = document.createElement('strong'); title.textContent = query ? '没有匹配的歌曲' : '这份歌单，等待你的音乐';
    const detail = document.createElement('span'); detail.textContent = query ? '试试其他名称，或清空搜索。' : `将歌曲放入「${label(selected)}」文件夹，然后重新扫描。`;
    empty.append(title,detail); fragment.append(empty);
  }
  tracks.forEach((t,index)=>{
    const row=document.createElement('div'); row.className=`track${t.id===state.current?' playing':''}${t.disabled?' off':''}`; row.setAttribute('role','listitem');
    const number=document.createElement('span'); number.className='track-number'; number.textContent=t.id===state.current?'♫':String(index+1).padStart(2,'0');
    const info=document.createElement('div'); info.style.minWidth='0';
    const name=document.createElement('div'); name.className='song-name'; name.textContent=t.name; name.title=t.name;
    const detail=document.createElement('div'); detail.className=`song-detail${t.error?' error':''}`; detail.textContent=t.error || t.id; info.append(name,detail);
    const format=document.createElement('span'); format.className='format'; format.textContent=t.id.split('.').pop().toUpperCase();
    const actions=document.createElement('div'); actions.className='track-actions';
    const play=document.createElement('button'); play.textContent='▷ 试听'; play.dataset.track=t.id; play.dataset.action='preview'; play.setAttribute('aria-label',`试听 ${t.name}`); play.disabled=!state.enabled || Boolean(t.error); play.onclick=()=>send('preview',{id:t.id});
    const enabled=document.createElement('input'); enabled.type='checkbox'; enabled.checked=!t.disabled; enabled.dataset.track=t.id; enabled.dataset.action='disable'; enabled.setAttribute('aria-label',`启用 ${t.name}`); enabled.onchange=()=>send('disable',{id:t.id});
    actions.append(play,enabled); row.append(number,info,format,actions); fragment.append(row);
  });
  container.replaceChildren(fragment); container.scrollTop=scroll;
  if (focusId) for (const el of container.querySelectorAll('[data-track]')) if (el.dataset.track===focusId && el.dataset.action===focusAction) el.focus({preventScroll:true});
}
for (const [id,name,symbol] of labels) {
  const button=document.createElement('button'); button.className='category'; button.dataset.category=id;
  const icon=document.createElement('span'); icon.className='symbol'; icon.textContent=symbol;
  const title=document.createElement('span'); title.textContent=name;
  const count=document.createElement('span'); count.className='count';
  button.append(icon,title,count); button.onclick=()=>{selected=id;listKey='';$('tracks').scrollTop=0;render();}; $('categories').append(button);
}
function settings(open) { $('settings').hidden=!open; if(open){playbackDirty=false;hotkeyDirty=false;pendingPlayback=null;pendingHotkey=null;renderSettings();text('playback-message','');text('hotkey-message',state.hotkeyMessage||'');previousFocus=document.activeElement;$('settings-close').focus();}else previousFocus?.focus(); }
$('settings-button').onclick=()=>settings(true); $('settings-close').onclick=()=>settings(false);
$('settings').onclick=e=>{if(e.target===$('settings'))settings(false);};
$('close').onclick=()=>send('close'); $('scan').onclick=()=>send('scan'); $('next').onclick=()=>send('next'); $('pause').onclick=()=>send('pause'); $('auto').onclick=()=>send('auto');
$('enabled').onchange=e=>send('enabled',{value:e.target.checked}); $('fallback').onchange=e=>send('fallback',{value:e.target.checked});
$('open-folder').onclick=()=>send('openFolder',{category:selected});
$('volume').oninput=e=>text('volume-value',`${e.target.value}%`); $('volume').onchange=e=>send('volume',{value:Number(e.target.value)/100});
$('search').oninput=e=>{query=e.target.value;render();};
function escapePanel(){if(!$('settings').hidden)settings(false);else send('close');}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){e.preventDefault();if(!nativeReceived)escapePanel();}
  const h=state.hotkey||defaultHotkey;
  if(e.code===keyOptions.find(k=>k.scanCode===h.scanCode)?.code && e.shiftKey===h.shift && e.ctrlKey===h.ctrl && e.altKey===h.alt){e.preventDefault();if(!nativeReceived)send('close');}
  if(e.key==='Tab' && !$('settings').hidden){const nodes=[...$('settings').querySelectorAll('button,input,select,summary')].filter(el=>el.getClientRects().length&&!el.disabled);if(e.shiftKey&&document.activeElement===nodes[0]){e.preventDefault();nodes.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===nodes.at(-1)){e.preventDefault();nodes[0].focus();}}
});
window.MusicManager={escape:escapePanel,receiveState(next){nativeReceived=true;$('demo-label').hidden=true;document.body.classList.remove('preview');state=next;render();}};
function demoAction(type,extra){
  if(type==='configure'){state.playback={...extra.value};state.message='播放设置已保存并生效';}
  else if(type==='hotkey'){state.hotkey={...extra.value};state.hotkeyMessage='已保存并生效：'+hotkeyLabel(state.hotkey);}
  else if(type==='volume')state.volume=extra.value;
  else if(type==='pause')state.paused=!state.paused;
  else if(type==='enabled')state.enabled=extra.value;
  else if(type==='fallback')state.fallback=extra.value;
  else if(type==='disable'){const t=state.tracks.find(t=>t.id===extra.id);if(t)t.disabled=!t.disabled;}
  else if(type==='preview'){state.current=extra.id;state.preview=true;state.position=0;}
  else if(type==='auto'||type==='next'){state.preview=false;state.current=state.tracks.filter(t=>!t.disabled)[1]?.id || '';state.position=0;}
  else if(type==='openFolder')state.message='界面预览：游戏内将打开对应音乐文件夹。';
  else if(type==='scan')state.message='界面预览：重新扫描完成。';
  else if(type==='close')state.message='界面预览：游戏内此操作返回游戏。';
  state.status=!state.enabled?'已关闭接管':state.paused?'已暂停':state.preview?'正在试听':'正在播放';
  if(type==='configure'||type==='hotkey')try{localStorage.setItem('musicManagerPreviewSettings',JSON.stringify({playback:state.playback,hotkey:state.hotkey}));}catch{}
  state.categories.forEach(c=>c.count=state.tracks.filter(t=>t.category===c.id&&!t.disabled).length);render();
}
render(); send('ready');
setTimeout(()=>{
  if(nativeReceived || typeof window.musicManagerAction==='function')return;
  try{const saved=JSON.parse(localStorage.getItem('musicManagerPreviewSettings')||'{}');state.playback=saved.playback||playbackDefaults;state.hotkey=saved.hotkey||defaultHotkey;}catch{}
  document.body.classList.add('preview');$('demo-label').hidden=false;
  const names=['远山与晨光','漫步白漫领','Ancient Stones','穿过松林的风','From Past to Present','旅途未尽','晨雾中的溪流'];
  state.tracks=names.map((name,i)=>({id:`野外白天/${name}.mp3`,name,category:'explore_day',disabled:i===5,error:''}));
  state.tracks.push({id:'野外夜晚/夜空下.flac',name:'夜空下',category:'explore_night',disabled:false,error:''});
  state.current=state.tracks[0].id;state.duration=243;state.position=78;state.playlist='explore_day';state.location='白漫领 · 西部哨塔';state.root='Data / Music / MusicManager';state.message='预览数据 · 游戏内显示实际导入的音乐';demoAction('ready',{});
},700);
