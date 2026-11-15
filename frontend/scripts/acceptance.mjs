/**
 * Phase 4 acceptance run against the real FastAPI backend and the running app.
 *
 *   cd backend && uvicorn app.main:app --port 8000
 *   cd frontend && npm run dev
 *   cd frontend && npm run acceptance
 *
 * Set ACCEPTANCE_SHOTS=1 to keep screenshots in .tmp-acceptance/.
 * There is no hosted deployment in this repository; set LUNANAV_APP to test one.
 */
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright-core'

const APP = (process.env.LUNANAV_APP ?? 'http://127.0.0.1:5173').replace(/\/$/, '')
const API = (process.env.LUNANAV_API ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const SHOTS = process.env.ACCEPTANCE_SHOTS === '1'
const CHROME = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const SITE_IDS = ['shackleton-rim', 'connecting-ridge', 'de-gerlache-rim']
const SITE_LABEL = {
  'shackleton-rim': 'Shackleton Crater Rim (SR1)',
  'connecting-ridge': 'Shackleton-de Gerlache Connecting Ridge (CR1)',
  'de-gerlache-rim': 'de Gerlache Crater Rim (GR1)',
}
const DEC1 = '2026-12-01T00:00:00Z'
const DEC11 = '2026-12-11T00:00:00Z'
const DURATION = 168
const TARGETS = { min_sun_visible_pct: 60, min_earth_visible_pct: 50, max_earth_blackout_hours: 12 }

const results = []
let page
let browser
let consoleErrors = []
let pageErrors = []
let apiFailures = []
let snapshots = 0

/* ------------------------------ API helpers ------------------------------ */

async function apiGet(path) {
  const res = await fetch(`${API}${path}`)
  const body = await res.json()
  if (!res.ok) throw new Error(`${path} -> ${res.status}: ${body.message ?? JSON.stringify(body)}`)
  return body
}

async function apiPost(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(`${path} -> ${res.status}: ${data.message ?? JSON.stringify(data)}`)
  return data
}

const scenario = (site, landing = DEC1, duration = DURATION, mode = 'jpl') =>
  apiPost('/api/scenario', { location: { site_id: site }, landing_utc: landing, duration_hours: duration, mode })

const requirements = (site, landing = DEC1, duration = DURATION, mode = 'jpl', thresholds = TARGETS) =>
  apiPost('/api/requirements', {
    location: { site_id: site },
    landing_utc: landing,
    duration_hours: duration,
    mode,
    thresholds,
  })

const snapshot = (site, time, mode = 'jpl') =>
  apiPost('/api/snapshot', { location: { site_id: site }, time_utc: time, mode })

const reschedule = (site, original, proposed, duration = DURATION, mode = 'jpl') =>
  apiPost('/api/reschedule', {
    location: { site_id: site },
    original_landing_utc: original,
    proposed_landing_utc: proposed,
    duration_hours: duration,
    mode,
  })

/* ------------------------------ UI helpers ------------------------------- */

const fmtDate = (iso) => iso.slice(0, 16).replace('T', ' ')
const fmtHours = (h) => {
  if (h == null || Number.isNaN(h)) return '—'
  if (h < 1) return `${Math.round(h * 60)} min`
  if (h < 48) return `${h.toFixed(1)} h`
  const total = Math.round(h)
  const d = Math.floor(total / 24)
  return `${d} d ${total - d * 24} h`
}
const fmtMetric = (value, unit) => {
  if (value == null) return '—'
  if (unit === 'h') return fmtHours(value)
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 'deg') return `${value.toFixed(2)}°`
  return `${value.toFixed(2)} ${unit}`
}
const fmtLat = (v) => `${Math.abs(v).toFixed(3)}° ${v < 0 ? 'S' : 'N'}`
const fmtLon = (v) => `${Math.abs(v).toFixed(3)}° ${v < 0 ? 'W' : 'E'}`
const normalise = (s) => s.replace(/\s+/g, ' ').trim()
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

async function text(locator) {
  return normalise(await locator.innerText())
}

function snapshotSection(body) {
  const name = body === 'sun' ? 'Sun' : 'Earth'
  return page.getByRole('heading', { name, exact: true }).locator('xpath=ancestor::div[.//dl][1]')
}

async function snapshotValue(body, label) {
  const section = snapshotSection(body)
  const dt = section.locator('dt').filter({ hasText: new RegExp(`^${escapeRe(label)}$`) }).first()
  return text(dt.locator('xpath=following-sibling::dd[1]'))
}

async function metricValue(label) {
  const dt = page.locator('dt').filter({ hasText: new RegExp(`^${escapeRe(label)}$`) }).first()
  return text(dt.locator('xpath=following-sibling::dd[1]'))
}

async function scenarioRange(date, duration) {
  const end = new Date(Date.parse(date) + duration * 3_600_000).toISOString()
  await page
    .getByText(new RegExp(`${escapeRe(fmtDate(date))} to ${escapeRe(fmtDate(end))} UTC`))
    .first()
    .waitFor({ timeout: 90_000 })
  await page.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 90_000 })
}

async function openPlanner() {
  await page.goto(`${APP}/#planner`, { waitUntil: 'networkidle', timeout: 90_000 })
  await scenarioRange(DEC1, DURATION)
}

