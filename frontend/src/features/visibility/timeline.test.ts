import { describe, expect, it } from 'vitest'
import { zoomDomain } from './timeline'

const H = 3_600_000
const t0 = Date.parse('2026-12-01T00:00:00Z')
const t1 = t0 + 168 * H

describe('zoomDomain', () => {
  it('returns the full mission when no zoom is selected', () => {
    expect(zoomDomain(t0, t1, t0 + 50 * H, null)).toEqual([t0, t1])
  })

  it('returns the full mission when the requested span is not shorter', () => {
    expect(zoomDomain(t0, t1, t0 + 50 * H, 168)).toEqual([t0, t1])
    expect(zoomDomain(t0, t1, t0 + 50 * H, 200)).toEqual([t0, t1])
  })

  it('centres a 24 h window on the inspected sample', () => {
    const cursor = t0 + 84 * H
    expect(zoomDomain(t0, t1, cursor, 24)).toEqual([cursor - 12 * H, cursor + 12 * H])
  })

  it('pulls the window inside the mission near the start', () => {
    expect(zoomDomain(t0, t1, t0 + 2 * H, 24)).toEqual([t0, t0 + 24 * H])
  })

  it('pulls the window inside the mission near the end', () => {
    expect(zoomDomain(t0, t1, t1 - 2 * H, 24)).toEqual([t1 - 24 * H, t1])
  })

  it('handles a zero-length mission without dividing by zero', () => {
    expect(zoomDomain(t0, t0, t0, 24)).toEqual([t0, t0])
  })
})
