import { describe, expect, it } from 'vitest'
import { nightPolygon, polarNightRings } from './night'

const sinElevation = (lat: number, lon: number, sunLat: number, sunLon: number) => {
  const r = Math.PI / 180
  return Math.sin(lat * r) * Math.sin(sunLat * r) + Math.cos(lat * r) * Math.cos(sunLat * r) * Math.cos((lon - sunLon) * r)
}

describe('nightPolygon', () => {
  it('follows the line where the Sun is on the horizon', () => {
    for (const [sunLat, sunLon] of [[1.5, 40], [-1.5, -120], [0, 90]]) {
      for (const [lat, lon] of nightPolygon(sunLat, sunLon).slice(0, -2)) {
        expect(Math.abs(sinElevation(lat, lon, sunLat, sunLon))).toBeLessThan(0.01)
      }
    }
  })
  it('closes around the pole that is in darkness', () => {
    expect(nightPolygon(1.5, 0).at(-1)?.[0]).toBe(-90)
    expect(nightPolygon(-1.5, 0).at(-1)?.[0]).toBe(90)
  })
})

describe('polarNightRings', () => {
  it('leaves the pole dark when the Sun is north of the equator', () => {
    const [ring] = polarNightRings(1.5, 40)
    expect(Math.max(...ring.map(([lat]) => lat))).toBeLessThanOrEqual(-80)
    expect(polarNightRings(1.5, 40)).toHaveLength(1)
  })
  it('cuts the sunlit polar cap out of the dark band when the Sun is south of the equator', () => {
    const [outer, hole] = polarNightRings(-1.5, 40)
    expect(outer.every(([lat]) => lat === -80)).toBe(true)
    // Anti-sun meridian: the terminator is 1.5° from the pole. Sun meridian: all of it is lit.
    const at = (lon: number) => hole.find((p) => p[1] === lon)![0]
    expect(at(-140)).toBeCloseTo(-88.5, 1)
    expect(at(40)).toBe(-80)
  })
})