async function setPlanner(site, date = DEC1, duration = DURATION) {
  const siteSelect = page.getByLabel('Landing site')
  const dateInput = page.getByLabel('Landing time (UTC)')
  const durationInput = page.getByLabel('Duration in hours')
  if ((await siteSelect.inputValue()) !== site) {
    await siteSelect.selectOption(site)
  }
  if ((await dateInput.inputValue()) !== date.slice(0, 16)) {
    await dateInput.fill(date.slice(0, 16))
  }
  if ((await durationInput.inputValue()) !== String(duration)) {
    await durationInput.fill(String(duration))
  }
  await scenarioRange(date, duration)
}

async function openCompare() {
  await page.goto(`${APP}/#compare`, { waitUntil: 'networkidle', timeout: 90_000 })
  await page.getByText('Side by side').waitFor({ timeout: 90_000 })
}

async function bandData() {
  return page.locator('div.relative.hatch-blocked').evaluateAll((nodes) =>
    nodes.map((node) => {
      const row = node.parentElement
      const spans = [...(row?.querySelectorAll(':scope > span') ?? [])]
      return {
        label: spans[0]?.textContent?.trim() ?? '',
        total: spans.at(-1)?.textContent?.trim() ?? '',
        titles: [...node.children].map((child) => child.getAttribute('title')).filter(Boolean),
      }
    }),
  )
}

async function panoramaLabel() {
  return page.getByRole('img', { name: /Horizon panorama/ }).getAttribute('aria-label')
}

function panoramaAngles(label) {
  const m = label.match(
    /Sun at azimuth (-?\d+)°, elevation (-?\d+\.\d+)°\. Earth at azimuth (-?\d+)°, elevation (-?\d+\.\d+)°/,
  )
  assert.ok(m, `unexpected panorama label: ${label}`)
  return { sunAz: Number(m[1]), sunEl: Number(m[2]), earthAz: Number(m[3]), earthEl: Number(m[4]) }
}

async function waitForCompareResult() {
  await page.getByText('Side by side').waitFor({ timeout: 90_000 })
  await page.getByText('Trade-offs').waitFor({ timeout: 90_000 })
}

async function screenshot(name) {
  if (!SHOTS) return
  await mkdir('.tmp-acceptance', { recursive: true })
  await page.screenshot({ path: `.tmp-acceptance/${String(++snapshots).padStart(2, '0')}-${name}.png`, fullPage: true })
}

function resetDiagnostics() {
  consoleErrors = []
  pageErrors = []
  apiFailures = []
}

function note(message) {
  console.log(`      ${message}`)
}

async function test(id, title, fn) {
  resetDiagnostics()
  try {
    const notes = await fn()
    results.push({ id, title, status: 'PASS', notes: notes ?? '' })
    console.log(`PASS ${id} ${title}`)
  } catch (error) {
    results.push({ id, title, status: 'FAIL', notes: error instanceof Error ? error.message : String(error) })
    console.error(`FAIL ${id} ${title}\n      ${error instanceof Error ? error.stack : error}`)
    await page.screenshot({ path: `/tmp/lunanav-acceptance-failure-${id}.png`, fullPage: true }).catch(() => {})
  }
}

/* -------------------------------- Tests --------------------------------- */

