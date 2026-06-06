import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://localhost:3212';
const OUT = '/tmp/shots';

async function settle(page, ms = 2500) {
  try { await page.waitForLoadState('networkidle', { timeout: 25000 }); } catch {}
  await page.waitForTimeout(ms);
}

const browser = await chromium.launch();

// ---- Mobile match cards + nav drawer ----
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
const mp = await mctx.newPage();
await mp.goto(`${BASE}/match-tracker`, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(mp);
await mp.screenshot({ path: `${OUT}/x-cards-mobile.png`, fullPage: true });
console.log('shot: x-cards-mobile');
// Expand the first card's prediction
try {
  await mp.getByRole('button', { name: /view prediction/i }).first().click();
  await mp.waitForTimeout(900);
  await mp.screenshot({ path: `${OUT}/x-card-expanded.png` });
  console.log('shot: x-card-expanded');
} catch (e) { console.log('card expand failed:', e.message); }
// Open nav drawer
try {
  await mp.locator('.mantine-Burger-root').first().click();
  await mp.waitForTimeout(700);
  await mp.screenshot({ path: `${OUT}/x-nav-drawer.png` });
  console.log('shot: x-nav-drawer');
} catch (e) { console.log('nav drawer failed:', e.message); }
await mctx.close();

// ---- Model history desktop ----
const dctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });
const dp = await dctx.newPage();
await dp.goto(`${BASE}/model-history`, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(dp, 3500);
await dp.screenshot({ path: `${OUT}/x-mh-desktop.png`, fullPage: true });
console.log('shot: x-mh-desktop');
await dctx.close();

// ---- Model history mobile ----
const m2 = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
const m2p = await m2.newPage();
await m2p.goto(`${BASE}/model-history`, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(m2p, 3500);
await m2p.screenshot({ path: `${OUT}/x-mh-mobile.png`, fullPage: true });
console.log('shot: x-mh-mobile');
await m2.close();

await browser.close();
console.log('done');
