// Drive the web interface that `lbx serve` serves from the Small library, and keep screenshots for a person.
// usage: node screenshots.mjs <base url> <out dir>
// Chromium: CHROME=<path> (the Nix dev shell sets it), else Playwright's own (npx playwright-core install chromium).
// Exits 1 if any page fails, or the browser logs an error that isn't on the expected list.
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const [BASE, OUT] = process.argv.slice(2);
const EXPECTED = [/\/ui\/home-area\.json/];     // optional local file (web/map.js): 404 is normal
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
let current = '';
const problems = [];
page.on('pageerror', e => problems.push(`[${current}] ${e.message}`));
page.on('response', r => { if (r.status() >= 400 && !EXPECTED.some(x => x.test(r.url()))) problems.push(`[${current}] ${r.status()} ${r.url()}`) });

const report = {};
async function step(name, fn) {
  current = name;
  try { report[name] = { ok: true, ...(await fn()) } }
  catch (e) { report[name] = { ok: false, error: String(e.message || e).split('\n')[0] } }
  await page.screenshot({ path: `${OUT}/${name}.png` }).catch(() => { });
  console.log(`${report[name].ok ? 'ok  ' : 'FAIL'} ${name} ${JSON.stringify(report[name])}`);
}
const go = async h => { await page.goto(`${BASE}/${h}`); await page.waitForLoadState('networkidle').catch(() => { }); await page.waitForTimeout(800) };
const h1 = () => page.locator('main h1').first().textContent({ timeout: 5000 });
const atLeast = (n, what, x) => { if (x < n) throw new Error(`${what}: ${x}, expected at least ${n}`); return x };

await step('01-home', async () => { await go(''); return { h1: await h1() } });
await step('02-guides', async () => { await go('#/guides'); return { guides: atLeast(10, 'guides', await page.locator('main a[href^="#/t/"]').count()) } });
await step('03-guide-water', async () => {
  await go('#/t/water');
  return { h1: await h1(), sources: atLeast(20, 'sources', await page.locator('main a[href^="#/read/"], main a[href^="#/watch/"], main a[href^="#/wiki/"]').count()) };
});
await step('04-search', async () => {
  await go('#/search?q=' + encodeURIComponent('boil water'));
  return { results: atLeast(5, 'results', await page.locator('main a[href^="#/read/"], main a[href^="#/watch/"]').count()) };
});
await step('05-reader', async () => {
  await go('#/read/ed5bac0a81b009?p=135');
  await page.waitForFunction(() => [...document.querySelectorAll('main img')].some(i => i.complete && i.naturalWidth > 100), null, { timeout: 20000 });
  return { h1: await h1() };
});
await step('06-video', async () => {
  await go('#/watch/video-k98ilfQmUWw');
  const seek = await page.evaluate(async () => {
    const v = document.querySelector('video'); v.muted = true; await v.play().catch(() => { });
    await new Promise((res, rej) => { if (v.readyState >= 1) res(); v.addEventListener('loadedmetadata', res, { once: true }); setTimeout(() => rej(new Error('no metadata')), 15000) });
    const t = Math.floor(v.duration * 0.7);
    await new Promise((res, rej) => { v.addEventListener('seeked', res, { once: true }); setTimeout(() => rej(new Error('no seeked event')), 15000); v.currentTime = t });
    return { duration: v.duration, seekedTo: v.currentTime };
  });
  return seek;
});
await step('07-encyclopedia', async () => {
  await go('#/encyclopedias?q=cholera');
  await page.locator('main a[href^="#/wiki/"]').first().click();
  await page.waitForLoadState('networkidle').catch(() => { });
  const title = await page.frameLocator('#wframe').locator('h1').first().textContent({ timeout: 10000 });
  return { article: title };
});
await step('08-map-us', async () => { await go('#/map'); await page.waitForTimeout(2500); return {} });
await step('09-map-street', async () => { await go('#/map?lat=38.5816&lon=-121.4944&z=16'); await page.waitForTimeout(3000); return {} });
await step('10-chat-no-ai', async () => {
  await go('#/ask');
  const box = page.locator('main textarea').first();
  await box.fill('how do I purify water');
  await box.press('Enter');
  await page.waitForFunction(() => document.querySelectorAll('main a[href^="#/read/"]').length >= 3, null, { timeout: 20000 });
  return { pages: await page.locator('main a[href^="#/read/"]').count() };
});

report.problems = problems;
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
await browser.close();
for (const p of problems) console.log('PROBLEM', p);
const failed = Object.values(report).filter(r => r && r.ok === false).length;
console.log(`${failed ? 'FAIL' : 'OK'}: ${Object.keys(report).length - 1} pages, ${failed} failed, ${problems.length} problems. Screenshots in ${OUT}`);
process.exit(failed || problems.length ? 1 : 0);
