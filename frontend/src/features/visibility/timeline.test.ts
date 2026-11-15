import { describe, expect, it } from 'vitest'
import type { Interval, IntervalSet } from '@/types/api'
import { nextTransition, zoomDomain } from './timeline'

const interval = (start: string, end: string): Interval => ({
  start_utc: start,
  end_utc: end,
  duration_hours: (Date.parse(end) - Date.parse(start)) / 3_600_000,
  clipped_start: false,
  clipped_end: false,
})

const emptyIntervals = (): IntervalSet => ({
  sun_visible: [], earth_visible: [], both_visible: [],
  sun_blocked: [], earth_blocked: [], neither_visible: [],
})

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

describe('nextTransition', () => {
  it('returns the first visibility edge after the cursor across both bodies', () => {
    const intervals = emptyIntervals()
    intervals.sun_visible = [interval('2026-12-01T02:00:00Z', '2026-12-01T05:00:00Z')]
    intervals.earth_visible = [interval('2026-12-01T03:00:00Z', '2026-12-01T06:00:00Z')]
    const result = nextTransition(intervals, Date.parse('2026-12-01T01:00:00Z'))
    expect(result?.label).toBe('Sunrise')
    expect(result?.body).toBe('sun')
    expect(result?.time).toBe(Date.parse('2026-12-01T02:00:00Z'))
  })

  it('uses a set when the body is already visible', () => {
    const intervals = emptyIntervals()
    intervals.earth_visible = [interval('2026-12-01T03:00:00Z', '2026-12-01T06:00:00Z')]
    const result = nextTransition(intervals, Date.parse('2026-12-01T04:00:00Z'))
    expect(result?.label).toBe('Earthset')
    expect(result?.time).toBe(Date.parse('2026-12-01T06:00:00Z'))
  })

  it('returns null when no edge remains', () => {
    expect(nextTransition(emptyIntervals(), t0)).toBeNull()
  })
})
