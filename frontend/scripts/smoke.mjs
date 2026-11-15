import assert from 'node:assert/strict'
import { chromium } from 'playwright-core'

const CHROME =
  process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const BASE = process.env.LUNANAV_URL ?? 'http://127.0.0.1:5173'
const SHOTS = process.env.SMOKE_SHOTS === '1'

async function widthReport(page) {
  return page.evaluate(() => ({
    viewport: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
  }))
}

async function assertNoOverflow(page, label) {
  const report = await widthReport(page)
  assert.ok(
    report.documentWidth <= report.viewport + 1,
    `${label}: page is ${report.documentWidth}px wide in a ${report.viewport}px viewport`,
  )
  return report
}

async function waitForScenario(page, action) {
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/scenario') &&
        response.request().method() === 'POST' &&
        response.ok(),
    ),
    action(),
  ])
}

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
const pageErrors = []
const apiFailures = []
page.on('pageerror', (error) => pageErrors.push(error.message))
page.on('response', (response) => {
  if (response.url().includes('/api/') && response.status() >= 400) {
    apiFailures.push(`${response.status()} ${response.url()}`)
  }
})

try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.getByText('South polar region').waitFor()
  await assertNoOverflow(page, 'planner at 390px')
  if (SHOTS) await page.screenshot({ path: '.tmp-shots/smoke-mobile-planner.png' })

  const siteSelect = page.getByLabel('Landing site')
  for (const label of [
    'Shackleton-de Gerlache Connecting Ridge (CR1)',
    'de Gerlache Crater Rim (GR1)',
    'Shackleton Crater Rim (SR1)',
  ]) {
    await waitForScenario(page, () => siteSelect.selectOption({ label }))
    await page.getByText(label.split(' (')[0]).first().waitFor()
  }

  const dateInput = page.getByLabel('Landing time (UTC)')
  await waitForScenario(page, () => dateInput.fill('2026-12-11T00:00'))
  const duration = page.getByLabel('Duration in hours')
  await waitForScenario(page, () => duration.fill('72'))

  const zoom = page
    .getByRole('group', { name: 'Timeline zoom' })
    .getByRole('button', { name: '24 h', exact: true })
  await zoom.click()
  assert.equal(await zoom.getAttribute('aria-pressed'), 'true', '24 h zoom should be selected')
  const snapshotLine = page.getByText(/UTC\. Move the timeline cursor/)
  const before = await snapshotLine.textContent()
  await page.getByRole('button', { name: 'Next sample' }).click()
  await page.waitForTimeout(400)
  assert.notEqual(await snapshotLine.textContent(), before, 'snapshot should follow the timeline cursor')

  await page.getByRole('button', { name: /Compare scenarios/ }).click()
  await page.getByRole('tab', { name: /All candidates/ }).click()
  await page.getByRole('button', { name: 'Compare all candidates' }).click()
  await page.getByText('Most sunlight:').waitFor({ timeout: 30_000 })
  assert.equal(
    await page.locator('dt:visible').filter({ hasText: 'Sun visible' }).count(),
    3,
    'phone layout should show one result card per candidate',
  )
  await assertNoOverflow(page, 'all candidates at 390px')
  if (SHOTS) await page.screenshot({ path: '.tmp-shots/smoke-mobile-candidates.png' })

  await page.getByRole('tab', { name: /Reschedule a mission/ }).click()
  await page.getByText(/Effect of moving the landing/).waitFor({ timeout: 30_000 })

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.getByRole('tab', { name: /All candidates/ }).click()
  await page.getByRole('button', { name: 'Compare all candidates' }).click()
  await page.getByText('Most sunlight:').waitFor({ timeout: 30_000 })
  await assertNoOverflow(page, 'all candidates at 1440px')
  assert.equal(
    await page.locator('table:visible tbody tr').first().locator('td').count(),
    8,
    'desktop should show the full comparison table',
  )
  if (SHOTS) await page.screenshot({ path: '.tmp-shots/smoke-desktop-candidates.png' })

  assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(' | ')}`)
  assert.deepEqual(apiFailures, [], `API failures: ${apiFailures.join(' | ')}`)
  console.log('Smoke test passed: 3 sites, date, duration, timeline, all-candidate comparison, delay panel, 390/1440px layouts.')
} finally {
  await browser.close()
}
