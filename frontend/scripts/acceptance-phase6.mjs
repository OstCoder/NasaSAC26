/**
 * Phase 6 acceptance against the real FastAPI backend and running app.
 *
 *   cd backend && uvicorn app.main:app --port 8000
 *   cd frontend && npm run dev
 *   cd frontend && npm run acceptance:phase6
 *
 * Set ACCEPTANCE_SHOTS=1 to keep screenshots in .tmp-acceptance-phase6/.
 */
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright-core'

const APP = (process.env.LUNANAV_APP ?? 'http://127.0.0.1:5173').replace(/\/$/, '')
const API = (process.env.LUNANAV_API ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const SHOTS = process.env.ACCEPTANCE_SHOTS === '1'
const CHROME = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const DEC1 = '2026-12-01T00:00:00Z'
const DURATION = 168

const results = []
let browser
let context
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

const text = async (locator) => (await locator.innerText()).replace(/\s+/g, ' ').trim()

async function screenshot(name) {
  if (!SHOTS) return
  await mkdir('.tmp-acceptance-phase6', { recursive: true })
  await page.screenshot({
    path: `.tmp-acceptance-phase6/${String(++shots).padStart(2, '0')}-${name}.png`,
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
    await page.screenshot({ path: `/tmp/lunanav-phase6-failure-${id}.png`, fullPage: true }).catch(() => {})
  }
}

async function openPlanner() {
  await page.goto(`${APP}/#planner`, { waitUntil: 'networkidle', timeout: 120_000 })
  await page.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 120_000 })
}

