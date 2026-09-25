// Run against the browser preview: PLAYWRIGHT_MODULE may point to an installed Playwright package.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.argv[2]||'http://127.0.0.1:5187');
  await page.getByRole('button',{name:/伙伴穿搭/}).click();
  const entry=async(id,mode)=>page.evaluate(({id,mode})=>window.dispatchEvent(new CustomEvent('companion:wardrobe',{detail:{actorId:id,mode,session:window.__companionSnapshot.session}})),{id,mode});
  await entry('000A2C94','save');
  await page.locator('dialog[open]').waitFor();
  assert.match(await page.locator('dialog input').inputValue(),/^莱迪亚/);
  await page.locator('dialog input').fill('回归测试套装');
  await page.getByRole('button',{name:'保存并收藏',exact:true}).click();
  await page.locator('dialog[open]').waitFor({state:'hidden'}); // two dialogs exist, only one opens
  await page.locator('.cm-companion-trigger').click();
  await page.getByRole('option',{name:/伊奥拉/}).click();
  assert.equal(await page.locator('dialog[open]').count(),0);
  await page.getByRole('button',{name:'保存当前套装',exact:true}).click();
  assert.match(await page.locator('dialog input').inputValue(),/^伊奥拉/);
  await page.getByRole('button',{name:'取消',exact:true}).click();
  await page.getByRole('button',{name:/伙伴库存/}).click();
  await page.getByRole('button',{name:/伙伴穿搭/}).click();
  assert.equal(await page.locator('dialog[open]').count(),0);
  // The requested actor arrives later than the navigation event. Never open for a fallback actor.
  await page.evaluate(()=>{window.savedOutfitSnapshot=structuredClone(window.__companionSnapshot);window.__companionSnapshot.followers=window.__companionSnapshot.followers.filter(f=>f.id!=='00000012');window.dispatchEvent(new Event('companion:snapshot'));});
  await entry('00000012','save');
  await page.getByText('等待目标伙伴的数据，请刷新或重新选择伙伴。',{exact:true}).waitFor();
  assert.equal(await page.locator('dialog[open]').count(),0);
  await page.evaluate(()=>{window.__companionSnapshot=window.savedOutfitSnapshot;window.dispatchEvent(new Event('companion:snapshot'));});
  await page.locator('dialog[open]').waitFor();
  assert.match(await page.locator('dialog input').inputValue(),/^法恩达尔/);
  await page.getByRole('button',{name:'取消',exact:true}).click();
  // The manual slot page was removed: the panel keeps only the saved-set and wear tabs, and an
  // entry that still asks for "part" lands on the wear page instead of a page that no longer exists.
  await entry('000A2C94','part');
  await page.locator('.cm-wear-list').waitFor();
  assert.equal(await page.getByRole('button',{name:'手动调整',exact:true}).count(),0);
  assert.equal(await page.locator('.cm-outfit-toolbar .tabs button').count(),2);
  // The dialogue's 调整穿搭 line now opens the wear page: one flat apparel list, hover preview,
  // arrow-key selection and a click that equips or unequips the exact instance.
  await entry('000A2C94','wear');
  await page.locator('.cm-wear-list').waitFor();
  const wearRows=page.locator('.cm-wear-row');
  assert.equal(await wearRows.count(),6);
  assert.equal(await page.locator('.cm-wear').getByText('铁剑',{exact:true}).count(),0);
  assert.equal(await page.locator('.cm-wear').getByText('治疗药剂',{exact:true}).count(),0);
  assert.equal(await page.locator('.cm-wear-row.is-worn').count(),2);
  // Rows are separated by a 2px gap over a transparent list background, so the cards read as
  // individual rows instead of one block of stripes.
  assert.equal(await page.locator('.cm-wear-list').evaluate(e=>getComputedStyle(e).rowGap),'2px');
  // Favourited rows carry a light blue background, and the list stretches to the column height.
  assert.equal(await page.locator('.cm-wear-row.is-favorite').count(),2);
  assert.match(await page.locator('.cm-wear-row.is-favorite').first().evaluate(e=>getComputedStyle(e).backgroundColor),/122, 176, 226/);
  assert.ok(await page.locator('.cm-wear-list').evaluate(e=>e.getBoundingClientRect().height)>=400);
  const armorStat=page.locator('.cm-wear-stats > div').first();
  await wearRows.nth(1).hover();
  assert.equal(await page.locator('.cm-wear-detail h3').innerText(),'皮甲（火焰抗性）');
  assert.equal((await armorStat.innerText()).includes('36'),true);
  assert.equal(await page.locator('.cm-wear-facts div').last().locator('dd').innerText(),'皮甲');
  await wearRows.nth(5).hover(); // shield: +20 armor, nothing replaced
  assert.equal((await armorStat.innerText()).includes('+20'),true);
  // Live ratings are floats; the page must never show the raw value.
  assert.equal(/\d\.\d/.test(await armorStat.innerText()),false);
  assert.equal(await page.locator('.cm-wear-facts').getByText('将换下',{exact:true}).count(),0);
  await page.locator('.cm-wear-list').focus();
  await page.keyboard.press('ArrowDown');
  assert.equal(await wearRows.nth(1).getAttribute('aria-selected'),'true');
  await page.keyboard.press('Enter');
  await page.waitForFunction(()=>{const r=document.querySelectorAll('.cm-wear-row');return !r[0].className.includes('is-worn')&&r[1].className.includes('is-worn');});
  await wearRows.nth(3).click(); // necklace: an unworn piece in a free slot goes on
  await page.waitForFunction(()=>document.querySelectorAll('.cm-wear-row.is-worn').length===3);
  await page.getByLabel('搜索随从装备').fill('皮甲');
  assert.equal(await wearRows.count(),2);
  await page.getByLabel('搜索随从装备').fill('不存在');
  assert.equal(await wearRows.count(),0);
  await page.getByLabel('搜索随从装备').fill('');
  assert.equal(await wearRows.count(),6);
  // The 3D area reports its viewport and follows the previewed item; the HTTP preview stands in for
  // the game renderer, so each native status can be checked without a GPU.
  await page.evaluate(()=>{window.__previewCalls=[];const original=window.companionRequest;window.companionRequest=payload=>{const r=JSON.parse(payload);if(typeof r.type==='string'&&r.type.startsWith('preview'))window.__previewCalls.push(r);return original(payload);};});
  await page.evaluate(()=>{window.__companionPreviewStatus='ready';});
  await wearRows.nth(5).hover(); // shield, so the requested base form is unambiguous
  await page.getByText('拖动旋转 · 滚轮缩放',{exact:true}).waitFor();
  // The model needs room to read: the viewport stays at least 300px tall.
  const previewHeight=await page.locator('.cm-preview-viewport').evaluate(e=>e.getBoundingClientRect().height);
  assert.ok(previewHeight>=300,`preview viewport too short: ${previewHeight}`);
  const calls=await page.evaluate(()=>window.__previewCalls);
  const select=calls.find(call=>call.type==='previewSelect');
  assert.equal(select.id,'00012EB6');assert.equal(select.actorId,'000A2C94');
  const layout=calls.filter(call=>call.type==='previewLayout').pop();
  assert.ok(layout.width>0&&layout.height>0&&layout.x>=0&&layout.y>=0);
  assert.equal(await page.getByRole('button',{name:'重置视角',exact:true}).isEnabled(),true);
  const box=await page.locator('.cm-preview-viewport').boundingBox();
  await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
  await page.mouse.down();await page.mouse.move(box.x+box.width/2+40,box.y+box.height/2+12);await page.mouse.up();
  assert.equal((await page.evaluate(()=>window.__previewCalls)).some(call=>call.type==='previewCamera'),true);
  await page.evaluate(()=>{window.__companionPreviewStatus='unsupported';});
  await page.getByText('此物品暂不支持模型预览',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'重置视角',exact:true}).isDisabled(),true);
  await page.evaluate(()=>{window.__companionPreviewStatus='unavailable';});
  await page.getByText('模型预览未连接',{exact:true}).waitFor();
  // Leaving the page drops the model instead of leaving a surface over the other tabs.
  await page.getByRole('button',{name:'整套随机',exact:true}).click();
  await page.waitForFunction(()=>window.__previewCalls.some(call=>call.type==='previewClear'));
  assert.deepEqual(errors,[]);
  console.log('PASS save once, companion switch, delayed actor, dialogue ownership, worn slot highlights, the wear page and its model viewport');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
