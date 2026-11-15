import { describe, expect, it } from 'vitest'
import { terrainIllumination } from './terrainShadow'

const flat = (size = 7) => Array.from({ length: size }, () => Array<number>(size).fill(0))

describe('terrainIllumination', () => {
  it('lights flat ground for a Sun above the horizon', () => {
    const result = terrainIllumination({ heights: flat(), cellM: 125 }, {
      az: 90, el: 45,
    })
    expect(result.litFraction).toBe(1)
    expect(result.shadowFraction).toBe(0)
    expect(result.values.every((value) => value > 0)).toBe(true)
    expect(result.rayLengthKm).toBeCloseTo(12, 3)
  })

  it('marks every cell dark when the Sun is below the horizon', () => {
    const result = terrainIllumination({ heights: flat(), cellM: 125 }, {
      az: 90, el: -1,
    })
    expect(result.litFraction).toBe(0)
    expect(result.shadowFraction).toBe(1)
    expect(result.values.every((value) => value === 0)).toBe(true)
  })

  it('casts a ray shadow behind a tall east wall', () => {
    const heights = flat()
    for (let row = 0; row < heights.length; row++) heights[row][4] = 1000
    const result = terrainIllumination({ heights, cellM: 125 }, {
      az: 90, el: 10,
    })
    // The wall itself and the cells west of it are shadowed; the far east side can see the Sun.
    expect(result.values[3 * 7 + 0]).toBe(0)
    expect(result.values[3 * 7 + 3]).toBe(0)
    expect(result.litFraction).toBeGreaterThan(0)
    expect(result.litFraction).toBeLessThan(0.9)
  })

  it('does not cast the same shadow when the Sun is on the opposite side', () => {
    const heights = flat()
    for (let row = 0; row < heights.length; row++) heights[row][4] = 1000
    const east = terrainIllumination({ heights, cellM: 125 }, {
      az: 270, el: 10,
    })
    // Looking west from the wall's east side: the cell just east of the wall is shadowed,
    // while the west side is now the lit side.
    expect(east.values[3 * 7 + 6]).toBe(0)
    expect(east.values[3 * 7 + 2]).toBeGreaterThan(0)
  })
})