async function main() {
  browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--use-gl=angle', '--use-angle=swiftshader'],
  })
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  page = await context.newPage()
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('response', (response) => {
    if (response.url().includes('/api/') && response.status() >= 500) {
      apiFailures.push(`${response.status()} ${response.url()}`)
    }
  })

  await test('P6-1', 'PSR catalogue and proximity API', async () => {
    const catalogue = await apiGet('/api/science/psrs')
    assert.equal(catalogue.schema, 'lunanav.science_psr_catalogue.v1')
    assert.equal(catalogue.catalogue_count, 653)
    assert.equal(catalogue.count, 390)
    assert.equal(catalogue.area_threshold_km2, 5)
    assert.equal(catalogue.projection.sphere_radius_km, 1737.4)
    assert.ok(catalogue.source.provider.includes('LROC'))
    assert.ok(catalogue.psrs[0].rings[0].length > 3)

    const nearest = await apiGet('/api/science/nearest-psr?site_id=shackleton-rim')
    assert.equal(nearest.nearest_psr.psr_id, 'SP_896450_1282030')
    assert.ok(Math.abs(nearest.nearest_psr.boundary_distance_km - 2.479) < 0.001)
    assert.ok(nearest.nearest_psr.centroid_distance_km > nearest.nearest_psr.boundary_distance_km)
    assert.equal(nearest.nearest_psr.distance_uncertainty_km, 0.06)
    assert.equal(nearest.water_ice.confirmed, null)
    assert.equal(nearest.water_ice.status, 'not_assessed')
    assert.ok(nearest.limits.some((line) => line.includes('not a traverse')))

    const outOfRange = await fetch(`${API}/api/science/nearest-psr`)
    assert.equal(outOfRange.status, 422)
    return `Catalogue ${catalogue.count}/${catalogue.catalogue_count} polygons; Shackleton nearest ${nearest.nearest_psr.boundary_distance_km} km; centroid ${nearest.nearest_psr.centroid_distance_km} km; water ice explicitly not assessed.`
  })

  await test('P6-2', 'Site science context and mesh API', async () => {
    const contextBody = await apiGet('/api/science/site-context?site_id=de-gerlache-rim')
    assert.equal(contextBody.schema, 'lunanav.science_context.v1')
    assert.equal(contextBody.nearest_psr.psr_id, 'SP_883120_2691430')
    assert.equal(contextBody.terrain.available, true)
    assert.equal(contextBody.terrain.coverage.near.pixel_m, 5)
    assert.equal(contextBody.terrain.coverage.far.pixel_m, 80)
    assert.equal(contextBody.science.water_ice_confirmed, null)
    assert.equal(contextBody.visibility_windows.initial.available, true)
    assert.equal(contextBody.visibility_windows.alternative.available, true)

    const mesh = await apiGet('/api/terrain/mesh?site_id=de-gerlache-rim')
    const direct = await apiGet('/api/terrain-dem?site_id=de-gerlache-rim')
    assert.equal(mesh.schema, 'lunanav.terrain_dem.v1')
    assert.equal(mesh.source.sha256, direct.source.sha256)
    assert.equal(mesh.grid.size, 128)
    assert.equal(mesh.grid.cell_m, 125)
    assert.equal(mesh.heights_m.length, 128)
    return 'Context carries 5 m/80 m terrain, both windows, PSR geometry and unknown water ice; /api/terrain/mesh matches the committed DEM checksum.'
  })

  await test('P6-3', 'Science page, map layer and education', async () => {
    const started = Date.now()
    await page.goto(`${APP}/#science`, { waitUntil: 'networkidle', timeout: 120_000 })
    await page.getByRole('heading', { name: 'Science exploration' }).waitFor({ timeout: 120_000 })
    await page.getByText('Water ice: not assessed').waitFor({ timeout: 120_000 })
    await page.getByText('Nearest mapped PSR').first().waitFor({ timeout: 120_000 })
    const nav = await page.evaluate(() => {
      const entry = performance.getEntriesByType('navigation')[0]
      return {
        dcl: entry?.domContentLoadedEventEnd ?? 0,
        load: entry?.loadEventEnd ?? 0,
      }
    })
    assert.ok(nav.load < 20_000, `initial load ${nav.load} ms exceeded 20 s`)
    assert.ok(await page.locator('.leaflet-container').count(), 'science PSR map is missing')
    const body = await text(page.locator('body'))
    assert.ok(body.toUpperCase().includes('NEAREST MAPPED PSR'))
    assert.ok(body.includes('Boundary distance'))
    assert.ok(body.includes('Water ice: not assessed'))
    assert.ok(body.includes('Unknown is not evidence of absence'))
    assert.ok(body.includes('Scientific model labels'))
    assert.ok(body.includes('TERRAIN-AWARE MODEL'))
    assert.ok(body.includes('Learn the science'))
    assert.ok(body.includes('Why are water-ice deposits scientifically important?'))
    assert.ok(body.includes('NASA LOLA south-pole topography'))
    assert.ok(!/confirmed water ice|NASA-approved|fully safe/i.test(body), 'science page makes an unsupported claim')
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    assert.equal(apiFailures.length, 0, `API failures: ${apiFailures.join(' | ')}`)
    await screenshot('science-desktop')
    return `Science view rendered in ${Date.now() - started} ms (navigation load ${nav.load} ms); PSR map, context, model labels, education and attribution are present.`
  })

  await test('P6-4', 'Science page at 390 px', async () => {
    const mobile = await context.newPage()
    await mobile.setViewportSize({ width: 390, height: 844 })
    await mobile.goto(`${APP}/#science`, { waitUntil: 'networkidle', timeout: 120_000 })
    await mobile.getByRole('heading', { name: 'Science exploration' }).waitFor({ timeout: 120_000 })
    await mobile.getByText('Water ice: not assessed').waitFor({ timeout: 120_000 })
    const layout = await mobile.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      map: document.querySelector('.leaflet-container')?.getBoundingClientRect().width ?? 0,
    }))
    assert.ok(layout.width <= layout.viewport + 1, `science page overflows: ${layout.width} > ${layout.viewport}`)
    assert.ok(layout.map > 250 && layout.map <= layout.viewport, `science map is not readable: ${layout.map} px`)
    if (SHOTS) {
      await mkdir('.tmp-acceptance-phase6', { recursive: true })
      await mobile.screenshot({ path: '.tmp-acceptance-phase6/mobile-science.png', fullPage: true })
    }
    await mobile.close()
    return `390 px science page has no horizontal overflow (${layout.width}/${layout.viewport}) and the PSR map is ${layout.map.toFixed(0)} px wide.`
  })

  await test('P6-5', 'Planner PSR layer toggle and nearest highlight', async () => {
    await openPlanner()
    const toggle = page.getByLabel('PSR layer')
    assert.equal(await toggle.isChecked(), true)
    const nearestCount = () => page.locator('.leaflet-tooltip').evaluateAll((nodes) =>
      nodes.filter((node) => node.textContent?.includes('Nearest mapped PSR')).length)
    await page.waitForFunction(() =>
      [...document.querySelectorAll('.leaflet-tooltip')].some((node) => node.textContent?.includes('Nearest mapped PSR')),
      null, { timeout: 120_000 })
    assert.ok((await nearestCount()) > 0)
    await toggle.uncheck()
    await page.waitForFunction(() =>
      ![...document.querySelectorAll('.leaflet-tooltip')].some((node) => node.textContent?.includes('Nearest mapped PSR')),
      null, { timeout: 30_000 })
    await toggle.check()
    await page.waitForFunction(() =>
      [...document.querySelectorAll('.leaflet-tooltip')].some((node) => node.textContent?.includes('Nearest mapped PSR')),
      null, { timeout: 30_000 })
    const body = await text(page.locator('body'))
    assert.ok(body.includes('PSR · LROC/LOLA >5 km²'))
    assert.ok(body.includes('Gold outline: nearest to selected site'))
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    return 'PSR layer starts on, hides on toggle, returns with the gold nearest-PSR highlight, and carries its LROC legend.'
  })

  await test('P6-6', 'Mission playback speed and transition marker', async () => {
    await openPlanner()
    await page.getByLabel('Landing site').selectOption('connecting-ridge')
    await page.getByLabel('Landing time (UTC)').fill('2026-12-11T00:00')
    await page.getByRole('heading', { name: 'Mission summary' }).waitFor({ timeout: 120_000 })
    await page.waitForTimeout(800)
    const before = await page.getByText(/UTC\. Move the timeline cursor/).innerText()
    await page.getByRole('button', { name: '4×' }).click()
    assert.equal(await page.getByRole('button', { name: '4×' }).getAttribute('aria-pressed'), 'true')
    await page.getByRole('button', { name: 'Play through mission' }).click()
    await page.waitForTimeout(650)
    await page.getByRole('button', { name: 'Pause' }).click()
    const after = await page.getByText(/UTC\. Move the timeline cursor/).innerText()
    assert.notEqual(after, before, 'playback did not advance the inspected time')
    const body = await text(page.locator('body'))
    assert.ok(body.includes('Next modelled edge:'), 'next transition readout is missing')
    assert.ok(body.includes('The dashed amber rule marks it'), 'transition marker description is missing')
    await screenshot('planner-playback')
    return `4× playback advanced the shared snapshot from ${before.split(' ')[0]} to ${after.split(' ')[0]}; the next modelled edge is shown.`
  })

  await test('P6-7', '3D terrain shadows, marker and scale', async () => {
    await openPlanner()
    const enable = page.getByRole('button', { name: 'Enable 3D view' })
    await enable.scrollIntoViewIfNeeded()
    await enable.click()
    await page.getByText('Terrain shadow: local ray-march').waitFor({ timeout: 120_000 })
    await page.locator('canvas').last().waitFor({ timeout: 120_000 })
    const body = await text(page.locator('body'))
    assert.ok(body.includes('% shadowed'), 'ray-march shadow percentage is missing')
    assert.ok(body.includes('Blue marker: selected site cell'), 'landing marker legend is missing')
    assert.ok(body.includes('125 m cells'), 'terrain scale is missing')
    assert.ok(body.includes('vertical'), 'vertical exaggeration label is missing')
    assert.ok(body.includes('not a PSR map') || body.includes('not a PSR classifier'), 'shadow/PSR distinction is missing')
    await screenshot('terrain-3d')
    return 'Lazy 3D scene rendered a LOLA mesh, landing marker, local ray-march shadow percentage and a labelled 125 m/vertical-exaggeration scale.'
  })

  await test('P6-8', 'Transparency, missing-data handling and no overclaim', async () => {
    await page.goto(`${APP}/#science`, { waitUntil: 'networkidle', timeout: 120_000 })
    await page.getByRole('heading', { name: 'Science exploration' }).waitFor({ timeout: 120_000 })
    await page.getByText('Water ice: not assessed').waitFor({ timeout: 120_000 })
    const body = await text(page.locator('body'))
    for (const phrase of [
      'PSR boundaries:', 'Terrain:', 'Ephemeris:', 'Coordinate frame:',
      '120 m at 75–82°S and 60 m poleward of 82°S',
      'UNAVAILABLE DATA',
      'Unknown is not evidence of absence',
      'not evidence of water ice or a safe traverse',
    ]) {
      assert.ok(body.includes(phrase), `missing transparency phrase: ${phrase}`)
    }
    assert.ok(!/confirmed water ice|ice concentration [0-9]|NASA-approved/i.test(body))
    assert.equal(pageErrors.length, 0, `page errors: ${pageErrors.join(' | ')}`)
    assert.equal(apiFailures.length, 0, `API failures: ${apiFailures.join(' | ')}`)
    return 'Sources, coordinate/resolution conventions, model labels, unknowns and the no-overclaim contract are visible; no 5xx or page errors.'
  })

  await browser.close()
  console.log('\n=== PHASE 6 ACCEPTANCE RESULTS ===')
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