async function main() {
  browser = await chromium.launch({ executablePath: CHROME, headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  page = await context.newPage()
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('response', (response) => {
    if (response.url().includes('/api/') && response.status() >= 500) {
      apiFailures.push(`${response.status()} ${response.url()}`)
    }
  })

  await test('T1', 'Website loading and dashboard', async () => {
    resetDiagnostics()
    await page.goto(`${APP}/#planner`, { waitUntil: 'networkidle', timeout: 90_000 })
    await scenarioRange(DEC1, DURATION)
    assert.equal(await page.title(), 'LunaNav')
    assert.ok(await page.locator('.leaflet-container').count(), 'lunar map is missing')
    assert.ok(await page.getByLabel('Landing site').isVisible(), 'site selector is not visible')
    assert.ok(await page.getByLabel('Landing time (UTC)').isVisible(), 'date control is not visible')
    assert.ok(await page.getByRole('button', { name: /JPL connected/i }).count(), 'backend/JPL status is missing')
    const config = await apiGet('/api/config')
    const sites = await apiGet('/api/sites')
    assert.equal(config.app.name, 'LunaNav')
    assert.ok(sites.length >= 3)
    assert.equal(consoleErrors.length, 0, `console errors: ${consoleErrors.join(' | ')}`)
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    await screenshot('dashboard-desktop')
    return `Dashboard, map, selectors loaded; ${sites.length} sites; backend /api/config and /api/sites 200; no console errors.`
  })

  await test('T2', 'Landing-site selection', async () => {
    await openPlanner()
    const sites = await apiGet('/api/sites')
    for (const id of ['shackleton-rim', 'connecting-ridge', 'de-gerlache-rim', 'shackleton-rim']) {
      if ((await page.getByLabel('Landing site').inputValue()) !== id) {
        await page.getByLabel('Landing site').selectOption(id)
      }
      const site = sites.find((s) => s.id === id)
      await page.getByRole('heading', { name: site.name, exact: true }).first().waitFor({ timeout: 90_000 })
      const body = await text(page.locator('body'))
      assert.ok(body.includes(`${fmtLat(site.latitude_deg)}, ${fmtLon(site.longitude_deg)}`), `${id} coordinates missing`)
      assert.ok(
        await page.locator('.leaflet-tooltip').filter({ hasText: site.name }).count(),
        `${id} is not labelled on the map`,
      )
      assert.ok(await page.locator('.leaflet-marker-icon').filter({ hasText: 'A' }).count(), 'selected marker A is missing')
    }
    await screenshot('site-selection')
    return 'All three sites loaded their own scenario and coordinates; selected marker A and map label change with the site.'
  })

  await test('T3', 'Mission date and duration selection', async () => {
    await openPlanner()
    await setPlanner('shackleton-rim', DEC1, DURATION)
    const a = await scenario('shackleton-rim', DEC1, DURATION)
    assert.equal(a.end_utc, '2026-12-08T00:00:00Z')
    assert.ok((await text(page.locator('body'))).includes('2026-12-01 00:00 to 2026-12-08 00:00 UTC'))
    assert.ok((await text(page.locator('body'))).includes('7 d 0 h'))
    await page.getByLabel('Landing time (UTC)').fill(DEC11.slice(0, 16))
    await scenarioRange(DEC11, DURATION)
    const b = await scenario('shackleton-rim', DEC11, DURATION)
    assert.equal(b.end_utc, '2026-12-18T00:00:00Z')
    assert.ok((await text(page.locator('body'))).includes('2026-12-11 00:00 to 2026-12-18 00:00 UTC'))
    assert.ok((await text(page.locator('body'))).includes('7 d 0 h'))
    return '1 Dec produced 1–8 Dec and 11 Dec produced 11–18 Dec; both requests were 168 h and the results reloaded.'
  })

  await test('T4', 'NASA Sun and Earth data integration', async () => {
    await setPlanner('shackleton-rim', DEC1, DURATION)
    const snap = await snapshot('shackleton-rim', DEC1)
    const sc = await scenario('shackleton-rim', DEC1, DURATION)
    const phase3 = await apiGet('/api/phase3/windows')
    const committed = phase3.sites.find((s) => s.site_id === 'shackleton-rim').windows.initial.summary

    assert.equal(await snapshotValue('sun', 'Elevation (geometric)'), `${snap.sun.elevation_deg.toFixed(2)}°`)
    assert.equal(await snapshotValue('sun', 'Azimuth'), `${snap.sun.azimuth_deg.toFixed(1)}°`)
    assert.equal(await snapshotValue('earth', 'Elevation (geometric)'), `${snap.earth.elevation_deg.toFixed(2)}°`)
    assert.equal(await snapshotValue('earth', 'Azimuth'), `${snap.earth.azimuth_deg.toFixed(1)}°`)
    assert.equal(await snapshotValue('sun', 'Terrain skyline at that azimuth'), `${snap.sun.terrain_horizon_deg.toFixed(2)}°`)
    assert.equal(await snapshotValue('earth', 'Clearance above terrain'), `${snap.earth.clearance_deg.toFixed(2)}°`)
    assert.match(await page.getByText(/UTC\. Move the timeline cursor/).innerText(), /2026-12-01 00:00 UTC/)
    assert.ok((await text(page.locator('body'))).includes('Sourced scientific data'))
    assert.ok((await text(page.locator('body'))).includes('JPL Horizons (live)'))
    assert.ok((await text(page.locator('body'))).includes('LOLA horizon masks'))
    assert.equal(await page.getByRole('radio', { name: 'JPL Live' }).getAttribute('aria-checked'), 'true')

    const uiSun = Number((await metricValue('Sun above terrain (share)')).replace('%', ''))
    const uiEarth = Number((await metricValue('Earth above terrain (share)')).replace('%', ''))
    assert.ok(Math.abs(uiSun - committed.sun_visible_pct) <= 1, 'UI sunlight does not match committed Phase 3 data')
    assert.ok(Math.abs(uiEarth - committed.earth_visible_pct) <= 1, 'UI Earth visibility does not match committed Phase 3 data')
    const nullMetric = sc.metrics.find((m) => m.id === 'hours_until_first_sunset')
    assert.equal(nullMetric.value, null)
    assert.equal(await metricValue('Time to first sunset'), '—')
    return `Snapshot az/el matches /api/snapshot; JPL/LOLA provenance shown; Phase 3 initial window agrees (${uiSun}% Sun, ${uiEarth}% Earth); missing event time shown as —.`
  })

  await test('T5', 'Sun and Earth sky visualization', async () => {
    const sc = await scenario('shackleton-rim', DEC1, DURATION)
    const snap = await snapshot('shackleton-rim', DEC1)
    const pano = page.getByRole('img', { name: /Horizon panorama/ })
    assert.ok(await pano.count(), 'horizon panorama is missing')
    const a0 = panoramaAngles(await panoramaLabel())
    assert.equal(a0.sunAz, Math.round(sc.series.sun_azimuth_deg[0]))
    assert.equal(a0.sunEl, Number(sc.series.sun_elevation_deg[0].toFixed(1)))
    assert.equal(a0.earthAz, Math.round(sc.series.earth_azimuth_deg[0]))
    assert.equal(a0.earthEl, Number(sc.series.earth_elevation_deg[0].toFixed(1)))
    assert.ok((await pano.locator('circle').count()) > 50, 'Sun/Earth track markers are missing')
    assert.ok(await pano.getByText('geometric horizon').count(), 'geometric horizon is missing')
    const body = await text(page.locator('body'))
    assert.ok(body.includes('Sun') && body.includes('Earth') && body.includes('Terrain'))
    assert.ok(body.includes('two-tier LOLA ray-march'), 'terrain source is not labelled')

    const before = await page.getByText(/UTC\. Move the timeline cursor/).innerText()
    await page.getByRole('button', { name: 'Next sample' }).click()
    await page.waitForFunction((old) => {
      const el = [...document.querySelectorAll('span')].find((n) => n.textContent?.includes('Move the timeline cursor'))
      return el && el.textContent !== old
    }, before, { timeout: 15_000 })
    const a1 = panoramaAngles(await panoramaLabel())
    assert.equal(a1.sunAz, Math.round(sc.series.sun_azimuth_deg[1]))
    assert.equal(a1.earthEl, Number(sc.series.earth_elevation_deg[1].toFixed(1)))

    const labels = await snapshotSection('sun').innerText()
    const expectedStatus = snap.sun.visible
      ? 'Above terrain horizon'
      : snap.sun.elevation_deg > 0
        ? 'Blocked by terrain'
        : 'Below geometric horizon'
    assert.ok(labels.includes(expectedStatus), `Sun status does not match backend: ${labels}`)

    await page.getByLabel('Landing site').selectOption('__custom__')
    await page.getByText(/Custom −87\.000° 0\.000°/).first().waitFor({ timeout: 90_000 })
    await page.getByText('No LOLA horizon mask for this location: flat geometric horizon used.').waitFor({ timeout: 90_000 })
    const custom = await apiPost('/api/scenario', {
      location: { latitude_deg: -87, longitude_deg: 0 },
      landing_utc: DEC1,
      duration_hours: DURATION,
      mode: 'jpl',
    })
    assert.equal(custom.provenance.overall, 'geometric_only')
    assert.ok((await text(page.locator('body'))).includes('Geometric only, no terrain'))
    return `Panorama markers, terrain skyline and geometric horizon rendered; marker az/el match the series; Next sample synchronized the snapshot; Sun status "${expectedStatus}" matches backend; custom coordinates are labelled geometric only.`
  })

  await test('T6', 'Visibility timeline and synchronization', async () => {
    await setPlanner('connecting-ridge', DEC11, DURATION)
    const sc = await scenario('connecting-ridge', DEC11, DURATION)
    const bands = await bandData()
    assert.equal(bands.length, 3, 'expected Sun, Earth and Both bands')
    assert.deepEqual(bands.map((b) => b.label), ['Sun', 'Earth', 'Both'])
    assert.equal(bands[0].total, fmtHours(168))
    assert.equal(bands[1].total, fmtHours(sc.metrics.find((m) => m.id === 'earth_visible_hours').value))
    assert.equal(bands[2].total, fmtHours(sc.metrics.find((m) => m.id === 'both_visible_hours').value))
    assert.ok(sc.intervals.sun_visible.length > 0 && sc.intervals.earth_visible.length > 0 && sc.intervals.both_visible.length > 0)
    assert.ok(bands.every((b) => b.titles.length > 0), 'visible interval bands are missing')
    const firstSun = sc.intervals.sun_visible[0]
    assert.ok(
      bands[0].titles[0].includes(`${firstSun.start_utc.slice(0, 16).replace('T', ' ')} to ${firstSun.end_utc.slice(0, 16).replace('T', ' ')}`),
      'timeline interval timestamp does not match the backend',
    )

    const band = page.locator('div.relative.hatch-blocked').first()
    await band.scrollIntoViewIfNeeded()
    const box = await band.boundingBox()
    assert.ok(box)
    const frac = 0.4
    const index = Math.round(frac * (sc.series.times_utc.length - 1))
    await page.mouse.click(box.x + box.width * frac, box.y + box.height / 2)
    await page.waitForTimeout(900)
    const desc = await page.getByText(/UTC\. Move the timeline cursor/).innerText()
    assert.ok(desc.includes(fmtDate(sc.series.times_utc[index])), `timeline click did not select ${sc.series.times_utc[index]}: ${desc}`)
    const a = panoramaAngles(await panoramaLabel())
    assert.equal(a.sunAz, Math.round(sc.series.sun_azimuth_deg[index]))

    await setPlanner('shackleton-rim', DEC1, DURATION)
    const darkBands = await bandData()
    assert.ok(darkBands.every((b) => b.total === '0 min'), 'Site A should have no visible intervals in this window')
    assert.ok((await text(page.locator('body'))).includes('Longest Sun blackout'))
    assert.ok((await text(page.locator('body'))).includes('≥7 d 0 h'))
    assert.equal(await metricValue('Time to first sunset'), '—')
    return 'Sun/Earth/Both intervals, UTC titles and totals match the API; clicking the timeline moved the cursor and sky; Site A’s all-blocked timeline and — missing event are clearly shown.'
  })

  await test('T7', 'Mission metrics dashboard', async () => {
    await setPlanner('shackleton-rim', DEC1, DURATION)
    const sc = await scenario('shackleton-rim', DEC1, DURATION)
    const byId = new Map(sc.metrics.map((m) => [m.id, m]))
    const checks = [
      ['Sun above terrain (share)', 'sun_visible_pct'],
      ['Sun above terrain', 'sun_visible_hours'],
      ['Longest Sun blackout', 'longest_sun_blackout_hours'],
      ['Earth above terrain (share)', 'earth_visible_pct'],
      ['Earth above terrain', 'earth_visible_hours'],
      ['Longest Earth blackout', 'longest_earth_blackout_hours'],
      ['Sun and Earth simultaneously (share)', 'both_visible_pct'],
    ]
    for (const [label, id] of checks) {
      const metric = byId.get(id)
      const expected = `${metric.censored ? '≥' : ''}${fmtMetric(metric.value, metric.unit)}`
      const actual = await metricValue(label)
      assert.equal(actual, expected, `${label}: expected ${expected}, got ${actual}`)
    }
    assert.ok((await text(page.locator('body'))).includes('Mission summary'))
    assert.ok((await text(page.locator('body'))).includes('sampled every 30 min'))
    assert.ok((await text(page.locator('body'))).includes('Sunlight'))
    assert.ok((await text(page.locator('body'))).includes('Earth line of sight'))
    assert.ok((await text(page.locator('body'))).includes('Combined'))
    const phase3 = await apiGet('/api/phase3/windows')
    const committed = phase3.sites.find((s) => s.site_id === 'shackleton-rim').windows.initial.summary
    assert.ok(Math.abs(byId.get('sun_visible_pct').value - committed.sun_visible_pct) <= 1)
    assert.ok(Math.abs(byId.get('earth_visible_pct').value - committed.earth_visible_pct) <= 1)
    assert.ok(Math.abs(byId.get('longest_earth_blackout_hours').value - committed.longest_earth_blackout_hours) <= 1)
    return 'All seven required metrics match the scenario API exactly; units and Phase 3 committed values agree; lower-bound markers are shown.'
  })

  await test('T8', 'Landing-site comparison', async () => {
    await openCompare()
    const selects = page.getByLabel('Landing site')
    const dates = page.getByLabel('Landing time (UTC)')
    await selects.nth(0).selectOption('shackleton-rim')
    await selects.nth(1).selectOption('connecting-ridge')
    await dates.nth(0).fill(DEC1.slice(0, 16))
    await dates.nth(1).fill(DEC1.slice(0, 16))
    await waitForCompareResult()
    await page.getByText('B Shackleton-de Gerlache Connecting Ridge (CR1)', { exact: true }).waitFor({ timeout: 90_000 })
    const cmp = await apiPost('/api/compare', {
      a: { location: { site_id: 'shackleton-rim' }, landing_utc: DEC1, duration_hours: DURATION, mode: 'jpl' },
      b: { location: { site_id: 'connecting-ridge' }, landing_utc: DEC1, duration_hours: DURATION, mode: 'jpl' },
    })
    const body = await text(page.locator('body'))
    assert.ok(body.includes('A Shackleton Crater Rim (SR1)'))
    assert.ok(body.includes('B Shackleton-de Gerlache Connecting Ridge (CR1)'))
    assert.equal(cmp.a.landing_utc, cmp.b.landing_utc)
    assert.equal(cmp.a.duration_hours, DURATION)
    assert.equal(cmp.b.duration_hours, DURATION)
    const rows = await page.locator('table tbody tr').evaluateAll((trs) =>
      trs.map((tr) => [...tr.querySelectorAll('td')].map((td) => td.textContent?.replace(/\s+/g, ' ').trim() ?? '')),
    )
    const sunRow = rows.find((r) => r[0] === 'Sun above terrain (share)')
    assert.ok(sunRow, 'side-by-side sunlight row is missing')
    assert.equal(sunRow[1], '0.0%')
    assert.equal(sunRow[2], '100.0%')
    assert.ok(body.includes('Trade-offs') && body.includes('Comparability'))
    assert.ok(cmp.tradeoffs.length > 0, 'trade-off explanation is empty')

    await page.getByRole('tab', { name: /All candidates/ }).click()
    await page.getByRole('button', { name: 'Compare all candidates' }).click()
    const region = page.getByRole('region', { name: 'All-candidate comparison results' })
    await region.waitFor({ timeout: 90_000 })
    const regionText = await text(region)
    for (const id of SITE_IDS) assert.ok(regionText.includes(SITE_LABEL[id]), `comparison missing ${SITE_LABEL[id]}`)
    const evals = await Promise.all(SITE_IDS.map((id) => requirements(id, DEC1, DURATION)))
    for (const ev of evals) {
      for (const check of ev.checks) {
        const word = check.status === 'met' ? 'PASS' : check.status === 'not_met' ? 'FAIL' : 'UNDECIDED'
        assert.ok(regionText.includes(word), `comparison missing ${word} for ${ev.location.name}`)
      }
    }
    assert.ok(regionText.includes('does not combine them into a score'))
    assert.ok((await text(page.locator('body'))).includes('not NASA flight requirements'))
    await screenshot('comparison-desktop')
    return 'A/B share one date/duration and show separate metrics; all three candidates show per-check PASS/FAIL and an explicit no-ranking trade-off explanation.'
  })

  await test('T9', 'Mission-delay comparison', async () => {
    await openPlanner()
    const delay = page.getByRole('heading', { name: 'Landing-delay comparison' }).locator('xpath=ancestor::div[.//table][1]')
    await delay.scrollIntoViewIfNeeded()
    const body = await text(delay)
    assert.ok(body.includes('Before/after'))
    assert.ok(body.includes('Initial constraints') && body.includes('After delay'))
    assert.ok(body.includes('0% → 21%'), 'Site B delayed Earth visibility is not shown')
    assert.ok(body.includes('1% → 60%'), 'Site C delayed Earth visibility is not shown')
    assert.ok(body.includes('not a site ranking'), 'delay panel does not disclaim ranking')

    await page.locator('#delay-site').selectOption('connecting-ridge')
    await page.getByRole('button', { name: 'Compare dates' }).click()
    const result = page.getByRole('region', { name: 'Reschedule comparison result' })
    await result.waitFor({ timeout: 90_000 })
    const cmp = await reschedule('connecting-ridge', DEC1, DEC11)
    assert.equal(cmp.shift_hours, 240)
    const resultText = await text(result)
    assert.ok(resultText.includes('Shift: 240 h'))
    assert.ok(resultText.includes('same site and duration'))
    const fmtDeltaValue = (value, unit) =>
      value == null ? '—' : unit === '%' ? `${Math.round(value)}%` : `${Math.round(value * 10) / 10} ${unit}`
    for (const delta of cmp.headline_changes.filter((d) => d.id.endsWith('_hours'))) {
      assert.ok(resultText.includes(fmtDeltaValue(delta.a, delta.unit)), `${delta.id} original value missing`)
      assert.ok(resultText.includes(fmtDeltaValue(delta.b, delta.unit)), `${delta.id} delayed value missing`)
    }
    const plannerText = await text(page.locator('body'))
    assert.ok(plannerText.includes('Demonstration targets only — not NASA flight requirements'))
    return 'Committed 1–8 vs 11–18 Dec table shows A/B/C changes and both constraint verdicts; Site B recompute reports a 240 h shift and the API’s original/delayed values, without ranking.'
  })

  await test('T10', 'Mission requirement evaluation', async () => {
    await setPlanner('shackleton-rim', DEC1, DURATION)
    const tuner = page.getByRole('heading', { name: 'Mission requirements check' }).locator('xpath=ancestor::div[.//table][1]')
    await tuner.scrollIntoViewIfNeeded()
    assert.ok((await text(tuner)).includes('not NASA flight requirements'))
    await page.getByRole('button', { name: 'Check requirements' }).click()
    const region = page.getByRole('region', { name: 'Mission requirement results' })
    await region.waitFor({ timeout: 90_000 })
    let textNow = await text(region)
    assert.ok(textNow.includes('One or more constraints fail'))
    for (const c of (await requirements('shackleton-rim')).checks) {
      assert.ok(textNow.includes(c.label))
      assert.ok(textNow.includes(c.status === 'met' ? 'PASS' : c.status === 'not_met' ? 'FAIL' : 'UNDECIDED'))
    }
    const sunInput = page.getByLabel('Minimum sunlight (%)')
    const earthInput = page.getByLabel('Minimum Earth visibility (%)')
    const blackoutInput = page.getByLabel('Maximum communication blackout (h)')
    await sunInput.fill('0')
    await earthInput.fill('0')
    await blackoutInput.fill('200')
    await page.getByRole('button', { name: 'Check requirements' }).click()
    await page.waitForFunction(
      () => document.querySelector('[aria-label="Mission requirement results"]')?.textContent?.includes('Undecided'),
      null,
      { timeout: 90_000 },
    )
    textNow = await text(region)
    assert.ok(textNow.includes('Undecided'))
    assert.ok(textNow.includes('PASS'))
    assert.ok(textNow.includes('UNDECIDED'))
    const relaxed = await requirements('shackleton-rim', DEC1, DURATION, 'jpl', {
      min_sun_visible_pct: 0,
      min_earth_visible_pct: 0,
      max_earth_blackout_hours: 200,
    })
    assert.equal(relaxed.satisfied, null)
    const censored = relaxed.checks.find((c) => c.id === 'max_earth_blackout_hours')
    assert.equal(censored.status, 'unknown')
    await sunInput.fill('101')
    assert.ok((await text(page.locator('body'))).includes('Minimum sunlight must be between 0 and 100%.'))
    assert.equal(await page.getByRole('button', { name: 'Check requirements' }).isDisabled(), true)
    return 'Site A at 60/50/12 produced three FAILs matching the API; relaxing to 0/0/200 updated the checks to PASS/PASS/UNDECIDED because the 168 h blackout touches the window edge; 101% is blocked before sending.'
  })

  await test('T11', 'Error handling and retry', async () => {
    await openPlanner()
    const date = page.getByLabel('Landing time (UTC)')
    await date.fill('2031-01-01T00:00')
    await page.waitForTimeout(1200)
    const invalidText = await text(page.locator('body'))
    assert.ok(
      invalidText.includes('Dates outside the supported window') || invalidText.includes('mission window must stay between'),
      'out-of-range date did not produce a helpful message',
    )
    assert.ok(invalidText.includes('2030-12-31') || invalidText.includes('supported'), 'supported range is not shown')
    await setPlanner('shackleton-rim', DEC1, DURATION)
    assert.ok((await page.getByLabel('Landing time (UTC)').getAttribute('max')).startsWith('2030-12-31'))

    await page.getByRole('radio', { name: 'Scientific' }).click()
    await page.getByLabel('Landing site').selectOption('peak-near-shackleton')
    await page.getByText('Scientific data is not loaded').waitFor({ timeout: 90_000 })
    const missing = await text(page.locator('body'))
    assert.ok(missing.includes('No values are shown rather than substituting demo data.'))
    assert.equal(await page.getByRole('heading', { name: 'Mission summary' }).count(), 0)

    await page.getByRole('radio', { name: 'JPL Live' }).click()
    await setPlanner('shackleton-rim', DEC1, DURATION)

    await page.route('**/api/scenario', (route) => route.abort('failed'))
    await page.getByLabel('Landing site').selectOption('connecting-ridge')
    await page.getByText('Backend not reachable').waitFor({ timeout: 90_000 })
    assert.equal(await page.getByRole('heading', { name: 'Mission summary' }).count(), 0)
    await page.unroute('**/api/scenario')
    await page.getByRole('button', { name: 'Try again' }).click()
    await page.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 90_000 })
    assert.ok((await text(page.locator('body'))).includes(SITE_LABEL['connecting-ridge']))

    await page.route('**/api/scenario', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'INTERNAL', message: 'Forced acceptance-test failure', details: {} }),
      }),
    )
    await page.getByLabel('Landing site').selectOption('de-gerlache-rim')
    await page.getByText('The calculation could not run').waitFor({ timeout: 90_000 })
    assert.ok((await text(page.locator('body'))).includes('Forced acceptance-test failure'))
    await page.unroute('**/api/scenario')
    await page.getByRole('button', { name: 'Try again' }).first().click()
    await page.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 90_000 })
    assert.ok((await text(page.locator('body'))).includes(SITE_LABEL['de-gerlache-rim']))

    const boot = await context.newPage()
    await boot.route('**/api/config', (route) => route.abort('failed'))
    await boot.route('**/api/sites', (route) => route.abort('failed'))
    await boot.goto(`${APP}/#planner`, { waitUntil: 'domcontentloaded', timeout: 30_000 })
    await boot.getByText(/Backend not reachable/i).waitFor({ timeout: 30_000 })
    assert.ok(await boot.getByRole('button', { name: 'Try again' }).count())
    await boot.unroute('**/api/config')
    await boot.unroute('**/api/sites')
    await boot.getByRole('button', { name: 'Try again' }).click()
    await boot.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 90_000 })
    await boot.close()

    assert.equal(await page.getByLabel('Landing site').isVisible(), true)
    return 'Invalid/out-of-range dates, unavailable scientific site, aborted scenario requests, HTTP 500 and full boot failure all show guidance without crashes; Try again recovers each request.'
  })

  await test('T12', 'Responsive design and accessibility', async () => {
    await openPlanner()
    const desktop = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }))
    assert.ok(desktop.width <= desktop.viewport + 1, 'desktop layout overflows horizontally')

    const compare = page.getByRole('button', { name: 'Compare scenarios' })
    await compare.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('tab', { name: /All candidates/ }).waitFor({ timeout: 30_000 })
    const tab = page.getByRole('tab', { name: /All candidates/ })
    await tab.focus()
    await page.keyboard.press('Enter')
    assert.equal(await tab.getAttribute('aria-selected'), 'true')

    await page.goto(`${APP}/#planner`, { waitUntil: 'networkidle', timeout: 90_000 })
    await scenarioRange(DEC1, DURATION)
    const band = page.locator('div.relative.hatch-blocked').first()
    await band.focus()
    const before = await page.getByText(/UTC\. Move the timeline cursor/).innerText()
    await page.keyboard.press('ArrowRight')
    await page.waitForTimeout(900)
    assert.notEqual(await page.getByText(/UTC\. Move the timeline cursor/).innerText(), before)
    const body = await text(page.locator('body'))
    assert.ok(body.includes('Sun') && body.includes('Earth') && body.includes('Both'))
    assert.ok(
      body.includes('Above terrain horizon') ||
        body.includes('Blocked by terrain') ||
        body.includes('Below geometric horizon'),
      'visibility status is not presented as text',
    )
    assert.ok(body.includes('Height above terrain') && body.includes('Geometric elevation'))
    assert.ok((await page.locator('footer a').count()) >= 5, 'NASA data-source links are missing')
    assert.ok(body.includes('Not affiliated with or endorsed by NASA'))
    assert.ok(body.includes('Sourced scientific data'))

    await page.goto(`${APP}/#methodology`, { waitUntil: 'networkidle', timeout: 90_000 })
    const methodology = await text(page.locator('body'))
    assert.ok(methodology.length > 200)
    assert.ok(/not power|power/i.test(methodology), 'methodology does not explain that sunlight is not power')
    assert.ok(/link budget|communications/i.test(methodology), 'methodology does not explain Earth visibility')

    const mobile = await context.newPage()
    await mobile.setViewportSize({ width: 390, height: 844 })
    await mobile.goto(`${APP}/#planner`, { waitUntil: 'networkidle', timeout: 90_000 })
    await mobile.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 90_000 })
    const layout = await mobile.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      chart: document.querySelector('[role="img"][aria-label^="Sun and Earth"]')?.getBoundingClientRect().width ?? 0,
      pano: document.querySelector('[role="img"][aria-label^="Horizon panorama"]')?.getBoundingClientRect().width ?? 0,
    }))
    assert.ok(layout.width <= layout.viewport + 1, `mobile overflow: ${layout.width} > ${layout.viewport}`)
    assert.ok(layout.chart > 200 && layout.chart <= layout.viewport, 'timeline chart is not readable on mobile')
    assert.ok(layout.pano > 200 && layout.pano <= layout.viewport, 'panorama is not readable on mobile')
    if (SHOTS) {
      await mkdir('.tmp-acceptance', { recursive: true })
      await mobile.screenshot({ path: '.tmp-acceptance/05-mobile-planner.png' })
    }
    await mobile.getByRole('button', { name: 'Compare scenarios' }).click()
    await mobile.getByRole('tab', { name: /All candidates/ }).click()
    await mobile.getByRole('button', { name: 'Compare all candidates' }).click()
    await mobile.getByRole('region', { name: 'All-candidate comparison results' }).waitFor({ timeout: 90_000 })
    const mobileLayout = await mobile.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }))
    assert.ok(mobileLayout.width <= mobileLayout.viewport + 1, `mobile comparison overflow: ${mobileLayout.width} > ${mobileLayout.viewport}`)
    if (SHOTS) {
      await mobile.screenshot({ path: '.tmp-acceptance/06-mobile-candidates.png', fullPage: true })
    }
    await mobile.close()
    return 'Desktop and 390 px layouts do not overflow; charts/map/controls remain usable; keyboard navigation, text status labels, methodology and NASA source links are present.'
  })

  await test('E2E', 'Critical end-to-end mission-delay scenario', async () => {
    await openPlanner()
    await setPlanner('shackleton-rim', DEC1, DURATION)
    const a1 = await scenario('shackleton-rim', DEC1, DURATION)
    const a1m = new Map(a1.metrics.map((m) => [m.id, m.value]))
    await setPlanner('shackleton-rim', DEC11, DURATION)
    const a2 = await scenario('shackleton-rim', DEC11, DURATION)
    const a2m = new Map(a2.metrics.map((m) => [m.id, m.value]))
    assert.equal(a1.end_utc, '2026-12-08T00:00:00Z')
    assert.equal(a2.end_utc, '2026-12-18T00:00:00Z')

    await setPlanner('connecting-ridge', DEC11, DURATION)
    const b = await scenario('connecting-ridge', DEC11, DURATION)
    const bm = new Map(b.metrics.map((m) => [m.id, m.value]))
    assert.equal(bm.get('sun_visible_pct'), 100)
    assert.ok(Math.abs(bm.get('earth_visible_pct') - 20.53) < 1)
    assert.ok(Math.abs(bm.get('longest_earth_blackout_hours') - 133.51) < 1)

    await page.goto(`${APP}/#compare`, { waitUntil: 'networkidle', timeout: 90_000 })
    await page.getByRole('tab', { name: /All candidates/ }).click()
    await page.getByLabel('Landing time (UTC)').fill(DEC11.slice(0, 16))
    await page.getByRole('button', { name: 'Compare all candidates' }).click()
    const region = page.getByRole('region', { name: 'All-candidate comparison results' })
    await region.waitFor({ timeout: 90_000 })
    const comparison = await text(region)
    for (const id of SITE_IDS) assert.ok(comparison.includes(SITE_LABEL[id]))
    assert.ok(comparison.includes('Most sunlight:'))
    assert.ok(comparison.includes('Shortest Earth blackout:'))

    const evals = await Promise.all(SITE_IDS.map((id) => requirements(id, DEC11, DURATION)))
    assert.ok(evals.every((e) => e.satisfied === false), 'at least one candidate unexpectedly meets all targets')
    const sunFail = evals.map((e) => e.checks.find((c) => c.id === 'min_sun_visible_pct').status)
    const earthFail = evals.map((e) => e.checks.find((c) => c.id === 'min_earth_visible_pct').status)
    const blackoutFail = evals.map((e) => e.checks.find((c) => c.id === 'max_earth_blackout_hours').status)
    assert.deepEqual(sunFail, ['not_met', 'met', 'met'])
    assert.deepEqual(earthFail, ['not_met', 'not_met', 'met'])
    assert.deepEqual(blackoutFail, ['not_met', 'not_met', 'not_met'])
    const summary = await text(page.locator('body'))
    assert.ok(summary.includes('Different measures can point to different sites'))
    assert.ok(!/NASA-approved|fully safe/i.test(summary), 'UI claims NASA approval or full safety')
    assert.equal(pageErrors.length, 0, `page errors during E2E: ${pageErrors.join(' | ')}`)
    return `A: ${a1m.get('sun_visible_pct')}% Sun / ${a1m.get('earth_visible_pct')}% Earth / ${fmtHours(a1m.get('longest_earth_blackout_hours'))} blackout (1 Dec) and ${a2m.get('sun_visible_pct')}% / ${a2m.get('earth_visible_pct')}% / ${fmtHours(a2m.get('longest_earth_blackout_hours'))} (11 Dec); B: ${bm.get('sun_visible_pct')}% / ${bm.get('earth_visible_pct').toFixed(1)}% / ${fmtHours(bm.get('longest_earth_blackout_hours'))}. No candidate meets all 60/50/12 targets; C has the most Earth visibility and shortest blackout but still fails the 12 h blackout target.`
  })

  await browser.close()

  console.log('\n=== PHASE 4 ACCEPTANCE RESULTS ===')
  for (const r of results) console.log(`${r.status}  ${r.id}  ${r.title}\n      ${r.notes}`)
  const failed = results.filter((r) => r.status === 'FAIL')
  console.log(`\n${results.length - failed.length}/${results.length} tests passed`)
  if (failed.length) process.exitCode = 1
}

main().catch(async (error) => {
  console.error(error)
  await browser?.close().catch(() => {})
  process.exitCode = 1
})
