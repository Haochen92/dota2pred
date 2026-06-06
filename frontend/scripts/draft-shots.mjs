import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://localhost:3212';
const URL = `${BASE}/draft-predictor`;
const OUT = '/tmp/shots';

async function settle(page, ms = 1500) {
  try { await page.waitForLoadState('networkidle', { timeout: 20000 }); } catch {}
  await page.waitForTimeout(ms);
}

const browser = await chromium.launch();

// ---------- Desktop ----------
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(page);
await page.screenshot({ path: `${OUT}/desktop-empty.png`, fullPage: true });
console.log('shot: desktop-empty');

// Active-slot state
try {
  await page.getByRole('button', { name: '1', exact: true }).first().click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/desktop-active.png`, fullPage: true });
  console.log('shot: desktop-active');
} catch (e) { console.log('active failed:', e.message); }

// Fill both teams + predict -> modal
try {
  // Click the first currently-enabled pool hero (avoids board portraits and
  // already-picked, now-disabled heroes). Scope to the visible desktop tree.
  const pickFirst = async () => {
    const hero = page.locator('[data-testid="hero-pick"]:not([disabled]):visible').first();
    await hero.scrollIntoViewIfNeeded();
    await hero.click();
    await page.waitForTimeout(250);
  };
  // Radiant slot 0 is already active from the step above.
  for (let i = 0; i < 5; i++) await pickFirst();
  await page.getByRole('button', { name: '1', exact: true }).first().click(); // dire slot 0
  await page.waitForTimeout(300);
  for (let i = 0; i < 5; i++) await pickFirst();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/desktop-filled.png`, fullPage: true });
  console.log('shot: desktop-filled');

  await page.getByRole('button', { name: /predict/i }).first().click();
  await page.waitForSelector('text=Predicted Winner', { timeout: 20000 });
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/desktop-modal.png`, fullPage: true });
  console.log('shot: desktop-modal');
} catch (e) {
  console.log('fill/predict failed:', e.message);
  await page.screenshot({ path: `${OUT}/desktop-partial.png`, fullPage: true });
}
await ctx.close();

// ---------- Mobile ----------
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
const mpage = await mctx.newPage();
await mpage.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await settle(mpage);
await mpage.screenshot({ path: `${OUT}/mobile-empty.png`, fullPage: true });
console.log('shot: mobile-empty');
await mctx.close();

await browser.close();
console.log('done');
