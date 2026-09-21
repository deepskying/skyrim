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
  await page.locator('dialog').waitFor({state:'hidden'});
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
  await entry('000A2C94','part');
  const body=page.locator('.cm-outfit-slots button').nth(2),feet=page.locator('.cm-outfit-slots button').nth(7);
  assert.match(await body.getAttribute('class'),/is-worn/);
  assert.equal(await page.locator('.cm-slot-equipment-grid').evaluate(e=>getComputedStyle(e).display),'grid');
  assert.equal(await page.locator('.cm-slot-equipment-card.is-worn').count(),1);
  await page.getByRole('button',{name:'卸下装备',exact:true}).click();
  await page.getByText('当前未穿戴',{exact:true}).waitFor();
  assert.equal(await page.locator('.cm-slot-equipment-card.is-worn').count(),0);
  assert.doesNotMatch(await body.getAttribute('class'),/is-worn/);
  await page.getByRole('button',{name:/弥光连体袍/}).click();
  await page.getByText('卸下将同时腾出：身体、脚部',{exact:true}).waitFor();
  assert.match(await body.getAttribute('class'),/is-worn/);assert.match(await feet.getAttribute('class'),/is-worn/);
  assert.equal(await page.locator('.cm-slot-equipment-card.is-worn').count(),1);
  assert.deepEqual(errors,[]);
  console.log('PASS save once, companion switch, delayed actor, dialogue ownership and worn slot highlights');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
