import { describe, expect, it } from 'vitest'
import { craterRing } from './craterRing'

describe('craterRing', () => {
  it('has the right size on the equator', () => {
    const ring = craterRing(0, 10, 60.64)
    expect(Math.max(...ring.map(([lat]) => lat))).toBeCloseTo(1, 2)
    expect(Math.max(...ring.map(([, lon]) => lon))).toBeCloseTo(11, 2)
  })
  it('widens in longitude away from the equator, as circles do on this projection', () => {
    const ring = craterRing(-60, 0, 60.64)
    expect(Math.max(...ring.map(([, lon]) => lon))).toBeCloseTo(2, 1)
  })
})
