/**
 * Phase 5 acceptance against the real FastAPI backend and running app.
 *
 *   cd backend && uvicorn app.main:app --port 8000
 *   cd frontend && npm run dev
 *   cd frontend && npm run acceptance:phase5
 *
 * Set ACCEPTANCE_SHOTS=1 to keep screenshots in .tmp-acceptance-phase5/.
 */
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright-core'

const APP = (process.env.LUNANAV_APP ?? 'http://127.0.0.1:5173').replace(/\/$/, '')
const API = (process.env.LUNANAV_API ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const SHOTS = process.env.ACCEPTANCE_SHOTS === '1'
const CHROME = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const DEC1 = '2026-12-01T00:00:00Z'
const DEC11 = '2026-12-11T00:00:00Z'
const DURATION = 168

const results = []
let browser
let page
let pageErrors = []
let apiFailures = []
let shots = 0

async function apiGet(path) {
  const response = await fetch(`${API}${path}`)
  const body = await response.json()
  if (!response.ok) throw new Error(`${path} -> ${response.status}: ${body.message ?? JSON.stringify(body)}`)
  return body
}

async function apiPost(path, body) {
  const response = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(`${path} -> ${response.status}: ${data.message ?? JSON.stringify(data)}`)
  return data
}

const text = async (locator) => (await locator.innerText()).replace(/\s+/g, ' ').trim()

async function screenshot(name) {
  if (!SHOTS) return
  await mkdir('.tmp-acceptance-phase5', { recursive: true })
  await page.screenshot({
    path: `.tmp-acceptance-phase5/${String(++shots).padStart(2, '0')}-${name}.png`,
    fullPage: true,
  })
}

async function test(id, title, fn) {
  pageErrors = []
  apiFailures = []
  try {
    const notes = await fn()
    results.push({ id, title, status: 'PASS', notes: notes ?? '' })
    console.log(`PASS ${id} ${title}`)
  } catch (error) {
    results.push({ id, title, status: 'FAIL', notes: error instanceof Error ? error.message : String(error) })
    console.error(`FAIL ${id} ${title}\n      ${error instanceof Error ? error.stack : error}`)
    await page.screenshot({ path: `/tmp/lunanav-phase5-failure-${id}.png`, fullPage: true }).catch(() => {})
  }
}

async function openPlanner() {
  await page.goto(`${APP}/#planner`, { waitUntil: 'networkidle', timeout: 120_000 })
  await page.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 120_000 })
}

