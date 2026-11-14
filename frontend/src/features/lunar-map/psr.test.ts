import { describe, expect, it } from 'vitest'
import { simplifyRing, toShape } from './psr'
import type { PsrOut } from '@/types/api'

const psr: PsrOut = {
  psr_id: 'SP_825610',
  area_km2: 124.33,
  perimeter_km: 61.1,
  centroid_latitude_deg: -88.57,
  centroid_longitude_deg: 204.35,
  near_crater: 'Shackleton',
  rings: [[[10, 0], [10.02, 0.01], [10.04, 0.02], [10, 5], [0, 5], [0, 0], [10, 0]]],
}

describe('simplifyRing', () => {
  it('keeps corners and the closing point, drops near-duplicate vertices', () => {
    const out = simplifyRing(psr.rings[0])
    expect(out).toEqual([[10, 0], [10, 5], [0, 5], [0, 0], [10, 0]])
  })
  it('never returns fewer than 4 points', () => {
    const dense = Array.from({ length: 20 }, (_, i) => [i * 0.01, 0])
    expect(simplifyRing(dense).length).toBeGreaterThanOrEqual(4)
  })
  it('respects the tolerance', () => {
    const ring = [[0, 0], [1, 0], [2, 0], [2, 2], [0, 2], [0, 0]]
    expect(simplifyRing(ring, 1.1)).toEqual([[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]])
  })
})

describe('toShape', () => {
  it('swaps projected [x, y] km into Leaflet [lat, lng] order', () => {
    const [first] = toShape(psr).positions[0]
    expect(first[0]).toBe(0) // y first
    expect(first[1]).toBe(10) // x second
  })
  it('keeps every ring and point count >= 4', () => {
    const shape = toShape(psr)
    expect(shape.psr.psr_id).toBe('SP_825610')
    shape.positions.forEach((ring) => expect(ring.length).toBeGreaterThanOrEqual(4))
  })
})
