const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
import {rename} from 'node:fs/promises';
import assert from 'node:assert/strict';
const db=process.env.LOTUS_TEST_DB;
const url=process.env.LOTUS_TEST_URL;
const fixedTime=process.env.LOTUS_TEST_TIME;
assert(db && url && fixedTime, 'Run via scripts.check_browser using a disposable DB');
assert(['localhost','127.0.0.1'].includes(new URL(url).hostname));
const browser=await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
let moved=false;
try {
 for(const width of [390,1280]) {
  const page=await browser.newPage({viewport:{width,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  // Forward the real request with limit=1; never replace the server response.
  await page.route('**/api/v1/recommendations',route=>{
   const data=route.request().postDataJSON();
   return route.continue({postData:JSON.stringify({...data,limit:1})});
  });
  await page.clock.install({time: new Date(fixedTime)});
  await page.goto(url);
  await page.getByRole('combobox',{name:'관심 분야 추천 표현 선택'}).selectOption('사업');
  await page.getByRole('button',{name:'입력 확인',exact:true}).click();
  await rename(db,db+'.held');moved=true;
  const bad=page.waitForResponse(r=>r.url().endsWith('/recommendations'));
  await page.getByRole('button',{name:'다음',exact:true}).click();
  assert.equal((await bad).status(),503);
  await page.getByText('일시적으로 불러오지 못했어요. 다시 시도해 주세요.',{exact:true}).waitFor();
  await rename(db+'.held',db);moved=false;
  const good=page.waitForResponse(r=>r.url().endsWith('/recommendations'));
  await page.getByRole('button',{name:'추천 다시 요청',exact:true}).click();
  const response=await good;assert.equal(response.status(),200);
  const data=await response.json();assert.equal(data.candidate_count,2);assert.equal(data.items.length,1);
  await page.getByText('전체 추천 후보 2건 중 1건을 받았어요.',{exact:true}).waitFor();
  assert.equal(await page.locator('.results .result-card').count(),1);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({width,actual503:true,retry200:true,candidates:2,displayed:1,pageErrors:0}));
  await page.getByRole('button',{name:'입력 수정',exact:true}).click();
  assert.equal(await page.locator('input[name="interests"]').inputValue(),'사업');
  await page.unroute('**/api/v1/recommendations');
  let release;
  const gate=new Promise(resolve=>{release=resolve;});
  let captured;
  const pending=new Promise(resolve=>{captured=resolve;});
  let forwarded;
  const finished=new Promise(resolve=>{forwarded=resolve;});
  await page.route('**/api/v1/recommendations',async route=>{
    if(route.request().postDataJSON().profile.interests.includes('사업')) {
      captured(); await gate;
      try {await route.continue();} catch {} finally {forwarded();}
    } else await route.continue();
  });
  // Invalidate the old confirmation before starting a deliberately delayed request.
  await page.locator('input[name="interests"]').fill('사업, 경영');
  await page.getByRole('button',{name:'입력 확인',exact:true}).click();
  await page.getByRole('button',{name:'다음',exact:true}).click();
  await pending;
  await page.getByRole('button',{name:'입력 수정',exact:true}).click();
  await page.locator('input[name="interests"]').fill('개발');
  await page.getByRole('button',{name:'입력 확인',exact:true}).click();
  const empty=page.waitForResponse(r=>r.url().endsWith('/recommendations'));
  await page.getByRole('button',{name:'다음',exact:true}).click();
  assert.deepEqual((await (await empty).json()).items,[]);
  release(); await finished;
  await page.getByText('조건에 맞는 추천이 없어요. 관심 분야나 목표를 바꿔 다시 시도해 보세요.',{exact:true}).waitFor();
  assert.equal(await page.locator('.results .result-card').count(),0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({width,oldRequestCancelled:true,inputRetained:true}));
  await page.close();
 }
 const recoveryPage=await browser.newPage();
 await recoveryPage.clock.install({time:new Date(fixedTime)});
 let rejectCapabilities=true;
 await recoveryPage.route('**/api/v1/capabilities',route=>{
   if(rejectCapabilities)return route.abort('failed');
   return route.continue();
 });
 await recoveryPage.goto(url);
 await recoveryPage.getByRole('combobox',{name:'관심 분야 추천 표현 선택'}).selectOption('사업');
 await recoveryPage.getByRole('button',{name:'입력 확인',exact:true}).click();
 await recoveryPage.getByRole('button',{name:'다음',exact:true}).click();
 await recoveryPage.getByRole('button',{name:'공고 탐색',exact:true}).click();
 await recoveryPage.getByText(/기능 상태를 확인하지 못했어요/).filter({visible:true}).waitFor();
 rejectCapabilities=false;
 await recoveryPage.getByRole('button',{name:'연결 다시 확인',exact:true}).filter({visible:true}).click();
 await recoveryPage.getByText('검색 결과 3건',{exact:true}).waitFor();
 await recoveryPage.getByRole('button',{name:'맞춤 추천',exact:true}).click();
 await recoveryPage.getByRole('button',{name:'추천 요청 보내기',exact:true}).click();
 await recoveryPage.getByText('추천 2건을 찾았어요.',{exact:true}).waitFor();
 await recoveryPage.close();
 console.log(JSON.stringify({capabilityTransportFailureRecovery:true}));
} finally {if(moved)await rename(db+'.held',db);await browser.close();}