async function main() {
  browser = await chromium.launch({ executablePath: CHROME, headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  page = await context.newPage()
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('response', (response) => {
    if (response.url().includes('/api/') && response.status() >= 500) {
      apiFailures.push(`${response.status()} ${response.url()}`)
    }
  })

  await test('P5-1', 'Engineering orientation and sensitivity API', async () => {
    const fixed = await apiGet(
      `/api/engineering?site_id=de-gerlache-rim&window=initial&panel_design=fixed&panel_tilt_deg=45&panel_azimuth_deg=180`,
    )
    const power = fixed.power
    assert.equal(power.design.selected, 'fixed')
    assert.equal(power.design.tilt_deg, 45)
    assert.equal(power.design.azimuth_deg, 180)
    assert.deepEqual(power.designs.map((item) => item.id), ['horizontal', 'vertical_tracking', 'fixed'])
    const selected = power.designs.find((item) => item.id === 'fixed')
    assert.ok(Math.abs(power.budget.array_energy_wh - selected.energy_wh) < 1e-6)
    assert.equal(power.series.solar_w.length, power.series.times_utc.length)
    const cases = new Map(power.sensitivity.cases.map((item) => [item.id, item]))
    assert.equal(cases.size, 7)
    assert.ok(cases.get('solar_low').array_energy_wh < cases.get('base').array_energy_wh)
    assert.ok(cases.get('load_high').min_soc_pct <= cases.get('base').min_soc_pct)
    assert.ok(power.sensitivity.method.includes('One-at-a-time'))
    return `Fixed 45°/180° selected; battery follows it (${power.budget.array_energy_wh.toFixed(0)} Wh); 7 sensitivity cases span ${power.sensitivity.min_soc_range_pct.join('–')}% SOC.`
  })

  await test('P5-2', 'Decision API carries orientation and science mode', async () => {
    const decision = await apiPost('/api/decision', {
      landing_utc: DEC1,
      duration_hours: DURATION,
      site_ids: ['shackleton-rim', 'connecting-ridge', 'de-gerlache-rim'],
      thresholds: {
        min_sun_visible_pct: 0,
        min_earth_visible_pct: 0,
        max_earth_blackout_hours: 8000,
        max_darkness_hours: 8000,
        power_demand_w: 40,
      },
      weights: { sunlight: 0.3, earth_visibility: 0.2, communication: 0.1, science: 0.4 },
      panel_design: 'fixed',
      panel_tilt_deg: 45,
      panel_azimuth_deg: 180,
    })
    assert.equal(decision.weights.science, 0.4)
    assert.ok(decision.sites.length === 3)
    for (const site of decision.sites) {
      assert.equal(site.power.panel_design, 'fixed')
      assert.equal(site.power.panel_tilt_deg, 45)
      assert.ok(site.reasons.join(' ').includes('Science priority includes'))
      assert.ok(site.reasons.join(' ').includes('not water-ice or rover-access evidence'))
    }
    return 'Decision API honors the fixed panel selection and explains PSR proximity without claiming water ice.'
  })

  await test('P5-3', 'Energy panel and built-in sensitivity', async () => {
    await openPlanner()
    await page.getByRole('heading', { name: 'Energy timeline' }).waitFor({ timeout: 120_000 })
    const fixedResponse = page.waitForResponse(
      (response) => response.url().includes('/api/engineering') && response.url().includes('panel_design=fixed'),
      { timeout: 120_000 },
    )
    await page.getByRole('button', { name: 'Fixed tilt/azimuth' }).click()
    await fixedResponse
    await page.getByLabel('Panel tilt (°)').fill('45')
    await page.getByLabel('Panel azimuth (°)').fill('180')
    const sensitivity = page.getByText(/Sensitivity · minimum battery range/)
    await sensitivity.waitFor({ timeout: 120_000 })
    await sensitivity.click()
    const body = await text(page.locator('body'))
    assert.ok(body.includes('selected'))
    assert.ok(body.includes('Base case'))
    assert.ok(body.includes('Solar conversion −10%'))
    assert.ok(body.includes('Load +20%'))
    assert.ok(!/NASA-approved|fully safe/i.test(body), 'power UI makes an unsupported safety claim')
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    assert.equal(apiFailures.length, 0, `API failures: ${apiFailures.join(' | ')}`)
    await screenshot('energy-orientation')
    return 'The power panel selected the fixed array, rendered the timeline and exposed the sensitivity table with no console/API errors.'
  })

  await test('P5-4', 'Science exploration mode UI', async () => {
    await page.goto(`${APP}/#decision`, { waitUntil: 'networkidle', timeout: 120_000 })
    await page.getByRole('heading', { name: 'Mission decision support' }).waitFor({ timeout: 120_000 })
    await page.getByRole('button', { name: 'Science exploration' }).click()
    await page.getByRole('heading', { name: 'Science exploration mode' }).waitFor({ timeout: 120_000 })
    const body = await text(page.locator('body'))
    assert.ok(body.includes('nearest mapped PSR'))
    assert.ok(body.includes('not a traverse plan'))
    assert.ok(body.includes('Science weight 0.40'))
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    assert.equal(apiFailures.length, 0, `API failures: ${apiFailures.join(' | ')}`)
    await screenshot('science-exploration')
    return 'Science exploration mode is visible, sends the science weights, lists PSR context and states the traverse/water-ice limits.'
  })

  await test('P5-5', 'Delay power and requirement comparison UI', async () => {
    await openPlanner()
    await page.getByLabel('Landing site').selectOption('de-gerlache-rim')
    await page.getByLabel('Landing time (UTC)').fill(DEC1.slice(0, 16))
    await page.getByLabel('Duration in hours').fill(String(DURATION))
    await page.waitForTimeout(800)
    await page.getByRole('button', { name: 'Compare scenarios' }).click()
    await page.getByRole('tab', { name: /Reschedule a mission/ }).click()
    await page.getByLabel('Proposed landing time (UTC)').fill(DEC11.slice(0, 16))
    await page.getByRole('heading', { name: 'Requirement verdicts' }).waitFor({ timeout: 120_000 })
    await page.getByRole('heading', { name: 'Power and battery' }).waitFor({ timeout: 120_000 })
    const body = await text(page.locator('body'))
    assert.ok(body.includes('Array energy'))
    assert.ok(body.includes('Minimum battery'))
    assert.ok(body.includes('Unserved load'))
    assert.ok(body.includes('New failures:') || body.includes('Improvements:') || body.includes('No requirement verdict changes.'))
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    assert.equal(apiFailures.length, 0, `API failures: ${apiFailures.join(' | ')}`)
    await screenshot('delay-power')
    return 'The reschedule view rendered requirement verdict changes, array energy, minimum battery and unserved-load deltas for the committed windows.'
  })

  await test('P5-6', 'Date and power changes refresh the best-site recommendation', async () => {
    await page.goto(`${APP}/#decision`, { waitUntil: 'networkidle', timeout: 120_000 })
    await page.getByRole('heading', { name: 'Mission decision support' }).waitFor({ timeout: 120_000 })

    const alternateResponse = page.waitForResponse(
      (response) => response.url().endsWith('/api/decision') && response.request().method() === 'POST',
      { timeout: 120_000 },
    )
    await page.getByRole('button', { name: /11 Dec 2026/ }).click()
    await alternateResponse
    await page.getByText(/de Gerlache.*is top-ranked/).waitFor({ timeout: 120_000 })

    const overloadResponse = page.waitForResponse(
      (response) => response.url().endsWith('/api/decision') && response.request().method() === 'POST',
      { timeout: 120_000 },
    )
    await page.getByLabel('Average power demand (W)').fill('100000')
    await overloadResponse
    await page.getByText('No site is recommended').waitFor({ timeout: 120_000 })

    const restoredResponse = page.waitForResponse(
      (response) => response.url().endsWith('/api/decision') && response.request().method() === 'POST',
      { timeout: 120_000 },
    )
    await page.getByLabel('Average power demand (W)').fill('40')
    await restoredResponse
    await page.getByText(/de Gerlache.*is top-ranked/).waitFor({ timeout: 120_000 })

    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    assert.equal(apiFailures.length, 0, `API failures: ${apiFailures.join(' | ')}`)
    await screenshot('decision-date-requirement')
    return 'Changing the date to 11 Dec produced a top-ranked site; raising the load to 100 kW removed it and restoring 40 W recovered it.'
  })

  await browser.close()
  console.log('\n=== PHASE 5 ACCEPTANCE RESULTS ===')
  for (const result of results) {
    console.log(`${result.status}  ${result.id}  ${result.title}\n      ${result.notes}`)
  }
  const failed = results.filter((result) => result.status === 'FAIL')
  console.log(`\n${results.length - failed.length}/${results.length} tests passed`)
  if (failed.length) process.exitCode = 1
}

main().catch(async (error) => {
  console.error(error)
  await browser?.close().catch(() => {})
  process.exitCode = 1
})
