// Run against dedicated local real-data servers; never substitutes API responses.
// PLAYWRIGHT_MODULE may point at an installed playwright index.mjs.
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const url = process.env.LOTUS_TEST_URL || 'http://127.0.0.1:5183';
assert(['localhost', '127.0.0.1'].includes(new URL(url).hostname), 'Use a dedicated local test server');
assert(!new URL(url).search, 'Preview mode is not an integration test');
const output = 'runtime/v3-validation';
await mkdir(output, {recursive: true});
const browser = await chromium.launch({headless: true,
  ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
const errors = [];
const summary = [];
try {
 for (const width of [1280, 390]) {
  const context = await browser.newContext({viewport: {width, height: 900}});
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const recommendation = () => page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/recommendations'
    && r.request().method() === 'POST');
  await page.goto(url);
  await page.locator('input[name="interests"]').waitFor({state: 'visible'});
  await page.getByRole('combobox', {name: '관심 분야 등록 표현 선택'}).selectOption('사업');
  await page.getByRole('button', {name: '입력 확인', exact: true}).click();
  const responsePromise = recommendation();
  await page.getByRole('button', {name: '다음', exact: true}).click();
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  const data = await response.json();
  assert.equal(data.items.length, 2, 'Reviewed real batch must still have two matching open notices');
  assert.equal(data.candidate_count, 2);
  for (const item of data.items) {
    assert.equal(item.opportunity.source_kind, 'real');
    assert.equal(item.recommendation.relevance_score, 40);
    assert.equal(item.recommendation.eligibility, 'unknown');
  }
  await page.getByText('추천 2건을 찾았어요.', {exact: true}).waitFor();
  assert.equal(await page.locator('.results .result-card').count(), 2);
  assert.equal(await page.getByText('추가 확인 필요', {exact: true}).count(), 2);
  await page.locator('.results .result-details summary').first().click();
  assert.equal(await page.locator('.results .result-details a').first().getAttribute('href'), data.items[0].opportunity.source_url);
  assert.match(await page.locator('.results').innerText(), /마감일이 기재되지 않은/);
  await page.getByRole('button', {name: '관심 공고 저장', exact: true}).first().click();
  const storage = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage)));
  assert.deepEqual(Object.keys(storage), ['lotus.saved-opportunity-ids']);
  assert.deepEqual(JSON.parse(storage['lotus.saved-opportunity-ids']), [data.items[0].opportunity.id]);
  assert.equal(new URL(page.url()).search, '');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.screenshot({path: `${output}/real-recommendations-${width}.png`, fullPage: true});
  await page.getByRole('button', {name: '공고 탐색', exact: true}).click();
  await page.getByRole('button', {name: '공고 불러오기', exact: true}).click();
  await page.getByText('불러온 공고 3 / 3건 · 표시 3건', {exact: true}).waitFor();
  await page.getByRole('button', {name: '입력 수정', exact: true}).click();
  await page.locator('input[name="interests"]').fill('개발');
  await page.getByRole('button', {name: '입력 확인', exact: true}).click();
  const emptyPromise = recommendation();
  await page.getByRole('button', {name: '다음', exact: true}).click();
  const empty = await emptyPromise;
  assert.equal(empty.status(), 200);
  assert.deepEqual((await empty.json()).items, []);
  await page.getByText('조건에 맞는 추천이 없어요. 관심 분야나 목표를 바꿔 다시 시도해 보세요.', {exact: true}).waitFor();
  assert.equal(await page.locator('.results .result-card').count(), 0);
  summary.push({width, positive: 2, score: 40, eligibility: 'unknown', empty: 0, catalogue: 3});
  await context.close();
 }
 assert.deepEqual(errors, []);
 await writeFile(`${output}/browser-result.json`, JSON.stringify({summary, pageErrors: errors}, null, 2));
 console.log(JSON.stringify(summary));
} finally {
 await browser.close();
}
