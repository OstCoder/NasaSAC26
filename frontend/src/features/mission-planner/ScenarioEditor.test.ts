import { describe, expect, it } from 'vitest'
import { rangeProblem } from './ScenarioEditor'

const START = '2026-12-01T00:00:00Z'
const END = '2026-12-18T23:59:59Z'
const draft = {
  location: { site_id: 'A' },
  locationName: 'Shackleton Rim',
  landing_utc: START,
  duration_hours: 168,
}

describe('rangeProblem', () => {
  it('accepts the default seven-day mission', () => {
    expect(rangeProblem(draft, START, END)).toBeNull()
  })

  it('rejects a mission whose end falls outside the supported window', () => {
    expect(rangeProblem({ ...draft, landing_utc: '2026-12-16T00:00:00Z' }, START, END)).toMatch(
      /must stay between/,
    )
  })

  it('rejects a landing date before the supported window', () => {
    expect(rangeProblem({ ...draft, landing_utc: '2026-11-30T23:00:00Z' }, START, END)).toMatch(
      /must stay between/,
    )
  })

  it('rejects an unparseable date rather than sending it to the backend', () => {
    expect(rangeProblem({ ...draft, landing_utc: 'not-a-date' }, START, END)).toBe(
      'Enter a valid UTC landing time.',
    )
  })
})
