/**
 * Browser test of the Assistant page. EXPECT=gemini (backend has GEMINI_API_KEY), EXPECT=local (no key),
 * or EXPECT=fallback (key set but Gemini failing: expects the visible fallback notice).
 *   EXPECT=gemini node e2e/assistant.cjs      EXPECT=local node e2e/assistant.cjs
 * Asserts for each of 4 prompts: the right SocialIQ tool chip, the right result card, and the right mode line.
 */
const { chromium } = require('playwright')
const BASE = process.env.BASE_URL || 'http://localhost:5173'
const EXPECT = process.env.EXPECT || 'local'
const SHOTS = process.env.SHOTS || '/tmp'
const CASES = [
  ['Why did my engagement drop?', 'analyze_engagement', 'What changed in engagement'],
  ['Which platform is performing best?', 'compare_platforms', 'Platform comparison'],
  ['What should I post next?', 'generate_content_strategy', 'Recommended plan'],
  ['Show my best-performing content.', 'get_top_content', 'Top content'],
]
;(async () => {
  const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 1360, height: 1000 } })).newPage()
  const errs = []; p.on('pageerror', (e) => errs.push(e.message))
  let failed = false
  await p.goto(BASE + '/'); await p.getByRole('button', { name: /Explore the live demo/ }).click(); await p.waitForURL('**/app')
  console.log(`\nAssistant browser test, expecting mode = ${EXPECT}\n`)
  for (const [i, [q, tool, card]] of CASES.entries()) {
    try {
      await p.goto(BASE + '/app/assistant'); await p.getByText('What would you like to know?').waitFor()
      const t = Date.now()
      await p.getByRole('textbox', { name: 'Ask the assistant' }).fill(q); await p.keyboard.press('Enter')
      const chip = p.locator('span.font-mono', { hasText: tool }); await chip.first().waitFor({ timeout: 30000 })
      await p.getByText(card, { exact: false }).first().waitFor({ timeout: 10000 })
      const modeLine = await p.getByText(/using SocialIQ tools|Rule-based router/).first().innerText()
      const answer = await p.locator('div.whitespace-pre-wrap').first().innerText()
      const notice = await p.getByText(/answered with the built-in router instead/).count()
      if (EXPECT === 'gemini') {
        if (!/^Gemini \(gemini-/.test(modeLine.trim())) throw new Error(`mode line was: ${modeLine}`)
        if (!answer.startsWith('[MOCK-GEMINI]')) throw new Error(`answer did not come from the Gemini path: ${answer.slice(0, 60)}`)
        if (notice) throw new Error('unexpected fallback notice')
      } else {
        if (!/Rule-based router/.test(modeLine)) throw new Error(`mode line was: ${modeLine}`)
        if (EXPECT === 'fallback' && !(await p.getByText(/Gemini API error 500; answered with the built-in router instead/).count())) throw new Error('fallback notice not shown')
        if (EXPECT === 'local' && notice) throw new Error('fallback notice shown although no key is configured')
        if (answer.startsWith('[MOCK-GEMINI]')) throw new Error('local mode returned a Gemini answer')
      }
      await p.waitForTimeout(600); await p.screenshot({ path: `${SHOTS}/assistant-${EXPECT}-${i + 1}.png` })
      console.log(`  ✔ "${q}"\n      tool=${tool} · card="${card}" · ${modeLine.trim()} · ${Date.now() - t}ms\n      answer: ${answer.replace(/\n/g, ' ').slice(0, 110)}…`)
    } catch (e) { failed = true; console.log(`  ✘ "${q}": ${e.message.split('\n')[0]}`) }
  }
  if (errs.length) { failed = true; console.log('page errors:', errs.join(' | ')) }
  console.log(failed ? '\nFAILED\n' : '\nAll 4 prompts passed.\n'); await b.close(); process.exit(failed ? 1 : 0)
})()
