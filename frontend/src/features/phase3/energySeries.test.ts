import { describe, expect, it } from 'vitest'
import type { PowerSeries } from '@/types/api'
import { blockedSpans, chargingSpans, dischargingSpans, toEnergyPoints } from './energySeries'

const times = [
  '2026-12-01T00:00:00Z',
  '2026-12-01T01:00:00Z',
  '2026-12-01T02:00:00Z',
  '2026-12-01T03:00:00Z',
  '2026-12-01T04:00:00Z',
]

const series: PowerSeries = {
  times_utc: times,
  solar_w: [0, 10, 0, 0, 12],
  load_w: [40, 40, 40, 40, 40],
  battery_wh: [1000, 970, 940, 910, 882],
  battery_soc_pct: [100, 97, 94, 91, 88.2],
  sun_visible: [false, true, false, false, true],
  charging: [false, false, false, false, false],
  discharging: [true, true, true, true, true],
  unserved_wh: [0, 0, 0, 0, 0],
}

describe('energy timeline helpers', () => {
  it('maps aligned arrays into chart points', () => {
    const points = toEnergyPoints(series)
    expect(points).toHaveLength(5)
    expect(points[1]).toMatchObject({ solar: 10, load: 40, battery: 970, soc: 97, sun: true })
    expect(points[0].t).toBe(Date.parse(times[0]))
    expect(points[4].unserved).toBe(0)
  })

  it('does not invent points when an array is short', () => {
    const points = toEnergyPoints({ ...series, solar_w: [0, 10] })
    expect(points).toHaveLength(2)
  })

  it('merges adjacent blocked samples into shaded spans', () => {
    expect(blockedSpans(series)).toEqual([
      { x1: Date.parse(times[0]), x2: Date.parse(times[1]) },
      { x1: Date.parse(times[2]), x2: Date.parse(times[4]) },
    ])
  })

  it('returns no spans when the Sun is visible everywhere', () => {
    expect(blockedSpans({ ...series, sun_visible: [true, true, true, true, true] })).toEqual([])
  })

  it('isolates charging and discharging spans', () => {
    expect(chargingSpans(series)).toEqual([])
    expect(dischargingSpans(series)).toEqual([
      { x1: Date.parse(times[0]), x2: Date.parse(times[4]) },
    ])
  })
})
