// Render a 1080x1920 story image that wraps an already-rendered card.
// Usage: node story.js <card.jpg> <out.jpg> "<title>" ["<tag>"]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [card, out, title, tag] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'templates', 'story.html'));
  await page.evaluate(d => window.render(d), { card: 'file://' + path.resolve(card), title, tag });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out, type: 'jpeg', quality: 92 });
  console.log('rendered', out);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
