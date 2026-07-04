// Regenerates docs/demo/preview.gif — the README hero — by driving the demo page
// itself (file://, no server needed) and encoding the frames with ffmpeg. The asset
// is always a byproduct of this script, never hand-crafted.
//
// Run (playwright comes from the seller-web sibling repo, ffmpeg from PATH):
//   NODE_PATH=../../../seller-web/node_modules node record-preview.cjs
const { execFileSync } = require('node:child_process');
const { mkdtempSync, rmSync } = require('node:fs');
const { join } = require('node:path');
const os = require('node:os');
const { chromium } = require('playwright');

const PAGE = 'file://' + join(__dirname, 'index.html');
const OUTPUT = join(__dirname, 'preview.gif');
// Two-pass palette keeps the GIF crisp and small at a readable frame rate/width.
const FILTERS =
  'scale=900:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer';

(async () => {
  const dir = mkdtempSync(join(os.tmpdir(), 'seller-preview-'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1000, height: 850 } });
  await page.goto(PAGE, { waitUntil: 'networkidle' });

  let n = 0;
  const shot = () => page.screenshot({ path: join(dir, `f${String(n++).padStart(3, '0')}.png`) });
  const capture = async (ms) => {
    for (let t = 0; t < ms; t += 350) {
      await shot();
      await page.waitForTimeout(350);
    }
  };

  await shot(); await shot();                    // landing: what do you want to explore?
  await page.click('#rail .sess:first-child');   // enter coppia-serale (local · qwen2.5:7b)
  await capture(3500);                           // turn 1 reveals (search → cards → reply)
  await page.click('#nextBtn');
  await capture(3500);                           // turn 2 (duration≤60 becomes a filter)
  await page.click('#nextBtn');
  await capture(4200);                           // turn 3 (FORCED badge, coop cards, note)

  await page.click('#changeBtn');                // back to picker
  await page.click('#tier-frontier');             // switch to the frontier tier
  await capture(1400);                            // rail redraws with the frontier sessions
  await page.click('#rail .sess:first-child');   // enter coppia-serale-frontier (Claude Sonnet 5)
  await capture(3000);                           // turn 1 reveals
  await page.click('#nextBtn');
  await capture(3000);                           // turn 2
  await page.click('#nextBtn');
  await capture(3800);                           // turn 3 (full constraint stack, unprompted — no floor needed)
  await shot(); await shot(); await shot();      // hold the ending

  await browser.close();
  execFileSync('ffmpeg', ['-y', '-framerate', '3', '-i', join(dir, 'f%03d.png'), '-vf', FILTERS, OUTPUT], { stdio: 'inherit' });
  rmSync(dir, { recursive: true, force: true });
  console.log(`\nPreview GIF written to ${OUTPUT} (${n} frames).`);
})();
