import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://localhost:3212';
const URL = `${BASE}/match-tracker`;
const OUT = '/tmp/shots';

async function settle(page, ms = 2500) {
  try { await page.waitForLoadState('networkidle', { timeout: 25000 }); } catch {}
  await page.waitForTimeout(ms);
}

const browser = await chromium.launch();

// Desktop
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(page);
await page.screenshot({ path: `${OUT}/mt-desktop.png`, fullPage: true });
console.log('shot: mt-desktop');

// Expanded filters
try {
  await page.getByLabel('Toggle filters').click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/mt-filters.png`, fullPage: true });
  console.log('shot: mt-filters');
} catch (e) { console.log('filters expand failed:', e.message); }
await ctx.close();

// Mobile
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
const mpage = await mctx.newPage();
await mpage.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(mpage);
await mpage.screenshot({ path: `${OUT}/mt-mobile.png`, fullPage: true });
console.log('shot: mt-mobile');
await mctx.close();

await browser.close();
console.log('done');
