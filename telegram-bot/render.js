// Render a TechHub card to PNG.
// Usage: node render.js <data.json> <out.png>
// data.json "type" is one of: digest | single | registry  (see templates/card.html and data/*.example.json)
// For "single" cards, "image" should be a LOCAL file path (download it first with curl).
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const [dataPath, outPath] = process.argv.slice(2);
  if (!dataPath || !outPath) { console.error('usage: node render.js data.json out.png'); process.exit(2); }
  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  if (data.image && !/^(https?:|file:|data:)/.test(data.image)) {
    data.image = 'file://' + path.resolve(path.dirname(dataPath), data.image);
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1024, height: 1280 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'templates', 'card.html'));
  await page.evaluate(d => window.render(d), data);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState('networkidle');
  const el = await page.$('#page');
  await el.screenshot({ path: outPath, type: outPath.endsWith('.jpg') ? 'jpeg' : 'png', quality: outPath.endsWith('.jpg') ? 92 : undefined });
  const box = await el.boundingBox();
  console.log(`rendered ${outPath} ${Math.round(box.width)}x${Math.round(box.height)}`);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
