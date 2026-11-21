/**
 * End-to-end rehearsal of the judge flow, with assertions, and README screenshot capture.
 *
 *   cd frontend && npm i --no-save playwright && npx playwright install chromium
 *   # backend on :8000, frontend dev server on :5173 (or BASE_URL=http://localhost:8000 for the built app)
 *   node e2e/demo-walkthrough.cjs            # asserts the flow, writes ../docs/screenshots/*.png
 *
 * Exits non-zero on the first failed step.
 */
const { chromium } = require('playwright')
const path = require('path')
const BASE = process.env.BASE_URL || 'http://localhost:5173'
const OUT = path.resolve(__dirname, '../../docs/screenshots')
const steps = []
const step = async (name, fn) => {
  const t = Date.now()
  try { await fn(); steps.push([name, 'ok', Date.now() - t]); console.log(`  ✔ ${name} (${Date.now() - t}ms)`) }
  catch (e) { console.log(`  ✘ ${name}\n    ${e.message.split('\n')[0]}`); throw e }
}

;(async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const p = await ctx.newPage()
  const pageErrors = []
  p.on('pageerror', (e) => pageErrors.push(e.message))
  // Full-page capture resizes the viewport, which restarts chart animations mid-frame. Instead grow the viewport,
  // wait for animations to settle, then take a normal screenshot.
  const shot = async (n, full = false) => {
    if (full) {
      const h = await p.evaluate(() => document.documentElement.scrollHeight)
      await p.setViewportSize({ width: 1440, height: h }); await p.waitForTimeout(2200)
      await p.screenshot({ path: `${OUT}/${n}.png` }); await p.setViewportSize({ width: 1440, height: 900 })
    } else await p.screenshot({ path: `${OUT}/${n}.png` })
  }
  const see = (text, t = 15000) => p.getByText(text, { exact: false }).first().waitFor({ state: 'visible', timeout: t })
  console.log(`\nSocialIQ judge walkthrough → ${BASE}\n`)

  try {
    await step('1. Open site; value is clear immediately', async () => {
      await p.goto(BASE + '/'); await see('One intelligent view'); await see('explains why, predicts what is next'); await p.waitForTimeout(900); await shot('01-landing')
    })
    await step('2. Enter demo mode; data is labelled DEMO DATA', async () => {
      await p.getByRole('button', { name: /Explore the live demo/ }).click(); await p.waitForURL('**/app')
      await see('DEMO DATA'); await see('synthetic creator, not a real account')
    })
    await step('3. See analytics: KPIs, trend, platform comparison, insight headline', async () => {
      await see('Total reach'); await see('Platform comparison'); await see('Top content'); await see('Social DNA')
      await see('Your audience grew'); await p.waitForTimeout(1500); await shot('02-overview', true)
    })
    await step('4. Analytics: why engagement changed + best times + cross-platform + anomalies', async () => {
      await p.goto(BASE + '/app/analytics'); await see('Why engagement changed'); await see('Statistically significant')
      await see('Best publishing times'); await see('Cross-platform intelligence'); await see('Anomaly detection'); await p.waitForTimeout(1500); await shot('03-analytics', true)
    })
    await step('5. Ask the assistant; it uses real tools and shows a card', async () => {
      await p.goto(BASE + '/app/assistant'); await see('What would you like to know?')
      await p.getByRole('button', { name: 'Why did my engagement drop?' }).click()
      await see('analyze_engagement'); await see('What changed in engagement'); await see('Statistically significant'); await p.waitForTimeout(700); await shot('04-assistant')
      await p.getByRole('textbox', { name: 'Ask the assistant' }).fill('Which platform is performing best?'); await p.keyboard.press('Enter')
      await see('compare_platforms'); await see('Platform comparison'); await p.waitForTimeout(500)
      await p.screenshot({ path: `${OUT}/05-assistant-compare.png`, fullPage: false })
    })
    await step('6. Predict content performance', async () => {
      await p.goto(BASE + '/app/predictions'); await p.getByRole('button', { name: /Predict performance/ }).click()
      await see('Pushing the score up'); await see('Holding it back'); await see('80% range'); await p.waitForTimeout(1200); await shot('06-prediction', true)
    })
    await step('7. Understand why (SHAP) and compare runs with a what-if', async () => {
      // The default form time depends on the current date, so the model may legitimately find a what-if improvement or not.
      const tip = p.getByText('Each suggestion was re-scored').first()
      const none = p.getByText('No single change was predicted to improve this post')
      await tip.or(none).first().waitFor({ timeout: 8000 })
      if (await tip.isVisible()) { await p.getByRole('button', { name: /predicted to/ }).first().click(); await see('Compare runs'); await p.waitForTimeout(900) }
      await p.getByRole('button', { name: /Model details/ }).click(); await see('Held-out test'); await see('Leakage controls'); await p.waitForTimeout(500); await shot('07-model-card')
      await p.keyboard.press('Escape')
    })
    await step('8. Compare platforms (cross-platform focus recommendation)', async () => {
      await p.goto(BASE + '/app/insights'); await see('Model-suggested ideas for tomorrow'); await see('gives you the most engagement per follower'); await p.waitForTimeout(800); await shot('08-insights')
    })
    await step('9. Security & privacy controls', async () => {
      await p.goto(BASE + '/app/privacy'); await see('SocialIQ never needs your social-media password'); await see('What we do not claim')
      await see('Demo only'); await p.waitForTimeout(600); await shot('09-privacy', true)
    })
    await step('10. Mobile layout has no horizontal overflow', async () => {
      const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 }); const mp = await m.newPage()
      await mp.goto(BASE + '/'); await mp.getByRole('button', { name: /Explore the live demo/ }).click(); await mp.waitForURL('**/app');
      await mp.getByText('Total reach').first().waitFor(); await mp.waitForTimeout(1500)
      for (const u of ['/app', '/app/analytics', '/app/predictions', '/app/privacy']) {
        await mp.goto(BASE + u); await mp.waitForTimeout(1500)
        const w = await mp.evaluate(() => document.documentElement.scrollWidth)
        if (w > 392) throw new Error(`${u} overflows horizontally: ${w}px`)
      }
      await mp.goto(BASE + '/app'); await mp.waitForTimeout(1500); await mp.screenshot({ path: `${OUT}/10-mobile.png` }); await m.close()
    })
    if (pageErrors.length) throw new Error('page errors: ' + pageErrors.join(' | '))
    console.log(`\nAll ${steps.length} steps passed.\n`)
  } catch (e) {
    process.exitCode = 1; console.error('\nWalkthrough FAILED\n')
  } finally { await browser.close() }
})()
